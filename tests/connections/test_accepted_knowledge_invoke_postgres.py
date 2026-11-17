"""Private entry point + real accepted rows + durable Command Bus audit.

Provider responses are synthetic HTTPX transport fixtures, never live requests.
"""

import asyncio
import json

from fastapi import FastAPI
import httpx
import pytest

from guardian.command_bus.accepted_knowledge_invoke import (
    execute_accepted_knowledge_read,
)
from guardian.command_bus.accepted_knowledge_read import (
    AcceptedKnowledgeReadUnavailable,
)
from guardian.command_bus.store import CommandBusStore
from guardian.connections import chat_pilot, oauth_store
from guardian.connections.github.router import operations_router as github_router
from guardian.connections.notion.router import operations_router as notion_router
from guardian.db.models import CommandRun, ChatCompletionAttempt
from guardian.core.chat_account_custody import ChatAccountAcceptancePending
from tests.connections import test_accepted_chat_custody_postgres as custody
from tests.connections.test_accepted_knowledge_read_postgres import connect
from tests.command_bus.test_accepted_knowledge_invoke import (
    CASES,
    WaitingBody,
    install_http,
    payload_for,
    response_for,
)

db, engine = custody.db, custody.engine


@pytest.fixture(autouse=True)
def enabled(monkeypatch):
    monkeypatch.setenv("CODEXIFY_ENABLE_KNOWLEDGE_OAUTH", "1")
    monkeypatch.delenv("GUARDIAN_COMMAND_BUS_LOOPBACK_BASE", raising=False)
    monkeypatch.delenv("GUARDIAN_API_BASE", raising=False)


def prepare(db, command, raw, owner="a"):
    provider = chat_pilot.COMMANDS[command][0]
    connect(db, owner, provider)
    task, _, _ = custody.accepted(
        db, owner, provider, command_id=command, raw_arguments=raw
    )
    payload = payload_for(task, command, chat_pilot.hydrate_arguments(command, raw))
    payload.provenance_json = {"forged": "synthetic-private-sentinel"}
    payload.idempotency_key = "caller-must-not-control-this"
    app = FastAPI()
    app.include_router(github_router)
    app.include_router(notion_router)
    return task, payload, app


