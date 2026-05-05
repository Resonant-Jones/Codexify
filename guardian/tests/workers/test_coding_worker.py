from __future__ import annotations

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


def _seed_execution_run(
    store: AgentStore,
    *,
    thread_id: int | None,
    source_message_id: int | None,
    user_id: str | None,
    project_id: int | None,
    runtime_target: str = "container",
) -> tuple[str, str]:
    deployment = store.create_deployment(
        flow_id="coding_return_path",
        thread_id=thread_id,
        spec_json={
            "source_thread_id": thread_id,
            "source_message_id": source_message_id,
            "user_id": user_id,
            "project_id": project_id,
        },
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
) -> CodingExecutionTask:
    return CodingExecutionTask.from_dict(
        {
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
    )


def _install_fake_adapter(monkeypatch, result: Any) -> list[SimpleNamespace]:
    calls: list[SimpleNamespace] = []

    class _FakeAdapter:
        def execute(self, request: Any) -> Any:
            calls.append(request)
            return result

    monkeypatch.setattr(
        coding_worker, "ADAPTERS", {"pi_codex_runner": _FakeAdapter()}
    )
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
            "visibility_scope": "terminal"
            if event_type in {"task.completed", "task.failed"}
            else "progress",
            "terminal_visibility": event_type in {
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


def _fetch_run_state(store: AgentStore, run_id: str) -> dict[str, Any] | None:
    return store.get_run(run_id)


def _fetch_coding_result_artifacts(store: AgentStore, run_id: str) -> list[dict[str, Any]]:
    return store.list_artifacts(run_id=run_id, artifact_type="coding_result")


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
            artifacts=(
                {
                    "path": "guardian/workers/coding_worker.py",
                    "commit_hash": "abc123def",
                    "validation_results": {"pytest": "passed"},
                },
            ),
            errors=(),
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
    assert message.extra_meta["run_id"] == run_id
    assert message.extra_meta["coding_task_id"] == task.coding_task_id
    assert message.extra_meta["source_thread_id"] == seeded["thread_id"]
    assert message.extra_meta["source_message_id"] == seeded["source_message_id"]
    assert message.extra_meta["user_id"] == seeded["user_id"]
    assert message.extra_meta["project_id"] == seeded["project_id"]
    assert message.extra_meta["commit_hash"] == "abc123def"
    assert "abc123def" in message.content
    assert '"pytest": "passed"' in message.content
    run_state = _fetch_run_state(store, run_id)
    assert run_state is not None
    assert run_state["status"] == "succeeded"
    artifacts = _fetch_coding_result_artifacts(store, run_id)
    assert len(artifacts) == 1
    assert artifacts[0]["content_json"]["delivery_ok"] is True
    assert artifacts[0]["content_json"]["commit_hash"] == "abc123def"


def test_duplicate_finalization_does_not_duplicate_return_messages(
    db,
    monkeypatch,
) -> None:
    seeded = _seed_source_context(db, user_id="user-2", project_name="project-2")
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
    seeded = _seed_source_context(db, user_id="user-4", project_name="project-4")
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
    assert artifacts[0]["content_json"]["delivery_reason"] == "delivery_database_unavailable"
