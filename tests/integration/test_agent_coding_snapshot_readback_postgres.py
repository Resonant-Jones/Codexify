"""Mounted account-reader proof with disposable PostgreSQL authority.

Requires AGENT_SNAPSHOT_TEST_DATABASE_URL pointing to the dedicated loopback
agent_snapshot_proof database. Creates only a unique test schema; never uses
the application's DATABASE_URL or production services.
"""

from __future__ import annotations

import os
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.attributes import flag_modified

from guardian.agents.store import AgentStore
from guardian.core import session_store
from guardian.core.auth import (
    ACCOUNT_SESSION_PURPOSE,
    OPERATOR_SESSION_PURPOSE,
    issue_session_token,
)
from guardian.core.hosted_room_session import issue_guest_session_token
from guardian.db.models import (
    AgentDeployment,
    AgentRun,
    AgentRunArtifact,
    Base,
    ChatThread,
    User,
)
from guardian.queue import redis_queue
from guardian.routes import agent_orchestration as routes

ACCOUNT_A = "snapshot-a@example.invalid"
ACCOUNT_B = "snapshot-b@example.invalid"
READ_PATHS = (
    "/api/agents/runs/{run_id}/coding",
    "/api/agents/runs/{run_id}",
    "/api/chat/{thread_id}/coding-runs",
    "/api/chat/{thread_id}/agent-runs",
    "/api/agents/chat/{thread_id}/agent-runs",
)


@pytest.fixture
def readback(monkeypatch):
    raw_url = os.getenv("AGENT_SNAPSHOT_TEST_DATABASE_URL")
    if not raw_url:
        pytest.skip("AGENT_SNAPSHOT_TEST_DATABASE_URL is required")
    url = make_url(raw_url)
    assert url.host in {"localhost", "127.0.0.1"}
    assert url.database == "agent_snapshot_proof"
    assert url.drivername == "postgresql+psycopg"
    schema = f"agent_snapshot_{uuid4().hex}"
    admin = create_engine(url)
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    sessions = sessionmaker(bind=engine)
    # Existing ORM tables and their FK closure; no runtime schema/migration edit.
    tables = {
        User.__table__,
        ChatThread.__table__,
        AgentDeployment.__table__,
        AgentRun.__table__,
        AgentRunArtifact.__table__,
    }
    while True:
        expanded = tables | {
            fk.column.table for table in tables for fk in table.foreign_keys
        }
        if expanded == tables:
            break
        tables = expanded
    try:
        Base.metadata.create_all(engine, tables=list(tables))
        with sessions() as session:
            session.add_all(
                [
                    User(id=account, username=account, password_hash="inert-fixture")
                    for account in (ACCOUNT_A, ACCOUNT_B)
                ]
            )
            session.flush()
            thread = ChatThread(user_id=ACCOUNT_A, title="account A source")
            other = ChatThread(user_id=ACCOUNT_B, title="account B source")
            session.add_all([thread, other])
            session.commit()
            thread_id, other_id = thread.id, other.id
        db = SimpleNamespace(get_session=Mock(side_effect=sessions))
        store = AgentStore(db=db)
        deployment = store.create_deployment(
            flow_id="coding-proof",
            thread_id=thread_id,
            spec_json={
                "user_id": ACCOUNT_A,
                "coding_task_id": "coding-proof",
                "source_thread_id": thread_id,
                "attempt_id": "attempt-proof",
            },
            spec_hash="fixture",
        )
        run = store.create_run(
            deployment_id=deployment["deployment_id"], thread_id=thread_id
        )
        monkeypatch.setattr(routes, "_store", store)
        events = Mock(
            side_effect=AssertionError("snapshot/quarantine must not read events")
        )
        monkeypatch.setattr(routes.task_events, "read_events", events)
        monkeypatch.setenv("GUARDIAN_AUTH_MODE", "remote")
        monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "local_safe")
        monkeypatch.setenv("CODEXIFY_MULTI_USER_ENABLED", "true")
        monkeypatch.setenv("GUARDIAN_SESSION_SECRET", "inert-snapshot-proof-secret")
        monkeypatch.setenv(
            "CODEXIFY_PREVIEW_APPROVED_EMAILS", f"{ACCOUNT_A},{ACCOUNT_B}"
        )
        token_store = session_store.SessionStore(
            redis_client=redis_queue._InMemoryRedis()
        )
        monkeypatch.setattr(session_store, "_SESSION_STORE", token_store)
        tokens = {}
        for account in (ACCOUNT_A, ACCOUNT_B):
            token, _ = issue_session_token(
                subject=account, purpose=ACCOUNT_SESSION_PURPOSE
            )
            token_store.store(token, account, ttl=3600)
            tokens[account] = token
        app = FastAPI()
        app.include_router(routes.router)
        app.include_router(routes.chat_router)
        assert not app.dependency_overrides
        with TestClient(app, raise_server_exceptions=False) as client:
            yield SimpleNamespace(
                client=client,
                sessions=sessions,
                store=store,
                db=db,
                events=events,
                thread_id=thread_id,
                other_id=other_id,
                run_id=run["run_id"],
                deployment_id=deployment["deployment_id"],
                tokens=tokens,
            )
        events.assert_not_called()
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


