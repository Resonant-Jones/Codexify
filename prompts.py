# codexify/prompts.py

from typing import Any, Dict, Optional


def _base_codexify_system_prompt() -> str:
    """
    Immutable core: your liability-bearing, non-user-editable rules.
    This does NOT read any per-user config.
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


def _imprint_zero_style_block(user_id: str) -> str:
    """
    Optional: pull from Imprint_Zero memory (grammar, tone, name, etc.)
    This is advisory, not overriding the core rules.
    """
    # Pseudocode – you’ll wire this to your imprint store:
    # imprint = imprint_store.get(user_id)
    imprint = None

    if not imprint:
        return ""

    parts = []

    name = imprint.get("guardian_name")
    if name:
        parts.append(
            f"Address the user as '{imprint.get('preferred_name', 'friend')}'."
        )
        parts.append(f"Present yourself as '{name}', their Guardian.")

    style = imprint.get("style")
    if style == "playful-dry":
        parts.append("Use a dry, lightly playful tone when appropriate.")
    elif style == "clinical":
        parts.append("Prefer a clinical, highly-structured tone.")

    # etc…

    if not parts:
        return ""

    return (
        "User-style guidance (from Imprint_Zero):\n"
        + "\n".join(f"- {p}" for p in parts)
        + "\n"
    )


def _user_persona_block(user_id: str, project_id: Optional[int]) -> str:
    """
    Optional: user-configurable persona / instructions stored in DB or config.
    This is constrained to *add* behavior, not remove safety rules.
    """
    # Pseudocode: fetch persona from DB
    # persona = persona_store.get(user_id=user_id, project_id=project_id)
    persona = None
    if not persona:
        return ""

    instructions = persona.get("instructions")
    if not instructions:
        return ""

    return (
        "User-provided persona instructions (do not override safety rules):\n"
        f"{instructions}\n"
    )


def _depth_block(depth: str) -> str:
    if depth == "shallow":
        return "Prioritize speed over exhaustive analysis.\n"
    if depth == "deep":
        return "Favor deep, multi-step reasoning and rich explanations.\n"
    # normal
    return "Balance speed and depth.\n"


def _rag_hint_block(bundle: Optional[Dict[str, Any]]) -> str:
    """
    Optional: lightly describe that RAG context exists without duplicating content.
    `_groq_complete` still injects a detailed context system message.
    """
    if not bundle:
        return ""
    hints = []
    if bundle.get("documents"):
        hints.append(
            "You may have access to retrieved documents relevant to the query."
        )
    if bundle.get("graph"):
        hints.append(
            "You may have access to knowledge graph nodes and relationships."
        )
    if not hints:
        return ""
    return "Context hints:\n" + "\n".join(f"- {h}" for h in hints) + "\n"


def get_guardian_system_prompt(
    user_id: str,
    depth: str,
    project_id: Optional[int] = None,
    bundle: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Compose the final system message:

    1. Immutable Codexify core (non-negotiable).
    2. Depth / reasoning mode guidance.
    3. Imprint_Zero style block (if available).
    4. User persona instructions (if configured).
    5. Light hint that additional context may exist (bundle).

    Users never see or edit the core; they only control the persona slice.
    """
    parts = [
        _base_codexify_system_prompt(),
        _depth_block(depth),
        _imprint_zero_style_block(user_id),
        _user_persona_block(user_id, project_id),
        _rag_hint_block(bundle),
    ]

    # Filter out empty segments and join with spacing
    return "\n\n".join(p for p in parts if p.strip())
