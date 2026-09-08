from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.cognition import system_prompt_builder
from guardian.cognition.identity_resolution import (
    ResolvedImprint,
    ResolvedPersona,
)
from guardian.cognition.system_profiles import (
    resolver as system_profile_resolver,
)
from guardian.cognition.system_profiles import store as persona_profile_store
from guardian.core import chat_completion_service
from guardian.db import models as db_models
from guardian.tasks.types import (
    ChatCompletionTask,
    PersonaSelectionSnapshot,
    task_from_dict,
)


def _coerce_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


@contextmanager
def _persona_profile_session() -> Iterator[None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    db_models.Base.metadata.create_all(
        engine,
        tables=[
            db_models.User.__table__,
            db_models.PersonaProfile.__table__,
            db_models.PersonaProfileRevision.__table__,
            db_models.PersonaProfileBinding.__table__,
        ],
    )
    session_factory = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, future=True
    )
    with session_factory.begin() as session:
        session.add_all(
            [
                db_models.User(
                    id="account-a",
                    username="account-a",
                    password_hash="not-a-real-hash",
                    role="guest",
                ),
                db_models.User(
                    id="account-b",
                    username="account-b",
                    password_hash="not-a-real-hash",
                    role="guest",
                ),
            ]
        )
    persona_profile_store._set_session_factory(session_factory)
    try:
        yield
    finally:
        persona_profile_store._set_session_factory(None)
        engine.dispose()


class _FakeChatLogDB:
    def __init__(self, thread: dict[str, object], messages: list[dict[str, object]]):
        self._thread = thread
        self._messages = messages

    def get_chat_thread(self, thread_id: int):
        if _coerce_int(self._thread.get("id", 0)) == int(thread_id):
            return dict(self._thread)
        return None

    def set_thread_active_profile_id(
        self, thread_id, profile_id, *, profile_revision=None
    ):
        if int(self._thread["id"]) != thread_id:
            return False
        self._thread.update(
            active_profile_id=profile_id, active_profile_revision=profile_revision
        )
        return True

    def list_messages(self, thread_id: int, limit: int = 50, offset: int = 0):
        if _coerce_int(self._thread.get("id", 0)) != int(thread_id):
            return []
        return list(self._messages)


def _accept_task(monkeypatch, db, task):
    """Capture through production acceptance and reconstruct the queued task."""
    from guardian.queue.redis_queue import _deserialize, _serialize

    queued = []
    monkeypatch.setattr(chat_completion_service.dependencies, "chatlog_db", db)
    monkeypatch.setattr(chat_completion_service, "acquire_turn_lock", lambda *_a: True)
    monkeypatch.setattr(
        chat_completion_service,
        "enqueue",
        lambda value, _queue: queued.append(_serialize(value)),
    )
    monkeypatch.setattr(
        chat_completion_service.task_events,
        "publish_with_visibility",
        lambda *_a: {"ok": True, "event_id": "accepted"},
    )
    chat_completion_service.enqueue_chat_completion(
        task, thread_id=task.thread_id, turn_id="test-turn"
    )
    return task_from_dict(_deserialize(queued[0]))


def _fake_retrieval_plan():
    return SimpleNamespace(
        intent=SimpleNamespace(value="chat"),
        effective_depth=SimpleNamespace(value="normal"),
        default_scope=SimpleNamespace(value="thread"),
        time_mode=SimpleNamespace(value="none"),
        graph_allowance=SimpleNamespace(value="none"),
        retrieval_needed=False,
        allow_global_fallback=False,
        escalation_order=[],
        reasons=[],
    )


