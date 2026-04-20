"""Password hashing helpers for local auth."""

from __future__ import annotations

import bcrypt


def hash_password(password: str) -> str:
    value = str(password or "").encode("utf-8")
    if not value:
        raise ValueError("password is required")
    return bcrypt.hashpw(value, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    raw_password = str(password or "").encode("utf-8")
    raw_hash = str(password_hash or "").encode("utf-8")
    if not raw_password or not raw_hash:
        return False
    try:
        return bool(bcrypt.checkpw(raw_password, raw_hash))
    except Exception:
        return False
