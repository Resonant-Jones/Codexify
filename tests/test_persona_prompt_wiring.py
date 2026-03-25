from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from guardian.cognition.identity_resolution import (
    ResolvedImprint,
    ResolvedPersona,
)
from guardian.cognition.personas import store as persona_store
from guardian.cognition.system_prompt_builder import (
    build_guardian_system_prompt,
)
from guardian.core.chat_completion_service import (
    build_sanitized_payload_summary,
)
from guardian.db.models import Persona


def _setup_in_memory_persona_store(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Persona.__table__.create(engine)
    factory = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, future=True
    )
    monkeypatch.setattr(persona_store, "_SessionFactory", factory)
    return engine


def test_persona_store_set_and_get_active(monkeypatch):
    _setup_in_memory_persona_store(monkeypatch)

    first = persona_store.set_persona("user-1", 7, "Alpha persona")
    active = persona_store.get_active_persona("user-1", 7)
    assert active is not None
    assert active.body == "Alpha persona"

    second = persona_store.set_persona("user-1", 7, "Beta persona")
    newest = persona_store.get_active_persona("user-1", 7)
    assert newest is not None
    assert newest.id == second.id
    assert newest.body == "Beta persona"


def test_system_prompt_builder_includes_active_persona(monkeypatch):
    def _fake_resolve_persona(
        user_id,
        project_id,
        requested_persona_id_or_name=None,
        system_default_persona="",
    ):
        return ResolvedPersona(
            source="active_scope",
            persona_id=99,
            user_id=user_id,
            project_id=project_id,
            body="Be concise and direct.",
            record_source="store",
        )

    def _fake_resolve_imprint(user_id, project_id, system_default_imprint=None):
        return ResolvedImprint(
            source="system_default",
            imprint_id=None,
            user_id=user_id,
            project_id=project_id,
            guardian_name=None,
            preferred_name=None,
            style=None,
            grammar_prefs={},
            metrics={},
            heat_score=None,
        )

    monkeypatch.setattr(
        "guardian.cognition.system_prompt_builder.resolve_persona",
        _fake_resolve_persona,
    )
    monkeypatch.setattr(
        "guardian.cognition.system_prompt_builder.resolve_imprint",
        _fake_resolve_imprint,
    )
    monkeypatch.setattr(
        "guardian.cognition.system_prompt_builder.get_docs_for",
        lambda *_args, **_kwargs: [],
    )
    monkeypatch.setattr(
        "guardian.cognition.system_prompt_builder.estimate_token_cost_for_docs",
        lambda _docs: 0,
    )

    prompt, meta = build_guardian_system_prompt(
        user_id="user-1",
        project_id=None,
        depth="normal",
        bundle={},
    )

    assert "Be concise and direct." in prompt
    assert "=== PERSONA" in prompt
    assert meta.get("persona_has_body") is True
    assert meta.get("resolved_persona_source") == "active_scope"


def test_payload_summary_persona_flag():
    system_content = """=== PERSONA ===\nUser-provided persona instructions (do not override safety rules):\nStay focused"""
    messages = [{"role": "system", "content": system_content}]
    bundle = {"_prompt_meta": {"persona_has_body": True}}

    summary = build_sanitized_payload_summary(
        messages, bundle, provider="groq", model="llama3"
    )

    assert summary["persona_or_imprint_present"] is True

    summary_no_persona = build_sanitized_payload_summary(
        [{"role": "system", "content": "=== BASE SYSTEM ==="}],
        {
            "_prompt_meta": {
                "persona_has_body": False,
                "resolved_imprint_source": "system_default",
            }
        },
        provider="groq",
        model="llama3",
    )
    assert summary_no_persona["persona_or_imprint_present"] is False
