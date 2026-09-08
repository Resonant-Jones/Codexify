from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from guardian.cognition.imprints import store as imprint_store
from guardian.cognition.personas import store as persona_store
from guardian.cognition.system_docs import store as system_doc_store
from guardian.cognition.system_profiles.resolver import ResolvedSystemProfile
from guardian.cognition.system_prompt_builder import (
    build_guardian_system_prompt,
)
from guardian.db.models import Base, Imprint, Persona, SystemDoc, SystemDocLink


def setup_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(
        bind=engine,
        tables=[
            Imprint.__table__,
            Persona.__table__,
            SystemDoc.__table__,
            SystemDocLink.__table__,
        ],
    )
    return sessionmaker(
        bind=engine, autoflush=False, autocommit=False, future=True
    )


def test_build_guardian_system_prompt_includes_segments():
    Session = setup_session()
    imprint_store._set_session_factory(Session)
    persona_store._set_session_factory(Session)
    system_doc_store._set_session_factory(Session)

    # Seed data
    im = imprint_store.save_imprint(
        "user-1",
        None,
        guardian_name="Auri",
        preferred_name="Friend",
        style="playful-dry",
    )
    imprint_store.activate_imprint(im.id)
    persona_store.set_persona("user-1", None, body="You love testing.")

    with Session() as session:
        doc = SystemDoc(
            scope="global",
            slug="doc-1",
            title="Doc One",
            content="Be kind.",
            is_enabled=True,
        )
        session.add(doc)
        session.commit()

    prompt, meta = build_guardian_system_prompt(
        user_id="user-1", project_id=None, depth="normal", bundle=None
    )

    assert "You are Guardian" in prompt
    assert "Auri" in prompt
    assert "You love testing." in prompt
    assert "Doc One" in prompt
    assert "=== BASE SYSTEM ===" in prompt
    assert "=== IMPRINT_ZERO ===" in prompt
    assert "=== PERSONA ===" in prompt
    assert "=== SYSTEM DOCS ===" in prompt
    assert (
        prompt.index("=== BASE SYSTEM ===")
        < prompt.index("=== IMPRINT_ZERO ===")
        < prompt.index("=== PERSONA ===")
    )
    assert meta["estimated_tokens"] > 0
    assert meta["docs_count"] == 1


def test_build_guardian_system_prompt_truncates_docs_when_over_cap():
    Session = setup_session()
    imprint_store._set_session_factory(Session)
    persona_store._set_session_factory(Session)
    system_doc_store._set_session_factory(Session)

    with Session() as session:
        doc = SystemDoc(
            scope="global",
            slug="doc-big",
            title="Big Doc",
            content="X" * 20000,
            is_enabled=True,
        )
        session.add(doc)
        session.commit()

    prompt, meta = build_guardian_system_prompt(
        user_id="u2",
        project_id=None,
        depth="normal",
        bundle=None,
        token_cap=200,
    )
    assert meta["estimated_tokens"] <= 200
    assert meta["docs_truncated"] is True


def test_build_guardian_system_prompt_includes_profile_guidance_in_scratchpad():
    Session = setup_session()
    imprint_store._set_session_factory(Session)
    persona_store._set_session_factory(Session)
    system_doc_store._set_session_factory(Session)

    persona_store.set_persona("user-3", None, body="Persona guidance.")
    profile = ResolvedSystemProfile(
        profile_id="local_mode",
        active_profile_id="local_mode",
        source="catalog",
        provider_override="local",
        system_prompt_blocks={
            "behavior": "Profile behavior guidance.",
            "constraints": "Profile constraint guidance.",
        },
    )

    prompt, meta = build_guardian_system_prompt(
        user_id="user-3",
        project_id=None,
        depth="normal",
        bundle=None,
        profile=profile,
    )

    assert "Resolved system profile guidance" in prompt
    assert "Profile behavior guidance." in prompt
    assert "=== SCRATCHPAD ===" in prompt
    segments = {segment["name"]: segment for segment in meta["segments"]}
    assert segments["scratchpad"]["chars"] > 0
    assert prompt.index("=== PERSONA ===") < prompt.index("=== SCRATCHPAD ===")


