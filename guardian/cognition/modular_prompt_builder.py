"""Deterministic modular system prompt assembly with token metadata."""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Any

SEGMENT_ORDER: tuple[str, ...] = (
    "base",
    "imprint",
    "persona",
    "system_docs",
    "scratchpad",
)

SEGMENT_HEADERS: dict[str, str] = {
    "base": "=== BASE SYSTEM ===",
    "imprint": "=== IMPRINT_ZERO ===",
    "persona": "=== PERSONA ===",
    "system_docs": "=== SYSTEM DOCS ===",
    "scratchpad": "=== SCRATCHPAD ===",
}


@dataclass(frozen=True)
class PromptBudgets:
    imprint_max_tokens: int | None = None
    system_docs_max_tokens: int | None = None
    total_max_tokens: int | None = None


def estimate_tokens(text: str) -> int:
    """Conservative token estimate using repo-standard fallback heuristic."""
    if not text:
        return 0
    return max(1, ceil(len(text) / 4))


def _coerce_budgets(
    budgets: PromptBudgets | dict[str, Any] | None,
) -> PromptBudgets:
    if budgets is None:
        return PromptBudgets()
    if isinstance(budgets, PromptBudgets):
        return budgets
    payload = dict(budgets)
    return PromptBudgets(
        imprint_max_tokens=payload.get("imprint_max_tokens"),
        system_docs_max_tokens=payload.get("system_docs_max_tokens"),
        total_max_tokens=payload.get("total_max_tokens"),
    )


def _truncate_to_token_budget(
    text: str, max_tokens: int | None
) -> tuple[str, bool]:
    if max_tokens is None:
        return text, False
    safe_budget = max(0, int(max_tokens))
    if estimate_tokens(text) <= safe_budget:
        return text, False

    max_chars = safe_budget * 4
    marker = "\n[TRUNCATED DUE TO TOKEN BUDGET]"
    if max_chars <= 0:
        return "", True
    if max_chars <= len(marker):
        return marker[:max_chars], True
    return text[: max_chars - len(marker)].rstrip() + marker, True


def build_system_prompt(
    *,
    base_system_prompt: str,
    imprint_block: str | None = None,
    persona_block: str | None = None,
    system_docs_block: str | None = None,
    scratchpad_block: str | None = None,
    budgets: PromptBudgets | dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any]]:
    """Assemble a single system prompt string with deterministic segment metadata."""

    if (
        not isinstance(base_system_prompt, str)
        or not base_system_prompt.strip()
    ):
        raise ValueError("base_system_prompt is required")

    effective_budgets = _coerce_budgets(budgets)
    raw_segments: dict[str, str] = {
        "base": base_system_prompt.strip(),
        "imprint": (imprint_block or "").strip(),
        "persona": (persona_block or "").strip(),
        "system_docs": (system_docs_block or "").strip(),
        "scratchpad": (scratchpad_block or "").strip(),
    }

    truncation_notes: list[str] = []
    truncated_flags = {name: False for name in SEGMENT_ORDER}

    capped_segments = dict(raw_segments)
    for name, max_tokens in (
        ("imprint", effective_budgets.imprint_max_tokens),
        ("system_docs", effective_budgets.system_docs_max_tokens),
    ):
        if not capped_segments[name]:
            continue
        updated, truncated = _truncate_to_token_budget(
            capped_segments[name], max_tokens
        )
        capped_segments[name] = updated
        truncated_flags[name] = truncated_flags[name] or truncated
        if truncated:
            truncation_notes.append(
                f"{name} segment truncated to {max_tokens} tokens"
            )

    if effective_budgets.total_max_tokens is not None:
        total_budget = max(0, int(effective_budgets.total_max_tokens))
        consumed = 0
        for name in SEGMENT_ORDER:
            text = capped_segments[name]
            if not text:
                continue
            segment_tokens = estimate_tokens(text)
            remaining = total_budget - consumed
            if remaining <= 0:
                capped_segments[name] = ""
                truncated_flags[name] = True
                truncation_notes.append(
                    f"{name} segment removed by total_max_tokens budget"
                )
                continue
            if segment_tokens > remaining:
                updated, _ = _truncate_to_token_budget(text, remaining)
                capped_segments[name] = updated
                truncated_flags[name] = True
                truncation_notes.append(
                    f"{name} segment truncated by total_max_tokens budget"
                )
                consumed = total_budget
                continue
            consumed += segment_tokens

    prompt_chunks: list[str] = []
    segment_meta: list[dict[str, Any]] = []

    for name in SEGMENT_ORDER:
        text = capped_segments[name]
        if text:
            prompt_chunks.append(f"{SEGMENT_HEADERS[name]}\n{text}")
        segment_meta.append(
            {
                "name": name,
                "chars": len(text),
                "estimated_tokens": estimate_tokens(text),
                "truncated": bool(truncated_flags[name]),
            }
        )

    system_prompt = "\n\n".join(prompt_chunks).strip()
    estimated_total = sum(s["estimated_tokens"] for s in segment_meta)
    meta = {
        "estimated_tokens_total": estimated_total,
        "segments": segment_meta,
        "truncation_notes": truncation_notes,
    }
    return system_prompt, meta


__all__ = [
    "PromptBudgets",
    "SEGMENT_HEADERS",
    "SEGMENT_ORDER",
    "build_system_prompt",
    "estimate_tokens",
]