def test_resolve_thread_system_profile_embeds_backend_profile_guidance(
    monkeypatch,
):
    with _persona_profile_session():
        persona_profile_store.create_persona_profile(
            account_id="account-a",
            profile_id="profile-runtime",
            name="Runtime Persona",
            system_prompt="Backend prompt for the runtime profile.",
            model_provider="Anthropic",
            model_id="claude-sonnet-4-20250514",
            temperature=0.2,
        )

        fake_db = _FakeChatLogDB(
            {
                "id": 42,
                "user_id": "account-a",
                "active_profile_id": "profile-runtime",
                "active_profile_revision": 1,
            },
            [{"id": 1, "role": "user", "content": "hello"}],
        )

        resolved = system_profile_resolver.resolve_thread_system_profile(
            42, chatlog_db=fake_db
        )
        assert resolved.profile_id == "profile-runtime"
        assert resolved.name == "Runtime Persona"
        assert resolved.provider_override == "anthropic"
        assert resolved.model_override == "claude-sonnet-4-20250514"
        assert resolved.temperature_override == 0.2
        assert resolved.system_prompt == "Backend prompt for the runtime profile."

        monkeypatch.setattr(
            system_prompt_builder,
            "resolve_imprint",
            lambda *args, **kwargs: ResolvedImprint(
                source="system_default",
                imprint_id=None,
                user_id="user-1",
                project_id=None,
                guardian_name="Guardian",
                preferred_name="Resonant",
                style="Warm",
                grammar_prefs={},
                metrics={},
                heat_score=None,
            ),
        )
        monkeypatch.setattr(
            system_prompt_builder,
            "resolve_persona",
            lambda *args, **kwargs: ResolvedPersona(
                source="system_default",
                persona_id=None,
                user_id="user-1",
                project_id=None,
                body="Be precise.",
                record_source="system_default",
            ),
        )
        monkeypatch.setattr(
            system_prompt_builder, "get_docs_for", lambda *args, **kwargs: []
        )

        (
            system_prompt,
            meta,
        ) = system_prompt_builder.build_guardian_system_prompt(
            user_id="user-1",
            project_id=None,
            depth="normal",
            bundle={},
            profile=resolved,
        )

        assert "profile_id: profile-runtime" in system_prompt
        assert "name: Runtime Persona" in system_prompt
        assert "model_provider: anthropic" in system_prompt
        assert "model_id: claude-sonnet-4-20250514" in system_prompt
        assert "temperature: 0.2" in system_prompt
        assert "Backend prompt for the runtime profile." in system_prompt
        assert meta["active_profile_id"] == "profile-runtime"


