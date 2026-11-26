"""Ordinary chat native serialization at an isolated HTTP transport."""

import json
import socket
from datetime import datetime, timezone

import httpx
import pytest
from fastapi import HTTPException

from guardian.core import ai_router
from guardian.core.config import Settings
from guardian.core.llm_catalog import _cloud_models
from guardian.core.provider_registry import resolve_provider_capability
from guardian.tasks.chat_deadline import build_accepted_chat_task_deadline

ROUTE = ("deepseek", "deepseek-flash", "https://api.deepseek.com")
MESSAGES = [{"role": "user", "content": "Synthetic fixture."}]


def dispatch(route, effort, mode, settings, deadline):
    return ai_router.chat_with_ai(
        MESSAGES,
        provider=route[0],
        model=route[1],
        thinking_effort=effort,
        reasoning_mode=mode,
        settings=settings,
        accepted_deadline=deadline,
    )


@pytest.fixture
def capture(monkeypatch):
    def no_network(*args, **kwargs):
        raise AssertionError("network access outside the fixture")

    monkeypatch.setattr(socket.socket, "connect", no_network)
    monkeypatch.setattr(socket, "getaddrinfo", no_network)
    monkeypatch.setenv("CODEXIFY_SUPPORTED_PROFILE", "v1-whooshd-deepseek-web")
    settings = Settings(
        _env_file=None,
        LLM_PROVIDER="local",
        ALLOW_CLOUD_PROVIDERS=True,
        CODEXIFY_LOCAL_ONLY_MODE=False,
        CODEXIFY_EGRESS_ALLOWLIST="deepseek,deepgram",
        LOCAL_BASE_URL="http://host.docker.internal:8000/v1",
        LOCAL_PROVIDER_VENDOR="whooshd",
        LOCAL_CHAT_MODEL="local-chat",
        LOCAL_API_KEY="local",
        DEEPSEEK_BASE_URL=ROUTE[2],
        DEEPSEEK_CHAT_MODEL=ROUTE[1],
        DEEPSEEK_API_KEY="fixture-only",
    )
    seen = []

    def capture_post(request):
        assert request.method == "POST"
        assert str(request.url) == ROUTE[2] + "/v1/chat/completions"
        seen.append(json.loads(request.content))
        if any(
            tool["function"]["description"] == "echo"
            for tool in seen[-1].get("tools", [])
        ) and not any(m["role"] == "tool" for m in seen[-1]["messages"]):
            message = {
                "role": "assistant",
                "reasoning_content": "fixture trace",
                "content": None,
                "tool_calls": [
                    {
                        "id": "fixture-call",
                        "type": "function",
                        "function": {
                            "name": seen[-1]["tools"][0]["function"]["name"],
                            "arguments": '{"body": {"value":"alpha"}}',
                        },
                    }
                ],
            }
            return httpx.Response(200, json={"choices": [{"message": message}]})
        return httpx.Response(
            200, json={"choices": [{"message": {"content": "fixture reply"}}]}
        )

    def inventory(url, **kwargs):
        assert url.startswith(ROUTE[2] + "/") and url.endswith("/models")
        return httpx.Response(200, json={"data": [{"id": ROUTE[1]}]})

    client = httpx.AsyncClient
    monkeypatch.setattr(ai_router.requests, "get", inventory)
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda: client(transport=httpx.MockTransport(capture_post), trust_env=False),
    )
    return settings, build_accepted_chat_task_deadline(datetime.now(timezone.utc)), seen


def test_catalog_and_existing_local_only_gate(capture, test_client, monkeypatch):
    from guardian.core import llm_catalog

    settings, deadline, seen = capture
    capability = resolve_provider_capability("deepseek", settings)
    monkeypatch.setattr(llm_catalog, "_PROVIDER_ORDER", (ROUTE[0],))
    monkeypatch.setattr(llm_catalog, "get_settings", lambda: settings)
    response = test_client.get("/api/llm/catalog")
    assert response.status_code == 200
    (provider,) = response.json()["providers"]
    assert provider["id"] == ROUTE[0]
    assert provider["models"][0]["thinking_effort"] == {
        "requires_mode": "think",
        "levels": ["low", "high", "max"],
    }
    assert capability["enabled"]
    assert capability["model_index"]["state"] == "available"
    assert ROUTE[1] in {
        row["id"] for row in capability["models"] if row["supports_chat"]
    }
    settings.CODEXIFY_LOCAL_ONLY_MODE = True
    settings.ALLOW_CLOUD_PROVIDERS = False
    settings.CODEXIFY_EGRESS_ALLOWLIST = ""
    with pytest.raises(HTTPException):
        dispatch(ROUTE[:2], "max", "think", settings, deadline)
    assert seen == []


