"""Private Command Bus and native async adapter; no real provider requests."""

import asyncio
from dataclasses import replace
import json
from types import SimpleNamespace

from fastapi import HTTPException
import httpx
import pytest

from guardian.command_bus import invoke, accepted_knowledge_transport as transport
from guardian.command_bus.accepted_knowledge_read import (
    prepare_accepted_knowledge_read,
)
from guardian.command_bus.contracts import (
    ActorSpec,
    CommandSpec,
    InvokeRequest,
    InvokePermissionProfile,
    InvokeExternalPolicyRule,
)
from guardian.command_bus.store import CommandBusStore, IdempotencyConflictError
from guardian.connections import chat_pilot, oauth_store
from guardian.tasks.chat_deadline import AcceptedChatTaskDeadlineExceeded
from tests.command_bus.test_accepted_knowledge_read import fixture as authority_fixture

ROOT_ID = "11111111-1111-1111-1111-111111111111"
CHILD_ID = "22222222-2222-2222-2222-222222222222"
CASES = [
    (
        "op::github_content_search",
        {"repository": "example/selected", "query": "synthetic"},
    ),
    ("op::github_content_read", {"repository": "example/selected", "number": 1}),
    ("op::notion_content_search", {"query": "synthetic"}),
    ("op::notion_content_read", {"object_id": ROOT_ID}),
]


def payload_for(task, command, args):
    provider = chat_pilot.COMMANDS[command][0]
    return InvokeRequest(
        invoke_version="1.0",
        command_id=command,
        actor=ActorSpec(
            kind="agent", id="guardian-accepted-knowledge", delegated_by=task.user_id
        ),
        arguments=args,
        permission_profile=InvokePermissionProfile(
            profile_id="synthetic-grant",
            actor_id="guardian-accepted-knowledge",
            subject_id=task.user_id,
            task_id=task.task_id,
            thread_id=str(task.thread_id),
            request_task_id=task.task_id,
            request_thread_id=str(task.thread_id),
            request_command_class="connector",
            allowed_command_ids=(command,),
            network_allowed=True,
            connector_allowed=True,
            uses_network=True,
            uses_connector=True,
        ),
        external_transport="https",
        external_target_url=transport.ORIGINS[provider],
        external_connector_name=provider,
        external_command_namespace=provider,
        external_command_name=command.split("_", 1)[1],
        external_policy_rules=(
            InvokeExternalPolicyRule(
                effect="allow",
                connector_name=provider,
                transport="https",
                url_scheme="https",
                url_host_pattern=f"api.{provider}.com",
            ),
        ),
    )


def command_for(command):
    return CommandSpec(
        command_id=command,
        method="GET",
        path_template=chat_pilot.COMMANDS[command][1],
        risk="read_only",
        effect="read",
        idempotency="safe",
        approval_mode="none",
    )


def setup(monkeypatch, command, raw):
    task, args, grant, _ = authority_fixture(monkeypatch, command, raw)
    state = {"valid": True}
    monkeypatch.setattr(
        oauth_store, "read_grant", lambda *a: grant if state["valid"] else None
    )
    monkeypatch.setattr(
        oauth_store,
        "credential",
        lambda *a: oauth_store.CredentialSnapshot(
            "a",
            grant.provider,
            grant.generation,
            "synthetic-private-token",
            None,
            None,
            {},
            list(grant.repositories),
        ),
    )
    fence = prepare_accepted_knowledge_read(
        object(), task, command_id=command, arguments=args
    )
    spec = command_for(command)
    monkeypatch.setattr(
        invoke,
        "build_command_index",
        lambda app: ({command: spec}, SimpleNamespace(manifest_version="1.0")),
    )
    monkeypatch.setattr(
        invoke,
        "execute_loopback_request",
        lambda **k: pytest.fail("private path must not impersonate HTTP auth"),
    )
    monkeypatch.delenv("GUARDIAN_COMMAND_BUS_LOOPBACK_BASE", raising=False)
    monkeypatch.delenv("GUARDIAN_API_BASE", raising=False)
    return fence, payload_for(task, command, args), spec, state


