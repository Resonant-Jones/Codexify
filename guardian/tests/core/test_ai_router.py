import pytest
from fastapi import HTTPException

from guardian.core.ai_router import chat_with_ai, stream_local
from guardian.core.config import Settings


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload
        self.status_code = 200
        self.text = ""

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


def _fake_settings(provider: str) -> Settings:
    return Settings(
        LLM_PROVIDER=provider,
        ALLOW_CLOUD_PROVIDERS=True,
        CODEXIFY_LOCAL_ONLY_MODE=False,
        CODEXIFY_EGRESS_ALLOWLIST="openai,groq,minimax",
        GROQ_API_KEY="groq-key",
        OPENAI_API_KEY="openai-key",
        MINIMAX_API_KEY="minimax-key",
        MINIMAX_API_BASE="https://api.minimax.local/v1",
        MINIMAX_API_FLAVOR="openai",
        MINIMAX_MODEL="minimax-chat",
        LLM_MODEL="moonshotai-kimi-k2-instruct-9050",
        DEFAULT_GROQ_MODEL="moonshotai-kimi-k2-instruct-9050",
        DEFAULT_OPENAI_MODEL="gpt-4o",
    )


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
    assert calls["json"]["model"] == "moonshotai-kimi-k2-instruct-9050"
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
        return _FakeResponse({"choices": [{"message": {"content": "ok"}}]})

    monkeypatch.setattr("guardian.core.ai_router.requests.post", fake_post)

    settings = _fake_settings("minimax")
    reply = chat_with_ai([{"role": "user", "content": "hi"}], settings=settings)

    assert "api.minimax.local/v1/chat/completions" in calls["url"]
    assert calls["json"]["model"] == "minimax-chat"
    assert calls["headers"]["Authorization"] == "Bearer minimax-key"
    assert calls["timeout"] == 60.0
    assert reply == "ok"


def test_chat_with_ai_minimax_anthropic_surface(monkeypatch):
    calls = {}

    def fake_post(url, json, headers, timeout):
        calls["url"] = url
        calls["json"] = json
        calls["headers"] = headers
        calls["timeout"] = timeout
        return _FakeResponse({"content": [{"type": "text", "text": "ok-a"}]})

    monkeypatch.setattr("guardian.core.ai_router.requests.post", fake_post)

    settings = _fake_settings("minimax")
    settings.MINIMAX_API_FLAVOR = "anthropic"
    settings.MINIMAX_API_BASE = "https://api.minimax.local/anthropic"
    settings.MINIMAX_MODEL = "MiniMax-M2.5"
    settings.MINIMAX_ANTHROPIC_VERSION = "2023-06-01"

    reply = chat_with_ai(
        [
            {"role": "system", "content": "Be precise."},
            {"role": "user", "content": "hi"},
        ],
        settings=settings,
    )

    assert "api.minimax.local/anthropic/v1/messages" in calls["url"]
    assert calls["json"]["model"] == "MiniMax-M2.5"
    assert calls["json"]["system"] == "Be precise."
    assert calls["json"]["messages"] == [
        {"role": "user", "content": [{"type": "text", "text": "hi"}]}
    ]
    assert calls["headers"]["x-api-key"] == "minimax-key"
    assert calls["headers"]["anthropic-version"] == "2023-06-01"
    assert calls["timeout"] == 60.0
    assert reply == "ok-a"


def test_chat_with_ai_groq_override_not_openai(monkeypatch):
    calls = {}

    def fake_post(url, json, headers, timeout):
        calls.setdefault("urls", []).append(url)
        return _FakeResponse({"choices": [{"message": {"content": "ok"}}]})

    monkeypatch.setattr("guardian.core.ai_router.requests.post", fake_post)

    settings = _fake_settings("groq")
    chat_with_ai(
        [{"role": "user", "content": "hi"}],
        settings=settings,
        provider="groq",
        model="custom-model",
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
