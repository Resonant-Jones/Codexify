"""Guardian-authorized Saved Widget promotion routes.

The first authorized product surface for Saved Widgets, and the only path by
which a Saved Widget may come into existence.

Authority
---------

The accepted contract describes a chain in which the machine narrows the
options and the human decides
(``docs/architecture/saved-widget-contract.md``). This module is the human
side of that chain:

* **The server narrows.** The artifact is resolved from *stored* message
  content and judged by :mod:`guardian.core.saved_widget_validation`
  (E1-E6). The client names coordinates; it never supplies the artifact, and a
  client-supplied payload is never accepted as evidence that it came from the
  message it names.
* **The human decides.** The request itself is the act. This route is
  reachable only by an authenticated **account session**, which is the
  credential a signed-in person holds. Guardian's *service* credentials are
  deliberately not accepted in its place, and the route is not registered as a
  command-bus command, so the model has no dispatch path to it. There is
  deliberately no approval flag: a caller-supplied boolean is not evidence
  that a human acted.
* **The account owns the result.** Ownership is resolved from the
  authenticated transport and is never client-supplied, client-hinted, or
  derived from a Project or a thread.

What this module does not do
----------------------------

1. It does not decide that an artifact *may* be saved. That judgement belongs
   to the eligibility service, and passing it is a necessary condition rather
   than a grant.
2. It does not grant the saved artifact any new execution capability. Saving
   a widget changes nothing about its containment: it remains untrusted
   executable content in the same opaque-origin sandbox, with the same bridge
   action set, and it is not rendered, invoked, or installed by this path.
3. It does not introduce a second identity or storage authority. Canonical
   identity, revision semantics, provenance capture, and account isolation
   remain owned by :mod:`guardian.core.saved_widget_store` and
   :mod:`guardian.core.saved_widget_validation`.

Repeated promotion
------------------

Each authorized promotion creates a **new** canonical widget identity with its
own first revision. The storage contract defines no natural key for a widget,
so two explicit promotions of the same artifact are two explicit human acts
and produce two independently owned resources. A promotion never replaces,
overwrites, or silently re-points an existing widget or revision.

Contract: docs/architecture/saved-widget-contract.md
ADR: docs/architecture/adr/102-saved-widget-identity-and-revision-boundary.md
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from guardian.core import dependencies
from guardian.core.dependencies import get_account_user_id, require_account_session
from guardian.core.saved_widget_store import (
    SavedWidgetIneligible,
    SavedWidgetStoreError,
    read_saved_widget,
    read_saved_widget_revision,
    read_saved_widget_revisions,
)
from guardian.core.saved_widget_store import (
    # Aliased so this module's own handler name stays ``promote_saved_widget``
    # without shadowing the storage operation it calls.
    promote_saved_widget as persist_saved_widget,
)

logger = logging.getLogger(__name__)

#: The only actor that may promote. The value is recorded in the revision's
#: creation context, so a persisted revision states that its promotion was
#: user-originated.
PROMOTION_ACTOR_USER = "user"

#: Maximum length of a user-supplied display name. Mirrors the store's own
#: bound so an over-long name is rejected at the edge rather than mid-write.
_MAX_NAME_CHARS = 255

router = APIRouter(prefix="/saved-widgets", tags=["Saved Widgets"])


# ---------------------------------------------------------------------------
# Request and response contracts
# ---------------------------------------------------------------------------


class SavedWidgetPromotionRequest(BaseModel):
    """One explicit, user-originated promotion request.

    The request names *coordinates*, never content. The server resolves the
    artifact itself from stored message content, proves its lineage, and
    judges its eligibility. There is deliberately no artifact field, no
    provenance field, and no approval field:

    * an artifact field would let a caller assert what the server stored, and
      a caller-supplied artifact is not evidence of anything;
    * a provenance field would let a caller assert where the artifact came
      from, and the whole point of E5 is that provenance is server-proven;
    * an approval field would let a caller assert that a human acted, and a
      caller-supplied boolean is not evidence of a human decision.

    Unknown fields are rejected so that no such assertion can be smuggled in
    alongside the real request.
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(
        min_length=1,
        max_length=_MAX_NAME_CHARS,
        description="User-supplied display name for the Saved Widget.",
    )
    thread_id: int = Field(
        description="Thread that owns the source assistant message.",
    )
    message_id: int = Field(
        description="Assistant message holding the generated artifact.",
    )
    artifact_index: int = Field(
        default=0,
        ge=0,
        description="Index of the cfy-ui marker within the source message.",
    )


