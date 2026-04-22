from __future__ import annotations

from types import SimpleNamespace

import pytest

from guardian.core import (
    candidate_trace_store,
    chat_completion_service,
    dependencies,
)
from guardian.tasks.types import ChatCompletionTask


@pytest.fixture(autouse=True)
def _stable_single_user_auth(monkeypatch):
    monkeypatch.setattr(
        dependencies,
        "_multi_user_mode_enabled",
        lambda: False,
    )
    monkeypatch.setattr(
        dependencies,
        "get_single_user_id",
        lambda: "test_user",
    )


@pytest.fixture(autouse=True)
def _clear_candidate_trace_store():
    candidate_trace_store._candidate_traces.clear()
    yield
    candidate_trace_store._candidate_traces.clear()


def _stub_completion_pipeline(monkeypatch, assistant_text: str):
    async def _build_messages(_task):
        return (
            [{"role": "user", "content": "Hello"}],
            "groq",
            "mock-model",
            {},
            {},
        )

    monkeypatch.setattr(
        chat_completion_service,
        "build_messages_for_llm",
        _build_messages,
    )
    monkeypatch.setattr(
        chat_completion_service,
        "_apply_image_attachment_routing",
        lambda messages, **_kwargs: (messages, {"image_routing_path": None}),
    )
    monkeypatch.setattr(
        chat_completion_service,
        "build_sanitized_payload_summary",
        lambda *args, **kwargs: {"message_count": 1},
    )
    monkeypatch.setattr(
        chat_completion_service,
        "_build_retrieval_provenance",
        lambda **_kwargs: {
            "requested_source_mode": "project",
            "normalized_source_mode": "project",
            "source_hit_counts": {},
            "retrieval_status": "not_requested",
        },
    )
    monkeypatch.setattr(
        chat_completion_service,
        "chat_with_ai",
        lambda *args, **kwargs: assistant_text,
    )
    monkeypatch.setattr(
        chat_completion_service,
        "stream_local",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("stream_local should not be used")
        ),
    )
    monkeypatch.setattr(
        chat_completion_service,
        "_embed_message",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        chat_completion_service.event_bus,
        "emit_event",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        chat_completion_service,
        "get_settings",
        lambda: SimpleNamespace(),
    )


def _run_completion(
    *,
    monkeypatch,
    assistant_text: str,
    thread_id: int,
    request_id: str,
    persist_assistant_message: bool = False,
):
    _stub_completion_pipeline(monkeypatch, assistant_text)
    task = ChatCompletionTask(
        user_id="test_user",
        thread_id=thread_id,
        provider="groq",
        model="mock-model",
        request_id=request_id,
    )
    return chat_completion_service.run_chat_completion_task(
        task,
        persist_assistant_message=persist_assistant_message,
    )


def test_candidate_trace_exists_after_completion(
    test_client, mock_db, monkeypatch
):
    mock_db.get_chat_thread.return_value = {"id": 1, "user_id": "test_user"}

    result = _run_completion(
        monkeypatch=monkeypatch,
        assistant_text="final answer",
        thread_id=1,
        request_id="req-1",
        persist_assistant_message=False,
    )

    assert result["assistant_text"] == "final answer"

    response = test_client.get("/chat/1/debug/candidate-trace/latest")
    assert response.status_code == 200
    body = response.json()
    assert body["thread_id"] == "1"
    assert body["request_id"] == "req-1"
    assert body["selection_strategy"] == "single_candidate"
    assert body["candidates"][0]["content"] == "final answer"


def test_candidate_trace_empty_state_when_missing(test_client, mock_db):
    mock_db.get_chat_thread.return_value = {"id": 1, "user_id": "test_user"}

    response = test_client.get("/chat/1/debug/candidate-trace/latest")
    assert response.status_code == 200
    body = response.json()
    assert body["thread_id"] == "1"
    assert body["request_id"] == ""
    assert body["candidates"] == []
    assert body["selection_strategy"] == ""


def test_candidate_trace_thread_isolation(test_client, mock_db, monkeypatch):
    mock_db.get_chat_thread.side_effect = lambda thread_id: {
        "id": thread_id,
        "user_id": "test_user",
    }

    _run_completion(
        monkeypatch=monkeypatch,
        assistant_text="thread one",
        thread_id=1,
        request_id="req-1",
        persist_assistant_message=False,
    )
    _run_completion(
        monkeypatch=monkeypatch,
        assistant_text="thread two",
        thread_id=2,
        request_id="req-2",
        persist_assistant_message=False,
    )

    response_one = test_client.get("/chat/1/debug/candidate-trace/latest")
    response_two = test_client.get("/chat/2/debug/candidate-trace/latest")

    assert response_one.status_code == 200
    assert response_two.status_code == 200
    assert response_one.json()["request_id"] == "req-1"
    assert response_one.json()["candidates"][0]["content"] == "thread one"
    assert response_two.json()["request_id"] == "req-2"
    assert response_two.json()["candidates"][0]["content"] == "thread two"


def test_candidate_trace_not_persisted_as_message(
    test_client, mock_db, monkeypatch
):
    mock_db.get_chat_thread.return_value = {"id": 1, "user_id": "test_user"}

    _run_completion(
        monkeypatch=monkeypatch,
        assistant_text="canonical assistant answer",
        thread_id=1,
        request_id="req-3",
        persist_assistant_message=True,
    )

    mock_db.create_message.assert_called_once_with(
        1,
        "assistant",
        "canonical assistant answer",
    )

    response = test_client.get("/chat/1/debug/candidate-trace/latest")
    assert response.status_code == 200
    body = response.json()
    assert body["request_id"] == "req-3"
    assert body["candidates"][0]["content"] == "canonical assistant answer"
