from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Literal

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import CheckConstraint

from guardian.agents.coding_agent_contracts import (
    CodingAgentPermissionPolicy,
    CodingAgentTaskEnvelope,
)
from guardian.agents.events import AgentEventPublisher
from guardian.agents.store import AgentStore
from guardian.core.auth import ACCOUNT_SESSION_PURPOSE, issue_session_token
from guardian.core.session_store import get_session_store
from guardian.db.models import AgentEvent, AgentRun
from guardian.routes import agent_orchestration
from guardian.tasks.types import CodingExecutionTask
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
    app.dependency_overrides[agent_orchestration.get_current_user] = (
        lambda: "local-user"
    )
    return TestClient(app)


def _build_identity_client() -> TestClient:
    """Build a client that resolves the principal through the real
    authentication dependencies instead of an override."""
    app = FastAPI()
    app.include_router(agent_orchestration.router)
    app.include_router(agent_orchestration.chat_router)
    return TestClient(app)


def _account_session_headers(email: str) -> dict[str, str]:
    """Issue a real account-session credential for the given subject."""
    token, _ = issue_session_token(
        subject=email,
        ttl_seconds=60,
        purpose=ACCOUNT_SESSION_PURPOSE,
    )
    get_session_store().store(token, email, 60)
    return {"Authorization": f"Bearer {token}"}


def _remote_account_env(monkeypatch) -> None:
    """Put the process in the remote account boundary."""
    monkeypatch.setenv("CODEXIFY_DISABLE_DOTENV", "1")
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-key")
    monkeypatch.setenv("GUARDIAN_SESSION_SECRET", "test-session-secret")
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "remote")
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "local_safe")


class _AccountScopedStoreSpy:
    """Route-wiring spy for the account-scoped readback store methods.

    It records the identity each readback handler supplies and applies the
    same ownership rule the real AgentStore applies: only the owning account
    may read the resource, and any other account is refused. This is route
    and authentication wiring proof. The durable ownership decision itself
    is owned by the real AgentStore and is proven separately by the
    PostgreSQL snapshot suite.
    """

    def __init__(self, owner: str) -> None:
        self.owner = owner
        self.calls: list[tuple[str, str | None]] = []
        self.run = {
            "run_id": "run-owned",
            "deployment_id": "dep-owned",
            "thread_id": 77,
            "status": "running",
            "runtime_target": "container",
        }
        self.snapshot = {
            "run_id": "run-owned",
            "deployment_id": "dep-owned",
            "thread_id": 77,
            "coding_task_id": "coding-owned",
            "status": "running",
        }

    def _owned(self, method: str, user_id: str | None) -> bool:
        resolved = str(user_id or "").strip()
        self.calls.append((method, resolved or None))
        return resolved == self.owner

    def get_account_run(self, run_id: str, *, user_id: str) -> dict[str, Any] | None:
        if not self._owned("get_account_run", user_id):
            return None
        return dict(self.run)

    def get_run(
        self, run_id: str, *, user_id: str | None = None
    ) -> dict[str, Any] | None:
        if not self._owned("get_run", user_id):
            return None
        return dict(self.run)

    def get_coding_run_snapshot(
        self, run_id: str, *, user_id: str | None = None
    ) -> dict[str, Any] | None:
        if not self._owned("get_coding_run_snapshot", user_id):
            return None
        return dict(self.snapshot)

    def list_account_runs_for_thread(
        self, thread_id: int, *, user_id: str
    ) -> list[dict[str, Any]] | None:
        if not self._owned("list_account_runs_for_thread", user_id):
            return None
        return [dict(self.run)]

    def list_coding_runs_for_thread(
        self, thread_id: int, *, user_id: str | None = None
    ) -> list[dict[str, Any]] | None:
        if not self._owned("list_coding_runs_for_thread", user_id):
            return None
        return [dict(self.snapshot)]


def _patch_readback_store(monkeypatch, store: Any) -> None:
    monkeypatch.setattr(agent_orchestration, "_store", store)
    monkeypatch.setattr(agent_orchestration, "_event_publisher", AgentEventPublisher())


