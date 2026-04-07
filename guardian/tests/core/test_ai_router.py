import json

import pytest
from fastapi import HTTPException

from guardian.core.ai_router import chat_with_ai, stream_local
from guardian.core.config import Settings


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload
        self.status_code = 200
        self.text = ""
        self.content = json.dumps(payload).encode("utf-8")

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _FakeStreamingResponse:
    def __init__(self, lines):
        self._lines = lines
        self.status_code = 200
        self.text = ""

    def raise_for_status(self):
        return None

    def iter_lines(self, decode_unicode=False):
        _ = decode_unicode
        yield from self._lines

    def close(self):
        return None


class _MockDiscoveryResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload


def _fake_settings(provider: str) -> Settings:
    return Settings(
        LLM_PROVIDER=provider,
        ALLOW_CLOUD_PROVIDERS=True,
        CODEXIFY_LOCAL_ONLY_MODE=False,
        CODEXIFY_EGRESS_ALLOWLIST="openai,groq,minimax",
        GROQ_API_KEY="groq-key",
        GROQ_MODEL="moonshotai/kimi-k2-instruct-0905",
        OPENAI_API_KEY="openai-key",
        MINIMAX_API_KEY="minimax-key",
        MINIMAX_API_BASE="https://api.minimax.local/anthropic",
        MINIMAX_API_FLAVOR="anthropic",
        MINIMAX_MODEL="MiniMax-M2.5",
        LLM_MODEL="moonshotai/kimi-k2-instruct-0905",
        DEFAULT_GROQ_MODEL="moonshotai/kimi-k2-instruct-0905",
        DEFAULT_OPENAI_MODEL="gpt-4o",
    )


def _mock_minimax_model_index(url, headers, timeout):
    assert url == "https://api.minimax.local/v1/models"
    assert timeout == 3.0
    assert headers["Authorization"] == "Bearer minimax-key"
    return _MockDiscoveryResponse({"data": [{"id": "minimax-chat"}]})


def test_chat_with_ai_groq_default(monkeypatch):
    calls = {}

    def fake_post(url, json, headers, timeout):
        calls["url"] = url
        calls["json"] = json
        return _FakeResponse({"choices": [{"message": {"content": "ok"}}]})

    monkeypatch.setattr("guardian.core.ai_router.requests.post", fake_post)

    settings = _fake_settings("groq")
    reply = chat_with_ai([{"role": "user", "content": "hi"}], settings=settings)

    assert "api.groq.com/openai/v1/chat/completions" in calls["url"]
    assert calls["json"]["model"] == "moonshotai/kimi-k2-instruct-0905"
    assert reply == "ok"


def test_chat_with_ai_groq_prefers_groq_model_over_generic_llm_model(
    monkeypatch,
):
    calls = {}

    def fake_post(url, json, headers, timeout):
        calls["url"] = url
        calls["json"] = json
        return _FakeResponse({"choices": [{"message": {"content": "ok"}}]})

    monkeypatch.setattr("guardian.core.ai_router.requests.post", fake_post)

    settings = _fake_settings("groq")
    settings.LLM_MODEL = "qwen3.5:27b"
    settings.GROQ_MODEL = "moonshotai/kimi-k2-instruct-0905"

    reply = chat_with_ai([{"role": "user", "content": "hi"}], settings=settings)

    assert "api.groq.com/openai/v1/chat/completions" in calls["url"]
    assert calls["json"]["model"] == "moonshotai/kimi-k2-instruct-0905"
    assert reply == "ok"


def test_chat_with_ai_openai_default(monkeypatch):
    calls = {}

    def fake_post(url, json, headers, timeout):
        calls["url"] = url
        calls["json"] = json
        return _FakeResponse({"choices": [{"message": {"content": "ok"}}]})

    monkeypatch.setattr("guardian.core.ai_router.requests.post", fake_post)

    settings = _fake_settings("openai")
    reply = chat_with_ai([{"role": "user", "content": "hi"}], settings=settings)

    assert "api.openai.com/v1/chat/completions" in calls["url"]
    assert calls["json"]["model"] == "gpt-4o"
    assert reply == "ok"


