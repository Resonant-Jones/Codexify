"""Legacy SDK calls must not borrow the bounded chat reservation."""

import importlib
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from guardian.metering import runtime

CONFIG = json.dumps(
    dict(
        mode="enforce",
        payer_scope="operator",
        monthly_window="month",
        funding_window="funding",
        max_output_tokens=100,
        quote={},
    )
)

CASES = [
    ("guardian.core.research.Modules.model.deepseek", "Deepseek", "get_client", [], {}),
    (
        "guardian.core.research.Modules.model.deepseek",
        "Deepseek",
        "get_llm_config",
        [],
        {},
    ),
    ("guardian.core.research.Modules.model.gork", "Gork", "get_client", [], {}),
    ("guardian.core.research.Modules.model.gork", "Gork", "get_llm_config", [], {}),
    ("guardian.providers.groq_adapter", "GroqChat", "generate", ["hi"], {}),
    ("guardian.providers.groq_adapter", "GroqChat", "stream", ["hi"], {}),
    ("guardian.providers.groq_client", "GroqChatClient", "__call__", ["hi"], {}),
    ("guardian.providers.groq_client", "GroqChatClient", "stream", ["hi"], {}),
    ("guardian.providers.gemini_adapter", "GeminiChat", "generate", ["hi"], {}),
    ("guardian.providers.gemini_adapter", "GeminiChat", "stream", ["hi"], {}),
    ("guardian.providers.minimax_adapter", "MiniMaxAdapter", "generate", ["hi"], {}),
    ("guardian.providers.minimax_adapter", "MiniMaxAdapter", "stream", ["hi"], {}),
    (
        "guardian.providers.minimax_adapter",
        "MiniMaxAdapter",
        "_generate_anthropic",
        ["hi"],
        {},
    ),
    (
        "guardian.providers.minimax_adapter",
        "MiniMaxAdapter",
        "_stream_anthropic",
        ["hi"],
        {},
    ),
    (
        "guardian.memoryos.utils",
        "GroqClient",
        "chat_completion",
        [],
        {"model": "test", "messages": []},
    ),
    (
        "guardian.core.research.Modules.model.deepseek",
        "Deepseek",
        "completion",
        ["hi"],
        {},
    ),
    ("guardian.core.research.Modules.model.gork", "Gork", "completion", ["hi"], {}),
    (
        "guardian.tts.providers.deepgram_provider",
        "DeepgramProvider",
        "synthesize",
        ["hi", "voice"],
        {},
    ),
    (
        "guardian.tts.providers.deepgram_provider",
        "DeepgramProvider",
        "_synthesize_chunk",
        ["hi", "voice"],
        {},
    ),
    (
        "guardian.tts.providers.elevenlabs_provider",
        "ElevenLabsProvider",
        "synthesize",
        ["hi", "voice"],
        {},
    ),
    (
        "guardian.tts.providers.google_provider",
        "GoogleProvider",
        "synthesize",
        ["hi", "voice"],
        {},
    ),
    (
        "guardian.memoryos.utils",
        "OpenAIClient",
        "chat_completion",
        [],
        {"model": "test", "messages": []},
    ),
    ("guardian.providers.openai_adapter", "OpenAIChat", "generate", ["hello"], {}),
    ("guardian.providers.openai_adapter", "OpenAIChat", "stream", ["hello"], {}),
    ("guardian.providers.openai_adapter", "OpenAIEmbeddings", "embed", [["hello"]], {}),
    (
        "guardian.image_gen.providers.openai",
        "OpenAIImageGen",
        "generate",
        ["hello"],
        {"model": "unqualified"},
    ),
    (
        "guardian.memoryos.embedders.openai_embedder",
        "OpenAIEmbedder",
        "embed",
        ["hello"],
        {},
    ),
    (
        "guardian.memoryos.embedders.openai_embedder",
        "OpenAIEmbedder",
        "embed_batch",
        [["hello"]],
        {},
    ),
    (
        "guardian.core.research.Modules.model.openai",
        "OpenAI",
        "completion",
        ["hello"],
        {},
    ),
    ("guardian.core.research.Modules.model.openai", "OpenAI", "get_client", [], {}),
    ("guardian.core.research.Modules.model.openai", "OpenAI", "get_llm_config", [], {}),
]


@pytest.mark.parametrize("raw", [CONFIG, "malformed"])
@pytest.mark.parametrize("module,cls,method,args,kwargs", CASES)
def test_legacy_spend_denied_before_sdk(
    monkeypatch, raw, module, cls, method, args, kwargs
):
    monkeypatch.setenv(runtime.ENV, raw)
    instance = object.__new__(getattr(importlib.import_module(module), cls))
    instance.client = Mock(side_effect=AssertionError("network must not run"))
    instance.timeout = 1
    instance.model = "test"
    token = runtime._CONTEXT.set(SimpleNamespace())
    try:
        with pytest.raises(HTTPException) as exc:
            result = getattr(instance, method)(*args, **kwargs)
            if "stream" in method:
                list(result)
        assert exc.value.status_code == 503
        assert not instance.client.mock_calls
    finally:
        runtime._CONTEXT.reset(token)