def test_chat_completion_task_uses_backend_temperature_through_completion_routing(
    monkeypatch,
):
    with _persona_profile_session():
        persona_profile_store.create_persona_profile(
            account_id="account-a",
            profile_id="profile-runtime",
            name="Runtime Persona",
            system_prompt="Backend prompt for the runtime profile.",
            model_provider="OpenAI",
            model_id="gpt-4o",
            temperature=0.25,
        )

        fake_db = _FakeChatLogDB(
            {
                "id": 42,
                "user_id": "account-a",
                "active_profile_id": "profile-runtime",
                "active_profile_revision": 1,
            },
            [{"id": 1, "role": "user", "content": "hello"}],
        )

        async def _fake_assemble_context_bundle(*args, **kwargs):
            return {}, None

        monkeypatch.setattr(
            chat_completion_service.dependencies,
            "chatlog_db",
            fake_db,
            raising=False,
        )
        monkeypatch.setattr(
            chat_completion_service,
            "_assemble_context_bundle",
            _fake_assemble_context_bundle,
        )
        monkeypatch.setattr(
            chat_completion_service,
            "build_guardian_system_prompt",
            lambda **kwargs: (
                kwargs["profile"].system_prompt,
                {
                    "estimated_tokens": 1,
                    "resolved_persona_id": "profile-runtime",
                    "persona_has_body": True,
                },
            ),
        )
        monkeypatch.setattr(
            chat_completion_service,
            "build_context_system_message_with_meta",
            lambda bundle: (None, {}),
        )
        monkeypatch.setattr(
            chat_completion_service,
            "resolve_retrieval_plan",
            lambda *args, **kwargs: _fake_retrieval_plan(),
        )
        monkeypatch.setattr(
            chat_completion_service,
            "validate_llm_config",
            lambda *args, **kwargs: None,
        )
        monkeypatch.setattr(
            chat_completion_service,
            "resolve_thread_completion_settings",
            lambda *args, **kwargs: chat_completion_service.ThreadCompletionSettings(
                provider="",
                model="",
                reasoning_mode=None,
                source_mode="thread",
            ),
        )

        captured = {}

        def _fake_chat_with_ai(
            messages,
            model=None,
            provider=None,
            reasoning_mode=None,
            temperature=None,
            prompt_meta=None,
            settings=None,
        ):
            captured["messages"] = messages
            captured["model"] = model
            captured["provider"] = provider
            captured["temperature"] = temperature
            return "assistant answer"

        monkeypatch.setattr(chat_completion_service, "chat_with_ai", _fake_chat_with_ai)

        task = ChatCompletionTask(
            user_id="account-a",
            thread_id=42,
            origin="test",
        )

        system_profile_resolver.switch_thread_profile(
            42, "profile-runtime", chatlog_db=fake_db
        )
        task = _accept_task(monkeypatch, fake_db, task)
        assert task.persona_selection_snapshot == PersonaSelectionSnapshot(
            "profile-runtime", 1
        )
        persona_profile_store.update_persona_profile(
            "profile-runtime",
            account_id="account-a",
            name="Edited Persona",
            system_prompt="Edited instructions.",
            model_provider="anthropic",
            model_id="edited-model",
            temperature=0.8,
        )
        system_profile_resolver.switch_thread_profile(
            42, "profile-runtime", chatlog_db=fake_db
        )
        assert fake_db._thread["active_profile_revision"] == 2

        result = chat_completion_service.run_chat_completion_task(
            task,
            persist_assistant_message=False,
        )

        assert result["provider"] == "openai"
        assert result["model"] == "gpt-4o"
        assert task.provider == "openai"
        assert task.model == "gpt-4o"
        assert task.temperature == 0.25
        assert captured["provider"] == "openai"
        assert captured["model"] == "gpt-4o"
        assert captured["temperature"] == 0.25
        assert captured["messages"][0]["role"] == "system"
        assert captured["messages"][-1]["role"] == "user"
        assert (
            captured["messages"][0]["content"].split(
                "\n\nCompletion targeting guidance:"
            )[0]
            == "Backend prompt for the runtime profile."
        )

        system_profile_resolver.switch_thread_profile(
            42, "profile-runtime", chatlog_db=fake_db
        )
        assert fake_db._thread["active_profile_revision"] == 2
        next_task = ChatCompletionTask(user_id="account-a", thread_id=42, origin="test")
        next_task = _accept_task(monkeypatch, fake_db, next_task)
        chat_completion_service.run_chat_completion_task(
            next_task, persist_assistant_message=False
        )
        assert (captured["provider"], captured["model"], captured["temperature"]) == (
            "anthropic",
            "edited-model",
            0.8,
        )
        assert (
            captured["messages"][0]["content"].split(
                "\n\nCompletion targeting guidance:"
            )[0]
            == "Edited instructions."
        )

        system_profile_resolver.switch_thread_profile(
            42, "local_mode", chatlog_db=fake_db
        )
        task.attempt_id = "retry-attempt"
        chat_completion_service.run_chat_completion_task(
            task, persist_assistant_message=False
        )
        assert task.persona_selection_snapshot == PersonaSelectionSnapshot(
            "profile-runtime", 1
        )
        assert (captured["provider"], captured["model"], captured["temperature"]) == (
            "openai",
            "gpt-4o",
            0.25,
        )
        assert (
            captured["messages"][0]["content"].split(
                "\n\nCompletion targeting guidance:"
            )[0]
            == "Backend prompt for the runtime profile."
        )

        # Legacy tasks intentionally follow the current thread selection.
        system_profile_resolver.switch_thread_profile(
            42, "profile-runtime", chatlog_db=fake_db
        )
        legacy = ChatCompletionTask(user_id="account-a", thread_id=42)
        chat_completion_service.run_chat_completion_task(
            legacy, persist_assistant_message=False
        )
        assert (
            captured["messages"][0]["content"].split(
                "\n\nCompletion targeting guidance:"
            )[0]
            == "Edited instructions."
        )
        assert (captured["provider"], captured["model"], captured["temperature"]) == (
            "anthropic",
            "edited-model",
            0.8,
        )
        captured.clear()
        invalid_task = ChatCompletionTask(
            user_id="account-a",
            task_id="invalid-task",
            thread_id=42,
            origin="test",
            persona_selection_snapshot=PersonaSelectionSnapshot("profile-runtime", 99),
        )
        with pytest.raises(system_profile_resolver.ProfileResolutionError):
            chat_completion_service.run_chat_completion_task(
                invalid_task, persist_assistant_message=False
            )
        assert captured == {}