def _headers(readback, account=ACCOUNT_A):
    return {"Authorization": f"Bearer {readback.tokens[account]}", "X-API-Key": ""}


def _path(readback, template):
    return template.format(run_id=readback.run_id, thread_id=readback.thread_id)


@pytest.mark.parametrize("path", READ_PATHS)
def test_owner_reads_exact_durable_run_and_thread(readback, path):
    response = readback.client.get(_path(readback, path), headers=_headers(readback))
    assert response.status_code == 200
    payload = response.json()
    runs = payload.get("runs", [payload.get("run")])
    assert [run["run_id"] for run in runs] == [readback.run_id]
    assert all(run["thread_id"] == readback.thread_id for run in runs)


@pytest.mark.parametrize("path", READ_PATHS)
def test_other_account_and_spoofed_header_are_denied(readback, path):
    headers = {**_headers(readback, ACCOUNT_B), "X-User-Id": ACCOUNT_A}
    response = readback.client.get(_path(readback, path), headers=headers)
    assert response.status_code == 404
    assert readback.run_id not in response.text


@pytest.mark.parametrize("path", READ_PATHS)
@pytest.mark.parametrize(
    "kind", ["missing", "operator", "operator_key", "guest", "mixed"]
)
def test_wrong_principal_rejected_before_resource_lookup(readback, path, kind):
    headers = {"X-API-Key": ""}
    cookies = {}
    if kind == "operator":
        token, _ = issue_session_token(subject="web", purpose=OPERATOR_SESSION_PURPOSE)
        headers["Authorization"] = f"Bearer {token}"
    elif kind == "operator_key":
        headers["X-API-Key"] = "test-api-key"
    elif kind == "guest":
        token, _ = issue_guest_session_token(
            room_id="fixture-room",
            room_slug="fixture-room",
            participant_id="fixture-guest",
            invitation_id="fixture-invite",
        )
        headers["Authorization"] = f"Bearer {token}"
    elif kind == "mixed":
        headers = _headers(readback)
        cookies["codexify_hosted_room_session"] = "malformed-guest-selector"
    readback.db.get_session.reset_mock()
    response = readback.client.get(
        _path(readback, path), headers=headers, cookies=cookies
    )
    assert response.status_code == (400 if kind == "mixed" else 401)
    readback.db.get_session.assert_not_called()


@pytest.mark.parametrize("path", READ_PATHS[:2])
@pytest.mark.parametrize(
    "identifier", ["unknown-run", "coding-proof", "attempt-proof", "queue-uuid"]
)
def test_correlation_identifiers_do_not_authorize_run_reads(readback, path, identifier):
    response = readback.client.get(
        path.format(run_id=identifier), headers=_headers(readback)
    )
    assert response.status_code == 404


