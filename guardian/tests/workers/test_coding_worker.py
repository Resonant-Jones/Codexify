from __future__ import annotations

import subprocess
from contextlib import suppress
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy import JSON, Integer, create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.agents.store import AgentStore
from guardian.db.models import (
    AgentDeployment,
    AgentRun,
    AgentRunArtifact,
    Base,
    ChatMessage,
    ChatThread,
    Project,
    User,
)
from guardian.tasks.types import CodingExecutionTask
from guardian.workers import coding_worker


class _TestDB:
    def __init__(self) -> None:
        self._engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self._original_types = {
            AgentDeployment.__table__.c.id: AgentDeployment.__table__.c.id.type,
            AgentRun.__table__.c.id: AgentRun.__table__.c.id.type,
            AgentRunArtifact.__table__.c.id: AgentRunArtifact.__table__.c.id.type,
            ChatMessage.__table__.c.id: ChatMessage.__table__.c.id.type,
            ChatThread.__table__.c.thread_config: ChatThread.__table__.c.thread_config.type,
            AgentDeployment.__table__.c.spec_json: AgentDeployment.__table__.c.spec_json.type,
            ChatMessage.__table__.c.extra_meta: ChatMessage.__table__.c.extra_meta.type,
            AgentRunArtifact.__table__.c.content_json: AgentRunArtifact.__table__.c.content_json.type,
        }
        for column in self._original_types:
            if column.name == "id" and column.table.name in {
                "agent_deployments",
                "agent_runs",
                "agent_run_artifacts",
                "chat_messages",
            }:
                column.type = Integer()
            else:
                column.type = JSON().with_variant(JSONB, "postgresql")
        Base.metadata.create_all(
            bind=self._engine,
            tables=[
                User.__table__,
                Project.__table__,
                ChatThread.__table__,
                ChatMessage.__table__,
                AgentDeployment.__table__,
                AgentRun.__table__,
                AgentRunArtifact.__table__,
            ],
        )
        self._session_factory = sessionmaker(
            bind=self._engine,
            autoflush=False,
            autocommit=False,
            future=True,
        )

    def get_session(self):  # noqa: ANN201
        return self._session_factory()

    def close(self) -> None:
        for column, original in self._original_types.items():
            column.type = original
        self._engine.dispose()


@pytest.fixture
def db() -> _TestDB:
    test_db = _TestDB()
    try:
        yield test_db
    finally:
        with suppress(Exception):
            test_db.close()


def _seed_source_context(
    db: _TestDB,
    *,
    user_id: str = "user-1",
    project_name: str = "project-1",
    thread_title: str = "Source thread",
    thread_summary: str = "",
    thread_user_id: str | None = None,
) -> dict[str, Any]:
    thread_owner = thread_user_id or user_id
    with db.get_session() as session:
        user = User(
            id=user_id,
            username=f"{user_id}-username",
            password_hash="hash",
        )
        session.add(user)
        if thread_owner != user_id:
            session.add(
                User(
                    id=thread_owner,
                    username=f"{thread_owner}-username",
                    password_hash="hash",
                )
            )
        project = Project(
            user_id=thread_owner,
            name=f"{project_name}-{thread_owner}",
            description=None,
            icon=None,
        )
        session.add(project)
        session.flush()
        thread = ChatThread(
            user_id=thread_owner,
            title=thread_title,
            summary=thread_summary,
            project_id=project.id,
        )
        session.add(thread)
        session.flush()
        source_message = ChatMessage(
            thread_id=thread.id,
            user_id=thread_owner,
            role="user",
            content="Please patch the return path.",
            kind="chat",
            extra_meta={},
        )
        session.add(source_message)
        session.commit()
        session.refresh(project)
        session.refresh(thread)
        session.refresh(source_message)

    return {
        "user_id": user_id,
        "thread_user_id": thread_owner,
        "project_id": project.id,
        "thread_id": thread.id,
        "source_message_id": source_message.id,
    }


def _make_store(db: _TestDB) -> AgentStore:
    return AgentStore(db=db)


_MISSING = object()


def _seed_execution_run(
    store: AgentStore,
    *,
    thread_id: int | None,
    source_message_id: int | None,
    user_id: str | None,
    project_id: int | None,
    runtime_target: str = "container",
    adapter_kind: Any = "pi_sdk",
) -> tuple[str, str]:
    spec_json = {
        "source_thread_id": thread_id,
        "source_message_id": source_message_id,
        "user_id": user_id,
        "project_id": project_id,
    }
    if adapter_kind is not _MISSING:
        spec_json["adapter_kind"] = adapter_kind
    deployment = store.create_deployment(
        flow_id="coding_return_path",
        thread_id=thread_id,
        spec_json=spec_json,
        spec_hash="spec-hash",
        trust_state="supervised",
    )
    run = store.create_run(
        deployment_id=str(deployment["deployment_id"]),
        thread_id=thread_id,
        runtime_target=runtime_target,
        rollback_mode="auto",
        status="queued",
    )
    return str(deployment["deployment_id"]), str(run["run_id"])


