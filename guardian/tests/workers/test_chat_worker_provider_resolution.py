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
        lambda thread_id, chatlog_db=None, accepted_selection=None: profile,
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
        user_id="local",
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
        user_id="local",
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
        user_id="local",
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
        user_id="local",
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


@pytest.fixture
def accepted_runtime(monkeypatch):
    from guardian.cognition.system_profiles import resolver, store
    from guardian.core import chat_completion_service as service
    from guardian.tests.test_persona_profile_runtime import (
        _fake_retrieval_plan,
        _persona_profile_session,
    )
    from guardian.tests.test_persona_profile_runtime import (
        _FakeChatLogDB as ProfileDB,
    )

    with _persona_profile_session():
        store.create_persona_profile(
            account_id="account-a",
            profile_id="axis",
            name="Axis One",
            system_prompt="Historical instructions.",
            model_provider="openai",
            model_id="historical-model",
            temperature=0.2,
        )
        db = ProfileDB(
            {
                "id": 1,
                "user_id": "account-a",
                "active_profile_id": "axis",
                "active_profile_revision": 1,
            },
            [{"id": 1, "role": "user", "content": "hello"}],
        )
        _patch_common(
            monkeypatch, settings=_fake_settings(), profile=None, resolved_provider=None
        )
        monkeypatch.setattr(chat_worker.dependencies, "chatlog_db", db)
        monkeypatch.setattr(
            chat_worker,
            "resolve_thread_system_profile",
            resolver.resolve_thread_system_profile,
        )
        monkeypatch.setattr(
            chat_worker,
            "validate_provider_model_selection",
            lambda **_kwargs: (True, None),
        )
        monkeypatch.setattr(
            chat_worker,
            "build_guardian_system_prompt",
            lambda **kwargs: (
                kwargs["profile"].system_prompt or "Default instructions.",
                {"estimated_tokens": 1},
            ),
        )
        monkeypatch.setattr(
            service, "resolve_retrieval_plan", lambda *_a, **_k: _fake_retrieval_plan()
        )
        # Restore global compatibility seams after exercising the real worker wrapper.
        for name in (
            "get_settings",
            "validate_llm_config",
            "ContextBroker",
            "chat_with_ai",
            "stream_local",
            "build_guardian_system_prompt",
            "build_context_system_message_with_meta",
        ):
            monkeypatch.setattr(service, name, getattr(service, name))

        async def assemble(*_args, **_kwargs):
            return {}, None

        monkeypatch.setattr(service, "_assemble_context_bundle", assemble)
        calls = []

        def infer(messages, **kwargs):
            calls.append(
                (
                    messages[0]["content"].split("\n\nCompletion targeting guidance:")[
                        0
                    ],
                    kwargs.get("provider"),
                    kwargs.get("model"),
                    kwargs.get("temperature"),
                )
            )
            return "assistant answer"

        monkeypatch.setattr(chat_worker, "chat_with_ai", infer)
        yield db, store, resolver, calls


def test_worker_executes_accepted_revision_across_switch_and_retry(
    monkeypatch, accepted_runtime
):
    from guardian.tasks.types import PersonaSelectionSnapshot
    from guardian.tests.test_persona_profile_runtime import _accept_task

    db, store, resolver, calls = accepted_runtime
    task_a = _accept_task(
        monkeypatch, db, ChatCompletionTask(user_id="account-a", thread_id=1)
    )
    store.update_persona_profile(
        "axis",
        account_id="account-a",
        name="Axis Two",
        system_prompt="Current instructions.",
        model_provider="groq",
        model_id="current-model",
        temperature=0.8,
    )
    resolver.switch_thread_profile(1, "axis", chatlog_db=db)
    task_b = _accept_task(
        monkeypatch, db, ChatCompletionTask(user_id="account-a", thread_id=1)
    )
    chat_worker.run_chat_completion_task(task_a, persist_assistant_message=False)
    assert calls[-1] == ("Historical instructions.", "openai", "historical-model", 0.2)
    chat_worker.run_chat_completion_task(task_b, persist_assistant_message=False)
    assert calls[-1] == ("Current instructions.", "groq", "current-model", 0.8)
    resolver.switch_thread_profile(1, "local_mode", chatlog_db=db)
    task_a.attempt_id = "another-attempt"
    chat_worker.run_chat_completion_task(task_a, persist_assistant_message=False)
    assert calls[-1] == ("Historical instructions.", "openai", "historical-model", 0.2)
    assert task_a.persona_selection_snapshot == PersonaSelectionSnapshot("axis", 1)


@pytest.mark.parametrize("profile_id", [None, "env-profile", "flow"])
def test_worker_preserves_accepted_revisionless_selection(
    monkeypatch, accepted_runtime, profile_id
):
    from guardian.tests.test_persona_profile_runtime import _accept_task

    db, _store, resolver, calls = accepted_runtime
    monkeypatch.setenv(
        "GUARDIAN_SYSTEM_PROFILES_JSON",
        '[{"profile_id":"env-profile","provider_override":"openai","model_override":"env-model","system_prompt":"Env instructions.","temperature_override":0.4}]',
    )
    db._thread.update(
        active_profile_id=profile_id,
        active_profile_revision=None,
        metadata={
            "profile_overrides": {
                "flow": {
                    "profile_id": "flow",
                    "provider_override": "openai",
                    "model_override": "flow-model",
                    "system_prompt": "Flow instructions.",
                    "temperature_override": 0.6,
                }
            }
        },
    )
    task = _accept_task(
        monkeypatch,
        db,
        ChatCompletionTask(
            user_id="account-a",
            thread_id=1,
            # Explicit routing keeps no-profile proof independent of local streaming.
            provider="openai" if profile_id is None else None,
        ),
    )
    resolver.switch_thread_profile(1, "axis", chatlog_db=db)
    chat_worker.run_chat_completion_task(task, persist_assistant_message=False)
    assert (
        calls[-1][0]
        == {
            None: "Default instructions.",
            "env-profile": "Env instructions.",
            "flow": "Flow instructions.",
        }[profile_id]
    )
    if profile_id is not None:
        assert calls[-1][1:] == (
            "openai",
            {"env-profile": "env-model", "flow": "flow-model"}[profile_id],
            {"env-profile": 0.4, "flow": 0.6}[profile_id],
        )


def test_worker_legacy_task_follows_thread_selection(accepted_runtime):
    db, store, resolver, calls = accepted_runtime
    task = ChatCompletionTask(user_id="account-a", thread_id=1)
    store.update_persona_profile(
        "axis", account_id="account-a", system_prompt="Current instructions."
    )
    resolver.switch_thread_profile(1, "axis", chatlog_db=db)
    chat_worker.run_chat_completion_task(task, persist_assistant_message=False)
    assert task.persona_selection_snapshot is None
    assert calls[-1] == ("Current instructions.", "openai", "historical-model", 0.2)


@pytest.mark.parametrize("owner,revision", [("account-a", 99), ("account-b", 1)])
def test_worker_unavailable_accepted_revision_never_invokes_provider(
    accepted_runtime, owner, revision
):
    from guardian.tasks.types import PersonaSelectionSnapshot

    db, _store, resolver, calls = accepted_runtime
    db._thread.update(
        user_id=owner, active_profile_id="local_mode", active_profile_revision=None
    )
    task = ChatCompletionTask(
        user_id="account-a",
        thread_id=1,
        persona_selection_snapshot=PersonaSelectionSnapshot("axis", revision),
    )
    with pytest.raises(resolver.ProfileResolutionError):
        chat_worker.run_chat_completion_task(task, persist_assistant_message=False)
    assert calls == []
