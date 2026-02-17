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
