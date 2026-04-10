from __future__ import annotations

from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.cognition.imprints import store as imprint_store
from guardian.cognition.personas import store as persona_store
from guardian.core import chat_completion_service
from guardian.core.chat_completion_service import (
    build_sanitized_payload_summary,
)
from guardian.db.models import Base, Imprint, Persona
from guardian.tasks.types import ChatCompletionTask


def _setup_session_factory():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        bind=engine,
        tables=[Imprint.__table__, Persona.__table__],
    )
    return sessionmaker(
        bind=engine, autoflush=False, autocommit=False, future=True
    )


def _fake_retrieval_plan():
    return SimpleNamespace(
        intent=SimpleNamespace(value="identity"),
        effective_depth=SimpleNamespace(value="normal"),
        default_scope=SimpleNamespace(value="thread"),
        time_mode=SimpleNamespace(value="current"),
        graph_allowance=SimpleNamespace(value="allowed"),
        retrieval_needed=False,
        allow_global_fallback=False,
        escalation_order=[],
        reasons=[],
    )


@pytest.fixture
def _runtime_prompt_setup(monkeypatch: pytest.MonkeyPatch):
    Session = _setup_session_factory()
    imprint_store._set_session_factory(Session)
    persona_store._set_session_factory(Session)

    monkeypatch.setattr(
        "guardian.cognition.system_prompt_builder.get_docs_for",
        lambda *_args, **_kwargs: [],
    )
    monkeypatch.setattr(
        "guardian.cognition.system_prompt_builder.estimate_token_cost_for_docs",
        lambda _docs: 0,
    )
    monkeypatch.setattr(
        chat_completion_service, "resolve_thread_system_profile", None
    )
    monkeypatch.setattr(
        chat_completion_service,
        "validate_llm_config",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        chat_completion_service,
        "resolve_retrieval_plan",
        lambda *args, **kwargs: _fake_retrieval_plan(),
    )
    monkeypatch.setattr(
        chat_completion_service,
        "get_settings",
        lambda: SimpleNamespace(
            LLM_PROVIDER="groq",
            LOCAL_LLM_MODEL="runtime-local-model",
            DEFAULT_LOCAL_MODEL="runtime-local-model",
            LLM_MODEL="runtime-local-model",
        ),
    )
    monkeypatch.setattr(
        chat_completion_service.dependencies,
        "CHAT_PROVIDER",
        "groq",
        raising=False,
    )
    monkeypatch.setattr(
        chat_completion_service.dependencies,
        "DEFAULT_MODEL",
        "runtime-default-model",
        raising=False,
    )
    monkeypatch.setattr(
        chat_completion_service.dependencies,
        "_vector_store",
        None,
        raising=False,
    )
    monkeypatch.setattr(
        chat_completion_service.dependencies,
        "_memory_store",
        None,
        raising=False,
    )
    monkeypatch.setattr(
        chat_completion_service.dependencies,
        "_sensors",
        None,
        raising=False,
    )

    class _FakeBroker:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def assemble(
            self,
            thread_id,
            query,
            depth_mode,
            user_id,
            project_id=None,
            source_mode="project",
        ):
            return {"semantic": [], "graph": []}, {
                "documents": [],
                "graph": [],
                "source_mode": source_mode,
            }

    monkeypatch.setattr(chat_completion_service, "ContextBroker", _FakeBroker)

    mock_chatlog_db = SimpleNamespace(
        get_chat_thread=lambda thread_id: {
            "id": thread_id,
            "user_id": "u1",
            "project_id": 7,
            "thread_config": None,
            "active_profile_id": None,
        },
        list_messages=lambda thread_id, limit, offset: [
            {"id": 1, "role": "user", "content": "What changed?"}
        ],
    )
    monkeypatch.setattr(
        chat_completion_service.dependencies,
        "chatlog_db",
        mock_chatlog_db,
        raising=False,
    )
    return Session


