"""Agent event publisher with durable DB persistence + SSE stream fanout."""

from __future__ import annotations

import logging
from typing import Any

from guardian.db.models import AgentEvent, AgentRun
from guardian.queue import task_events

logger = logging.getLogger(__name__)


class AgentEventPublisher:
    """Persist agent events and publish them on existing task event streams."""

    def __init__(self, db: Any | None = None) -> None:
        self._db = db
        self._mem_events: list[dict[str, Any]] = []

    def configure_db(self, db: Any | None) -> None:
        self._db = db

    def emit(
        self,
        *,
        run_id: str,
        event_type: str,
        payload: dict[str, Any] | None = None,
        run_step_id: int | None = None,
        attempt_id: int | None = None,
    ) -> None:
        safe_payload = dict(payload or {})
        self._mem_events.append(
            {
                "run_id": run_id,
                "event_type": event_type,
                "payload": safe_payload,
            }
        )

        # Stream fanout for existing `/api/tasks/{task_id}/events` compatibility.
        try:
            task_events.publish(run_id, event_type, safe_payload)
        except Exception as exc:
            logger.warning("[agent-events] stream publish failed: %s", exc)

        db = self._db
        if db is None or not hasattr(db, "get_session"):
            return

        try:
            with db.get_session() as session:
                run_row = (
                    session.query(AgentRun).filter_by(run_id=run_id).first()
                )
                if run_row is None:
                    return
                row = AgentEvent(
                    run_id=run_row.id,
                    run_step_id=run_step_id,
                    attempt_id=attempt_id,
                    event_type=event_type,
                    payload_json=safe_payload,
                )
                session.add(row)
                session.commit()
        except Exception as exc:
            logger.warning("[agent-events] durable write failed: %s", exc)

    def list_events(self, run_id: str | None = None) -> list[dict[str, Any]]:
        if run_id is None:
            return list(self._mem_events)
        return [
            event for event in self._mem_events if event.get("run_id") == run_id
        ]


publisher = AgentEventPublisher()


__all__ = ["AgentEventPublisher", "publisher"]
