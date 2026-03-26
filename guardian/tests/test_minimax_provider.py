from __future__ import annotations

from types import SimpleNamespace

import pytest

from guardian.core.config import LLMConfigError, Settings, validate_llm_config
from guardian.providers.minimax_adapter import MiniMaxAdapter
from guardian.providers.registry import ProviderRegistry


def _allow_minimax_egress(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CODEXIFY_LOCAL_ONLY_MODE", "false")
    monkeypatch.setenv("ALLOW_CLOUD_PROVIDERS", "true")
    monkeypatch.setenv("CODEXIFY_EGRESS_ALLOWLIST", "minimax")


def test_registry_loads_minimax_when_env_is_set(monkeypatch):
    _allow_minimax_egress(monkeypatch)
    monkeypatch.setenv("MINIMAX_API_KEY", "minimax-test-key")
    monkeypatch.setenv("MINIMAX_API_BASE", "https://api.minimax.local/v1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    class _DummyOpenAI:
        def __init__(self, *, api_key, base_url):
            self.api_key = api_key
            self.base_url = base_url

    monkeypatch.setattr(
        "guardian.providers.minimax_adapter.OpenAI", _DummyOpenAI
    )

    registry = ProviderRegistry()
    capabilities = registry.capabilities()

    assert "minimax" in capabilities["chat"]
    assert registry.get_chat("minimax").name == "minimax"


def test_validate_llm_config_minimax_missing_required_env(monkeypatch):
    monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
    monkeypatch.delenv("MINIMAX_API_BASE", raising=False)

    settings = Settings(
        LLM_PROVIDER="minimax",
        ALLOW_CLOUD_PROVIDERS=True,
        MINIMAX_API_KEY=None,
        MINIMAX_API_BASE=None,
    )

    with pytest.raises(LLMConfigError) as exc:
        validate_llm_config(settings)

    message = str(exc.value)
    assert "LLM_PROVIDER is 'minimax'" in message
    assert "MINIMAX_API_KEY" in message
    assert "MINIMAX_API_BASE" in message


def test_validate_llm_config_minimax_invalid_api_flavor():
    settings = Settings(
        LLM_PROVIDER="minimax",
        ALLOW_CLOUD_PROVIDERS=True,
        MINIMAX_API_KEY="minimax-key",
        MINIMAX_API_BASE="https://api.minimax.local/v1",
        MINIMAX_API_FLAVOR="invalid",
    )

    with pytest.raises(LLMConfigError) as exc:
        validate_llm_config(settings)

    assert "MINIMAX_API_FLAVOR" in str(exc.value)


def test_minimax_adapter_uses_openai_compatible_client(monkeypatch):
    _allow_minimax_egress(monkeypatch)

    captured: dict[str, object] = {}
    calls: list[dict[str, object]] = []

    class _DummyCompletions:
        def create(self, **kwargs):
            calls.append(kwargs)
            if kwargs.get("stream"):
                return iter(
                    [
                        SimpleNamespace(
                            choices=[
                                SimpleNamespace(
                                    delta=SimpleNamespace(content="hello")
                                )
                            ]
                        ),
                        SimpleNamespace(
                            choices=[
                                SimpleNamespace(
                                    delta=SimpleNamespace(content=" world")
                                )
                            ]
                        ),
                    ]
                )
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content="generated reply")
                    )
                ]
            )

    class _DummyOpenAI:
        def __init__(self, *, api_key, base_url):
            captured["api_key"] = api_key
            captured["base_url"] = base_url
            self.chat = SimpleNamespace(completions=_DummyCompletions())

    monkeypatch.setattr(
        "guardian.providers.minimax_adapter.OpenAI", _DummyOpenAI
    )

    adapter = MiniMaxAdapter(
        api_key="minimax-secret",
        base_url="https://api.minimax.local/v1",
        default_model="minimax-chat",
        timeout=45,
        api_flavor="openai",
    )
    reply = adapter.generate(
        "ignored prompt",
        messages=[
            {"role": "system", "content": "You are concise."},
            {"role": "user", "content": "Say hi"},
        ],
    )
    chunks = list(
        adapter.stream(
            "ignored prompt",
            model="minimax-override",
            messages=[{"role": "user", "content": "stream this"}],
        )
    )

    assert captured["api_key"] == "minimax-secret"
    assert captured["base_url"] == "https://api.minimax.local/v1"

    assert reply == "generated reply"
    assert "".join(chunks) == "hello world"

    assert len(calls) == 2
    assert calls[0]["model"] == "minimax-chat"
    assert calls[0]["messages"] == [
        {"role": "system", "content": "You are concise."},
        {"role": "user", "content": "Say hi"},
    ]
    assert calls[0]["timeout"] == 45

    assert calls[1]["stream"] is True
    assert calls[1]["model"] == "minimax-override"
    assert calls[1]["messages"] == [
        {"role": "user", "content": "stream this"},
    ]


