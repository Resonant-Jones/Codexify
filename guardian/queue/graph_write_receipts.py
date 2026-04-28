"""Ephemeral receipt helpers for inspection-only graph-write tasks."""

from __future__ import annotations

from typing import Any

from guardian.queue.redis_queue import set_if_absent_with_ttl

GRAPH_WRITE_RECEIPT_KEY_PREFIX = "codexify:graph-write:receipt"
GRAPH_WRITE_RECEIPT_TTL_SECONDS = 3600


def build_graph_write_receipt_key(idempotency_key: str) -> str:
    return f"{GRAPH_WRITE_RECEIPT_KEY_PREFIX}:{str(idempotency_key).strip()}"


def claim_graph_write_receipt(
    redis_client: Any,
    idempotency_key: str,
    ttl_seconds: int = GRAPH_WRITE_RECEIPT_TTL_SECONDS,
) -> bool:
    key = build_graph_write_receipt_key(idempotency_key)
    return bool(
        set_if_absent_with_ttl(
            redis_client,
            key,
            "claimed",
            ttl_seconds,
        )
    )
