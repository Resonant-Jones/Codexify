from __future__ import annotations

import subprocess
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy import JSON, Integer, create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.agents.commit_gate import CommitGateResult
from guardian.agents.store import AgentStore
from guardian.agents.worktree_lease_store import (
    WorktreeLeaseStore,
    WorktreeLeaseStoreError,
)
from guardian.agents.worktree_leases import WorktreeLeaseContract
from guardian.db.models import (
    AgentDeployment,
    AgentRun,
    AgentRunArtifact,
    Base,
    Campaign,
    CampaignExecutionAttempt,
    CampaignGoal,
    ChatMessage,
    ChatThread,
    CodingWorkOrder,
    CodingWorktreeLease,
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
                CampaignGoal.__table__,
                Campaign.__table__,
                CodingWorkOrder.__table__,
                CampaignExecutionAttempt.__table__,
                CodingWorktreeLease.__table__,
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


def _seed_campaign_entities(
    db: _TestDB,
    *,
    goal_id: str,
    campaign_id: str,
    work_order_id: str,
) -> None:
    now = datetime.now(UTC)
    with db.get_session() as session:
        session.add(
            CampaignGoal(
                goal_id=goal_id,
                title="Goal",
                summary="Goal summary",
                status="active",
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            Campaign(
                campaign_id=campaign_id,
                goal_id=goal_id,
                title="Campaign",
                summary="Campaign summary",
                status="active",
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            CodingWorkOrder(
                work_order_id=work_order_id,
                campaign_id=campaign_id,
                title="Work order",
                objective="Objective",
                status="ready",
                priority=1,
                dependency_ids=[],
                file_scope=[],
                max_validation_attempts=1,
                require_worktree_lease=False,
                commit_after_validation=False,
                require_human_review_before_merge=True,
                extra_meta={},
                created_at=now,
                updated_at=now,
            )
        )
        session.commit()


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
    extra_spec: dict[str, Any] | None = None,
) -> tuple[str, str]:
    spec_json = {
        "source_thread_id": thread_id,
        "source_message_id": source_message_id,
        "user_id": user_id,
        "project_id": project_id,
    }
    if isinstance(extra_spec, dict):
        spec_json.update(extra_spec)
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
    campaign_id: str | None = None,
    work_order_id: str | None = None,
    cwd: str | None = "/workspace/repo",
    validation_command: str | None = None,
    max_validation_attempts: int | None = None,
    permission_policy: dict[str, Any] | None = None,
    worktree_lease_id: str | None = None,
    require_worktree_lease: bool | None = None,
    commit_after_validation: bool | None = None,
    commit_message: str | None = None,
    require_human_review_before_merge: bool | None = None,
) -> CodingExecutionTask:
    payload: dict[str, Any] = {
        "task_id": f"task-{coding_task_id}",
        "run_id": run_id,
        "deployment_id": deployment_id,
        "instructions": "Patch the seam and keep the return path intact.",
        "timeout_seconds": 60,
        "coding_task_id": coding_task_id,
        "attempt_id": attempt_id,
        "thread_id": thread_id,
        "source_message_id": source_message_id,
    }
    if campaign_id is not None:
        payload["campaign_id"] = campaign_id
    if work_order_id is not None:
        payload["work_order_id"] = work_order_id
    if cwd is not None:
        payload["cwd"] = cwd
    if validation_command is not None:
        payload["validation_command"] = validation_command
    if max_validation_attempts is not None:
        payload["max_validation_attempts"] = max_validation_attempts
    if permission_policy is not None:
        payload["permission_policy"] = permission_policy
    if worktree_lease_id is not None:
        payload["worktree_lease_id"] = worktree_lease_id
    if require_worktree_lease is not None:
        payload["require_worktree_lease"] = require_worktree_lease
    if commit_after_validation is not None:
        payload["commit_after_validation"] = commit_after_validation
    if commit_message is not None:
        payload["commit_message"] = commit_message
    if require_human_review_before_merge is not None:
        payload[
            "require_human_review_before_merge"
        ] = require_human_review_before_merge
    return CodingExecutionTask.from_dict(payload)


def _create_active_worktree_lease(
    db: _TestDB,
    *,
    lease_id: str,
    work_order_id: str,
    run_id: str,
    worker_id: str,
    branch_name: str,
    worktree_path: str,
) -> WorktreeLeaseContract:
    created_at = datetime(2026, 5, 10, 12, 0, tzinfo=UTC)
    lease = WorktreeLeaseContract(
        lease_id=lease_id,
        work_order_id=work_order_id,
        run_id=run_id,
        worker_id=worker_id,
        base_ref="origin/main",
        branch_name=branch_name,
        worktree_path=worktree_path,
        status="active",
        created_at=created_at,
        expires_at=created_at + timedelta(hours=1),
        preserve_on_failure=False,
        cleanup_policy="cleanup_on_merge",
        last_heartbeat_at=created_at + timedelta(minutes=1),
    )
    store = WorktreeLeaseStore(db=db)
    return store.create_lease(lease)


def _insert_invalid_worktree_lease_row(
    db: _TestDB,
    *,
    lease_id: str,
    work_order_id: str,
    run_id: str,
    worker_id: str,
    branch_name: str,
    worktree_path: str,
) -> None:
    created_at = datetime(2026, 5, 10, 12, 0, tzinfo=UTC)
    with db.get_session() as session:
        session.add(
            CodingWorktreeLease(
                lease_id=lease_id,
                work_order_id=work_order_id,
                run_id=run_id,
                worker_id=worker_id,
                base_ref="origin/main",
                branch_name=branch_name,
                worktree_path=worktree_path,
                status="active",
                created_at=created_at,
                expires_at=created_at - timedelta(minutes=5),
                preserve_on_failure=False,
                cleanup_policy="cleanup_on_merge",
                last_heartbeat_at=created_at + timedelta(minutes=1),
                extra_meta={},
            )
        )
        session.commit()


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
    assert task.max_validation_attempts == 1
    assert task.worktree_lease_id is None
    assert task.require_worktree_lease is False
    assert task.commit_after_validation is False
    assert task.commit_message is None
    assert task.require_human_review_before_merge is True


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


def _install_fake_commit_gate(
    monkeypatch,
    *,
    result: CommitGateResult | None = None,
    side_effect: BaseException | None = None,
) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    def _fake_commit_after_green(
        worktree_path: str,
        commit_message: str,
        branch_name: str | None = None,
    ) -> CommitGateResult:
        calls.append(
            {
                "worktree_path": worktree_path,
                "commit_message": commit_message,
                "branch_name": branch_name,
            }
        )
        if side_effect is not None:
            raise side_effect
        return result or CommitGateResult(
            attempted=True,
            committed=True,
            commit_hash="abc123def456",
            status="committed",
            reason_code="GIT_COMMIT_CREATED",
            message="commit created",
            files_changed=["README.md"],
            worktree_path=worktree_path,
            branch_name=branch_name,
        )

    monkeypatch.setattr(
        coding_worker, "commit_after_green", _fake_commit_after_green
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


def _fetch_campaign_attempts(
    db: _TestDB, campaign_id: str
) -> list[CampaignExecutionAttempt]:
    with db.get_session() as session:
        return (
            session.query(CampaignExecutionAttempt)
            .filter_by(campaign_id=campaign_id)
            .order_by(CampaignExecutionAttempt.created_at.asc())
            .all()
        )


def _fetch_work_order(
    db: _TestDB, work_order_id: str
) -> CodingWorkOrder | None:
    with db.get_session() as session:
        return (
            session.query(CodingWorkOrder)
            .filter_by(work_order_id=work_order_id)
            .first()
        )


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


def test_worker_records_campaign_attempt_ledger_and_work_order_markers(
    db,
    monkeypatch,
) -> None:
    seeded = _seed_source_context(db, user_id="campaign-ledger-user")
    _seed_campaign_entities(
        db,
        goal_id="goal-ledger-1",
        campaign_id="campaign-ledger-1",
        work_order_id="wo-ledger-1",
    )
    store = _make_store(db)
    deployment_id, run_id = _seed_execution_run(
        store,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        user_id=seeded["user_id"],
        project_id=seeded["project_id"],
        adapter_kind="codex",
        extra_spec={
            "campaign_id": "campaign-ledger-1",
            "work_order_id": "wo-ledger-1",
        },
    )
    worker = coding_worker.CodingWorker(agent_store=store)
    _capture_task_events(monkeypatch)
    _install_fake_adapter(
        monkeypatch,
        SimpleNamespace(
            status="ok",
            summary="Campaign attempt succeeded.",
            artifacts=({"commit_hash": "abc123def456"},),
            errors=(),
        ),
        adapter_kind="codex",
    )
    _install_fake_validation_runner(monkeypatch)

    task = _build_task(
        run_id=run_id,
        deployment_id=deployment_id,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        coding_task_id="coding-task-campaign-ledger",
        campaign_id="campaign-ledger-1",
        work_order_id="wo-ledger-1",
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

    attempts = _fetch_campaign_attempts(db, "campaign-ledger-1")
    assert len(attempts) == 1
    attempt = attempts[0]
    assert attempt.work_order_id == "wo-ledger-1"
    assert attempt.run_id == run_id
    assert attempt.attempt_id == task.attempt_id
    assert attempt.status == "succeeded"
    assert attempt.commit_hash == "abc123def456"
    assert attempt.delivery_ok is True
    assert attempt.delivered_message_id is not None
    assert attempt.validation_summary.get("final_validation_status") == "passed"

    work_order = _fetch_work_order(db, "wo-ledger-1")
    assert work_order is not None
    assert work_order.latest_run_id == run_id
    assert work_order.latest_receipt_id is not None


def test_lease_bound_execution_uses_leased_worktree_and_metadata(
    db,
    monkeypatch,
    tmp_path,
) -> None:
    seeded = _seed_source_context(db, user_id="lease-bound-user")
    store = _make_store(db)
    deployment_id, run_id = _seed_execution_run(
        store,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        user_id=seeded["user_id"],
        project_id=seeded["project_id"],
        adapter_kind="codex",
    )
    lease_path = tmp_path / "lease-worktree"
    lease_path.mkdir(parents=True, exist_ok=True)
    lease = _create_active_worktree_lease(
        db,
        lease_id="lease-bound-1",
        work_order_id="wo-lease-bound-1",
        run_id=run_id,
        worker_id="coding-worker",
        branch_name="codex/lease-bound-1",
        worktree_path=str(lease_path),
    )
    worker = coding_worker.CodingWorker(agent_store=store)
    published = _capture_task_events(monkeypatch)
    adapter_calls = _install_fake_adapter(
        monkeypatch,
        SimpleNamespace(
            status="ok",
            summary="Lease-bound adapter completed.",
            artifacts=(),
            errors=(),
        ),
        adapter_kind="codex",
    )
    validation_calls = _install_fake_validation_runner(monkeypatch)
    heartbeat_calls: list[str] = []
    original_heartbeat = coding_worker.WorktreeLeaseStore.heartbeat

    def _spy_heartbeat(
        self, lease_id: str, at: datetime | None = None
    ) -> WorktreeLeaseContract:
        heartbeat_calls.append(lease_id)
        return original_heartbeat(self, lease_id, at=at)

    monkeypatch.setattr(
        coding_worker.WorktreeLeaseStore, "heartbeat", _spy_heartbeat
    )
    task = _build_task(
        run_id=run_id,
        deployment_id=deployment_id,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        coding_task_id="coding-task-lease-bound",
        cwd="/tmp/ignored-cwd",
        validation_command="pytest -q",
        worktree_lease_id=lease.lease_id,
        require_worktree_lease=True,
        permission_policy={
            "allow_shell": True,
            "allow_network": False,
            "allow_write": True,
            "allowed_paths": [str(lease_path)],
            "max_runtime_seconds": 60,
        },
    )

    worker._process_task(task)

    assert len(adapter_calls) == 1
    assert adapter_calls[0].cwd == str(lease_path)
    assert len(validation_calls) == 1
    assert validation_calls[0]["cwd"] == str(lease_path)
    assert len(heartbeat_calls) >= 4
    terminal_payload = published[-1][2]
    assert published[-1][1] == "task.completed"
    assert terminal_payload["worktree_lease_id"] == lease.lease_id
    assert terminal_payload["branch_name"] == lease.branch_name
    assert terminal_payload["worktree_path"] == str(lease_path)
    artifacts = _fetch_coding_result_artifacts(store, run_id)
    assert len(artifacts) == 1
    content = artifacts[0]["content_json"]
    assert content["worktree_lease_id"] == lease.lease_id
    assert content["branch_name"] == lease.branch_name
    assert content["worktree_path"] == str(lease_path)
    assert content["lease_required"] is True


def test_missing_required_lease_fails_before_adapter_execution(
    db,
    monkeypatch,
) -> None:
    seeded = _seed_source_context(db, user_id="lease-required-user")
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
    adapter_calls = _install_fake_adapter(
        monkeypatch,
        SimpleNamespace(status="ok", summary="should not run"),
        adapter_kind="codex",
    )
    validation_calls = _install_fake_validation_runner(monkeypatch)
    task = _build_task(
        run_id=run_id,
        deployment_id=deployment_id,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        coding_task_id="coding-task-missing-required-lease",
        require_worktree_lease=True,
        validation_command="pytest -q",
        permission_policy={"allow_shell": True},
    )

    worker._process_task(task)

    assert adapter_calls == []
    assert validation_calls == []
    assert [event for _, event, _ in published] == ["task.failed"]
    assert published[-1][2]["error_code"] == "WORKTREE_LEASE_REQUIRED"
    artifacts = _fetch_coding_result_artifacts(store, run_id)
    assert len(artifacts) == 1


def test_unknown_lease_fails_before_adapter_execution(
    db,
    monkeypatch,
) -> None:
    seeded = _seed_source_context(db, user_id="lease-unknown-user")
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
    adapter_calls = _install_fake_adapter(
        monkeypatch,
        SimpleNamespace(status="ok", summary="should not run"),
        adapter_kind="codex",
    )
    task = _build_task(
        run_id=run_id,
        deployment_id=deployment_id,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        coding_task_id="coding-task-unknown-lease",
        worktree_lease_id="lease-does-not-exist",
        require_worktree_lease=False,
        validation_command="pytest -q",
        permission_policy={"allow_shell": True},
    )

    worker._process_task(task)

    assert adapter_calls == []
    assert [event for _, event, _ in published] == ["task.failed"]
    assert published[-1][2]["error_code"] == "WORKTREE_LEASE_NOT_FOUND"
    assert published[-1][2]["worktree_lease_id"] == "lease-does-not-exist"


def test_inactive_lease_fails_before_adapter_execution(
    db,
    monkeypatch,
    tmp_path,
) -> None:
    seeded = _seed_source_context(db, user_id="lease-inactive-user")
    store = _make_store(db)
    deployment_id, run_id = _seed_execution_run(
        store,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        user_id=seeded["user_id"],
        project_id=seeded["project_id"],
        adapter_kind="codex",
    )
    lease_path = tmp_path / "inactive-lease"
    lease_path.mkdir(parents=True, exist_ok=True)
    released_lease = WorktreeLeaseContract(
        lease_id="lease-inactive-1",
        work_order_id="wo-inactive-1",
        run_id=run_id,
        worker_id="coding-worker",
        base_ref="origin/main",
        branch_name="codex/inactive-1",
        worktree_path=str(lease_path),
        status="released",
        created_at=datetime(2026, 5, 10, 12, 0, tzinfo=UTC),
        expires_at=datetime(2026, 5, 10, 13, 0, tzinfo=UTC),
        preserve_on_failure=False,
        cleanup_policy="cleanup_on_merge",
        last_heartbeat_at=datetime(2026, 5, 10, 12, 5, tzinfo=UTC),
    )
    WorktreeLeaseStore(db=db).create_lease(released_lease)
    worker = coding_worker.CodingWorker(agent_store=store)
    published = _capture_task_events(monkeypatch)
    adapter_calls = _install_fake_adapter(
        monkeypatch,
        SimpleNamespace(status="ok", summary="should not run"),
        adapter_kind="codex",
    )
    task = _build_task(
        run_id=run_id,
        deployment_id=deployment_id,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        coding_task_id="coding-task-inactive-lease",
        worktree_lease_id="lease-inactive-1",
        require_worktree_lease=True,
    )

    worker._process_task(task)

    assert adapter_calls == []
    assert [event for _, event, _ in published] == ["task.failed"]
    assert published[-1][2]["error_code"] == "WORKTREE_LEASE_NOT_ACTIVE"


def test_invalid_lease_contract_fails_before_adapter_execution(
    db,
    monkeypatch,
    tmp_path,
) -> None:
    seeded = _seed_source_context(db, user_id="lease-invalid-user")
    store = _make_store(db)
    deployment_id, run_id = _seed_execution_run(
        store,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        user_id=seeded["user_id"],
        project_id=seeded["project_id"],
        adapter_kind="codex",
    )
    lease_path = tmp_path / "invalid-lease"
    lease_path.mkdir(parents=True, exist_ok=True)
    _insert_invalid_worktree_lease_row(
        db,
        lease_id="lease-invalid-1",
        work_order_id="wo-invalid-1",
        run_id=run_id,
        worker_id="coding-worker",
        branch_name="codex/invalid-1",
        worktree_path=str(lease_path),
    )
    worker = coding_worker.CodingWorker(agent_store=store)
    published = _capture_task_events(monkeypatch)
    adapter_calls = _install_fake_adapter(
        monkeypatch,
        SimpleNamespace(status="ok", summary="should not run"),
        adapter_kind="codex",
    )
    task = _build_task(
        run_id=run_id,
        deployment_id=deployment_id,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        coding_task_id="coding-task-invalid-lease",
        worktree_lease_id="lease-invalid-1",
        require_worktree_lease=True,
    )

    worker._process_task(task)

    assert adapter_calls == []
    assert [event for _, event, _ in published] == ["task.failed"]
    assert published[-1][2]["error_code"] == "WORKTREE_LEASE_INVALID"


def test_missing_lease_path_fails_before_adapter_execution(
    db,
    monkeypatch,
    tmp_path,
) -> None:
    seeded = _seed_source_context(db, user_id="lease-missing-path-user")
    store = _make_store(db)
    deployment_id, run_id = _seed_execution_run(
        store,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        user_id=seeded["user_id"],
        project_id=seeded["project_id"],
        adapter_kind="codex",
    )
    missing_path = tmp_path / "missing-lease-path"
    _create_active_worktree_lease(
        db,
        lease_id="lease-missing-path-1",
        work_order_id="wo-missing-path-1",
        run_id=run_id,
        worker_id="coding-worker",
        branch_name="codex/missing-path-1",
        worktree_path=str(missing_path),
    )
    worker = coding_worker.CodingWorker(agent_store=store)
    published = _capture_task_events(monkeypatch)
    adapter_calls = _install_fake_adapter(
        monkeypatch,
        SimpleNamespace(status="ok", summary="should not run"),
        adapter_kind="codex",
    )
    task = _build_task(
        run_id=run_id,
        deployment_id=deployment_id,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        coding_task_id="coding-task-missing-lease-path",
        worktree_lease_id="lease-missing-path-1",
        require_worktree_lease=True,
    )

    worker._process_task(task)

    assert adapter_calls == []
    assert [event for _, event, _ in published] == ["task.failed"]
    assert published[-1][2]["error_code"] == "WORKTREE_LEASE_PATH_UNAVAILABLE"


def test_lease_path_file_fails_before_adapter_execution(
    db,
    monkeypatch,
    tmp_path,
) -> None:
    seeded = _seed_source_context(db, user_id="lease-file-path-user")
    store = _make_store(db)
    deployment_id, run_id = _seed_execution_run(
        store,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        user_id=seeded["user_id"],
        project_id=seeded["project_id"],
        adapter_kind="codex",
    )
    file_path = tmp_path / "not-a-dir.txt"
    file_path.write_text("lease path file", encoding="utf-8")
    _create_active_worktree_lease(
        db,
        lease_id="lease-file-path-1",
        work_order_id="wo-file-path-1",
        run_id=run_id,
        worker_id="coding-worker",
        branch_name="codex/file-path-1",
        worktree_path=str(file_path),
    )
    worker = coding_worker.CodingWorker(agent_store=store)
    published = _capture_task_events(monkeypatch)
    adapter_calls = _install_fake_adapter(
        monkeypatch,
        SimpleNamespace(status="ok", summary="should not run"),
        adapter_kind="codex",
    )
    task = _build_task(
        run_id=run_id,
        deployment_id=deployment_id,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        coding_task_id="coding-task-file-lease-path",
        worktree_lease_id="lease-file-path-1",
        require_worktree_lease=True,
    )

    worker._process_task(task)

    assert adapter_calls == []
    assert [event for _, event, _ in published] == ["task.failed"]
    assert published[-1][2]["error_code"] == "WORKTREE_LEASE_PATH_UNAVAILABLE"


def test_lease_heartbeat_failure_fails_before_adapter_execution(
    db,
    monkeypatch,
    tmp_path,
) -> None:
    seeded = _seed_source_context(db, user_id="lease-heartbeat-fail-user")
    store = _make_store(db)
    deployment_id, run_id = _seed_execution_run(
        store,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        user_id=seeded["user_id"],
        project_id=seeded["project_id"],
        adapter_kind="codex",
    )
    lease_path = tmp_path / "lease-heartbeat-fail"
    lease_path.mkdir(parents=True, exist_ok=True)
    _create_active_worktree_lease(
        db,
        lease_id="lease-heartbeat-fail-1",
        work_order_id="wo-heartbeat-fail-1",
        run_id=run_id,
        worker_id="coding-worker",
        branch_name="codex/heartbeat-fail-1",
        worktree_path=str(lease_path),
    )
    worker = coding_worker.CodingWorker(agent_store=store)
    published = _capture_task_events(monkeypatch)
    adapter_calls = _install_fake_adapter(
        monkeypatch,
        SimpleNamespace(status="ok", summary="should not run"),
        adapter_kind="codex",
    )

    def _boom_heartbeat(
        _self, _lease_id: str, at: datetime | None = None
    ) -> WorktreeLeaseContract:
        _ = at
        raise WorktreeLeaseStoreError("heartbeat unavailable")

    monkeypatch.setattr(
        coding_worker.WorktreeLeaseStore, "heartbeat", _boom_heartbeat
    )
    task = _build_task(
        run_id=run_id,
        deployment_id=deployment_id,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        coding_task_id="coding-task-lease-heartbeat-fail",
        worktree_lease_id="lease-heartbeat-fail-1",
        require_worktree_lease=True,
    )

    worker._process_task(task)

    assert adapter_calls == []
    assert [event for _, event, _ in published] == ["task.failed"]
    assert published[-1][2]["error_code"] == "WORKTREE_LEASE_HEARTBEAT_FAILED"


def test_commit_after_validation_omitted_preserves_existing_behavior(
    db,
    monkeypatch,
) -> None:
    seeded = _seed_source_context(
        db, user_id="commit-omitted-user", project_name="commit-omitted"
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
        SimpleNamespace(status="ok", summary="Adapter succeeded."),
        adapter_kind="codex",
    )
    _install_fake_validation_runner(monkeypatch)
    commit_calls = _install_fake_commit_gate(monkeypatch)
    task = _build_task(
        run_id=run_id,
        deployment_id=deployment_id,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        coding_task_id="coding-task-commit-omitted",
        validation_command="pytest -q",
        permission_policy={"allow_shell": True},
    )

    worker._process_task(task)

    assert commit_calls == []
    assert published[-1][1] == "task.completed"
    assert published[-1][2]["commit_after_validation"] is False


def test_commit_after_validation_without_lease_fails_closed(
    db,
    monkeypatch,
) -> None:
    seeded = _seed_source_context(
        db, user_id="commit-missing-lease-user", project_name="commit-missing"
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
    adapter_calls = _install_fake_adapter(
        monkeypatch,
        SimpleNamespace(status="ok", summary="should not run"),
        adapter_kind="codex",
    )
    validation_calls = _install_fake_validation_runner(monkeypatch)
    commit_calls = _install_fake_commit_gate(monkeypatch)
    task = _build_task(
        run_id=run_id,
        deployment_id=deployment_id,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        coding_task_id="coding-task-commit-missing-lease",
        validation_command="pytest -q",
        permission_policy={"allow_shell": True},
        commit_after_validation=True,
    )

    worker._process_task(task)

    assert adapter_calls == []
    assert validation_calls == []
    assert commit_calls == []
    assert published[-1][1] == "task.failed"
    assert published[-1][2]["error_code"] == "GIT_WORKTREE_REQUIRED"


def test_validation_failure_does_not_run_commit_gate(
    db,
    monkeypatch,
    tmp_path,
) -> None:
    seeded = _seed_source_context(
        db, user_id="commit-validation-fail-user", project_name="commit-fail"
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
    lease_path = tmp_path / "commit-validation-fail"
    lease_path.mkdir(parents=True, exist_ok=True)
    lease = _create_active_worktree_lease(
        db,
        lease_id="lease-commit-validation-fail",
        work_order_id="wo-commit-validation-fail",
        run_id=run_id,
        worker_id="coding-worker",
        branch_name="codex/commit-validation-fail",
        worktree_path=str(lease_path),
    )
    worker = coding_worker.CodingWorker(agent_store=store)
    published = _capture_task_events(monkeypatch)
    _install_fake_adapter(
        monkeypatch,
        SimpleNamespace(status="ok", summary="Adapter succeeded."),
        adapter_kind="codex",
    )
    _install_fake_validation_runner(
        monkeypatch,
        result=subprocess.CompletedProcess(
            args=["pytest", "-q"],
            returncode=1,
            stdout="1 failed\n",
            stderr="failure\n",
        ),
    )
    commit_calls = _install_fake_commit_gate(monkeypatch)
    task = _build_task(
        run_id=run_id,
        deployment_id=deployment_id,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        coding_task_id="coding-task-validation-fail-no-commit",
        validation_command="pytest -q",
        worktree_lease_id=lease.lease_id,
        require_worktree_lease=True,
        permission_policy={"allow_shell": True},
        commit_after_validation=True,
    )

    worker._process_task(task)

    assert commit_calls == []
    assert published[-1][1] == "task.failed"
    assert published[-1][2]["commit_after_validation"] is True
    assert published[-1][2]["commit_status"] == "skipped"
    assert published[-1][2]["merge_ready"] is False


def test_validation_error_does_not_run_commit_gate(
    db,
    monkeypatch,
    tmp_path,
) -> None:
    seeded = _seed_source_context(
        db, user_id="commit-validation-error-user", project_name="commit-error"
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
    lease_path = tmp_path / "commit-validation-error"
    lease_path.mkdir(parents=True, exist_ok=True)
    lease = _create_active_worktree_lease(
        db,
        lease_id="lease-commit-validation-error",
        work_order_id="wo-commit-validation-error",
        run_id=run_id,
        worker_id="coding-worker",
        branch_name="codex/commit-validation-error",
        worktree_path=str(lease_path),
    )
    worker = coding_worker.CodingWorker(agent_store=store)
    published = _capture_task_events(monkeypatch)
    _install_fake_adapter(
        monkeypatch,
        SimpleNamespace(status="ok", summary="Adapter succeeded."),
        adapter_kind="codex",
    )
    _install_fake_validation_runner(
        monkeypatch,
        side_effect=subprocess.TimeoutExpired(["pytest", "-q"], timeout=1),
    )
    commit_calls = _install_fake_commit_gate(monkeypatch)
    task = _build_task(
        run_id=run_id,
        deployment_id=deployment_id,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        coding_task_id="coding-task-validation-error-no-commit",
        validation_command="pytest -q",
        worktree_lease_id=lease.lease_id,
        require_worktree_lease=True,
        permission_policy={"allow_shell": True},
        commit_after_validation=True,
    )

    worker._process_task(task)

    assert commit_calls == []
    assert published[-1][1] == "task.failed"
    assert published[-1][2]["commit_after_validation"] is True
    assert published[-1][2]["commit_status"] == "skipped"
    assert published[-1][2]["merge_ready"] is False


def test_validation_not_run_does_not_run_commit_gate(
    db,
    monkeypatch,
    tmp_path,
) -> None:
    seeded = _seed_source_context(
        db,
        user_id="commit-validation-not-run-user",
        project_name="commit-not-run",
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
    lease_path = tmp_path / "commit-validation-not-run"
    lease_path.mkdir(parents=True, exist_ok=True)
    lease = _create_active_worktree_lease(
        db,
        lease_id="lease-commit-validation-not-run",
        work_order_id="wo-commit-validation-not-run",
        run_id=run_id,
        worker_id="coding-worker",
        branch_name="codex/commit-validation-not-run",
        worktree_path=str(lease_path),
    )
    worker = coding_worker.CodingWorker(agent_store=store)
    published = _capture_task_events(monkeypatch)
    _install_fake_adapter(
        monkeypatch,
        SimpleNamespace(status="ok", summary="Adapter succeeded."),
        adapter_kind="codex",
    )
    commit_calls = _install_fake_commit_gate(monkeypatch)
    task = _build_task(
        run_id=run_id,
        deployment_id=deployment_id,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        coding_task_id="coding-task-validation-not-run-no-commit",
        validation_command="pytest -q",
        worktree_lease_id=lease.lease_id,
        require_worktree_lease=True,
        permission_policy={"allow_shell": False},
        commit_after_validation=True,
    )

    worker._process_task(task)

    assert commit_calls == []
    assert published[-1][1] == "task.completed"
    assert published[-1][2]["commit_after_validation"] is True
    assert published[-1][2]["commit_status"] == "skipped"
    assert published[-1][2]["commit_reason_code"] == "VALIDATION_NOT_RUN"
    assert published[-1][2]["merge_ready"] is False


def test_validation_pass_with_lease_runs_commit_gate_and_emits_metadata(
    db,
    monkeypatch,
    tmp_path,
) -> None:
    seeded = _seed_source_context(
        db, user_id="commit-success-user", project_name="commit-success"
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
    lease_path = tmp_path / "commit-success-lease"
    lease_path.mkdir(parents=True, exist_ok=True)
    lease = _create_active_worktree_lease(
        db,
        lease_id="lease-commit-success",
        work_order_id="wo-commit-success",
        run_id=run_id,
        worker_id="coding-worker",
        branch_name="codex/commit-success",
        worktree_path=str(lease_path),
    )
    worker = coding_worker.CodingWorker(agent_store=store)
    published = _capture_task_events(monkeypatch)
    _install_fake_adapter(
        monkeypatch,
        SimpleNamespace(status="ok", summary="Adapter succeeded."),
        adapter_kind="codex",
    )
    _install_fake_validation_runner(monkeypatch)
    commit_calls = _install_fake_commit_gate(
        monkeypatch,
        result=CommitGateResult(
            attempted=True,
            committed=True,
            commit_hash="abc123def456",
            status="committed",
            reason_code="GIT_COMMIT_CREATED",
            message="commit created",
            files_changed=["README.md"],
            worktree_path=str(lease_path),
            branch_name=lease.branch_name,
        ),
    )
    task = _build_task(
        run_id=run_id,
        deployment_id=deployment_id,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        coding_task_id="coding-task-commit-success",
        validation_command="pytest -q",
        worktree_lease_id=lease.lease_id,
        require_worktree_lease=True,
        permission_policy={"allow_shell": True},
        commit_after_validation=True,
        commit_message="Commit after green from worker test",
        require_human_review_before_merge=False,
    )

    worker._process_task(task)

    assert len(commit_calls) == 1
    assert commit_calls[0]["worktree_path"] == str(lease_path)
    assert commit_calls[0]["branch_name"] == lease.branch_name
    assert (
        commit_calls[0]["commit_message"]
        == "Commit after green from worker test"
    )
    assert published[-1][1] == "task.completed"
    terminal_payload = published[-1][2]
    assert terminal_payload["commit_hash"] == "abc123def456"
    assert terminal_payload["commit_status"] == "committed"
    assert terminal_payload["merge_ready"] is True
    assert terminal_payload["worktree_lease_id"] == lease.lease_id
    artifacts = _fetch_coding_result_artifacts(store, run_id)
    assert artifacts[0]["content_json"]["commit_hash"] == "abc123def456"
    assert artifacts[0]["content_json"]["merge_ready"] is True


def test_commit_no_changes_records_non_merge_ready_completion(
    db,
    monkeypatch,
    tmp_path,
) -> None:
    seeded = _seed_source_context(
        db, user_id="commit-no-changes-user", project_name="commit-no-changes"
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
    lease_path = tmp_path / "commit-no-changes-lease"
    lease_path.mkdir(parents=True, exist_ok=True)
    lease = _create_active_worktree_lease(
        db,
        lease_id="lease-commit-no-changes",
        work_order_id="wo-commit-no-changes",
        run_id=run_id,
        worker_id="coding-worker",
        branch_name="codex/commit-no-changes",
        worktree_path=str(lease_path),
    )
    worker = coding_worker.CodingWorker(agent_store=store)
    published = _capture_task_events(monkeypatch)
    _install_fake_adapter(
        monkeypatch,
        SimpleNamespace(status="ok", summary="Adapter succeeded."),
        adapter_kind="codex",
    )
    _install_fake_validation_runner(monkeypatch)
    _install_fake_commit_gate(
        monkeypatch,
        result=CommitGateResult(
            attempted=True,
            committed=False,
            commit_hash=None,
            status="skipped",
            reason_code="GIT_NO_CHANGES_TO_COMMIT",
            message="no changes to commit",
            files_changed=[],
            worktree_path=str(lease_path),
            branch_name=lease.branch_name,
        ),
    )
    task = _build_task(
        run_id=run_id,
        deployment_id=deployment_id,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        coding_task_id="coding-task-commit-no-changes",
        validation_command="pytest -q",
        worktree_lease_id=lease.lease_id,
        require_worktree_lease=True,
        permission_policy={"allow_shell": True},
        commit_after_validation=True,
    )

    worker._process_task(task)

    assert published[-1][1] == "task.completed"
    terminal_payload = published[-1][2]
    assert terminal_payload["commit_status"] == "skipped"
    assert terminal_payload["commit_reason_code"] == "GIT_NO_CHANGES_TO_COMMIT"
    assert terminal_payload["merge_ready"] is False


def test_commit_failure_marks_terminal_failed_and_not_merge_ready(
    db,
    monkeypatch,
    tmp_path,
) -> None:
    seeded = _seed_source_context(
        db, user_id="commit-failure-user", project_name="commit-failure"
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
    lease_path = tmp_path / "commit-failure-lease"
    lease_path.mkdir(parents=True, exist_ok=True)
    lease = _create_active_worktree_lease(
        db,
        lease_id="lease-commit-failure",
        work_order_id="wo-commit-failure",
        run_id=run_id,
        worker_id="coding-worker",
        branch_name="codex/commit-failure",
        worktree_path=str(lease_path),
    )
    worker = coding_worker.CodingWorker(agent_store=store)
    published = _capture_task_events(monkeypatch)
    _install_fake_adapter(
        monkeypatch,
        SimpleNamespace(status="ok", summary="Adapter succeeded."),
        adapter_kind="codex",
    )
    _install_fake_validation_runner(monkeypatch)
    _install_fake_commit_gate(
        monkeypatch,
        result=CommitGateResult(
            attempted=True,
            committed=False,
            commit_hash=None,
            status="failed",
            reason_code="GIT_COMMIT_FAILED",
            message="commit failure",
            files_changed=["README.md"],
            worktree_path=str(lease_path),
            branch_name=lease.branch_name,
        ),
    )
    task = _build_task(
        run_id=run_id,
        deployment_id=deployment_id,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        coding_task_id="coding-task-commit-failure",
        validation_command="pytest -q",
        worktree_lease_id=lease.lease_id,
        require_worktree_lease=True,
        permission_policy={"allow_shell": True},
        commit_after_validation=True,
    )

    worker._process_task(task)

    assert published[-1][1] == "task.failed"
    terminal_payload = published[-1][2]
    assert terminal_payload["error_code"] == "GIT_COMMIT_FAILED"
    assert terminal_payload["commit_status"] == "failed"
    assert terminal_payload["merge_ready"] is False


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
        "task.validation_started",
        "task.validation_passed",
        "task.completed",
    ]
    terminal_payload = published[-1][2]
    assert terminal_payload["coding_result_status"] == "ok"
    assert terminal_payload["validation_results"]["status"] == "passed"
    assert terminal_payload["validation_results"]["tests_passed"] == 2
    assert terminal_payload["validation_attempt_count"] == 1
    assert terminal_payload["validation_stop_reason"] == "validation_passed"
    assert terminal_payload["final_validation_status"] == "passed"
    assert terminal_payload["final_fail_signature"] is None
    assert len(terminal_payload["validation_attempts"]) == 1
    assert terminal_payload["best_validation_result"]["status"] == "passed"
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
    assert artifacts[0]["content_json"]["validation_stop_reason"] == (
        "validation_passed"
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
        "task.attempt_started",
        "task.validation_started",
        "task.validation_failed",
        "task.failed",
    ]
    terminal_payload = published[-1][2]
    assert terminal_payload["coding_result_status"] == "failed"
    assert terminal_payload["validation_results"]["status"] == "failed"
    assert terminal_payload["errors"][-1] == "validation_failed"
    assert terminal_payload["validation_attempt_count"] == 1
    assert terminal_payload["validation_stop_reason"] == (
        "max_validation_attempts_reached"
    )
    assert terminal_payload["final_validation_status"] == "failed"
    assert terminal_payload["final_fail_signature"] is not None
    assert terminal_payload["best_validation_result"]["status"] == "failed"
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
    assert (
        content["validation_stop_reason"] == "max_validation_attempts_reached"
    )
    assert content["best_validation_result"]["status"] == "failed"
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
    assert terminal_payload["validation_results"]["status"] == "not_run"
    assert terminal_payload["validation_attempt_count"] == 1
    assert terminal_payload["validation_stop_reason"] == (
        "validation_shell_not_allowed"
    )
    assert terminal_payload["final_validation_status"] == "not_run"
    assert (
        terminal_payload["validation_results"]["error_message"]
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
    published = _capture_task_events(monkeypatch)
    adapter_calls = _install_fake_adapter(
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

    assert len(adapter_calls) == 1
    assert adapter_calls[0].cwd == "/workspace/repo"
    terminal_payload = published[-1][2]
    assert terminal_payload.get("worktree_lease_id") is None
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
        "task.validation_started",
        "task.validation_failed",
        "task.failed",
    ]
    terminal_payload = published[-1][2]
    assert terminal_payload["validation_results"]["status"] == "error"
    assert (
        terminal_payload["validation_results"]["error_message"]
        == "validation_command_timeout"
    )
    assert terminal_payload["validation_attempt_count"] == 1
    assert terminal_payload["validation_stop_reason"] == (
        "validation_command_timeout"
    )
    assert terminal_payload["final_validation_status"] == "error"
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
    assert artifacts[0]["content_json"]["validation_stop_reason"] == (
        "validation_command_timeout"
    )
    run_state = _fetch_run_state(store, run_id)
    assert run_state is not None
    assert run_state["status"] == "failed"


def test_validation_failure_retries_once_and_completes(
    db,
    monkeypatch,
) -> None:
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
    validation_calls = _install_fake_validation_runner(monkeypatch)

    def _sequenced_validation_run(
        argv: list[str],
        *,
        cwd: str | None = None,
        capture_output: bool | None = None,
        text: bool | None = None,
        check: bool | None = None,
        timeout: int | float | None = None,
    ) -> subprocess.CompletedProcess[str]:
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
        validation_command="pytest -q",
        max_validation_attempts=2,
        permission_policy={
            "allow_shell": True,
            "allow_network": False,
            "allow_write": True,
            "allowed_paths": ["/workspace/repo"],
            "max_runtime_seconds": 60,
        },
    )

    worker._process_task(task)

    assert len(calls) == 2
    assert len(validation_calls) == 2
    assert [event for _, event, _ in published] == [
        "task.running",
        "task.attempt_started",
        "task.validation_started",
        "task.validation_failed",
        "task.validation_retrying",
        "task.attempt_started",
        "task.validation_started",
        "task.validation_passed",
        "task.completed",
    ]
    second_prompt = calls[1].prompt
    assert "Validation feedback:" in second_prompt
    assert "pytest -q" in second_prompt
    assert "Fail signature:" in second_prompt
    assert "Repair the previous attempt" in second_prompt
    terminal_payload = published[-1][2]
    assert terminal_payload["coding_result_status"] == "ok"
    assert terminal_payload["validation_results"]["status"] == "passed"
    assert terminal_payload["validation_attempt_count"] == 2
    assert terminal_payload["validation_stop_reason"] == "validation_passed"
    assert terminal_payload["final_validation_status"] == "passed"
    assert terminal_payload["best_validation_result"]["status"] == "passed"
    assert len(terminal_payload["validation_attempts"]) == 2
    artifacts = _fetch_coding_result_artifacts(store, run_id)
    assert len(artifacts) == 1
    content = artifacts[0]["content_json"]
    assert content["validation_results"]["status"] == "passed"
    assert content["validation_attempt_count"] == 2
    assert content["validation_stop_reason"] == "validation_passed"
    assert len(content["validation_attempts"]) == 2
    messages = _fetch_thread_messages(db, seeded["thread_id"])
    assert len(messages) == 1
    assert messages[0].extra_meta["validation_results"]["status"] == "passed"
    run_state = _fetch_run_state(store, run_id)
    assert run_state is not None
    assert run_state["status"] == "succeeded"


def test_retry_prompt_uses_bounded_validation_feedback(
    db,
    monkeypatch,
) -> None:
    seeded = _seed_source_context(
        db, user_id="validation-bounded-user", project_name="validation-bounded"
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
    long_stdout = "A" * 6000
    long_stderr = "B" * 6000
    validation_results = iter(
        [
            subprocess.CompletedProcess(
                args=["pytest", "-q"],
                returncode=1,
                stdout=f"FAILED tests/unit/test_alpha.py::test_something - boom\n{long_stdout}\n",
                stderr=f"E AssertionError: boom\n{long_stderr}\n",
            ),
            subprocess.CompletedProcess(
                args=["pytest", "-q"],
                returncode=0,
                stdout="2 passed in 0.02s\n",
                stderr="",
            ),
        ]
    )
    validation_calls = _install_fake_validation_runner(monkeypatch)

    def _sequenced_validation_run(
        argv: list[str],
        *,
        cwd: str | None = None,
        capture_output: bool | None = None,
        text: bool | None = None,
        check: bool | None = None,
        timeout: int | float | None = None,
    ) -> subprocess.CompletedProcess[str]:
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
        coding_task_id="coding-task-validation-bounded",
        validation_command="pytest -q",
        max_validation_attempts=2,
        permission_policy={
            "allow_shell": True,
            "allow_network": False,
            "allow_write": True,
            "allowed_paths": ["/workspace/repo"],
            "max_runtime_seconds": 60,
        },
    )

    worker._process_task(task)

    assert len(calls) == 2
    assert len(validation_calls) == 2
    second_prompt = calls[1].prompt
    assert "Validation feedback:" in second_prompt
    assert "Fail signature:" in second_prompt
    assert "A" * 3000 not in second_prompt
    assert "B" * 3000 not in second_prompt


def test_validation_failure_across_all_attempts_emits_terminal_failure(
    db,
    monkeypatch,
) -> None:
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
    validation_calls = _install_fake_validation_runner(monkeypatch)

    def _sequenced_validation_run(
        argv: list[str],
        *,
        cwd: str | None = None,
        capture_output: bool | None = None,
        text: bool | None = None,
        check: bool | None = None,
        timeout: int | float | None = None,
    ) -> subprocess.CompletedProcess[str]:
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
        validation_command="pytest -q",
        max_validation_attempts=2,
        permission_policy={
            "allow_shell": True,
            "allow_network": False,
            "allow_write": True,
            "allowed_paths": ["/workspace/repo"],
            "max_runtime_seconds": 60,
        },
    )

    worker._process_task(task)

    assert len(validation_calls) == 2
    assert [event for _, event, _ in published] == [
        "task.running",
        "task.attempt_started",
        "task.validation_started",
        "task.validation_failed",
        "task.validation_retrying",
        "task.attempt_started",
        "task.validation_started",
        "task.validation_failed",
        "task.failed",
    ]
    terminal_payload = published[-1][2]
    assert terminal_payload["coding_result_status"] == "failed"
    assert terminal_payload["validation_results"]["status"] == "failed"
    assert terminal_payload["validation_attempt_count"] == 2
    assert terminal_payload["validation_stop_reason"] == (
        "max_validation_attempts_reached"
    )
    assert terminal_payload["final_validation_status"] == "failed"
    assert terminal_payload["error_code"] == "VALIDATION_FAILED"
    assert terminal_payload["best_validation_result"]["tests_failed"] == 1
    assert len(terminal_payload["validation_attempts"]) == 2
    artifacts = _fetch_coding_result_artifacts(store, run_id)
    assert len(artifacts) == 1
    content = artifacts[0]["content_json"]
    assert content["validation_results"]["status"] == "failed"
    assert content["validation_attempt_count"] == 2
    assert (
        content["validation_stop_reason"] == "max_validation_attempts_reached"
    )
    assert content["best_validation_result"]["tests_failed"] == 1
    messages = _fetch_thread_messages(db, seeded["thread_id"])
    assert messages == []
    run_state = _fetch_run_state(store, run_id)
    assert run_state is not None
    assert run_state["status"] == "failed"


def test_repeated_fail_signature_stops_before_budget_exhausted(
    db,
    monkeypatch,
) -> None:
    seeded = _seed_source_context(
        db,
        user_id="validation-repeat-user",
        project_name="validation-repeat",
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
                returncode=1,
                stdout="FAILED tests/unit/test_alpha.py::test_something - boom\n",
                stderr="E AssertionError: boom\n",
            ),
        ]
    )
    validation_calls = _install_fake_validation_runner(monkeypatch)

    def _sequenced_validation_run(
        argv: list[str],
        *,
        cwd: str | None = None,
        capture_output: bool | None = None,
        text: bool | None = None,
        check: bool | None = None,
        timeout: int | float | None = None,
    ) -> subprocess.CompletedProcess[str]:
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
        coding_task_id="coding-task-validation-repeat",
        validation_command="pytest -q",
        max_validation_attempts=3,
        permission_policy={
            "allow_shell": True,
            "allow_network": False,
            "allow_write": True,
            "allowed_paths": ["/workspace/repo"],
            "max_runtime_seconds": 60,
        },
    )

    worker._process_task(task)

    assert len(calls) == 2
    assert len(validation_calls) == 2
    assert [event for _, event, _ in published] == [
        "task.running",
        "task.attempt_started",
        "task.validation_started",
        "task.validation_failed",
        "task.validation_retrying",
        "task.attempt_started",
        "task.validation_started",
        "task.validation_failed",
        "task.failed",
    ]
    terminal_payload = published[-1][2]
    assert terminal_payload["coding_result_status"] == "failed"
    assert terminal_payload["validation_results"]["status"] == "failed"
    assert terminal_payload["validation_attempt_count"] == 2
    assert terminal_payload["validation_stop_reason"] == (
        "repeated_fail_signature"
    )
    assert terminal_payload["final_validation_status"] == "failed"
    assert terminal_payload["final_fail_signature"] is not None
    assert terminal_payload["error_code"] == "VALIDATION_FAILED"
    assert len(terminal_payload["validation_attempts"]) == 2
    artifacts = _fetch_coding_result_artifacts(store, run_id)
    assert len(artifacts) == 1
    content = artifacts[0]["content_json"]
    assert content["validation_stop_reason"] == "repeated_fail_signature"
    assert content["validation_attempt_count"] == 2
    run_state = _fetch_run_state(store, run_id)
    assert run_state is not None
    assert run_state["status"] == "failed"


def test_validation_command_with_missing_cwd_records_not_run(
    db,
    monkeypatch,
) -> None:
    seeded = _seed_source_context(
        db, user_id="missing-cwd-user", project_name="missing-cwd"
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
        cwd=None,
        coding_task_id="coding-task-missing-cwd",
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
        "task.completed",
    ]
    terminal_payload = published[-1][2]
    assert terminal_payload["validation_results"]["status"] == "not_run"
    assert (
        terminal_payload["validation_stop_reason"] == "validation_cwd_missing"
    )
    assert terminal_payload["final_validation_status"] == "not_run"
    assert terminal_payload["validation_attempt_count"] == 1
    messages = _fetch_thread_messages(db, seeded["thread_id"])
    assert len(messages) == 1
    assert messages[0].extra_meta["validation_results"]["status"] == "not_run"


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
