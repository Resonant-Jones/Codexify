"""Canonical Saved Widget identity and immutable revision persistence.

The durable storage authority for Saved Widgets. One widget has one canonical
server-assigned identity and one account owner; its revisions are immutable
snapshots keyed by ``(widget_id, revision)``; and its current-revision pointer
only moves forward.

This module is **internal**. It exposes no HTTP route, no tool command, no
worker dispatch, and no model-accessible entrypoint. Nothing here makes Saved
Widgets available in the product: no save button, no listing, no invocation,
no Library projection, and no rendering path exist. This is the storage
foundation that a later, separately authorized human-promotion operation would
use.

What this module deliberately does not do
------------------------------------------

1. It does not decide that a widget may be saved. An eligible assessment is a
   *necessary* condition, not permission. The future save route must establish
   the explicit human action first; this module cannot verify that a human
   acted, and it deliberately accepts no approval flag, because a
   caller-supplied boolean is not evidence of a human decision.
2. It does not re-implement eligibility. The artifact is resolved and judged
   by the existing Guardian service in
   :mod:`guardian.core.saved_widget_validation`; that service owns E1-E6 and
   the server-proven provenance lookup, and its policy is not duplicated here.
3. It does not expose another account's data. A wrong-account request fails
   closed with the same error as a missing widget, so a caller cannot learn
   whether another account's widget exists.
4. It does not make a deleted or archived widget servable. Deletion withdraws
   the executable source while leaving the identity, ownership, and revision
   numbering addressable for audit and transcript truth.

Authority model
---------------

Ownership is a property of the *widget*, resolved from the account the
caller authenticated as. It is never client-supplied, and a Project or thread
is never an alternative ownership authority: the source thread is provenance,
not storage authority.

Provenance is snapshotted into the revision row at save time rather than held
as a live join, because the referents cascade on thread deletion. Deleting
the source thread does not delete, alter, or un-provenance a Saved Widget.

Contract: docs/architecture/saved-widget-contract.md
Storage authority: docs/architecture/data-and-storage.md
ADR: docs/architecture/adr/102-saved-widget-identity-and-revision-boundary.md
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

from guardian.core.saved_widget_validation import (
    WidgetCandidateStatus,
    assess_saved_widget_candidate,
)
from guardian.db.models import (
    SAVED_WIDGET_LIFECYCLE_ACTIVE,
    SAVED_WIDGET_LIFECYCLE_ARCHIVED,
    SAVED_WIDGET_LIFECYCLE_DELETED,
    SavedWidget,
    SavedWidgetRevision,
)

__all__ = [
    "PROVENANCE_SERVER_PROVEN_ACCEPTED_ATTEMPT",
    "REVISION_ORIGIN_INITIAL_PROMOTION",
    "REVISION_ORIGIN_REVISION_APPEND",
    "SAVED_WIDGET_ID_PREFIX",
    "SAVED_WIDGET_LIFECYCLE_STATES",
    "SavedWidgetConflict",
    "SavedWidgetIneligible",
    "SavedWidgetInvalidState",
    "SavedWidgetNotFound",
    "SavedWidgetRecord",
    "SavedWidgetRevisionRecord",
    "SavedWidgetRevisionSummary",
    "SavedWidgetStoreError",
    "append_saved_widget_revision",
    "promote_saved_widget",
    "read_saved_widget",
    "read_saved_widget_revision",
    "read_saved_widget_revisions",
]


#: Opaque, server-generated widget identity. Never derived from a title, a
#: thread, a project, or any other client-visible value.
SAVED_WIDGET_ID_PREFIX = "sw_"

#: The only provenance classification this module can record. Generated
#: provenance is established by server-owned completion-attempt linkage; a
#: client-supplied role, metadata field, filename, or resource type is never
#: provenance and is never read here.
PROVENANCE_SERVER_PROVEN_ACCEPTED_ATTEMPT = "server_proven_accepted_attempt"

#: Revision-creation context origins.
REVISION_ORIGIN_INITIAL_PROMOTION = "initial_promotion"
REVISION_ORIGIN_REVISION_APPEND = "revision_append"

#: Lifecycle states a widget may hold. Re-exported so callers can reason
#: about a readback record without importing the ORM module directly.
SAVED_WIDGET_LIFECYCLE_STATES = (
    SAVED_WIDGET_LIFECYCLE_ACTIVE,
    SAVED_WIDGET_LIFECYCLE_ARCHIVED,
    SAVED_WIDGET_LIFECYCLE_DELETED,
)

_MAX_NAME_CHARS = 255


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class SavedWidgetStoreError(Exception):
    """Base class for Saved Widget storage failures."""


class SavedWidgetIneligible(SavedWidgetStoreError):
    """The candidate artifact did not pass the eligibility service.

    Carries the service's own reason codes. The store never re-derives them.
    """

    def __init__(
        self,
        reasons: tuple[str, ...],
        status: WidgetCandidateStatus | str = WidgetCandidateStatus.INELIGIBLE,
    ) -> None:
        self.reasons = tuple(reasons)
        self.status = status
        detail = ", ".join(self.reasons) if self.reasons else str(status)
        super().__init__(f"artifact is not eligible for promotion: {detail}")


class SavedWidgetNotFound(SavedWidgetStoreError):
    """No such widget *for this account*.

    A wrong-account request raises this same error rather than a distinct
    "forbidden" one, because distinguishing "missing" from "belongs to
    another account" would leak the existence of another account's data.
    """


class SavedWidgetInvalidState(SavedWidgetStoreError):
    """The widget is not in a state that permits this operation.

    Archived and deleted widgets are not active widgets. Archived revision
    serving is deferred until the invocation authorization path exists, and a
    deleted widget never has its executable source returned.
    """


class SavedWidgetConflict(SavedWidgetStoreError):
    """The edit base is no longer the widget's current revision.

    The store does not retry against a newer base. The candidate is carried on
    the exception so the caller can deliberately re-base or discard it.
    """

    def __init__(
        self,
        *,
        widget_id: str,
        base_revision: int,
        current_revision: int,
        candidate_artifact: Mapping[str, Any] | None = None,
    ) -> None:
        self.widget_id = widget_id
        self.base_revision = int(base_revision)
        self.current_revision = int(current_revision)
        self.candidate_artifact = (
            dict(candidate_artifact) if candidate_artifact is not None else None
        )
        super().__init__(
            f"edit base {self.base_revision} is stale for widget {widget_id}; "
            f"current revision is {self.current_revision}"
        )


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SavedWidgetRevisionRecord:
    """One immutable revision snapshot, as read back."""

    widget_id: str
    revision: int
    artifact_snapshot: dict[str, Any] | None
    provenance_snapshot: dict[str, Any]
    creation_context: dict[str, Any]
    edit_base_revision: int | None
    created_at: datetime


@dataclass(frozen=True)
class SavedWidgetRevisionSummary:
    """Revision metadata without the executable snapshot."""

    revision: int
    edit_base_revision: int | None
    created_at: datetime


@dataclass(frozen=True)
class SavedWidgetRecord:
    """One canonical widget, as read back.

    ``source_withheld`` is true when the widget is not an active widget. The
    artifact snapshot is then absent, and a caller must not treat this record
    as a servable program.
    """

    widget_id: str
    owner_user_id: str
    name: str
    lifecycle_state: str
    current_revision: int
    created_at: datetime
    updated_at: datetime
    current: SavedWidgetRevisionRecord
    revisions: tuple[SavedWidgetRevisionSummary, ...]
    source_withheld: bool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: Any) -> str | None:
    """Render a timestamp as an ISO-8601 string, or None when absent."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _new_widget_id() -> str:
    """Allocate an opaque, server-generated widget identity."""
    return f"{SAVED_WIDGET_ID_PREFIX}{uuid.uuid4().hex}"