def _build_task(
    *,
    run_id: str,
    deployment_id: str,
    thread_id: int | None,
    source_message_id: int | None,
    coding_task_id: str = "coding-task-1",
    attempt_id: str = "attempt-1",
    validation_command: str | None = None,
    permission_policy: dict[str, Any] | None = None,
) -> CodingExecutionTask:
    payload: dict[str, Any] = {
        "task_id": f"task-{coding_task_id}",
        "run_id": run_id,
        "deployment_id": deployment_id,
        "instructions": "Patch the seam and keep the return path intact.",
        "cwd": "/workspace/repo",
        "timeout_seconds": 60,
        "coding_task_id": coding_task_id,
        "attempt_id": attempt_id,
        "thread_id": thread_id,
        "source_message_id": source_message_id,
    }
    if validation_command is not None:
        payload["validation_command"] = validation_command
    if permission_policy is not None:
        payload["permission_policy"] = permission_policy
    return CodingExecutionTask.from_dict(payload)


def _install_fake_adapter(
    monkeypatch,
    result: Any,
    *,
    adapter_kind: str = "pi_codex_runner",
) -> list[SimpleNamespace]:
    calls: list[SimpleNamespace] = []

    class _FakeAdapter:
        def execute(self, request: Any) -> Any:
            calls.append(request)
            return result

    monkeypatch.setattr(
        coding_worker, "ADAPTERS", {adapter_kind: _FakeAdapter()}
    )
    return calls


