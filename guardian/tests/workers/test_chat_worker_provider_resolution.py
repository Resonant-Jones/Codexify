from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from guardian.core.config import LLMConfigError, Settings
from guardian.tasks.types import ChatCompletionTask
from guardian.workers import chat_worker


class _FakeChatLogDB:
    def get_chat_thread(self, thread_id: int):
        return {"id": thread_id, "user_id": "user-1", "project_id": 1}

    def list_messages(self, thread_id: int, limit: int, offset: int):
        return [
            {"id": 1, "role": "user", "content": "hello"},
        ]


class _FakeContextBroker:
    def __init__(self, *args, **kwargs):
        pass

    async def assemble(self, thread_id, query, depth_mode, user_id):
        return ({}, None)


def _fake_settings() -> Settings:
    return Settings(
        LLM_PROVIDER="local",
        ALLOW_CLOUD_PROVIDERS=True,
        CODEXIFY_LOCAL_ONLY_MODE=False,
        CODEXIFY_EGRESS_ALLOWLIST="openai,groq,minimax",
        LLM_MODEL="local-model",
        LOCAL_LLM_MODEL="local-model",
        DEFAULT_LOCAL_MODEL="local-model",
        GROQ_API_KEY="groq-key",
        OPENAI_API_KEY="openai-key",
        MINIMAX_API_KEY="minimax-key",
        MINIMAX_API_BASE="https://api.minimax.local/v1",
        MINIMAX_MODEL="minimax-chat",
    )


def _fake_profile(
    *,
    provider_override: str | None = None,
    model_override: str | None = None,
):
    return SimpleNamespace(
        active_profile_id="profile-1",
        profile_id="profile-1",
        provider_override=provider_override,
        model_override=model_override,
        mode="cloud",
        temperature_override=None,
    )


def _patch_common(
    monkeypatch: pytest.MonkeyPatch,
    *,
    settings: Settings,
    profile,
    resolved_provider: str | None,
    first_provider: str | None = "local",
    first_model: str | None = "local-model",
) -> None:
    monkeypatch.setattr(chat_worker, "get_settings", lambda: settings)
    monkeypatch.setattr(
        chat_worker.dependencies, "CHAT_PROVIDER", "local", raising=False
    )
    monkeypatch.setattr(
        chat_worker.dependencies, "chatlog_db", _FakeChatLogDB(), raising=False
    )
    monkeypatch.setattr(
        chat_worker.dependencies, "_vector_store", None, raising=False
    )
    monkeypatch.setattr(
        chat_worker.dependencies, "_memory_store", None, raising=False
    )
    monkeypatch.setattr(
        chat_worker.dependencies, "_sensors", None, raising=False
    )
    monkeypatch.setattr(
        chat_worker.dependencies, "DEFAULT_MODEL", "local-model", raising=False
    )
    monkeypatch.setattr(
        chat_worker,
        "resolve_thread_system_profile",
        lambda thread_id, chatlog_db=None: profile,
    )
    monkeypatch.setattr(
        chat_worker,
        "resolve_provider_for_model",
        lambda model_id, settings=None: resolved_provider,
    )
    monkeypatch.setattr(
        chat_worker,
        "first_enabled_provider",
        lambda settings=None: first_provider,
    )
    monkeypatch.setattr(
        chat_worker,
        "first_model_for_provider",
        lambda provider_id, settings=None: first_model,
    )
    monkeypatch.setattr(
        chat_worker,
        "validate_llm_config",
        lambda settings, provider_override=None: None,
    )
    monkeypatch.setattr(chat_worker, "ContextBroker", _FakeContextBroker)
    monkeypatch.setattr(chat_worker, "build_guardian_system_prompt", None)
    monkeypatch.setattr(
        chat_worker, "build_context_system_message", lambda _: ""
    )


def test_explicit_provider_wins_over_profile_override(monkeypatch):
    settings = _fake_settings()
    _patch_common(
        monkeypatch,
        settings=settings,
        profile=_fake_profile(provider_override="openai"),
        resolved_provider=None,
    )

    task = ChatCompletionTask(
        thread_id=1,
        provider="groq",
        model=None,
        max_context=10,
    )

    _, provider, _, _, _, _, _ = asyncio.run(
        chat_worker._build_messages_for_llm(task)
    )
    assert provider == "groq"


def test_explicit_model_unavailable_fails_instead_of_fallback(monkeypatch):
    settings = _fake_settings()
    _patch_common(
        monkeypatch,
        settings=settings,
        profile=_fake_profile(provider_override="openai"),
        resolved_provider=None,
        first_provider="openai",
        first_model="gpt-4o",
    )

    task = ChatCompletionTask(
        thread_id=1,
        provider="groq",
        model="missing-model",
        max_context=10,
    )

    with pytest.raises(
        LLMConfigError, match="Requested model 'missing-model' is not available"
    ):
        asyncio.run(chat_worker._build_messages_for_llm(task))


def test_explicit_model_selects_provider_even_with_profile_override(
    monkeypatch,
):
    settings = _fake_settings()
    _patch_common(
        monkeypatch,
        settings=settings,
        profile=_fake_profile(provider_override="openai"),
        resolved_provider="groq",
    )

    task = ChatCompletionTask(
        thread_id=1,
        provider=None,
        model="moonshotai/kimi-k2-instruct-0905",
        max_context=10,
    )

    _, provider, model, _, _, _, _ = asyncio.run(
        chat_worker._build_messages_for_llm(task)
    )
    assert provider == "groq"
    assert model == "moonshotai/kimi-k2-instruct-0905"


def test_resolution_uses_degraded_model_fallback_on_classification_failure(
    monkeypatch,
):
    settings = _fake_settings()
    _patch_common(
        monkeypatch,
        settings=settings,
        profile=_fake_profile(provider_override="openai"),
        resolved_provider=None,
        first_provider="groq",
        first_model=None,
    )
    monkeypatch.setattr(
        chat_worker,
        "validate_provider_model_selection",
        lambda **kwargs: (
            False,
            "Provider model index returned no chat-capable models",
        ),
    )
    monkeypatch.setattr(
        chat_worker,
        "resolve_provider_capability",
        lambda provider_id, settings: {
            "models": [
                {"id": "recovered-model"},
                {"id": "backup-model"},
            ]
        },
    )

    task = ChatCompletionTask(
        thread_id=1,
        provider="groq",
        model=None,
        max_context=10,
    )

    _, provider, model, _, _, _, _ = asyncio.run(
        chat_worker._build_messages_for_llm(task)
    )
    assert provider == "groq"
    assert model == "recovered-model"