def _require_account_id(account_id: Any) -> str:
    if not isinstance(account_id, str) or not account_id.strip():
        raise ValueError("account_id is required and must be a non-empty string")
    return account_id


def _require_name(name: Any) -> str:
    if not isinstance(name, str) or not name.strip():
        raise ValueError("name is required and must be a non-empty string")
    if len(name) > _MAX_NAME_CHARS:
        raise ValueError(f"name must be at most {_MAX_NAME_CHARS} characters")
    return name


@dataclass(frozen=True)
class _Candidate:
    """A resolved, eligible candidate, ready to be persisted."""

    artifact: dict[str, Any]
    provenance: dict[str, Any]
    creation_context: dict[str, Any]


def _resolve_candidate(
    chatlog_db: Any,
    *,
    account_id: str,
    thread_id: int,
    message_id: int,
    artifact_index: int,
    origin: str,
    actor: str,
) -> _Candidate:
    """Resolve one server-stored artifact through the eligibility service.

    The artifact is resolved from stored message content by
    :func:`guardian.core.saved_widget_validation.assess_saved_widget_candidate`.
    No caller-supplied payload is accepted here, and the eligibility service's
    own policy is neither duplicated nor weakened.
    """
    assessment = assess_saved_widget_candidate(
        chatlog_db,
        account_id=account_id,
        thread_id=thread_id,
        message_id=message_id,
        artifact_index=artifact_index,
    )

    if not assessment.is_eligible:
        raise SavedWidgetIneligible(assessment.reasons, assessment.status)

    artifact = assessment.artifact
    lineage = assessment.lineage
    if artifact is None or lineage is None:
        # ELIGIBLE implies a proven lineage, so this is a guard rather than a
        # reachable path.
        raise SavedWidgetIneligible(assessment.reasons, assessment.status)

    captured_at = _iso(_now())
    provenance: dict[str, Any] = {
        "source_thread_id": int(lineage.thread_id),
        "source_message_id": int(lineage.message_id),
        "completion_attempt_request_id": str(lineage.request_id),
        "provenance_classification": PROVENANCE_SERVER_PROVEN_ACCEPTED_ATTEMPT,
        "captured_at": captured_at,
    }
    accepted_at = _iso(lineage.accepted_at)
    if accepted_at is not None:
        provenance["accepted_at"] = accepted_at

    creation_context: dict[str, Any] = {
        "origin": origin,
        "actor": actor,
        "artifact_index": assessment.artifact_index,
        "captured_at": captured_at,
    }

    return _Candidate(
        artifact=dict(artifact),
        provenance=provenance,
        creation_context=creation_context,
    )


