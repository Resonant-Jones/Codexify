"""Request-only archive-read receipt from canonical ordinary thread authority.

ADR-016 permits owner inspection, including modeling-excluded diary records.
There is no independent diary/source read lock in the current ordinary chat
reader. diary_requires_unlock governs identity writes, not this read permission.
No historical metadata or client consent supplies authority here.
"""

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
    MAX_THREADS,
    EvidenceAccessError,
    EvidenceReadError,
    RecordReadAuthority,
    ThreadReadDecision,
)


def resolve_inspection_access(
    connect: Callable[[], psycopg.Connection],
    *,
    principal: RequestUserScope,
    project_id: int,
    thread_ids: tuple[int, ...],
    origins: tuple[ConversationOriginSystem, ...],
) -> RecordReadAuthority:
    """Resolve one receipt; the reader independently rechecks mutable owners.

    There is no separate revocable policy receipt/cache at this baseline. If a
    future read lock is introduced, its atomic handoff must be reviewed before
    this composition can authorize it. Never infer read rights from model flags.
    """
    if (
        not isinstance(principal, RequestUserScope)
        or not principal.user_id.strip()
        or principal.account_id != principal.user_id
        or type(project_id) is not int
        or not 0 < project_id <= 2147483647
        or not isinstance(thread_ids, tuple)
        or not 1 <= len(thread_ids) <= MAX_THREADS
        or any(type(t) is not int or not 0 < t <= 2147483647 for t in thread_ids)
        or len(set(thread_ids)) != len(thread_ids)
        or not origins
        or any(
            o
            not in (ConversationOriginSystem.OPENAI, ConversationOriginSystem.ANTHROPIC)
            for o in origins
        )
    ):
        raise EvidenceAccessError("Inspection authority unresolved")
    try:
        conn = connect()
        if (
            not isinstance(conn, psycopg.Connection)
            or conn.info.transaction_status != TransactionStatus.IDLE
            or conn.autocommit
        ):
            raise EvidenceReadError("Fresh transactional connection required")
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
                    or project["user_id"] != principal.account_id
                    or classify_project_ownership(project).has_authority_conflict
                ):
                    raise EvidenceAccessError("Selected history unavailable")
                cur.execute(
                    """SELECT id, user_id, project_id, origin_system FROM chat_threads
                       WHERE id = ANY(%s) ORDER BY id""",
                    (list(thread_ids),),
                )
                threads = cur.fetchall()
                if len(threads) != len(thread_ids):
                    raise EvidenceAccessError("Selected history unavailable")
                decisions = []
                for thread in threads:
                    if (
                        thread["user_id"] != principal.account_id
                        or thread["project_id"] != project_id
                        or thread["origin_system"] not in origins
                    ):
                        raise EvidenceAccessError("Selected history unavailable")
                    try:
                        access = require_thread_read_access(
                            thread["id"], principal, thread=thread
                        )
                    except HTTPException:
                        raise EvidenceAccessError(
                            "Selected history unavailable"
                        ) from None
                    # Positive basis: an actual ordinary owner-read decision for
                    # this canonical record, plus an explicitly selected imported
                    # origin. The same ordinary read covers its stored source and
                    # diary content; no independent read lock exists at this tip.
                    # None/malformed access cannot become an implicit allow.
                    allowed = (
                        isinstance(access, ThreadReadAccess)
                        and access.thread_id == thread["id"]
                        and access.thread is thread
                    )
                    if not allowed:
                        raise EvidenceAccessError("Inspection authority unresolved")
                    decisions.append(
                        ThreadReadDecision(thread["id"], allowed, allowed, allowed)
                    )
                return RecordReadAuthority(principal, project_id, tuple(decisions))
    except psycopg.Error:
        raise EvidenceReadError("Canonical read authority unavailable") from None