@pytest.mark.parametrize("effort", [None, "default", "max"])
def test_canonical_policy_veto_prevents_dispatch(capture, monkeypatch, effort):
    settings, deadline, seen = capture
    calls = []

    def reject(**kwargs):
        calls.append(kwargs)
        return False, "canonical selection veto"

    monkeypatch.setattr(ai_router, "validate_provider_model_selection", reject)
    with pytest.raises(HTTPException, match="canonical selection veto"):
        dispatch(ROUTE[:2], effort, "think", settings, deadline)
    assert len(calls) == 1
    assert seen == []


def test_effort_stays_stricter_during_degraded_discovery(capture, monkeypatch):
    settings, deadline, seen = capture
    lookups = []

    def offline(url, **kwargs):
        lookups.append(url)
        raise ai_router.requests.ConnectionError("fixture model inventory offline")

    monkeypatch.setattr(ai_router.requests, "get", offline)
    dispatch(ROUTE[:2], None, "think", settings, deadline)
    legacy_lookup_count = len(lookups)
    assert legacy_lookup_count > 0 and len(seen) == 1
    with pytest.raises(HTTPException, match="available discovered chat model"):
        dispatch(ROUTE[:2], "high", "think", settings, deadline)
    assert len(lookups) == 2 * legacy_lookup_count
    assert len(seen) == 1


@pytest.mark.parametrize("effort", ["default", "low", "high", "max"])
def test_native_effort_on_prepared_request_and_same_route_repeat(capture, effort):
    settings, deadline, seen = capture
    for _ in range(2):
        assert (
            dispatch(ROUTE[:2], effort, "think", settings, deadline).content
            == "fixture reply"
        )
    expected = {
        "model": ROUTE[1],
        "messages": MESSAGES,
        "thinking": {"type": "enabled"},
    }
    if effort != "default":
        expected["reasoning_effort"] = effort
    assert seen == [expected, expected]


@pytest.mark.parametrize(
    ("route", "effort", "mode", "base"),
    [
        (("local", "local-chat"), "max", "think", ROUTE[2]),
        (("deepseek", "deepseek-v4-pro"), "max", "think", ROUTE[2]),
        (ROUTE[:2], "max", "think", "https://proxy.invalid"),
        (ROUTE[:2], "medium", "think", ROUTE[2]),
        (ROUTE[:2], "max", "no_think", ROUTE[2]),
    ],
)
def test_incompatible_attempt_never_posts(capture, route, effort, mode, base):
    settings, deadline, seen = capture
    settings.DEEPSEEK_BASE_URL = base
    with pytest.raises(HTTPException):
        dispatch(route, effort, mode, settings, deadline)
    assert seen == []


@pytest.mark.parametrize(("mode", "expected"), [(None, None), ("think", "high")])
def test_shipped_serializer_control(capture, mode, expected):
    settings, deadline, seen = capture
    ai_router.chat_with_ai(
        MESSAGES,
        provider=ROUTE[0],
        model=ROUTE[1],
        reasoning_mode=mode,
        settings=settings,
        accepted_deadline=deadline,
    )
    assert len(seen) == 1
    if expected is None:
        assert "reasoning_effort" not in seen[0]
        assert seen[0]["thinking"] == {"type": "disabled"}
    else:
        assert seen[0]["reasoning_effort"] == expected