def test_unconfigured_guard_is_inert(monkeypatch):
    monkeypatch.delenv(runtime.ENV, raising=False)
    runtime.deny_unqualified_spend()


def test_unconfigured_sdk_generation_unchanged(monkeypatch):
    monkeypatch.delenv(runtime.ENV, raising=False)
    from guardian.providers.openai_adapter import OpenAIChat

    instance = object.__new__(OpenAIChat)
    instance.client = Mock()
    instance.timeout = 1
    instance.client.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))]
    )
    assert instance.generate("hello") == "ok"
    instance.client.chat.completions.create.assert_called_once()


@pytest.mark.parametrize("raw", [CONFIG, "malformed"])
def test_openai_voice_denied_before_http(monkeypatch, raw):
    from guardian.voice import service

    monkeypatch.setenv(runtime.ENV, raw)
    network = Mock(side_effect=AssertionError("network must not run"))
    monkeypatch.setattr(service.requests, "post", network)
    with pytest.raises(HTTPException) as exc:
        service.transcribe_audio(b"audio", "audio/wav", provider="openai")
    assert exc.value.status_code == 503
    network.assert_not_called()


@pytest.mark.parametrize(
    "module,method,args,kwargs",
    [
        ("guardian.core.groq", "groq_chat", [[]], {}),
        (
            "guardian.utils.groq_helpers",
            "run_groq_vision_url",
            ["https://example.com/image"],
            {},
        ),
        ("guardian.utils.groq_helpers", "run_groq_vision_file", ["not-a-file"], {}),
        (
            "guardian.voice.service",
            "_request_transcription_deepgram",
            [],
            dict(
                api_key="synthetic",
                model="test",
                audio_bytes=b"test",
                mime_type="audio/wav",
                timeout_seconds=1,
            ),
        ),
    ],
)
def test_cloud_helpers_denied(monkeypatch, module, method, args, kwargs):
    monkeypatch.setenv(runtime.ENV, CONFIG)
    with pytest.raises(HTTPException) as exc:
        getattr(importlib.import_module(module), method)(*args, **kwargs)
    assert exc.value.status_code == 503


@pytest.mark.parametrize(
    "url",
    [
        "https://api.deepseek.com/v1/chat/completions",
        "https://api.groq.com/openai/v1/chat/completions",
        "https://proxy.example/v1/chat/completions",
    ],
)
def test_cloud_choke_point_cannot_bypass_with_alias_or_direct_call(monkeypatch, url):
    monkeypatch.setenv(runtime.ENV, CONFIG)
    send = Mock(side_effect=AssertionError("must not dispatch"))
    with pytest.raises(HTTPException):
        runtime.guarded_http(url, {}, send)
    send.assert_not_called()


@pytest.mark.parametrize(
    "module,cls",
    [
        ("guardian.providers.groq_adapter", "GroqChat"),
        ("guardian.providers.minimax_adapter", "MiniMaxAdapter"),
    ],
)
def test_unconfigured_other_sdk_generation_unchanged(monkeypatch, module, cls):
    monkeypatch.delenv(runtime.ENV, raising=False)
    instance = object.__new__(getattr(importlib.import_module(module), cls))
    instance.client = Mock()
    instance.timeout = 1
    instance.api_flavor = "openai"
    instance.default_model = "test"
    instance.model = "test"
    instance._resolve_model = lambda model: "test"
    instance.client.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))]
    )
    assert instance.generate("hello") == "ok"
    instance.client.chat.completions.create.assert_called_once()


@pytest.mark.parametrize("raw", [CONFIG, "malformed"])
def test_legacy_simple_chat_groq_cannot_dispatch(monkeypatch, raw):
    from guardian.core.dependencies import _groq_complete

    monkeypatch.setenv(runtime.ENV, raw)
    with pytest.raises(HTTPException):
        _groq_complete([])


@pytest.mark.parametrize("method", ["transcribe", "synthesize"])
@pytest.mark.parametrize("raw", [CONFIG, "malformed"])
def test_remote_voice_cannot_delegate_unbounded_spend(monkeypatch, method, raw):
    from guardian.voice import client

    monkeypatch.setenv(runtime.ENV, raw)
    monkeypatch.setattr(client, "_service_url", lambda: "http://127.0.0.1:9999")
    monkeypatch.setattr(client, "enforce_audio_input_limits", lambda *a, **kw: None)
    network = Mock(side_effect=AssertionError("must not forward"))
    monkeypatch.setattr(client.requests, "post", network)
    with pytest.raises(HTTPException):
        if method == "transcribe":
            client.transcribe(b"test", "audio/wav")
        else:
            client.synthesize("test")
    network.assert_not_called()
