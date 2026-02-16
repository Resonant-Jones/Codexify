"""Identity modeling policy helpers for diary and depth gating."""

from __future__ import annotations

from typing import Any, Mapping


def normalize_identity_depth(value: Any) -> str:
    depth = str(value or "light").strip().lower()
    return "deep" if depth == "deep" else "light"


def thread_blocks_identity_modeling(
    thread: Mapping[str, Any] | None,
) -> bool:
    if not thread:
        return False
    diary_mode = bool(thread.get("diary_mode") or thread.get("is_diary"))
    modeling_excluded = bool(
        thread.get("modeling_excluded") or thread.get("exclude_from_identity")
    )
    return diary_mode or modeling_excluded


def can_run_deep_identity_modeling(identity_depth: Any) -> bool:
    return normalize_identity_depth(identity_depth) == "deep"


__all__ = [
    "can_run_deep_identity_modeling",
    "normalize_identity_depth",
    "thread_blocks_identity_modeling",
]
