"""Browser approval workflow and audit logging primitives."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    and_,
    func,
    insert,
    select,
    update,
)

metadata = MetaData()

browser_approvals = Table(
    "browser_approvals",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("operation", String(64), nullable=False),
    Column("target", String(512), nullable=True),
    Column("status", String(16), nullable=False),
    Column("requested_by", String(255), nullable=True),
    Column("request_reason", Text, nullable=True),
    Column("decided_by", String(255), nullable=True),
    Column("decision_reason", Text, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("decided_at", DateTime(timezone=True), nullable=True),
)

browser_audit_log = Table(
    "browser_audit_log",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column(
        "approval_id",
        Integer,
        ForeignKey("browser_approvals.id", ondelete="SET NULL"),
        nullable=True,
    ),
    Column("operation", String(64), nullable=False),
    Column("target", String(512), nullable=True),
    Column("status", String(32), nullable=False),
    Column("actor", String(255), nullable=True),
    Column("detail", Text, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

_db: Any | None = None
_DANGEROUS_OPS = {"evaluate", "cookie.get", "cookie.set"}


class ApprovalError(RuntimeError):
    """Base approval workflow error."""


class ApprovalNotFoundError(ApprovalError):
    """Requested approval id does not exist."""


class ApprovalTransitionError(ApprovalError):
    """State transition is not allowed."""


class ApprovalRequiredError(ApprovalError):
    """Dangerous operation requires approval."""

    def __init__(self, approval_id: int) -> None:
        super().__init__(f"approval required: {approval_id}")
        self.approval_id = approval_id


def configure_db(db: Any) -> None:
    """Configure db provider (GuardianDB or test double)."""

    global _db
    _db = db


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@contextmanager
def _session_scope() -> Iterator[Any]:
    if _db is None:
        raise RuntimeError("Browser approval DB not configured")

    if hasattr(_db, "get_session"):
        with _db.get_session() as session:
            yield session
        return

    session_factory = getattr(_db, "SessionLocal", None)
    if not callable(session_factory):
        raise RuntimeError("Configured DB has no get_session/SessionLocal")
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def ensure_tables(bind: Any) -> None:
    """Create approval/audit tables when absent (test/dev helper)."""

    metadata.create_all(
        bind=bind, tables=[browser_approvals, browser_audit_log]
    )


def _to_iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _serialize_approval(row: Any) -> dict[str, Any]:
    return {
        "id": int(row.id),
        "operation": row.operation,
        "target": row.target,
        "status": row.status,
        "requested_by": row.requested_by,
        "request_reason": row.request_reason,
        "decided_by": row.decided_by,
        "decision_reason": row.decision_reason,
        "created_at": _to_iso(row.created_at),
        "decided_at": _to_iso(row.decided_at),
    }


def _write_audit(
    *,
    session: Any,
    approval_id: int | None,
    operation: str,
    target: str | None,
    status: str,
    actor: str | None,
    detail: str | None,
) -> None:
    session.execute(
        insert(browser_audit_log).values(
            approval_id=approval_id,
            operation=operation,
            target=target,
            status=status,
            actor=actor,
            detail=detail,
            created_at=_utc_now(),
        )
    )


def create_approval_request(
    *,
    operation: str,
    target: str | None,
    actor: str | None,
    request_reason: str | None,
) -> dict[str, Any]:
    """Create a pending approval request and write a blocked audit record."""

    with _session_scope() as session:
        result = session.execute(
            insert(browser_approvals).values(
                operation=operation,
                target=target,
                status="PENDING",
                requested_by=actor,
                request_reason=request_reason,
                created_at=_utc_now(),
            )
        )
        approval_id = int(result.inserted_primary_key[0])
        row = session.execute(
            select(browser_approvals).where(
                browser_approvals.c.id == approval_id
            )
        ).first()
        if row is None:
            raise RuntimeError("failed to load created approval")
        _write_audit(
            session=session,
            approval_id=approval_id,
            operation=operation,
            target=target,
            status="blocked",
            actor=actor,
            detail="approval_required",
        )
        return _serialize_approval(row)


def list_approvals(
    *, status: str | None = None, limit: int = 100
) -> list[dict[str, Any]]:
    with _session_scope() as session:
        stmt = (
            select(browser_approvals)
            .order_by(browser_approvals.c.id.desc())
            .limit(limit)
        )
        if status:
            stmt = stmt.where(browser_approvals.c.status == status.upper())
        rows = session.execute(stmt).all()
        return [_serialize_approval(row) for row in rows]


def decide_approval(
    *,
    approval_id: int,
    decision: str,
    actor: str | None,
    decision_reason: str,
) -> dict[str, Any]:
    """Apply one pending-only decision (APPROVED or DENIED)."""

    normalized = decision.strip().upper()
    if normalized not in {"APPROVED", "DENIED"}:
        raise ApprovalTransitionError("decision must be APPROVED or DENIED")

    with _session_scope() as session:
        current = session.execute(
            select(browser_approvals).where(
                browser_approvals.c.id == approval_id
            )
        ).first()
        if current is None:
            raise ApprovalNotFoundError(f"approval not found: {approval_id}")
        if current.status != "PENDING":
            raise ApprovalTransitionError(
                f"approval {approval_id} already resolved: {current.status}"
            )

        session.execute(
            update(browser_approvals)
            .where(
                and_(
                    browser_approvals.c.id == approval_id,
                    browser_approvals.c.status == "PENDING",
                )
            )
            .values(
                status=normalized,
                decided_by=actor,
                decision_reason=decision_reason,
                decided_at=_utc_now(),
            )
        )
        updated = session.execute(
            select(browser_approvals).where(
                browser_approvals.c.id == approval_id
            )
        ).first()

        if updated is None or updated.status != normalized:
            raise ApprovalTransitionError(
                f"approval {approval_id} transition failed"
            )

        _write_audit(
            session=session,
            approval_id=approval_id,
            operation=updated.operation,
            target=updated.target,
            status=f"decision_{normalized.lower()}",
            actor=actor,
            detail=decision_reason,
        )
        return _serialize_approval(updated)


def is_approved(*, approval_id: int, operation: str | None = None) -> bool:
    with _session_scope() as session:
        stmt = (
            select(func.count())
            .select_from(browser_approvals)
            .where(
                and_(
                    browser_approvals.c.id == approval_id,
                    browser_approvals.c.status == "APPROVED",
                )
            )
        )
        if operation:
            stmt = stmt.where(browser_approvals.c.operation == operation)
        count = session.execute(stmt).scalar_one()
        return int(count) > 0


def require_approval_for_operation(
    *,
    operation: str,
    target: str | None,
    actor: str | None,
    reason: str | None = None,
    approval_id: int | None = None,
) -> None:
    """Enforce approval for dangerous operations and always audit attempts."""

    op = operation.strip().lower()
    with _session_scope() as session:
        if op not in _DANGEROUS_OPS:
            _write_audit(
                session=session,
                approval_id=approval_id,
                operation=op,
                target=target,
                status="allowed",
                actor=actor,
                detail="non_dangerous_operation",
            )
            return

        if approval_id is not None and is_approved(
            approval_id=approval_id, operation=op
        ):
            _write_audit(
                session=session,
                approval_id=approval_id,
                operation=op,
                target=target,
                status="allowed",
                actor=actor,
                detail="approved",
            )
            return

    request = create_approval_request(
        operation=op,
        target=target,
        actor=actor,
        request_reason=reason or "dangerous_browser_operation",
    )
    raise ApprovalRequiredError(int(request["id"]))


__all__ = [
    "ApprovalError",
    "ApprovalNotFoundError",
    "ApprovalRequiredError",
    "ApprovalTransitionError",
    "browser_approvals",
    "browser_audit_log",
    "configure_db",
    "create_approval_request",
    "decide_approval",
    "ensure_tables",
    "is_approved",
    "list_approvals",
    "require_approval_for_operation",
]
