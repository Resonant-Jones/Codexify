from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from guardian.tasks.types import ChatCompletionTask
from guardian.core.completion_terminal import successful_non_stream_terminal
from guardian.workers import chat_worker


@pytest.mark.parametrize("has_terminal_evidence", [True, False])
def test_worker_replaces_blank_output_only_after_successful_terminal(
    monkeypatch, has_terminal_evidence
):
    mock_db = MagicMock()
    mock_db.create_message.return_value = 123
    mock_db.write_audit_log = MagicMock()

    monkeypatch.setattr(chat_worker.dependencies, "chatlog_db", mock_db)
    monkeypatch.setattr(
        chat_worker, "_safe_publish", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(
        chat_worker, "_embed_message", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(
        chat_worker.event_bus, "emit_event", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(
        chat_worker, "is_cancelled", lambda *args, **kwargs: False
    )
    monkeypatch.setattr(
        chat_worker, "clear_cancelled", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(
        chat_worker,
        "build_provider_truth",
        lambda provider, settings, **kwargs: {
            "provider": provider,
            **kwargs,
        },
    )

    async def fake_build_messages(_task):
        return [], "local", "model", {}, None, None, {}

    monkeypatch.setattr(
        chat_worker, "_build_messages_for_llm", fake_build_messages
    )
    completion = {"assistant_text": ""}
    if has_terminal_evidence:
        completion["terminal_evidence"] = successful_non_stream_terminal(
            provider="local", model="model", finish_reason="stop"
        ).as_dict()
    monkeypatch.setattr(
        chat_worker._chat_completion_service,
        "_execute_bounded_tool_turn_completion",
        lambda *args, **kwargs: completion,
    )

    task = ChatCompletionTask(
        user_id="local", thread_id=1, provider="local", model="model"
    )
    chat_worker._run_chat_task(task)

    if not has_terminal_evidence:
        mock_db.create_message.assert_not_called()
        return

    args, _kwargs = mock_db.create_message.call_args
    assert args[0] == 1
    assert args[1] == "assistant"
    assert args[2].strip() != ""


@pytest.mark.asyncio
async def test_build_messages_for_llm_uses_single_system_message(monkeypatch):
    mock_db = MagicMock()
    mock_db.get_chat_thread.return_value = {
        "id": 1,
        "user_id": "default",
        "project_id": None,
    }
    mock_db.list_messages.return_value = [
        {"id": 1, "role": "user", "content": "Hello"},
    ]

    settings = SimpleNamespace(
        LLM_PROVIDER="local",
        ALLOW_CLOUD_PROVIDERS=True,
        LOCAL_LLM_MODEL="",
        DEFAULT_LOCAL_MODEL="",
        LLM_MODEL="",
    )
    monkeypatch.setattr(chat_worker, "get_settings", lambda: settings)
    monkeypatch.setattr(chat_worker.dependencies, "chatlog_db", mock_db)
    monkeypatch.setattr(
        chat_worker, "validate_llm_config", lambda *a, **k: None
    )
    monkeypatch.setattr(
        chat_worker, "resolve_thread_system_profile", lambda *a, **k: None
    )
    monkeypatch.setattr(
        chat_worker,
        "build_guardian_system_prompt",
        lambda **k: ("BASE BLOCK", {"estimated_tokens": 10}),
    )
    monkeypatch.setattr(
        chat_worker,
        "build_context_system_message",
        lambda bundle: "CONTEXT BLOCK",
    )
    monkeypatch.setattr(chat_worker, "_resolve_media_items", lambda *a, **k: [])
    monkeypatch.setattr(
        chat_worker, "_build_media_system_message", lambda items: None
    )
    monkeypatch.setattr(
        chat_worker, "_maybe_add_vision_summary", lambda items, provider: None
    )

    class _Broker:
        def __init__(self, *args, **kwargs):
            pass

        async def assemble(self, *args, **kwargs):
            return {}, None

    monkeypatch.setattr(chat_worker, "ContextBroker", _Broker)

    task = ChatCompletionTask(
        user_id="local",
        thread_id=1,
        provider="local",
        model="test-model",
    )
    messages_for_llm, *_rest = await chat_worker._build_messages_for_llm(task)
    system_messages = [m for m in messages_for_llm if m.get("role") == "system"]

    assert len(system_messages) == 1
    assert "BASE BLOCK" in system_messages[0]["content"]
    assert "CONTEXT BLOCK" in system_messages[0]["content"]
