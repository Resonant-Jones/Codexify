"""Persistence helpers for command bus runs and events."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from guardian.db.models import CommandRun, CommandRunEvent

TERMINAL_STATUSES = {"completed", "failed", "blocked"}


class IdempotencyConflictError(RuntimeError):
    """Raised when create_run hits an idempotency uniqueness race."""

    def __init__(self, existing_run: dict[str, Any]) -> None:
        super().__init__("idempotency_conflict")
        self.existing_run = existing_run


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CommandBusStore:
    """Store command runs/events in DB with in-memory fallback for tests."""

    def __init__(self, db: Any | None = None) -> None:
        self._db = db
        self._mem_runs: dict[str, dict[str, Any]] = {}
        self._mem_events: dict[str, list[dict[str, Any]]] = {}
        self._mem_idempotency_index: dict[tuple[str, str], str] = {}

    def configure_db(self, db: Any | None) -> None:
        self._db = db

    def _has_db(self) -> bool:
        return bool(self._db is not None and hasattr(self._db, "get_session"))

    def create_run(
        self,
        *,
        command_id: str,
        status: str,
        actor_kind: str,
        actor_id: str,
        actor_session_id: str | None,
        delegated_by: str | None,
        auth_subject: str,
        invoke_version: str,
        idempotency_key: str | None,
        args_hash: str,
        args_redacted: dict[str, Any],
    ) -> dict[str, Any]:
        run_id = f"run_{uuid4().hex[:16]}"
        now = _utc_now()

        if self._has_db():
            with self._db.get_session() as session:
                row = CommandRun(
                    run_id=run_id,
                    command_id=command_id,
                    status=status,
                    actor_kind=actor_kind,
                    actor_id=actor_id,
                    actor_session_id=actor_session_id,
                    delegated_by=delegated_by,
                    auth_subject=auth_subject,
                    invoke_version=invoke_version,
                    idempotency_key=idempotency_key,
                    args_hash=args_hash,
                    args_redacted=args_redacted,
                    created_at=now,
                )
                try:
                    session.add(row)
                    session.commit()
                except IntegrityError as exc:
                    session.rollback()
                    if idempotency_key:
                        existing_row = (
                            session.query(CommandRun)
                            .filter_by(
                                command_id=command_id,
                                idempotency_key=idempotency_key,
                            )
                            .first()
                        )
                        if existing_row is not None:
                            raise IdempotencyConflictError(
                                self._row_to_dict(existing_row)
                            ) from exc
                    raise

            return {
                "run_id": run_id,
                "command_id": command_id,
                "status": status,
                "idempotency_key": idempotency_key,
                "args_hash": args_hash,
                "args_redacted": args_redacted,
            }

        if idempotency_key:
            existing_run_id = self._mem_idempotency_index.get(
                (command_id, idempotency_key)
            )
            if existing_run_id is not None:
                existing_run = self._mem_runs.get(existing_run_id)
                if existing_run is not None:
                    raise IdempotencyConflictError(dict(existing_run))

        run = {
            "run_id": run_id,
            "command_id": command_id,
            "status": status,
            "actor_kind": actor_kind,
            "actor_id": actor_id,
            "actor_session_id": actor_session_id,
            "delegated_by": delegated_by,
            "auth_subject": auth_subject,
            "invoke_version": invoke_version,
            "idempotency_key": idempotency_key,
            "args_hash": args_hash,
            "args_redacted": args_redacted,
            "result_json": None,
            "error_text": None,
            "created_at": now.isoformat(),
            "started_at": None,
            "ended_at": None,
        }
        self._mem_runs[run_id] = run
        self._mem_events.setdefault(run_id, [])
        if idempotency_key:
            self._mem_idempotency_index[(command_id, idempotency_key)] = run_id
        return dict(run)

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        if self._has_db():
            with self._db.get_session() as session:
                row = session.query(CommandRun).filter_by(run_id=run_id).first()
                if row is None:
                    return None
                return self._row_to_dict(row)
        run = self._mem_runs.get(run_id)
        return dict(run) if run is not None else None

    def get_run_by_idempotency_key(
        self,
        command_id: str,
        idempotency_key: str,
    ) -> dict[str, Any] | None:
        key = str(idempotency_key or "").strip()
        if not key:
            return None

        if self._has_db():
            with self._db.get_session() as session:
                row = (
                    session.query(CommandRun)
                    .filter_by(command_id=command_id, idempotency_key=key)
                    .first()
                )
                if row is None:
                    return None
                return self._row_to_dict(row)

        existing_run_id = self._mem_idempotency_index.get((command_id, key))
        if existing_run_id is not None:
            run = self._mem_runs.get(existing_run_id)
            return dict(run) if run is not None else None

        for run in self._mem_runs.values():
            if (
                run.get("command_id") == command_id
                and run.get("idempotency_key") == key
            ):
                return dict(run)
        return None

    def append_event(
        self, *, run_id: str, event_type: str, payload: dict[str, Any]
    ) -> int:
        now = _utc_now()
        if self._has_db():
            with self._db.get_session() as session:
                run_row = (
                    session.query(CommandRun)
                    .filter_by(run_id=run_id)
                    .with_for_update()
                    .first()
                )
                if run_row is None:
                    raise ValueError(f"run_id not found: {run_id}")
                max_seq = (
                    session.query(
                        func.coalesce(func.max(CommandRunEvent.sequence), 0)
                    )
                    .filter(CommandRunEvent.run_id == run_id)
                    .scalar()
                )
                next_seq = int(max_seq or 0) + 1
                row = CommandRunEvent(
                    run_id=run_id,
                    sequence=next_seq,
                    event_type=event_type,
                    payload_json=payload or {},
                    created_at=now,
                )
                session.add(row)
                session.commit()
                return next_seq

        events = self._mem_events.setdefault(run_id, [])
        next_seq = len(events) + 1
        events.append(
            {
                "run_id": run_id,
                "sequence": next_seq,
                "event_type": event_type,
                "payload_json": dict(payload or {}),
                "created_at": now.isoformat(),
            }
        )
        return next_seq

    def list_events_after(
        self, *, run_id: str, after_seq: int, limit: int = 100
    ) -> list[dict[str, Any]]:
        if self._has_db():
            with self._db.get_session() as session:
                rows = (
                    session.query(CommandRunEvent)
                    .filter(
                        CommandRunEvent.run_id == run_id,
                        CommandRunEvent.sequence > max(after_seq, 0),
                    )
                    .order_by(CommandRunEvent.sequence.asc())
                    .limit(limit)
                    .all()
                )
                return [
                    {
                        "run_id": row.run_id,
                        "sequence": row.sequence,
                        "event_type": row.event_type,
                        "payload_json": row.payload_json or {},
                        "created_at": row.created_at.isoformat()
                        if row.created_at
                        else None,
                    }
                    for row in rows
                ]

        rows = [
            event
            for event in self._mem_events.get(run_id, [])
            if int(event.get("sequence") or 0) > max(after_seq, 0)
        ]
        rows.sort(key=lambda item: int(item.get("sequence") or 0))
        return [dict(item) for item in rows[:limit]]

    def update_run(
        self,
        *,
        run_id: str,
        status: str,
        result_json: dict[str, Any] | None = None,
        error_text: str | None = None,
    ) -> None:
        now = _utc_now()
        if self._has_db():
            with self._db.get_session() as session:
                row = session.query(CommandRun).filter_by(run_id=run_id).first()
                if row is None:
                    raise ValueError(f"run_id not found: {run_id}")
                row.status = status
                if row.started_at is None and status in {"running"}:
                    row.started_at = now
                if status in TERMINAL_STATUSES:
                    row.ended_at = now
                    if row.started_at is None:
                        row.started_at = now
                if result_json is not None:
                    row.result_json = result_json
                if error_text is not None:
                    row.error_text = error_text
                session.commit()
                return

        run = self._mem_runs.get(run_id)
        if run is None:
            raise ValueError(f"run_id not found: {run_id}")
        run["status"] = status
        if run.get("started_at") is None and status in {"running"}:
            run["started_at"] = now.isoformat()
        if status in TERMINAL_STATUSES:
            if run.get("started_at") is None:
                run["started_at"] = now.isoformat()
            run["ended_at"] = now.isoformat()
        if result_json is not None:
            run["result_json"] = result_json
        if error_text is not None:
            run["error_text"] = error_text

    @staticmethod
    def _row_to_dict(row: CommandRun) -> dict[str, Any]:
        return {
            "run_id": row.run_id,
            "command_id": row.command_id,
            "status": row.status,
            "actor_kind": row.actor_kind,
            "actor_id": row.actor_id,
            "actor_session_id": row.actor_session_id,
            "delegated_by": row.delegated_by,
            "auth_subject": row.auth_subject,
            "invoke_version": row.invoke_version,
            "idempotency_key": row.idempotency_key,
            "args_hash": row.args_hash,
            "args_redacted": row.args_redacted or {},
            "result_json": row.result_json,
            "error_text": row.error_text,
            "created_at": row.created_at.isoformat()
            if row.created_at
            else None,
            "started_at": row.started_at.isoformat()
            if row.started_at
            else None,
            "ended_at": row.ended_at.isoformat() if row.ended_at else None,
        }
