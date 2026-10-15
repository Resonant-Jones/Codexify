"""Synthetic, process-local provider request inspection proof."""

import json
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from guardian.core import chat_completion_service as service
from guardian.core.ai_router import _post_provider_request


@pytest.fixture(autouse=True)
def capture_store(monkeypatch):
    monkeypatch.setattr(service, "_PROVIDER_CAPTURE_REQUESTS", {})
    monkeypatch.setattr(service.threading, "Timer", MagicMock())


def enable(task_id="task-one", account_id="owner"):
    return service.enable_provider_request_capture(
        task_id=task_id,
        request_id="req-one",
        account_id=account_id,
        thread_id=1,
        project_id=10,
    )


def store(body=b'{"messages": []}', attempt_id="attempt-one", dispatch_index=1):
    return service.store_provider_request_capture(
        task_id="task-one",
        request_id="req-one",
        attempt_id=attempt_id,
        dispatch_index=dispatch_index,
        provider="local",
        logical_model="logical",
        body=body,
        byte_size=len(body),
    )


def test_capture_requires_explicit_consent_and_never_reconstructs():
    assert not store()
    assert (
        service.read_provider_request_captures("task-one")["availability"]
        == "CAPTURE_UNAVAILABLE"
    )
    assert enable()
    assert not enable(account_id="other")
    assert service.read_provider_request_captures("task-one")["captures"] == []


def test_exact_body_and_projection_share_bytes():
    body = b'{ "messages": [{"role":"system","content":"  exact\\n\\t"}, {"role":"user","content":"IV?"}], "model":"effective", "temperature":0.1 }'
    assert enable() and store(body)
    capture = service.read_provider_request_captures("task-one")["captures"][0]
    assert capture["raw_json"].encode() == body
    assert capture["request_json"] == json.loads(body)
    assert capture["request_json"]["messages"][0]["content"] == "  exact\n\t"
    assert capture["completeness"] == "COMPLETE"
    assert capture["parameter_fields"] == ["model", "temperature"]
    assert capture["model_visible_fields"] == ["messages"]


def test_expiry_discards_bytes_and_prevents_reuse(monkeypatch):
    clock = [100.0]
    monkeypatch.setattr(service.time, "monotonic", lambda: clock[0])
    assert enable() and store()
    clock[0] += service.PROVIDER_CAPTURE_TTL_SECONDS
    assert service.provider_capture_scope("task-one") is None
    assert service._PROVIDER_CAPTURE_REQUESTS == {}
    assert not store()


def test_timer_expires_without_readback():
    assert enable() and store()
    timer = service.threading.Timer.call_args
    callback = timer.args[1]
    callback(*timer.kwargs["args"])
    assert service._PROVIDER_CAPTURE_REQUESTS == {}


def test_overflow_is_unavailable_without_truncation(monkeypatch):
    monkeypatch.setattr(service, "PROVIDER_CAPTURE_MAX_BYTES", 4)
    assert enable() and store()
    capture = service.read_provider_request_captures("task-one")["captures"][0]
    assert capture["byte_size"] == len(b'{"messages": []}')
    assert capture["raw_json"] is None
    assert capture["request_json"] is None
    assert capture["completeness"] == "CAPTURE_UNAVAILABLE"
    assert capture["omission_reasons"] == ["capture_size_exceeded"]


def test_concurrent_attempts_and_transport_dispatches_do_not_collide():
    assert enable()

    def capture(index):
        return store(attempt_id=f"attempt-{index // 2}", dispatch_index=index % 2 + 1)

    with ThreadPoolExecutor(max_workers=4) as pool:
        assert all(pool.map(capture, range(8)))
    captures = service.read_provider_request_captures("task-one")["captures"]
    assert len(captures) == 8
    assert len({(item["attempt_id"], item["dispatch_index"]) for item in captures}) == 8
    assert not store(attempt_id="attempt-0")


def test_resource_budgets_and_wrong_correlation(monkeypatch):
    monkeypatch.setattr(service, "PROVIDER_CAPTURE_MAX_REQUESTS", 1)
    assert enable()
    assert not enable("other-task")
    monkeypatch.setattr(service, "PROVIDER_CAPTURE_MAX_TOTAL_BYTES", 1)
    assert store()
    capture = service.read_provider_request_captures("task-one")["captures"][0]
    assert capture["raw_json"] is None
    assert capture["omission_reasons"] == ["capture_memory_budget_exceeded"]
    assert not service.store_provider_request_capture(
        task_id="task-one",
        request_id="wrong",
        attempt_id="attempt-two",
        dispatch_index=1,
        provider="local",
        logical_model="m",
        body=b"{}",
        byte_size=2,
    )


def test_default_attempt_has_no_relay_calls(monkeypatch):
    get = MagicMock()
    monkeypatch.setattr("requests.get", get)
    task = SimpleNamespace(origin="api:chat.complete")
    assert (
        service._provider_request_capture_observer(task, provider="local", model="m")
        is None
    )
    get.assert_not_called()


def test_attempt_capture_failure_preserves_result_and_one_model_call(monkeypatch):
    task = SimpleNamespace(
        origin="api:chat.complete", request_id="req-one", task_id="task-one"
    )
    post = MagicMock(return_value="provider-response")
    monkeypatch.setattr("requests.post", post)
    monkeypatch.setattr(
        service,
        "_provider_request_capture_observer",
        lambda *a, **k: lambda body: 1 / 0,
    )
    calls = []

    def execution(**kwargs):
        calls.append(kwargs)
        return _post_provider_request(
            "https://synthetic.invalid", json={"model": "m", "messages": []}
        )

    monkeypatch.setattr(service, "_dispatch_completion_attempt", execution)
    result = service._execute_completion_attempt(
        task=task,
        messages_for_llm=[],
        provider="groq",
        model="m",
        bundle=None,
    )
    assert result == "provider-response"
    assert task.attempt_id.startswith("attempt_")
    assert len(calls) == post.call_count == 1
    assert service._PROVIDER_CAPTURE_REQUESTS == {}


def test_dispatch_ceiling_is_explicit_and_preserves_complete_records(monkeypatch):
    monkeypatch.setattr(service, "PROVIDER_CAPTURE_MAX_DISPATCHES", 1)
    assert enable() and store()
    assert not store(attempt_id="attempt-two")
    payload = service.read_provider_request_captures("task-one")
    assert len(payload["captures"]) == 1
    assert payload["dispatch_limit_exceeded"]
    assert payload["omission_reasons"] == ["capture_dispatch_limit_exceeded"]
    assert payload["captures"][0]["completeness"] == "COMPLETE"


def test_failed_expiry_timer_does_not_leave_consent(monkeypatch):
    monkeypatch.setattr(
        service.threading.Timer.return_value,
        "start",
        MagicMock(side_effect=RuntimeError),
    )
    assert not enable()
    assert service._PROVIDER_CAPTURE_REQUESTS == {}


@pytest.mark.parametrize("body", [b"not-json", b"[]", '{"model":"m"}'.encode("utf-16")])
def test_invalid_request_bytes_are_never_labeled_complete(body):
    assert enable() and store(body)
    capture = service.read_provider_request_captures("task-one")["captures"][0]
    assert capture["completeness"] == "CAPTURE_UNAVAILABLE"
    assert capture["raw_json"] is None
    assert capture["omission_reasons"] == ["invalid_request_json"]
