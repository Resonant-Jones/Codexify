"""Helpers for encrypting OAuth tokens at rest."""

from __future__ import annotations

import base64
import hashlib
import os

from cryptography.fernet import Fernet, InvalidToken

_KEY_ENV_NAMES = (
    "GUARDIAN_OAUTH_TOKEN_ENCRYPTION_KEY",
    "OAUTH_TOKEN_ENCRYPTION_KEY",
)
_FALLBACK_SECRET_ENV_NAMES = (
    "GUARDIAN_SESSION_SECRET",
    "GUARDIAN_JWT_SECRET",
    "GUARDIAN_API_KEY",
)


def _derive_fernet_key(secret: str) -> bytes:
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def _load_fernet() -> Fernet:
    for env_name in _KEY_ENV_NAMES:
        value = (os.getenv(env_name) or "").strip()
        if not value:
            continue
        try:
            return Fernet(value.encode("utf-8"))
        except Exception as exc:  # pragma: no cover - invalid config guard
            raise RuntimeError(
                f"{env_name} is set but not a valid Fernet key."
            ) from exc

    for env_name in _FALLBACK_SECRET_ENV_NAMES:
        value = (os.getenv(env_name) or "").strip()
        if value:
            return Fernet(_derive_fernet_key(value))

    raise RuntimeError(
        "Missing OAuth token encryption key. Set "
        "GUARDIAN_OAUTH_TOKEN_ENCRYPTION_KEY (preferred) or one of "
        "GUARDIAN_SESSION_SECRET/GUARDIAN_JWT_SECRET/GUARDIAN_API_KEY."
    )


def encrypt_token(value: str | None) -> str | None:
    if not value:
        return None
    fernet = _load_fernet()
    return fernet.encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_token(value: str | None) -> str | None:
    if not value:
        return None
    fernet = _load_fernet()
    try:
        return fernet.decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise RuntimeError(
            "Stored OAuth token could not be decrypted."
        ) from exc
