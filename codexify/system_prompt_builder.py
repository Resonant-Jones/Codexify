"""
System prompt builder.

Fetches imprint/persona/system-doc data, assembles a single system message
via codexify.prompts, and returns prompt metadata for UI/token warnings.
"""
from __future__ import annotations

from typing import Dict, Optional, Tuple

from codexify.imprints.store import get_active_imprint
from codexify.personas.store import get_active_persona
from codexify.prompts import (
    _base_codexify_system_prompt,
    _depth_block,
    _imprint_zero_style_block,
    _rag_hint_block,
    _system_docs_block,
    _user_persona_block,
    get_guardian_system_prompt,
)
from codexify.system_docs.store import (
    estimate_token_cost_for_docs,
    get_docs_for,
)


def _estimate_tokens(text: str) -> int:
    """Rough heuristic for token counting."""
    return len(text or "") // 4


def build_guardian_system_prompt(
    *,
    user_id: str,
    project_id: int | None,
    depth: str,
    bundle: dict | None = None,
    token_cap: int | None = None,
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

    # Apply optional token cap (char heuristic) by truncating system docs if necessary.
    # We never drop/modify the immutable core, depth, imprint, or persona blocks.
    system_prompt = get_guardian_system_prompt(
        user_id=user_id,
        depth=depth,
        project_id=project_id,
        bundle=bundle,
        imprint=imprint_data,
        persona=persona_body,
        system_docs_text=docs_block,
    )
    cap_tokens = token_cap or 2000
    estimated_tokens = _estimate_tokens(system_prompt)
    docs_truncated = False

    if estimated_tokens > cap_tokens and docs_block:
        # Remove current docs contribution and reapply with truncation budget
        non_doc_prompt = get_guardian_system_prompt(
            user_id=user_id,
            depth=depth,
            project_id=project_id,
            bundle=bundle,
            imprint=imprint_data,
            persona=persona_body,
            system_docs_text="",
        )
        remaining_tokens = cap_tokens - _estimate_tokens(non_doc_prompt)
        if remaining_tokens < 0:
            remaining_tokens = 0
        max_chars = max(0, remaining_tokens * 4)
        truncated_text = docs_block[:max_chars].rstrip()
        if truncated_text != docs_block:
            truncated_text += "\n[TRUNCATED DUE TO TOKEN BUDGET]"
        system_prompt = get_guardian_system_prompt(
            user_id=user_id,
            depth=depth,
            project_id=project_id,
            bundle=bundle,
            imprint=imprint_data,
            persona=persona_body,
            system_docs_text=truncated_text,
        )
        estimated_tokens = _estimate_tokens(system_prompt)
        docs_truncated = True

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
            "persona": len(persona_block),
            "system_docs": len(system_docs_formatted),
            "rag_hint": len(rag_block),
        },
        "cap_tokens": cap_tokens,
        "docs_truncated": docs_truncated,
        "overflow": estimated_tokens > cap_tokens,
    }

    # Include doc token estimates separately
    meta["docs_estimated_tokens"] = estimate_token_cost_for_docs(docs)
    return system_prompt, meta


__all__ = ["build_guardian_system_prompt"]
