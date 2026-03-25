from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from guardian.core import chat_completion_service
from guardian.tasks.types import ChatCompletionTask


def _seed_common(monkeypatch: pytest.MonkeyPatch, *, provider: str, model: str):
    mock_chatlog_db = MagicMock()
    mock_chatlog_db.get_chat_thread.return_value = {
        "id": 1,
        "user_id": "user-1",
        "project_id": 42,
    }
    mock_chatlog_db.list_messages.return_value = [
        {
            "id": 1,
            "role": "user",
            "content": (
                "<!-- cfy-media:image:img-1 -->\n\n"
                "<!-- cfy-media-src:https://example.test/image.png -->\n\n"
                "<!-- cfy-media-name:Test.png -->\n\n"
                "Describe this."
            ),
        }
    ]

    class _EmptyBroker:
        def __init__(self, *args, **kwargs):
            pass

        async def assemble(self, thread_id, query, depth_mode, user_id):
            return {}, None

    settings = SimpleNamespace(
        LLM_PROVIDER=provider,
        LLM_MODEL=model,
        DEFAULT_LOCAL_MODEL=model,
        LOCAL_LLM_MODEL=model,
        ALLOW_CLOUD_PROVIDERS=True,
        GROQ_API_KEY="test",
        GROQ_VISION_MODEL="meta-llama/llama-4-scout-17b-16e-instruct",
    )

    monkeypatch.setattr(
        chat_completion_service, "get_settings", lambda: settings
    )
    monkeypatch.setattr(
        chat_completion_service,
        "validate_llm_config",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        chat_completion_service,
        "build_guardian_system_prompt",
        lambda **kwargs: ("BASE SYSTEM", {"estimated_tokens": 16}),
    )
    monkeypatch.setattr(
        chat_completion_service,
        "build_context_system_message_with_meta",
        lambda *args, **kwargs: (None, {}),
    )
    monkeypatch.setattr(chat_completion_service, "ContextBroker", _EmptyBroker)
    monkeypatch.setattr(
        chat_completion_service.dependencies,
        "chatlog_db",
        mock_chatlog_db,
        raising=False,
    )
    monkeypatch.setattr(
        chat_completion_service.dependencies,
        "CHAT_PROVIDER",
        provider,
        raising=False,
    )
    monkeypatch.setattr(
        chat_completion_service.dependencies,
        "_vector_store",
        None,
        raising=False,
    )
    monkeypatch.setattr(
        chat_completion_service.dependencies,
        "_memory_store",
        None,
        raising=False,
    )
    monkeypatch.setattr(
        chat_completion_service.dependencies,
        "_sensors",
        None,
        raising=False,
    )

    return mock_chatlog_db


def test_image_routing_vlm_builds_multimodal_payload(
    monkeypatch: pytest.MonkeyPatch,
):
    _seed_common(monkeypatch, provider="openai", model="gpt-4o")

    captured: dict[str, object] = {}

    def _capture(messages, **kwargs):
        captured["messages"] = messages
        return "ok"

    monkeypatch.setattr(chat_completion_service, "chat_with_ai", _capture)

    task = ChatCompletionTask(thread_id=1, provider="openai", model="gpt-4o")
    result = chat_completion_service.run_chat_completion_task(
        task,
        persist_assistant_message=False,
    )

    messages = captured["messages"]
    system_messages = [m for m in messages if str(m.get("role")) == "system"]
    assert len(system_messages) == 1

    last_user = messages[-1]
    assert last_user["role"] == "user"
    assert isinstance(last_user["content"], list)
    assert last_user["content"][0]["type"] == "text"
    assert last_user["content"][0]["text"] == "Describe this."
    assert last_user["content"][1]["type"] == "image_url"
    assert last_user["content"][1]["image_url"]["url"] == (
        "https://example.test/image.png"
    )

    summary = result["payload_summary"]
    assert summary["image_routing_path"] == "vlm"
    assert summary["image_attachment_count"] == 1
    assert summary["derived_image_context_injected"] is False


def test_image_routing_text_only_runs_interpreter(
    monkeypatch: pytest.MonkeyPatch,
):
    _seed_common(monkeypatch, provider="groq", model="llama-3.1-70b-versatile")

    def _fake_interpreter(*_args, **_kwargs):
        return [
            {
                "label": "Test.png",
                "summary": "A test image of a chart.",
            }
        ]

    monkeypatch.setattr(
        chat_completion_service,
        "_interpret_image_attachments",
        _fake_interpreter,
    )

    captured: dict[str, object] = {}

    def _capture(messages, **kwargs):
        captured["messages"] = messages
        return "ok"

    monkeypatch.setattr(chat_completion_service, "chat_with_ai", _capture)

    task = ChatCompletionTask(
        thread_id=1, provider="groq", model="llama-3.1-70b-versatile"
    )
    result = chat_completion_service.run_chat_completion_task(
        task,
        persist_assistant_message=False,
    )

    messages = captured["messages"]
    system_messages = [m for m in messages if str(m.get("role")) == "system"]
    assert len(system_messages) == 1

    last_user = messages[-1]
    assert last_user["role"] == "user"
    assert isinstance(last_user["content"], str)
    assert "Derived image context" in last_user["content"]
    assert "A test image of a chart." in last_user["content"]
    assert "Describe this." in last_user["content"]

    summary = result["payload_summary"]
    assert summary["image_routing_path"] == "interpreter"
    assert summary["image_attachment_count"] == 1
    assert summary["derived_image_context_injected"] is True


def test_image_routing_fails_without_path(monkeypatch: pytest.MonkeyPatch):
    _seed_common(monkeypatch, provider="groq", model="llama-3.1-70b-versatile")

    monkeypatch.setattr(
        chat_completion_service,
        "_interpret_image_attachments",
        lambda *args, **kwargs: None,
    )

    task = ChatCompletionTask(
        thread_id=1, provider="groq", model="llama-3.1-70b-versatile"
    )

    with pytest.raises(Exception) as excinfo:
        chat_completion_service.run_chat_completion_task(
            task,
            persist_assistant_message=False,
        )

    assert "Image attachments present" in str(excinfo.value)