def _record_from_rows(
    widget: SavedWidget,
    current: SavedWidgetRevision | None,
    revisions: tuple[SavedWidgetRevision, ...],
) -> SavedWidgetRecord:
    """Project ORM rows into the readback record.

    The artifact snapshot is withheld for any widget that is not an active
    widget, so a deleted or archived widget can never be served as a program
    through this path.
    """
    source_withheld = widget.lifecycle_state != SAVED_WIDGET_LIFECYCLE_ACTIVE

    if current is None:
        # A widget whose current revision is missing cannot happen: the
        # pointer is protected by a deferrable composite foreign key. Treat it
        # as an absent source rather than inventing one.
        current_record = SavedWidgetRevisionRecord(
            widget_id=widget.widget_id,
            revision=int(widget.current_revision),
            artifact_snapshot=None,
            provenance_snapshot={},
            creation_context={},
            edit_base_revision=None,
            created_at=widget.created_at,
        )
    else:
        current_record = SavedWidgetRevisionRecord(
            widget_id=current.widget_id,
            revision=int(current.revision),
            artifact_snapshot=None if source_withheld else dict(current.artifact_snapshot),
            provenance_snapshot=dict(current.provenance_snapshot),
            creation_context=dict(current.creation_context),
            edit_base_revision=current.edit_base_revision,
            created_at=current.created_at,
        )

    return SavedWidgetRecord(
        widget_id=widget.widget_id,
        owner_user_id=widget.owner_user_id,
        name=widget.name,
        lifecycle_state=widget.lifecycle_state,
        current_revision=int(widget.current_revision),
        created_at=widget.created_at,
        updated_at=widget.updated_at,
        current=current_record,
        revisions=tuple(
            SavedWidgetRevisionSummary(
                revision=int(row.revision),
                edit_base_revision=row.edit_base_revision,
                created_at=row.created_at,
            )
            for row in revisions
        ),
        source_withheld=source_withheld,
    )


# ---------------------------------------------------------------------------
# Operations
# ---------------------------------------------------------------------------


