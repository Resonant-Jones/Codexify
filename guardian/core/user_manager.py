"""User bootstrap helpers."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from guardian.core.db import GuardianDB, load_guardian_db_from_env
from guardian.core.passwords import hash_password
from guardian.db.models import User

logger = logging.getLogger(__name__)


DEFAULT_BOOTSTRAP_PASSWORD = "local"


def _resolve_default_user_id() -> str:
    return "local"


def get_or_create_default_user(
    db: GuardianDB | None = None,
) -> dict[str, Any]:
    """Ensure the canonical seed user exists and return its record."""

    user_id = _resolve_default_user_id()
    guardian_db = db or load_guardian_db_from_env()
    if guardian_db is None:
        logger.warning(
            "[users] GuardianDB unavailable; returning seed identity %s without persistence",
            user_id,
        )
        return {
            "id": user_id,
            "username": user_id,
            "password_hash": hash_password(DEFAULT_BOOTSTRAP_PASSWORD),
            "created_at": None,
        }

    with guardian_db.get_session() as session:
        user = session.get(User, user_id)
        if user is None:
            user = User(
                id=user_id,
                username=user_id,
                password_hash=hash_password(DEFAULT_BOOTSTRAP_PASSWORD),
                created_at=datetime.now(timezone.utc),
            )
            session.add(user)
            session.commit()
            session.refresh(user)
        return {
            "id": user.id,
            "username": user.username,
            "password_hash": user.password_hash,
            "created_at": user.created_at,
        }


class UserManager:
    """Tiny compatibility wrapper around the bootstrap helper."""

    def get_or_create_default_user(
        self, db: GuardianDB | None = None
    ) -> dict[str, Any]:
        return get_or_create_default_user(db)