def test_inspection_uses_shared_composition_without_legacy_reads(monkeypatch):
    import json
    from unittest.mock import Mock

    from guardian.cognition import system_prompt_builder as builder

    Session = setup_session()
    imprint_store._set_session_factory(Session)
    system_doc_store._set_session_factory(Session)
    imprint = imprint_store.save_imprint(
        "inspect-user", None, guardian_name="PRIVATE_IMPRINT_NAME", style="dry"
    )
    imprint_store.activate_imprint(imprint.id)
    with Session() as session:
        session.add(SystemDoc(
            scope="global", slug="inspection-doc", title="PRIVATE_DOC_TITLE",
            content="PRIVATE_DOCUMENT_CONTENT", is_enabled=True,
        ))
        session.commit()
    forbidden = Mock(side_effect=AssertionError("legacy read forbidden"))
    monkeypatch.setattr(builder, "resolve_persona", forbidden)
    monkeypatch.setattr(persona_store, "get_active_persona", forbidden)
    monkeypatch.setattr(builder, "_base_codexify_system_prompt", lambda: "PRIVATE_BASE")
    shared = Mock(wraps=builder.build_system_prompt)
    monkeypatch.setattr(builder, "build_system_prompt", shared)
    profile = ResolvedSystemProfile(
        profile_id="canonical", active_profile_id="canonical",
        active_profile_revision=2, source="persona_profile_revision",
        system_prompt="PRIVATE_PROFILE_PROMPT", provider_override="local",
    )
    result = builder.build_guardian_system_prompt_inspection_metadata(
        user_id="inspect-user", project_id=None, depth="normal", profile=profile,
        token_cap=10000,
    )
    forbidden.assert_not_called()
    shared.assert_called_once()
    assert not shared.call_args.kwargs["persona_block"]
    assert "PRIVATE_PROFILE_PROMPT" in shared.call_args.kwargs["scratchpad_block"]
    assert result["projection_kind"] == "canonical_inspection"
    assert result["legacy_persona_included"] is False
    assert result["docs_count"] == 1
    assert result["estimated_tokens_total"] > 0
    assert result["docs_truncated"] is False
    assert set(result) == {
        "projection_kind", "legacy_persona_included", "total_chars",
        "estimated_tokens", "estimated_tokens_total", "docs_count", "cap_tokens",
        "docs_truncated", "profile_truncated", "docs_estimated_tokens", "segments",
    }
    for segment in result["segments"]:
        assert set(segment) == {"name", "chars", "estimated_tokens", "truncated", "cacheable"}
    assert "PRIVATE_" not in json.dumps(result)
    without_profile = builder.build_guardian_system_prompt_inspection_metadata(
        user_id="inspect-user", project_id=None, depth="normal", token_cap=10000,
    )
    assert result["estimated_tokens_total"] > without_profile["estimated_tokens_total"]
    truncated = builder.build_guardian_system_prompt_inspection_metadata(
        user_id="inspect-user", project_id=None, depth="normal", token_cap=1,
    )
    assert truncated["docs_truncated"] is True
    assert truncated["estimated_tokens_total"] <= 1
    forbidden.assert_not_called()


def test_runtime_preserves_legacy_resolution_and_metadata(monkeypatch):
    from unittest.mock import Mock

    from guardian.cognition import system_prompt_builder as builder

    Session = setup_session()
    imprint_store._set_session_factory(Session)
    persona_store._set_session_factory(Session)
    system_doc_store._set_session_factory(Session)
    persona_store.set_persona("runtime-user", None, body="LEGACY_RUNTIME_TEXT")
    resolver = Mock(wraps=builder.resolve_persona)
    monkeypatch.setattr(builder, "resolve_persona", resolver)
    prompt, meta = builder.build_guardian_system_prompt(
        user_id="runtime-user", project_id=None, depth="normal"
    )
    resolver.assert_called_once_with(
        "runtime-user", None, requested_persona_id_or_name=None
    )
    assert "LEGACY_RUNTIME_TEXT" in prompt
    assert meta["resolved_persona_source"] == "active_scope"
    assert meta["resolved_persona_id"] is not None
    assert meta["persona_has_body"] is True
    assert "projection_kind" not in meta
    assert set(meta) == {
        "total_chars", "estimated_tokens", "estimated_tokens_total", "docs_count",
        "segments", "segments_char_map", "truncation_notes", "cap_tokens",
        "docs_truncated", "profile_truncated", "overflow", "active_profile_id",
        "resolved_persona_source", "resolved_imprint_source", "resolved_persona_id",
        "persona_has_body", "docs_estimated_tokens",
    }
    assert any("LEGACY_RUNTIME_TEXT" in s["text"] for s in meta["segments"])


def test_inspection_matches_runtime_measurements_without_legacy_body(monkeypatch):
    from types import SimpleNamespace
    from guardian.cognition import system_prompt_builder as builder

    Session = setup_session()
    imprint_store._set_session_factory(Session)
    system_doc_store._set_session_factory(Session)
    monkeypatch.setattr(builder, "resolve_persona", lambda *a, **kw: SimpleNamespace(
        body="", source="system_default", persona_id=None,
    ))
    profile = ResolvedSystemProfile(
        profile_id="test-profile", system_prompt="Shared profile guidance."
    )
    args = dict(user_id="parity-user", project_id=None, depth="normal", profile=profile)
    _, runtime = builder.build_guardian_system_prompt(**args)
    inspection = builder.build_guardian_system_prompt_inspection_metadata(**args)
    for key, value in inspection.items():
        if key in {"projection_kind", "legacy_persona_included"}:
            continue
        if key == "segments":
            assert value == [
                {k: s[k] for k in value[0]} for s in runtime["segments"]
            ]
        else:
            assert value == runtime[key]
