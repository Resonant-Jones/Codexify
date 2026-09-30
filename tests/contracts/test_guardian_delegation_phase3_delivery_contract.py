from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from guardian.agents.store import AgentStore
from guardian.core.guardian_delegation_service import (
    build_guardian_delegation_result_delivery_key,
)
from guardian.db.models import (
    AgentDeployment,
    AgentRun,
    AgentRunArtifact,
    AgentRunAttempt,
    AgentRunStep,
    Base,
    ChatMessage,
    ChatThread,
    GeneratedDocument,
    GuardianDelegationIntent,
    PersonalFact,
    Project,
    ProjectDocumentLink,
    User,
)
from guardian.routes import guardian_delegations
from tests.contracts.test_guardian_delegation_phase2a_contract import (
    _clear_disposable_tables,
    _disposable_postgres_engine,
)


class _TestDB:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine
        self._session_factory = sessionmaker(
            bind=self._engine,
            autoflush=False,
            autocommit=False,
            future=True,
        )

    def get_session(self):  # noqa: ANN201
        return self._session_factory()


@pytest.fixture(scope="module")
def _postgres_engine() -> Iterator[Engine]:
    with _disposable_postgres_engine() as engine:
        Base.metadata.create_all(bind=engine)
        yield engine


@pytest.fixture
def db(_postgres_engine: Engine) -> _TestDB:
    _clear_disposable_tables(_postgres_engine)
    return _TestDB(_postgres_engine)


@pytest.fixture
def delegation_client(db: _TestDB) -> TestClient:
    guardian_delegations.configure_db(db)
    app = FastAPI()
    app.include_router(guardian_delegations.router)
    return TestClient(app)


def _make_store(db: _TestDB) -> AgentStore:
    return AgentStore(db=db)


def _seed_source_context(
    db: _TestDB,
    *,
    user_id: str = "user-1",
    project_name: str = "project-1",
    thread_title: str = "Source thread",
    selected_content: str = "Please patch the return path.",
) -> dict[str, Any]:
    with db.get_session() as session:
        user = User(
            id=user_id,
            username=f"{user_id}-username",
            password_hash="hash",
        )
        session.add(user)
        project = Project(
            user_id=user_id,
            name=f"{project_name}-{user_id}",
            description=None,
            icon=None,
        )
        session.add(project)
        session.flush()
        thread = ChatThread(
            user_id=user_id,
            title=thread_title,
            summary="",
            project_id=project.id,
        )
        session.add(thread)
        session.flush()
        source_message = ChatMessage(
            thread_id=thread.id,
            user_id=user_id,
            role="user",
            content=selected_content,
            kind="chat",
            extra_meta={},
        )
        session.add(source_message)
        session.commit()
        return {
            "user_id": user_id,
            "project_id": project.id,
            "thread_id": thread.id,
            "source_message_id": source_message.id,
        }


def _fetch_intent(db: _TestDB, intent_id: str) -> GuardianDelegationIntent | None:
    with db.get_session() as session:
        return (
            session.query(GuardianDelegationIntent)
            .filter_by(intent_id=intent_id)
            .first()
        )


def _fetch_thread_messages(
    db: _TestDB,
    thread_id: int,
    *,
    kind: str | None = None,
) -> list[ChatMessage]:
    with db.get_session() as session:
        query = session.query(ChatMessage).filter_by(thread_id=thread_id)
        if kind is not None:
            query = query.filter_by(kind=kind)
        return list(query.order_by(ChatMessage.id.asc()).all())


def _create_guardian_intent(
    client: TestClient,
    auth_headers: dict[str, str],
    seeded: dict[str, Any],
) -> dict[str, Any]:
    response = client.post(
        "/api/guardian/delegations",
        headers=auth_headers,
        json={
            "thread_id": seeded["thread_id"],
            "source_message_id": seeded["source_message_id"],
            "project_id": seeded["project_id"],
        },
    )
    assert response.status_code == 201
    return response.json()