def promote_saved_widget(
    chatlog_db: Any,
    *,
    account_id: str,
    thread_id: int,
    message_id: int,
    name: str,
    artifact_index: int = 0,
    actor: str = "guardian",
) -> SavedWidgetRecord:
    """Create a canonical Saved Widget with its first immutable revision.

    The candidate artifact is resolved from server-stored message content and
    must pass the existing Guardian eligibility service (E1-E6) before
    anything is written. The widget row and revision 1 are then written in a
    single transaction, so a failure leaves neither a widget row nor an
    orphan revision.

    This is a storage operation, not a save *decision*. The caller is
    responsible for having established explicit human promotion first; this
    function has no way to verify that and deliberately accepts no approval
    flag.
    """
    account_id = _require_account_id(account_id)
    name = _require_name(name)

    candidate = _resolve_candidate(
        chatlog_db,
        account_id=account_id,
        thread_id=thread_id,
        message_id=message_id,
        artifact_index=artifact_index,
        origin=REVISION_ORIGIN_INITIAL_PROMOTION,
        actor=actor,
    )

    widget_id = _new_widget_id()
    now = _now()

    with chatlog_db._sa_session() as session:
        widget = SavedWidget(
            widget_id=widget_id,
            owner_user_id=account_id,
            name=name,
            lifecycle_state=SAVED_WIDGET_LIFECYCLE_ACTIVE,
            current_revision=1,
            created_at=now,
            updated_at=now,
        )
        session.add(widget)
        # The widget row is written first. The current-revision pointer names
        # revision 1, which does not exist yet; the constraint is deferrable,
        # so it is checked at commit time, when revision 1 is present.
        session.flush()

        revision = SavedWidgetRevision(
            widget_id=widget_id,
            revision=1,
            artifact_snapshot=candidate.artifact,
            provenance_snapshot=candidate.provenance,
            creation_context=candidate.creation_context,
            edit_base_revision=None,
            created_at=now,
        )
        session.add(revision)
        session.flush()

    return SavedWidgetRecord(
        widget_id=widget_id,
        owner_user_id=account_id,
        name=name,
        lifecycle_state=SAVED_WIDGET_LIFECYCLE_ACTIVE,
        current_revision=1,
        created_at=now,
        updated_at=now,
        current=SavedWidgetRevisionRecord(
            widget_id=widget_id,
            revision=1,
            artifact_snapshot=candidate.artifact,
            provenance_snapshot=candidate.provenance,
            creation_context=candidate.creation_context,
            edit_base_revision=None,
            created_at=now,
        ),
        revisions=(
            SavedWidgetRevisionSummary(
                revision=1, edit_base_revision=None, created_at=now
            ),
        ),
        source_withheld=False,
    )


def append_saved_widget_revision(
    chatlog_db: Any,
    *,
    account_id: str,
    widget_id: str,
    base_revision: int,
    thread_id: int,
    message_id: int,
    artifact_index: int = 0,
    actor: str = "guardian",
) -> SavedWidgetRevisionRecord:
    """Append one immutable revision to an existing widget.

    The widget row is locked for the duration of the transaction, so two
    concurrent appends that share an edit base cannot both succeed: one wins
    and the other is rejected as an explicit conflict. The store never retries
    a conflict against a newer base.

    The new revision is inserted and the current-revision pointer is advanced
    in the same transaction. An existing revision is never overwritten.

    Two checks can refuse the write, in this order. The candidate is resolved
    first, so a caller who presents a source they do not own is refused by
    the eligibility service without the store ever touching the widget. The
    widget's ownership is checked second, under the row lock. Both refusals
    fail closed, and neither reveals whether a widget exists.
    """
    account_id = _require_account_id(account_id)
    if not isinstance(widget_id, str) or not widget_id.strip():
        raise ValueError("widget_id is required and must be a non-empty string")
    if isinstance(base_revision, bool) or not isinstance(base_revision, int):
        raise ValueError("base_revision is required and must be an integer")
    if base_revision < 1:
        raise ValueError("base_revision must be a positive revision number")

    candidate = _resolve_candidate(
        chatlog_db,
        account_id=account_id,
        thread_id=thread_id,
        message_id=message_id,
        artifact_index=artifact_index,
        origin=REVISION_ORIGIN_REVISION_APPEND,
        actor=actor,
    )

    with chatlog_db._sa_session() as session:
        widget = (
            session.query(SavedWidget)
            .filter_by(widget_id=widget_id)
            .with_for_update()
            .one_or_none()
        )
        if widget is None or widget.owner_user_id != account_id:
            # One uniform failure for "missing" and "belongs to another
            # account", so a caller cannot probe for another account's
            # widget.
            raise SavedWidgetNotFound(
                f"no saved widget {widget_id} for this account"
            )
        if widget.lifecycle_state != SAVED_WIDGET_LIFECYCLE_ACTIVE:
            raise SavedWidgetInvalidState(
                f"saved widget {widget_id} is {widget.lifecycle_state}, not active"
            )
        if int(widget.current_revision) != int(base_revision):
            raise SavedWidgetConflict(
                widget_id=widget_id,
                base_revision=base_revision,
                current_revision=int(widget.current_revision),
                candidate_artifact=candidate.artifact,
            )

        next_revision = int(widget.current_revision) + 1
        now = _now()
        revision = SavedWidgetRevision(
            widget_id=widget_id,
            revision=next_revision,
            artifact_snapshot=candidate.artifact,
            provenance_snapshot=candidate.provenance,
            creation_context=candidate.creation_context,
            edit_base_revision=int(base_revision),
            created_at=now,
        )
        session.add(revision)
        widget.current_revision = next_revision
        widget.updated_at = now
        session.flush()

    return SavedWidgetRevisionRecord(
        widget_id=widget_id,
        revision=next_revision,
        artifact_snapshot=candidate.artifact,
        provenance_snapshot=candidate.provenance,
        creation_context=candidate.creation_context,
        edit_base_revision=int(base_revision),
        created_at=now,
    )


