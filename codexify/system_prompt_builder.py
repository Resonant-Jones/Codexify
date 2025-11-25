"""
System prompt builder.

Fetches imprint/persona/system-doc data, assembles a single system message
via codexify.prompts, and returns prompt metadata for UI/token warnings.
"""
from __future__ import annotations

from typing import Dict, Optional, Tuple

from codexify.prompts import (
    _base_codexify_system_prompt,
    _imprint_zero_style_block,
    _user_persona_block,
    _system_docs_block,
    _depth_block,
    _rag_hint_block,
    get_guardian_system_prompt,
)
from codexify.imprints.store import get_active_imprint
from codexify.personas.store import get_active_persona
from codexify.system_docs.store import get_docs_for, estimate_token_cost_for_docs


def _estimate_tokens(text: str) -> int:
    """Rough heuristic for token counting."""
    return len(text or "") // 4


def build_guardian_system_prompt(
    *,
    user_id: str,
    project_id: Optional[int],
    depth: str,
    bundle: Optional[Dict] = None,
) -> Tuple[str, Dict]:
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
            segments.append(f"=== System Document: {doc.title} ===\n{doc.content}\n")
        docs_block = "\n".join(segments).strip()

    system_prompt = get_guardian_system_prompt(
        user_id=user_id,
        depth=depth,
        project_id=project_id,
        bundle=bundle,
        imprint=imprint_data,
        persona=persona_body,
        system_docs_text=docs_block,
    )

    # Segment breakdown for meta
    base = _base_codexify_system_prompt()
    depth_block = _depth_block(depth)
    imprint_block = _imprint_zero_style_block(imprint_data)
    persona_block = _user_persona_block(persona_body)
    system_docs_formatted = _system_docs_block(docs_block)
    rag_block = _rag_hint_block(bundle)

    meta = {
        "total_chars": len(system_prompt or ""),
        "estimated_tokens": _estimate_tokens(system_prompt),
        "docs_count": len(docs),
        "segments": {
            "base": len(base),
            "depth": len(depth_block),
            "imprint": len(imprint_block),
            "persona": len(persona_block),
            "system_docs": len(system_docs_formatted),
            "rag_hint": len(rag_block),
        },
    }

    # Include doc token estimates separately
    meta["docs_estimated_tokens"] = estimate_token_cost_for_docs(docs)
    return system_prompt, meta


__all__ = ["build_guardian_system_prompt"]