@pytest.mark.parametrize(
    "saved_mode,saved_model,receipt_id,expected",
    [
        ("think", ROUTE[1], 42, 200),
        ("think", ROUTE[1], 41, 409),
        ("think", ROUTE[1], None, 409),
        ("fast", ROUTE[1], 42, 409),
        ("think", "another-model", 42, 409),
    ],
)
def test_admission_uses_saved_route(
    test_client,
    mock_db,
    monkeypatch,
    capture,
    saved_mode,
    saved_model,
    receipt_id,
    expected,
):
    from guardian.routes import chat
    from guardian.tasks.types import ChatCompletionTask
    from tests.routes.test_chat_complete_thread_config_precedence import (
        _capture_accepted_completion,
        _override_request_scope,
    )
    from tests.utils import get_test_user_id

    settings, _, seen = capture
    captured = {}
    mock_db.get_chat_thread.return_value.update(
        thread_config={
            "providerId": ROUTE[0],
            "modelId": saved_model,
            "inferenceMode": saved_mode,
        }
    )
    mock_db.list_messages.return_value = [
        dict(MESSAGES[0], id=41),
        dict(MESSAGES[0], id=42),
    ]
    mock_db.resolve_authored_chat_turn.side_effect = (
        lambda thread_id, *, user_id, message_id: (
            dict(MESSAGES[0], id=42) if message_id == 42 else None
        )
    )
    monkeypatch.setattr(chat, "llm_settings", settings)
    monkeypatch.setattr(
        chat, "enqueue_chat_completion", _capture_accepted_completion(captured)
    )
    monkeypatch.setattr(chat, "_get_task_completed_payload", lambda *a, **kw: None)
    _override_request_scope(test_client, get_test_user_id())
    try:
        response = test_client.post(
            "/chat/1/complete",
            json={
                "provider": ROUTE[0],
                "model": ROUTE[1],
                "reasoning_mode": "think",
                "thinking_effort": "max",
                "expected_message_id": receipt_id,
            },
        )
        if expected == 409:
            assert response.status_code == 409 and captured == {}
            retry = test_client.post(
                "/chat/1/complete", json={"provider": ROUTE[0], "model": saved_model}
            )
            assert retry.status_code == 200
            assert "thinking_effort" not in captured["task"].to_dict()
    finally:
        test_client.app.dependency_overrides.pop(chat.get_request_user_scope, None)
    assert response.status_code == expected, response.text
    if expected == 200:
        task = ChatCompletionTask.from_dict(captured["task"].to_dict())
        assert task.latest_turn_message_id == 42
        assert (task.provider, task.model, task.thinking_effort) == (*ROUTE[:2], "max")
    assert seen == []


@pytest.mark.parametrize("change_route", [False, True])
def test_dispatch_rechecks_tool_continuation(monkeypatch, capture, change_route):
    from guardian.core import chat_completion_service as service
    from tests.core.test_chat_completion_service_tool_loop import (
        _build_task,
        _seed_service,
    )

    settings, _, seen = capture
    _seed_service(monkeypatch, provider=ROUTE[0], model=ROUTE[1])
    monkeypatch.setattr(service, "get_settings", lambda: settings)
    monkeypatch.setattr(service, "chat_with_ai", ai_router.chat_with_ai)
    task = _build_task()
    task.provider, task.model = ROUTE[:2]
    task.reasoning_mode = "think"
    task.thinking_effort = "max"
    task.tools = [{"command_id": "op::echo", "description": "echo"}]

    def invoke(**kwargs):
        if change_route:
            settings.DEEPSEEK_BASE_URL = "https://proxy.invalid"
        return {
            "run_id": "fixture",
            "status": "completed",
            "invoke_version": "1.0",
            "manifest_version": "1.0",
            "events_url": "/events/run",
            "inline_result": {"value": "ok"},
        }

    monkeypatch.setattr(service, "execute_invoke", invoke)
    if change_route:
        with pytest.raises(HTTPException, match="Thinking effort"):
            service.run_chat_completion_task(task, persist_assistant_message=False)
        assert len(seen) == 1
    else:
        result = service.run_chat_completion_task(task, persist_assistant_message=False)
        assert result["assistant_text"] == "fixture reply"
        assert [p["reasoning_effort"] for p in seen] == ["max", "max"]
        assert seen[1]["messages"][-1]["tool_call_id"] == "fixture-call"


@pytest.mark.parametrize("route_changed", [False, True])
def test_rehydrated_worker_attempt(monkeypatch, capture, route_changed):
    from guardian.tasks.types import ChatCompletionTask
    from guardian.workers import chat_worker
    from tests.workers.test_chat_worker_streaming_chunks import (
        _build_task,
        _prepare_worker_harness,
    )

    settings, deadline, seen = capture
    provider, model = ("local", "test-model") if route_changed else ROUTE[:2]
    events = _prepare_worker_harness(monkeypatch, provider=provider, model=model)
    service = chat_worker._chat_completion_service
    monkeypatch.setattr(
        service, "get_chat_tool_checkpoint", lambda *args, **kwargs: None
    )
    for module in (service, chat_worker):
        monkeypatch.setattr(module, "get_settings", lambda: settings)
        monkeypatch.setattr(module, "chat_with_ai", ai_router.chat_with_ai)
    task = _build_task(task_id="effort-retry", provider=ROUTE[0], model=ROUTE[1])
    task.reasoning_mode = "think"
    task.thinking_effort = "low"
    for key, value in deadline.to_dict().items():
        setattr(task, key, value)
    chat_worker._run_chat_task(ChatCompletionTask.from_dict(task.to_dict()))
    if route_changed:
        assert any(event == "task.failed" for event, _ in events)
        assert seen == []
    else:
        assert any(event == "task.completed" for event, _ in events), [
            payload for event, payload in events if event == "task.failed"
        ]
        assert [p["reasoning_effort"] for p in seen] == ["low"]