class SavedWidgetProvenanceSnapshot(BaseModel):
    """The server-proven provenance denormalized into the revision record."""

    provenance_classification: str
    source_thread_id: Optional[int] = None
    source_message_id: Optional[int] = None
    completion_attempt_request_id: Optional[str] = None
    accepted_at: Optional[str] = None
    captured_at: Optional[str] = None


class SavedWidgetRevisionRef(BaseModel):
    """A reference to one immutable revision. No executable source."""

    revision: int
    edit_base_revision: Optional[int] = None
    created_at: datetime


class SavedWidgetPromotionResponse(BaseModel):
    """The result of one authorized promotion.

    Carries the canonical widget identity and the reference to the first
    immutable revision. The artifact itself is not returned here; a saved
    widget is not a servable program at promotion time.
    """

    ok: bool = True
    widget_id: str
    name: str
    lifecycle_state: str
    revision: int
    current_revision: int
    created_at: datetime
    provenance: SavedWidgetProvenanceSnapshot


class SavedWidgetReadbackResponse(BaseModel):
    """One Saved Widget, read back under its owning account."""

    ok: bool = True
    widget_id: str
    name: str
    lifecycle_state: str
    current_revision: int
    created_at: datetime
    updated_at: datetime
    source_withheld: bool
    provenance: SavedWidgetProvenanceSnapshot
    revisions: list[SavedWidgetRevisionRef]


class SavedWidgetRevisionReadbackResponse(BaseModel):
    """One immutable revision, read back under its owning account."""

    ok: bool = True
    widget_id: str
    revision: int
    edit_base_revision: Optional[int] = None
    created_at: datetime
    provenance: SavedWidgetProvenanceSnapshot
    artifact_snapshot: Optional[dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_chatlog_db() -> Any:
    """Resolve the application's database handle."""
    db = dependencies.chatlog_db
    if db is None:
        db = dependencies.init_database()
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "saved_widget_storage_unavailable",
                "message": "Saved Widget storage is not configured.",
            },
        )
    return db


def _provenance_payload(
    provenance: Optional[dict[str, Any]],
) -> SavedWidgetProvenanceSnapshot:
    """Project the stored provenance snapshot into its response shape."""
    data = dict(provenance or {})
    return SavedWidgetProvenanceSnapshot(
        provenance_classification=str(data.get("provenance_classification") or ""),
        source_thread_id=(
            int(data["source_thread_id"])
            if data.get("source_thread_id") is not None
            else None
        ),
        source_message_id=(
            int(data["source_message_id"])
            if data.get("source_message_id") is not None
            else None
        ),
        completion_attempt_request_id=(
            str(data["completion_attempt_request_id"])
            if data.get("completion_attempt_request_id") is not None
            else None
        ),
        accepted_at=(
            str(data["accepted_at"]) if data.get("accepted_at") is not None else None
        ),
        captured_at=(
            str(data["captured_at"]) if data.get("captured_at") is not None else None
        ),
    )


def _not_found(widget_id: str) -> HTTPException:
    """One uniform not-found error.

    A wrong-account request is indistinguishable from a missing one, so a
    caller cannot learn whether another account's widget exists.
    """
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"error": "saved_widget_not_found", "widget_id": widget_id},
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_account_session)],
)
def promote_saved_widget(
    body: SavedWidgetPromotionRequest,
    current_user: str = Depends(get_account_user_id),
) -> SavedWidgetPromotionResponse:
    """Promote one eligible generated artifact into a durable Saved Widget.

    The source artifact is resolved server-side from stored message content
    and must pass the existing eligibility service before anything is
    written. The widget row and its first immutable revision are then written
    in one transaction, so a failure leaves neither a widget row nor an
    orphan revision.

    A source that is missing, unaccepted, failed, cancelled, cross-account, or
    otherwise ineligible is rejected without disclosing whether another
    account's artifact exists.
    """
    db = _get_chatlog_db()

    name = body.name.strip()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_request",
                "message": "name is required and must be a non-empty string",
            },
        )

    try:
        record = persist_saved_widget(
            db,
            account_id=current_user,
            thread_id=body.thread_id,
            message_id=body.message_id,
            name=name,
            artifact_index=body.artifact_index,
            actor=PROMOTION_ACTOR_USER,
        )
    except SavedWidgetIneligible as exc:
        # The eligibility service returns one uniform reason for every
        # authorization failure, so these reasons never disclose the
        # existence of another account's artifact.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "artifact_not_eligible",
                "reasons": list(exc.reasons),
            },
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_request", "message": str(exc)},
        ) from exc
    except SavedWidgetStoreError as exc:
        logger.warning(
            "Saved Widget promotion failed account=%s thread=%s message=%s: %s",
            current_user,
            body.thread_id,
            body.message_id,
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "promotion_failed", "message": str(exc)},
        ) from exc

    logger.info(
        "Saved Widget promoted widget_id=%s revision=%s account=%s "
        "source_thread=%s source_message=%s",
        record.widget_id,
        record.current_revision,
        current_user,
        body.thread_id,
        body.message_id,
    )

    return SavedWidgetPromotionResponse(
        widget_id=record.widget_id,
        name=record.name,
        lifecycle_state=record.lifecycle_state,
        revision=record.current_revision,
        current_revision=record.current_revision,
        created_at=record.created_at,
        provenance=_provenance_payload(record.current.provenance_snapshot),
    )


