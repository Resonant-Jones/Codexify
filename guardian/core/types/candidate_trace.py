from __future__ import annotations

from typing import Any, TypedDict


class CandidateTrace(TypedDict):
    thread_id: str
    request_id: str
    candidates: list[dict[str, Any]]
    selection_strategy: str
    created_at: str
