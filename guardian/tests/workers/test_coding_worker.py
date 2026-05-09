from __future__ import annotations

import subprocess
from contextlib import suppress
from pathlib import Path
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
    cwd: str = "/workspace/repo",
    validation_command: str | None = None,
    max_validation_attempts: int | None = None,
    permission_policy: dict[str, Any] | None = None,
) -> CodingExecutionTask:
    payload: dict[str, Any] = {
        "task_id": f"task-{coding_task_id}",
        "run_id": run_id,
        "deployment_id": deployment_id,
        "instructions": "Patch the seam and keep the return path intact.",
        "cwd": cwd,
        "timeout_seconds": 60,
        "coding_task_id": coding_task_id,
        "attempt_id": attempt_id,
        "thread_id": thread_id,
        "source_message_id": source_message_id,
    }
    if validation_command is not None:
        payload["validation_command"] = validation_command
    if max_validation_attempts is not None:
        payload["max_validation_attempts"] = max_validation_attempts
    if permission_policy is not None:
        payload["permission_policy"] = permission_policy
    return CodingExecutionTask.from_dict(payload)


def test_coding_execution_task_from_dict_accepts_missing_validation_fields() -> (
    None
):
    task = CodingExecutionTask.from_dict(
        {
            "task_id": "task-1",
            "run_id": "run-1",
            "deployment_id": "dep-1",
            "instructions": "Do the thing.",
            "cwd": "/workspace/repo",
            "timeout_seconds": 30,
            "coding_task_id": "coding-task-1",
            "attempt_id": "attempt-1",
            "thread_id": 7,
            "source_message_id": 11,
        }
    )

    assert task.validation_command is None
    assert task.max_validation_attempts is None


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
    real_run = subprocess.run

    def _fake_run(
        argv: list[str],
        *,
        cwd: str | None = None,
        capture_output: bool | None = None,
        text: bool | None = None,
        check: bool | None = None,
        timeout: int | float | None = None,
        ) -> subprocess.CompletedProcess[str]:
        if argv and str(argv[0]) == "git":
            return real_run(
                argv,
                cwd=cwd,
                capture_output=capture_output,
                text=text,
                check=check,
                timeout=timeout,
            )
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


