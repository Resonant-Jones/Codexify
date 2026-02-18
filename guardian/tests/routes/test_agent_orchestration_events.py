from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import CheckConstraint

from guardian.agents.events import AgentEventPublisher
from guardian.agents.store import AgentStore
from guardian.db.models import AgentEvent, AgentRun
from guardian.routes import agent_orchestration
from guardian.workers.agent_worker import (
    AttemptEvaluation,
    process_mutating_step,
)


class _SessionContext:
    def __init__(self, session: _FakeSession) -> None:
        self._session = session

    def __enter__(self) -> _FakeSession:
        return self._session

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> Literal[False]:
        return False


class _FakeRunRow:
    def __init__(self, run_id: str, db_id: int) -> None:
        self.run_id = run_id
        self.id = db_id


class _FakeQuery:
    def __init__(self, model: Any, session: _FakeSession) -> None:
        self._model = model
        self._session = session
        self._filter: dict[str, Any] = {}

    def filter_by(self, **kwargs: Any) -> _FakeQuery:
        self._filter = dict(kwargs)
        return self

    def first(self) -> Any | None:
        if self._model is AgentRun:
            run_id = self._filter.get("run_id")
            return self._session.run_rows.get(run_id)
        return None


class _FakeSession:
    def __init__(
        self, run_rows: dict[str, _FakeRunRow], added: list[Any]
    ) -> None:
        self.run_rows = run_rows
        self.added = added

    def query(self, model: Any) -> _FakeQuery:
        return _FakeQuery(model, self)

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    def commit(self) -> None:
        return


class _FakeDB:
    def __init__(self) -> None:
        self.added: list[Any] = []
        self.run_rows: dict[str, _FakeRunRow] = {
            "run-123": _FakeRunRow(run_id="run-123", db_id=101)
        }

    def get_session(self) -> _SessionContext:
        return _SessionContext(_FakeSession(self.run_rows, self.added))


def _build_client() -> TestClient:
    app = FastAPI()
    app.include_router(agent_orchestration.router)
    app.include_router(agent_orchestration.chat_router)
    return TestClient(app)


def test_escalation_persists_and_streams_event(monkeypatch) -> None:
    published: list[tuple[str, str, dict[str, Any]]] = []

    def fake_publish(
        task_id: str,
        event_type: str,
        data: dict[str, Any] | None = None,
    ) -> str:
        published.append((task_id, event_type, dict(data or {})))
        return "1-0"

    monkeypatch.setattr(
        "guardian.agents.events.task_events.publish", fake_publish
    )

    telemetry_store = AgentStore()
    event_publisher = AgentEventPublisher()
    deployment = telemetry_store.create_deployment(
        flow_id="flow-1",
        thread_id=7,
        spec_json={"steps": []},
        spec_hash="spec-hash",
    )
    run = telemetry_store.create_run(
        deployment_id=str(deployment["deployment_id"]),
        thread_id=7,
        status="running",
    )

    def executor(_attempt_index: int) -> AttemptEvaluation:
        return AttemptEvaluation(
            schema_valid=True,
            tests_passed=True,
            spec_alignment_ok=False,
            fail_count=0,
            fail_signature="spec-mismatch",
            diff_added=0,
            diff_deleted=0,
            error_category="spec_alignment_violation",
        )

    result = process_mutating_step(
        deployment_id=str(deployment["deployment_id"]),
        run_id=str(run["run_id"]),
        step_index=1,
        step_id="step-1",
        primitive="mutate",
        worktree_path="/tmp/worktree",
        attempt_executor=executor,
        telemetry_store=telemetry_store,
        event_publisher=event_publisher,
    )

    assert result.status == "escalated"
    escalations = telemetry_store.list_escalations(run_id=str(run["run_id"]))
    assert len(escalations) == 1
    assert escalations[0]["reason_code"] == "spec_alignment_violation"
    assert any(event_type == "escalated" for _, event_type, _ in published)