def _install_fake_validation_runner(
    monkeypatch,
    *,
    result: subprocess.CompletedProcess[str] | None = None,
    side_effect: BaseException | None = None,
) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    def _fake_run(
        argv: list[str],
        *,
        cwd: str | None = None,
        capture_output: bool | None = None,
        text: bool | None = None,
        check: bool | None = None,
        timeout: int | float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        calls.append(
            {
                "argv": list(argv),
                "cwd": cwd,
                "capture_output": capture_output,
                "text": text,
                "check": check,
                "timeout": timeout,
            }
        )
        if side_effect is not None:
            raise side_effect
        return result or subprocess.CompletedProcess(
            argv,
            0,
            stdout="1 passed in 0.01s\n",
            stderr="",
        )

    monkeypatch.setattr(coding_worker.subprocess, "run", _fake_run)
    return calls


def _capture_task_events(monkeypatch) -> list[tuple[str, str, dict[str, Any]]]:
    published: list[tuple[str, str, dict[str, Any]]] = []
    monkeypatch.setattr(
        coding_worker.task_events,
        "publish_with_visibility",
        lambda task_id, event_type, data=None: published.append(
            (task_id, event_type, dict(data or {}))
        )
        or {
            "ok": True,
            "task_id": task_id,
            "event_type": event_type,
            "visibility_scope": (
                "terminal"
                if event_type in {"task.completed", "task.failed"}
                else "progress"
            ),
            "terminal_visibility": event_type
            in {
                "task.completed",
                "task.failed",
            },
            "execution_continued": True,
            "event_id": "1-0",
            "error_code": None,
            "failure_class": None,
            "error": None,
        },
    )
    return published


def _fetch_thread_messages(db: _TestDB, thread_id: int) -> list[ChatMessage]:
    with db.get_session() as session:
        return (
            session.query(ChatMessage)
            .filter_by(thread_id=thread_id, kind="coding_result")
            .order_by(ChatMessage.id.asc())
            .all()
        )


def _fetch_message(db: _TestDB, message_id: int) -> ChatMessage | None:
    with db.get_session() as session:
        return session.query(ChatMessage).filter_by(id=message_id).first()


def _fetch_run_state(store: AgentStore, run_id: str) -> dict[str, Any] | None:
    return store.get_run(run_id)


def _fetch_coding_result_artifacts(
    store: AgentStore, run_id: str
) -> list[dict[str, Any]]:
    return store.list_artifacts(run_id=run_id, artifact_type="coding_result")


def test_codex_adapter_kind_selects_codex_adapter_and_lineage(
    db,
    monkeypatch,
) -> None:
    seeded = _seed_source_context(
        db, user_id="codex-user", project_name="codex"
    )
    store = _make_store(db)
    deployment_id, run_id = _seed_execution_run(
        store,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        user_id=seeded["user_id"],
        project_id=seeded["project_id"],
        adapter_kind="codex",
    )
    worker = coding_worker.CodingWorker(agent_store=store)
    published = _capture_task_events(monkeypatch)
    calls = _install_fake_adapter(
        monkeypatch,
        SimpleNamespace(
            status="ok",
            summary="Codex adapter completed.",
            artifacts=(),
            errors=(),
        ),
        adapter_kind="codex",
    )

    task = _build_task(
        run_id=run_id,
        deployment_id=deployment_id,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        coding_task_id="coding-task-codex",
    )
    worker._process_task(task)

    assert len(calls) == 1
    assert [event for _, event, _ in published] == [
        "task.running",
        "task.completed",
    ]
    assert [payload["adapter_kind"] for _, _, payload in published] == [
        "codex",
        "codex",
    ]
    messages = _fetch_thread_messages(db, seeded["thread_id"])
    assert len(messages) == 1
    assert messages[0].extra_meta["adapter_kind"] == "codex"


def test_pi_sdk_adapter_kind_resolves_to_pi_codex_runner(
    db,
    monkeypatch,
) -> None:
    seeded = _seed_source_context(db, user_id="pi-user", project_name="pi")
    store = _make_store(db)
    deployment_id, run_id = _seed_execution_run(
        store,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        user_id=seeded["user_id"],
        project_id=seeded["project_id"],
        adapter_kind="pi_sdk",
    )
    worker = coding_worker.CodingWorker(agent_store=store)
    published = _capture_task_events(monkeypatch)
    calls = _install_fake_adapter(
        monkeypatch,
        SimpleNamespace(status="ok", summary="Pi adapter completed."),
    )

    task = _build_task(
        run_id=run_id,
        deployment_id=deployment_id,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        coding_task_id="coding-task-pi-sdk",
    )
    worker._process_task(task)

    assert len(calls) == 1
    assert [payload["adapter_kind"] for _, _, payload in published] == [
        "pi_codex_runner",
        "pi_codex_runner",
    ]


@pytest.mark.parametrize("adapter_kind", [_MISSING, "", "   "])
def test_missing_or_blank_adapter_kind_defaults_to_pi_codex_runner(
    db,
    monkeypatch,
    adapter_kind,
) -> None:
    seeded = _seed_source_context(
        db, user_id=f"default-user-{id(adapter_kind)}"
    )
    store = _make_store(db)
    deployment_id, run_id = _seed_execution_run(
        store,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        user_id=seeded["user_id"],
        project_id=seeded["project_id"],
        adapter_kind=adapter_kind,
    )
    worker = coding_worker.CodingWorker(agent_store=store)
    published = _capture_task_events(monkeypatch)
    calls = _install_fake_adapter(
        monkeypatch,
        SimpleNamespace(status="ok", summary="Default adapter completed."),
    )

    task = _build_task(
        run_id=run_id,
        deployment_id=deployment_id,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        coding_task_id=f"coding-task-default-{len(published)}",
    )
    worker._process_task(task)

    assert len(calls) == 1
    assert [payload["adapter_kind"] for _, _, payload in published] == [
        "pi_codex_runner",
        "pi_codex_runner",
    ]


def test_unknown_adapter_kind_fails_closed_with_adapter_not_found(
    db,
    monkeypatch,
) -> None:
    seeded = _seed_source_context(db, user_id="unknown-adapter-user")
    store = _make_store(db)
    deployment_id, run_id = _seed_execution_run(
        store,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        user_id=seeded["user_id"],
        project_id=seeded["project_id"],
        adapter_kind="mystery_adapter",
    )
    worker = coding_worker.CodingWorker(agent_store=store)
    published = _capture_task_events(monkeypatch)
    monkeypatch.setattr(
        coding_worker, "ADAPTERS", {"pi_codex_runner": object()}
    )

    task = _build_task(
        run_id=run_id,
        deployment_id=deployment_id,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        coding_task_id="coding-task-unknown-adapter",
    )
    worker._process_task(task)

    assert [event for _, event, _ in published] == [
        "task.running",
        "task.failed",
    ]
    failure_payload = published[-1][2]
    assert failure_payload["adapter_kind"] == "mystery_adapter"
    assert failure_payload["error_code"] == "ADAPTER_NOT_FOUND"
    assert "mystery_adapter" in failure_payload["error_message"]
    assert _fetch_thread_messages(db, seeded["thread_id"]) == []
    assert _fetch_coding_result_artifacts(store, run_id) == []
    run_state = _fetch_run_state(store, run_id)
    assert run_state is not None
    assert run_state["status"] == "failed"


def test_passing_validation_is_persisted_and_emitted(
    db,
    monkeypatch,
) -> None:
    seeded = _seed_source_context(
        db, user_id="validation-pass-user", project_name="validation-pass"
    )
    store = _make_store(db)
    deployment_id, run_id = _seed_execution_run(
        store,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        user_id=seeded["user_id"],
        project_id=seeded["project_id"],
        adapter_kind="codex",
    )
    worker = coding_worker.CodingWorker(agent_store=store)
    published = _capture_task_events(monkeypatch)
    calls = _install_fake_adapter(
        monkeypatch,
        SimpleNamespace(
            status="ok",
            summary="Adapter succeeded.",
            artifacts=(),
            errors=(),
        ),
        adapter_kind="codex",
    )
    validation_calls = _install_fake_validation_runner(
        monkeypatch,
        result=subprocess.CompletedProcess(
            args=["pytest", "-q"],
            returncode=0,
            stdout="2 passed in 0.02s\n",
            stderr="",
        ),
    )
    task = _build_task(
        run_id=run_id,
        deployment_id=deployment_id,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        coding_task_id="coding-task-validation-pass",
        validation_command="pytest -q",
        permission_policy={
            "allow_shell": True,
            "allow_network": False,
            "allow_write": True,
            "allowed_paths": ["/workspace/repo"],
            "max_runtime_seconds": 60,
        },
    )

    worker._process_task(task)

    assert len(calls) == 1
    assert len(validation_calls) == 1
    assert validation_calls[0]["cwd"] == "/workspace/repo"
    assert validation_calls[0]["timeout"] == 60
    assert [event for _, event, _ in published] == [
        "task.running",
        "task.completed",
    ]
    terminal_payload = published[-1][2]
    assert terminal_payload["coding_result_status"] == "ok"
    assert terminal_payload["validation_result"]["status"] == "passed"
    assert terminal_payload["validation_result"]["tests_passed"] == 2
    messages = _fetch_thread_messages(db, seeded["thread_id"])
    assert len(messages) == 1
    message = messages[0]
    assert message.extra_meta["validation_results"]["status"] == "passed"
    assert message.extra_meta["validation_results"]["command"] == "pytest -q"
    artifacts = _fetch_coding_result_artifacts(store, run_id)
    assert len(artifacts) == 1
    assert (
        artifacts[0]["content_json"]["validation_results"]["status"] == "passed"
    )
    assert (
        artifacts[0]["content_json"]["validation_results"]["command"]
        == "pytest -q"
    )
    run_state = _fetch_run_state(store, run_id)
    assert run_state is not None
    assert run_state["status"] == "succeeded"


def test_failing_validation_marks_attempt_failed(
    db,
    monkeypatch,
) -> None:
    seeded = _seed_source_context(
        db, user_id="validation-fail-user", project_name="validation-fail"
    )
    store = _make_store(db)
    deployment_id, run_id = _seed_execution_run(
        store,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        user_id=seeded["user_id"],
        project_id=seeded["project_id"],
        adapter_kind="codex",
    )
    worker = coding_worker.CodingWorker(agent_store=store)
    published = _capture_task_events(monkeypatch)
    _install_fake_adapter(
        monkeypatch,
        SimpleNamespace(
            status="ok",
            summary="Adapter succeeded before validation.",
            artifacts=(),
            errors=(),
        ),
        adapter_kind="codex",
    )
    validation_calls = _install_fake_validation_runner(
        monkeypatch,
        result=subprocess.CompletedProcess(
            args=["pytest", "-q"],
            returncode=1,
            stdout="FAILED tests/unit/test_alpha.py::test_something - boom\n",
            stderr="E AssertionError: boom\n",
        ),
    )
    task = _build_task(
        run_id=run_id,
        deployment_id=deployment_id,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        coding_task_id="coding-task-validation-fail",
        validation_command="pytest -q",
        permission_policy={
            "allow_shell": True,
            "allow_network": False,
            "allow_write": True,
            "allowed_paths": ["/workspace/repo"],
            "max_runtime_seconds": 60,
        },
    )

    worker._process_task(task)

    assert len(validation_calls) == 1
    assert [event for _, event, _ in published] == [
        "task.running",
        "task.failed",
    ]
    terminal_payload = published[-1][2]
    assert terminal_payload["coding_result_status"] == "failed"
    assert terminal_payload["validation_result"]["status"] == "failed"
    assert terminal_payload["errors"][-1] == "validation_failed"
    messages = _fetch_thread_messages(db, seeded["thread_id"])
    assert messages == []
    artifacts = _fetch_coding_result_artifacts(store, run_id)
    assert len(artifacts) == 1
    content = artifacts[0]["content_json"]
    assert content["coding_result_status"] == "failed"
    assert content["validation_results"]["status"] == "failed"
    assert content["validation_results"]["fail_signature"] is not None
    run_state = _fetch_run_state(store, run_id)
    assert run_state is not None
    assert run_state["status"] == "failed"


def test_adapter_failure_does_not_run_validation(
    db,
    monkeypatch,
) -> None:
    seeded = _seed_source_context(
        db, user_id="adapter-fail-user", project_name="adapter-fail"
    )
    store = _make_store(db)
    deployment_id, run_id = _seed_execution_run(
        store,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        user_id=seeded["user_id"],
        project_id=seeded["project_id"],
        adapter_kind="codex",
    )
    worker = coding_worker.CodingWorker(agent_store=store)
    _capture_task_events(monkeypatch)
    _install_fake_adapter(
        monkeypatch,
        SimpleNamespace(
            status="error",
            summary="Adapter failed before validation could start.",
            artifacts=(),
            errors=("adapter failed",),
            error_message="adapter failed",
        ),
        adapter_kind="codex",
    )
    validation_calls = _install_fake_validation_runner(monkeypatch)
    task = _build_task(
        run_id=run_id,
        deployment_id=deployment_id,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        coding_task_id="coding-task-adapter-fail",
        validation_command="pytest -q",
        permission_policy={
            "allow_shell": True,
            "allow_network": False,
            "allow_write": True,
            "allowed_paths": ["/workspace/repo"],
            "max_runtime_seconds": 60,
        },
    )

    worker._process_task(task)

    assert validation_calls == []
    run_state = _fetch_run_state(store, run_id)
    assert run_state is not None
    assert run_state["status"] == "failed"


def test_validation_command_with_shell_blocked_records_not_run(
    db,
    monkeypatch,
) -> None:
    seeded = _seed_source_context(
        db, user_id="shell-blocked-user", project_name="shell-blocked"
    )
    store = _make_store(db)
    deployment_id, run_id = _seed_execution_run(
        store,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        user_id=seeded["user_id"],
        project_id=seeded["project_id"],
        adapter_kind="codex",
    )
    worker = coding_worker.CodingWorker(agent_store=store)
    published = _capture_task_events(monkeypatch)
    _install_fake_adapter(
        monkeypatch,
        SimpleNamespace(
            status="ok",
            summary="Adapter succeeded.",
            artifacts=(),
            errors=(),
        ),
        adapter_kind="codex",
    )
    validation_calls = _install_fake_validation_runner(monkeypatch)
    task = _build_task(
        run_id=run_id,
        deployment_id=deployment_id,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        coding_task_id="coding-task-shell-blocked",
        validation_command="pytest -q",
        permission_policy={
            "allow_shell": False,
            "allow_network": False,
            "allow_write": True,
            "allowed_paths": ["/workspace/repo"],
            "max_runtime_seconds": 60,
        },
    )

    worker._process_task(task)

    assert validation_calls == []
    assert [event for _, event, _ in published] == [
        "task.running",
        "task.completed",
    ]
    terminal_payload = published[-1][2]
    assert terminal_payload["validation_result"]["status"] == "not_run"
    assert (
        terminal_payload["validation_result"]["error_message"]
        == "validation_shell_not_allowed"
    )
    messages = _fetch_thread_messages(db, seeded["thread_id"])
    assert len(messages) == 1
    assert messages[0].extra_meta["validation_results"]["status"] == "not_run"
    assert (
        messages[0].extra_meta["validation_results"]["error_message"]
        == "validation_shell_not_allowed"
    )


def test_omitted_validation_command_preserves_existing_behavior(
    db,
    monkeypatch,
) -> None:
    seeded = _seed_source_context(
        db, user_id="no-validation-user", project_name="no-validation"
    )
    store = _make_store(db)
    deployment_id, run_id = _seed_execution_run(
        store,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        user_id=seeded["user_id"],
        project_id=seeded["project_id"],
        adapter_kind="codex",
    )
    worker = coding_worker.CodingWorker(agent_store=store)
    _capture_task_events(monkeypatch)
    _install_fake_adapter(
        monkeypatch,
        SimpleNamespace(
            status="ok",
            summary="Adapter succeeded.",
            artifacts=(),
            errors=(),
        ),
        adapter_kind="codex",
    )
    validation_calls = _install_fake_validation_runner(monkeypatch)
    task = _build_task(
        run_id=run_id,
        deployment_id=deployment_id,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        coding_task_id="coding-task-no-validation",
        permission_policy={
            "allow_shell": True,
            "allow_network": False,
            "allow_write": True,
            "allowed_paths": ["/workspace/repo"],
            "max_runtime_seconds": 60,
        },
    )

    worker._process_task(task)

    assert validation_calls == []
    messages = _fetch_thread_messages(db, seeded["thread_id"])
    assert len(messages) == 1
    assert messages[0].extra_meta.get("validation_results") is None


def test_validation_timeout_is_normalized_and_fails_closed(
    db,
    monkeypatch,
) -> None:
    seeded = _seed_source_context(
        db, user_id="validation-timeout-user", project_name="validation-timeout"
    )
    store = _make_store(db)
    deployment_id, run_id = _seed_execution_run(
        store,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        user_id=seeded["user_id"],
        project_id=seeded["project_id"],
        adapter_kind="codex",
    )
    worker = coding_worker.CodingWorker(agent_store=store)
    published = _capture_task_events(monkeypatch)
    _install_fake_adapter(
        monkeypatch,
        SimpleNamespace(
            status="ok",
            summary="Adapter succeeded.",
            artifacts=(),
            errors=(),
        ),
        adapter_kind="codex",
    )
    validation_calls = _install_fake_validation_runner(
        monkeypatch,
        side_effect=subprocess.TimeoutExpired(
            cmd=["pytest", "-q"],
            timeout=5,
        ),
    )
    task = _build_task(
        run_id=run_id,
        deployment_id=deployment_id,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        coding_task_id="coding-task-validation-timeout",
        validation_command="pytest -q",
        permission_policy={
            "allow_shell": True,
            "allow_network": False,
            "allow_write": True,
            "allowed_paths": ["/workspace/repo"],
            "max_runtime_seconds": 60,
        },
    )

    worker._process_task(task)

    assert len(validation_calls) == 1
    assert [event for _, event, _ in published] == [
        "task.running",
        "task.failed",
    ]
    terminal_payload = published[-1][2]
    assert terminal_payload["validation_result"]["status"] == "error"
    assert (
        terminal_payload["validation_result"]["error_message"]
        == "validation_command_timeout"
    )
    assert terminal_payload["errors"][-1] == "validation_error"
    artifacts = _fetch_coding_result_artifacts(store, run_id)
    assert len(artifacts) == 1
    assert (
        artifacts[0]["content_json"]["validation_results"]["status"] == "error"
    )
    assert (
        artifacts[0]["content_json"]["validation_results"]["error_message"]
        == "validation_command_timeout"
    )
    run_state = _fetch_run_state(store, run_id)
    assert run_state is not None
    assert run_state["status"] == "failed"


def test_successful_completion_writes_one_result_message_with_lineage(
    db,
    monkeypatch,
) -> None:
    seeded = _seed_source_context(db)
    store = _make_store(db)
    deployment_id, run_id = _seed_execution_run(
        store,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        user_id=seeded["user_id"],
        project_id=seeded["project_id"],
    )
    worker = coding_worker.CodingWorker(agent_store=store)
    published = _capture_task_events(monkeypatch)
    calls = _install_fake_adapter(
        monkeypatch,
        SimpleNamespace(
            status="ok",
            summary="Implemented the return-path fix.",
            files_changed=(
                "guardian/workers/coding_worker.py",
                "guardian/agents/store.py",
            ),
            artifacts=(
                {
                    "path": "guardian/workers/coding_worker.py",
                    "commit_hash": "abc123def",
                    "validation_results": {"pytest": "passed"},
                },
            ),
            errors=(),
            adapter_session_ref="pi-session-123",
        ),
    )

    task = _build_task(
        run_id=run_id,
        deployment_id=deployment_id,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
    )
    worker._process_task(task)

    assert len(calls) == 1
    assert [event for _, event, _ in published] == [
        "task.running",
        "task.completed",
    ]
    messages = _fetch_thread_messages(db, seeded["thread_id"])
    assert len(messages) == 1
    message = messages[0]
    assert message.role == "assistant"
    assert message.kind == "coding_result"
    assert message.extra_meta["run_id"] == run_id
    assert message.extra_meta["coding_task_id"] == task.coding_task_id
    assert message.extra_meta["attempt_id"] == task.attempt_id
    assert message.extra_meta["adapter_kind"] == "pi_codex_runner"
    assert message.extra_meta["source_thread_id"] == seeded["thread_id"]
    assert (
        message.extra_meta["source_message_id"] == seeded["source_message_id"]
    )
    assert message.extra_meta["user_id"] == seeded["user_id"]
    assert message.extra_meta["project_id"] == seeded["project_id"]
    assert message.extra_meta["coding_result_status"] == "ok"
    assert message.extra_meta["result_captured_by_guardian"] is True
    assert message.extra_meta["files_changed"] == [
        "guardian/workers/coding_worker.py",
        "guardian/agents/store.py",
    ]
    assert message.extra_meta["artifacts"] == [
        {
            "path": "guardian/workers/coding_worker.py",
            "commit_hash": "abc123def",
            "validation_results": {"pytest": "passed"},
        }
    ]
    assert message.extra_meta["adapter_session_ref"] == "pi-session-123"
    assert message.extra_meta["commit_hash"] == "abc123def"
    assert "abc123def" in message.content
    assert '"pytest": "passed"' in message.content
    assert "guardian/workers/coding_worker.py" in message.content
    run_state = _fetch_run_state(store, run_id)
    assert run_state is not None
    assert run_state["status"] == "succeeded"
    artifacts = _fetch_coding_result_artifacts(store, run_id)
    assert len(artifacts) == 1
    assert artifacts[0]["content_json"]["delivery_ok"] is True
    assert artifacts[0]["content_json"]["commit_hash"] == "abc123def"
    assert artifacts[0]["content_json"]["result_captured_by_guardian"] is True
    assert artifacts[0]["content_json"]["coding_result_status"] == "ok"
    source_message = _fetch_message(db, seeded["source_message_id"])
    assert source_message is not None
    assert source_message.role == "user"
    assert source_message.kind == "chat"
    assert source_message.content == "Please patch the return path."
    assert source_message.extra_meta == {}


def test_duplicate_finalization_does_not_duplicate_return_messages(
    db,
    monkeypatch,
) -> None:
    seeded = _seed_source_context(
        db, user_id="user-2", project_name="project-2"
    )
    store = _make_store(db)
    deployment_id, run_id = _seed_execution_run(
        store,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        user_id=seeded["user_id"],
        project_id=seeded["project_id"],
    )
    worker = coding_worker.CodingWorker(agent_store=store)
    _capture_task_events(monkeypatch)
    _install_fake_adapter(
        monkeypatch,
        SimpleNamespace(
            status="ok",
            summary="Repeatable completion.",
            artifacts=(),
            errors=(),
        ),
    )

    task = _build_task(
        run_id=run_id,
        deployment_id=deployment_id,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        coding_task_id="coding-task-dup",
        attempt_id="attempt-dup",
    )
    worker._process_task(task)
    worker._process_task(task)

    messages = _fetch_thread_messages(db, seeded["thread_id"])
    artifacts = _fetch_coding_result_artifacts(store, run_id)
    assert len(messages) == 1
    assert len(artifacts) == 1


def test_partial_success_still_persists_a_result_message(
    db,
    monkeypatch,
) -> None:
    seeded = _seed_source_context(
        db, user_id="user-1b", project_name="project-1b"
    )
    store = _make_store(db)
    deployment_id, run_id = _seed_execution_run(
        store,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        user_id=seeded["user_id"],
        project_id=seeded["project_id"],
    )
    worker = coding_worker.CodingWorker(agent_store=store)
    published = _capture_task_events(monkeypatch)
    _install_fake_adapter(
        monkeypatch,
        SimpleNamespace(
            status="partial_success",
            summary="Core fix landed; follow-up cleanup remains.",
            files_changed=("guardian/agents/store.py",),
            artifacts=(
                {
                    "path": "notes/cleanup.md",
                    "description": "Follow-up cleanup list",
                },
            ),
            errors=("follow-up cleanup remains",),
            adapter_session_ref="pi-session-partial",
        ),
    )

    task = _build_task(
        run_id=run_id,
        deployment_id=deployment_id,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        coding_task_id="coding-task-partial",
        attempt_id="attempt-partial",
    )
    worker._process_task(task)

    assert [event for _, event, _ in published] == [
        "task.running",
        "task.completed",
    ]
    messages = _fetch_thread_messages(db, seeded["thread_id"])
    assert len(messages) == 1
    message = messages[0]
    assert message.extra_meta["coding_result_status"] == "partial_success"
    assert message.extra_meta["attempt_id"] == task.attempt_id
    assert message.extra_meta["adapter_session_ref"] == "pi-session-partial"
    assert message.extra_meta["files_changed"] == ["guardian/agents/store.py"]
    assert message.extra_meta["result_captured_by_guardian"] is True
    assert "PARTIAL_SUCCESS" in message.content
    run_state = _fetch_run_state(store, run_id)
    assert run_state is not None
    assert run_state["status"] == "succeeded"


def test_missing_source_thread_fails_closed_without_fallback_write(
    db,
    monkeypatch,
) -> None:
    store = _make_store(db)
    deployment_id, run_id = _seed_execution_run(
        store,
        thread_id=None,
        source_message_id=None,
        user_id="user-3",
        project_id=None,
    )
    worker = coding_worker.CodingWorker(agent_store=store)
    published = _capture_task_events(monkeypatch)
    _install_fake_adapter(
        monkeypatch,
        SimpleNamespace(
            status="ok",
            summary="Should never be visible.",
            artifacts=(),
            errors=(),
        ),
    )

    task = _build_task(
        run_id=run_id,
        deployment_id=deployment_id,
        thread_id=999,
        source_message_id=None,
        coding_task_id="coding-task-missing-thread",
        attempt_id="attempt-missing-thread",
    )
    worker._process_task(task)

    assert [event for _, event, _ in published] == [
        "task.running",
        "task.failed",
    ]
    run_state = _fetch_run_state(store, run_id)
    assert run_state is not None
    assert run_state["status"] == "failed"
    assert _fetch_thread_messages(db, 999) == []
    assert _fetch_coding_result_artifacts(store, run_id)


def test_adapter_failure_does_not_create_a_success_result_message(
    db,
    monkeypatch,
) -> None:
    seeded = _seed_source_context(
        db, user_id="user-5", project_name="project-5"
    )
    store = _make_store(db)
    deployment_id, run_id = _seed_execution_run(
        store,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        user_id=seeded["user_id"],
        project_id=seeded["project_id"],
    )
    worker = coding_worker.CodingWorker(agent_store=store)
    published = _capture_task_events(monkeypatch)
    _install_fake_adapter(
        monkeypatch,
        SimpleNamespace(
            status="error",
            summary="The adapter failed before any durable result could be shown.",
            files_changed=("guardian/agents/store.py",),
            artifacts=(
                {
                    "path": "logs/failure.txt",
                    "description": "fatal adapter failure",
                },
            ),
            errors=("fatal adapter failure",),
            error_code="adapter_failed",
            error_message="fatal adapter failure",
            adapter_session_ref="pi-session-failed",
        ),
    )

    task = _build_task(
        run_id=run_id,
        deployment_id=deployment_id,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        coding_task_id="coding-task-failure",
        attempt_id="attempt-failure",
    )
    worker._process_task(task)

    assert [event for _, event, _ in published] == [
        "task.running",
        "task.failed",
    ]
    assert _fetch_thread_messages(db, seeded["thread_id"]) == []
    run_state = _fetch_run_state(store, run_id)
    assert run_state is not None
    assert run_state["status"] == "failed"
    artifacts = _fetch_coding_result_artifacts(store, run_id)
    assert len(artifacts) == 1
    content = artifacts[0]["content_json"]
    assert content["coding_result_status"] == "error"
    assert content["result_captured_by_guardian"] is True
    assert content["delivery_ok"] is False
    assert content["message_id"] is None
    assert content["adapter_session_ref"] == "pi-session-failed"
    source_message = _fetch_message(db, seeded["source_message_id"])
    assert source_message is not None
    assert source_message.content == "Please patch the return path."


def test_cross_user_scope_mismatch_fails_closed(db, monkeypatch) -> None:
    seeded = _seed_source_context(
        db,
        user_id="source-user",
        thread_user_id="other-user",
        project_name="project-3",
    )
    store = _make_store(db)
    deployment_id, run_id = _seed_execution_run(
        store,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        user_id=seeded["user_id"],
        project_id=seeded["project_id"],
    )
    worker = coding_worker.CodingWorker(agent_store=store)
    published = _capture_task_events(monkeypatch)
    _install_fake_adapter(
        monkeypatch,
        SimpleNamespace(
            status="ok",
            summary="Scope mismatch should block delivery.",
            artifacts=(),
            errors=(),
        ),
    )

    task = _build_task(
        run_id=run_id,
        deployment_id=deployment_id,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        coding_task_id="coding-task-scope",
        attempt_id="attempt-scope",
    )
    worker._process_task(task)

    assert [event for _, event, _ in published] == [
        "task.running",
        "task.failed",
    ]
    messages = _fetch_thread_messages(db, seeded["thread_id"])
    assert messages == []
    run_state = _fetch_run_state(store, run_id)
    assert run_state is not None
    assert run_state["status"] == "failed"


def test_delivery_failure_is_observable_and_persists_result_artifact(
    db,
    monkeypatch,
) -> None:
    seeded = _seed_source_context(
        db, user_id="user-4", project_name="project-4"
    )
    store = _make_store(db)
    deployment_id, run_id = _seed_execution_run(
        store,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        user_id=seeded["user_id"],
        project_id=seeded["project_id"],
    )
    worker = coding_worker.CodingWorker(agent_store=store)
    published = _capture_task_events(monkeypatch)
    _install_fake_adapter(
        monkeypatch,
        SimpleNamespace(
            status="ok",
            summary="Delivery should fail after the durable artifact is written.",
            artifacts=(),
            errors=(),
        ),
    )
    monkeypatch.setattr(
        store,
        "_inject_coding_result_into_thread",
        lambda **_kwargs: (None, "delivery_database_unavailable"),
    )

    task = _build_task(
        run_id=run_id,
        deployment_id=deployment_id,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        coding_task_id="coding-task-delivery",
        attempt_id="attempt-delivery",
    )
    worker._process_task(task)

    assert [event for _, event, _ in published] == [
        "task.running",
        "task.failed",
    ]
    assert _fetch_thread_messages(db, seeded["thread_id"]) == []
    run_state = _fetch_run_state(store, run_id)
    assert run_state is not None
    assert run_state["status"] == "failed"
    artifacts = _fetch_coding_result_artifacts(store, run_id)
    assert len(artifacts) == 1
    assert artifacts[0]["content_json"]["delivery_ok"] is False
    assert (
        artifacts[0]["content_json"]["delivery_reason"]
        == "delivery_database_unavailable"
    )
