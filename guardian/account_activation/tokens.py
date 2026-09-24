"""Secret-safe token primitives and bounded activation vocabulary."""

from __future__ import annotations

import hashlib
import secrets
from enum import StrEnum

ACCOUNT_ACTIVATION_TOKEN_BYTES = 32
ACCOUNT_ACTIVATION_TOKEN_MIN_LENGTH = 32
ACCOUNT_ACTIVATION_TOKEN_MAX_LENGTH = 512
ACCOUNT_ACTIVATION_ENTITY = "account_activation"


class AccountActivationAuditAction(StrEnum):
    ISSUED = "account_activation_issued"
    REVOKED = "account_activation_revoked"
    REDEEMED = "account_activation_redeemed"


def generate_activation_token() -> str:
    """Return a URL-safe bearer with at least 256 bits of source entropy."""

    return secrets.token_urlsafe(ACCOUNT_ACTIVATION_TOKEN_BYTES)


def normalize_activation_token(raw_token: object) -> str:
    """Validate a bounded bearer without changing its cryptographic value."""

    if not isinstance(raw_token, str):
        raise ValueError("activation token is unavailable")
    token = raw_token.strip()
    if not (
        ACCOUNT_ACTIVATION_TOKEN_MIN_LENGTH
        <= len(token)
        <= ACCOUNT_ACTIVATION_TOKEN_MAX_LENGTH
    ):
        raise ValueError("activation token is unavailable")
    if not token.isascii():
        raise ValueError("activation token is unavailable")
    return token


def digest_activation_token(raw_token: object) -> str:
    """Return the one-way SHA-256 lookup digest for a bounded bearer."""

    token = normalize_activation_token(raw_token)
    return hashlib.sha256(token.encode("ascii")).hexdigest()


__all__ = [
    "ACCOUNT_ACTIVATION_ENTITY",
    "ACCOUNT_ACTIVATION_TOKEN_BYTES",
    "ACCOUNT_ACTIVATION_TOKEN_MAX_LENGTH",
    "ACCOUNT_ACTIVATION_TOKEN_MIN_LENGTH",
    "AccountActivationAuditAction",
    "digest_activation_token",
    "generate_activation_token",
    "normalize_activation_token",
]
