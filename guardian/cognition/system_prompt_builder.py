"""
System prompt builder.

Fetches imprint/persona/system-doc data, composes deterministic prompt segments
through the modular builder, and returns prompt metadata for UI/token warnings.
"""

from __future__ import annotations

from typing import Any

from guardian.cognition.identity_resolution import (
    resolve_imprint,
    resolve_persona,
)
from guardian.cognition.modular_prompt_builder import (
    PromptBudgets,
    build_system_prompt,
)
from guardian.cognition.prompts import (
    _base_codexify_system_prompt,
    _depth_block,
    _imprint_zero_style_block,
    _rag_hint_block,
    _system_docs_block,
    _system_profile_block,
    _user_persona_block,
)
from guardian.cognition.system_docs.store import (
    estimate_token_cost_for_docs,
    get_docs_for,
)
from guardian.cognition.system_profiles.resolver import ResolvedSystemProfile


def _render_profile_guidance(
    profile: ResolvedSystemProfile | dict[str, Any] | None,
) -> str:
    if not profile:
        return ""
    if isinstance(profile, ResolvedSystemProfile):
        payload = profile.model_dump(mode="json", exclude_none=True)
    elif isinstance(profile, dict):
        payload = dict(profile)
    else:
        return ""

    blocks_raw = payload.get("system_prompt_blocks")
    if not isinstance(blocks_raw, dict):
        blocks_raw = {}

    lines: list[str] = []
    profile_id = str(payload.get("profile_id") or "").strip()
    if profile_id:
        lines.append(f"profile_id: {profile_id}")

    for key in ("style", "behavior", "constraints"):
        value = blocks_raw.get(key)
        if isinstance(value, str) and value.strip():
            lines.append(f"{key}: {value.strip()}")

    # Preserve any additional named blocks while keeping the core order stable.
    for key in sorted(blocks_raw.keys()):
        if key in {"style", "behavior", "constraints"}:
            continue
        value = blocks_raw.get(key)
        if isinstance(value, str) and value.strip():
            lines.append(f"{key}: {value.strip()}")

    return "\n".join(lines).strip()


def _segment_map(meta: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw = meta.get("segments")
    if not isinstance(raw, list):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if isinstance(name, str):
            out[name] = item
    return out


def _build_docs_block(docs: list[Any]) -> str:
    if not docs:
        return ""
    sections: list[str] = []
    for doc in docs:
        sections.append(
            f"=== System Document: {doc.title} ===\n{doc.content}\n"
        )
    return "\n".join(sections).strip()


def build_guardian_system_prompt(
    *,
    user_id: str,
    project_id: int | None,
    depth: str,
    bundle: dict | None = None,
    token_cap: int | None = None,
    profile: ResolvedSystemProfile | dict[str, Any] | None = None,
) -> tuple[str, dict]:
    """
    Orchestrate prompt assembly for Guardian.

    Returns:
        system_prompt (str): the single system message to prepend
        meta (dict): size estimates and segment breakdown
    """
    bundle_payload = bundle if isinstance(bundle, dict) else {}
    resolved_imprint = resolve_imprint(user_id, project_id)
    resolved_persona = resolve_persona(
        user_id,
        project_id,
        requested_persona_id_or_name=bundle_payload.get("requested_persona"),
    )
    docs = get_docs_for(user_id, project_id)

    persona_body = resolved_persona.body or None
    imprint_data = {
        "guardian_name": resolved_imprint.guardian_name,
        "preferred_name": resolved_imprint.preferred_name,
        "style": resolved_imprint.style,
        "grammar_prefs": resolved_imprint.grammar_prefs,
        "metrics": resolved_imprint.metrics,
        "heat_score": resolved_imprint.heat_score,
    }
    if not any(
        [
            imprint_data.get("guardian_name"),
            imprint_data.get("preferred_name"),
            imprint_data.get("style"),
            imprint_data.get("grammar_prefs"),
            imprint_data.get("metrics"),
            imprint_data.get("heat_score"),
        ]
    ):
        imprint_data = None

    docs_block = _build_docs_block(docs)
    profile_text = _render_profile_guidance(profile)

    scratchpad_parts = [
        _depth_block(depth).strip(),
        _system_profile_block(profile_text).strip(),
        _rag_hint_block(bundle_payload).strip(),
    ]
    user_system_override = bundle_payload.get("user_system_override")
    if isinstance(user_system_override, str) and user_system_override.strip():
        scratchpad_parts.append(
            "User system override:\n" + user_system_override.strip()
        )
    scratchpad_block = "\n\n".join(part for part in scratchpad_parts if part)

    cap_tokens = token_cap or 2000
    system_prompt, builder_meta = build_system_prompt(
        base_system_prompt=_base_codexify_system_prompt(),
        imprint_block=_imprint_zero_style_block(imprint_data),
        persona_block=_user_persona_block(persona_body),
        system_docs_block=_system_docs_block(docs_block),
        scratchpad_block=scratchpad_block,
        budgets=PromptBudgets(total_max_tokens=cap_tokens),
    )

    segment_lookup = _segment_map(builder_meta)
    docs_segment = segment_lookup.get("system_docs", {})
    scratch_segment = segment_lookup.get("scratchpad", {})

    meta = {
        "total_chars": len(system_prompt or ""),
        "estimated_tokens": builder_meta["estimated_tokens_total"],
        "estimated_tokens_total": builder_meta["estimated_tokens_total"],
        "docs_count": len(docs),
        "segments": builder_meta["segments"],
        "segments_char_map": {
            name: int(segment.get("chars") or 0)
            for name, segment in segment_lookup.items()
        },
        "truncation_notes": builder_meta.get("truncation_notes", []),
        "cap_tokens": cap_tokens,
        "docs_truncated": bool(docs_segment.get("truncated")),
        "profile_truncated": bool(
            scratch_segment.get("truncated") and profile_text
        ),
        "overflow": False,
        "active_profile_id": (
            profile.active_profile_id
            if isinstance(profile, ResolvedSystemProfile)
            else (profile or {}).get("active_profile_id")
            if isinstance(profile, dict)
            else None
        ),
        "resolved_persona_source": resolved_persona.source,
        "resolved_imprint_source": resolved_imprint.source,
    }
    meta["docs_estimated_tokens"] = estimate_token_cost_for_docs(docs)
    return system_prompt, meta


__all__ = ["build_guardian_system_prompt"]
