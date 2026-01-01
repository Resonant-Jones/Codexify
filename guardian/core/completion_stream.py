"""Canonical completion streaming contract for Codexify.

CompletionStream is transport-agnostic. It emits events into the durable event
bus so SSE (/api/events), in-process loops, and workers share one contract.

Event types (topics):
  - completion.started: completion accepted/queued
  - completion.delta: token-level updates
  - completion.done: terminal success
  - completion.error: terminal error
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from guardian.core import event_bus

COMPLETION_STARTED = "completion.started"
COMPLETION_DELTA = "completion.delta"
COMPLETION_DONE = "completion.done"
COMPLETION_ERROR = "completion.error"


@dataclass
class CompletionStream:
    thread_id: int
    task_id: str
    provider: str | None = None
    model: str | None = None

    def _base_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "thread_id": self.thread_id,
            "task_id": self.task_id,
        }
        if self.provider:
            payload["provider"] = self.provider
        if self.model:
            payload["model"] = self.model
        return payload

    def emit_started(self) -> None:
        payload = self._base_payload()
        event_bus.emit_event(COMPLETION_STARTED, payload)

    def emit_delta(self, token: str, *, index: int | None = None) -> None:
        if not token:
            return
        payload = self._base_payload()
        payload["token"] = token
        if index is not None:
            payload["index"] = index
        event_bus.emit_event(COMPLETION_DELTA, payload)

    def emit_done(
        self,
        *,
        message_id: int | None = None,
        content: str | None = None,
    ) -> None:
        payload = self._base_payload()
        if message_id is not None:
            payload["message_id"] = message_id
        if content is not None:
            payload["content"] = content
        event_bus.emit_event(COMPLETION_DONE, payload)

    def emit_error(self, error: str) -> None:
        payload = self._base_payload()
        payload["error"] = error
        event_bus.emit_event(COMPLETION_ERROR, payload)
