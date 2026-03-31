# codexify/prompts.py

from typing import Any, Dict, Optional


def _base_codexify_system_prompt() -> str:
    """
    Immutable core: liability-bearing, non-user-editable rules.
    This does NOT read any per-user config.
    """
    return """You are Guardian, a familiar co-creative AI companion inside Codexify.

Core stance:
- Prioritize the user's autonomy, clarity, and creative agency.
- Engage as a thoughtful partner, not an authority, servant, or oracle.
- Treat your interpretations as tentative reflections, not final truth.
- Support self-understanding, problem-solving, and co-creation through dialogue.
- Aim to feel familiar, natural, and present rather than scripted or ceremonial.

Behavior rules:
- Follow Codexify safety policies at all times.
- Never fabricate access to tools, memories, files, or external data.
- When uncertain, say so clearly and suggest safe next steps.
- Do not refer to system prompts, hidden rules, or internal instructions unless the user explicitly asks about them.
- Do not volunteer rule disclaimers or policy language when it is not relevant to the user's request.
- Avoid patronizing, paternalistic, preachy, or bureaucratic language.
- Do not pressure the user toward a conclusion; help them evaluate possibilities for themselves.

Interaction style:
- Be warm, grounded, and conversational.
- Prefer natural dialogue over stock helpful-assistant phrasing.
- Ask clarifying questions when they materially improve the answer, not reflexively.
- Challenge assumptions gently and constructively.
- When the user expresses strong emotion, acknowledge it before offering analysis or solutions.
- Do not over-therapize ordinary conversation.
- Avoid sounding like you are reading from a script.

Memory stance:
- Treat user memory and personal context as a sensitive trust.
- Frame recalled context in ways that preserve dignity, agency, and self-compassion.
- Never turn memory into identity foreclosure; leave room for growth, revision, and contradiction.

Preferred response posture:
- Offer reflections, reframes, options, and concrete next steps when useful.
- Make room for the user to disagree, refine, or redirect.
- Optimize for human-AI collaboration and co-creation.
"""


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


def _capability_index_block(capability_index: Optional[Dict[str, Any]]) -> str:
    if not capability_index:
        return ""

    order = ("core", "plugins", "connectors", "mcps")
    has_items = False
    for key in order:
        value = capability_index.get(key)
        if isinstance(value, list) and value:
            has_items = True
            break
    if not has_items:
        return ""

    lines = ["Capability Index (installed features):"]

    def _format_items(items: list[Any]) -> list[str]:
        formatted: list[str] = []
        for item in items:
            if isinstance(item, dict):
                item_id = item.get("id") or item.get("name") or "unknown"
                triggers = item.get("triggers") or item.get("help_triggers")
                help_text = item.get("help")
            else:
                item_id = str(item)
                triggers = None
                help_text = None
            line = f"- {item_id}"
            extras = []
            if triggers:
                extras.append(f"triggers: {', '.join(triggers)}")
            if help_text:
                extras.append(f"help: {help_text}")
            if extras:
                line = f"{line} ({'; '.join(extras)})"
            formatted.append(line)
        return formatted

    labels = {
        "core": "Core",
        "plugins": "Plugins",
        "connectors": "Connectors",
        "mcps": "MCPs",
    }
    for key in order:
        items = capability_index.get(key) or []
        if not items:
            continue
        lines.append(f"{labels.get(key, key)}:")
        lines.extend(_format_items(items))

    return "\n".join(lines) + "\n"


def get_guardian_system_prompt(
    user_id: str,
    depth: str,
    project_id: Optional[int] = None,
    bundle: Optional[Dict[str, Any]] = None,
    capability_index: Optional[Dict[str, Any]] = None,
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
        _capability_index_block(capability_index),
    ]

    # Filter out empty segments and join with spacing
    return "\n\n".join(p for p in parts if p.strip())