def _patch_execution_authority(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        agent_orchestration,
        "_validate_coding_lineage",
        lambda *, account_id, thread_id, source_message_id, requested_project_id: (
            str(requested_project_id) if requested_project_id is not None else None
        ),
    )
    monkeypatch.setattr(
        agent_orchestration,
        "authorize_credential_selection",
        lambda _db, *, credential_ref, account_id, provider_id, model_id: {
            "credential_ref": credential_ref,
            "owner_scope": "account",
            "owner_id": account_id,
            "provider_id": provider_id,
            "credential_type": "api_key",
            "funding_route": "user_byok",
            "source_class": "account_api_key",
            "usage_policy_ref": None,
            # This sentinel stands in for secret-bearing custody data. The
            # binding builder must project only safe authority metadata.
            "api_key": "SECRET-SENTINEL-must-not-cross-the-task-boundary",
        },
    )


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


def test_chat_thread_agent_runs_rejects_memory_only_authority(monkeypatch) -> None:
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-key")

    local_store = AgentStore()
    local_publisher = AgentEventPublisher()
    monkeypatch.setattr(agent_orchestration, "_store", local_store)
    monkeypatch.setattr(agent_orchestration, "_event_publisher", local_publisher)

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

    assert response.status_code == 404
    assert str(run["run_id"]) not in response.text