@pytest.mark.parametrize(
    "fault",
    [
        "missing_owner",
        "empty_owner",
        "foreign_owner",
        "missing_source",
        "foreign_source",
        "string_source",
        "bool_source",
        "numeric_source",
        "operator_only",
        "threadless",
        "deployment_thread_mismatch",
        "deleted_thread",
        "thread_owner_changed",
    ],
)
def test_missing_deleted_or_ambiguous_authority_fails_closed(readback, fault):
    with readback.sessions() as session:
        deployment = (
            session.query(AgentDeployment)
            .filter_by(deployment_id=readback.deployment_id)
            .one()
        )
        run = session.query(AgentRun).filter_by(run_id=readback.run_id).one()
        spec = dict(deployment.spec_json)
        if fault == "missing_owner":
            spec.pop("user_id")
        elif fault == "empty_owner":
            spec["user_id"] = ""
        elif fault == "foreign_owner":
            spec["user_id"] = ACCOUNT_B
        elif fault == "missing_source":
            spec.pop("source_thread_id")
        elif fault == "foreign_source":
            spec["source_thread_id"] = readback.other_id
        elif fault == "string_source":
            spec["source_thread_id"] = str(readback.thread_id)
        elif fault == "bool_source":
            spec["source_thread_id"] = True
        elif fault == "numeric_source":
            spec["source_thread_id"] = float(readback.thread_id)
        elif fault == "operator_only":
            spec.pop("coding_task_id")
        elif fault == "threadless":
            run.thread_id = deployment.thread_id = None
        elif fault == "deployment_thread_mismatch":
            deployment.thread_id = readback.other_id
        elif fault == "deleted_thread":
            session.execute(
                delete(ChatThread).where(ChatThread.id == readback.thread_id)
            )
        elif fault == "thread_owner_changed":
            session.get(ChatThread, readback.thread_id).user_id = ACCOUNT_B
        deployment.spec_json = spec
        # Python considers True/1/1.0 equal; force the intended JSONB mutation.
        flag_modified(deployment, "spec_json")
        session.commit()
    for path in READ_PATHS[:2]:
        response = readback.client.get(
            _path(readback, path), headers=_headers(readback)
        )
        assert response.status_code == 404
    for path in READ_PATHS[2:]:
        response = readback.client.get(
            _path(readback, path), headers=_headers(readback)
        )
        expected = 404 if fault in {"deleted_thread", "thread_owner_changed"} else 200
        assert response.status_code == expected
        if expected == 200:
            assert response.json()["runs"] == []


@pytest.mark.parametrize("path", READ_PATHS)
def test_memory_fallback_cannot_supply_account_authority(readback, monkeypatch, path):
    memory = AgentStore()
    deployment = memory.create_deployment(
        flow_id="memory-only",
        thread_id=readback.thread_id,
        spec_json={
            "user_id": ACCOUNT_A,
            "coding_task_id": "coding-proof",
            "source_thread_id": readback.thread_id,
        },
        spec_hash="memory",
    )
    run = memory.create_run(
        deployment_id=deployment["deployment_id"], thread_id=readback.thread_id
    )
    monkeypatch.setattr(routes, "_store", memory)
    target = path.format(run_id=run["run_id"], thread_id=readback.thread_id)
    assert readback.client.get(target, headers=_headers(readback)).status_code == 404


def test_database_failure_does_not_fall_back_to_memory_or_events(readback):
    readback.db.get_session.side_effect = RuntimeError(
        "disposable database unavailable"
    )
    for path in READ_PATHS:
        response = readback.client.get(
            _path(readback, path), headers=_headers(readback)
        )
        assert response.status_code == 500
        assert readback.run_id not in response.text


@pytest.mark.parametrize(
    "exposure,auth_mode",
    [
        ("local_safe", "remote"),
        ("public_allowlist", "local"),
        ("private_preview", "local"),
        ("local_safe", "unknown-mode"),
    ],
)
@pytest.mark.parametrize("identifier", ["owned", "unknown-run"])
def test_public_dedicated_sse_is_quarantined_before_lookup_and_redis(
    readback,
    monkeypatch,
    exposure,
    auth_mode,
    identifier,
):
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", exposure)
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", auth_mode)
    readback.db.get_session.reset_mock()
    run_id = readback.run_id if identifier == "owned" else identifier
    response = readback.client.get(
        f"/api/agents/runs/{run_id}/events", headers=_headers(readback)
    )
    assert response.status_code == 404
    readback.db.get_session.assert_not_called()


def test_snapshot_result_stays_path_bounded(readback):
    with readback.sessions() as session:
        run = session.query(AgentRun).filter_by(run_id=readback.run_id).one()
        session.add(
            AgentRunArtifact(
                run_id=run.id,
                artifact_type="coding_result",
                content_json={
                    "status": "failed",
                    "summary": "bounded readback",
                    "files_changed": ["/private/worktree/secret.py"],
                    "artifacts": [
                        {"kind": "patch", "name": "/private/worktree/result.patch"}
                    ],
                    "error_message": "failure in /private/worktree/secret.py",
                },
            )
        )
        session.commit()
    response = readback.client.get(
        _path(readback, READ_PATHS[0]), headers=_headers(readback)
    )
    assert response.status_code == 200
    assert "/private/worktree" not in response.text
    assert response.json()["run"]["result"]["files_changed_count"] == 1
