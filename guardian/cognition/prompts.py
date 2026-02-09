"""
codexify/prompts.py

System prompt assembly with a small, immutable core plus optional
Imprint_Zero, persona, system-doc, and RAG hint blocks. All storage lookups
are expected to be handled by the caller (see system_prompt_builder.py).
"""

from datetime import datetime, timezone
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


def _parse_anchor_timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value).strip()
        if not text:
            return None
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _format_memory_anchor(item: Dict[str, Any]) -> str | None:
    txt = item.get("text") or item.get("content") or ""
    if not txt:
        return None

    meta = item.get("metadata")
    if not isinstance(meta, dict):
        meta = {}

    timestamp = _parse_anchor_timestamp(meta.get("source_created_at"))
    if timestamp is None:
        timestamp = _parse_anchor_timestamp(meta.get("imported_at"))
    timestamp_label = (
        timestamp.strftime("%Y-%m-%d %H:%M")
        if timestamp is not None
        else "timestamp:unknown"
    )

    source_thread_id = meta.get("source_thread_id")
    thread_id = source_thread_id if source_thread_id else meta.get("thread_id")
    thread_label = str(thread_id) if thread_id not in (None, "") else "unknown"

    turn_index = meta.get("turn_index")
    try:
        turn_label = str(int(turn_index))
    except (TypeError, ValueError):
        turn_label = "?"

    role = meta.get("role") or item.get("role")
    if isinstance(role, str) and role.strip():
        role_label = role.strip()
    else:
        role_label = "role:unknown"

    return (
        f"- [{timestamp_label} | thread:{thread_label} | "
        f"turn:{turn_label} | {role_label}] {txt}"
    )


def build_context_system_message(
    bundle: Optional[Dict[str, Any]],
) -> Optional[str]:
    """
    Build a system message with concrete context from the ContextBroker bundle.
    """
    if not bundle:
        return None

    context_parts = []

    if bundle.get("semantic"):
        sem_parts = []
        for item in bundle["semantic"]:
            snippet = (
                item.get("content")
                or item.get("snippet")
                or item.get("text")
                or ""
            )
            if snippet:
                sem_parts.append(f"- {snippet}")
        if sem_parts:
            context_parts.append(
                "**Semantic Context:**\n" + "\n".join(sem_parts)
            )

    if bundle.get("memory"):
        mem_parts = []
        for item in bundle["memory"]:
            anchor_line = _format_memory_anchor(item)
            if anchor_line:
                mem_parts.append(anchor_line)
        if mem_parts:
            context_parts.append("**Memory Context:**\n" + "\n".join(mem_parts))

    if bundle.get("graph"):
        graph_parts = []
        for item in bundle["graph"]:
            txt = item.get("text") or item.get("content") or ""
            if txt:
                graph_parts.append(f"- {txt}")
        if graph_parts:
            context_parts.append(
                "**Graph Context:**\n" + "\n".join(graph_parts)
            )

    if bundle.get("federated"):
        federated_parts = []
        for item in bundle["federated"]:
            txt = (
                item.get("text")
                or item.get("content")
                or item.get("snippet")
                or ""
            )
            if txt:
                federated_parts.append(f"- {txt}")
        if federated_parts:
            context_parts.append(
                "**Federated Context:**\n" + "\n".join(federated_parts)
            )

    if bundle.get("sensors"):
        sensor_info = []
        sensors = bundle["sensors"]
        if sensors.get("timestamp"):
            sensor_info.append(f"Timestamp: {sensors['timestamp']}")
        if sensors.get("thread_count") is not None:
            sensor_info.append(f"Active Threads: {sensors['thread_count']}")
        if sensor_info:
            context_parts.append("**System State:**\n" + "\n".join(sensor_info))

    if not context_parts:
        return None

    return "You have access to the following context:\n\n" + "\n\n".join(
        context_parts
    )


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
    "build_context_system_message",
    "get_guardian_system_prompt",
]
