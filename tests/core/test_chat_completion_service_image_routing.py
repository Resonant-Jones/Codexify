from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from guardian.core import chat_completion_service
from guardian.protocol_tokens import (
    ImageRoutingPath,
    TraceSnapshotAbsenceReason,
)
from guardian.tasks.types import ChatCompletionTask
from guardian.workers import chat_worker


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

        async def assemble(
            self,
            thread_id,
            query,
            depth_mode,
            user_id,
            retrieval_policy=None,
            **kwargs,
        ):
            _ = (retrieval_policy, kwargs)
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

    return mock_chatlog_db, settings


def test_image_routing_native_vision_builds_multimodal_payload(
    monkeypatch: pytest.MonkeyPatch,
):
    _seed_common(monkeypatch, provider="openai", model="gpt-4o")

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
    assert (
        summary["image_routing_path"]
        == ImageRoutingPath.NATIVE_MULTIMODAL_VISION.value
    )
    assert summary["image_attachment_count"] == 1
    assert summary["derived_image_context_injected"] is False


def test_image_routing_origin_hints_preserve_absence_reason(
    monkeypatch: pytest.MonkeyPatch,
):
    mock_chatlog_db = _seed_common(
        monkeypatch, provider="openai", model="gpt-4o"
    )
    mock_chatlog_db.list_messages.return_value = [
        {
            "id": 1,
            "role": "user",
            "content": "What is in this image?",
        }
    ]

    captured: dict[str, object] = {}

    def _capture(messages, **kwargs):
        captured["messages"] = messages
        return "ok"

    monkeypatch.setattr(chat_completion_service, "chat_with_ai", _capture)

    task = ChatCompletionTask(
        user_id="local",
        thread_id=1,
        provider="openai",
        model="gpt-4o",
        origin="api:chat.complete|turn_id=turn-1|source_mode=project|image_attachment_count=1",
    )
    result = chat_completion_service.run_chat_completion_task(
        task,
        persist_assistant_message=False,
    )

    summary = result["payload_summary"]
    assert summary["image_attachment_count"] == 1
    assert summary["image_routing_path"] is None
    assert (
        summary["image_routing_absence_reason"]
        == TraceSnapshotAbsenceReason.VISION_MODEL_SELECTED_BUT_IMAGE_PAYLOAD_NOT_ROUTED.value
    )


def test_image_routing_origin_hints_mark_local_model_substitution_absence(
    monkeypatch: pytest.MonkeyPatch,
):
    mock_chatlog_db = _seed_common(
        monkeypatch,
        provider="local",
        model="library2/ministral-3:8b",
    )
    mock_chatlog_db.list_messages.return_value = [
        {
            "id": 1,
            "role": "user",
            "content": "What is in this image?",
        }
    ]

    monkeypatch.setattr(
        chat_completion_service,
        "resolve_model_vision_capability_state",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        chat_completion_service,
        "resolve_thread_completion_settings",
        lambda *args, **kwargs: SimpleNamespace(
            provider="local",
            model="library2/ministral-3:8b",
            source_mode="project",
            persona_id=None,
            temperature_override=None,
        ),
    )
    monkeypatch.setattr(
        chat_completion_service,
        "chat_with_ai",
        lambda *_args, **_kwargs: "ok",
    )
    monkeypatch.setattr(
        chat_completion_service,
        "stream_local",
        lambda *_args, **_kwargs: "ok",
    )

    task = ChatCompletionTask(
        user_id="local",
        thread_id=1,
        provider="local",
        model="medgemma:4b-it-q8_0",
        requested_provider="local",
        requested_model="medgemma:4b-it-q8_0",
        origin=(
            "api:chat.complete|turn_id=turn-1|source_mode=project"
            "|image_attachment_count=1"
        ),
    )
    result = chat_completion_service.run_chat_completion_task(
        task,
        persist_assistant_message=False,
    )

    trace = result["trace"]
    assert trace["image_attachment_count"] == 1
    assert trace["image_routing_path"] is None
    assert (
        trace["image_routing_absence_reason"]
        == TraceSnapshotAbsenceReason.LOCAL_MODEL_SUBSTITUTION_SELECTED_NONVISION_MODEL.value
    )
    assert result["payload_summary"]["image_attachment_count"] == 1
    assert result["payload_summary"]["image_routing_path"] is None
    assert (
        result["payload_summary"]["image_routing_absence_reason"]
        == TraceSnapshotAbsenceReason.LOCAL_MODEL_SUBSTITUTION_SELECTED_NONVISION_MODEL.value
    )


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
    system_messages = [m for m in messages if str(m.get("role")) == "system"]
    assert len(system_messages) == 2
    assert system_messages[0]["content"] == "BASE SYSTEM"
    assert "Completion targeting guidance" in system_messages[1]["content"]

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