def _run_git(repo_root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def _init_git_repo(
    tmp_path: Path,
    *,
    tracked_files: dict[str, str] | None = None,
) -> Path:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _run_git(repo_root, "init")
    _run_git(repo_root, "config", "user.email", "codex@example.com")
    _run_git(repo_root, "config", "user.name", "Codex")
    for relative_path, content in (tracked_files or {}).items():
        target = repo_root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
    if tracked_files:
        _run_git(repo_root, "add", ".")
        _run_git(repo_root, "commit", "-m", "initial commit")
    return repo_root


def _install_repo_mutating_adapter(
    monkeypatch,
    result: Any,
    *,
    writes: dict[str, str] | None = None,
    adapter_kind: str = "pi_codex_runner",
) -> list[SimpleNamespace]:
    calls: list[SimpleNamespace] = []

    class _FakeAdapter:
        def execute(self, request: Any) -> Any:
            calls.append(request)
            if writes:
                cwd = Path(str(getattr(request, "cwd", "") or ""))
                for relative_path, content in writes.items():
                    target = cwd / relative_path
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(content)
            return result

    monkeypatch.setattr(
        coding_worker, "ADAPTERS", {adapter_kind: _FakeAdapter()}
    )
    return calls


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
        "task.attempt_started",
        "task.completed",
    ]
    terminal_payload = published[-1][2]
    assert terminal_payload["coding_result_status"] == "ok"
    assert terminal_payload["validation_result"]["status"] == "passed"
    assert terminal_payload["validation_result"]["tests_passed"] == 2
    assert terminal_payload["validation_attempt_count"] == 1
    messages = _fetch_thread_messages(db, seeded["thread_id"])
    assert len(messages) == 1
    message = messages[0]
    assert message.extra_meta["validation_results"]["status"] == "passed"
    assert message.extra_meta["validation_results"]["command"] == "pytest -q"
    assert message.extra_meta["validation_results"]["status"] == "passed"
    artifacts = _fetch_coding_result_artifacts(store, run_id)
    assert len(artifacts) == 1
    assert (
        artifacts[0]["content_json"]["validation_results"]["status"] == "passed"
    )
    assert (
        artifacts[0]["content_json"]["validation_results"]["command"]
        == "pytest -q"
    )
    assert artifacts[0]["content_json"]["validation_attempt_count"] == 1
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
        max_validation_attempts=1,
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
        "task.attempt_started",
        "task.validation_failed",
        "task.failed",
    ]
    terminal_payload = published[-1][2]
    assert terminal_payload["coding_result_status"] == "failed"
    assert terminal_payload["validation_result"]["status"] == "failed"
    assert terminal_payload["errors"][-1] == "validation_failed"
    assert terminal_payload["validation_attempt_count"] == 1
    assert terminal_payload["error_code"] == "VALIDATION_FAILED"
    messages = _fetch_thread_messages(db, seeded["thread_id"])
    assert messages == []
    artifacts = _fetch_coding_result_artifacts(store, run_id)
    assert len(artifacts) == 1
    content = artifacts[0]["content_json"]
    assert content["coding_result_status"] == "failed"
    assert content["validation_results"]["status"] == "failed"
    assert content["validation_results"]["fail_signature"] is not None
    assert content["validation_attempt_count"] == 1
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
    published = _capture_task_events(monkeypatch)
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
    assert [event for _, event, _ in published] == [
        "task.running",
        "task.attempt_started",
        "task.failed",
    ]
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
        "task.attempt_started",
        "task.completed",
    ]
    terminal_payload = published[-1][2]
    assert terminal_payload["validation_result"]["status"] == "not_run"
    assert terminal_payload["validation_attempt_count"] == 1
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
        max_validation_attempts=1,
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
        "task.attempt_started",
        "task.validation_failed",
        "task.failed",
    ]
    terminal_payload = published[-1][2]
    assert terminal_payload["validation_result"]["status"] == "error"
    assert (
        terminal_payload["validation_result"]["error_message"]
        == "validation_command_timeout"
    )
    assert terminal_payload["validation_attempt_count"] == 1
    assert terminal_payload["error_code"] == "VALIDATION_FAILED"
    assert terminal_payload["errors"][-1] == "validation_failed"
    artifacts = _fetch_coding_result_artifacts(store, run_id)
    assert len(artifacts) == 1
    assert (
        artifacts[0]["content_json"]["validation_results"]["status"] == "error"
    )
    assert (
        artifacts[0]["content_json"]["validation_results"]["error_message"]
        == "validation_command_timeout"
    )
    assert artifacts[0]["content_json"]["validation_attempt_count"] == 1
    run_state = _fetch_run_state(store, run_id)
    assert run_state is not None
    assert run_state["status"] == "failed"