def test_chat_with_ai_minimax_default(monkeypatch):
    calls = {}

    def fake_post(url, json, headers, timeout):
        calls["url"] = url
        calls["json"] = json
        calls["headers"] = headers
        calls["timeout"] = timeout
        return _FakeResponse({"content": [{"type": "text", "text": "ok"}]})

    monkeypatch.setattr("guardian.core.ai_router.requests.post", fake_post)

    settings = _fake_settings("minimax")
    reply = chat_with_ai([{"role": "user", "content": "hi"}], settings=settings)

    assert "api.minimax.local/anthropic/v1/messages" in calls["url"]
    assert calls["json"]["model"] == "MiniMax-M2.5"
    assert calls["headers"]["x-api-key"] == "minimax-key"
    assert calls["headers"]["anthropic-version"] == "2023-06-01"
    assert calls["timeout"] == 60.0
    assert reply == "ok"
    assert getattr(reply, "provider", None) == "minimax"
    assert getattr(reply, "raw_payload", {}).get("content")


def test_chat_with_ai_minimax_anthropic_preserves_image_blocks(monkeypatch):
    calls = {}

    def fake_post(url, json, headers, timeout):
        calls["url"] = url
        calls["json"] = json
        calls["headers"] = headers
        calls["timeout"] = timeout
        return _FakeResponse({"content": [{"type": "text", "text": "ok"}]})

    monkeypatch.setattr("guardian.core.ai_router.requests.post", fake_post)
    monkeypatch.setattr(
        "guardian.core.provider_registry.requests.get",
        lambda url, headers, timeout: _MockDiscoveryResponse(
            {"data": [{"id": "MiniMax-M2.5"}]}
        ),
    )

    settings = _fake_settings("minimax")
    reply = chat_with_ai(
        [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": "https://example.test/image.png"},
                    },
                    {"type": "text", "text": "Describe the image."},
                ],
            }
        ],
        provider="minimax",
        model="MiniMax-M2.5",
        settings=settings,
    )

    assert "api.minimax.local/anthropic/v1/messages" in calls["url"]
    assert calls["json"]["messages"] == [
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "url",
                        "url": "https://example.test/image.png",
                    },
                },
                {"type": "text", "text": "Describe the image."},
            ],
        }
    ]
    assert reply == "ok"


def test_chat_with_ai_minimax_anthropic_surface(monkeypatch):
    calls = {}

    def fake_post(url, json, headers, timeout):
        calls["url"] = url
        calls["json"] = json
        calls["headers"] = headers
        calls["timeout"] = timeout
        return _FakeResponse({"choices": [{"message": {"content": "ok-a"}}]})

    monkeypatch.setattr("guardian.core.ai_router.requests.post", fake_post)

    settings = _fake_settings("minimax")
    settings.MINIMAX_API_FLAVOR = "openai"
    settings.MINIMAX_API_BASE = "https://api.minimax.local/v1"
    settings.MINIMAX_MODEL = "minimax-chat"
    monkeypatch.setattr(
        "guardian.core.provider_registry.requests.get",
        lambda url, headers, timeout: _MockDiscoveryResponse(
            {"data": [{"id": "minimax-chat"}]}
        ),
    )

    reply = chat_with_ai(
        [
            {"role": "system", "content": "Be precise."},
            {"role": "user", "content": "hi"},
        ],
        settings=settings,
    )

    assert "api.minimax.local/v1/chat/completions" in calls["url"]
    assert calls["json"]["model"] == "minimax-chat"
    assert calls["json"]["messages"] == [
        {"role": "system", "content": "Be precise."},
        {"role": "user", "content": "hi"},
    ]
    assert calls["headers"]["Authorization"] == "Bearer minimax-key"
    assert calls["timeout"] == 60.0
    assert reply == "ok-a"


def test_chat_with_ai_rejects_undiscovered_minimax_model(monkeypatch):
    def fake_post(url, json, headers, timeout):  # pragma: no cover
        return _FakeResponse({"choices": [{"message": {"content": "ok"}}]})

    monkeypatch.setattr("guardian.core.ai_router.requests.post", fake_post)
    monkeypatch.setattr(
        "guardian.core.provider_registry.requests.get",
        lambda url, headers, timeout: _MockDiscoveryResponse(
            {"data": [{"id": "minimax-chat"}]}
        ),
    )

    settings = _fake_settings("minimax")

    with pytest.raises(HTTPException) as exc:
        chat_with_ai(
            [{"role": "user", "content": "hi"}],
            provider="minimax",
            model="bogus-model",
            settings=settings,
        )

    assert exc.value.status_code == 400
    assert "bogus-model" in str(exc.value.detail)


