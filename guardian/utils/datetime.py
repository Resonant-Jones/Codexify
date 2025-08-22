from __future__ import annotations

from datetime import datetime, timezone


def utc_now() -> datetime:
    """Always return an aware UTC datetime."""
    return datetime.now(timezone.utc)


def parse_ts(s: str) -> datetime:
    """Parse ISO-8601 strings, treating naive timestamps as UTC and normalizing 'Z'."""
    s = s.replace("Z", "+00:00")
    dt = datetime.fromisoformat(s)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def to_iso_z(dt: datetime) -> str:
    """Serialize aware datetimes as ISO with trailing 'Z'."""
    if dt.tzinfo is None:
        raise ValueError("Naive datetime passed to to_iso_z()")
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