@pytest.mark.asyncio
async def test_build_messages_for_llm_uses_persisted_active_imprint_and_persona(
    _runtime_prompt_setup,
):
    imprint = imprint_store.save_imprint(
        "u1",
        7,
        status="draft",
        guardian_name="Auri",
        preferred_name="Friend",
        style="playful-dry",
        metrics={"persona_draft": "Speak like a calm guide."},
    )
    imprint_store.activate_imprint(imprint.id)
    persona = persona_store.set_persona(
        "u1",
        7,
        body="Speak like a calm guide.",
        source="imprint_zero_seed",
    )

    task = ChatCompletionTask(thread_id=1, max_context=50, depth_mode="normal")

    (
        messages_for_llm,
        provider,
        model,
        bundle,
        trace,
    ) = await chat_completion_service.build_messages_for_llm(task)

    system_content = messages_for_llm[0]["content"]
    assert "=== IMPRINT_ZERO ===" in system_content
    assert "=== PERSONA ===" in system_content
    assert "Auri" in system_content
    assert "Speak like a calm guide." in system_content

    prompt_meta = bundle["_prompt_meta"]
    assert prompt_meta["resolved_imprint_source"] == "active_scope"
    assert prompt_meta["resolved_persona_source"] == "active_scope"
    assert prompt_meta["resolved_persona_id"] == persona.id
    assert prompt_meta["persona_has_body"] is True

    summary = build_sanitized_payload_summary(
        messages_for_llm,
        bundle,
        provider=provider,
        model=model,
    )
    assert summary["has_system_prompt"] is True
    assert summary["persona_or_imprint_present"] is True
    assert summary["message_count"] >= 2
    assert trace is not None


@pytest.mark.asyncio
async def test_build_messages_for_llm_prefers_thread_persona_override_without_rebinding_actor(
    _runtime_prompt_setup,
    monkeypatch: pytest.MonkeyPatch,
):
    imprint = imprint_store.save_imprint(
        "u1",
        7,
        status="active",
        guardian_name="Auri",
        preferred_name="Friend",
        style="playful-dry",
    )
    imprint_store.activate_imprint(imprint.id)

    active_persona = persona_store.set_persona(
        "u1",
        7,
        body="Active persona text.",
        source="user",
    )
    override_persona = persona_store.create_persona(
        "u1",
        7,
        "thread",
        "Thread override persona text.",
    )

    monkeypatch.setattr(
        chat_completion_service.dependencies,
        "chatlog_db",
        SimpleNamespace(
            get_chat_thread=lambda thread_id: {
                "id": thread_id,
                "user_id": "u1",
                "project_id": 7,
                "thread_config": {
                    "providerId": "groq",
                    "modelId": "runtime-model",
                    "inferenceMode": "fast",
                    "retrievalSource": "project",
                    "personaId": str(override_persona.id),
                },
                "active_profile_id": None,
            },
            list_messages=lambda thread_id, limit, offset: [
                {"id": 1, "role": "user", "content": "What changed?"}
            ],
        ),
        raising=False,
    )

    task = ChatCompletionTask(thread_id=1, max_context=50, depth_mode="normal")

    (
        messages_for_llm,
        _provider,
        _model,
        bundle,
        _trace,
    ) = await chat_completion_service.build_messages_for_llm(task)

    system_content = messages_for_llm[0]["content"]
    assert "=== BASE SYSTEM ===" in system_content
    assert "You are Guardian" in system_content
    assert "=== IMPRINT_ZERO ===" in system_content
    assert "Auri" in system_content
    assert "=== PERSONA ===" in system_content
    assert "Thread override persona text." in system_content
    assert "Active persona text." not in system_content

    prompt_meta = bundle["_prompt_meta"]
    assert prompt_meta["resolved_imprint_source"] == "active_scope"
    assert prompt_meta["resolved_persona_source"] == "request_override"
    assert prompt_meta["resolved_persona_id"] == override_persona.id
    assert prompt_meta["persona_has_body"] is True
    assert persona_store.get_active_persona("u1", 7).id == active_persona.id
