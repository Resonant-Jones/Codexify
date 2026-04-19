from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from types import SimpleNamespace
from typing import Any

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
from guardian.tasks.types import ChatCompletionTask


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
        tables=[db_models.PersonaProfile.__table__],
    )
    session_factory = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, future=True
    )
    persona_profile_store._set_session_factory(session_factory)
    try:
        yield
    finally:
        persona_profile_store._set_session_factory(None)


class _FakeChatLogDB:
    def __init__(
        self, thread: dict[str, object], messages: list[dict[str, object]]
    ):
        self._thread = thread
        self._messages = messages

    def get_chat_thread(self, thread_id: int):
        if _coerce_int(self._thread.get("id", 0)) == int(thread_id):
            return dict(self._thread)
        return None

    def list_messages(self, thread_id: int, limit: int = 50, offset: int = 0):
        if _coerce_int(self._thread.get("id", 0)) != int(thread_id):
            return []
        return list(self._messages)


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
        backend_profile = persona_profile_store.create_persona_profile(
            profile_id="profile-runtime",
            name="Runtime Persona",
            system_prompt="Backend prompt for the runtime profile.",
            model_provider="Anthropic",
            model_id="claude-sonnet-4-20250514",
            temperature=0.2,
        )

        fake_db = _FakeChatLogDB(
            {"id": 42, "active_profile_id": "profile-runtime"},
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
        assert (
            resolved.system_prompt == "Backend prompt for the runtime profile."
        )

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
            profile_id="profile-runtime",
            name="Runtime Persona",
            system_prompt="Backend prompt for the runtime profile.",
            model_provider="OpenAI",
            model_id="gpt-4o",
            temperature=0.25,
        )

        fake_db = _FakeChatLogDB(
            {"id": 42, "active_profile_id": "profile-runtime"},
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
                "system prompt",
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

        monkeypatch.setattr(
            chat_completion_service, "chat_with_ai", _fake_chat_with_ai
        )

        task = ChatCompletionTask(
            user_id="local",
            task_id="task-runtime",
            thread_id=42,
            origin="test",
        )

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
