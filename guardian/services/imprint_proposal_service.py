"""
Deterministic proposal generator built from canonical imprint snapshots.
"""

from __future__ import annotations

import hashlib
from typing import Any

from guardian.contracts.imprint_proposal import ImprintProposal
from guardian.contracts.imprint_snapshot import ImprintSignalSnapshot

PROPOSAL_VERSION = 1
GENERATOR_VERSION = "imprint-proposal-v1"

_FIRST_NAME_BY_TONE = {
    "calm": "Len",
    "curious": "Noa",
    "direct": "Ren",
    "formal": "Ari",
    "friendly": "Mira",
    "playful": "Kai",
    "warm": "Sol",
}
_LAST_NAME_BY_VERBOSITY = {
    "balanced": "Vale",
    "brief": "Quill",
    "concise": "Vale",
    "detailed": "Thorne",
    "elaborate": "Thorne",
    "minimal": "Quill",
}
_LAST_NAME_BY_FORMALITY = {
    "casual": "Lark",
    "formal": "Bennett",
    "neutral": "Reed",
}
_LAST_NAME_BY_DIRECTNESS = {
    "direct": "North",
    "gentle": "South",
    "soft": "South",
}
_FALLBACK_FIRST_NAMES = [
    "Ari",
    "Kai",
    "Len",
    "Mira",
    "Noa",
    "Ren",
    "Sol",
]
_FALLBACK_LAST_NAMES = [
    "Vale",
    "Bennett",
    "Lark",
    "North",
    "Quill",
    "Reed",
    "Thorne",
]


