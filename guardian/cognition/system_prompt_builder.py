"""
System prompt builder.

Fetches imprint/persona/system-doc data, assembles a single system message
via codexify.prompts, and returns prompt metadata for UI/token warnings.
"""
from __future__ import annotations

from typing import Any

from guardian.cognition.imprints.store import get_active_imprint
from guardian.cognition.personas.store import get_active_persona
from guardian.cognition.prompts import (
    _base_codexify_system_prompt,
    _depth_block,
    _imprint_zero_style_block,
    _rag_hint_block,
    _system_docs_block,
    _system_profile_block,
    _user_persona_block,
    get_guardian_system_prompt,
)
from guardian.cognition.system_docs.store import (
    estimate_token_cost_for_docs,
    get_docs_for,
)
from guardian.cognition.system_profiles.resolver import ResolvedSystemProfile


def _estimate_tokens(text: str) -> int:
    """Rough heuristic for token counting."""
    return len(text or "") // 4


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


def _truncate_segment_for_budget(
    *,
    full_text: str,
    remaining_tokens: int,
) -> str:
    remaining_tokens = max(0, int(remaining_tokens))
    max_chars = max(0, remaining_tokens * 4)
    if len(full_text) <= max_chars:
        return full_text
    if max_chars <= 0:
        return ""
    marker = "\n[TRUNCATED DUE TO TOKEN BUDGET]"
    if max_chars <= len(marker):
        return marker[:max_chars]
    return full_text[: max_chars - len(marker)].rstrip() + marker


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
    imprint = get_active_imprint(user_id, project_id)
    persona_row = get_active_persona(user_id, project_id)
    docs = get_docs_for(user_id, project_id)

    persona_body = persona_row.body if persona_row else None
    imprint_data = None
    if imprint:
        imprint_data = {
            "guardian_name": getattr(imprint, "guardian_name", None),
            "preferred_name": getattr(imprint, "preferred_name", None),
            "style": getattr(imprint, "style", None),
            "grammar_prefs": getattr(imprint, "grammar_prefs", None),
            "metrics": getattr(imprint, "metrics", None),
            "heat_score": getattr(imprint, "heat_score", None),
        }

    docs_block = ""
    if docs:
        segments = []
        for doc in docs:
            segments.append(
                f"=== System Document: {doc.title} ===\n{doc.content}\n"
            )
        docs_block = "\n".join(segments).strip()
    profile_text = _render_profile_guidance(profile)
    docs_text_for_prompt = docs_block
    profile_text_for_prompt = profile_text

    # Apply optional token cap (char heuristic) by truncating system docs if necessary.
    # We never drop/modify the immutable core, depth, or imprint/persona blocks.
    system_prompt = get_guardian_system_prompt(
        user_id=user_id,
        depth=depth,
        project_id=project_id,
        bundle=bundle,
        imprint=imprint_data,
        system_profile_text=profile_text_for_prompt,
        persona=persona_body,
        system_docs_text=docs_text_for_prompt,
    )
    cap_tokens = token_cap or 2000
    estimated_tokens = _estimate_tokens(system_prompt)
    docs_truncated = False
    profile_truncated = False

    if estimated_tokens > cap_tokens and docs_block:
        # Remove current docs contribution and reapply with truncation budget
        non_doc_prompt = get_guardian_system_prompt(
            user_id=user_id,
            depth=depth,
            project_id=project_id,
            bundle=bundle,
            imprint=imprint_data,
            system_profile_text=profile_text_for_prompt,
            persona=persona_body,
            system_docs_text="",
        )
        remaining_tokens = cap_tokens - _estimate_tokens(non_doc_prompt)
        truncated_text = _truncate_segment_for_budget(
            full_text=docs_block,
            remaining_tokens=remaining_tokens,
        )
        docs_text_for_prompt = truncated_text
        system_prompt = get_guardian_system_prompt(
            user_id=user_id,
            depth=depth,
            project_id=project_id,
            bundle=bundle,
            imprint=imprint_data,
            system_profile_text=profile_text_for_prompt,
            persona=persona_body,
            system_docs_text=docs_text_for_prompt,
        )
        estimated_tokens = _estimate_tokens(system_prompt)
        docs_truncated = True

    if estimated_tokens > cap_tokens and profile_text:
        # Preserve immutable+depth (+imprint/persona/docs) and shrink profile slice.
        non_profile_prompt = get_guardian_system_prompt(
            user_id=user_id,
            depth=depth,
            project_id=project_id,
            bundle=bundle,
            imprint=imprint_data,
            system_profile_text="",
            persona=persona_body,
            system_docs_text=docs_text_for_prompt,
        )
        remaining_tokens = cap_tokens - _estimate_tokens(non_profile_prompt)
        truncated_profile = _truncate_segment_for_budget(
            full_text=profile_text,
            remaining_tokens=remaining_tokens,
        )
        profile_text_for_prompt = truncated_profile
        system_prompt = get_guardian_system_prompt(
            user_id=user_id,
            depth=depth,
            project_id=project_id,
            bundle=bundle,
            imprint=imprint_data,
            system_profile_text=profile_text_for_prompt,
            persona=persona_body,
            system_docs_text=docs_text_for_prompt,
        )
        estimated_tokens = _estimate_tokens(system_prompt)
        profile_truncated = truncated_profile != profile_text

    # Hard cap if still over budget (truncate tail, keep marker)
    if estimated_tokens > cap_tokens:
        marker = "\n[TRUNCATED DUE TO TOKEN BUDGET]"
        hard_chars = max(0, cap_tokens * 4)
        if hard_chars > len(marker):
            system_prompt = (
                system_prompt[: hard_chars - len(marker)].rstrip()
            ) + marker
        else:
            system_prompt = marker[:hard_chars]
        estimated_tokens = _estimate_tokens(system_prompt)
        docs_truncated = True

    # Segment breakdown for meta
    base = _base_codexify_system_prompt()
    depth_block = _depth_block(depth)
    imprint_block = _imprint_zero_style_block(imprint_data)
    profile_block = _system_profile_block(profile_text)
    persona_block = _user_persona_block(persona_body)
    system_docs_formatted = _system_docs_block(docs_block)
    rag_block = _rag_hint_block(bundle)

    meta = {
        "total_chars": len(system_prompt or ""),
        "estimated_tokens": estimated_tokens,
        "docs_count": len(docs),
        "segments": {
            "base": len(base),
            "depth": len(depth_block),
            "imprint": len(imprint_block),
            "profile": len(profile_block),
            "persona": len(persona_block),
            "system_docs": len(system_docs_formatted),
            "rag_hint": len(rag_block),
        },
        "cap_tokens": cap_tokens,
        "docs_truncated": docs_truncated,
        "profile_truncated": profile_truncated,
        "overflow": estimated_tokens > cap_tokens,
        "active_profile_id": (
            profile.active_profile_id
            if isinstance(profile, ResolvedSystemProfile)
            else (profile or {}).get("active_profile_id")
            if isinstance(profile, dict)
            else None
        ),
    }

    # Include doc token estimates separately
    meta["docs_estimated_tokens"] = estimate_token_cost_for_docs(docs)
    return system_prompt, meta


__all__ = ["build_guardian_system_prompt"]
