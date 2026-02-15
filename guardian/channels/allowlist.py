"""Channel sender allowlist and pairing code primitives."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe


class PairingCodeError(ValueError):
    """Raised when a pairing code cannot be redeemed."""


@dataclass(slots=True)
class _PairingCode:
    sender_id: str
    channel_id: str
    expires_at: datetime
    used: bool = False


_ALLOWED: set[tuple[str, str]] = set()
_CODES: dict[str, _PairingCode] = {}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def is_allowed(sender_id: str, channel_id: str) -> bool:
    return (sender_id, channel_id) in _ALLOWED


def allow_sender(sender_id: str, channel_id: str) -> None:
    _ALLOWED.add((sender_id, channel_id))


def create_pairing_code(
    sender_id: str, channel_id: str, ttl_seconds: int = 300
) -> str:
    if ttl_seconds <= 0:
        raise ValueError("ttl_seconds must be > 0")
    code = token_urlsafe(18)
    _CODES[code] = _PairingCode(
        sender_id=sender_id,
        channel_id=channel_id,
        expires_at=_utcnow() + timedelta(seconds=ttl_seconds),
    )
    return code


def redeem_pairing_code(code: str) -> tuple[str, str]:
    entry = _CODES.get(code)
    if entry is None:
        raise PairingCodeError("pairing code not found")
    if entry.used:
        raise PairingCodeError("pairing code already used")
    if _utcnow() > entry.expires_at:
        raise PairingCodeError("pairing code expired")
    entry.used = True
    allow_sender(entry.sender_id, entry.channel_id)
    return entry.sender_id, entry.channel_id


def reset_state() -> None:
    """Test helper to clear in-memory allowlist and pairing codes."""

    _ALLOWED.clear()
    _CODES.clear()