def response_for(request):
    path = request.url.path
    if path == "/search/issues":
        return {"items": [], "total_count": 0}
    if "/repos/" in path:
        return {
            "number": 1,
            "url": "https://api.github.com/repos/example/selected/issues/1",
            "body": "bounded evidence",
        }
    if path == "/v1/search":
        return {"results": []}
    if path.startswith("/v1/pages/"):
        return {"object": "page", "id": ROOT_ID, "properties": {}}
    return {
        "results": [
            {
                "id": CHILD_ID,
                "type": "paragraph",
                "paragraph": {"rich_text": [{"plain_text": "bounded evidence"}]},
            }
        ]
    }


def install_http(monkeypatch, handler):
    original = httpx.AsyncClient
    clients = []

    def factory(**kwargs):
        assert kwargs["trust_env"] is False and kwargs["follow_redirects"] is False
        client = original(**kwargs, transport=httpx.MockTransport(handler))
        clients.append(client)
        return client

    monkeypatch.setattr(transport.httpx, "AsyncClient", factory)
    return clients


async def execute(fence, payload, store):
    return await invoke.execute_invoke(
        payload=payload,
        auth_subject="a",
        inbound_headers={"X-API-Key": "must-not-forward"},
        store=store,
        app=object(),
        execution_lane="tools",
        _accepted_knowledge=fence,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("command,raw", CASES)
async def test_four_commands_audited_and_replayed_without_duplicate_http(
    monkeypatch, command, raw
):
    fence, payload, spec, state = setup(monkeypatch, command, raw)
    calls = []

    async def handler(request):
        calls.append(request)
        assert request.headers["authorization"] == "Bearer synthetic-private-token"
        assert "x-api-key" not in request.headers
        return httpx.Response(200, json=response_for(request))

    clients = install_http(monkeypatch, handler)
    store = CommandBusStore()
    first = await execute(fence, payload, store)
    assert first["status"] == "completed", first
    count = len(calls)
    second = await execute(fence, payload, store)
    assert second["run_id"] == first["run_id"] and len(calls) == count
    events = store.list_events_after(run_id=first["run_id"], after_seq=0)
    assert [e["event_type"] for e in events] == [
        "run.created",
        "run.started",
        "run.completed",
    ]
    assert all(
        e["payload_json"]["provenance_json"]["accepted_knowledge"]["account_id"] == "a"
        for e in events
    )
    assert "synthetic-private-token" not in json.dumps(events) + json.dumps(
        store.get_run(first["run_id"])
    )
    assert all(c.is_closed for c in clients)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "denial",
    [
        "network",
        "connector",
        "missing_profile",
        "external",
        "target",
        "manifest",
        "tool_policy",
    ],
)
async def test_policy_denials_prevent_provider_io_and_persist_block(
    monkeypatch, denial
):
    fence, payload, spec, state = setup(monkeypatch, *CASES[0])
    install_http(
        monkeypatch, lambda request: pytest.fail("denied request must not execute")
    )
    if denial in {"network", "connector"}:
        setattr(payload.permission_profile, denial + "_allowed", False)
    elif denial == "missing_profile":
        payload.permission_profile = None
    elif denial == "external":
        payload.external_policy_rules = ()
    elif denial == "target":
        payload.external_target_url = "https://unapproved.invalid"
    elif denial == "manifest":
        spec.path_template = "/not-the-read-route"
    else:
        from guardian.tools.policy import PolicyDecision

        monkeypatch.setattr(
            invoke,
            "evaluate_tool_policy",
            lambda *a, **k: PolicyDecision(
                decision="deny", reason_codes=["synthetic_deny"]
            ),
        )
    store = CommandBusStore()
    result = await execute(fence, payload, store)
    assert result["status"] == "blocked"
    assert store.get_run(result["run_id"])["status"] == "blocked"


@pytest.mark.asyncio
async def test_replay_rechecks_policy_and_does_not_rewrite_original_completion(
    monkeypatch,
):
    fence, payload, _, _ = setup(monkeypatch, *CASES[0])
    install_http(
        monkeypatch, lambda request: httpx.Response(200, json=response_for(request))
    )
    store = CommandBusStore()
    first = await execute(fence, payload, store)
    payload.permission_profile.network_allowed = False
    with pytest.raises(HTTPException) as error:
        await execute(fence, payload, store)
    assert error.value.status_code == 403
    assert store.get_run(first["run_id"])["status"] == "completed"
    last = store.list_events_after(run_id=first["run_id"], after_seq=0)[-1]
    assert (
        last["event_type"] == "run.blocked"
        and last["payload_json"]["phase"] == "replay"
    )