def read_saved_widget(
    chatlog_db: Any,
    *,
    account_id: str,
    widget_id: str,
) -> SavedWidgetRecord | None:
    """Read one widget, scoped to the authenticated account.

    Returns None when the widget does not exist *for this account*; a
    wrong-account request is indistinguishable from a missing one.

    The executable source is withheld for any widget that is not active, so a
    deleted or archived widget is never returned as a servable program.
    """
    account_id = _require_account_id(account_id)

    with chatlog_db._sa_session() as session:
        widget = (
            session.query(SavedWidget).filter_by(widget_id=widget_id).one_or_none()
        )
        if widget is None or widget.owner_user_id != account_id:
            return None

        revisions = (
            session.query(SavedWidgetRevision)
            .filter_by(widget_id=widget_id)
            .order_by(SavedWidgetRevision.revision.asc())
            .all()
        )
        current = next(
            (row for row in revisions if int(row.revision) == int(widget.current_revision)),
            None,
        )
        return _record_from_rows(widget, current, tuple(revisions))


def read_saved_widget_revisions(
    chatlog_db: Any,
    *,
    account_id: str,
    widget_id: str,
) -> tuple[SavedWidgetRevisionSummary, ...]:
    """Read the revision history metadata, scoped to the account.

    Metadata only: no executable source is returned here.
    """
    account_id = _require_account_id(account_id)

    with chatlog_db._sa_session() as session:
        widget = (
            session.query(SavedWidget).filter_by(widget_id=widget_id).one_or_none()
        )
        if widget is None or widget.owner_user_id != account_id:
            return ()
        rows = (
            session.query(SavedWidgetRevision)
            .filter_by(widget_id=widget_id)
            .order_by(SavedWidgetRevision.revision.asc())
            .all()
        )
        return tuple(
            SavedWidgetRevisionSummary(
                revision=int(row.revision),
                edit_base_revision=row.edit_base_revision,
                created_at=row.created_at,
            )
            for row in rows
        )


def read_saved_widget_revision(
    chatlog_db: Any,
    *,
    account_id: str,
    widget_id: str,
    revision: int,
) -> SavedWidgetRevisionRecord | None:
    """Read one specific immutable revision, scoped to the account.

    Historical revision serving is deferred until the invocation authorization
    path exists, so the executable source is withheld for any widget that is
    not active. The snapshot itself is always returned for audit purposes.
    """
    account_id = _require_account_id(account_id)

    with chatlog_db._sa_session() as session:
        widget = (
            session.query(SavedWidget).filter_by(widget_id=widget_id).one_or_none()
        )
        if widget is None or widget.owner_user_id != account_id:
            return None
        row = (
            session.query(SavedWidgetRevision)
            .filter_by(widget_id=widget_id, revision=revision)
            .one_or_none()
        )
        if row is None:
            return None

        source_withheld = widget.lifecycle_state != SAVED_WIDGET_LIFECYCLE_ACTIVE
        return SavedWidgetRevisionRecord(
            widget_id=row.widget_id,
            revision=int(row.revision),
            artifact_snapshot=None if source_withheld else dict(row.artifact_snapshot),
            provenance_snapshot=dict(row.provenance_snapshot),
            creation_context=dict(row.creation_context),
            edit_base_revision=row.edit_base_revision,
            created_at=row.created_at,
        )
