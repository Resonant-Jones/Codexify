"""Synthetic catalog -> freeze -> private bus -> durable delivery; no chat wiring."""

from fastapi import FastAPI
import httpx
import pytest

from guardian.command_bus.accepted_knowledge_admission import (
    project_accepted_knowledge_tools,
    read_accepted_knowledge_result,
)
from guardian.command_bus.accepted_knowledge_invoke import (
    execute_accepted_knowledge_read,
)
from guardian.command_bus.accepted_knowledge_read import (
    AcceptedKnowledgeReadUnavailable,
)
from guardian.command_bus.manifest import build_command_index
from guardian.command_bus.store import CommandBusStore
from guardian.connections import chat_pilot, oauth_store
from guardian.core.chat_account_custody import ChatAccountAcceptancePending
from guardian.core.db import (
    freeze_chat_tool_decision,
    mark_chat_completion_attempt_accepted,
)
from guardian.db.models import ChatCompletionAttempt, ChatThread, Project
from tests.connections import test_accepted_chat_custody_postgres as custody
from tests.connections.test_accepted_knowledge_read_postgres import connect
from tests.command_bus.test_accepted_knowledge_invoke import (
    CASES,
    payload_for,
    install_http,
    response_for,
)

db, engine = custody.db, custody.engine


@pytest.fixture(autouse=True)
def enable(monkeypatch):
    monkeypatch.setenv("CODEXIFY_ENABLE_KNOWLEDGE_OAUTH", "1")
    monkeypatch.setenv("CODEXIFY_ENABLE_KNOWLEDGE_CHAT_PILOT", "1")


def prepare(db, command, raw, owner="a", acknowledged=True):
    provider = chat_pilot.COMMANDS[command][0]
    connect(db, owner, provider)
    task, _, digest = custody.accepted(
        db,
        owner,
        provider,
        command_id=command,
        raw_arguments=raw,
        acknowledged=acknowledged,
        freeze=False,
    )
    payload = payload_for(task, command, chat_pilot.hydrate_arguments(command, raw))
    return task, payload, digest


def freeze(db, task, payload, digest):
    freeze_chat_tool_decision(
        db,
        request_id=task.request_id,
        backend_task_id=task.task_id,
        thread_id=task.thread_id,
        turn_id=task.turn_id,
        account_id=task.user_id,
        command_id=payload.command_id,
        args_hash=digest,
    )


async def project(db, state):
    return await project_accepted_knowledge_tools(
        db=db, task=state[0], grants=[state[1]]
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("command,raw", CASES)
async def test_synthetic_admission_execution_delivery_and_revocation(
    db, monkeypatch, command, raw
):
    state = prepare(db, command, raw)
    task, payload, digest = state
    app = FastAPI()  # Actual operations remain unmounted.
    calls = []

    async def handler(request):
        calls.append(request)
        return httpx.Response(200, json=response_for(request))

    install_http(monkeypatch, handler)
    original = oauth_store.credential
    monkeypatch.setattr(
        oauth_store, "credential", lambda *a: pytest.fail("catalog must not decrypt")
    )
    catalog = await project(db, state)
    assert [item["command_id"] for item in catalog] == [command]
    assert calls == [] and app.openapi()["paths"] == {}
    assert command not in build_command_index(app)[0]
    with pytest.raises(AcceptedKnowledgeReadUnavailable):
        await execute_accepted_knowledge_read(
            db=db, task=task, payload=payload, app=app
        )
    freeze(db, task, payload, digest)
    monkeypatch.setattr(oauth_store, "credential", original)
    response = await execute_accepted_knowledge_read(
        db=db, task=task, payload=payload, app=app
    )
    count = len(calls)
    assert response["status"] == "completed" and count > 0
    monkeypatch.setattr(
        oauth_store, "credential", lambda *a: pytest.fail("delivery must not decrypt")
    )
    delivered = await read_accepted_knowledge_result(
        db=db,
        task=task,
        payload=payload,
        run_id=response["run_id"],
        app=app,
    )
    assert delivered["inline_result"] == response["inline_result"]
    assert len(calls) == count
    oauth_store.disconnect(db, "a", chat_pilot.COMMANDS[command][0])
    assert await project(db, state) == []
    with pytest.raises(AcceptedKnowledgeReadUnavailable):
        await read_accepted_knowledge_result(
            db=db, task=task, payload=payload, run_id=response["run_id"], app=app
        )
    assert len(calls) == count


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "change", ["account", "thread", "project", "terminal", "cancel", "preview"]
)
async def test_catalog_rechecks_owner_and_lifecycle(db, monkeypatch, change):
    state = prepare(db, *CASES[0])
    assert await project(db, state)
    if change == "account":
        state[0].user_id = "b"
    elif change == "cancel":
        monkeypatch.setattr("guardian.queue.redis_queue.is_cancelled", lambda _: True)
    elif change == "preview":
        monkeypatch.setattr(
            "guardian.core.preview_access.is_private_preview", lambda: True
        )
        monkeypatch.setattr(
            "guardian.core.preview_access.role_for_preview_email", lambda _: None
        )
    else:
        with db._sa_session() as session:
            if change == "thread":
                session.get(ChatThread, 1).user_id = "b"
            elif change == "project":
                session.add(Project(id=10, name="B", user_id="b"))
                session.flush()
                session.get(ChatThread, 1).project_id = 10
            else:
                session.get(
                    ChatCompletionAttempt, state[0].request_id
                ).terminal_event_type = "task.failed"
    with pytest.raises(AcceptedKnowledgeReadUnavailable):
        await project(db, state)


