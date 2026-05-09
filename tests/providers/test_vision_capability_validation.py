from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from guardian.core import ai_router, chat_completion_service, llm_catalog
from guardian.protocol_tokens import ErrorCode
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
        LOCAL_CHAT_MODEL=model,
        LOCAL_BASE_URL="http://127.0.0.1:11434/v1",
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


def test_vision_capable_image_turn_proceeds_to_provider_ready_assembly(
    monkeypatch: pytest.MonkeyPatch,
):
    _seed_common(monkeypatch, provider="openai", model="gpt-4o")
    monkeypatch.setattr(
        chat_completion_service,
        "resolve_model_vision_capability_state",
        lambda *args, **kwargs: True,
    )

    captured: dict[str, object] = {}

    def _capture(messages, **kwargs):
        captured["messages"] = messages
        return "ok"

    monkeypatch.setattr(chat_completion_service, "chat_with_ai", _capture)

    task = ChatCompletionTask(
        user_id="local", thread_id=1, provider="openai", model="gpt-4o"
    )
    result = chat_completion_service.run_chat_completion_task(
        task,
        persist_assistant_message=False,
    )

    messages = captured["messages"]
    system_messages = [m for m in messages if str(m.get("role")) == "system"]
    assert len(system_messages) == 2
    assert system_messages[0]["content"] == "BASE SYSTEM"
    assert "Completion targeting guidance" in system_messages[1]["content"]

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
    assert summary["image_routing_path"] == "native_multimodal_vision"
    assert summary["image_attachment_count"] == 1
    assert summary["derived_image_context_injected"] is False


def test_non_vision_model_rejects_image_turn_before_provider_execution(
    monkeypatch: pytest.MonkeyPatch,
):
    _seed_common(monkeypatch, provider="openai", model="gpt-4o")
    monkeypatch.setattr(
        chat_completion_service,
        "resolve_model_vision_capability_state",
        lambda *args, **kwargs: False,
    )
    monkeypatch.setattr(
        chat_completion_service,
        "chat_with_ai",
        lambda *_args, **_kwargs: pytest.fail(
            "provider execution should not be reached when vision is unsupported"
        ),
    )

    task = ChatCompletionTask(
        user_id="local", thread_id=1, provider="openai", model="gpt-4o"
    )

    with pytest.raises(HTTPException) as excinfo:
        chat_completion_service.run_chat_completion_task(
            task,
            persist_assistant_message=False,
        )

    detail = excinfo.value.detail
    assert isinstance(detail, dict)
    assert (
        detail["error_code"]
        == ErrorCode.CHAT_COMPLETE_IMAGE_VISION_UNSUPPORTED.value
    )
    assert "support image turns" in str(detail["message"]).lower()
    assert detail["provider"] == "openai"
    assert detail["model"] == "gpt-4o"
    assert detail["image_attachment_count"] == 1


def test_unknown_vision_capability_preserves_existing_fallback_behavior(
    monkeypatch: pytest.MonkeyPatch,
):
    _seed_common(monkeypatch, provider="groq", model="llama-3.1-70b-versatile")
    monkeypatch.setattr(
        chat_completion_service,
        "resolve_model_vision_capability_state",
        lambda *args, **kwargs: None,
    )

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
        user_id="local",
        thread_id=1,
        provider="groq",
        model="llama-3.1-70b-versatile",
    )
    result = chat_completion_service.run_chat_completion_task(
        task,
        persist_assistant_message=False,
    )

    messages = captured["messages"]
    last_user = messages[-1]
    assert last_user["role"] == "user"
    assert isinstance(last_user["content"], str)
    assert "Derived image context" in last_user["content"]
    assert "A test image of a chart." in last_user["content"]
    assert "Describe this." in last_user["content"]

    summary = result["payload_summary"]
    assert summary["image_routing_path"] == "interpreter"
    assert summary["derived_image_context_injected"] is True


def test_local_vision_hint_model_is_classified_as_vision_capable(
    monkeypatch: pytest.MonkeyPatch,
):
    settings = SimpleNamespace(
        LOCAL_BASE_URL="http://127.0.0.1:11434/v1",
        LOCAL_CHAT_MODEL="medgemma:4b-it-q8_0",
    )

    monkeypatch.setattr(
        llm_catalog,
        "_fetch_local_models",
        lambda _settings: ([], {}, {}),
    )

    assert (
        llm_catalog.resolve_model_vision_capability_state(
            "local",
            "medgemma:4b-it-q8_0",
            settings,
        )
        is True
    )


def test_image_payload_missing_has_distinct_error_code(
    monkeypatch: pytest.MonkeyPatch,
):
    _seed_common(monkeypatch, provider="openai", model="gpt-4o")
    monkeypatch.setattr(
        chat_completion_service,
        "resolve_model_vision_capability_state",
        lambda *args, **kwargs: True,
    )
    monkeypatch.setattr(
        chat_completion_service,
        "extract_attachments_and_text",
        lambda _content: (
            [{"kind": "image", "name": "Test.png"}],
            "Describe this.",
        ),
    )
    monkeypatch.setattr(
        chat_completion_service,
        "chat_with_ai",
        lambda *_args, **_kwargs: pytest.fail(
            "provider execution should not be reached when image payload is missing"
        ),
    )

    task = ChatCompletionTask(
        user_id="local", thread_id=1, provider="openai", model="gpt-4o"
    )

    with pytest.raises(HTTPException) as excinfo:
        chat_completion_service.run_chat_completion_task(
            task,
            persist_assistant_message=False,
        )

    detail = excinfo.value.detail
    assert isinstance(detail, dict)
    assert (
        detail["error_code"]
        == ErrorCode.CHAT_COMPLETE_IMAGE_PAYLOAD_MISSING.value
    )
    assert "missing source urls" in str(detail["message"]).lower()
    assert detail["provider"] == "openai"
    assert detail["model"] == "gpt-4o"


def test_chat_router_rejects_image_turn_when_vision_is_explicitly_unsupported(
    monkeypatch: pytest.MonkeyPatch,
):
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Describe this."},
                {
                    "type": "image_url",
                    "image_url": {"url": "https://example.test/image.png"},
                },
            ],
        }
    ]

    monkeypatch.setattr(
        ai_router,
        "resolve_model_vision_capability_state",
        lambda *args, **kwargs: False,
    )
    monkeypatch.setattr(
        ai_router,
        "call_openai",
        lambda *_args, **_kwargs: pytest.fail(
            "provider execution should not be reached when vision is unsupported"
        ),
    )

    with pytest.raises(HTTPException) as excinfo:
        ai_router.chat_with_ai(
            messages,
            model="gpt-4o",
            provider="openai",
        )

    detail = excinfo.value.detail
    assert isinstance(detail, dict)
    assert (
        detail["error_code"]
        == ErrorCode.CHAT_COMPLETE_IMAGE_VISION_UNSUPPORTED.value
    )
    assert "support image turns" in str(detail["message"]).lower()
    assert detail["provider"] == "openai"
