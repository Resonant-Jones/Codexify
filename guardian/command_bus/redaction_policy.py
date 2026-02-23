"""Deterministic argument redaction and hashing for command runs."""

from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

REDACTED = "[REDACTED]"

_SENSITIVE_KEY_PARTS = {
    "authorization",
    "cookie",
    "token",
    "secret",
    "password",
    "api_key",
    "apikey",
    "x-api-key",
}

# Optional per-command explicit path rules.
# Path segments are rooted at InvokeArguments keys: path_params/query/headers/body.
COMMAND_REDACTION_RULES: dict[str, list[tuple[str, ...]]] = {
    "*": [
        ("headers", "authorization"),
        ("headers", "cookie"),
        ("headers", "x-api-key"),
        ("query", "api_key"),
        ("query", "token"),
    ]
}


def canonical_json(value: Any) -> str:
    """Serialize deterministic JSON for hashing."""
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )


def compute_args_hash(arguments: dict[str, Any]) -> str:
    """Compute stable sha256 hash for the original invocation arguments."""
    raw = canonical_json(arguments).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def redact_arguments(
    command_id: str, arguments: dict[str, Any]
) -> dict[str, Any]:
    """Apply deterministic redaction to arguments."""
    payload = copy.deepcopy(arguments)
    _redact_recursive(payload)
    _apply_explicit_paths(payload, COMMAND_REDACTION_RULES.get("*", []))
    _apply_explicit_paths(payload, COMMAND_REDACTION_RULES.get(command_id, []))
    return payload


def _looks_sensitive_key(key: str) -> bool:
    normalized = key.strip().lower().replace("-", "_")
    if not normalized:
        return False
    if normalized in _SENSITIVE_KEY_PARTS:
        return True
    return any(part in normalized for part in _SENSITIVE_KEY_PARTS)


def _redact_recursive(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key in list(value.keys()):
            key_text = str(key)
            if _looks_sensitive_key(key_text):
                value[key] = REDACTED
                continue
            value[key] = _redact_recursive(value[key])
        return value
    if isinstance(value, list):
        for idx in range(len(value)):
            value[idx] = _redact_recursive(value[idx])
        return value
    return value


def _apply_explicit_paths(
    payload: dict[str, Any], path_rules: Sequence[tuple[str, ...]]
) -> None:
    for path in path_rules:
        if not path:
            continue
        _set_path_redacted(payload, path)


def _set_path_redacted(root: Any, path: Sequence[str]) -> None:
    current = root
    for segment in path[:-1]:
        if not isinstance(current, Mapping):
            return
        match = _find_mapping_key(current, segment)
        if match is None:
            return
        current = current.get(match)
    if not isinstance(current, Mapping):
        return
    target = _find_mapping_key(current, path[-1])
    if target is None:
        return
    current[target] = REDACTED


def _find_mapping_key(mapping: Mapping[Any, Any], target: str) -> Any | None:
    target_norm = str(target).strip().lower()
    for key in mapping.keys():
        if str(key).strip().lower() == target_norm:
            return key
    return None
