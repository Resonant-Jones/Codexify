"""Groundedness evaluator for post-completion inspection."""

from __future__ import annotations

import re
from typing import Any

_SENTENCE_SPLIT_RE = re.compile(r"[.!?\n]+")
_WHITESPACE_RE = re.compile(r"\s+")
_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _normalize_text(value: str) -> str:
    tokens = _TOKEN_RE.findall(value.lower())
    return " ".join(tokens)


def _stringify_evidence(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        cleaned = value.strip()
        return [cleaned] if cleaned else []
    if isinstance(value, dict):
        items: list[str] = []
        for key, item in value.items():
            if key in {
                "assistant_output_text",
                "assistant_text",
                "output",
                "final_output",
            }:
                continue
            items.extend(_stringify_evidence(item))
        return items
    if isinstance(value, (list, tuple, set)):
        items: list[str] = []
        for item in value:
            items.extend(_stringify_evidence(item))
        return items
    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat):
        try:
            rendered = isoformat()
        except Exception:
            rendered = ""
        return [rendered] if rendered else []
    rendered = str(value).strip()
    return [rendered] if rendered else []


def _collect_support_text(trace_snapshot: dict[str, Any]) -> str:
    trace = trace_snapshot.get("trace_json")
    if not isinstance(trace, dict):
        trace = trace_snapshot.get("trace")
    fragments: list[str] = []
    if isinstance(trace, dict):
        for key in (
            "messages",
            "retrieved_context",
            "documents",
            "semantic",
            "obsidian",
            "memory",
            "graph",
        ):
            fragments.extend(_stringify_evidence(trace.get(key)))
    fragments.extend(
        _stringify_evidence(
            trace_snapshot.get("retrieval_summary_json")
            or trace_snapshot.get("retrieval_summary")
        )
    )
    fragments.extend(_stringify_evidence(trace_snapshot.get("payload_summary")))
    return "\n".join(fragments)


def _split_sentences(text: str) -> list[str]:
    sentences = []
    for sentence in _SENTENCE_SPLIT_RE.split(text):
        cleaned = _WHITESPACE_RE.sub(" ", sentence).strip()
        if cleaned:
            sentences.append(cleaned)
    return sentences


def evaluate_groundedness(trace_snapshot: dict[str, Any]) -> dict[str, Any]:
    """Return a deterministic groundedness verdict for one snapshot."""

    assistant_text = str(
        trace_snapshot.get("assistant_output_text")
        or trace_snapshot.get("assistant_text")
        or ""
    ).strip()
    support_text = _collect_support_text(trace_snapshot)
    normalized_support = _normalize_text(support_text)

    sentences = _split_sentences(assistant_text)
    supported_sentences: list[str] = []
    unsupported_sentences: list[str] = []
    for sentence in sentences:
        normalized_sentence = _normalize_text(sentence)
        if not normalized_sentence:
            continue
        if normalized_sentence in normalized_support:
            supported_sentences.append(sentence)
        else:
            unsupported_sentences.append(sentence)

    if not assistant_text:
        score = 0.0
        label = "ungrounded"
        reason = "Assistant output was empty."
    elif unsupported_sentences:
        score = 0.0
        label = "ungrounded"
        reason = f"Unsupported claim: {unsupported_sentences[0]}"
    else:
        score = 1.0
        label = "grounded"
        reason = "Assistant output is supported by the persisted trace context."

    return {
        "evaluator_kind": "code",
        "evaluator_name": "groundedness_basic",
        "score": score,
        "label": label,
        "status": "succeeded",
        "reason": reason,
        "structured_findings_json": {
            "supported_sentence_count": len(supported_sentences),
            "unsupported_sentence_count": len(unsupported_sentences),
            "supported_sentences": supported_sentences,
            "unsupported_sentences": unsupported_sentences,
        },
    }