def test_local_operator_can_read_threadless_agent_run(monkeypatch) -> None:
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-key")
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "local")
    monkeypatch.setattr(
        agent_orchestration.dependencies, "is_private_preview", lambda: False
    )
    local_store = AgentStore()
    monkeypatch.setattr(agent_orchestration, "_store", local_store)
    deployment = local_store.create_deployment(
        flow_id="operator-threadless",
        thread_id=None,
        spec_json={},
        spec_hash="operator-threadless-spec",
    )
    run = local_store.create_run(
        deployment_id=str(deployment["deployment_id"]),
        thread_id=None,
        status="running",
    )

    response = _build_client().get(
        f"/api/agents/runs/{run['run_id']}",
        headers={"X-API-Key": "test-key"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["run"]["run_id"] == run["run_id"]
    assert response.json()["run"]["thread_id"] is None


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


@pytest.mark.asyncio
async def test_execute_coding_task_preserves_source_thread_lineage(
    monkeypatch,
) -> None:
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-key")
    _patch_execution_authority(monkeypatch)

    captured_payloads: list[dict[str, Any]] = []
    local_store = AgentStore()
    local_publisher = AgentEventPublisher()
    monkeypatch.setattr(agent_orchestration, "_store", local_store)
    monkeypatch.setattr(
        agent_orchestration, "_event_publisher", local_publisher
    )
    monkeypatch.setattr(
        "guardian.queue.redis_queue.enqueue_coding_execution",
        lambda payload: captured_payloads.append(dict(payload)),
    )

    envelope = CodingAgentTaskEnvelope(
        coding_task_id="coding-task-123",
        thread_id="42",
        source_message_id="99",
        attempt_id="attempt-7",
        user_id="local-user",
        project_id="17",
        adapter_kind="pi_sdk",
        instructions="Patch the failing seam.",
        repo_root="/workspace/repo",
        context_summary="source thread summary",
        validation_command="pytest -q",
        max_validation_attempts=3,
        permission_policy=CodingAgentPermissionPolicy(
            allow_shell=True,
            allow_network=False,
            allow_write=True,
            allowed_paths=("/workspace/repo",),
            max_runtime_seconds=60,
        ),
        provider_id="test-provider",
        model_id="test-model-a",
        credential_ref="credential-account-a",
    )

    result = await agent_orchestration.execute_coding_task(
        envelope, current_user="local-user"
    )

    assert result["ok"] is True
    assert result["status"] == "accepted"
    assert result["source_thread_id"] == 42
    assert result["source_message_id"] == 99
    assert captured_payloads
    payload = captured_payloads[0]
    assert payload["thread_id"] == 42
    assert payload["source_thread_id"] == 42
    assert payload["source_message_id"] == 99
    assert payload["user_id"] == "local-user"
    assert payload["project_id"] == "17"
    assert payload["validation_command"] == "pytest -q"
    assert payload["max_validation_attempts"] == 3
    assert payload["permission_policy"]["allow_shell"] is True
    assert payload["execution_binding"]["provider_id"] == "test-provider"
    assert payload["execution_binding"]["model_id"] == "test-model-a"
    assert payload["execution_binding"]["credential_ref"] == "credential-account-a"
    serialized_payload = json.dumps(payload)
    assert "SECRET-SENTINEL-must-not-cross-the-task-boundary" not in serialized_payload
    assert "api_key" not in payload["execution_binding"]
    assert payload["worktree_lease_id"] is None
    assert payload["require_worktree_lease"] is False
    assert payload["commit_after_validation"] is False
    assert payload["commit_message"] is None
    assert payload["require_human_review_before_merge"] is True

    deployment = local_store.get_deployment(result["deployment_id"])
    assert deployment is not None
    assert deployment["thread_id"] == 42
    assert deployment["spec_json"]["adapter_kind"] == "pi_sdk"
    assert deployment["spec_json"]["validation_command"] == "pytest -q"
    assert deployment["spec_json"]["max_validation_attempts"] == 3
    assert deployment["spec_json"]["source_thread_id"] == 42
    assert deployment["spec_json"]["source_message_id"] == 99
    assert deployment["spec_json"]["user_id"] == "local-user"
    assert deployment["spec_json"]["execution_binding"] == payload["execution_binding"]
    assert deployment["spec_json"]["project_id"] == "17"
    assert deployment["spec_json"]["worktree_lease_id"] is None
    assert deployment["spec_json"]["require_worktree_lease"] is False
    assert deployment["spec_json"]["commit_after_validation"] is False
    assert deployment["spec_json"]["commit_message"] is None
    assert deployment["spec_json"]["require_human_review_before_merge"] is True


def test_internal_coding_snapshot_is_path_bounded_but_not_account_authority() -> None:
    local_store = AgentStore()
    deployment = local_store.create_deployment(
        flow_id="coding_snapshot",
        thread_id=42,
        spec_json={
            "coding_task_id": "coding-snapshot-1",
            "source_thread_id": 42,
            "source_message_id": 99,
            "attempt_id": "attempt-snapshot-1",
            "adapter_kind": "pi_codex_runner",
            "user_id": "alice",
            "project_id": "17",
        },
        spec_hash="snapshot-hash",
    )
    run = local_store.create_run(
        deployment_id=deployment["deployment_id"],
        thread_id=42,
        status="queued",
    )

    local_store.store_coding_result(
        run_id=run["run_id"],
        coding_task_id="coding-snapshot-1",
        attempt_id="attempt-snapshot-1",
        thread_id=42,
        source_message_id=99,
        result_status="failed",
        result_summary="Bounded result returned.",
        files_changed=["/workspace/repo/secret.py"],
        artifacts=[{"kind": "patch", "name": "/workspace/repo/result.patch"}],
        error_message="worker touched /workspace/repo/secret.py",
    )

    snapshot = local_store.get_coding_run_snapshot(run["run_id"])
    assert snapshot is not None
    assert snapshot["status"] == "failed"
    assert snapshot["source_message_id"] == 99
    assert snapshot["result"]["files_changed_count"] == 1
    assert snapshot["result"]["artifacts"][0]["name"] == "result.patch"
    assert "/workspace/repo" not in json.dumps(snapshot)
    assert local_store.get_coding_run_snapshot(run["run_id"], user_id="alice") is None
    assert local_store.get_coding_run_snapshot(run["run_id"], user_id="bob") is None
    assert local_store.list_coding_runs_for_thread(42, user_id="alice") is None


@pytest.mark.asyncio
async def test_execute_coding_task_propagates_worktree_lease_fields(
    monkeypatch,
) -> None:
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-key")
    _patch_execution_authority(monkeypatch)

    captured_payloads: list[dict[str, Any]] = []
    local_store = AgentStore()
    local_publisher = AgentEventPublisher()
    monkeypatch.setattr(agent_orchestration, "_store", local_store)
    monkeypatch.setattr(
        agent_orchestration, "_event_publisher", local_publisher
    )
    monkeypatch.setattr(
        "guardian.queue.redis_queue.enqueue_coding_execution",
        lambda payload: captured_payloads.append(dict(payload)),
    )

    envelope = CodingAgentTaskEnvelope(
        coding_task_id="coding-task-lease-123",
        thread_id="42",
        source_message_id="99",
        attempt_id="attempt-1",
        user_id="local-user",
        project_id="17",
        adapter_kind="pi_sdk",
        instructions="Patch the failing seam.",
        repo_root="/workspace/repo",
        context_summary="source thread summary",
        validation_command="pytest -q",
        max_validation_attempts=2,
        worktree_lease_id="lease-abc",
        require_worktree_lease=True,
        permission_policy=CodingAgentPermissionPolicy(
            allow_shell=True,
            allow_network=False,
            allow_write=True,
            allowed_paths=("/workspace/repo",),
            max_runtime_seconds=60,
        ),
        provider_id="test-provider",
        model_id="test-model-a",
        credential_ref="credential-account-a",
    )

    result = await agent_orchestration.execute_coding_task(
        envelope, current_user="local-user"
    )

    assert result["ok"] is True
    assert captured_payloads
    payload = captured_payloads[0]
    assert payload["worktree_lease_id"] == "lease-abc"
    assert payload["require_worktree_lease"] is True

    deployment = local_store.get_deployment(result["deployment_id"])
    assert deployment is not None
    assert deployment["spec_json"]["worktree_lease_id"] == "lease-abc"
    assert deployment["spec_json"]["require_worktree_lease"] is True


@pytest.mark.asyncio
async def test_execute_coding_task_propagates_commit_gate_fields(
    monkeypatch,
) -> None:
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-key")
    _patch_execution_authority(monkeypatch)

    captured_payloads: list[dict[str, Any]] = []
    local_store = AgentStore()
    local_publisher = AgentEventPublisher()
    monkeypatch.setattr(agent_orchestration, "_store", local_store)
    monkeypatch.setattr(
        agent_orchestration, "_event_publisher", local_publisher
    )
    monkeypatch.setattr(
        "guardian.queue.redis_queue.enqueue_coding_execution",
        lambda payload: captured_payloads.append(dict(payload)),
    )

    envelope = CodingAgentTaskEnvelope(
        coding_task_id="coding-task-commit-123",
        thread_id="42",
        source_message_id="99",
        attempt_id="attempt-1",
        user_id="local-user",
        project_id="17",
        adapter_kind="pi_sdk",
        instructions="Patch the failing seam.",
        repo_root="/workspace/repo",
        context_summary="source thread summary",
        validation_command="pytest -q",
        max_validation_attempts=1,
        worktree_lease_id="lease-commit-abc",
        require_worktree_lease=True,
        commit_after_validation=True,
        commit_message="Commit after green",
        require_human_review_before_merge=False,
        permission_policy=CodingAgentPermissionPolicy(
            allow_shell=True,
            allow_network=False,
            allow_write=True,
            allowed_paths=("/workspace/repo",),
            max_runtime_seconds=60,
        ),
        provider_id="test-provider",
        model_id="test-model-a",
        credential_ref="credential-account-a",
    )

    result = await agent_orchestration.execute_coding_task(
        envelope, current_user="local-user"
    )

    assert result["ok"] is True
    assert captured_payloads
    payload = captured_payloads[0]
    assert payload["commit_after_validation"] is True
    assert payload["commit_message"] == "Commit after green"
    assert payload["require_human_review_before_merge"] is False

    deployment = local_store.get_deployment(result["deployment_id"])
    assert deployment is not None
    assert deployment["spec_json"]["commit_after_validation"] is True
    assert deployment["spec_json"]["commit_message"] == "Commit after green"
    assert deployment["spec_json"]["require_human_review_before_merge"] is False


@pytest.mark.asyncio
async def test_execute_coding_task_propagates_campaign_runner_ids(
    monkeypatch,
) -> None:
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-key")
    _patch_execution_authority(monkeypatch)

    captured_payloads: list[dict[str, Any]] = []
    local_store = AgentStore()
    local_publisher = AgentEventPublisher()
    monkeypatch.setattr(agent_orchestration, "_store", local_store)
    monkeypatch.setattr(
        agent_orchestration, "_event_publisher", local_publisher
    )
    monkeypatch.setattr(
        "guardian.queue.redis_queue.enqueue_coding_execution",
        lambda payload: captured_payloads.append(dict(payload)),
    )

    envelope = CodingAgentTaskEnvelope(
        coding_task_id="coding-task-campaign-123",
        thread_id="42",
        source_message_id="99",
        attempt_id="attempt-1",
        user_id="local-user",
        project_id="17",
        adapter_kind="pi_sdk",
        instructions="Patch campaign runner seams.",
        repo_root="/workspace/repo",
        context_summary="source thread summary",
        campaign_id="campaign_abc",
        work_order_id="wo_abc",
        validation_command="pytest -q",
        max_validation_attempts=1,
        permission_policy=CodingAgentPermissionPolicy(
            allow_shell=True,
            allow_network=False,
            allow_write=True,
            allowed_paths=("/workspace/repo",),
            max_runtime_seconds=60,
        ),
        provider_id="test-provider",
        model_id="test-model-a",
        credential_ref="credential-account-a",
    )

    result = await agent_orchestration.execute_coding_task(
        envelope, current_user="local-user"
    )

    assert result["ok"] is True
    payload = captured_payloads[0]
    assert payload["campaign_id"] == "campaign_abc"
    assert payload["work_order_id"] == "wo_abc"

    deployment = local_store.get_deployment(result["deployment_id"])
    assert deployment is not None
    assert deployment["spec_json"]["campaign_id"] == "campaign_abc"
    assert deployment["spec_json"]["work_order_id"] == "wo_abc"


def test_execute_coding_task_route_accepts_pi_codex_runner_adapter_kind(
    monkeypatch,
) -> None:
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-key")
    _patch_execution_authority(monkeypatch)

    local_store = AgentStore()
    local_publisher = AgentEventPublisher()
    monkeypatch.setattr(agent_orchestration, "_store", local_store)
    monkeypatch.setattr(
        agent_orchestration, "_event_publisher", local_publisher
    )

    payload = asdict(
        CodingAgentTaskEnvelope(
            coding_task_id="coding-task-codex-route",
            thread_id="42",
            source_message_id="99",
            attempt_id="attempt-route",
            user_id="local-user",
            project_id="17",
            adapter_kind="pi_codex_runner",
            instructions="Patch the failing seam.",
            repo_root="/workspace/repo",
            context_summary="source thread summary",
            validation_command="pytest -q",
            max_validation_attempts=3,
            permission_policy=CodingAgentPermissionPolicy(
                allow_shell=True,
                allow_network=False,
                allow_write=True,
                allowed_paths=("/workspace/repo",),
                max_runtime_seconds=60,
            ),
            provider_id="test-provider",
            model_id="test-model-a",
            credential_ref="credential-account-a",
        )
    )

    client = _build_client()
    response = client.post(
        "/api/agents/coding/execute",
        json=payload,
        headers={"X-API-Key": "test-key"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["coding_task_id"] == "coding-task-codex-route"

    deployment = local_store.get_deployment(body["deployment_id"])
    assert deployment is not None
    assert deployment["spec_json"]["adapter_kind"] == "pi_codex_runner"


def test_execute_coding_task_rejects_account_identity_mismatch_before_dispatch(
    monkeypatch,
) -> None:
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-key")
    _patch_execution_authority(monkeypatch)
    authority_calls: list[str] = []
    queued_payloads: list[dict[str, Any]] = []
    monkeypatch.setattr(
        agent_orchestration,
        "authorize_credential_selection",
        lambda *_args, **_kwargs: authority_calls.append("credential_lookup"),
    )
    monkeypatch.setattr(
        "guardian.queue.redis_queue.enqueue_coding_execution",
        lambda payload: queued_payloads.append(dict(payload)),
    )

    local_store = AgentStore()
    monkeypatch.setattr(agent_orchestration, "_store", local_store)
    monkeypatch.setattr(
        agent_orchestration, "_event_publisher", AgentEventPublisher()
    )
    payload = asdict(
        CodingAgentTaskEnvelope(
            coding_task_id="coding-task-cross-account",
            thread_id="42",
            source_message_id="99",
            attempt_id="attempt-cross-account",
            user_id="account-b",
            project_id=None,
            adapter_kind="pi",
            instructions="Do not dispatch this cross-account task.",
            repo_root="/workspace/repo",
            context_summary=None,
            permission_policy=CodingAgentPermissionPolicy(
                allow_shell=True,
                allow_network=False,
                allow_write=True,
                allowed_paths=("/workspace/repo",),
                max_runtime_seconds=60,
            ),
            provider_id="test-provider",
            model_id="test-model",
            credential_ref="credential-account-b",
        )
    )

    response = _build_client().post(
        "/api/agents/coding/execute",
        json=payload,
        headers={"X-API-Key": "test-key"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "account_identity_mismatch"}
    assert authority_calls == []
    assert queued_payloads == []
    assert local_store.get_deployment("coding_coding-task-cross-account") is None


def test_execute_coding_task_route_rejects_unknown_adapter_kind(
    monkeypatch,
) -> None:
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-key")
    _patch_execution_authority(monkeypatch)

    local_store = AgentStore()
    local_publisher = AgentEventPublisher()
    monkeypatch.setattr(agent_orchestration, "_store", local_store)
    monkeypatch.setattr(
        agent_orchestration, "_event_publisher", local_publisher
    )

    payload = asdict(
        CodingAgentTaskEnvelope(
            coding_task_id="coding-task-reject",
            thread_id="42",
            source_message_id="99",
            attempt_id="attempt-reject",
            user_id="local-user",
            project_id="17",
            adapter_kind="pi_codex_runner",
            instructions="Patch the failing seam.",
            repo_root="/workspace/repo",
            context_summary="source thread summary",
            validation_command="pytest -q",
            max_validation_attempts=1,
            permission_policy=CodingAgentPermissionPolicy(
                allow_shell=True,
                allow_network=False,
                allow_write=True,
                allowed_paths=("/workspace/repo",),
                max_runtime_seconds=60,
            ),
            provider_id="test-provider",
            model_id="test-model-a",
            credential_ref="credential-account-a",
        )
    )
    payload["adapter_kind"] = "mystery_adapter"

    client = _build_client()
    response = client.post(
        "/api/agents/coding/execute",
        json=payload,
        headers={"X-API-Key": "test-key"},
    )

    assert response.status_code == 422


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


def test_coding_execution_payload_defaults_validation_attempts_to_one() -> None:
    body = agent_orchestration.CodingExecutionRequest(
        run_id="run-123",
        coding_task_id="coding-123",
        thread_id="thread-123",
        source_message_id="message-123",
        attempt_id="attempt-123",
        user_id="local",
        adapter_kind="mock",
        instructions="Fix the parser.",
        permission_policy={
            "allow_shell": True,
            "allow_network": False,
            "allow_write": True,
            "allowed_paths": ["/workspace/repo"],
            "max_runtime_seconds": 300,
        },
    )

    payload = agent_orchestration.build_coding_execution_task_payload(body)
    task = CodingExecutionTask.from_dict(payload)

    assert payload["max_validation_attempts"] == 1
    assert "worktree_lease_id" not in payload
    assert payload["require_worktree_lease"] is False
    assert payload["commit_after_validation"] is False
    assert "commit_message" not in payload
    assert payload["require_human_review_before_merge"] is True
    assert task.run_id == "run-123"
    assert task.max_validation_attempts == 1
    assert task.worktree_lease_id is None
    assert task.require_worktree_lease is False
    assert task.commit_after_validation is False
    assert task.commit_message is None
    assert task.require_human_review_before_merge is True
    assert task.permission_policy["allow_shell"] is True


def test_coding_execution_payload_round_trips_retry_field() -> None:
    body = agent_orchestration.CodingExecutionRequest(
        run_id="run-456",
        coding_task_id="coding-456",
        thread_id="thread-456",
        source_message_id="message-456",
        attempt_id="attempt-456",
        user_id="local",
        adapter_kind="codex",
        instructions="Fix the failing test.",
        validation_command="pytest -q",
        max_validation_attempts=3,
        worktree_lease_id="lease-xyz",
        require_worktree_lease=True,
        commit_after_validation=True,
        commit_message="Commit after green",
        require_human_review_before_merge=False,
    )

    payload = agent_orchestration.build_coding_execution_task_payload(body)
    task = CodingExecutionTask.from_dict(payload)

    assert payload["max_validation_attempts"] == 3
    assert payload["worktree_lease_id"] == "lease-xyz"
    assert payload["require_worktree_lease"] is True
    assert payload["commit_after_validation"] is True
    assert payload["commit_message"] == "Commit after green"
    assert payload["require_human_review_before_merge"] is False
    assert task.max_validation_attempts == 3
    assert task.worktree_lease_id == "lease-xyz"
    assert task.require_worktree_lease is True
    assert task.commit_after_validation is True
    assert task.commit_message == "Commit after green"
    assert task.require_human_review_before_merge is False
    assert task.validation_command == "pytest -q"


def test_coding_execution_request_rejects_validation_attempts_over_cap() -> (
    None
):
    with pytest.raises(ValidationError):
        agent_orchestration.CodingExecutionRequest(
            run_id="run-789",
            coding_task_id="coding-789",
            thread_id="thread-789",
            source_message_id="message-789",
            attempt_id="attempt-789",
            user_id="local",
            adapter_kind="codex",
            instructions="Fix the failing test.",
            validation_command="pytest -q",
            max_validation_attempts=4,
        )


def test_account_owner_reads_run_and_thread_projections(monkeypatch) -> None:
    """An authenticated account owner reaches the resource lookup and reads
    the permitted projection.

    This is route and authentication wiring proof against a store spy: the
    handler must hand the authenticated account identity to the store and
    must not answer an identity mismatch. The durable ownership decision
    itself is proven by the PostgreSQL snapshot suite.
    """
    _remote_account_env(monkeypatch)
    spy = _AccountScopedStoreSpy(owner="account-a@example.invalid")
    _patch_readback_store(monkeypatch, spy)

    client = _build_identity_client()
    headers = _account_session_headers("account-a@example.invalid")

    coding = client.get("/api/agents/runs/run-owned/coding", headers=headers)
    assert coding.status_code == 200, coding.text
    assert coding.json()["run"]["coding_task_id"] == "coding-owned"

    single = client.get("/api/agents/runs/run-owned", headers=headers)
    assert single.status_code == 200, single.text
    assert single.json()["run"]["run_id"] == "run-owned"

    canonical = client.get("/api/agents/chat/77/agent-runs", headers=headers)
    assert canonical.status_code == 200, canonical.text
    assert canonical.json()["runs"][0]["run_id"] == "run-owned"

    coding_threads = client.get("/api/chat/77/coding-runs", headers=headers)
    assert coding_threads.status_code == 200, coding_threads.text
    assert coding_threads.json()["runs"][0]["coding_task_id"] == "coding-owned"

    # Every readback supplied the authenticated account identity, never an
    # empty or caller-supplied one.
    assert {identity for _method, identity in spy.calls} == {
        "account-a@example.invalid"
    }


def test_readback_refuses_a_foreign_accounts_resource(monkeypatch) -> None:
    """A foreign account cannot read another account's run or thread.

    The denial is a resource-existence 404, not an identity failure: the
    store was asked with the caller's own account, so the ownership decision
    is what refuses the read.
    """
    _remote_account_env(monkeypatch)
    spy = _AccountScopedStoreSpy(owner="account-a@example.invalid")
    _patch_readback_store(monkeypatch, spy)

    client = _build_identity_client()
    headers = _account_session_headers("account-b@example.invalid")

    for path in (
        "/api/agents/runs/run-owned/coding",
        "/api/agents/runs/run-owned",
        "/api/agents/chat/77/agent-runs",
        "/api/chat/77/agent-runs",
        "/api/chat/77/coding-runs",
    ):
        response = client.get(path, headers=headers)
        assert response.status_code == 404, f"{path}: {response.text}"
        assert "run-owned" not in response.text

    # The caller's own account identity reached the store; the resource
    # ownership check refused it.
    assert {identity for _method, identity in spy.calls} == {
        "account-b@example.invalid"
    }


def test_readback_identity_ignores_a_forged_user_id_header(monkeypatch) -> None:
    """A caller-supplied identity header cannot replace account authority."""
    _remote_account_env(monkeypatch)
    spy = _AccountScopedStoreSpy(owner="account-a@example.invalid")
    _patch_readback_store(monkeypatch, spy)

    client = _build_identity_client()
    headers = _account_session_headers("account-a@example.invalid")
    headers["X-User-Id"] = "account-c@example.invalid"

    response = client.get("/api/agents/runs/run-owned", headers=headers)
    assert response.status_code == 200, response.text
    # The authenticated session subject is the read identity, not the
    # forged header.
    assert {identity for _method, identity in spy.calls} == {
        "account-a@example.invalid"
    }


def test_readback_fails_closed_without_an_authenticated_identity(monkeypatch) -> None:
    """A missing authenticated identity denies the read before any lookup."""
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-key")
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "local")
    spy = _AccountScopedStoreSpy(owner="account-a@example.invalid")
    _patch_readback_store(monkeypatch, spy)

    app = FastAPI()
    app.include_router(agent_orchestration.router)
    app.include_router(agent_orchestration.chat_router)
    app.dependency_overrides[agent_orchestration.get_current_user] = lambda: None

    response = TestClient(app).get(
        "/api/agents/runs/run-owned",
        headers={"X-API-Key": "test-key"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "account_identity_missing"
    # No resource lookup happened.
    assert spy.calls == []


def test_remote_readback_rejects_an_operator_api_key_as_an_account_session(
    monkeypatch,
) -> None:
    """An operator credential cannot act as an account session."""
    _remote_account_env(monkeypatch)
    spy = _AccountScopedStoreSpy(owner="account-a@example.invalid")
    _patch_readback_store(monkeypatch, spy)

    client = _build_identity_client()
    response = client.get(
        "/api/agents/runs/run-owned",
        headers={"X-API-Key": "test-key"},
    )

    assert response.status_code == 401
    assert spy.calls == []


def test_remote_readback_does_not_fall_back_to_memory_only_state(monkeypatch) -> None:
    """Remote account readback must not read a memory-only run."""
    _remote_account_env(monkeypatch)
    local_store = AgentStore()
    _patch_readback_store(monkeypatch, local_store)

    deployment = local_store.create_deployment(
        flow_id="flow-memory-only",
        thread_id=77,
        spec_json={"user_id": "account-a@example.invalid"},
        spec_hash="spec-memory-only",
    )
    run = local_store.create_run(
        deployment_id=str(deployment["deployment_id"]),
        thread_id=77,
        status="running",
    )

    client = _build_identity_client()
    headers = _account_session_headers("account-a@example.invalid")

    for path in ("/api/chat/77/coding-runs", "/api/agents/chat/77/agent-runs"):
        response = client.get(path, headers=headers)
        assert response.status_code == 404, f"{path}: {response.text}"
        assert str(run["run_id"]) not in response.text


def test_local_operator_readback_still_refuses_another_accounts_run(
    monkeypatch,
) -> None:
    """Local operator readback keeps its established ownership boundary."""
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-key")
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "local")
    monkeypatch.setattr(
        agent_orchestration.dependencies, "is_private_preview", lambda: False
    )
    local_store = AgentStore()
    _patch_readback_store(monkeypatch, local_store)

    deployment = local_store.create_deployment(
        flow_id="operator-other-account",
        thread_id=None,
        spec_json={"user_id": "account-b@example.invalid"},
        spec_hash="operator-other-account-spec",
    )
    run = local_store.create_run(
        deployment_id=str(deployment["deployment_id"]),
        thread_id=None,
        status="running",
    )

    response = _build_identity_client().get(
        f"/api/agents/runs/{run['run_id']}",
        headers={"X-API-Key": "test-key"},
    )

    assert response.status_code == 404, response.text
    assert str(run["run_id"]) not in response.text


def test_thread_list_aliases_use_the_same_authoritative_account(monkeypatch) -> None:
    """Both thread-list aliases resolve the same account identity."""
    _remote_account_env(monkeypatch)
    spy = _AccountScopedStoreSpy(owner="account-a@example.invalid")
    _patch_readback_store(monkeypatch, spy)

    client = _build_identity_client()
    headers = _account_session_headers("account-a@example.invalid")

    canonical = client.get("/api/agents/chat/77/agent-runs", headers=headers)
    alias = client.get("/api/chat/77/agent-runs", headers=headers)

    assert canonical.status_code == 200, canonical.text
    assert alias.status_code == 200, alias.text
    assert canonical.json() == alias.json()
    assert [
        identity
        for method, identity in spy.calls
        if method == "list_account_runs_for_thread"
    ] == ["account-a@example.invalid", "account-a@example.invalid"]


def test_strict_requested_identity_helper_still_requires_a_matching_identity() -> None:
    """The strict execution-request identity helper is unchanged.

    A request that supplies an identity to be checked must still match the
    authenticated account exactly, and an empty requested identity is not a
    match.
    """
    assert (
        agent_orchestration._resolved_request_user("account-a", "account-a")
        == "account-a"
    )

    with pytest.raises(HTTPException) as mismatch:
        agent_orchestration._resolved_request_user("account-a", "account-b")
    assert mismatch.value.status_code == 403
    assert mismatch.value.detail == "account_identity_mismatch"

    with pytest.raises(HTTPException) as empty:
        agent_orchestration._resolved_request_user("account-a", "")
    assert empty.value.status_code == 403
    assert empty.value.detail == "account_identity_mismatch"

    with pytest.raises(HTTPException) as missing:
        agent_orchestration._resolved_request_user("", "account-a")
    assert missing.value.status_code == 401
    assert missing.value.detail == "account_identity_missing"
