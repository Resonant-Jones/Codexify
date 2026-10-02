"""Bounded account UX state; no identity-policy or messaging writes."""

from fastapi import HTTPException
from sqlalchemy.dialects.postgresql import insert
from guardian.db.models import User, UserOnboardingState

DEFAULT_STATE = dict(
    onboarding_version=1,
    status="not_started",
    last_step_key=None,
    desktop_tour_completed=False,
    mobile_tour_completed=False,
    contextual_tips_enabled=True,
)
STEP_KEYS = ("welcome", "identity", "username", "navigation", "core_surfaces", "help")


def require_owner(session, user_id):
    if not user_id or user_id == "default":
        raise HTTPException(403, "Authenticated account required")
    if session.get(User, user_id) is None:
        raise HTTPException(404, "Account not found")
    return user_id


def read_state(session, user_id):
    owner = require_owner(session, user_id)
    row = session.get(UserOnboardingState, owner)
    return (
        dict(DEFAULT_STATE)
        if row is None
        else {key: getattr(row, key) for key in DEFAULT_STATE}
    )


def patch_state(session, user_id, changes):
    owner = require_owner(session, user_id)
    # PostgreSQL upsert changes only supplied fields, including during concurrent
    # first writes. A partial PATCH never overwrites another field from stale GET.
    values = {**DEFAULT_STATE, **changes, "user_id": owner}
    statement = insert(UserOnboardingState).values(**values)
    from sqlalchemy import func

    session.execute(
        statement.on_conflict_do_update(
            index_elements=[UserOnboardingState.user_id],
            set_={**changes, "updated_at": func.now()},
        )
    )
    session.commit()
    session.expire_all()
    return read_state(session, owner)
