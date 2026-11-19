"""Synthetic final-wire regressions for the queue worker's public entry point."""

import base64
import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from guardian.core import ai_router, chat_completion_service as service
from guardian.core.config import Settings
from guardian.core.media_signing import sign_media_url
from guardian.tasks.types import ChatCompletionTask
from guardian.workers import chat_worker
from tests.core.test_chat_completion_service_image_routing import _seed_common


@pytest.mark.parametrize(
    "mode",
    ["history", "fresh", "queued", "persisted", "text", "missing", "unsupported"],
)
def test_worker_final_wire_image_transport(monkeypatch, tmp_path, caplog, mode):
    db, settings = _seed_common(monkeypatch, provider="openai", model="gpt-4o")
    monkeypatch.setattr(chat_worker, "get_settings", lambda: settings)
    # Keep real history assembly and the real public worker dispatch; isolate
    # retrieval/storage/transport rather than replacing the completion executor.
    monkeypatch.setattr(
        chat_worker, "_build_messages_for_llm_compat", service.build_messages_for_llm
    )
    monkeypatch.setenv("STORAGE_BASE_PATH", str(tmp_path))
    monkeypatch.setenv("GUARDIAN_MEDIA_URL_SECRET", "synthetic-worker-secret")
    image_bytes = Path("tests/fixtures/vision/color_shapes.png").read_bytes()
    (tmp_path / "images").mkdir()
    if mode != "missing":
        (tmp_path / "images/shapes.png").write_bytes(image_bytes)
    source = sign_media_url("https://preview.example.test/media/images/shapes.png")
    image_message = {
        "id": 1,
        "role": "user",
        "content": f"<!-- cfy-media:image:synthetic -->\n<!-- cfy-media-src:{source} -->\nDescribe the shapes.",
    }
    authored_parts = [
        {"type": "text", "text": "Describe the shapes."},
        {"type": "image_url", "image_url": {"url": source, "detail": "high"}},
    ]
    if mode in ("queued", "persisted"):
        image_message["content"] = "Describe the shapes. [Image attached]"
    if mode == "persisted":
        image_message["extra_meta"] = {"original_content": authored_parts}
    messages = [image_message]
    if mode in ("history", "missing"):
        messages += [
            {"id": 2, "role": "assistant", "content": "Colored shapes."},
            {"id": 3, "role": "user", "content": "Which shape is red?"},
        ]
    if mode == "text":
        messages = [{"id": 1, "role": "user", "content": "Hello."}]
    original = copy.deepcopy(messages)
    db.list_messages.return_value = messages
    if mode == "unsupported":
        monkeypatch.setattr(
            service, "resolve_model_vision_capability_state", lambda *a: False
        )
    captured = []

    def post(url, **kwargs):
        assert url == "https://api.openai.com/v1/chat/completions"
        kwargs.pop("timeout", None)
        body = json.loads(
            ai_router.requests.Request("POST", url, **kwargs).prepare().body
        )
        captured.append(body)
        return SimpleNamespace(
            status_code=200,
            json=lambda: {
                "choices": [
                    {
                        "message": {"content": "Synthetic answer."},
                        "finish_reason": "stop",
                    }
                ]
            },
        )

    monkeypatch.setattr(ai_router.requests, "post", post)
    monkeypatch.setattr(
        ai_router.requests,
        "get",
        lambda *a, **k: pytest.fail("Unexpected network read"),
    )
    monkeypatch.setattr(ai_router, "assert_egress_allowed", lambda *a, **k: None)
    adapter_settings = Settings(
        OPENAI_API_KEY="synthetic-key", ALLOW_CLOUD_PROVIDERS=True
    )
    monkeypatch.setattr(
        service,
        "chat_with_ai",
        lambda messages, **kw: ai_router.call_openai(
            messages, kw["model"], settings=adapter_settings
        ),
    )
    task = ChatCompletionTask(
        user_id="local",
        thread_id=1,
        provider="openai",
        model="gpt-4o",
        requested_provider="openai",
        requested_model="gpt-4o",
        selection_source="explicit",
    )
    if mode == "queued":
        task.latest_turn_messages = authored_parts
    if mode in ("missing", "unsupported"):
        with pytest.raises(HTTPException) as error:
            chat_worker.run_chat_completion_task(task, persist_assistant_message=False)
        assert not captured
        expected_code = (
            "CHAT_COMPLETE_IMAGE_PAYLOAD_MISSING"
            if mode == "missing"
            else "CHAT_COMPLETE_IMAGE_VISION_UNSUPPORTED"
        )
        assert error.value.detail["error_code"] == expected_code
        assert source not in str(error.value.detail)
        assert source not in caplog.text
        return
    result = chat_worker.run_chat_completion_task(task, persist_assistant_message=False)
    assert len(captured) == 1
    assert captured[0]["model"] == "gpt-4o"
    users = [m for m in captured[0]["messages"] if m["role"] == "user"]
    if mode == "text":
        assert users[-1]["content"] == "Hello."
    else:
        parts = users[0]["content"]
        assert isinstance(parts, list)
        actual = parts[1]["image_url"]["url"]
        expected = "data:image/png;base64," + base64.b64encode(image_bytes).decode()
        assert bool(
            actual == expected
        ), "final wire must contain exact synthetic image bytes"
        if mode in ("queued", "persisted"):
            assert bool(authored_parts[1]["image_url"]["url"] == source)
            assert users[0]["content"][1]["image_url"]["detail"] == "high"
        assert result["image_attachment_count"] == 1
        assert result["image_routing_path"] == "native_multimodal_vision"
        if mode == "history":
            assert users[-1]["content"] == "Which shape is red?"
    assert messages == original