async def run(db, prepared):
    task, payload, app = prepared
    return await execute_accepted_knowledge_read(
        db=db, task=task, payload=payload, app=app
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("command,raw", CASES)
async def test_durable_account_attempt_audit_and_duplicate_delivery(
    db, monkeypatch, command, raw
):
    prepared = prepare(db, command, raw)
    calls = []

    async def handler(request):
        calls.append(request)
        return httpx.Response(200, json=response_for(request))

    install_http(monkeypatch, handler)
    first, concurrent = await asyncio.gather(run(db, prepared), run(db, prepared))
    assert first["run_id"] == concurrent["run_id"]
    assert first["status"] in {"queued", "running", "completed"}
    replay = await run(db, prepared)
    assert replay["status"] == "completed"
    assert len(calls) == (2 if command == "op::notion_content_read" else 1)
    # A new store proves durable state rather than an in-memory assertion.
    store = CommandBusStore(db)
    saved = store.get_run(replay["run_id"])
    assert saved["auth_subject"] == saved["delegated_by"] == "a"
    assert saved["actor_id"] == "guardian-accepted-knowledge"
    assert saved["idempotency_key"].startswith("accepted-knowledge:")
    events = store.list_events_after(run_id=replay["run_id"], after_seq=0)
    assert [event["event_type"] for event in events] == [
        "run.created",
        "run.started",
        "run.completed",
    ]
    lineage = events[0]["payload_json"]["provenance_json"]["accepted_knowledge"]
    assert (
        lineage["request_id"] == prepared[0].request_id
        and lineage["backend_task_id"] == prepared[0].task_id
    )
    assert lineage["account_id"] == "a" and lineage["args_hash"] == saved["args_hash"]
    assert all(
        event["payload_json"]["provenance_json"]["accepted_knowledge"] == lineage
        for event in events
    )
    serialized = json.dumps(events) + json.dumps(saved)
    assert (
        "synthetic-access" not in serialized
        and "synthetic-private-sentinel" not in serialized
    )


@pytest.mark.asyncio
async def test_account_b_cannot_reuse_a_and_sequential_credentials_are_separate(
    db, monkeypatch
):
    a = prepare(db, *CASES[0], owner="a")
    b = prepare(db, *CASES[0], owner="b")
    seen = []

    async def handler(request):
        seen.append(request.headers["authorization"])
        return httpx.Response(200, json=response_for(request))

    install_http(monkeypatch, handler)
    ra, rb = await run(db, a), await run(db, b)
    assert ra["run_id"] != rb["run_id"]
    assert seen == ["Bearer synthetic-access-a", "Bearer synthetic-access-b"]
    a[0].user_id = "b"
    with pytest.raises(AcceptedKnowledgeReadUnavailable):
        await run(db, a)
    assert len(seen) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("reason", ["revoked", "cancelled"])
async def test_live_database_revocation_or_cancellation_has_durable_failure(
    db, monkeypatch, reason
):
    prepared = prepare(db, *CASES[0])
    body = WaitingBody()
    install_http(monkeypatch, lambda request: httpx.Response(200, stream=body))
    pending = asyncio.create_task(run(db, prepared))
    await asyncio.wait_for(body.started.wait(), 3)
    if reason == "revoked":
        oauth_store.disconnect(db, "a", "github")
        result = await asyncio.wait_for(pending, 3)
        assert result["status"] == "failed"
    else:
        pending.cancel()
        with pytest.raises(asyncio.CancelledError):
            await pending
    with db.get_session() as session:
        row = session.query(CommandRun).one()
        assert row.status == "failed" and row.result_json is None
        run_id = row.run_id
    events = CommandBusStore(db).list_events_after(run_id=run_id, after_seq=0)
    assert events[-1]["event_type"] == "run.failed"
    assert (
        events[-1]["payload_json"]["provenance_json"]["accepted_knowledge"][
            "account_id"
        ]
        == "a"
    )
    assert body.closed and body.cancelled


@pytest.mark.asyncio
async def test_permission_denial_persists_without_decrypting_credentials(
    db, monkeypatch
):
    prepared = prepare(db, *CASES[0])
    prepared[1].permission_profile.network_allowed = False
    monkeypatch.setattr(
        oauth_store, "credential", lambda *a: pytest.fail("denied before credentials")
    )
    install_http(monkeypatch, lambda request: pytest.fail("denied before provider"))
    result = await run(db, prepared)
    assert result["status"] == "blocked"
    store = CommandBusStore(db)
    assert store.get_run(result["run_id"])["status"] == "blocked"
    assert (
        store.list_events_after(run_id=result["run_id"], after_seq=0)[-1]["event_type"]
        == "run.blocked"
    )


@pytest.mark.asyncio
async def test_row_lock_timeout_refuses_before_any_provider_or_command_run(
    db, monkeypatch
):
    prepared = prepare(db, *CASES[0])
    install_http(
        monkeypatch, lambda request: pytest.fail("locked authority is unavailable")
    )
    with db._sa_session() as locker:
        locker.query(ChatCompletionAttempt).filter_by(
            request_id=prepared[0].request_id
        ).with_for_update().one()
        with pytest.raises(AcceptedKnowledgeReadUnavailable):
            await asyncio.wait_for(run(db, prepared), 3)
    with db.get_session() as session:
        assert session.query(CommandRun).count() == 0


@pytest.mark.asyncio
async def test_audit_storage_failure_refuses_before_io_without_raw_error(
    db, monkeypatch
):
    prepared = prepare(db, *CASES[0])

    def unavailable(*args, **kwargs):
        raise RuntimeError("synthetic-private-storage-detail")

    monkeypatch.setattr(CommandBusStore, "create_run", unavailable)
    install_http(monkeypatch, lambda request: pytest.fail("no audit means no read"))
    with pytest.raises(AcceptedKnowledgeReadUnavailable) as error:
        await run(db, prepared)
    assert str(error.value) == "accepted_knowledge_read_unavailable"
    assert error.value.__suppress_context__


@pytest.mark.asyncio
async def test_publication_before_acknowledgement_remains_retryable_pending(
    db, monkeypatch
):
    command, raw = CASES[0]
    connect(db, provider="github")
    task, _, _ = custody.accepted(db, provider="github", acknowledged=False)
    payload = payload_for(task, command, chat_pilot.hydrate_arguments(command, raw))
    install_http(
        monkeypatch, lambda request: pytest.fail("pending acceptance cannot read")
    )
    with pytest.raises(ChatAccountAcceptancePending):
        await execute_accepted_knowledge_read(
            db=db, task=task, payload=payload, app=FastAPI()
        )
    with db.get_session() as session:
        assert session.query(CommandRun).count() == 0
