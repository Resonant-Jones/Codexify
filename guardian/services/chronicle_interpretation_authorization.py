"""Request-local authority preflight for an ephemeral Migration Chronicle.

This module issues no durable or transferable capability. Its immutable grant
exists only while the current request is being evaluated and is never returned
to a caller or attached to inference work.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import psycopg
from fastapi import HTTPException
from psycopg.pq import TransactionStatus
from psycopg.rows import dict_row

from guardian.conversation_origin import ConversationOriginSystem
from guardian.core.dependencies import RequestUserScope
from guardian.core.project_ownership import classify_project_ownership
from guardian.core.thread_access import ThreadReadAccess, require_thread_read_access
from guardian.services.imported_history_evidence import (
    EvidenceAccessError,
    EvidenceMetadataError,
    EvidenceReadError,
    ImportedHistoryEvidenceReader,
    InspectionLimits,
    MAX_EXCERPT_BYTES,
    MAX_INSPECTED_MESSAGES,
    MAX_MESSAGES,
    MAX_OFFSET,
    MAX_RESPONSE_BYTES,
    MAX_THREADS,
)
from guardian.services.imported_history_inspection_access import (
    resolve_inspection_access,
)


class ChronicleAuthorizationError(Exception):
    """Content-free denial or unavailable authorization state."""


class ChronicleAuthorizationUnavailable(ChronicleAuthorizationError):
    """Required canonical authorization evidence could not be read."""


@dataclass(frozen=True)
class ChronicleInterpretationGrant:
    """Internal, immutable request-bound decision; never serialize or reuse."""

    principal: RequestUserScope
    account_id: str
    project_id: int
    thread_ids: tuple[int, ...]
    origins: tuple[ConversationOriginSystem, ...]
    limits: InspectionLimits
    offset: int
    purpose: str
    import_treatment: str
    exclusion_decisions: tuple[tuple[int, str], ...]
    valid_for_current_request_only: bool = True


def authorize_chronicle_interpretation(
    connect: Callable[[], psycopg.Connection],
    *,
    principal: RequestUserScope,
    project_id: int,
    thread_ids: tuple[int, ...],
    origins: tuple[ConversationOriginSystem, ...],
    limits: InspectionLimits,
    offset: int,
    purpose: str,
    interpretation_consent: bool,
    import_treatment: str,
) -> ChronicleInterpretationGrant:
    """Resolve exact scope, exclusions, and imported provenance without inference."""
    account = principal.account_id if isinstance(principal, RequestUserScope) else None
    if (
        account is None
        or not account.strip()
        or account != principal.user_id
        or purpose != "migration_chronicle_preview"
        or interpretation_consent is not True
        or import_treatment != "recallable_archive"
    ):
        raise ChronicleAuthorizationError("Authorization denied")
    if (
        not isinstance(thread_ids, tuple)
        or not thread_ids
        or len(thread_ids) > MAX_THREADS
        or any(
            type(thread_id) is not int or not 0 < thread_id <= 2147483647
            for thread_id in thread_ids
        )
        or len(set(thread_ids)) != len(thread_ids)
        or not origins
        or any(
            not isinstance(origin, ConversationOriginSystem)
            or origin
            not in (ConversationOriginSystem.OPENAI, ConversationOriginSystem.ANTHROPIC)
            for origin in origins
        )
        or len(set(origins)) != len(origins)
        or type(project_id) is not int
        or not 0 < project_id <= 2147483647
        or not isinstance(limits, InspectionLimits)
        or type(limits.max_messages) is not int
        or not 0 < limits.max_messages <= MAX_MESSAGES
        or type(limits.max_inspected_messages) is not int
        or not 0 < limits.max_inspected_messages <= MAX_INSPECTED_MESSAGES
        or type(limits.max_excerpt_bytes) is not int
        or not 0 < limits.max_excerpt_bytes <= MAX_EXCERPT_BYTES
        or type(limits.max_response_bytes) is not int
        or not 0 < limits.max_response_bytes <= MAX_RESPONSE_BYTES
        or type(offset) is not int
        or not 0 <= offset <= MAX_OFFSET
    ):
        raise ChronicleAuthorizationError("Authorization denied")

    exclusion_decisions: list[tuple[int, str]] = []
    try:
        conn = connect()
        if (
            not isinstance(conn, psycopg.Connection)
            or conn.info.transaction_status != TransactionStatus.IDLE
            or conn.autocommit
        ):
            raise ChronicleAuthorizationUnavailable("Authorization unavailable")
        with conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                cur.execute("SET LOCAL statement_timeout = '5s'")
                cur.execute(
                    "SELECT user_id, description FROM projects WHERE id = %s",
                    (project_id,),
                )
                project = cur.fetchone()
                if (
                    project is None
                    or project["user_id"] != account
                    or classify_project_ownership(project).has_authority_conflict
                ):
                    raise ChronicleAuthorizationError("Authorization denied")
                cur.execute(
                    """SELECT id, user_id, project_id, origin_system, is_diary,
                              diary_mode, exclude_from_identity, modeling_excluded
                       FROM chat_threads WHERE id = ANY(%s) ORDER BY id""",
                    (list(thread_ids),),
                )
                threads = cur.fetchall()
                if len(threads) != len(thread_ids):
                    raise ChronicleAuthorizationError("Authorization denied")
                if {thread["origin_system"] for thread in threads} != {
                    origin.value for origin in origins
                }:
                    raise ChronicleAuthorizationError("Authorization denied")
                for thread in threads:
                    if (
                        thread["user_id"] != account
                        or thread["project_id"] != project_id
                        or thread["origin_system"] not in origins
                    ):
                        raise ChronicleAuthorizationError("Authorization denied")
                    try:
                        access = require_thread_read_access(
                            thread["id"], principal, thread=thread
                        )
                    except HTTPException:
                        raise ChronicleAuthorizationError(
                            "Authorization denied"
                        ) from None
                    if (
                        not isinstance(access, ThreadReadAccess)
                        or access.thread_id != thread["id"]
                        or access.thread is not thread
                    ):
                        raise ChronicleAuthorizationError("Authorization denied")
                    if any(
                        thread[field] is not False
                        for field in (
                            "is_diary",
                            "diary_mode",
                            "exclude_from_identity",
                            "modeling_excluded",
                        )
                    ):
                        raise ChronicleAuthorizationError("Authorization denied")
                    exclusion_decisions.extend(
                        (thread["id"], field + "=clear")
                        for field in (
                            "is_diary",
                            "diary_mode",
                            "exclude_from_identity",
                            "modeling_excluded",
                        )
                    )
    except psycopg.Error:
        raise ChronicleAuthorizationUnavailable("Authorization unavailable") from None

    # Reuse the established reader's message-level provenance rules. Its bounded
    # excerpts remain transient in this stack frame and are discarded immediately.
    try:
        read_authority = resolve_inspection_access(
            connect,
            principal=principal,
            project_id=project_id,
            thread_ids=thread_ids,
            origins=origins,
        )
        evidence = ImportedHistoryEvidenceReader(connect).read(
            principal=principal,
            project_id=project_id,
            thread_ids=thread_ids,
            origins=origins,
            authority=read_authority,
            limits=limits,
            offset=offset,
        )
    except (
        EvidenceAccessError,
        EvidenceMetadataError,
        EvidenceReadError,
    ):
        raise ChronicleAuthorizationUnavailable("Authorization unavailable") from None
    if {excerpt.thread_id for excerpt in evidence.excerpts} != set(thread_ids):
        raise ChronicleAuthorizationError("Authorization denied")

    return ChronicleInterpretationGrant(
        principal=principal,
        account_id=account,
        project_id=project_id,
        thread_ids=tuple(thread_ids),
        origins=tuple(origins),
        limits=limits,
        offset=offset,
        purpose=purpose,
        import_treatment=import_treatment,
        exclusion_decisions=tuple(exclusion_decisions),
    )