def test_validation_runtime_error_is_normalized_and_fails_closed(
    db,
    monkeypatch,
    tmp_path,
) -> None:
    repo_root = _init_git_repo(
        tmp_path,
        tracked_files={"README.md": "seed\n"},
    )
    seeded = _seed_source_context(
        db, user_id="validation-retry-user", project_name="validation-retry"
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
    validation_results = iter(
        [
            subprocess.CompletedProcess(
                args=["pytest", "-q"],
                returncode=1,
                stdout="FAILED tests/unit/test_alpha.py::test_something - boom\n",
                stderr="E AssertionError: boom\n",
            ),
            subprocess.CompletedProcess(
                args=["pytest", "-q"],
                returncode=0,
                stdout="2 passed in 0.02s\n",
                stderr="",
                ),
            ]
        )
    validation_calls: list[dict[str, Any]] = []
    real_run = subprocess.run

    def _sequenced_validation_run(
        argv: list[str],
        *,
        cwd: str | None = None,
        capture_output: bool | None = None,
        text: bool | None = None,
        check: bool | None = None,
        timeout: int | float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        if argv and str(argv[0]) == "git":
            return real_run(
                argv,
                cwd=cwd,
                capture_output=capture_output,
                text=text,
                check=check,
                timeout=timeout,
            )
        validation_calls.append(
            {
                "argv": list(argv),
                "cwd": cwd,
                "capture_output": capture_output,
                "text": text,
                "check": check,
                "timeout": timeout,
            }
        )
        return next(validation_results)

    monkeypatch.setattr(
        coding_worker.subprocess, "run", _sequenced_validation_run
    )

    task = _build_task(
        run_id=run_id,
        deployment_id=deployment_id,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        coding_task_id="coding-task-validation-retry",
        cwd=str(repo_root),
        validation_command="pytest -q",
        max_validation_attempts=2,
        permission_policy={
            "allow_shell": True,
            "allow_network": False,
            "allow_write": True,
            "allowed_paths": ["src/"],
            "max_runtime_seconds": 60,
        },
    )

    worker._process_task(task)

    assert len(calls) == 2
    assert len(validation_calls) == 2
    assert [event for _, event, _ in published] == [
        "task.running",
        "task.attempt_started",
        "task.validation_failed",
        "task.retrying",
        "task.attempt_started",
        "task.completed",
    ]
    second_prompt = calls[1].prompt
    assert "Validation feedback:" in second_prompt
    assert "pytest -q" in second_prompt
    assert "Fail signature:" in second_prompt
    assert "Fix only the original task scope" in second_prompt
    terminal_payload = published[-1][2]
    assert terminal_payload["coding_result_status"] == "ok"
    assert terminal_payload["validation_result"]["status"] == "passed"
    assert terminal_payload["validation_attempt_count"] == 2
    assert terminal_payload["best_validation_result"]["status"] == "passed"
    assert len(terminal_payload["validation_attempts"]) == 2
    artifacts = _fetch_coding_result_artifacts(store, run_id)
    assert len(artifacts) == 1
    content = artifacts[0]["content_json"]
    assert content["validation_results"]["status"] == "passed"
    assert content["validation_attempt_count"] == 2
    assert len(content["validation_attempts"]) == 2
    messages = _fetch_thread_messages(db, seeded["thread_id"])
    assert len(messages) == 1
    assert messages[0].extra_meta["validation_results"]["status"] == "passed"
    run_state = _fetch_run_state(store, run_id)
    assert run_state is not None
    assert run_state["status"] == "succeeded"


def test_validation_failure_across_all_attempts_emits_terminal_failure(
    db,
    monkeypatch,
    tmp_path,
) -> None:
    repo_root = _init_git_repo(
        tmp_path,
        tracked_files={"README.md": "seed\n"},
    )
    seeded = _seed_source_context(
        db,
        user_id="validation-exhausted-user",
        project_name="validation-exhausted",
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
        side_effect=RuntimeError("boom"),
    validation_results = iter(
        [
            subprocess.CompletedProcess(
                args=["pytest", "-q"],
                returncode=1,
                stdout="FAILED tests/unit/test_alpha.py::test_something - boom\n",
                stderr="E AssertionError: boom\n",
            ),
            subprocess.CompletedProcess(
                args=["pytest", "-q"],
                returncode=1,
                stdout="FAILED tests/unit/test_beta.py::test_other - still broken\n",
                stderr="E AssertionError: still broken\n",
                ),
            ]
        )
    validation_calls: list[dict[str, Any]] = []
    real_run = subprocess.run

    def _sequenced_validation_run(
        argv: list[str],
        *,
        cwd: str | None = None,
        capture_output: bool | None = None,
        text: bool | None = None,
        check: bool | None = None,
        timeout: int | float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        if argv and str(argv[0]) == "git":
            return real_run(
                argv,
                cwd=cwd,
                capture_output=capture_output,
                text=text,
                check=check,
                timeout=timeout,
            )
        validation_calls.append(
            {
                "argv": list(argv),
                "cwd": cwd,
                "capture_output": capture_output,
                "text": text,
                "check": check,
                "timeout": timeout,
            }
        )
        return next(validation_results)

    monkeypatch.setattr(
        coding_worker.subprocess, "run", _sequenced_validation_run
    )
    task = _build_task(
        run_id=run_id,
        deployment_id=deployment_id,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        coding_task_id="coding-task-validation-exhausted",
        cwd=str(repo_root),
        validation_command="pytest -q",
        permission_policy={
            "allow_shell": True,
            "allow_network": False,
            "allow_write": True,
            "allowed_paths": ["src/"],
            "max_runtime_seconds": 60,
        },
    )

    worker._process_task(task)

    assert len(validation_calls) == 1
    assert [event for _, event, _ in published] == [
        "task.running",
        "task.attempt_started",
        "task.validation_failed",
        "task.failed",
    ]
    terminal_payload = published[-1][2]
    assert terminal_payload["coding_result_status"] == "failed"
    assert terminal_payload["validation_result"]["status"] == "error"
    assert terminal_payload["validation_result"]["error_message"].startswith(
        "validation_command_error:"
    )
    assert terminal_payload["error_code"] == "VALIDATION_FAILED"
    artifacts = _fetch_coding_result_artifacts(store, run_id)
    assert len(artifacts) == 1
    content = artifacts[0]["content_json"]
    assert content["validation_results"]["status"] == "error"
    assert content["validation_results"]["error_message"].startswith(
        "validation_command_error:"
    )
    messages = _fetch_thread_messages(db, seeded["thread_id"])
    assert messages == []
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
    assert message.extra_meta["artifacts"][0] == {
        "path": "guardian/workers/coding_worker.py",
        "commit_hash": "abc123def",
        "validation_results": {"pytest": "passed"},
    }
    assert message.extra_meta["artifacts"][-1]["kind"] == "mutation_guard"
    assert message.extra_meta["artifacts"][-1]["mutation_guard_status"] == (
        "unverified"
    )
    assert message.extra_meta["artifacts"][-1]["mutation_guard_error_code"] == (
        "MUTATION_SCOPE_UNVERIFIED"
    )
    assert message.extra_meta["artifacts"][-1]["mutation_guard_enabled"] is True
    assert message.extra_meta["artifacts"][-1]["changed_paths"] == []
    assert message.extra_meta["artifacts"][-1]["disallowed_paths"] == []
    assert message.extra_meta["artifacts"][-1]["allowed_paths"] == []
    assert len(message.extra_meta["artifacts"]) == 2
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


def test_clean_repo_allowed_path_mutation_passes_scope_guard(
    db,
    monkeypatch,
    tmp_path,
) -> None:
    repo_root = _init_git_repo(
        tmp_path,
        tracked_files={"README.md": "seed\n"},
    )
    seeded = _seed_source_context(
        db,
        user_id="allowed-mutation-user",
        project_name="allowed-mutation",
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
    calls = _install_repo_mutating_adapter(
        monkeypatch,
        SimpleNamespace(
            status="ok",
            summary="Allowed mutation applied.",
            files_changed=("src/app.py",),
            artifacts=(),
            errors=(),
            adapter_session_ref="session-allowed",
        ),
        writes={"src/app.py": "print('ok')\n"},
        adapter_kind="codex",
    )

    task = _build_task(
        run_id=run_id,
        deployment_id=deployment_id,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        coding_task_id="coding-task-guard-allowed",
        cwd=str(repo_root),
        permission_policy={
            "allow_shell": False,
            "allow_network": False,
            "allow_write": True,
            "allowed_paths": ["src/app.py"],
            "max_runtime_seconds": 60,
        },
    )
    worker._process_task(task)

    assert len(calls) == 1
    assert [event for _, event, _ in published] == [
        "task.running",
        "task.completed",
    ]
    terminal_payload = published[-1][2]
    assert terminal_payload["mutation_guard_status"] == "verified"
    assert terminal_payload["mutation_guard_error_code"] is None
    assert terminal_payload["changed_paths"] == ["src/app.py"]
    assert terminal_payload["disallowed_paths"] == []
    messages = _fetch_thread_messages(db, seeded["thread_id"])
    assert len(messages) == 1
    guard_artifact = messages[0].extra_meta["artifacts"][-1]
    assert guard_artifact["kind"] == "mutation_guard"
    assert guard_artifact["mutation_guard_status"] == "verified"
    assert guard_artifact["changed_paths"] == ["src/app.py"]


def test_clean_repo_disallowed_path_mutation_fails_with_mutation_scope_violation(
    db,
    monkeypatch,
    tmp_path,
) -> None:
    repo_root = _init_git_repo(
        tmp_path,
        tracked_files={"README.md": "seed\n"},
    )
    seeded = _seed_source_context(
        db,
        user_id="disallowed-mutation-user",
        project_name="disallowed-mutation",
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
    calls = _install_repo_mutating_adapter(
        monkeypatch,
        SimpleNamespace(
            status="ok",
            summary="This mutation escapes the approved scope.",
            files_changed=("docs/bad.md",),
            artifacts=(),
            errors=(),
        ),
        writes={"docs/bad.md": "blocked\n"},
        adapter_kind="codex",
    )

    task = _build_task(
        run_id=run_id,
        deployment_id=deployment_id,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        coding_task_id="coding-task-guard-disallowed",
        cwd=str(repo_root),
        permission_policy={
            "allow_shell": False,
            "allow_network": False,
            "allow_write": True,
            "allowed_paths": ["src/"],
            "max_runtime_seconds": 60,
        },
    )
    worker._process_task(task)

    assert len(calls) == 1
    assert [event for _, event, _ in published] == [
        "task.running",
        "task.failed",
    ]
    terminal_payload = published[-1][2]
    assert terminal_payload["error_code"] == "MUTATION_SCOPE_VIOLATION"
    assert terminal_payload["mutation_guard_status"] == "violated"
    assert "docs/bad.md" in terminal_payload["changed_paths"]
    assert "docs/bad.md" in terminal_payload["disallowed_paths"]
    assert _fetch_thread_messages(db, seeded["thread_id"]) == []


def test_allow_write_false_mutation_fails_closed(
    db,
    monkeypatch,
    tmp_path,
) -> None:
    repo_root = _init_git_repo(
        tmp_path,
        tracked_files={"README.md": "seed\n"},
    )
    seeded = _seed_source_context(
        db,
        user_id="readonly-mutation-user",
        project_name="readonly-mutation",
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
    calls = _install_repo_mutating_adapter(
        monkeypatch,
        SimpleNamespace(
            status="ok",
            summary="Any mutation should fail closed.",
            files_changed=("src/deny.py",),
            artifacts=(),
            errors=(),
        ),
        writes={"src/deny.py": "denied\n"},
        adapter_kind="codex",
    )

    task = _build_task(
        run_id=run_id,
        deployment_id=deployment_id,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        coding_task_id="coding-task-guard-readonly",
        cwd=str(repo_root),
        permission_policy={
            "allow_shell": False,
            "allow_network": False,
            "allow_write": False,
            "allowed_paths": ["src/"],
            "max_runtime_seconds": 60,
        },
    )
    worker._process_task(task)

    assert len(calls) == 1
    assert [event for _, event, _ in published] == [
        "task.running",
        "task.failed",
    ]
    terminal_payload = published[-1][2]
    assert terminal_payload["error_code"] == "MUTATION_SCOPE_VIOLATION"
    assert terminal_payload["mutation_guard_status"] == "violated"
    assert "src/deny.py" in terminal_payload["changed_paths"]
    assert "src/deny.py" in terminal_payload["disallowed_paths"]
    assert _fetch_thread_messages(db, seeded["thread_id"]) == []


def test_dirty_preflight_fails_before_adapter_execution(
    db,
    monkeypatch,
    tmp_path,
) -> None:
    repo_root = _init_git_repo(
        tmp_path,
        tracked_files={"README.md": "seed\n"},
    )
    dirty_file = repo_root / "stale.txt"
    dirty_file.write_text("dirty\n")
    seeded = _seed_source_context(
        db,
        user_id="dirty-preflight-user",
        project_name="dirty-preflight",
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
        SimpleNamespace(status="ok", summary="Should not run."),
        adapter_kind="codex",
    )

    task = _build_task(
        run_id=run_id,
        deployment_id=deployment_id,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        coding_task_id="coding-task-dirty-precheck",
        cwd=str(repo_root),
        permission_policy={
            "allow_shell": False,
            "allow_network": False,
            "allow_write": True,
            "allowed_paths": ["src/"],
            "max_runtime_seconds": 60,
        },
    )
    worker._process_task(task)

    assert calls == []
    assert [event for _, event, _ in published] == ["task.failed"]
    failure_payload = published[-1][2]
    assert failure_payload["error_code"] == "DIRTY_WORKTREE_PRECHECK_FAILED"
    assert failure_payload["mutation_guard_status"] == "precheck_failed"
    assert "stale.txt" in failure_payload["changed_paths"]
    assert _fetch_thread_messages(db, seeded["thread_id"]) == []


def test_validation_retry_does_not_continue_after_scope_violation(
    db,
    monkeypatch,
    tmp_path,
) -> None:
    repo_root = _init_git_repo(
        tmp_path,
        tracked_files={"README.md": "seed\n"},
    )
    seeded = _seed_source_context(
        db,
        user_id="scope-retry-user",
        project_name="scope-retry",
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
    calls = _install_repo_mutating_adapter(
        monkeypatch,
        SimpleNamespace(
            status="ok",
            summary="Scope violation should stop retries.",
            files_changed=("docs/bad.md",),
            artifacts=(),
            errors=(),
        ),
        writes={"docs/bad.md": "blocked\n"},
        adapter_kind="codex",
    )
    validation_calls: list[dict[str, Any]] = []
    real_run = subprocess.run
    validation_results = iter(
        [
            subprocess.CompletedProcess(
                args=["pytest", "-q"],
                returncode=1,
                stdout="FAILED tests/unit/test_alpha.py::test_something - boom\n",
                stderr="E AssertionError: boom\n",
            )
        ]
    )

    def _validation_run(
        argv: list[str],
        *,
        cwd: str | None = None,
        capture_output: bool | None = None,
        text: bool | None = None,
        check: bool | None = None,
        timeout: int | float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        if argv and str(argv[0]) == "git":
            return real_run(
                argv,
                cwd=cwd,
                capture_output=capture_output,
                text=text,
                check=check,
                timeout=timeout,
            )
        validation_calls.append(
            {
                "argv": list(argv),
                "cwd": cwd,
                "capture_output": capture_output,
                "text": text,
                "check": check,
                "timeout": timeout,
            }
        )
        return next(validation_results)

    monkeypatch.setattr(coding_worker.subprocess, "run", _validation_run)

    task = _build_task(
        run_id=run_id,
        deployment_id=deployment_id,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        coding_task_id="coding-task-scope-retry",
        cwd=str(repo_root),
        validation_command="pytest -q",
        max_validation_attempts=2,
        permission_policy={
            "allow_shell": True,
            "allow_network": False,
            "allow_write": True,
            "allowed_paths": ["src/"],
            "max_runtime_seconds": 60,
        },
    )
    worker._process_task(task)

    assert len(calls) == 1
    assert validation_calls == []
    assert [event for _, event, _ in published] == [
        "task.running",
        "task.attempt_started",
        "task.failed",
    ]
    assert all(event != "task.retrying" for _, event, _ in published)
    terminal_payload = published[-1][2]
    assert terminal_payload["error_code"] == "MUTATION_SCOPE_VIOLATION"
    assert terminal_payload["mutation_guard_status"] == "violated"
    assert terminal_payload["validation_attempt_count"] is None
    assert terminal_payload["validation_result"] is None
    assert _fetch_thread_messages(db, seeded["thread_id"]) == []


def test_allowed_directory_prefix_mutation_passes_scope_guard(
    db,
    monkeypatch,
    tmp_path,
) -> None:
    repo_root = _init_git_repo(
        tmp_path,
        tracked_files={"README.md": "seed\n"},
    )
    seeded = _seed_source_context(
        db,
        user_id="prefix-user",
        project_name="prefix-user",
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
    calls = _install_repo_mutating_adapter(
        monkeypatch,
        SimpleNamespace(
            status="ok",
            summary="Directory prefix allowed.",
            files_changed=("src/module/file.py",),
            artifacts=(),
            errors=(),
        ),
        writes={"src/module/file.py": "print('prefix')\n"},
        adapter_kind="codex",
    )

    task = _build_task(
        run_id=run_id,
        deployment_id=deployment_id,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        coding_task_id="coding-task-prefix",
        cwd=str(repo_root),
        permission_policy={
            "allow_shell": False,
            "allow_network": False,
            "allow_write": True,
            "allowed_paths": ["src/"],
            "max_runtime_seconds": 60,
        },
    )
    worker._process_task(task)

    assert len(calls) == 1
    assert [event for _, event, _ in published] == [
        "task.running",
        "task.completed",
    ]
    terminal_payload = published[-1][2]
    assert terminal_payload["mutation_guard_status"] == "verified"
    assert terminal_payload["changed_paths"] == ["src/module/file.py"]
    assert terminal_payload["disallowed_paths"] == []


def test_allowed_glob_pattern_mutation_passes_scope_guard(
    db,
    monkeypatch,
    tmp_path,
) -> None:
    repo_root = _init_git_repo(
        tmp_path,
        tracked_files={"README.md": "seed\n"},
    )
    seeded = _seed_source_context(
        db,
        user_id="glob-user",
        project_name="glob-user",
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
    calls = _install_repo_mutating_adapter(
        monkeypatch,
        SimpleNamespace(
            status="ok",
            summary="Glob pattern allowed.",
            files_changed=("docs/notes.md",),
            artifacts=(),
            errors=(),
        ),
        writes={"docs/notes.md": "glob\n"},
        adapter_kind="codex",
    )

    task = _build_task(
        run_id=run_id,
        deployment_id=deployment_id,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        coding_task_id="coding-task-glob",
        cwd=str(repo_root),
        permission_policy={
            "allow_shell": False,
            "allow_network": False,
            "allow_write": True,
            "allowed_paths": ["docs/*.md"],
            "max_runtime_seconds": 60,
        },
    )
    worker._process_task(task)

    assert len(calls) == 1
    assert [event for _, event, _ in published] == [
        "task.running",
        "task.completed",
    ]
    terminal_payload = published[-1][2]
    assert terminal_payload["mutation_guard_status"] == "verified"
    assert terminal_payload["changed_paths"] == ["docs/notes.md"]
    assert terminal_payload["disallowed_paths"] == []


def test_absolute_or_parent_policy_paths_do_not_escape_repo(
    db,
    monkeypatch,
    tmp_path,
) -> None:
    repo_root = _init_git_repo(
        tmp_path,
        tracked_files={"README.md": "seed\n"},
    )
    seeded = _seed_source_context(
        db,
        user_id="unsafe-policy-user",
        project_name="unsafe-policy",
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
    calls = _install_repo_mutating_adapter(
        monkeypatch,
        SimpleNamespace(
            status="ok",
            summary="Unsafe policy paths must be ignored.",
            files_changed=("src/escaped.py",),
            artifacts=(),
            errors=(),
        ),
        writes={"src/escaped.py": "blocked\n"},
        adapter_kind="codex",
    )

    task = _build_task(
        run_id=run_id,
        deployment_id=deployment_id,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        coding_task_id="coding-task-unsafe-policy",
        cwd=str(repo_root),
        permission_policy={
            "allow_shell": False,
            "allow_network": False,
            "allow_write": True,
            "allowed_paths": ["/tmp/*", "../*", "docs/../safe/"],
            "max_runtime_seconds": 60,
        },
    )
    worker._process_task(task)

    assert len(calls) == 1
    assert [event for _, event, _ in published] == [
        "task.running",
        "task.failed",
    ]
    terminal_payload = published[-1][2]
    assert terminal_payload["error_code"] == "MUTATION_SCOPE_VIOLATION"
    assert terminal_payload["mutation_guard_status"] == "violated"
    assert terminal_payload["allowed_paths"] == []
    assert "src/escaped.py" in terminal_payload["disallowed_paths"]


def test_non_git_cwd_emits_unverified_mutation_guard_metadata(
    db,
    monkeypatch,
    tmp_path,
) -> None:
    cwd = tmp_path / "scratch"
    cwd.mkdir()
    seeded = _seed_source_context(
        db,
        user_id="non-git-user",
        project_name="non-git",
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
            summary="Non-git cwd should degrade explicitly.",
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
        coding_task_id="coding-task-non-git",
        cwd=str(cwd),
        permission_policy={
            "allow_shell": False,
            "allow_network": False,
            "allow_write": True,
            "allowed_paths": ["scratch/"],
            "max_runtime_seconds": 60,
        },
    )
    worker._process_task(task)

    assert len(calls) == 1
    assert [event for _, event, _ in published] == [
        "task.running",
        "task.completed",
    ]
    terminal_payload = published[-1][2]
    assert terminal_payload["mutation_guard_status"] == "unverified"
    assert terminal_payload["mutation_guard_error_code"] == (
        "MUTATION_SCOPE_UNVERIFIED"
    )
    assert terminal_payload["changed_paths"] == []
    assert terminal_payload["disallowed_paths"] == []


def test_changed_path_metadata_is_bounded_and_truncated(
    db,
    monkeypatch,
    tmp_path,
) -> None:
    repo_root = _init_git_repo(
        tmp_path,
        tracked_files={"README.md": "seed\n"},
    )
    seeded = _seed_source_context(
        db,
        user_id="bounded-user",
        project_name="bounded-user",
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
    writes = {
        f"src/file-{index}.txt": f"{index}\n" for index in range(55)
    }
    calls = _install_repo_mutating_adapter(
        monkeypatch,
        SimpleNamespace(
            status="ok",
            summary="Many changes within scope.",
            files_changed=tuple(writes.keys()),
            artifacts=(),
            errors=(),
        ),
        writes=writes,
        adapter_kind="codex",
    )

    task = _build_task(
        run_id=run_id,
        deployment_id=deployment_id,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        coding_task_id="coding-task-bounded",
        cwd=str(repo_root),
        permission_policy={
            "allow_shell": False,
            "allow_network": False,
            "allow_write": True,
            "allowed_paths": ["src/"],
            "max_runtime_seconds": 60,
        },
    )
    worker._process_task(task)

    assert len(calls) == 1
    assert [event for _, event, _ in published] == [
        "task.running",
        "task.completed",
    ]
    terminal_payload = published[-1][2]
    assert terminal_payload["mutation_guard_status"] == "verified"
    assert terminal_payload["changed_paths_truncated"] is True
    assert terminal_payload["changed_paths_total"] == 55
    assert len(terminal_payload["changed_paths"]) == 50
    assert terminal_payload["disallowed_paths"] == []