@pytest.mark.parametrize(
    "condition", ["preview", "no-key", "wrong-profile", "missing-model"]
)
def test_catalog_and_dispatch_agree_on_ineligible_lane(capture, monkeypatch, condition):
    settings, deadline, seen = capture
    if condition == "preview":
        monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "private_preview")
        settings.CODEXIFY_EGRESS_ALLOWLIST = "deepseek,deepgram,openai"
    elif condition == "no-key":
        settings.DEEPSEEK_API_KEY = ""
    elif condition == "wrong-profile":
        monkeypatch.delenv("CODEXIFY_SUPPORTED_PROFILE")
    else:
        monkeypatch.setattr(
            ai_router.requests,
            "get",
            lambda *_a, **_k: httpx.Response(200, json={"data": [{"id": "other"}]}),
        )
    assert all(
        "thinking_effort" not in row for row in _cloud_models("deepseek", settings)
    )
    with pytest.raises(HTTPException):
        dispatch(ROUTE[:2], "low", "think", settings, deadline)
    assert seen == []


def test_incompatible_worker_rescue_fails_before_local_request(monkeypatch, capture):
    from guardian.workers import chat_worker
    from tests.workers.test_chat_worker_streaming_chunks import (
        _build_task,
        _prepare_worker_harness,
    )

    settings, _, seen = capture
    events = _prepare_worker_harness(monkeypatch, provider=ROUTE[0], model=ROUTE[1])
    task = _build_task(task_id="effort-rescue", provider=ROUTE[0], model=ROUTE[1])
    # Exercise a worker handed a fallback candidate even if normal admission pinned it.
    task.selection_source = "default"
    task.provider_pinned = False
    task.reasoning_mode = "think"
    task.thinking_effort = "max"
    calls = []

    def unavailable(*args, **kwargs):
        calls.append((kwargs["provider"], kwargs["thinking_effort"]))
        raise HTTPException(
            status_code=502, detail={"failure_kind": "provider_unavailable"}
        )

    for module in (chat_worker, chat_worker._chat_completion_service):
        monkeypatch.setattr(module, "get_settings", lambda: settings)
        monkeypatch.setattr(module, "chat_with_ai", unavailable)
    monkeypatch.setattr(
        chat_worker,
        "_fallback_provider_candidates",
        lambda **kwargs: [("local", "other")],
    )
    chat_worker._run_chat_task(task)
    assert calls == [("deepseek", "max")]
    failed = next(payload for event, payload in events if event == "task.failed")
    assert "Thinking effort" in str(failed)
    assert seen == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("saved_mode", "error", "message"),
    [
        ("fast", HTTPException, "Thinking effort"),
        ("think", ValueError, "thread_target_turn_missing"),
    ],
)
async def test_queued_effort_requires_saved_mode_and_bound_turn(
    monkeypatch, capture, saved_mode, error, message
):
    from guardian.core import chat_completion_service as service
    from guardian.tasks.types import ChatCompletionTask
    from tests.core.test_chat_completion_service_thread_config import (
        _seed_completion_service,
    )

    settings, _, seen = capture
    context = _seed_completion_service(
        monkeypatch,
        thread_row={
            "id": 1,
            "user_id": "fixture",
            "thread_config": {
                "providerId": ROUTE[0],
                "modelId": ROUTE[1],
                "inferenceMode": saved_mode,
            },
        },
    )
    monkeypatch.setattr(service, "get_settings", lambda: settings)
    task = ChatCompletionTask(
        user_id="fixture",
        thread_id=1,
        provider=ROUTE[0],
        model=ROUTE[1],
        reasoning_mode="think",
        thinking_effort="max",
    )
    with pytest.raises(error, match=message):
        await service.build_messages_for_llm(
            ChatCompletionTask.from_dict(task.to_dict())
        )
    assert "prompt_bundle" not in context
    assert seen == []