@pytest.mark.asyncio
async def test_pending_ack_and_policy_denial_cannot_advertise(db, monkeypatch):
    state = prepare(db, *CASES[0], acknowledged=False)
    with pytest.raises(ChatAccountAcceptancePending):
        await project(db, state)
    mark_chat_completion_attempt_accepted(db, backend_task_id=state[0].task_id)
    assert await project(db, state)
    state[1].permission_profile.network_allowed = False
    assert await project(db, state) == []
    assert await project_accepted_knowledge_tools(db=db, task=state[0], grants=[]) == []
    monkeypatch.delenv("CODEXIFY_ENABLE_KNOWLEDGE_CHAT_PILOT")
    assert await project(db, state) == []


@pytest.mark.asyncio
async def test_cross_account_result_and_policy_change_are_denied(db, monkeypatch):
    a, b = prepare(db, *CASES[0]), prepare(db, *CASES[0], owner="b")
    assert await project(db, a) and await project(db, b)
    for state in (a, b):
        freeze(db, *state)
    install_http(
        monkeypatch, lambda request: httpx.Response(200, json=response_for(request))
    )
    app = FastAPI()
    result = await execute_accepted_knowledge_read(
        db=db, task=a[0], payload=a[1], app=app
    )
    for state in (b, a):
        if state is a:
            state[1].permission_profile.network_allowed = False
        with pytest.raises(AcceptedKnowledgeReadUnavailable):
            await read_accepted_knowledge_result(
                db=db, task=state[0], payload=state[1], run_id=result["run_id"], app=app
            )
    assert CommandBusStore(db).get_run(result["run_id"])["status"] == "completed"


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["disconnect", "flag", "owner"])
async def test_change_during_projection_discards_catalog(db, monkeypatch, change):
    state = prepare(db, *CASES[0])
    original = oauth_store.read_grant
    calls = 0

    def read(*args):
        nonlocal calls
        value = original(*args)
        calls += 1
        if calls == 1:
            if change == "disconnect":
                oauth_store.disconnect(db, "a", "github")
            elif change == "flag":
                monkeypatch.setenv("CODEXIFY_ENABLE_KNOWLEDGE_CHAT_PILOT", "0")
            else:
                with db._sa_session() as session:
                    session.get(ChatThread, 1).user_id = "b"
        return value

    monkeypatch.setattr(oauth_store, "read_grant", read)
    with pytest.raises(AcceptedKnowledgeReadUnavailable):
        await project(db, state)


@pytest.mark.asyncio
async def test_catalog_returns_detached_metadata_and_rejects_foreign_policy(db):
    state = prepare(db, *CASES[0])
    first = await project(db, state)
    props = first[0]["input_schema"]["properties"]
    assert props["repository"]["enum"] == ["example/selected"]
    props["query"]["maxLength"] = 100000
    props["repository"]["enum"].append("foreign/repository")
    second = await project(db, state)
    assert second[0]["input_schema"]["properties"]["query"]["maxLength"] == 500
    assert second[0]["input_schema"]["properties"]["repository"]["enum"] == [
        "example/selected"
    ]
    state[1].permission_profile.subject_id = "b"
    assert await project(db, state) == []


@pytest.mark.asyncio
async def test_unknown_or_duplicate_catalog_policy_templates_fail_closed(db):
    state = prepare(db, *CASES[0])
    with pytest.raises(AcceptedKnowledgeReadUnavailable):
        await project_accepted_knowledge_tools(
            db=db, task=state[0], grants=[state[1], state[1]]
        )
    state[1].command_id = "op::history_search"
    with pytest.raises(AcceptedKnowledgeReadUnavailable):
        await project(db, state)


@pytest.mark.asyncio
async def test_result_refuses_pending_or_unknown_run_without_new_provider_work(
    db, monkeypatch
):
    state = prepare(db, *CASES[0])
    freeze(db, *state)
    install_http(
        monkeypatch, lambda request: httpx.Response(200, json=response_for(request))
    )
    app = FastAPI()
    result = await execute_accepted_knowledge_read(
        db=db, task=state[0], payload=state[1], app=app
    )
    store = CommandBusStore(db)
    store.update_run(run_id=result["run_id"], status="running")
    monkeypatch.setattr(
        oauth_store, "credential", lambda *a: pytest.fail("delivery never executes")
    )
    for run_id in (result["run_id"], "missing-synthetic-run"):
        with pytest.raises(AcceptedKnowledgeReadUnavailable):
            await read_accepted_knowledge_result(
                db=db, task=state[0], payload=state[1], run_id=run_id, app=app
            )
