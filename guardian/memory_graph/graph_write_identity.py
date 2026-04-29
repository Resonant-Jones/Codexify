"""Deterministic identity helpers for derived graph-write tasks."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def _canonicalize_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): _canonicalize_value(value[key])
            for key in sorted(value, key=lambda item: str(item))
        }
    if isinstance(value, (list, tuple, set)):
        canonical_items = [_canonicalize_value(item) for item in value]
        return sorted(
            canonical_items,
            key=lambda item: json.dumps(
                item,
                sort_keys=True,
                separators=(",", ":"),
                default=str,
                ensure_ascii=False,
            ),
        )
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _stable_json(value: Any) -> str:
    return json.dumps(
        _canonicalize_value(value),
        sort_keys=True,
        separators=(",", ":"),
        default=str,
        ensure_ascii=False,
    )


def _stable_digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compute_graph_write_fingerprint(
    nodes: list[dict], edges: list[dict], warnings: list[str]
) -> str:
    canonical_payload = {
        "nodes": sorted(
            (_canonicalize_value(node) for node in nodes),
            key=lambda item: _stable_json(item),
        ),
        "edges": sorted(
            (_canonicalize_value(edge) for edge in edges),
            key=lambda item: _stable_json(item),
        ),
        "warnings": sorted(
            _canonicalize_value(warning) for warning in warnings
        ),
    }
    return _stable_digest(_stable_json(canonical_payload))


def build_graph_write_identity(
    *,
    request_id: str,
    thread_id: str | int,
    candidate_trace_id: str,
    nodes: list[dict],
    edges: list[dict],
    warnings: list[str],
) -> dict:
    fingerprint = compute_graph_write_fingerprint(nodes, edges, warnings)
    identity_seed = {
        "candidate_trace_id": str(candidate_trace_id),
        "graph_fingerprint": fingerprint,
    }
    graph_write_id = f"gwr_{_stable_digest(_stable_json(identity_seed))[:24]}"
    idempotency_key = f"graph-write:{candidate_trace_id}:{fingerprint}"
    return {
        "request_id": str(request_id),
        "thread_id": thread_id,
        "candidate_trace_id": str(candidate_trace_id),
        "graph_write_id": graph_write_id,
        "idempotency_key": idempotency_key,
        "graph_fingerprint": fingerprint,
    }