def test_agent_event_publisher_persists_agent_event_rows(monkeypatch) -> None:
    monkeypatch.setattr(
        "guardian.agents.events.task_events.publish",
        lambda *_args, **_kwargs: "1-0",
    )
    fake_db = _FakeDB()
    event_publisher = AgentEventPublisher(db=fake_db)

    event_publisher.emit(
        run_id="run-123",
        event_type="succeeded",
        payload={"step_index": 3},
    )

    assert len(fake_db.added) == 1
    row = fake_db.added[0]
    assert isinstance(row, AgentEvent)
    assert row.run_id == 101
    assert row.event_type == "succeeded"
    assert row.payload_json == {"step_index": 3}


class _FakeRequest:
    def __init__(self, disconnect_after: int = 2) -> None:
        self._checks = 0
        self._disconnect_after = disconnect_after

    async def is_disconnected(self) -> bool:
        self._checks += 1
        return self._checks > self._disconnect_after


@pytest.mark.asyncio
async def test_agent_run_events_sse_streams_terminal_events(
    monkeypatch,
) -> None:
    batches: list[list[tuple[str, dict[str, Any]]]] = [
        [
            ("1-1", {"type": "escalated", "data": {"reason": "x"}}),
            ("1-2", {"type": "failed", "data": {"reason": "y"}}),
            ("1-3", {"type": "succeeded", "data": {"reason": "z"}}),
        ],
        [],
    ]

    def fake_read_events(
        _task_id: str,
        _last_id: str,
        *,
        block_ms: int = 15000,
        count: int = 100,
    ) -> list[tuple[str, dict[str, Any]]]:
        _ = block_ms, count
        if batches:
            return batches.pop(0)
        return []

    monkeypatch.setattr(
        agent_orchestration.task_events,
        "read_events",
        fake_read_events,
    )

    response = await agent_orchestration.stream_run_events(
        request=_FakeRequest(disconnect_after=2),
        run_id="run-evt",
        last_id_query="0-0",
        last_event_id_header=None,
    )
    observed: list[str] = []
    buffer = ""

    async for chunk in response.body_iterator:
        text = (
            chunk.decode()
            if isinstance(chunk, (bytes, bytearray))
            else str(chunk)
        )
        buffer += text
        while "\n\n" in buffer:
            frame, buffer = buffer.split("\n\n", 1)
            if (
                not frame.strip()
                or frame.startswith("retry:")
                or frame.startswith(": ping")
            ):
                continue
            lines = frame.splitlines()
            event_line = next(
                (line for line in lines if line.startswith("event:")),
                None,
            )
            data_line = next(
                (line for line in lines if line.startswith("data:")),
                None,
            )
            if event_line is None or data_line is None:
                continue
            observed.append(event_line.split(":", 1)[1].strip())
            _ = json.loads(data_line.split(":", 1)[1].strip() or "{}")

    assert "escalated" in observed
    assert "failed" in observed
    assert "succeeded" in observed


def test_chat_thread_agent_runs_endpoint(monkeypatch) -> None:
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-key")

    local_store = AgentStore()
    local_publisher = AgentEventPublisher()
    monkeypatch.setattr(agent_orchestration, "_store", local_store)
    monkeypatch.setattr(
        agent_orchestration, "_event_publisher", local_publisher
    )

    deployment = local_store.create_deployment(
        flow_id="flow-thread",
        thread_id=77,
        spec_json={},
        spec_hash="spec-thread",
    )
    run = local_store.create_run(
        deployment_id=str(deployment["deployment_id"]),
        thread_id=77,
        status="running",
    )

    client = _build_client()
    response = client.get(
        "/api/chat/77/agent-runs",
        headers={"X-API-Key": "test-key"},
    )

    assert response.status_code == 200
    payload = response.json()
    run_ids = [item["run_id"] for item in payload["runs"]]
    assert str(run["run_id"]) in run_ids