def test_chat_with_ai_groq_override_not_openai(monkeypatch):
    calls = {}

    def fake_post(url, json, headers, timeout):
        calls.setdefault("urls", []).append(url)
        return _FakeResponse({"choices": [{"message": {"content": "ok"}}]})

    monkeypatch.setattr("guardian.core.ai_router.requests.post", fake_post)
    monkeypatch.setattr(
        "guardian.core.provider_registry.requests.get",
        lambda url, headers, timeout: _MockDiscoveryResponse(
            {"data": [{"id": "moonshotai/kimi-k2-instruct-0905"}]}
        ),
    )

    settings = _fake_settings("groq")
    chat_with_ai(
        [{"role": "user", "content": "hi"}],
        settings=settings,
        provider="groq",
        model="moonshotai/kimi-k2-instruct-0905",
    )

    assert any(
        "api.groq.com/openai/v1/chat/completions" in u for u in calls["urls"]
    )
    assert not any("api.openai.com" in u for u in calls["urls"])


def test_chat_with_ai_openai_blocked_when_local_only_enabled(monkeypatch):
    def fake_post(url, json, headers, timeout):  # pragma: no cover
        return _FakeResponse({"choices": [{"message": {"content": "ok"}}]})

    monkeypatch.setattr("guardian.core.ai_router.requests.post", fake_post)

    settings = Settings(
        LLM_PROVIDER="openai",
        ALLOW_CLOUD_PROVIDERS=True,
        CODEXIFY_LOCAL_ONLY_MODE=True,
        CODEXIFY_EGRESS_ALLOWLIST="openai",
        OPENAI_API_KEY="openai-key",
    )

    with pytest.raises(HTTPException) as exc:
        chat_with_ai([{"role": "user", "content": "hi"}], settings=settings)

    assert exc.value.status_code == 403
    assert "LOCAL_ONLY_MODE" in str(exc.value.detail)


def test_stream_local_parses_openai_sse_chunks(monkeypatch):
    def fake_post(url, json, headers, stream, timeout):
        _ = (url, json, headers, stream, timeout)
        return _FakeStreamingResponse(
            [
                b'data: {"choices":[{"delta":{"content":"Hi"}}]}',
                b'data: {"choices":[{"delta":{"content":"!"}}]}',
                b"data: [DONE]",
            ]
        )

    monkeypatch.setattr("guardian.core.ai_router.requests.post", fake_post)

    settings = _fake_settings("local")
    settings.LOCAL_BASE_URL = "http://127.0.0.1:11434"
    tokens = list(
        stream_local(
            [{"role": "user", "content": "hello"}],
            "ministral-3:3b",
            settings=settings,
        )
    )
    assert "".join(tokens) == "Hi!"


def test_stream_local_parses_ollama_chat_chunks(monkeypatch):
    def fake_post(url, json, headers, stream, timeout):
        _ = (url, json, headers, stream, timeout)
        return _FakeStreamingResponse(
            [
                b'{"message":{"role":"assistant","content":"Hel"},"done":false}',
                b'{"message":{"role":"assistant","content":"lo"},"done":false}',
                b'{"done":true}',
            ]
        )

    monkeypatch.setattr("guardian.core.ai_router.requests.post", fake_post)

    settings = _fake_settings("local")
    settings.LOCAL_BASE_URL = "http://127.0.0.1:11434"
    tokens = list(
        stream_local(
            [{"role": "user", "content": "hello"}],
            "ministral-3:3b",
            settings=settings,
        )
    )
    assert "".join(tokens) == "Hello"


def test_stream_local_keeps_multimodal_payload_and_prefers_compat_endpoint(
    monkeypatch,
):
    calls = {}

    def fake_post(url, json, headers, stream, timeout):
        calls["url"] = url
        calls["json"] = json
        calls["headers"] = headers
        calls["stream"] = stream
        calls["timeout"] = timeout
        return _FakeStreamingResponse(
            [
                b'data: {"choices":[{"delta":{"content":"Vi"}}]}',
                b'data: {"choices":[{"delta":{"content":"sion"}}]}',
                b"data: [DONE]",
            ]
        )

    monkeypatch.setattr("guardian.core.ai_router.requests.post", fake_post)

    settings = _fake_settings("local")
    settings.LOCAL_BASE_URL = "http://127.0.0.1:11434"

    tokens = list(
        stream_local(
            [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Describe this image."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": "https://example.test/scene.png"
                            },
                        },
                    ],
                }
            ],
            "qwen3.5:4b",
            settings=settings,
        )
    )

    assert "".join(tokens) == "Vision"
    assert calls["url"].endswith("/v1/chat/completions")
    assert isinstance(calls["json"]["messages"][-1]["content"], list)
    assert any(
        block.get("type") == "image_url"
        for block in calls["json"]["messages"][-1]["content"]
        if isinstance(block, dict)
    )
    assert any(
        block.get("type") == "text"
        and "/no_think" in str(block.get("text") or "")
        for block in calls["json"]["messages"][-1]["content"]
        if isinstance(block, dict)
    )