def _clean_token(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    return text or None


def _title(value: str | None, fallback: str) -> str:
    text = _clean_token(value) or fallback
    return text.replace("_", " ").title()


def _pick_fallback(seed: str, items: list[str]) -> str:
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    return items[digest[0] % len(items)]


def _choose_name(snapshot: ImprintSignalSnapshot) -> tuple[str, str, str]:
    effective_state = snapshot.effective_state or {}
    profile = effective_state.get("communication_profile") or {}
    tone = _clean_token(profile.get("tone"))
    verbosity = _clean_token(profile.get("verbosity"))
    formality = _clean_token(profile.get("formality"))
    directness = _clean_token(profile.get("directness"))

    first_name = _FIRST_NAME_BY_TONE.get(tone or "") or _pick_fallback(
        f"{snapshot.snapshot_hash}:first:{tone}:{verbosity}:{formality}:{directness}",
        _FALLBACK_FIRST_NAMES,
    )
    last_name = (
        _LAST_NAME_BY_VERBOSITY.get(verbosity or "")
        or _LAST_NAME_BY_FORMALITY.get(formality or "")
        or _LAST_NAME_BY_DIRECTNESS.get(directness or "")
        or _pick_fallback(
            f"{snapshot.snapshot_hash}:last:{tone}:{verbosity}:{formality}:{directness}",
            _FALLBACK_LAST_NAMES,
        )
    )
    style = "-".join(
        part
        for part in (
            tone or "balanced",
            verbosity or "balanced",
        )
        if part
    )
    return first_name, last_name, style


def _merge_counts(*counters: dict[str, Any]) -> dict[str, int]:
    merged: dict[str, int] = {}
    for counter in counters:
        for key, value in (counter or {}).items():
            try:
                merged[key] = merged.get(key, 0) + int(value)
            except (TypeError, ValueError):
                continue
    return dict(sorted(merged.items()))


def _stable_heat_score(
    snapshot: ImprintSignalSnapshot, proposal_name: str
) -> float:
    effective_state = snapshot.effective_state or {}
    hint_count = sum(
        len(effective_state.get(field) or [])
        for field in (
            "name_hints",
            "persona_hints",
            "prompt_hints",
            "question_topics",
        )
    )
    observation_count = int(
        effective_state.get("source_observation_count") or 0
    )
    score = 0.2 + (hint_count * 0.05) + min(0.35, observation_count * 0.03)
    if _clean_token(snapshot.requested_depth) == "deep":
        score += 0.08
    if proposal_name:
        score += min(0.1, len(proposal_name) / 100.0)
    return round(min(1.0, score), 3)


def _build_persona_draft(
    *,
    proposal_name: str,
    preferred_name: str,
    snapshot: ImprintSignalSnapshot,
    style: str,
    prompt_hints: list[str],
    persona_hints: list[str],
    combined_markers: list[str],
) -> str:
    effective_state = snapshot.effective_state or {}
    profile = effective_state.get("communication_profile") or {}
    tone = _title(profile.get("tone"), "balanced")
    verbosity = _title(profile.get("verbosity"), "balanced")
    formality = _title(profile.get("formality"), "neutral")
    directness = _title(profile.get("directness"), "balanced")
    requested_depth = _title(snapshot.requested_depth, "light")
    project_depth = _title(snapshot.project_identity_depth, "light")

    lines = [
        f"You are {proposal_name}, the Guardian assistant for this user inside Codexify.",
        f"Modeling depth: {requested_depth} with project policy at {project_depth}.",
        f"Speak in a {tone.lower()} tone with {verbosity.lower()} answers.",
        f"Keep the style {style} and use {formality.lower()} but not stiff language.",
        f"Prefer {directness.lower()} phrasing when it is helpful.",
    ]
    if preferred_name:
        lines.append(
            f'Address the user as "{preferred_name}" when it feels natural.'
        )
    if persona_hints:
        lines.append("Persona cues:")
        lines.extend(f"- {hint}" for hint in persona_hints[:5])
    if prompt_hints:
        lines.append("Prompt cues:")
        lines.extend(f"- {hint}" for hint in prompt_hints[:5])
    if combined_markers:
        lines.append("Stable markers:")
        lines.extend(f"- {marker}" for marker in combined_markers[:5])
    lines.append("When unsure, ask a clarifying question instead of guessing.")
    return "\n".join(lines)


def build_imprint_proposal(
    snapshot: ImprintSignalSnapshot,
) -> ImprintProposal:
    effective_state = snapshot.effective_state or {}
    profile = effective_state.get("communication_profile") or {}
    first_name, last_name, style = _choose_name(snapshot)
    proposal_name = f"{first_name} {last_name}".strip()
    preferred_name = (
        _clean_token(effective_state.get("preferred_name")) or "friend"
    )
    prompt_hints = list(effective_state.get("prompt_hints") or [])
    persona_hints = list(effective_state.get("persona_hints") or [])
    name_hints = list(effective_state.get("name_hints") or [])
    question_topics = list(effective_state.get("question_topics") or [])
    tags = list(effective_state.get("tags") or [])
    combined_markers = list(effective_state.get("combined_markers") or [])
    signal_counts = _merge_counts(effective_state.get("signal_counts") or {})
    trait_scores = dict(
        sorted((effective_state.get("trait_scores") or {}).items())
    )
    grammar_prefs = {
        "tone": _clean_token(profile.get("tone")) or "balanced",
        "verbosity": _clean_token(profile.get("verbosity")) or "balanced",
        "formality": _clean_token(profile.get("formality")) or "neutral",
        "directness": _clean_token(profile.get("directness")) or "balanced",
        "requested_depth": _clean_token(snapshot.requested_depth) or "light",
        "project_identity_depth": _clean_token(snapshot.project_identity_depth)
        or "light",
    }
    heat_score = _stable_heat_score(snapshot, proposal_name)
    persona_draft = _build_persona_draft(
        proposal_name=proposal_name,
        preferred_name=preferred_name,
        snapshot=snapshot,
        style=style,
        prompt_hints=prompt_hints,
        persona_hints=persona_hints,
        combined_markers=combined_markers,
    )
    prompt_metadata: dict[str, Any] = {
        "proposal_name": proposal_name,
        "preferred_name": preferred_name,
        "style": style,
        "persona_style": {
            "tone": grammar_prefs["tone"],
            "verbosity": grammar_prefs["verbosity"],
            "formality": grammar_prefs["formality"],
            "directness": grammar_prefs["directness"],
        },
        "grammar_prefs": grammar_prefs,
        "prompt_hints": prompt_hints,
        "persona_hints": persona_hints,
        "name_hints": name_hints,
        "question_topics": question_topics,
        "tags": tags,
        "combined_markers": combined_markers,
        "signal_counts": signal_counts,
        "trait_scores": trait_scores,
        "source_observation_count": int(
            effective_state.get("source_observation_count") or 0
        ),
        "snapshot_version": snapshot.snapshot_version,
        "snapshot_hash": snapshot.snapshot_hash,
        "builder_version": snapshot.builder_version,
        "generator_version": GENERATOR_VERSION,
        "requested_depth": snapshot.requested_depth,
        "project_identity_depth": snapshot.project_identity_depth,
        "heat_score": heat_score,
    }
    return ImprintProposal(
        proposal_version=PROPOSAL_VERSION,
        generator_version=GENERATOR_VERSION,
        snapshot_version=snapshot.snapshot_version,
        snapshot_hash=snapshot.snapshot_hash,
        user_id=snapshot.user_id,
        project_id=snapshot.project_id,
        scope_kind=snapshot.scope_kind,
        proposal_name=proposal_name,
        preferred_name=preferred_name,
        persona_draft=persona_draft,
        prompt_metadata=prompt_metadata,
    )


__all__ = [
    "GENERATOR_VERSION",
    "PROPOSAL_VERSION",
    "build_imprint_proposal",
]
