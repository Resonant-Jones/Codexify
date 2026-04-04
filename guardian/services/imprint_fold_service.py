"""
Deterministic folding of durable imprint observations into materialized state.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from guardian.cognition.identity_policy import (
    can_run_deep_identity_modeling,
    normalize_identity_depth,
    thread_blocks_identity_modeling,
)
from guardian.core.dependencies import get_database_dsn
from guardian.db.models import ImprintFoldState
from guardian.services import iddb_settings_service, imprint_observation_service

FOLD_VERSION = 1
SCOPE_USER_GLOBAL = "user_global"
SCOPE_PROJECT_SCOPED = "project_scoped"
COMMUNICATION_FIELDS = (
    "tone",
    "verbosity",
    "formality",
    "directness",
    "style",
    "address_style",
    "sentence_length",
    "emoji_usage",
)
LIST_FIELDS = {
    "name_hints": (
        "name_hints",
        "preferred_name",
        "guardian_name",
        "name_hint",
        "alias",
        "nickname",
    ),
    "persona_hints": (
        "persona_hints",
        "persona_hint",
        "identity_hints",
        "identity_hint",
        "style_hints",
        "style_hint",
    ),
    "prompt_hints": (
        "prompt_hints",
        "prompt_hint",
        "communication_hints",
        "communication_hint",
    ),
    "question_topics": (
        "question_topics",
        "topics",
        "interests",
        "domains",
        "focus_areas",
    ),
    "tags": ("tags", "markers", "labels"),
}

_SessionFactory: sessionmaker | None = None


def _get_session_factory() -> sessionmaker:
    global _SessionFactory
    if _SessionFactory is not None:
        return _SessionFactory

    dsn = get_database_dsn()
    if not dsn:
        raise RuntimeError(
            "Database DSN not configured; cannot access imprint fold state."
        )

    engine = create_engine(dsn, future=True)
    _SessionFactory = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, future=True
    )
    return _SessionFactory


def _set_session_factory(factory: sessionmaker) -> None:
    global _SessionFactory
    _SessionFactory = factory


def _normalize_user_id(user_id: str) -> str:
    resolved = str(user_id or "").strip()
    if not resolved:
        raise HTTPException(
            status_code=403, detail="current user could not be resolved"
        )
    return resolved


def _normalize_project_id(project_id: Any) -> int | None:
    if project_id in {None, ""}:
        return None
    try:
        return int(project_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=400, detail="project_id must be an integer"
        ) from exc


def _normalize_scope_kind(scope_kind: str) -> str:
    resolved = str(scope_kind or "").strip().lower()
    if resolved not in {SCOPE_USER_GLOBAL, SCOPE_PROJECT_SCOPED}:
        raise HTTPException(
            status_code=400, detail="invalid imprint fold scope"
        )
    return resolved


def _scope_key(user_id: str, project_id: int | None, scope_kind: str) -> str:
    if scope_kind == SCOPE_USER_GLOBAL:
        return f"user:{user_id}"
    if project_id is None:
        raise HTTPException(
            status_code=400,
            detail="project_id is required for project-scoped folds",
        )
    return f"project:{user_id}:{project_id}"


def _normalize_text(value: Any) -> str | None:
    if value is None:
        return None
    text = re.sub(r"\s+", " ", str(value)).strip().lower()
    return text or None


def _coerce_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _collect_text_values(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        normalized = _normalize_text(value)
        return [normalized] if normalized else []
    if isinstance(value, Mapping):
        collected: list[str] = []
        for item in value.values():
            collected.extend(_collect_text_values(item))
        return collected
    if isinstance(value, (list, tuple, set)):
        collected: list[str] = []
        for item in value:
            collected.extend(_collect_text_values(item))
        return collected
    normalized = _normalize_text(value)
    return [normalized] if normalized else []


def _counter_choice(counter: Counter[str]) -> str | None:
    if not counter:
        return None
    return sorted(counter.items(), key=lambda item: (-item[1], item[0]))[0][0]


def _extract_observation_features(
    observation: Any,
) -> dict[str, Any]:
    payload = _coerce_mapping(getattr(observation, "signal_payload", None))
    provenance = _coerce_mapping(getattr(observation, "provenance", None))

    communication_counts: dict[str, Counter[str]] = {
        field: Counter() for field in COMMUNICATION_FIELDS
    }
    list_counts: dict[str, Counter[str]] = {
        field: Counter() for field in LIST_FIELDS
    }
    numeric_totals: defaultdict[str, float] = defaultdict(float)
    numeric_counts: defaultdict[str, int] = defaultdict(int)

    communication_sources = [
        payload.get("communication"),
        payload.get("communication_profile"),
        provenance.get("communication"),
        provenance.get("communication_profile"),
    ]
    for source in communication_sources:
        mapping = _coerce_mapping(source)
        for field in COMMUNICATION_FIELDS:
            for value in _collect_text_values(mapping.get(field)):
                communication_counts[field][value] += 1

    for field in COMMUNICATION_FIELDS:
        for source in (payload, provenance):
            for value in _collect_text_values(source.get(field)):
                communication_counts[field][value] += 1

    for field, keys in LIST_FIELDS.items():
        for source in (payload, provenance):
            for key in keys:
                for value in _collect_text_values(source.get(key)):
                    list_counts[field][value] += 1

    traits_sources = [
        payload.get("traits"),
        payload.get("identity_traits"),
        provenance.get("traits"),
        provenance.get("identity_traits"),
    ]
    for traits_source in traits_sources:
        traits = _coerce_mapping(traits_source)
        for trait_name, trait_value in traits.items():
            if isinstance(trait_value, Mapping):
                trait_value = (
                    trait_value.get("score")
                    if trait_value.get("score") is not None
                    else trait_value.get("value")
                )
            try:
                numeric = float(trait_value)
            except (TypeError, ValueError):
                continue
            normalized_trait = _normalize_text(trait_name)
            if not normalized_trait:
                continue
            numeric_totals[normalized_trait] += numeric
            numeric_counts[normalized_trait] += 1

    preferred_name_candidates = list_counts["name_hints"].copy()
    preferred_name = _counter_choice(preferred_name_candidates)

    communication_profile = {
        field: _counter_choice(counter)
        for field, counter in communication_counts.items()
    }
    list_payload = {
        field: sorted(counter.keys()) for field, counter in list_counts.items()
    }
    trait_scores = {
        trait: round(numeric_totals[trait] / numeric_counts[trait], 4)
        for trait in sorted(numeric_totals.keys())
        if numeric_counts[trait] > 0
    }
    trait_sample_counts = {
        trait: int(numeric_counts[trait])
        for trait in sorted(numeric_counts.keys())
    }

    return {
        "signal_type": _normalize_text(
            getattr(observation, "signal_type", None)
        ),
        "signal_type_raw": getattr(observation, "signal_type", None),
        "communication_profile": communication_profile,
        "preferred_name": preferred_name,
        **list_payload,
        "trait_scores": trait_scores,
        "trait_sample_counts": trait_sample_counts,
    }


def _merge_unique(*lists: list[str]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for items in lists:
        for item in items:
            normalized = _normalize_text(item)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            merged.append(normalized)
    return merged


def _merge_communication_profiles(
    user_profile: Mapping[str, Any] | None,
    project_profile: Mapping[str, Any] | None,
) -> dict[str, Any]:
    user_profile = user_profile or {}
    project_profile = project_profile or {}
    merged: dict[str, Any] = {}
    for field in COMMUNICATION_FIELDS:
        merged[field] = project_profile.get(field) or user_profile.get(field)
    return merged


def _merge_traits(
    user_traits: Mapping[str, Any] | None,
    project_traits: Mapping[str, Any] | None,
    user_counts: Mapping[str, Any] | None,
    project_counts: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    user_traits = user_traits or {}
    project_traits = project_traits or {}
    user_counts = user_counts or {}
    project_counts = project_counts or {}
    for key in sorted(set(user_traits) | set(project_traits)):
        if key in project_traits and key in user_traits:
            user_count = int(user_counts.get(key) or 1)
            project_count = int(project_counts.get(key) or 1)
            total = (
                float(user_traits[key]) * user_count
                + float(project_traits[key]) * project_count
            )
            merged[key] = round(total / (user_count + project_count), 4)
        elif key in project_traits:
            merged[key] = float(project_traits[key])
        else:
            merged[key] = float(user_traits[key])
    return merged


def _build_state_payload(
    *,
    user_id: str,
    project_id: int | None,
    scope_kind: str,
    observations: list[Any],
) -> dict[str, Any]:
    signal_counts: Counter[str] = Counter()
    communication_profiles: dict[str, Counter[str]] = {
        field: Counter() for field in COMMUNICATION_FIELDS
    }
    preferred_names: Counter[str] = Counter()
    list_fields: dict[str, Counter[str]] = {
        field: Counter() for field in LIST_FIELDS
    }
    trait_totals: defaultdict[str, float] = defaultdict(float)
    trait_counts: defaultdict[str, int] = defaultdict(int)

    for observation in observations:
        signal_type = _normalize_text(getattr(observation, "signal_type", None))
        if signal_type:
            signal_counts[signal_type] += 1
        features = _extract_observation_features(observation)
        for field, value in features["communication_profile"].items():
            if value:
                communication_profiles[field][value] += 1
        if features["preferred_name"]:
            preferred_names[features["preferred_name"]] += 1
        for field in LIST_FIELDS:
            for value in features[field]:
                list_fields[field][value] += 1
        for trait, score in features["trait_scores"].items():
            sample_count = int(features["trait_sample_counts"].get(trait, 1))
            trait_totals[trait] += float(score) * sample_count
            trait_counts[trait] += sample_count

    communication_profile = {
        field: _counter_choice(counter)
        for field, counter in communication_profiles.items()
    }
    signal_types = sorted(signal_counts.keys())
    state_payload = {
        "fold_version": FOLD_VERSION,
        "scope_kind": scope_kind,
        "scope_key": _scope_key(user_id, project_id, scope_kind),
        "user_id": user_id,
        "project_id": project_id,
        "source_observation_count": len(observations),
        "source_observation_max_id": (
            max(
                (
                    int(getattr(observation, "id", 0) or 0)
                    for observation in observations
                ),
                default=None,
            )
        ),
        "signal_counts": dict(sorted(signal_counts.items())),
        "signal_types": signal_types,
        "communication_profile": communication_profile,
        "preferred_name": _counter_choice(preferred_names),
        "name_hints": sorted(list_fields["name_hints"].keys()),
        "persona_hints": sorted(list_fields["persona_hints"].keys()),
        "prompt_hints": sorted(list_fields["prompt_hints"].keys()),
        "question_topics": sorted(list_fields["question_topics"].keys()),
        "tags": sorted(list_fields["tags"].keys()),
        "trait_scores": {
            trait: round(trait_totals[trait] / trait_counts[trait], 4)
            for trait in sorted(trait_totals.keys())
            if trait_counts[trait] > 0
        },
        "trait_sample_counts": {
            trait: int(trait_counts[trait])
            for trait in sorted(trait_counts.keys())
        },
    }
    state_payload["combined_markers"] = _merge_unique(
        state_payload["name_hints"],
        state_payload["persona_hints"],
        state_payload["prompt_hints"],
        state_payload["question_topics"],
        state_payload["tags"],
    )
    state_payload["derived_characteristics"] = {
        "tone": communication_profile.get("tone"),
        "verbosity": communication_profile.get("verbosity"),
        "formality": communication_profile.get("formality"),
        "directness": communication_profile.get("directness"),
    }
    return state_payload


def _state_hash(state_payload: Mapping[str, Any]) -> str:
    canonical_json = json.dumps(
        state_payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def _serialize_state(row: ImprintFoldState) -> dict[str, Any]:
    return {
        "scope_key": row.scope_key,
        "scope_kind": row.scope_kind,
        "user_id": row.user_id,
        "project_id": row.project_id,
        "fold_version": row.fold_version,
        "source_observation_count": row.source_observation_count,
        "source_observation_max_id": row.source_observation_max_id,
        "state_payload": row.state_payload,
        "state_hash": row.state_hash,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def _normalize_settings(settings: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "memory_mode": str(settings.get("memory_mode") or "deep")
        .strip()
        .lower(),
        "diary_requires_unlock": bool(
            settings.get("diary_requires_unlock", False)
        ),
        "allow_sensitive_modeling": bool(
            settings.get("allow_sensitive_modeling", False)
        ),
    }


def _provenance_thread(provenance: Mapping[str, Any]) -> dict[str, Any] | None:
    for key in ("thread", "thread_flags", "thread_context"):
        candidate = provenance.get(key)
        if isinstance(candidate, Mapping):
            return dict(candidate)
    return None


def _observation_requested_depth(
    provenance: Mapping[str, Any],
    payload: Mapping[str, Any],
) -> str:
    for source in (provenance, payload):
        for key in (
            "requested_depth",
            "identity_depth",
            "modeling_depth",
            "depth",
        ):
            candidate = source.get(key)
            if candidate is not None:
                return normalize_identity_depth(candidate)
    return "light"


def _observation_is_diary(provenance: Mapping[str, Any]) -> bool:
    thread = _provenance_thread(provenance)
    if thread and thread_blocks_identity_modeling(thread):
        return True
    return bool(
        provenance.get("is_diary")
        or provenance.get("diary_mode")
        or provenance.get("exclude_from_identity")
        or provenance.get("modeling_excluded")
    )


def _observation_allows_folding(
    observation: Any,
    *,
    settings: Mapping[str, Any],
    project_identity_depth: str,
) -> bool:
    resolved_settings = _normalize_settings(settings)
    if resolved_settings["memory_mode"] == "none":
        return False
    if not resolved_settings["allow_sensitive_modeling"]:
        return False

    provenance = _coerce_mapping(getattr(observation, "provenance", None))
    payload = _coerce_mapping(getattr(observation, "signal_payload", None))
    if resolved_settings["diary_requires_unlock"] and _observation_is_diary(
        provenance
    ):
        return False

    thread = _provenance_thread(provenance)
    if thread and thread_blocks_identity_modeling(thread):
        return False

    if _observation_requested_depth(
        provenance, payload
    ) == "deep" and not can_run_deep_identity_modeling(project_identity_depth):
        return False

    return True


def _refresh_scope_state(
    *,
    user_id: str,
    project_id: int | None,
    scope_kind: str,
    project_identity_depth: str,
) -> dict[str, Any]:
    resolved_user = _normalize_user_id(user_id)
    resolved_scope_kind = _normalize_scope_kind(scope_kind)
    resolved_project = _normalize_project_id(project_id)
    settings = _normalize_settings(
        iddb_settings_service.get_user_settings(resolved_user)
    )
    observations = imprint_observation_service.list_observations_for_scope(
        resolved_user,
        resolved_project,
    )
    included = [
        observation
        for observation in observations
        if _observation_allows_folding(
            observation,
            settings=settings,
            project_identity_depth=project_identity_depth,
        )
    ]
    state_payload = _build_state_payload(
        user_id=resolved_user,
        project_id=resolved_project,
        scope_kind=resolved_scope_kind,
        observations=included,
    )
    state_hash = _state_hash(state_payload)

    Session = _get_session_factory()
    now = datetime.now(timezone.utc)
    scope_key = state_payload["scope_key"]
    with Session() as session:
        row = session.scalar(
            select(ImprintFoldState).where(
                ImprintFoldState.scope_key == scope_key
            )
        )
        if row is None:
            row = ImprintFoldState(
                scope_key=scope_key,
                user_id=resolved_user,
                project_id=resolved_project,
                scope_kind=resolved_scope_kind,
                fold_version=FOLD_VERSION,
                state_payload=state_payload,
                state_hash=state_hash,
                source_observation_count=len(included),
                source_observation_max_id=state_payload[
                    "source_observation_max_id"
                ],
                created_at=now,
                updated_at=now,
            )
            session.add(row)
        else:
            row.user_id = resolved_user
            row.project_id = resolved_project
            row.scope_kind = resolved_scope_kind
            row.fold_version = FOLD_VERSION
            row.state_payload = state_payload
            row.state_hash = state_hash
            row.source_observation_count = len(included)
            row.source_observation_max_id = state_payload[
                "source_observation_max_id"
            ]
            row.updated_at = now
        session.commit()
        session.refresh(row)
        return _serialize_state(row)


def refresh_user_global_state(
    user_id: str,
    *,
    project_identity_depth: str = "light",
) -> dict[str, Any]:
    return _refresh_scope_state(
        user_id=user_id,
        project_id=None,
        scope_kind=SCOPE_USER_GLOBAL,
        project_identity_depth=project_identity_depth,
    )


def refresh_project_state(
    user_id: str,
    project_id: int | None,
    *,
    project_identity_depth: str = "light",
) -> dict[str, Any]:
    if project_id is None:
        raise HTTPException(
            status_code=400,
            detail="project_id is required for project-scoped folds",
        )
    return _refresh_scope_state(
        user_id=user_id,
        project_id=project_id,
        scope_kind=SCOPE_PROJECT_SCOPED,
        project_identity_depth=project_identity_depth,
    )


def get_scope_state(
    user_id: str,
    project_id: int | None,
    scope_kind: str,
) -> dict[str, Any] | None:
    resolved_user = _normalize_user_id(user_id)
    resolved_project = _normalize_project_id(project_id)
    resolved_scope_kind = _normalize_scope_kind(scope_kind)
    scope_key = _scope_key(resolved_user, resolved_project, resolved_scope_kind)
    Session = _get_session_factory()
    with Session() as session:
        row = session.scalar(
            select(ImprintFoldState).where(
                ImprintFoldState.scope_key == scope_key
            )
        )
        if row is None:
            return None
        return _serialize_state(row)


def refresh_folded_scope(
    user_id: str,
    project_id: int | None,
    *,
    project_identity_depth: str = "light",
) -> dict[str, Any]:
    if project_id is None:
        return refresh_user_global_state(
            user_id,
            project_identity_depth=project_identity_depth,
        )
    return refresh_project_state(
        user_id,
        project_id,
        project_identity_depth=project_identity_depth,
    )


def merge_fold_states(
    user_global_state: Mapping[str, Any] | None,
    project_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    user_payload = (
        dict((user_global_state or {}).get("state_payload") or {})
        if "state_payload" in (user_global_state or {})
        else dict(user_global_state or {})
    )
    project_payload = (
        dict((project_state or {}).get("state_payload") or {})
        if "state_payload" in (project_state or {})
        else dict(project_state or {})
    )

    merged_communication = _merge_communication_profiles(
        user_payload.get("communication_profile"),
        project_payload.get("communication_profile"),
    )
    merged_traits = _merge_traits(
        user_payload.get("trait_scores"),
        project_payload.get("trait_scores"),
        user_payload.get("trait_sample_counts"),
        project_payload.get("trait_sample_counts"),
    )
    merged = {
        "communication_profile": merged_communication,
        "preferred_name": project_payload.get("preferred_name")
        or user_payload.get("preferred_name"),
        "name_hints": _merge_unique(
            list(user_payload.get("name_hints") or []),
            list(project_payload.get("name_hints") or []),
        ),
        "persona_hints": _merge_unique(
            list(user_payload.get("persona_hints") or []),
            list(project_payload.get("persona_hints") or []),
        ),
        "prompt_hints": _merge_unique(
            list(user_payload.get("prompt_hints") or []),
            list(project_payload.get("prompt_hints") or []),
        ),
        "question_topics": _merge_unique(
            list(user_payload.get("question_topics") or []),
            list(project_payload.get("question_topics") or []),
        ),
        "tags": _merge_unique(
            list(user_payload.get("tags") or []),
            list(project_payload.get("tags") or []),
        ),
        "trait_scores": merged_traits,
        "source_observation_count": int(
            (user_payload.get("source_observation_count") or 0)
            + (project_payload.get("source_observation_count") or 0)
        ),
        "signal_counts": dict(
            Counter(user_payload.get("signal_counts") or {})
            + Counter(project_payload.get("signal_counts") or {})
        ),
    }
    merged["combined_markers"] = _merge_unique(
        merged["name_hints"],
        merged["persona_hints"],
        merged["prompt_hints"],
        merged["question_topics"],
        merged["tags"],
    )
    merged["derived_characteristics"] = {
        "tone": merged_communication.get("tone"),
        "verbosity": merged_communication.get("verbosity"),
        "formality": merged_communication.get("formality"),
        "directness": merged_communication.get("directness"),
    }
    return merged


__all__ = [
    "FOLD_VERSION",
    "SCOPE_PROJECT_SCOPED",
    "SCOPE_USER_GLOBAL",
    "get_scope_state",
    "merge_fold_states",
    "refresh_folded_scope",
    "refresh_project_state",
    "refresh_user_global_state",
    "_set_session_factory",
]
