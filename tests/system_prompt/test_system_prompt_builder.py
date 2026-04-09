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
