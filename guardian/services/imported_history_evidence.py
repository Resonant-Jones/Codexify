"""Bounded, ephemeral imported-record inspection; no interpretation or writes.

The authenticated principal and additional record-read decisions come from the
trusted caller, never imported metadata. See the companion architecture contract.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from typing import Callable

import psycopg
from fastapi import HTTPException
from psycopg.pq import TransactionStatus
from psycopg.rows import dict_row

from guardian.conversation_origin import ConversationOriginSystem
from guardian.core.dependencies import RequestUserScope
from guardian.core.project_ownership import classify_project_ownership
from guardian.core.thread_access import require_thread_read_access

MAX_THREADS = 20
MAX_MESSAGES = 100
MAX_INSPECTED_MESSAGES = 1000
MAX_EXCERPT_BYTES = 8192
MAX_RESPONSE_BYTES = 262144
MAX_OFFSET = 100000
# Existing persisted importer markers, NOT new origin or protocol vocabulary.
_IMPORT_MARKERS = {
    ConversationOriginSystem.OPENAI: ("chatgpt_import", "chatgpt_v1_canonical"),
    ConversationOriginSystem.ANTHROPIC: ("claude_import", "claude_v1_canonical"),
}


class EvidenceRequestError(ValueError):
    """Invalid explicit selection or budget (no record content)."""


class EvidenceAccessError(PermissionError):
    """Missing, denied or conflicted authority (no record content)."""


class EvidenceMetadataError(ValueError):
    """Canonical metadata integrity prevents a safe projection."""


class EvidenceReadError(RuntimeError):
    """Database read failed; this is never a successful empty result."""


@dataclass(frozen=True)
class ThreadReadDecision:
    thread_id: int
    record_read_allowed: bool | None
    source_read_allowed: bool | None
    # None means unresolved; True also covers an explicitly resolved absence
    # of an independent diary read lock. Modeling flags do not set this value.
    diary_read_allowed: bool | None


@dataclass(frozen=True)
class RecordReadAuthority:
    """Trusted, request-only restriction receipt; never an ownership grant.

    Bind to the very same server-resolved principal object for this invocation.
    Every selected thread needs an explicit resolved decision. No defaults.
    """

    principal: RequestUserScope
    project_id: int
    decisions: tuple[ThreadReadDecision, ...]


@dataclass(frozen=True)
class InspectionLimits:
    max_messages: int
    max_inspected_messages: int
    max_excerpt_bytes: int
    max_response_bytes: int


@dataclass(frozen=True)
class ImportedExcerpt:
    project_id: int
    thread_id: int
    message_id: int
    origin_system: ConversationOriginSystem
    source_thread_id: str | None
    # Stored importer reference; may be synthesized by the existing importer.
    source_message_id: str | None
    source_message_id_verified_original: bool
    canonical_role: str
    original_role: str | None
    original_content_type: str | None
    importer_role: str | None
    importer_content_type: str | None
    excerpt: str
    excerpt_truncated: bool
    source_time: str | None
    source_time_field: str | None
    normalized_source_time: str | None
    normalized_time_matches_source: bool
    fallback_or_uncertain_time: bool
    imported_at: str
    canonical_event_at: str
    canonical_created_at: str


@dataclass(frozen=True)
class ThreadCoverage:
    thread_id: int
    origin_system: ConversationOriginSystem
    stored_messages: int
    importer_messages_kept: int | None
    importer_messages_filtered: int | None


@dataclass(frozen=True)
class EvidenceCoverage:
    total_stored_messages: int
    inspected_records: int
    returned_records: int
    unproven_import_records: int
    omitted_by_message_limit: int
    omitted_by_response_budget: int
    truncated_excerpts: int
    offset: int
    next_offset: int | None
    selected_window_complete: bool
    pagination_limit_reached: bool
    # Import summaries cannot prove that the complete source archive arrived.
    source_archive_completeness_verified: bool = False


@dataclass(frozen=True)
class ImportedHistoryEvidence:
    project_id: int
    selected_thread_ids: tuple[int, ...]
    permitted_origins: tuple[ConversationOriginSystem, ...]
    read_at: str
    threads: tuple[ThreadCoverage, ...]
    excerpts: tuple[ImportedExcerpt, ...]
    coverage: EvidenceCoverage

    def to_json(self) -> str:
        """The canonical encoding on which the total byte budget is enforced."""
        return json.dumps(
            asdict(self), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )


def _positive(value: object, ceiling: int) -> bool:
    return type(value) is int and 0 < value <= ceiling


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or len(value.encode("utf-8")) > 1024:
        raise EvidenceMetadataError("Invalid bounded provenance field")
    return value or None


def _time(value: object) -> str | None:
    if value is None:
        return None
    try:
        if isinstance(value, datetime):
            parsed = value
        elif type(value) in (int, float) and math.isfinite(value):
            parsed = datetime.fromtimestamp(value, tz=timezone.utc)
        elif isinstance(value, str):
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        else:
            return None
        # An unzoned timestamp is ambiguous, not a verified original instant.
        if parsed.tzinfo is None:
            return None
        return parsed.astimezone(timezone.utc).isoformat()
    except (ValueError, OverflowError, OSError):
        return None


def _source_time(value: object) -> str | None:
    # Match the existing export epoch normalization, including numeric strings
    # and milliseconds. Do not import the migration module (it has write/queue
    # dependencies). Unzoned ISO source values remain uncertain here.
    if type(value) in (int, float, str):
        try:
            epoch = float(value)
            if math.isfinite(epoch):
                return _time(epoch / 1000 if epoch > 1_000_000_000_000 else epoch)
        except (ValueError, OverflowError):
            pass
    return _time(value)


def _summary_count(meta: dict, field: str) -> int | None:
    summary = meta.get("import_summary")
    if summary is None:
        return None
    if not isinstance(summary, dict):
        raise EvidenceMetadataError("Malformed import summary")
    count = summary.get(field)
    if count is None:
        return None
    if type(count) is not int or count < 0:
        raise EvidenceMetadataError("Malformed import summary count")
    return count


class ImportedHistoryEvidenceReader:
    """Read via a fresh psycopg connection factory (e.g. PgDB._connect).

    Never use a borrowed write transaction or PgDB.cursor (unimplemented).
    All resource authorization and queries share one read-only snapshot.
    """

    def __init__(self, connect: Callable[[], psycopg.Connection]):
        self._connect = connect

    def read(
        self,
        *,
        principal: RequestUserScope,
        project_id: int,
        thread_ids: tuple[int, ...],
        origins: tuple[ConversationOriginSystem, ...],
        limits: InspectionLimits,
        authority: RecordReadAuthority,
        offset: int = 0,
    ) -> ImportedHistoryEvidence:
        if not isinstance(principal, RequestUserScope):
            raise EvidenceAccessError("Authenticated account required")
        account = principal.account_id or principal.user_id
        if not isinstance(account, str) or not account.strip():
            raise EvidenceAccessError("Authenticated account required")
        if not _positive(project_id, 2147483647):
            raise EvidenceRequestError("Explicit canonical Project required")
        if (
            not isinstance(thread_ids, tuple)
            or not 1 <= len(thread_ids) <= MAX_THREADS
            or any(not _positive(t, 2147483647) for t in thread_ids)
            or len(set(thread_ids)) != len(thread_ids)
        ):
            raise EvidenceRequestError("Invalid bounded thread selection")
        if (
            not isinstance(origins, tuple)
            or not origins
            or len(origins) > 2
            or any(
                not isinstance(o, ConversationOriginSystem) or o not in _IMPORT_MARKERS
                for o in origins
            )
            or len(set(origins)) != len(origins)
        ):
            raise EvidenceRequestError("Explicit imported origins required")
        if (
            not isinstance(limits, InspectionLimits)
            or not _positive(limits.max_messages, MAX_MESSAGES)
            or not _positive(limits.max_inspected_messages, MAX_INSPECTED_MESSAGES)
            or not _positive(limits.max_excerpt_bytes, MAX_EXCERPT_BYTES)
            or not _positive(limits.max_response_bytes, MAX_RESPONSE_BYTES)
            or type(offset) is not int
            or not 0 <= offset <= MAX_OFFSET
        ):
            raise EvidenceRequestError("Invalid inspection limits")
        if (
            not isinstance(authority, RecordReadAuthority)
            or authority.principal is not principal
            or not _positive(authority.project_id, 2147483647)
            or authority.project_id != project_id
            or not isinstance(authority.decisions, tuple)
            or len(authority.decisions) != len(thread_ids)
            or any(
                not isinstance(d, ThreadReadDecision)
                or not _positive(d.thread_id, 2147483647)
                or d.record_read_allowed is not True
                or d.source_read_allowed is not True
                or d.diary_read_allowed is not True
                for d in authority.decisions
            )
            or {d.thread_id for d in authority.decisions} != set(thread_ids)
        ):
            raise EvidenceAccessError("Record-read authority unresolved or denied")
        selected = tuple(sorted(thread_ids))
        permitted = tuple(sorted(origins, key=lambda o: o.value))
        try:
            conn = self._connect()
            if (
                not isinstance(conn, psycopg.Connection)
                or conn.info.transaction_status != TransactionStatus.IDLE
                or conn.autocommit
            ):
                raise EvidenceReadError("Fresh transactional connection required")
            with conn:
                with conn.cursor(row_factory=dict_row) as cur:
                    cur.execute(
                        "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"
                    )
                    cur.execute("SET LOCAL statement_timeout = '5s'")
                    return self._read(
                        cur,
                        account,
                        principal,
                        project_id,
                        selected,
                        permitted,
                        limits,
                        offset,
                    )
        except psycopg.Error:
            # Do not disclose SQL diagnostics, DSNs or record content.
            raise EvidenceReadError("Canonical history read failed") from None

    def _read(
        self, cur, account, principal, project_id, selected, permitted, limits, offset
    ):
        cur.execute(
            "SELECT user_id, description FROM projects WHERE id = %s", (project_id,)
        )
        project = cur.fetchone()
        if (
            project is None
            or project["user_id"] != account
            or classify_project_ownership(project).has_authority_conflict
        ):
            raise EvidenceAccessError("Selected history unavailable")
        cur.execute(
            """SELECT id, user_id, project_id, origin_system, metadata
                       FROM chat_threads WHERE id = ANY(%s) ORDER BY id""",
            (list(selected),),
        )
        threads = cur.fetchall()
        if len(threads) != len(selected):
            raise EvidenceAccessError("Selected history unavailable")
        by_id = {}
        for thread in threads:
            if (
                thread["user_id"] != account
                or thread["project_id"] != project_id
                or thread["origin_system"] not in permitted
            ):
                raise EvidenceAccessError("Selected history unavailable")
            try:
                require_thread_read_access(thread["id"], principal, thread=thread)
            except HTTPException:
                raise EvidenceAccessError("Selected history unavailable") from None
            meta = thread["metadata"]
            if meta is None:
                meta = {}
            if not isinstance(meta, dict):
                raise EvidenceMetadataError("Malformed thread metadata")
            thread["metadata"] = meta
            by_id[thread["id"]] = thread
        # Validate message owners across the entire selection BEFORE content is
        # fetched, including outside this page. Single-user mode is no exception.
        cur.execute(
            """SELECT thread_id, count(*) AS total,
                       count(*) FILTER (WHERE user_id IS DISTINCT FROM %s) AS wrong_owner
                       FROM chat_messages WHERE thread_id = ANY(%s) GROUP BY thread_id""",
            (account, list(selected)),
        )
        counts = {r["thread_id"]: r for r in cur.fetchall()}
        if any(r["wrong_owner"] for r in counts.values()):
            raise EvidenceAccessError("Selected history unavailable")
        total = sum(r["total"] for r in counts.values())
        thread_coverage = tuple(
            ThreadCoverage(
                t["id"],
                ConversationOriginSystem(t["origin_system"]),
                counts.get(t["id"], {}).get("total", 0),
                _summary_count(t["metadata"], "messages_kept"),
                _summary_count(t["metadata"], "messages_filtered"),
            )
            for t in threads
        )
        # Bound content at the database boundary; do not transfer full raw_message
        # or arbitrary metadata into the projection. Raw fields are evidence only.
        cur.execute(
            """SELECT id, thread_id, user_id, role,
                       left(content, %s) AS content, octet_length(content) AS content_bytes,
                       event_at, created_at,
                       jsonb_typeof(extra_meta) AS meta_type,
                       jsonb_typeof(extra_meta->'raw_message') AS raw_type,
                       jsonb_build_object(
                         'origin', extra_meta->'origin',
                         'canonical_filter_profile', extra_meta->'canonical_filter_profile',
                         'imported_at', extra_meta->'imported_at',
                         'source_created_at', extra_meta->'source_created_at',
                         'user_id', extra_meta->'user_id',
                         'source_thread_id', extra_meta->'source_thread_id',
                         'source_message_id', extra_meta->'source_message_id',
                         'raw_role', extra_meta->'raw_role',
                         'content_type', extra_meta->'content_type'
                       ) AS meta,
                       jsonb_build_object(
                         'role', extra_meta->'raw_message'->'role',
                         'author_role', extra_meta->'raw_message'->'author'->'role',
                         'sender', extra_meta->'raw_message'->'sender',
                         'speaker', extra_meta->'raw_message'->'speaker',
                         'type', extra_meta->'raw_message'->'type',
                         'content_type', COALESCE(
                            extra_meta->'raw_message'->'content'->'content_type',
                            extra_meta->'raw_message'->'content_type'),
                         'id', extra_meta->'raw_message'->'id',
                         'uuid', extra_meta->'raw_message'->'uuid',
                         'message_id', extra_meta->'raw_message'->'message_id',
                         'create_time', extra_meta->'raw_message'->'create_time',
                         'created_at', extra_meta->'raw_message'->'created_at',
                         'updated_at', extra_meta->'raw_message'->'updated_at',
                         'timestamp', extra_meta->'raw_message'->'timestamp',
                         'createdAt', extra_meta->'raw_message'->'createdAt',
                         'updatedAt', extra_meta->'raw_message'->'updatedAt'
                       ) AS raw FROM chat_messages
                       WHERE thread_id = ANY(%s) ORDER BY thread_id, id LIMIT %s OFFSET %s""",
            (
                limits.max_excerpt_bytes,
                list(selected),
                limits.max_inspected_messages,
                offset,
            ),
        )
        rows = cur.fetchall()
        excerpts = []
        unproven = limited = 0
        for row in rows:
            if row["thread_id"] not in by_id or row["user_id"] != account:
                raise EvidenceAccessError("Selected history unavailable")
            if row["meta_type"] != "object" or row["raw_type"] not in (
                None,
                "null",
                "object",
            ):
                raise EvidenceMetadataError("Malformed message metadata")
            meta = row["meta"]
            thread = by_id[row["thread_id"]]
            origin = ConversationOriginSystem(thread["origin_system"])
            marker, profile = _IMPORT_MARKERS[origin]
            imported_at = _time(meta.get("imported_at"))
            if (
                meta.get("origin") != marker
                or meta.get("canonical_filter_profile") != profile
                or imported_at is None
            ):
                unproven += 1
                continue
            source_thread = _optional_text(meta.get("source_thread_id"))
            stored_thread = _optional_text(thread["metadata"].get("source_thread_id"))
            if meta.get("user_id") not in (None, account) or (
                source_thread and stored_thread and source_thread != stored_thread
            ):
                raise EvidenceMetadataError("Conflicting import provenance")
            source_message = _optional_text(meta.get("source_message_id"))
            raw = row["raw"]
            fields = (
                ("create_time",)
                if origin == ConversationOriginSystem.OPENAI
                else ("created_at", "updated_at", "timestamp", "createdAt", "updatedAt")
            )
            source_time = source_field = None
            for field in fields:
                source_time = _source_time(raw.get(field))
                if source_time is not None:
                    source_field = "raw_message." + field
                    break
            normalized = _time(meta.get("source_created_at"))
            matches = source_time is not None and normalized == source_time
            original_ids = [raw.get(k) for k in ("id", "uuid", "message_id")]
            role_fields = (
                ("author_role", "role")
                if origin == ConversationOriginSystem.OPENAI
                else ("sender", "role", "speaker", "type")
            )
            original_role = next((raw[k] for k in role_fields if raw.get(k)), None)
            text = (
                row["content"]
                .encode("utf-8")[: limits.max_excerpt_bytes]
                .decode("utf-8", "ignore")
            )
            excerpt = ImportedExcerpt(
                project_id,
                row["thread_id"],
                row["id"],
                origin,
                source_thread,
                source_message,
                source_message is not None and source_message in original_ids,
                row["role"],
                _optional_text(original_role),
                _optional_text(raw.get("content_type")),
                _optional_text(meta.get("raw_role")),
                _optional_text(meta.get("content_type")),
                text,
                len(text.encode("utf-8")) < row["content_bytes"],
                source_time,
                source_field,
                normalized,
                matches,
                not matches,
                imported_at,
                row["event_at"].isoformat(),
                row["created_at"].isoformat(),
            )
            if len(excerpts) < limits.max_messages:
                excerpts.append(excerpt)
            else:
                limited += 1
        has_more = offset + len(rows) < total
        pagination_limit = has_more and offset + len(rows) > MAX_OFFSET
        next_offset = offset + len(rows) if has_more and not pagination_limit else None
        coverage = EvidenceCoverage(
            total,
            len(rows),
            len(excerpts),
            unproven,
            limited,
            0,
            sum(e.excerpt_truncated for e in excerpts),
            offset,
            next_offset,
            offset == 0
            and not has_more
            and unproven == 0
            and limited == 0
            and not any(e.excerpt_truncated for e in excerpts),
            pagination_limit,
        )
        response = ImportedHistoryEvidence(
            project_id,
            selected,
            permitted,
            datetime.now(timezone.utc).isoformat(),
            thread_coverage,
            tuple(excerpts),
            coverage,
        )
        while len(response.to_json().encode("utf-8")) > limits.max_response_bytes:
            if not response.excerpts:
                raise EvidenceRequestError(
                    "Response budget cannot hold coverage metadata"
                )
            remaining = response.excerpts[:-1]
            coverage = replace(
                response.coverage,
                returned_records=len(remaining),
                omitted_by_response_budget=response.coverage.omitted_by_response_budget
                + 1,
                truncated_excerpts=sum(e.excerpt_truncated for e in remaining),
                selected_window_complete=False,
            )
            response = replace(response, excerpts=remaining, coverage=coverage)
        return response