def test_backend_catalog_does_not_leak_profile_values_across_accounts():
    with _persona_profile_session():
        persona_profile_store.create_persona_profile(
            account_id="account-a",
            manifest={
                "apiVersion": "codexify.persona/v1",
                "profileIdentity": "account-a-profile",
                "identity": {
                    "name": "Account A Persona",
                    "description": "Persistence-only description.",
                },
                "prompt": {
                    "systemPrompt": "Account A private system prompt.",
                },
                "model": {
                    "provider": "anthropic",
                    "model": "account-a-model",
                    "temperature": 0.17,
                    "topK": 21,
                    "topP": 0.8,
                    "maxTokens": 2048,
                },
                "capabilities": {
                    "pinnedTools": ["account-a-tool"],
                    "allowedTools": ["account-a-tool"],
                    "skills": ["account-a-skill"],
                    "permissions": {
                        "web": True,
                        "email": True,
                        "calendar": True,
                        "cli": True,
                        "filesystem": True,
                    },
                },
                "retrieval": {
                    "enabled": True,
                    "mode": "hybrid",
                    "topK": 7,
                    "rerank": True,
                },
            },
        )

        owner_db = _FakeChatLogDB(
            {
                "id": 101,
                "user_id": "account-a",
                "active_profile_id": "account-a-profile",
                "active_profile_revision": 1,
            },
            [],
        )
        foreign_db = _FakeChatLogDB(
            {
                "id": 202,
                "user_id": "account-b",
                "active_profile_id": "account-a-profile",
                "active_profile_revision": 1,
            },
            [],
        )

        owner = system_profile_resolver.resolve_thread_system_profile(
            101,
            chatlog_db=owner_db,
        )
        assert owner.system_prompt == "Account A private system prompt."
        assert owner.provider_override == "anthropic"
        assert owner.model_override == "account-a-model"
        assert owner.temperature_override == 0.17
        assert owner.retrieval_config is None
        assert owner.tool_permissions is None
        assert owner.model_config_payload is None

        with pytest.raises(system_profile_resolver.ProfileResolutionError):
            system_profile_resolver.resolve_thread_system_profile(
                202, chatlog_db=foreign_db
            )

        owner_ids = {
            profile["id"]
            for profile in system_profile_resolver.list_available_system_profiles(
                thread_id=101,
                chatlog_db=owner_db,
            )
        }
        foreign_ids = {
            profile["id"]
            for profile in system_profile_resolver.list_available_system_profiles(
                thread_id=202,
                chatlog_db=foreign_db,
            )
        }
        assert "account-a-profile" in owner_ids
        assert "account-a-profile" not in foreign_ids
        assert "default" in owner_ids
        assert "default" in foreign_ids