def test_minimax_adapter_supports_anthropic_compatible_http(monkeypatch):
    _allow_minimax_egress(monkeypatch)
    monkeypatch.setattr("guardian.providers.minimax_adapter.OpenAI", None)

    calls: list[dict[str, object]] = []

    class _DummyResponse:
        def __init__(
            self,
            *,
            payload: dict | None = None,
            lines: list[str] | None = None,
            status_code: int = 200,
        ):
            self._payload = payload or {}
            self._lines = lines or []
            self.status_code = status_code
            self.text = ""

        def json(self):
            return self._payload

        def iter_lines(self, decode_unicode=True):
            _ = decode_unicode
            yield from self._lines

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_post(url, json, headers, timeout, stream=False):
        calls.append(
            {
                "url": url,
                "json": json,
                "headers": headers,
                "timeout": timeout,
                "stream": stream,
            }
        )
        if stream:
            return _DummyResponse(
                lines=[
                    "event: message_start",
                    'data: {"type":"content_block_delta","delta":{"type":"text_delta","text":"hello"}}',
                    'data: {"type":"content_block_delta","delta":{"text":" world"}}',
                    'data: {"type":"message_stop"}',
                ]
            )
        return _DummyResponse(
            payload={"content": [{"type": "text", "text": "generated reply"}]}
        )

    monkeypatch.setattr(
        "guardian.providers.minimax_adapter.requests.post", fake_post
    )

    adapter = MiniMaxAdapter(
        api_key="minimax-secret",
        base_url="https://api.minimax.local/anthropic",
        default_model="MiniMax-M2.5",
        timeout=45,
        api_flavor="anthropic",
        anthropic_version="2023-06-01",
    )
    reply = adapter.generate(
        "ignored prompt",
        messages=[
            {"role": "system", "content": "You are concise."},
            {"role": "user", "content": "Say hi"},
        ],
        temperature=0.2,
        max_tokens=111,
    )
    chunks = list(
        adapter.stream(
            "ignored prompt",
            model="MiniMax-M2.5",
            messages=[{"role": "user", "content": "stream this"}],
        )
    )

    assert reply == "generated reply"
    assert "".join(chunks) == "hello world"
    assert len(calls) == 2

    assert calls[0]["url"] == "https://api.minimax.local/anthropic/v1/messages"
    assert calls[0]["headers"]["x-api-key"] == "minimax-secret"
    assert calls[0]["headers"]["anthropic-version"] == "2023-06-01"
    assert calls[0]["json"]["model"] == "MiniMax-M2.5"
    assert calls[0]["json"]["system"] == "You are concise."
    assert calls[0]["json"]["messages"] == [
        {
            "role": "user",
            "content": [{"type": "text", "text": "Say hi"}],
        }
    ]
    assert calls[0]["json"]["max_tokens"] == 111
    assert calls[0]["stream"] is False

    assert calls[1]["stream"] is True
    assert calls[1]["json"]["messages"] == [
        {
            "role": "user",
            "content": [{"type": "text", "text": "stream this"}],
        }
    ]