@pytest.mark.asyncio
async def test_create_run_conflict_revalidates_revocation_before_replay(monkeypatch):
    fence, payload, _, state = setup(monkeypatch, *CASES[0])
    install_http(
        monkeypatch, lambda request: httpx.Response(200, json=response_for(request))
    )
    store = CommandBusStore()
    first = await execute(fence, payload, store)
    old = store.get_run(first["run_id"])
    monkeypatch.setattr(store, "get_run_by_idempotency_key", lambda *a: None)

    def conflict(**kwargs):
        state["valid"] = False
        raise IdempotencyConflictError(old)

    monkeypatch.setattr(store, "create_run", conflict)
    with pytest.raises(HTTPException) as error:
        await execute(fence, payload, store)
    assert error.value.status_code == 403
    assert (
        store.list_events_after(run_id=first["run_id"], after_seq=0)[-1][
            "payload_json"
        ]["phase"]
        == "replay"
    )


class WaitingBody(httpx.AsyncByteStream):
    def __init__(self):
        self.started, self.closed, self.cancelled = asyncio.Event(), False, False

    async def __aiter__(self):
        self.started.set()
        try:
            await asyncio.Event().wait()
            yield b"{}"
        except asyncio.CancelledError:
            self.cancelled = True
            raise

    async def aclose(self):
        self.closed = True


@pytest.mark.asyncio
@pytest.mark.parametrize("reason", ["revoked", "parent_cancel", "deadline"])
@pytest.mark.parametrize("case", [CASES[0], CASES[3]])
async def test_inflight_native_async_read_cancels_and_persists_no_result(
    monkeypatch, reason, case
):
    fence, payload, _, state = setup(monkeypatch, *case)
    body = WaitingBody()
    clients = install_http(
        monkeypatch, lambda request: httpx.Response(200, stream=body)
    )
    if reason == "deadline":
        fence = replace(fence, _monotonic_deadline=transport.time.monotonic() + 0.75)
    store = CommandBusStore()
    pending = asyncio.create_task(execute(fence, payload, store))
    await asyncio.wait_for(body.started.wait(), 1)
    if reason == "parent_cancel":
        pending.cancel()
        with pytest.raises(asyncio.CancelledError):
            await pending
    elif reason == "deadline":
        with pytest.raises(AcceptedChatTaskDeadlineExceeded) as failure:
            await asyncio.wait_for(pending, 2)
        assert failure.value.detail["completion_truth"]["attempted"] is True
    else:
        if reason == "revoked":
            state["valid"] = False
        result = await asyncio.wait_for(pending, 2)
        assert result["status"] == "failed"
    assert body.cancelled and body.closed and all(c.is_closed for c in clients)
    run = list(store._mem_runs.values())[0]
    assert run["status"] == "failed" and run["result_json"] is None
    if reason == "deadline":
        assert run["error_text"] == failure.value.detail["failure_code"]
    assert (
        store.list_events_after(run_id=run["run_id"], after_seq=0)[-1]["event_type"]
        == "run.failed"
    )


@pytest.mark.asyncio
async def test_notion_revocation_between_requests_stops_traversal(monkeypatch):
    fence, payload, _, state = setup(monkeypatch, *CASES[3])
    calls = []

    async def handler(request):
        calls.append(request)
        state["valid"] = False
        return httpx.Response(200, json=response_for(request))

    install_http(monkeypatch, handler)
    result = await execute(fence, payload, CommandBusStore())
    assert result["status"] == "failed" and len(calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["redirect", "oversize", "malformed"])