def _store_guardian_result(
    db: _TestDB,
    *,
    intent_payload: dict[str, Any],
    coding_task_id: str = "task-1",
    attempt_id: str = "attempt-1",
    result_status: str = "succeeded",
    result_summary: str = "Patched the Guardian delegation return path.",
    files_changed: list[str] | None = None,
    validation_results: Any | None = None,
    commit_hash: str | None = None,
) -> dict[str, Any]:
    return _make_store(db).store_coding_result(
        run_id=str(intent_payload["run_id"]),
        coding_task_id=coding_task_id,
        attempt_id=attempt_id,
        thread_id=int(intent_payload["thread_id"]),
        source_message_id=int(intent_payload["source_message_id"]),
        result_status=result_status,
        result_summary=result_summary,
        files_changed=files_changed or ["guardian/agents/store.py"],
        validation_results=validation_results,
        commit_hash=commit_hash,
    )


def _create_non_guardian_run(
    db: _TestDB,
    *,
    seeded: dict[str, Any],
    spec_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    store = _make_store(db)
    spec_json = {
        "source_thread_id": seeded["thread_id"],
        "source_message_id": seeded["source_message_id"],
        "thread_id": seeded["thread_id"],
        "user_id": seeded["user_id"],
        "project_id": seeded["project_id"],
        "adapter_kind": "pi_codex_runner",
    }
    spec_json.update(spec_overrides or {})
    deployment = store.create_deployment(
        flow_id="non_guardian_coding",
        thread_id=seeded["thread_id"],
        spec_json=spec_json,
        spec_hash="non-guardian-spec-hash",
        trust_state="supervised",
    )
    run = store.create_run(
        deployment_id=str(deployment["deployment_id"]),
        thread_id=seeded["thread_id"],
        runtime_target="container",
        rollback_mode="auto",
        status="queued",
    )
    return {
        "deployment_id": str(deployment["deployment_id"]),
        "run_id": str(run["run_id"]),
    }


def test_guardian_delegation_result_posts_once_to_source_thread(
    delegation_client: TestClient,
    db: _TestDB,
    auth_headers,
) -> None:
    seeded = _seed_source_context(db)
    created = _create_guardian_intent(delegation_client, auth_headers, seeded)

    delivery = _store_guardian_result(
        db,
        intent_payload=created,
        result_summary="Patched the delivery path and preserved idempotency.",
        files_changed=["guardian/agents/store.py", "guardian/db/models.py"],
        validation_results={"status": "passed", "command": "pytest -q"},
        commit_hash="abc123def456",
    )

    assert delivery["delivery_ok"] is True
    assert delivery["delivery_status"] == "delivered"
    assert delivery["visibility_status"] == "result_posted"

    messages = _fetch_thread_messages(
        db, created["thread_id"], kind="coding_result"
    )
    assert len(messages) == 1
    message = messages[0]
    delivery_key = build_guardian_delegation_result_delivery_key(
        intent_id=created["intent_id"],
        run_id=created["run_id"],
    )
    assert message.role == "assistant"
    assert message.extra_meta["guardian_delegation_intent_id"] == created["intent_id"]
    assert message.extra_meta["run_id"] == created["run_id"]
    assert message.extra_meta["thread_id"] == created["thread_id"]
    assert message.extra_meta["source_message_id"] == created["source_message_id"]
    assert message.extra_meta["delivery_key"] == delivery_key
    assert message.extra_meta["delivery_kind"] == "guardian_delegation_result"
    assert message.extra_meta["visibility_status"] == "result_posted"

    row = _fetch_intent(db, created["intent_id"])
    assert row is not None
    assert row.visibility_status == "result_posted"
    assert row.result_message_id == message.id
    assert row.result_delivery_key == delivery_key
    assert row.result_delivered_at is not None


def test_guardian_delegation_result_delivery_is_idempotent(
    delegation_client: TestClient,
    db: _TestDB,
    auth_headers,
) -> None:
    seeded = _seed_source_context(db)
    created = _create_guardian_intent(delegation_client, auth_headers, seeded)

    first = _store_guardian_result(db, intent_payload=created)
    second = _store_guardian_result(db, intent_payload=created)

    assert first["message_id"] is not None
    assert second["message_id"] == first["message_id"]
    assert second["delivery_ok"] is True
    assert second["delivery_status"] == "delivered"
    assert len(_fetch_thread_messages(db, created["thread_id"], kind="coding_result")) == 1


def test_guardian_delegation_result_delivery_survives_new_session(
    delegation_client: TestClient,
    db: _TestDB,
    auth_headers,
) -> None:
    seeded = _seed_source_context(db)
    created = _create_guardian_intent(delegation_client, auth_headers, seeded)

    first = _store_guardian_result(
        db,
        intent_payload=created,
        coding_task_id="task-1",
        attempt_id="attempt-1",
    )
    second = _make_store(db).store_coding_result(
        run_id=str(created["run_id"]),
        coding_task_id="task-1",
        attempt_id="attempt-1",
        thread_id=int(created["thread_id"]),
        source_message_id=int(created["source_message_id"]),
        result_status="succeeded",
        result_summary="Patched the Guardian delegation return path.",
        files_changed=["guardian/agents/store.py"],
    )

    assert first["message_id"] is not None
    assert second["message_id"] == first["message_id"]
    assert len(_fetch_thread_messages(db, created["thread_id"], kind="coding_result")) == 1


def test_stale_guardian_delegation_run_is_suppressed(
    delegation_client: TestClient,
    db: _TestDB,
    auth_headers,
) -> None:
    seeded = _seed_source_context(db)
    created = _create_guardian_intent(delegation_client, auth_headers, seeded)

    with db.get_session() as session:
        row = (
            session.query(GuardianDelegationIntent)
            .filter_by(intent_id=created["intent_id"])
            .first()
        )
        assert row is not None
        row.run_id = "run_superseding"
        session.commit()

    delivery = _store_guardian_result(db, intent_payload=created)

    assert delivery["delivery_ok"] is False
    assert delivery["delivery_status"] == "stale_suppressed"
    assert delivery["visibility_status"] == "stale_suppressed"
    assert delivery["source_thread_delivery_suppressed"] is True
    assert _fetch_thread_messages(db, created["thread_id"], kind="coding_result") == []

    row = _fetch_intent(db, created["intent_id"])
    assert row is not None
    assert row.visibility_status == "stale_suppressed"


def test_superseded_guardian_delegation_run_is_suppressed(
    delegation_client: TestClient,
    db: _TestDB,
    auth_headers,
) -> None:
    seeded = _seed_source_context(db)
    created = _create_guardian_intent(delegation_client, auth_headers, seeded)

    with db.get_session() as session:
        row = (
            session.query(GuardianDelegationIntent)
            .filter_by(intent_id=created["intent_id"])
            .first()
        )
        assert row is not None
        row.intent_status = "superseded"
        session.commit()

    delivery = _store_guardian_result(db, intent_payload=created)

    assert delivery["delivery_status"] == "stale_suppressed"
    assert delivery["visibility_status"] == "stale_suppressed"
    assert _fetch_thread_messages(db, created["thread_id"], kind="coding_result") == []


def test_cancelled_guardian_delegation_run_is_suppressed(
    delegation_client: TestClient,
    db: _TestDB,
    auth_headers,
) -> None:
    seeded = _seed_source_context(db)
    created = _create_guardian_intent(delegation_client, auth_headers, seeded)

    with db.get_session() as session:
        row = (
            session.query(GuardianDelegationIntent)
            .filter_by(intent_id=created["intent_id"])
            .first()
        )
        assert row is not None
        row.intent_status = "cancelled"
        session.commit()

    delivery = _store_guardian_result(db, intent_payload=created)

    assert delivery["delivery_status"] == "stale_suppressed"
    assert delivery["visibility_status"] == "stale_suppressed"
    assert _fetch_thread_messages(db, created["thread_id"], kind="coding_result") == []


def test_missing_lineage_does_not_post_result(db: _TestDB) -> None:
    seeded = _seed_source_context(db)
    non_intent_run = _create_non_guardian_run(
        db,
        seeded=seeded,
        spec_overrides={
            "guardian_delegation": {
                "ownership": "guardian_delegation_intent",
                "phase": "phase3",
                "suppress_source_thread_delivery": False,
            }
        },
    )

    delivery = _make_store(db).store_coding_result(
        run_id=non_intent_run["run_id"],
        coding_task_id="task-1",
        attempt_id="attempt-1",
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        result_status="succeeded",
        result_summary="Completed the patch.",
        files_changed=["guardian/agents/store.py"],
    )

    assert delivery["delivery_ok"] is False
    assert delivery["delivery_status"] == "degraded"
    assert delivery["delivery_reason_code"] == "guardian_delegation_intent_missing"
    assert _fetch_thread_messages(db, seeded["thread_id"], kind="coding_result") == []


def test_non_guardian_coding_result_delivery_unchanged(db: _TestDB) -> None:
    seeded = _seed_source_context(db)
    run = _create_non_guardian_run(db, seeded=seeded)

    delivery = _make_store(db).store_coding_result(
        run_id=run["run_id"],
        coding_task_id="task-1",
        attempt_id="attempt-1",
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        result_status="succeeded",
        result_summary="Updated the normal coding result path.",
        files_changed=["guardian/agents/store.py"],
    )

    assert delivery["delivery_ok"] is True
    assert delivery["delivery_status"] == "delivered"

    messages = _fetch_thread_messages(db, seeded["thread_id"], kind="coding_result")
    assert len(messages) == 1
    assert messages[0].extra_meta.get("guardian_delegation_intent_id") is None
    assert messages[0].extra_meta.get("delivery_kind") != "guardian_delegation_result"


def test_guardian_result_message_does_not_include_internal_context_or_personal_data(
    delegation_client: TestClient,
    db: _TestDB,
    auth_headers,
) -> None:
    selected_content = "Please patch guardian/agents/store.py."
    seeded = _seed_source_context(db, selected_content=selected_content)
    created = _create_guardian_intent(delegation_client, auth_headers, seeded)

    _store_guardian_result(
        db,
        intent_payload=created,
        result_summary=(
            "selected_turn_content_hash: abc123 context_basis "
            "project_kb_reference my boss is frustrating me"
        ),
        files_changed=["guardian/agents/store.py"],
    )

    messages = _fetch_thread_messages(
        db, created["thread_id"], kind="coding_result"
    )
    assert len(messages) == 1
    content = messages[0].content
    assert selected_content not in content
    assert "selected_turn_content_hash" not in content
    assert "context_basis" not in content
    assert "project_kb_reference" not in content
    assert "my boss is frustrating me" not in content
    assert "**Summary**" not in content


def test_get_guardian_delegation_includes_visibility_status(
    delegation_client: TestClient,
    db: _TestDB,
    auth_headers,
) -> None:
    seeded = _seed_source_context(db)
    created = _create_guardian_intent(delegation_client, auth_headers, seeded)

    delivery = _store_guardian_result(db, intent_payload=created)
    assert delivery["message_id"] is not None

    response = delegation_client.get(
        f"/api/guardian/delegations/{created['intent_id']}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["visibility_status"] == "result_posted"
    assert body["result_message_id"] == delivery["message_id"]
    assert body["result_delivered_at"] is not None


def test_duplicate_delivery_key_recovers_without_duplicate_message(
    delegation_client: TestClient,
    db: _TestDB,
    auth_headers,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seeded = _seed_source_context(db)
    created = _create_guardian_intent(delegation_client, auth_headers, seeded)
    store = _make_store(db)
    original_commit = store._commit_guardian_delegation_delivery
    collision_raised = {"value": False}

    def commit_with_duplicate_collision(session: Any) -> None:
        original_commit(session)
        if not collision_raised["value"]:
            collision_raised["value"] = True
            raise IntegrityError(
                "UPDATE guardian_delegation_intents",
                {},
                Exception(
                    "duplicate key value violates unique constraint "
                    "'ix_guardian_delegation_intents_result_delivery_key'"
                ),
            )

    monkeypatch.setattr(
        store,
        "_commit_guardian_delegation_delivery",
        commit_with_duplicate_collision,
    )

    delivery = store.store_coding_result(
        run_id=str(created["run_id"]),
        coding_task_id="task-1",
        attempt_id="attempt-1",
        thread_id=int(created["thread_id"]),
        source_message_id=int(created["source_message_id"]),
        result_status="succeeded",
        result_summary="Patched the delivery path cleanly.",
        files_changed=["guardian/agents/store.py"],
    )

    assert delivery["delivery_ok"] is True
    assert delivery["delivery_status"] == "delivered"
    messages = _fetch_thread_messages(
        db, created["thread_id"], kind="coding_result"
    )
    assert len(messages) == 1
    assert delivery["message_id"] == messages[0].id


def test_late_cancelled_intent_suppresses_before_final_delivery(
    delegation_client: TestClient,
    db: _TestDB,
    auth_headers,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seeded = _seed_source_context(db)
    created = _create_guardian_intent(delegation_client, auth_headers, seeded)
    store = _make_store(db)

    def cancel_before_finalize(
        *,
        session: Any,
        intent: GuardianDelegationIntent,
        delivery_key: str,
        run_id: str,
    ) -> None:
        intent.intent_status = "cancelled"

    monkeypatch.setattr(
        store,
        "_before_guardian_delegation_delivery_finalize",
        cancel_before_finalize,
    )

    delivery = store.store_coding_result(
        run_id=str(created["run_id"]),
        coding_task_id="task-1",
        attempt_id="attempt-1",
        thread_id=int(created["thread_id"]),
        source_message_id=int(created["source_message_id"]),
        result_status="succeeded",
        result_summary="Patched the delivery path cleanly.",
        files_changed=["guardian/agents/store.py"],
    )

    assert delivery["delivery_ok"] is False
    assert delivery["delivery_status"] == "stale_suppressed"
    assert delivery["visibility_status"] == "stale_suppressed"
    assert _fetch_thread_messages(db, created["thread_id"], kind="coding_result") == []

    row = _fetch_intent(db, created["intent_id"])
    assert row is not None
    assert row.intent_status == "cancelled"
    assert row.visibility_status == "stale_suppressed"


def test_validation_results_error_message_is_sanitized(
    delegation_client: TestClient,
    db: _TestDB,
    auth_headers,
) -> None:
    selected_content = "Please patch guardian/agents/store.py."
    seeded = _seed_source_context(db, selected_content=selected_content)
    created = _create_guardian_intent(delegation_client, auth_headers, seeded)

    _store_guardian_result(
        db,
        intent_payload=created,
        result_summary="Patched the delivery path cleanly.",
        validation_results={
            "status": "failed",
            "error_message": (
                f"{selected_content} context_basis my boss is frustrating me"
            ),
        },
    )

    messages = _fetch_thread_messages(
        db, created["thread_id"], kind="coding_result"
    )
    assert len(messages) == 1
    content = messages[0].content
    assert selected_content not in content
    assert "context_basis" not in content
    assert "my boss is frustrating me" not in content
    assert "[redacted unsafe validation detail]" in content
    safe_validation = messages[0].extra_meta["validation_results"]
    assert safe_validation["error_message"] == "[redacted unsafe validation detail]"


def test_validation_results_command_is_sanitized(
    delegation_client: TestClient,
    db: _TestDB,
    auth_headers,
) -> None:
    seeded = _seed_source_context(db)
    created = _create_guardian_intent(delegation_client, auth_headers, seeded)

    _store_guardian_result(
        db,
        intent_payload=created,
        result_summary="Patched the delivery path cleanly.",
        validation_results={
            "status": "failed",
            "command": (
                "OPENAI_API_KEY=sk-supersecret "
                "/Users/chris/.ssh/id_rsa pytest guardian/agents/store.py"
            ),
        },
    )

    messages = _fetch_thread_messages(
        db, created["thread_id"], kind="coding_result"
    )
    assert len(messages) == 1
    content = messages[0].content
    assert "OPENAI_API_KEY" not in content
    assert "sk-supersecret" not in content
    assert "/Users/chris/.ssh/id_rsa" not in content
    assert "[redacted unsafe validation detail]" in content
    safe_validation = messages[0].extra_meta["validation_results"]
    assert safe_validation["command"] == "[redacted unsafe validation detail]"


def test_files_changed_paths_are_sanitized(
    delegation_client: TestClient,
    db: _TestDB,
    auth_headers,
) -> None:
    seeded = _seed_source_context(db)
    created = _create_guardian_intent(delegation_client, auth_headers, seeded)

    _store_guardian_result(
        db,
        intent_payload=created,
        result_summary="Patched the delivery path cleanly.",
        files_changed=[
            "guardian/agents/store.py",
            "/home/user/.ssh/id_rsa",
            ".env",
            "/Volumes/Dev_SSD/Codexify-main/guardian/core/guardian_delegation_service.py",
        ],
    )

    messages = _fetch_thread_messages(
        db, created["thread_id"], kind="coding_result"
    )
    assert len(messages) == 1
    content = messages[0].content
    assert "guardian/agents/store.py" in content
    assert "guardian/core/guardian_delegation_service.py" in content
    assert "/home/user/.ssh/id_rsa" not in content
    assert ".env" not in content
    assert "/Volumes/Dev_SSD/Codexify-main/" not in content
    assert "[redacted unsafe path]" in content
    assert messages[0].extra_meta["files_changed"] == [
        "guardian/agents/store.py",
        "guardian/core/guardian_delegation_service.py",
        "[redacted unsafe path]",
    ]


# The packet/job lane shares Guardian-owned delivery, without legacy run records.
def _completed_packet_job(
    db, *, summary_text="Completed the bounded task.", context=None
):
    from guardian.core.delegation_service import DelegationService
    from guardian.tasks.types import DelegationDraftRequest

    seeded = _seed_source_context(db)
    service = DelegationService(db)
    packet = service.draft_packet(
        DelegationDraftRequest(
            thread_id=seeded["thread_id"],
            project_id=seeded["project_id"],
            repo_path="/tmp/disposable-fixture",
            executor="codex",
            user_intent="Read the disposable token without modifications.",
            context={
                "source_message_id": seeded["source_message_id"],
                "execution_interface": "app_server",
                **(context or {}),
            },
        )
    )
    approval = service.approve_packet(packet.packet_id)
    normalized = service.build_summary_packet(
        approval.job,
        summary=summary_text,
        result={
            "execution_channel": "codex",
            "execution_interface": "app_server",
            "native_codex_thread_id": "native-thread",
            "native_codex_turn_id": "native-turn",
            "inference_route": {"provider_id": "openai", "evidence_status": "observed"},
            "model_identity": {
                "configured_model_id": "configured-only",
                "evidence_status": "configured_only",
            },
            "raw_transcript": "hidden prompt secret=DO_NOT_COPY",
            "environment": {"PASSWORD": "DO_NOT_COPY"},
            "request_id": approval.job.delegation_id,
        },
        status="completed",
    )
    service.mark_job_completed(approval.job.delegation_id, summary=normalized)
    return seeded, approval


def test_completed_packet_delivery_survives_fresh_sessions_and_concurrent_retry(db):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from guardian.core.delegation_service import DelegationService
    from guardian.db.models import DelegationSummary

    seeded, approval = _completed_packet_job(db)
    barrier = Barrier(2)

    def deliver():
        barrier.wait(timeout=10)
        return DelegationService(db).deliver_completed_result(
            approval.job.delegation_id
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(deliver) for _ in range(2)]
        receipts = [future.result(timeout=20).metadata for future in futures]
    replay = DelegationService(db).deliver_completed_result(approval.job.delegation_id)
    messages = _fetch_thread_messages(db, seeded["thread_id"], kind="coding_result")
    assert len(messages) == 1
    message = messages[0]
    assert message.role == "assistant"
    assert all(r["result_message_id"] == message.id for r in receipts)
    assert replay.metadata["result_message_id"] == message.id
    assert (
        replay.metadata["delivery_key"]
        == f"delegation:{approval.job.delegation_id}:thread_result"
    )
    for key, value in seeded.items():
        if key != "user_id":
            assert message.extra_meta[key] == value
    assert message.extra_meta["delegation_id"] == approval.job.delegation_id
    assert message.extra_meta["task_id"] == approval.job.task_id
    assert message.extra_meta["native_codex_thread_id"] == "native-thread"
    assert message.extra_meta["provider_id"] == "openai"
    assert "configured_model_id" not in message.extra_meta
    assert "Completed the bounded task." in message.content
    assert "DO_NOT_COPY" not in str(message.extra_meta) + message.content
    with db.get_session() as session:
        assert session.query(AgentRun).count() == 0
        assert session.query(GuardianDelegationIntent).count() == 0
        row = session.get(DelegationSummary, approval.job.delegation_id)
        assert row.status == "completed"
        assert row.summary_json["metadata"]["delivery_ok"] is True


@pytest.mark.parametrize(
    "corruption",
    [
        "missing_thread",
        "missing_source",
        "missing_project",
        "wrong_source_thread",
        "wrong_project",
        "wrong_source_owner",
        "wrong_project_owner",
        "wrong_account",
        "wrong_summary_lineage",
        "wrong_result_lineage",
        "missing_thread_row",
        "missing_message_row",
    ],
)
def test_completed_packet_delivery_rejects_orphaned_lineage(db, corruption):
    from guardian.core.delegation_service import DelegationService
    from guardian.db.models import DelegationJob, DelegationPacket, DelegationSummary

    seeded, approval = _completed_packet_job(db)
    with db.get_session() as session:
        job = session.get(DelegationJob, approval.job.delegation_id)
        packet = session.get(DelegationPacket, approval.packet.packet_id)
        row = session.get(DelegationSummary, approval.job.delegation_id)
        data = dict(row.summary_json)
        if corruption == "missing_thread":
            job.thread_id = None
        elif corruption == "missing_project":
            job.project_id = None
        elif corruption == "missing_source":
            packet.context_json = {"execution_interface": "app_server"}
        elif corruption == "wrong_source_thread":
            other = ChatThread(
                user_id=seeded["user_id"],
                project_id=seeded["project_id"],
                title="Other",
            )
            session.add(other)
            session.flush()
            session.get(ChatMessage, seeded["source_message_id"]).thread_id = other.id
        elif corruption == "wrong_project":
            session.get(ChatThread, seeded["thread_id"]).project_id = None
        elif corruption in {
            "wrong_source_owner",
            "wrong_project_owner",
            "wrong_account",
        }:
            session.add(
                User(id="other-user", username="other-user", password_hash="hash")
            )
            session.flush()
            if corruption == "wrong_source_owner":
                session.get(
                    ChatMessage, seeded["source_message_id"]
                ).user_id = "other-user"
            elif corruption == "wrong_project_owner":
                session.get(Project, seeded["project_id"]).user_id = "other-user"
            else:
                packet.context_json = {**packet.context_json, "user_id": "other-user"}
        elif corruption == "wrong_summary_lineage":
            data["source_message_id"] = 999
            row.summary_json = data
        elif corruption == "wrong_result_lineage":
            data["result"] = {**data["result"], "thread_id": 999}
            row.summary_json = data
        elif corruption == "missing_thread_row":
            session.delete(session.get(ChatThread, seeded["thread_id"]))
        elif corruption == "missing_message_row":
            session.delete(session.get(ChatMessage, seeded["source_message_id"]))
        session.commit()
    result = DelegationService(db).deliver_completed_result(approval.job.delegation_id)
    assert result.status == "completed"
    assert result.metadata["delivery_ok"] is False
    assert result.metadata["delivery_reason"]
    assert _fetch_thread_messages(db, seeded["thread_id"], kind="coding_result") == []


@pytest.mark.parametrize(
    "summary_text",
    [
        "hidden prompt DO_NOT_COPY",
        "api_key=DO_NOT_COPY",
        "worker file (/Users/operator/private/proof.txt)",
        "HOME=/private/operator",
        "Please patch the return path.",
        "x" * 10000,
    ],
)
def test_completed_packet_delivery_uses_bounded_sanitized_content(db, summary_text):
    from guardian.core.delegation_service import DelegationService

    seeded, approval = _completed_packet_job(db, summary_text=summary_text)
    result = DelegationService(db).deliver_completed_result(approval.job.delegation_id)
    assert result.metadata["delivery_ok"] is True
    message = _fetch_thread_messages(db, seeded["thread_id"], kind="coding_result")[0]
    assert len(message.content) < 1000
    for forbidden in [
        "DO_NOT_COPY",
        "/Users/operator",
        "HOME=",
        "/private/operator",
        "Please patch the return path.",
    ]:
        assert forbidden not in message.content + str(message.extra_meta)


def test_completed_packet_write_failure_retains_success_and_can_retry(db, monkeypatch):
    from guardian.agents import store as store_module
    from guardian.core.delegation_service import DelegationService

    seeded, approval = _completed_packet_job(db)
    insert = store_module._store_source_thread_result

    def fail_after_insert(*args, **kwargs):
        insert(*args, **kwargs)
        raise RuntimeError("password=DO_NOT_COPY /Users/private/sql")

    monkeypatch.setattr(store_module, "_store_source_thread_result", fail_after_insert)
    degraded = DelegationService(db).deliver_completed_result(
        approval.job.delegation_id
    )
    assert degraded.status == "completed"
    assert degraded.summary == "Completed the bounded task."
    assert degraded.metadata["delivery_ok"] is False
    assert "DO_NOT_COPY" not in str(degraded.metadata)
    assert _fetch_thread_messages(db, seeded["thread_id"], kind="coding_result") == []
    monkeypatch.setattr(store_module, "_store_source_thread_result", insert)
    recovered = DelegationService(db).deliver_completed_result(
        approval.job.delegation_id
    )
    assert recovered.metadata["delivery_ok"] is True
    assert (
        len(_fetch_thread_messages(db, seeded["thread_id"], kind="coding_result")) == 1
    )


def test_packet_worker_delivers_before_terminal_event_and_replays_without_executor(
    db, monkeypatch
):
    from guardian.core.delegation_service import DelegationService
    from guardian.core.executors.base import ExecutorTerminalResult
    from guardian.core.executors.codex_app_server_executor import CodexAppServerExecutor
    from guardian.db.models import DelegationJob, DelegationSummary
    from guardian.workers import delegation_worker

    seeded, approval = _completed_packet_job(db)
    with db.get_session() as session:
        session.delete(session.get(DelegationSummary, approval.job.delegation_id))
        job = session.get(DelegationJob, approval.job.delegation_id)
        job.status = "queued"
        job.completed_at = None
        session.commit()
    calls = []
    events = []

    def execute(self, request, **kwargs):
        calls.append(request.request_id)
        return ExecutorTerminalResult(
            request_id=request.request_id,
            delegation_id=request.delegation_id,
            task_id=request.task_id,
            thread_id=request.thread_id,
            source_message_id=request.source_message_id,
            project_id=request.project_id,
            executor_id=request.executor_id,
            title=request.title,
            status="completed",
            summary="Worker accepted this result.",
            final_text="Worker accepted this result.",
        )

    def publish(task_id, event_type, payload):
        events.append(event_type)
        if event_type == "delegation.completed":
            assert (
                DelegationService(db).get_job(approval.job.delegation_id).status
                == "completed"
            )
            assert (
                len(
                    _fetch_thread_messages(
                        db, seeded["thread_id"], kind="coding_result"
                    )
                )
                == 1
            )
            assert payload["metadata"]["delivery_ok"] is True
        return {"ok": True}

    monkeypatch.setattr(CodexAppServerExecutor, "execute", execute)
    monkeypatch.setattr(delegation_worker, "is_cancelled", lambda *_: False)
    monkeypatch.setattr(delegation_worker, "clear_cancelled", lambda *_: None)
    monkeypatch.setattr(
        delegation_worker.task_events, "publish_with_visibility", publish
    )
    first = delegation_worker.process_delegation_task(
        approval.task, service=DelegationService(db)
    )
    second = delegation_worker.process_delegation_task(
        approval.task, service=DelegationService(db)
    )
    assert (
        first["metadata"]["result_message_id"]
        == second["metadata"]["result_message_id"]
    )
    assert calls == [approval.job.delegation_id]
    assert events[-1] == "delegation.completed"


def test_packet_running_execution_cannot_post_terminal_message(db):
    from guardian.agents.store import AgentStore
    from guardian.db.models import DelegationJob

    seeded, approval = _completed_packet_job(db)
    with db.get_session() as session:
        session.get(DelegationJob, approval.job.delegation_id).status = "running"
        session.commit()
    receipt = AgentStore(db).deliver_completed_delegation(approval.job.delegation_id)
    assert receipt["delivery_ok"] is False
    assert _fetch_thread_messages(db, seeded["thread_id"], kind="coding_result") == []


@pytest.mark.parametrize('contradictory', [False, True])
def test_packet_delivery_source_aliases_are_explicit_and_unambiguous(db, contradictory):
    from guardian.core.delegation_service import DelegationService
    from guardian.db.models import DelegationPacket
    seeded, approval = _completed_packet_job(db)
    with db.get_session() as session:
        packet = session.get(DelegationPacket,approval.packet.packet_id)
        context = dict(packet.context_json)
        context['sourceMessageId'] = context.pop('source_message_id')
        if contradictory:
            context['messageId'] = 999
        packet.context_json = context
        session.commit()
    result = DelegationService(db).deliver_completed_result(approval.job.delegation_id)
    assert result.metadata['delivery_ok'] is (not contradictory)
    assert len(_fetch_thread_messages(db,seeded['thread_id'],kind='coding_result')) == (0 if contradictory else 1)
