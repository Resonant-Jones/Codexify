"""Outbox safety helpers for event streaming and cleanup."""

from __future__ import annotations

import math
from typing import Any

DEFAULT_OUTBOX_TENANT_ID = "default"
DEFAULT_OUTBOX_POLL_INTERVAL = 1.0
MIN_OUTBOX_POLL_INTERVAL = 0.1
MAX_OUTBOX_POLL_INTERVAL = 30.0
DEFAULT_OUTBOX_BATCH_SIZE = 100
MIN_OUTBOX_BATCH_SIZE = 1
MAX_OUTBOX_BATCH_SIZE = 1000


def normalize_outbox_tenant_id(
    tenant_id: str | None,
    *,
    default: str = DEFAULT_OUTBOX_TENANT_ID,
) -> str:
    """Return a non-empty outbox tenant id with a safe default."""
    normalized_default = (default or DEFAULT_OUTBOX_TENANT_ID).strip()
    if not normalized_default:
        normalized_default = DEFAULT_OUTBOX_TENANT_ID
    candidate = (tenant_id or "").strip()
    return candidate or normalized_default


def parse_outbox_poll_interval(
    raw: Any,
    *,
    default: float = DEFAULT_OUTBOX_POLL_INTERVAL,
) -> float:
    """Parse and clamp outbox poll interval for predictable SSE behavior."""
    try:
        value = float(raw)
    except (TypeError, ValueError):
        value = default

    if not math.isfinite(value):
        value = default

    if value < MIN_OUTBOX_POLL_INTERVAL:
        return MIN_OUTBOX_POLL_INTERVAL
    if value > MAX_OUTBOX_POLL_INTERVAL:
        return MAX_OUTBOX_POLL_INTERVAL
    return value


def parse_outbox_batch_size(
    raw: Any,
    *,
    default: int = DEFAULT_OUTBOX_BATCH_SIZE,
) -> int:
    """Parse and clamp outbox batch size for bounded memory/network pressure."""
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = default

    if value < MIN_OUTBOX_BATCH_SIZE:
        return MIN_OUTBOX_BATCH_SIZE
    if value > MAX_OUTBOX_BATCH_SIZE:
        return MAX_OUTBOX_BATCH_SIZE
    return value


def parse_last_event_id(
    header_value: str | None,
    query_value: int | str | None,
) -> int:
    """Resolve last processed SSE id with safe fallback to zero."""
    candidate = header_value if header_value is not None else query_value
    try:
        parsed = int(candidate or 0)
    except (TypeError, ValueError):
        return 0
    return max(parsed, 0)


__all__ = [
    "DEFAULT_OUTBOX_BATCH_SIZE",
    "DEFAULT_OUTBOX_POLL_INTERVAL",
    "DEFAULT_OUTBOX_TENANT_ID",
    "MAX_OUTBOX_BATCH_SIZE",
    "MAX_OUTBOX_POLL_INTERVAL",
    "MIN_OUTBOX_BATCH_SIZE",
    "MIN_OUTBOX_POLL_INTERVAL",
    "normalize_outbox_tenant_id",
    "parse_last_event_id",
    "parse_outbox_batch_size",
    "parse_outbox_poll_interval",
]