def test_start_run_terminal_runtime_target_is_persisted_and_emitted(
    monkeypatch,
) -> None:
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-key")

    published: list[tuple[str, str, dict[str, Any]]] = []

    def fake_publish(
        task_id: str,
        event_type: str,
        data: dict[str, Any] | None = None,
    ) -> str:
        published.append((task_id, event_type, dict(data or {})))
        return "1-0"

    monkeypatch.setattr(
        "guardian.agents.events.task_events.publish",
        fake_publish,
    )

    local_store = AgentStore()
    local_publisher = AgentEventPublisher()
    monkeypatch.setattr(agent_orchestration, "_store", local_store)
    monkeypatch.setattr(
        agent_orchestration, "_event_publisher", local_publisher
    )

    client = _build_client()
    deploy_response = client.post(
        "/api/agents/deployments",
        json={"flow_id": "flow-terminal", "thread_id": 91, "spec": {}},
        headers={"X-API-Key": "test-key"},
    )
    assert deploy_response.status_code == 200
    deployment_id = deploy_response.json()["deployment"]["deployment_id"]

    run_response = client.post(
        f"/api/agents/deployments/{deployment_id}/runs",
        json={"runtime_target": "terminal", "supervised": True},
        headers={"X-API-Key": "test-key"},
    )
    assert run_response.status_code == 200
    payload = run_response.json()
    assert payload["ok"] is True
    assert payload["run"]["runtime_target"] == "terminal"

    run_id = payload["run"]["run_id"]
    stored_run = local_store.get_run(run_id)
    assert stored_run is not None
    assert stored_run["runtime_target"] == "terminal"

    run_events = [
        (event_type, data)
        for task_id, event_type, data in published
        if task_id == run_id and event_type in {"created", "started"}
    ]
    assert len(run_events) == 2
    expected = {
        "deployment_id": deployment_id,
        "run_id": run_id,
        "runtime_target": "terminal",
    }
    assert dict(run_events)["created"] == expected
    assert dict(run_events)["started"] == expected


def test_start_run_rejects_invalid_runtime_target(monkeypatch) -> None:
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-key")

    published: list[tuple[str, str, dict[str, Any]]] = []

    def fake_publish(
        task_id: str,
        event_type: str,
        data: dict[str, Any] | None = None,
    ) -> str:
        published.append((task_id, event_type, dict(data or {})))
        return "1-0"

    monkeypatch.setattr(
        "guardian.agents.events.task_events.publish",
        fake_publish,
    )

    local_store = AgentStore()
    local_publisher = AgentEventPublisher()
    monkeypatch.setattr(agent_orchestration, "_store", local_store)
    monkeypatch.setattr(
        agent_orchestration, "_event_publisher", local_publisher
    )

    client = _build_client()
    deploy_response = client.post(
        "/api/agents/deployments",
        json={"flow_id": "flow-invalid-target", "thread_id": 92, "spec": {}},
        headers={"X-API-Key": "test-key"},
    )
    assert deploy_response.status_code == 200
    deployment_id = deploy_response.json()["deployment"]["deployment_id"]

    run_response = client.post(
        f"/api/agents/deployments/{deployment_id}/runs",
        json={"runtime_target": "host"},
        headers={"X-API-Key": "test-key"},
    )

    assert run_response.status_code == 400
    assert run_response.json() == {"detail": "invalid_runtime_target"}
    assert local_store.list_runs_for_thread(92) == []
    assert published == []


def test_runtime_target_route_allowlist_matches_agent_run_constraint() -> None:
    route_targets = set(agent_orchestration.ALLOWED_RUNTIME_TARGETS)
    runtime_check = next(
        constraint
        for constraint in AgentRun.__table__.constraints
        if isinstance(constraint, CheckConstraint)
        and constraint.name == "agent_runs_runtime_target_check"
    )
    sql = str(runtime_check.sqltext)
    values = {
        token.strip().strip("'")
        for token in sql.partition("(")[2].rstrip(")").split(",")
    }
    assert route_targets == values


def test_agent_run_migration_runtime_target_constraint_includes_terminal() -> (
    None
):
    migration_path = (
        Path(__file__).resolve().parents[2]
        / "db"
        / "migrations"
        / "versions"
        / "9f3d2b1a7c4e_add_agent_orchestration_tables.py"
    )
    text = migration_path.read_text(encoding="utf-8")
    assert "runtime_target IN ('container', 'terminal')" in text