@router.get(
    "/{widget_id}",
    dependencies=[Depends(require_account_session)],
)
def get_saved_widget(
    widget_id: str,
    current_user: str = Depends(get_account_user_id),
) -> SavedWidgetReadbackResponse:
    """Read one Saved Widget under its owning account."""
    db = _get_chatlog_db()
    record = read_saved_widget(db, account_id=current_user, widget_id=widget_id)
    if record is None:
        raise _not_found(widget_id)

    return SavedWidgetReadbackResponse(
        widget_id=record.widget_id,
        name=record.name,
        lifecycle_state=record.lifecycle_state,
        current_revision=record.current_revision,
        created_at=record.created_at,
        updated_at=record.updated_at,
        source_withheld=record.source_withheld,
        provenance=_provenance_payload(record.current.provenance_snapshot),
        revisions=[
            SavedWidgetRevisionRef(
                revision=summary.revision,
                edit_base_revision=summary.edit_base_revision,
                created_at=summary.created_at,
            )
            for summary in record.revisions
        ],
    )


@router.get(
    "/{widget_id}/revisions",
    dependencies=[Depends(require_account_session)],
)
def get_saved_widget_revisions(
    widget_id: str,
    current_user: str = Depends(get_account_user_id),
) -> dict[str, Any]:
    """Read one Saved Widget's revision history metadata under its account."""
    db = _get_chatlog_db()
    summaries = read_saved_widget_revisions(
        db, account_id=current_user, widget_id=widget_id
    )
    if not summaries:
        # A widget always has at least revision 1, so an empty history means
        # no such widget *for this account*.
        raise _not_found(widget_id)

    return {
        "ok": True,
        "widget_id": widget_id,
        "revisions": [
            {
                "revision": summary.revision,
                "edit_base_revision": summary.edit_base_revision,
                "created_at": summary.created_at,
            }
            for summary in summaries
        ],
    }


@router.get(
    "/{widget_id}/revisions/{revision}",
    dependencies=[Depends(require_account_session)],
)
def get_saved_widget_revision(
    widget_id: str,
    revision: int,
    current_user: str = Depends(get_account_user_id),
) -> SavedWidgetRevisionReadbackResponse:
    """Read one immutable revision under its owning account."""
    db = _get_chatlog_db()
    record = read_saved_widget_revision(
        db,
        account_id=current_user,
        widget_id=widget_id,
        revision=revision,
    )
    if record is None:
        raise _not_found(widget_id)

    return SavedWidgetRevisionReadbackResponse(
        widget_id=record.widget_id,
        revision=record.revision,
        edit_base_revision=record.edit_base_revision,
        created_at=record.created_at,
        provenance=_provenance_payload(record.provenance_snapshot),
        artifact_snapshot=record.artifact_snapshot,
    )


__all__ = [
    "PROMOTION_ACTOR_USER",
    "SavedWidgetPromotionRequest",
    "SavedWidgetPromotionResponse",
    "SavedWidgetProvenanceSnapshot",
    "SavedWidgetReadbackResponse",
    "SavedWidgetRevisionReadbackResponse",
    "SavedWidgetRevisionRef",
    "get_saved_widget",
    "get_saved_widget_revision",
    "get_saved_widget_revisions",
    "promote_saved_widget",
    "router",
]