def test_image_routing_text_only_uses_local_blip_captioning(
    monkeypatch: pytest.MonkeyPatch,
):
    _seed_common(monkeypatch, provider="local", model="qwen3.5:9b")

    monkeypatch.setattr(
        chat_completion_service.dependencies,
        "ENABLE_BLIP_MODEL",
        True,
        raising=False,
    )

    def _caption_local(_src):
        return "a green hill with clouds"

    monkeypatch.setattr(
        chat_completion_service,
        "_caption_image_with_local_blip",
        _caption_local,
    )
    monkeypatch.setattr(
        chat_completion_service,
        "_caption_image_with_groq_vision",
        lambda *args, **kwargs: pytest.fail(
            "cloud fallback should not be used when local BLIP is available"
        ),
    )

    captured: dict[str, object] = {}

    def _capture_stream(messages, model, **kwargs):
        captured["messages"] = messages
        captured["model"] = model
        captured["kwargs"] = kwargs
        return "yes, I do see the image of green hills and floating clouds."

    monkeypatch.setattr(
        chat_completion_service, "stream_local", _capture_stream
    )
    monkeypatch.setattr(
        chat_completion_service,
        "chat_with_ai",
        lambda *_args, **_kwargs: pytest.fail(
            "local caption fallback should use stream_local, not chat_with_ai"
        ),
    )

    task = ChatCompletionTask(
        user_id="local", thread_id=1, provider="local", model="qwen3.5:9b"
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
    assert isinstance(last_user["content"], str)
    assert "Derived image context" in last_user["content"]
    assert "a green hill with clouds" in last_user["content"]
    assert "Describe this." in last_user["content"]

    summary = result["payload_summary"]
    assert summary["image_routing_path"] == "interpreter"
    assert summary["image_attachment_count"] == 1
    assert summary["derived_image_context_injected"] is True
    assert "green hills and floating clouds" in result["assistant_text"]
    assert summary["requested_model"] == "qwen3.5:9b"
    assert summary["final_model"] == "qwen3.5:9b"
    assert summary["model_selection"]["requested_model"] == "qwen3.5:9b"
    assert summary["model_selection"]["final_model"] == "qwen3.5:9b"
    assert summary["model_selection"]["model_resolution"][
        "requested_model"
    ] == ("qwen3.5:9b")


def test_image_routing_local_model_substitution_is_machine_readable(
    monkeypatch: pytest.MonkeyPatch,
):
    _seed_common(monkeypatch, provider="local", model="medgemma:4b-it-q8_0")

    monkeypatch.setattr(
        chat_completion_service.dependencies,
        "ENABLE_BLIP_MODEL",
        True,
        raising=False,
    )

    monkeypatch.setattr(
        chat_completion_service,
        "_caption_image_with_local_blip",
        lambda _src: "a green hill with clouds",
    )
    monkeypatch.setattr(
        chat_completion_service,
        "_caption_image_with_groq_vision",
        lambda *args, **kwargs: pytest.fail(
            "cloud fallback should not be used when local BLIP is available"
        ),
    )

    class _Resolution:
        ok = True
        model = "library2/ministral-3:8b"
        source = "LOCAL_CHAT_MODEL"
        strict = True
        requested_model = "medgemma:4b-it-q8_0"
        failure_kind = None
        message = (
            "requested model 'medgemma:4b-it-q8_0' was overridden by "
            "configured local chat model 'library2/ministral-3:8b' from "
            "LOCAL_CHAT_MODEL"
        )
        endpoint_resolution = None

        def as_dict(self):
            return {
                "model": self.model,
                "source": self.source,
                "strict": self.strict,
                "requested_model": self.requested_model,
                "message": self.message,
            }

    captured: dict[str, object] = {}

    def _capture_stream(messages, model, **kwargs):
        captured["messages"] = messages
        captured["model"] = model
        captured["kwargs"] = kwargs
        return "local model substitution reply"

    monkeypatch.setattr(
        chat_completion_service,
        "resolve_local_execution_model",
        lambda **kwargs: _Resolution(),
    )
    monkeypatch.setattr(
        chat_completion_service, "stream_local", _capture_stream
    )

    task = ChatCompletionTask(
        user_id="local",
        thread_id=1,
        provider="local",
        model="medgemma:4b-it-q8_0",
    )
    result = chat_completion_service.run_chat_completion_task(
        task,
        persist_assistant_message=False,
    )

    summary = result["payload_summary"]
    assert "messages" in captured
    assert summary["requested_model"] == "medgemma:4b-it-q8_0"
    assert summary["final_model"] == "library2/ministral-3:8b"
    assert summary["selection_source"] == "LOCAL_CHAT_MODEL"
    assert summary["fallback_reason"] == (
        "requested model 'medgemma:4b-it-q8_0' was overridden by "
        "configured local chat model 'library2/ministral-3:8b' from "
        "LOCAL_CHAT_MODEL"
    )
    assert summary["model_selection"]["requested_model"] == (
        "medgemma:4b-it-q8_0"
    )
    assert summary["model_selection"]["final_model"] == (
        "library2/ministral-3:8b"
    )
    assert summary["model_selection"]["policy_reason"] == "LOCAL_CHAT_MODEL"
    assert summary["model_selection"]["model_resolution"]["source"] == (
        "LOCAL_CHAT_MODEL"
    )


def test_image_routing_local_only_reports_requested_override_reason(
    monkeypatch: pytest.MonkeyPatch,
):
    _, settings = _seed_common(
        monkeypatch, provider="local", model="library2/ministral-3:8b"
    )
    settings.CODEXIFY_LOCAL_ONLY_MODE = True
    settings.LOCAL_LLM_MODEL = "library2/ministral-3:8b"
    settings.LOCAL_CHAT_MODEL = "library2/ministral-3:8b"
    settings.DEFAULT_LOCAL_MODEL = "library2/ministral-3:8b"
    settings.LLM_MODEL = "library2/ministral-3:8b"

    monkeypatch.setattr(
        chat_completion_service.dependencies,
        "ENABLE_BLIP_MODEL",
        True,
        raising=False,
    )

    monkeypatch.setattr(
        chat_completion_service,
        "_caption_image_with_local_blip",
        lambda _src: "a green hill with clouds",
    )
    monkeypatch.setattr(
        chat_completion_service,
        "_caption_image_with_groq_vision",
        lambda *args, **kwargs: pytest.fail(
            "cloud fallback should not be used when local BLIP is available"
        ),
    )

    captured: dict[str, object] = {}

    def _capture_stream(messages, model, **kwargs):
        captured["messages"] = messages
        captured["model"] = model
        captured["kwargs"] = kwargs
        return "yes, I do see the image of green hills and floating clouds."

    monkeypatch.setattr(
        chat_completion_service, "stream_local", _capture_stream
    )
    monkeypatch.setattr(
        chat_completion_service,
        "chat_with_ai",
        lambda *_args, **_kwargs: pytest.fail(
            "local caption fallback should use stream_local, not chat_with_ai"
        ),
    )

    task = ChatCompletionTask(
        user_id="local",
        thread_id=1,
        provider="local",
        model="medgemma:4b-it-q8_0",
    )
    result = chat_completion_service.run_chat_completion_task(
        task,
        persist_assistant_message=False,
    )

    summary = result["payload_summary"]
    assert summary["requested_model"] == "medgemma:4b-it-q8_0"
    assert summary["final_model"] == "library2/ministral-3:8b"
    assert summary["selection_source"] == "LOCAL_CHAT_MODEL"
    assert summary["fallback_reason"] == (
        "requested model 'medgemma:4b-it-q8_0' was overridden by "
        "configured local chat model 'library2/ministral-3:8b' from "
        "LOCAL_CHAT_MODEL"
    )
    assert summary["model_selection"]["requested_model"] == (
        "medgemma:4b-it-q8_0"
    )
    assert summary["model_selection"]["final_model"] == (
        "library2/ministral-3:8b"
    )
    assert summary["model_selection"]["policy_reason"] == "LOCAL_CHAT_MODEL"
    assert summary["model_selection"]["model_resolution"]["message"] == (
        summary["fallback_reason"]
    )


def test_image_routing_fails_without_path(monkeypatch: pytest.MonkeyPatch):
    _seed_common(monkeypatch, provider="groq", model="llama-3.1-70b-versatile")

    monkeypatch.setattr(
        chat_completion_service,
        "_interpret_image_attachments",
        lambda *args, **kwargs: None,
    )

    task = ChatCompletionTask(
        user_id="local",
        thread_id=1,
        provider="groq",
        model="llama-3.1-70b-versatile",
    )

    with pytest.raises(Exception) as excinfo:
        chat_completion_service.run_chat_completion_task(
            task,
            persist_assistant_message=False,
        )

    assert "Image attachments present" in str(excinfo.value)


def test_image_routing_snapshot_carries_containment_fields(
    monkeypatch: pytest.MonkeyPatch,
):
    _seed_common(monkeypatch, provider="openai", model="gpt-4o")

    class _TracefulBroker:
        def __init__(self, *args, **kwargs):
            pass

        async def assemble(self, thread_id, query, depth_mode, user_id):
            bundle = {
                "semantic": [
                    {
                        "content": "I can't view the image.",
                        "source_type": "semantic_context",
                        "role": "assistant",
                        "thread_id": thread_id,
                        "project_id": 42,
                        "retrieval_lane": "semantic",
                        "score": 0.12,
                        "policy_reason": (
                            "assistant_vision_refusal_on_image_turn"
                        ),
                    }
                ],
                "docs": {"project": [], "thread": [], "global": []},
                "graph": [],
            }
            trace = {
                "effective_policy": {
                    "source_mode": "project",
                    "widening_enabled": True,
                    "identity_scope": "project",
                },
                "retrieval_plan": {
                    "retrieval_needed": True,
                    "user_depth": "normal",
                },
                "source_mode": "project",
                "widen_reason": "none",
            }
            return bundle, trace

    monkeypatch.setattr(
        chat_completion_service, "ContextBroker", _TracefulBroker
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

    trace = result["trace"]
    assert trace["retrieval_policy"] == {
        "source_mode": "project",
        "widening_enabled": True,
        "identity_scope": "project",
    }
    assert trace["retrieval_executed"] is True
    assert trace["retrieval_absence_reason"] == "retrieval_no_candidates"
    assert trace["retrieval_suppression"]["summary"] == {
        "total_suppressed": 1,
        "assistant_vision_refusal_on_image_turn": 1,
    }
    assert (
        trace["retrieval_suppression"]["items"][0]["suppression_reason"]
        == "assistant_vision_refusal_on_image_turn"
    )
    assert (
        trace["image_routing_path"]
        == ImageRoutingPath.NATIVE_MULTIMODAL_VISION.value
    )
    assert trace["image_routing_absence_reason"] is None
    assert trace["model_selection"]["requested_provider"] == "openai"
    assert trace["model_selection"]["requested_model"] == "gpt-4o"
    assert trace["model_selection"]["final_provider"] == "openai"
    assert trace["model_selection"]["final_model"] == "gpt-4o"
    assert (
        result["payload_summary"]["model_selection"] == trace["model_selection"]
    )
    assert (
        result["payload_summary"]["image_routing_path"]
        == ImageRoutingPath.NATIVE_MULTIMODAL_VISION.value
    )
    assert result["payload_summary"]["image_routing_absence_reason"] is None


def test_image_routing_snapshot_recovers_native_path_when_trace_helper_misses(
    monkeypatch: pytest.MonkeyPatch,
):
    _seed_common(monkeypatch, provider="openai", model="gpt-4o")

    monkeypatch.setattr(
        chat_completion_service,
        "_resolve_image_routing_trace",
        lambda **kwargs: (None, None),
    )
    monkeypatch.setattr(
        chat_completion_service,
        "messages_contain_image_payload",
        lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(
        chat_completion_service,
        "chat_with_ai",
        lambda *_args, **_kwargs: "ok",
    )

    task = ChatCompletionTask(
        user_id="local", thread_id=1, provider="openai", model="gpt-4o"
    )
    result = chat_completion_service.run_chat_completion_task(
        task,
        persist_assistant_message=False,
    )

    trace = result["trace"]
    assert trace["image_routing_path"] == (
        ImageRoutingPath.NATIVE_MULTIMODAL_VISION.value
    )
    assert trace["image_routing_absence_reason"] is None
    assert result["payload_summary"]["image_routing_path"] == (
        ImageRoutingPath.NATIVE_MULTIMODAL_VISION.value
    )
    assert result["payload_summary"]["image_routing_absence_reason"] is None


def test_image_routing_snapshot_infers_attachment_count_from_trace_text(
    monkeypatch: pytest.MonkeyPatch,
):
    _seed_common(monkeypatch, provider="openai", model="gpt-4o")

    monkeypatch.setattr(
        chat_completion_service,
        "_apply_image_attachment_routing",
        lambda messages, **kwargs: (
            messages,
            {
                "image_routing_path": "none",
                "image_attachment_count": 0,
                "derived_image_context_injected": False,
            },
        ),
    )
    monkeypatch.setattr(
        chat_completion_service,
        "_resolve_image_routing_trace",
        lambda **kwargs: (None, None),
    )
    monkeypatch.setattr(
        chat_completion_service,
        "messages_contain_image_payload",
        lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(
        chat_completion_service,
        "chat_with_ai",
        lambda *_args, **_kwargs: "ok",
    )

    task = ChatCompletionTask(
        user_id="local", thread_id=1, provider="openai", model="gpt-4o"
    )
    result = chat_completion_service.run_chat_completion_task(
        task,
        persist_assistant_message=False,
    )

    trace = result["trace"]
    assert trace["image_routing_path"] == (
        ImageRoutingPath.NATIVE_MULTIMODAL_VISION.value
    )
    assert trace["image_routing_absence_reason"] is None
    assert result["payload_summary"]["image_routing_path"] == (
        ImageRoutingPath.NATIVE_MULTIMODAL_VISION.value
    )
    assert result["payload_summary"]["image_routing_absence_reason"] is None


def test_image_routing_snapshot_marks_vision_model_selected_but_payload_not_routed(
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
        "messages_contain_image_payload",
        lambda *_args, **_kwargs: False,
    )

    monkeypatch.setattr(
        chat_completion_service,
        "chat_with_ai",
        lambda *_args, **_kwargs: "ok",
    )

    task = ChatCompletionTask(
        user_id="local", thread_id=1, provider="openai", model="gpt-4o"
    )
    result = chat_completion_service.run_chat_completion_task(
        task,
        persist_assistant_message=False,
    )

    trace = result["trace"]
    assert trace["image_routing_path"] is None
    assert trace["image_routing_absence_reason"] == (
        TraceSnapshotAbsenceReason.VISION_MODEL_SELECTED_BUT_IMAGE_PAYLOAD_NOT_ROUTED.value
    )
    assert result["payload_summary"]["image_routing_path"] is None
    assert result["payload_summary"]["image_routing_absence_reason"] == (
        TraceSnapshotAbsenceReason.VISION_MODEL_SELECTED_BUT_IMAGE_PAYLOAD_NOT_ROUTED.value
    )


def test_image_routing_snapshot_marks_local_model_substitution_absence(
    monkeypatch: pytest.MonkeyPatch,
):
    _seed_common(monkeypatch, provider="local", model="library2/ministral-3:8b")

    monkeypatch.setattr(
        chat_completion_service,
        "resolve_thread_completion_settings",
        lambda *args, **kwargs: SimpleNamespace(
            provider="local",
            model="library2/ministral-3:8b",
            source_mode="project",
            persona_id=None,
            temperature_override=None,
        ),
    )
    monkeypatch.setattr(
        chat_completion_service,
        "resolve_model_vision_capability_state",
        lambda *args, **kwargs: None,
    )

    monkeypatch.setattr(
        chat_completion_service,
        "_apply_image_attachment_routing",
        lambda messages, **kwargs: (
            messages,
            {
                "image_routing_path": None,
                "image_attachment_count": 1,
                "derived_image_context_injected": False,
            },
        ),
    )

    monkeypatch.setattr(
        chat_completion_service,
        "stream_local",
        lambda *args, **kwargs: "ok",
    )
    monkeypatch.setattr(
        chat_completion_service,
        "chat_with_ai",
        lambda *args, **kwargs: "ok",
    )

    task = ChatCompletionTask(
        user_id="local",
        thread_id=1,
        provider="local",
        model="medgemma:4b-it-q8_0",
        requested_provider="local",
        requested_model="medgemma:4b-it-q8_0",
    )
    result = chat_completion_service.run_chat_completion_task(
        task,
        persist_assistant_message=False,
    )

    trace = result["trace"]
    assert trace["model_selection"]["requested_model"] == (
        "medgemma:4b-it-q8_0"
    )
    assert trace["model_selection"]["final_model"] == (
        "library2/ministral-3:8b"
    )
    assert trace["image_routing_path"] is None
    assert trace["image_routing_absence_reason"] == (
        TraceSnapshotAbsenceReason.LOCAL_MODEL_SUBSTITUTION_SELECTED_NONVISION_MODEL.value
    )
    assert result["payload_summary"]["image_routing_absence_reason"] == (
        TraceSnapshotAbsenceReason.LOCAL_MODEL_SUBSTITUTION_SELECTED_NONVISION_MODEL.value
    )


def test_image_turn_final_assembly_normalizes_stale_not_evaluated_reason(
    monkeypatch: pytest.MonkeyPatch,
):
    mock_chatlog_db = _seed_common(
        monkeypatch,
        provider="local",
        model="library2/ministral-3:8b",
    )

    stale_reason = TraceSnapshotAbsenceReason.IMAGE_ROUTING_NOT_EVALUATED.value
    canonical_reason = (
        TraceSnapshotAbsenceReason.LOCAL_MODEL_SUBSTITUTION_SELECTED_NONVISION_MODEL.value
    )
    model_selection = {
        "requested_provider": "local",
        "requested_model": "medgemma:4b-it-q8_0",
        "final_provider": "local",
        "final_model": "library2/ministral-3:8b",
        "selection_source": "explicit",
        "policy_reason": "LOCAL_CHAT_MODEL",
        "fallback_reason": None,
        "model_resolution": {
            "source": "LOCAL_CHAT_MODEL",
            "message": (
                "requested model 'medgemma:4b-it-q8_0' was overridden "
                "by configured local chat model 'library2/ministral-3:8b' "
                "from LOCAL_CHAT_MODEL"
            ),
        },
    }

    monkeypatch.setattr(
        chat_completion_service,
        "_execute_bounded_tool_turn_completion",
        lambda *args, **kwargs: {
            "assistant_text": "ok",
            "provider": "local",
            "model": "library2/ministral-3:8b",
            "payload_summary": {
                "image_attachment_count": 1,
                "image_routing_path": None,
                "image_routing_absence_reason": stale_reason,
                "model_selection": dict(model_selection),
            },
            "trace": {
                "image_attachment_count": 1,
                "image_routing_path": None,
                "image_routing_absence_reason": stale_reason,
                "retrieval_policy": {
                    "source_mode": "project",
                    "widening_enabled": True,
                    "identity_scope": "project",
                },
                "retrieval_provenance": {
                    "requested_source_mode": "project",
                    "normalized_source_mode": "project",
                    "source_hit_counts": {
                        "semantic_total": 0,
                        "thread_semantic": 0,
                        "obsidian_semantic": 0,
                        "other_semantic": 0,
                        "project_documents": 0,
                        "thread_documents": 0,
                        "global_documents": 0,
                        "other_documents": 0,
                        "memory": 0,
                        "graph": 0,
                    },
                    "retrieval_status": "no_candidates",
                },
                "retrieval_suppression": {
                    "items": [],
                    "summary": {
                        "total_suppressed": 0,
                        "assistant_vision_refusal_on_image_turn": 0,
                    },
                },
                "retrieval_executed": True,
                "retrieval_absence_reason": None,
                "model_selection": dict(model_selection),
            },
        },
    )
    monkeypatch.setattr(
        chat_completion_service,
        "_apply_image_attachment_routing",
        lambda messages, **kwargs: (
            messages,
            {
                "image_attachment_count": 1,
                "image_routing_path": None,
                "derived_image_context_injected": False,
            },
        ),
    )
    monkeypatch.setattr(
        chat_completion_service,
        "chat_with_ai",
        lambda *_args, **_kwargs: "ok",
    )

    task = ChatCompletionTask(
        user_id="local",
        thread_id=1,
        provider="local",
        model="library2/ministral-3:8b",
        requested_provider="local",
        requested_model="medgemma:4b-it-q8_0",
        selection_source="explicit",
        origin=(
            "api:chat.complete|turn_id=turn-1|source_mode=project"
            "|image_attachment_count=1"
        ),
    )
    result = chat_completion_service.run_chat_completion_task(
        task,
        persist_assistant_message=False,
    )

    assert result["image_attachment_count"] == 1
    assert result["image_routing_path"] is None
    assert result["image_routing_absence_reason"] == canonical_reason
    assert result["image_routing_absence_reason"] != stale_reason
    assert result["payload_summary"]["image_attachment_count"] == 1
    assert result["payload_summary"]["image_routing_path"] is None
    assert result["payload_summary"]["image_routing_absence_reason"] == (
        canonical_reason
    )
    assert result["trace"]["image_attachment_count"] == 1
    assert result["trace"]["image_routing_path"] is None
    assert result["trace"]["image_routing_absence_reason"] == canonical_reason
    assert result["trace"]["image_routing_absence_reason"] != stale_reason
    assert result["payload_summary"]["model_selection"] == model_selection
    assert result["model_selection"] == model_selection


def test_worker_completion_normalizes_stale_nested_image_routing_reason(
    monkeypatch: pytest.MonkeyPatch,
):
    stale_reason = TraceSnapshotAbsenceReason.IMAGE_ROUTING_NOT_EVALUATED.value
    canonical_reason = (
        TraceSnapshotAbsenceReason.LOCAL_MODEL_SUBSTITUTION_SELECTED_NONVISION_MODEL.value
    )

    async def _fake_build_messages_for_llm_compat(task, user_id=None):
        return (
            [
                {
                    "role": "system",
                    "content": "BASE SYSTEM",
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "What is in this image?",
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": "https://example.test/image.png"
                            },
                        },
                    ],
                },
            ],
            "local",
            "library2/ministral-3:8b",
            {},
            {
                "source_mode": "project",
                "widen_reason": "none",
                "image_attachment_count": 1,
            },
        )

    monkeypatch.setattr(
        chat_worker,
        "_build_messages_for_llm_compat",
        _fake_build_messages_for_llm_compat,
    )
    monkeypatch.setattr(
        chat_worker._chat_completion_service,
        "_execute_bounded_tool_turn_completion",
        lambda *args, **kwargs: {
            "assistant_text": "ok",
            "provider": "local",
            "model": "library2/ministral-3:8b",
            "payload_summary": {
                "image_attachment_count": 1,
                "image_routing_path": None,
                "image_routing_absence_reason": stale_reason,
                "model_selection": {
                    "requested_provider": "local",
                    "requested_model": "medgemma:4b-it-q8_0",
                    "final_provider": "local",
                    "final_model": "library2/ministral-3:8b",
                    "selection_source": "explicit",
                    "policy_reason": "LOCAL_CHAT_MODEL",
                    "fallback_reason": None,
                },
            },
            "trace": {
                "image_attachment_count": 1,
                "image_routing_path": None,
                "image_routing_absence_reason": stale_reason,
                "model_selection": {
                    "requested_provider": "local",
                    "requested_model": "medgemma:4b-it-q8_0",
                    "final_provider": "local",
                    "final_model": "library2/ministral-3:8b",
                    "selection_source": "explicit",
                    "policy_reason": "LOCAL_CHAT_MODEL",
                    "fallback_reason": None,
                },
                "retrieval_policy": {
                    "source_mode": "project",
                    "widening_enabled": True,
                    "identity_scope": "project",
                },
                "retrieval_provenance": {
                    "requested_source_mode": "project",
                    "normalized_source_mode": "project",
                    "source_hit_counts": {
                        "semantic_total": 0,
                        "thread_semantic": 0,
                        "obsidian_semantic": 0,
                        "other_semantic": 0,
                        "project_documents": 0,
                        "thread_documents": 0,
                        "global_documents": 0,
                        "other_documents": 0,
                        "memory": 0,
                        "graph": 0,
                    },
                    "retrieval_status": "no_candidates",
                },
                "retrieval_suppression": {
                    "items": [],
                    "summary": {
                        "total_suppressed": 0,
                        "assistant_vision_refusal_on_image_turn": 0,
                    },
                },
                "retrieval_executed": True,
                "retrieval_absence_reason": None,
            },
        },
    )
    monkeypatch.setattr(
        chat_worker._chat_completion_service,
        "resolve_model_vision_capability_state",
        lambda *args, **kwargs: False,
    )
    monkeypatch.setattr(
        chat_worker,
        "get_settings",
        lambda: SimpleNamespace(
            LOCAL_CHAT_MODEL="library2/ministral-3:8b",
            LOCAL_BASE_URL="http://127.0.0.1:11434/v1",
            ALLOW_CLOUD_PROVIDERS=True,
        ),
    )

    task = ChatCompletionTask(
        user_id="local",
        thread_id=1,
        provider="local",
        model="medgemma:4b-it-q8_0",
        requested_provider="local",
        requested_model="medgemma:4b-it-q8_0",
        selection_source="explicit",
        origin=(
            "api:chat.complete|turn_id=turn-1|source_mode=project"
            "|image_attachment_count=1"
        ),
    )

    result = chat_worker._run_chat_completion_task_compat(
        task,
        persist_assistant_message=False,
    )

    assert result["image_attachment_count"] == 1
    assert result["image_routing_path"] is None
    assert result["image_routing_absence_reason"] == canonical_reason
    assert result["image_routing_absence_reason"] != stale_reason
    assert result["payload_summary"]["image_routing_absence_reason"] == (
        canonical_reason
    )
    assert result["trace"]["image_routing_absence_reason"] == canonical_reason
    assert result["trace"]["image_routing_absence_reason"] != stale_reason


def test_image_turn_local_substitution_zero_retained_results_completes(
    monkeypatch: pytest.MonkeyPatch,
):
    mock_chatlog_db = _seed_common(
        monkeypatch,
        provider="local",
        model="library2/ministral-3:8b",
    )
    mock_chatlog_db.list_messages.return_value = [
        {
            "id": 1,
            "role": "user",
            "content": (
                "<!-- cfy-media:image:img-1 -->\n\n"
                "<!-- cfy-media-src:https://example.test/image.png -->\n\n"
                "<!-- cfy-media-name:Test.png -->\n\n"
                "What is in this image?"
            ),
        }
    ]

    class _EmptyRetrievalBroker:
        def __init__(self, *args, **kwargs):
            pass

        async def assemble(self, thread_id, query, depth_mode, user_id):
            trace = {
                "effective_policy": {
                    "source_mode": "project",
                    "widening_enabled": True,
                    "identity_scope": "project",
                },
                "retrieval_plan": {
                    "retrieval_needed": True,
                    "user_depth": "normal",
                },
                "source_mode": "project",
                "widen_reason": "none",
                "retrieval_executed": True,
                "retrieval_absence_reason": None,
            }
            bundle = {
                "semantic": [],
                "docs": {"project": [], "thread": [], "global": []},
                "graph": [],
            }
            return bundle, trace

    monkeypatch.setattr(
        chat_completion_service,
        "ContextBroker",
        _EmptyRetrievalBroker,
    )
    monkeypatch.setattr(
        chat_completion_service,
        "resolve_thread_completion_settings",
        lambda *args, **kwargs: SimpleNamespace(
            provider="local",
            model="library2/ministral-3:8b",
            source_mode="project",
            persona_id=None,
            temperature_override=None,
        ),
    )
    monkeypatch.setattr(
        chat_completion_service,
        "resolve_model_vision_capability_state",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        chat_completion_service.dependencies,
        "ENABLE_BLIP_MODEL",
        False,
        raising=False,
    )
    monkeypatch.setattr(
        chat_completion_service,
        "stream_local",
        lambda *_args, **_kwargs: "ok",
    )
    monkeypatch.setattr(
        chat_completion_service,
        "chat_with_ai",
        lambda *_args, **_kwargs: "ok",
    )

    task = ChatCompletionTask(
        user_id="local",
        thread_id=1,
        provider="local",
        model="medgemma:4b-it-q8_0",
        requested_provider="local",
        requested_model="medgemma:4b-it-q8_0",
        origin=(
            "api:chat.complete|turn_id=turn-1|source_mode=project"
            "|image_attachment_count=1"
        ),
    )

    result = chat_completion_service.run_chat_completion_task(
        task,
        persist_assistant_message=False,
    )

    trace = result["trace"]
    assert trace["image_attachment_count"] == 1
    assert (
        trace["image_routing_path"] is not None
        or trace["image_routing_absence_reason"] is not None
    )
    assert trace["image_routing_absence_reason"] != (
        TraceSnapshotAbsenceReason.IMAGE_ROUTING_NOT_EVALUATED.value
    )
    assert trace["retrieval_absence_reason"] == "retrieval_no_candidates"
    assert (
        result["payload_summary"]["image_routing_path"] is not None
        or result["payload_summary"]["image_routing_absence_reason"] is not None
    )
    assert result["payload_summary"]["image_routing_absence_reason"] != (
        TraceSnapshotAbsenceReason.IMAGE_ROUTING_NOT_EVALUATED.value
    )
