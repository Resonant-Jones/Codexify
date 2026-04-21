"""Pure normalization helpers for candidate_trace payloads."""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from typing import Any, List, Optional

_FIELD_ENTITY_MAP: dict[str, tuple[str, str]] = {
    "documents": ("document", "retrieval"),
    "messages": ("message", "thread"),
    "memory": ("fact", "memory"),
    "graph": ("unknown", "graph"),
    "payload_summary": ("unknown", "model"),
}

_CONTENT_KEYS = (
    "content",
    "text",
    "summary",
    "body",
    "title",
    "name",
    "description",
    "value",
    "message",
    "label",
)


@dataclass
class NormalizedEntity:
    type: str
    content: str
    source: str
    confidence: float
    metadata: dict[str, Any]


@dataclass
class NormalizedEntitySet:
    entities: list[NormalizedEntity] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _stable_json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): _stable_json_value(value[key])
            for key in sorted(value, key=lambda item: str(item))
        }
    if isinstance(value, list):
        return [_stable_json_value(item) for item in value]
    if isinstance(value, tuple):
        return [_stable_json_value(item) for item in value]
    if isinstance(value, set):
        return [
            _stable_json_value(item)
            for item in sorted(value, key=lambda item: repr(item))
        ]
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, (dict, list, tuple, set)):
        try:
            return json.dumps(
                _stable_json_value(value),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                default=str,
            )
        except Exception:
            return str(value)
    return str(value)


def _extract_content(fragment: Any) -> tuple[str, bool]:
    if fragment is None:
        return "", True
    if isinstance(fragment, dict):
        if not fragment:
            return "", True
        for key in _CONTENT_KEYS:
            if key not in fragment:
                continue
            content = _stringify(fragment.get(key))
            if content.strip():
                return content, False
        return _stringify(fragment), False
    content = _stringify(fragment)
    return content, not bool(content.strip())


def _extract_confidence(fragment: Any) -> tuple[float, bool]:
    if not isinstance(fragment, dict):
        return 0.5, False

    if "confidence" in fragment:
        raw = fragment.get("confidence")
    elif "score" in fragment:
        raw = fragment.get("score")
    else:
        return 0.5, False

    try:
        confidence = float(raw)
    except (TypeError, ValueError):
        return 0.5, True

    if confidence != confidence:  # NaN guard
        return 0.5, True

    return max(0.0, min(1.0, confidence)), False


def _iter_field_items(field_value: Any) -> list[Any]:
    if field_value is None:
        return []
    if isinstance(field_value, (list, tuple)):
        return list(field_value)
    return [field_value]


def _normalize_fragment(
    fragment: Any,
    *,
    field_name: str,
    entity_type: str,
    source_label: str,
    index: int,
) -> tuple[NormalizedEntity | None, bool]:
    content, malformed_content = _extract_content(fragment)
    confidence, malformed_confidence = _extract_confidence(fragment)
    if malformed_content or malformed_confidence:
        return None, True
    if not content.strip():
        return None, True

    metadata = {
        "field": field_name,
        "fragment": copy.deepcopy(fragment),
        "index": index,
        "source_label": source_label,
    }
    if isinstance(fragment, dict):
        if "confidence" in fragment:
            metadata["confidence_override"] = fragment.get("confidence")
        elif "score" in fragment:
            metadata["confidence_override"] = fragment.get("score")

    return (
        NormalizedEntity(
            type=entity_type,
            content=content,
            source=source_label,
            confidence=confidence,
            metadata=metadata,
        ),
        False,
    )


def normalize_candidate_trace(candidate_trace: dict) -> NormalizedEntitySet:
    if not isinstance(candidate_trace, dict) or not candidate_trace:
        return NormalizedEntitySet(warnings=["empty_candidate_trace"])

    entities: list[NormalizedEntity] = []
    warnings: list[str] = []
    saw_known_field = False

    for field_name in (
        "documents",
        "messages",
        "memory",
        "graph",
        "payload_summary",
    ):
        if field_name not in candidate_trace:
            continue

        saw_known_field = True
        entity_type, source_label = _FIELD_ENTITY_MAP[field_name]
        field_value = candidate_trace.get(field_name)
        items = _iter_field_items(field_value)
        if not items:
            continue

        for index, fragment in enumerate(items):
            entity, malformed = _normalize_fragment(
                fragment,
                field_name=field_name,
                entity_type=entity_type,
                source_label=source_label,
                index=index,
            )
            if entity is None:
                if malformed:
                    warnings.append("malformed_candidate_entry")
                continue
            entities.append(entity)

    if not entities and (not saw_known_field or not warnings):
        warnings.append("empty_candidate_trace")
    elif (
        not entities
        and saw_known_field
        and "empty_candidate_trace" not in warnings
    ):
        warnings.append("empty_candidate_trace")

    return NormalizedEntitySet(entities=entities, warnings=warnings)