def test_call_local_injects_qwen_no_think_instruction(monkeypatch):
    calls = {}

    def fake_post(url, json, headers, timeout):
        calls["url"] = url
        calls["json"] = json
        calls["headers"] = headers
        calls["timeout"] = timeout
        return _FakeResponse({"message": {"content": "ok"}})

    monkeypatch.setattr("guardian.core.ai_router.requests.post", fake_post)

    settings = _fake_settings("local")
    settings.LOCAL_BASE_URL = "http://127.0.0.1:11434"

    reply = chat_with_ai(
        [{"role": "user", "content": "hello"}],
        provider="local",
        model="qwen3:4b",
        settings=settings,
    )

    assert reply == "ok"
    assert calls["json"]["messages"][-1]["role"] == "user"
    assert calls["json"]["messages"][-1]["content"].endswith("/no_think")


def test_call_local_injects_qwen_3_5_no_think_instruction(monkeypatch):
    calls = {}

    def fake_post(url, json, headers, timeout):
        calls["url"] = url
        calls["json"] = json
        _ = (headers, timeout)
        return _FakeResponse({"message": {"content": "ok"}})

    monkeypatch.setattr("guardian.core.ai_router.requests.post", fake_post)

    settings = _fake_settings("local")
    settings.LOCAL_BASE_URL = "http://127.0.0.1:11434"

    reply = chat_with_ai(
        [{"role": "user", "content": "hello"}],
        provider="local",
        model="qwen3.5:4b",
        settings=settings,
    )

    assert reply == "ok"
    assert calls["json"]["messages"][-1]["role"] == "user"
    assert calls["json"]["messages"][-1]["content"].endswith("/no_think")


def test_call_local_respects_explicit_qwen_think_instruction(monkeypatch):
    calls = {}

    def fake_post(url, json, headers, timeout):
        calls["url"] = url
        calls["json"] = json
        _ = (headers, timeout)
        return _FakeResponse({"message": {"content": "ok"}})

    monkeypatch.setattr("guardian.core.ai_router.requests.post", fake_post)

    settings = _fake_settings("local")
    settings.LOCAL_BASE_URL = "http://127.0.0.1:11434"

    reply = chat_with_ai(
        [{"role": "user", "content": "hello\n\n/think"}],
        provider="local",
        model="qwen3.5:4b",
        settings=settings,
    )

    assert reply == "ok"
    assert calls["json"]["messages"] == [
        {"role": "user", "content": "hello\n\n/think"}
    ]


def test_stream_local_skips_no_think_for_fixed_mode_qwen_release(monkeypatch):
    calls = {}

    def fake_post(url, json, headers, stream, timeout):
        calls["url"] = url
        calls["json"] = json
        _ = (headers, stream, timeout)
        return _FakeStreamingResponse(
            [
                b'{"message":{"role":"assistant","content":"Hi"},"done":false}',
                b'{"done":true}',
            ]
        )

    monkeypatch.setattr("guardian.core.ai_router.requests.post", fake_post)

    settings = _fake_settings("local")
    settings.LOCAL_BASE_URL = "http://127.0.0.1:11434"

    tokens = list(
        stream_local(
            [{"role": "user", "content": "hello"}],
            "qwen3-thinking-2507:30b",
            settings=settings,
        )
    )

    assert "".join(tokens) == "Hi"
    assert all(
        "/no_think" not in str(message.get("content") or "")
        for message in calls["json"]["messages"]
    )


def test_stream_local_skips_no_think_for_fixed_mode_qwen_3_5_release(
    monkeypatch,
):
    calls = {}

    def fake_post(url, json, headers, stream, timeout):
        calls["url"] = url
        calls["json"] = json
        _ = (headers, stream, timeout)
        return _FakeStreamingResponse(
            [
                b'{"message":{"role":"assistant","content":"Hi"},"done":false}',
                b'{"done":true}',
            ]
        )

    monkeypatch.setattr("guardian.core.ai_router.requests.post", fake_post)

    settings = _fake_settings("local")
    settings.LOCAL_BASE_URL = "http://127.0.0.1:11434"

    tokens = list(
        stream_local(
            [{"role": "user", "content": "hello"}],
            "qwen3.5-thinking-2507:30b",
            settings=settings,
        )
    )

    assert "".join(tokens) == "Hi"
    assert all(
        "/no_think" not in str(message.get("content") or "")
        for message in calls["json"]["messages"]
    )