async def test_transport_rejects_redirect_or_unbounded_invalid_response(
    monkeypatch, failure
):
    fence, payload, _, _ = setup(monkeypatch, *CASES[0])
    response = {
        "redirect": httpx.Response(
            302, headers={"location": "https://unapproved.invalid"}
        ),
        "oversize": httpx.Response(
            200, content=b"x" * (transport.MAX_RESPONSE_BYTES + 1)
        ),
        "malformed": httpx.Response(200, content=b"synthetic-private-token not json"),
    }[failure]
    install_http(monkeypatch, lambda request: response)
    store = CommandBusStore()
    result = await execute(fence, payload, store)
    assert result["status"] == "failed"
    assert "synthetic-private-token" not in json.dumps(
        store.list_events_after(run_id=result["run_id"], after_seq=0)
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("reason", ["deadline", "parent_cancel", "revoked"])
@pytest.mark.parametrize("case", [CASES[0], CASES[3]])
async def test_native_socket_is_closed_before_cancelled_read_finishes(
    monkeypatch, reason, case
):
    # Ephemeral loopback synthetic HTTP server only; no provider or shared port.
    fence, payload, _, state = setup(monkeypatch, *case)
    provider = chat_pilot.COMMANDS[case[0]][0]
    started, closed = asyncio.Event(), asyncio.Event()
    handlers = []

    async def server_read(reader, writer):
        handlers.append(asyncio.current_task())
        try:
            await reader.readuntil(b"\r\n\r\n")
            writer.write(
                b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 4096\r\n\r\n"
            )
            await writer.drain()
            started.set()
            assert await reader.read() == b""
            closed.set()
        finally:
            writer.close()
            await writer.wait_closed()

    server = await asyncio.start_server(server_read, "127.0.0.1", 0)
    origin = f"http://127.0.0.1:{server.sockets[0].getsockname()[1]}"
    monkeypatch.setitem(transport.ORIGINS, provider, origin)
    payload.external_target_url = origin
    payload.external_policy_rules = (
        InvokeExternalPolicyRule(
            effect="allow",
            connector_name=provider,
            transport="https",
            url_scheme="http",
            url_host_pattern="127.0.0.1",
        ),
    )
    if reason == "deadline":
        fence = replace(fence, _monotonic_deadline=transport.time.monotonic() + 1)
    store = CommandBusStore()
    pending = asyncio.create_task(execute(fence, payload, store))
    try:
        await asyncio.wait_for(started.wait(), 2)
        if reason == "parent_cancel":
            pending.cancel()
            with pytest.raises(asyncio.CancelledError):
                await pending
        elif reason == "deadline":
            with pytest.raises(AcceptedChatTaskDeadlineExceeded):
                await asyncio.wait_for(pending, 3)
        else:
            if reason == "revoked":
                state["valid"] = False
            assert (await asyncio.wait_for(pending, 3))["status"] == "failed"
        await asyncio.wait_for(closed.wait(), 2)
        assert list(store._mem_runs.values())[0]["result_json"] is None
    finally:
        if not pending.done():
            pending.cancel()
        await asyncio.gather(pending, return_exceptions=True)
        server.close()
        await server.wait_closed()
        for handler in handlers:
            if not handler.done():
                handler.cancel()
        await asyncio.gather(*handlers, return_exceptions=True)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "behavior", ["budget", "cursor_cycle", "unsafe_child", "wrong_page"]
)
async def test_notion_multi_request_bounds_and_identity(monkeypatch, behavior):
    fence, payload, _, _ = setup(monkeypatch, *CASES[3])
    calls = []

    async def handler(request):
        calls.append(request)
        if "/pages/" in request.url.path:
            data = {
                "object": "page",
                "id": CHILD_ID if behavior == "wrong_page" else ROOT_ID,
            }
        elif behavior == "unsafe_child":
            data = {"results": [{"has_children": True, "id": "../../unapproved"}]}
        else:
            data = {
                "results": [],
                "has_more": True,
                "next_cursor": (
                    "same" if behavior == "cursor_cycle" else str(len(calls))
                ),
            }
        return httpx.Response(200, json=data)

    install_http(monkeypatch, handler)
    result = await execute(fence, payload, CommandBusStore())
    if behavior == "budget":
        assert result["status"] == "completed"
        assert result["inline_result"]["body"]["content_truncated"] is True
        assert len(calls) == 21
    else:
        assert result["status"] == "failed" and len(calls) <= 3


def test_private_context_is_not_a_public_invoke_field():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        InvokeRequest.model_validate(
            {
                "invoke_version": "1.0",
                "command_id": CASES[0][0],
                "actor": {"kind": "human", "id": "a"},
                "_accepted_knowledge": {"account_id": "a"},
            }
        )


@pytest.mark.asyncio
async def test_provider_identity_mismatch_does_not_persist_evidence(monkeypatch):
    fence, payload, _, _ = setup(monkeypatch, *CASES[1])
    install_http(
        monkeypatch,
        lambda request: httpx.Response(
            200,
            json={
                "number": 1,
                "url": "https://api.github.com/repos/other/account/issues/1",
                "body": "wrong-account-evidence",
            },
        ),
    )
    store = CommandBusStore()
    result = await execute(fence, payload, store)
    assert (
        result["status"] == "failed"
        and store.get_run(result["run_id"])["result_json"] is None
    )
