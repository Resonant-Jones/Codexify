from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from guardian.core.completion_terminal import successful_non_stream_terminal
from guardian.tasks.types import ChatCompletionTask
from guardian.workers import chat_worker


@pytest.mark.parametrize("provider", ["local", "openai"])
@pytest.mark.parametrize("persist_assistant_message", [False, True])
@pytest.mark.parametrize("trace", [None, "unavailable", {}])
def test_successful_generation_without_trace_does_not_invent_persistence(
    monkeypatch, trace, persist_assistant_message, provider
):
    async def build(task, **kwargs):
        return (
            [{"role": "user", "content": "hello"}],
            provider,
            "test-model",
            {},
            trace,
        )

    monkeypatch.setattr(chat_worker, "_build_messages_for_llm_compat", build)
    monkeypatch.setattr(chat_worker, "get_settings", lambda: SimpleNamespace())
    monkeypatch.setattr(
        chat_worker,
        "build_provider_truth",
        lambda provider, settings, **kwargs: {"provider": provider, **kwargs},
    )
    service = chat_worker._chat_completion_service
    monkeypatch.setattr(service, "_prepare_chat_tool_exposure", lambda *a, **k: None)
    monkeypatch.setattr(
        service,
        "_execute_bounded_tool_turn_completion",
        lambda *a, **k: {
            "assistant_text": "ready",
            "terminal_evidence": successful_non_stream_terminal(
                provider=provider,
                model="test-model",
            ).as_dict(),
        },
    )
    persist = Mock(return_value=501)
    monkeypatch.setattr(chat_worker, "_embed_message", lambda *a, **k: None)
    monkeypatch.setattr(chat_worker.event_bus, "emit_event", lambda *a, **k: None)
    monkeypatch.setattr(
        chat_worker.dependencies, "chatlog_db", SimpleNamespace(create_message=persist)
    )
    task = ChatCompletionTask(
        user_id="local",
        thread_id=17,
        provider=provider,
        model="test-model",
        selection_source="explicit",
        provider_pinned=True,
    )
    result = chat_worker._run_chat_completion_task_compat(
        task, persist_assistant_message=persist_assistant_message
    )
    assert result["assistant_text"] == "ready"
    assert result["terminal_evidence"]["status"] == "success"
    assert result["completion_truth"]["executed"] is True
    assert result["completion_truth"]["completed"] is persist_assistant_message
    if persist_assistant_message:
        assert result["message_id"] == 501
        assert result["persistence_outcome"] == "persisted"
        persist.assert_called_once_with(17, "assistant", "ready")
    else:
        assert "message_id" not in result
        persist.assert_not_called()
    if isinstance(trace, dict):
        assert isinstance(result["trace"], dict)
    else:
        assert result["trace"] is None
