"""Deterministic read-only command-bus search index."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Sequence

_MIN_LIMIT = 1
_MAX_LIMIT = 50
_DEFAULT_LIMIT = 20

_WEIGHT_COMMAND_ID_EXACT = 10_000
_WEIGHT_COMMAND_ID_CONTAINS = 1_000
_WEIGHT_ALIAS_EXACT = 7_500
_WEIGHT_ALIAS_CONTAINS = 900
_WEIGHT_MEDIUM = 350
_WEIGHT_LOW = 180


@dataclass(frozen=True)
class CommandSearchRecord:
    command_id: str
    method: str | None = None
    path: str | None = None
    summary: str | None = None
    description: str | None = None
    aliases: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    command_class: str | None = None
    internal: bool = True


@dataclass(frozen=True)
class CommandSearchQuery:
    query: str
    limit: int = _DEFAULT_LIMIT


@dataclass(frozen=True)
class CommandSearchResult:
    command_id: str
    score: int
    matched_terms: tuple[str, ...]
    required_terms: tuple[str, ...]
    method: str | None = None
    path: str | None = None
    summary: str | None = None
    description: str | None = None
    aliases: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    command_class: str | None = None
    internal: bool = True


def search_commands(
    records: Sequence[CommandSearchRecord],
    query: CommandSearchQuery,
) -> list[CommandSearchResult]:
    required_terms, optional_terms, ordered_terms = _parse_query_terms(query.query)
    if not ordered_terms:
        return []

    limit = _clamp_limit(query.limit)
    results: list[CommandSearchResult] = []

    for record in records:
        index = _build_record_index(record)
        if not _matches_required_terms(required_terms, index):
            continue

        score = 0
        matched: list[str] = []
        for term in ordered_terms:
            term_score = _score_term(term, index)
            if term_score > 0:
                score += term_score
                matched.append(term)

        if score <= 0:
            continue

        results.append(
            CommandSearchResult(
                command_id=record.command_id,
                score=score,
                matched_terms=tuple(matched),
                required_terms=required_terms,
                method=record.method,
                path=record.path,
                summary=record.summary,
                description=record.description,
                aliases=record.aliases,
                tags=record.tags,
                command_class=record.command_class,
                internal=record.internal,
            )
        )

    results.sort(key=lambda item: (-item.score, item.command_id))
    return results[:limit]


def records_from_manifest(manifest: object) -> list[CommandSearchRecord]:
    command_objects = _extract_manifest_commands(manifest)
    records: list[CommandSearchRecord] = []

    for command in command_objects:
        command_id = _read_text_field(command, "command_id")
        if command_id is None:
            continue

        aliases = _read_string_iterable_field(command, "aliases")
        tags = _read_string_iterable_field(command, "tags")
        method = _read_text_field(command, "method")
        path = _read_text_field(command, "path_template") or _read_text_field(
            command, "path"
        )
        summary = _read_text_field(command, "summary") or _read_text_field(
            command, "operation_id"
        )
        description = _read_text_field(command, "description")
        command_class = _read_text_field(command, "command_class") or _read_text_field(
            command, "effect"
        )
        internal = _read_bool_field(command, "internal", default=True)

        records.append(
            CommandSearchRecord(
                command_id=command_id,
                method=method,
                path=path,
                summary=summary,
                description=description,
                aliases=aliases,
                tags=tags,
                command_class=command_class,
                internal=internal,
            )
        )

    records.sort(key=lambda record: record.command_id)
    return records


def _clamp_limit(raw_limit: int) -> int:
    return max(_MIN_LIMIT, min(_MAX_LIMIT, int(raw_limit or _DEFAULT_LIMIT)))


def _parse_query_terms(query_text: str) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    required_terms: list[str] = []
    optional_terms: list[str] = []
    ordered_terms: list[str] = []
    seen_terms: set[str] = set()

    for raw_term in (query_text or "").split():
        token = raw_term.strip()
        if not token:
            continue

        is_required = token.startswith("+")
        normalized = token[1:] if is_required else token
        normalized = normalized.strip().lower()
        if not normalized:
            continue

        if normalized not in seen_terms:
            ordered_terms.append(normalized)
            seen_terms.add(normalized)

        if is_required:
            if normalized not in required_terms:
                required_terms.append(normalized)
        elif normalized not in optional_terms:
            optional_terms.append(normalized)

    return tuple(required_terms), tuple(optional_terms), tuple(ordered_terms)


def _build_record_index(record: CommandSearchRecord) -> dict[str, Any]:
    command_id = record.command_id.lower()
    aliases = tuple(alias.lower() for alias in record.aliases)
    method = (record.method or "").lower()
    path = (record.path or "").lower()
    summary = (record.summary or "").lower()
    description = (record.description or "").lower()
    tags = tuple(tag.lower() for tag in record.tags)
    command_class = (record.command_class or "").lower()

    all_terms = [
        command_id,
        *aliases,
        method,
        path,
        summary,
        description,
        *tags,
        command_class,
    ]
    all_text = "\n".join(value for value in all_terms if value)

    return {
        "command_id": command_id,
        "aliases": aliases,
        "method": method,
        "path": path,
        "summary": summary,
        "description": description,
        "tags": tags,
        "command_class": command_class,
        "all_text": all_text,
    }


def _matches_required_terms(
    required_terms: tuple[str, ...], index: dict[str, Any]
) -> bool:
    haystack = index["all_text"]
    return all(term in haystack for term in required_terms)


def _score_term(term: str, index: dict[str, Any]) -> int:
    score = 0

    command_id = index["command_id"]
    if term == command_id:
        score += _WEIGHT_COMMAND_ID_EXACT
    elif term in command_id:
        score += _WEIGHT_COMMAND_ID_CONTAINS

    aliases: tuple[str, ...] = index["aliases"]
    if any(term == alias for alias in aliases):
        score += _WEIGHT_ALIAS_EXACT
    elif any(term in alias for alias in aliases):
        score += _WEIGHT_ALIAS_CONTAINS

    method = index["method"]
    if term in method and method:
        score += _WEIGHT_MEDIUM

    path = index["path"]
    if term in path and path:
        score += _WEIGHT_MEDIUM

    summary = index["summary"]
    if term in summary and summary:
        score += _WEIGHT_MEDIUM

    description = index["description"]
    if term in description and description:
        score += _WEIGHT_LOW

    tags: tuple[str, ...] = index["tags"]
    if any(term in tag for tag in tags):
        score += _WEIGHT_LOW

    command_class = index["command_class"]
    if term in command_class and command_class:
        score += _WEIGHT_LOW

    return score


def _extract_manifest_commands(manifest: object) -> list[object]:
    if hasattr(manifest, "commands"):
        commands = getattr(manifest, "commands")
    elif isinstance(manifest, dict):
        commands = manifest.get("commands")
    else:
        commands = None

    if not isinstance(commands, list):
        return []
    return list(commands)


def _read_text_field(payload: object, field_name: str) -> str | None:
    raw = _read_field(payload, field_name)
    if raw is None:
        return None
    text = str(raw).strip()
    return text or None


def _read_string_iterable_field(
    payload: object, field_name: str
) -> tuple[str, ...]:
    raw = _read_field(payload, field_name)
    if not isinstance(raw, Iterable) or isinstance(raw, (str, bytes, dict)):
        return ()

    values: list[str] = []
    for item in raw:
        text = str(item or "").strip()
        if text:
            values.append(text)
    return tuple(values)


def _read_bool_field(payload: object, field_name: str, *, default: bool) -> bool:
    raw = _read_field(payload, field_name)
    if isinstance(raw, bool):
        return raw
    return default


def _read_field(payload: object, field_name: str) -> Any:
    if isinstance(payload, dict):
        return payload.get(field_name)
    if hasattr(payload, field_name):
        return getattr(payload, field_name)
    return None
