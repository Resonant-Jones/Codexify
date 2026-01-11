"""
codexify/prompts.py

System prompt assembly with a small, immutable core plus optional
Imprint_Zero, persona, system-doc, and RAG hint blocks. All storage lookups
are expected to be handled by the caller (see system_prompt_builder.py).
"""

from typing import Any, Dict, Optional


def _base_codexify_system_prompt() -> str:
    """
    Immutable core: liability-bearing, non-user-editable rules.
    DO NOT modify this content or allow user overrides.
    """
    return (
        "You are Guardian, the resident assistant in the Codexify environment. "
        "Non-negotiable rules:\n"
        "- Follow Codexify safety policies at all times.\n"
        "- Never fabricate access to tools or data.\n"
        "- When you are uncertain, say so explicitly and propose safe next steps.\n"
        "- Treat the user as the owner of their data, but respect legal and safety constraints.\n"
        "- Optimize for software engineering workflows: clarity, structure, traceability.\n"
    )


def _imprint_zero_style_block(imprint: Optional[Dict[str, Any]]) -> str:
    """
    Optional: pull from Imprint_Zero memory (grammar, tone, name, etc.).
    Caller provides the imprint object; this function is pure string assembly.
    """
    if not imprint:
        return ""

    parts = []

    name = imprint.get("guardian_name")
    if name:
        parts.append(f"Present yourself as '{name}', the user's Guardian.")

    preferred_name = imprint.get("preferred_name")
    if preferred_name:
        parts.append(f"Address the user as '{preferred_name}'.")

    style = imprint.get("style")
    if style == "playful-dry":
        parts.append("Use a dry, lightly playful tone when appropriate.")
    elif style == "clinical":
        parts.append("Prefer a clinical, highly-structured tone.")

    grammar_prefs = imprint.get("grammar_prefs") or {}
    if grammar_prefs.get("oxfordComma"):
        parts.append("Prefer the Oxford comma when enumerating items.")

    if not parts:
        return ""

    return (
        "User-style guidance (from Imprint_Zero):\n"
        + "\n".join(f"- {p}" for p in parts)
        + "\n"
    )


def _user_persona_block(instructions: Optional[str]) -> str:
    """
    Optional: user-configurable persona / instructions provided by caller.
    This can add behavior but never overrides safety rules.
    """
    if not instructions:
        return ""

    return (
        "User-provided persona instructions (do not override safety rules):\n"
        f"{instructions}\n"
    )


def _system_docs_block(text: Optional[str]) -> str:
    """Formatted block for attached system documents."""
    if not text or not text.strip():
        return ""
    return "Attached system documents:\n" + text.strip() + "\n"


def _depth_block(depth: str) -> str:
    if depth == "shallow":
        return "Prioritize speed over exhaustive analysis.\n"
    if depth == "deep":
        return "Favor deep, multi-step reasoning and rich explanations.\n"
    if depth == "diagnostic":
        return "Expose traces and system reasoning verbosely for debugging.\n"
    # normal
    return "Balance speed and depth.\n"


def _rag_hint_block(bundle: Optional[Dict[str, Any]]) -> str:
    """
    Optional: lightly describe that RAG context exists without duplicating content.
    `_groq_complete` may inject a separate, detailed context system message.
    """
    if not bundle:
        return ""
    hints = []
    if bundle.get("semantic"):
        hints.append(
            "You may have semantic search context relevant to the query."
        )
    if bundle.get("memory"):
        hints.append("You may have memory search results for this user.")
    if bundle.get("graph"):
        hints.append("You may have graph-derived context.")
    if not hints:
        return ""
    return "Context hints:\n" + "\n".join(f"- {h}" for h in hints) + "\n"


def get_guardian_system_prompt(
    *,
    user_id: str,
    depth: str,
    project_id: Optional[int] = None,
    bundle: Optional[Dict[str, Any]] = None,
    imprint: Optional[Dict[str, Any]] = None,
    persona: Optional[str] = None,
    system_docs_text: Optional[str] = None,
) -> str:
    """
    Compose the final system message:

    1. Immutable Codexify core (non-negotiable).
    2. Depth / reasoning mode guidance.
    3. Imprint_Zero style block (if available).
    4. User persona instructions (if configured).
    5. Attached system docs (if any).
    6. Light hint that additional context may exist (bundle).

    Users never see or edit the core; they only control the persona/docs slices.
    All storage lookups must be performed upstream.
    """
    # Keep the immutable base untouched
    base = _base_codexify_system_prompt()
    depth_block = _depth_block(depth)
    imprint_block = _imprint_zero_style_block(imprint)
    persona_block = _user_persona_block(persona)
    docs_block = _system_docs_block(system_docs_text)
    rag_block = _rag_hint_block(bundle)

    parts = [
        base,
        depth_block,
        imprint_block,
        persona_block,
        docs_block,
        rag_block,
    ]

    # Filter out empty segments and join with spacing
    return "\n\n".join(p for p in parts if p and p.strip())


__all__ = [
    "_base_codexify_system_prompt",
    "_imprint_zero_style_block",
    "_user_persona_block",
    "_system_docs_block",
    "_depth_block",
    "_rag_hint_block",
    "get_guardian_system_prompt",
]
