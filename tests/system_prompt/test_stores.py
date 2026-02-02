import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from guardian.cognition.imprints import store as imprint_store
from guardian.cognition.personas import store as persona_store
from guardian.cognition.system_docs import store as system_doc_store
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


def test_imprint_activation_supersedes_prior():
    Session = setup_session()
    imprint_store._set_session_factory(Session)

    im1 = imprint_store.save_imprint(
        "u1", None, guardian_name="G1", status="draft"
    )
    assert im1.status == "draft"

    # Activate first imprint
    active1 = imprint_store.activate_imprint(im1.id)
    assert active1.status == "active"

    # Create second and activate, superseding prior
    im2 = imprint_store.save_imprint(
        "u1", None, guardian_name="G2", status="draft"
    )
    active2 = imprint_store.activate_imprint(im2.id)
    assert active2.status == "active"

    fetched = imprint_store.get_active_imprint("u1", None)
    assert fetched.id == im2.id


def test_imprints_are_per_project():
    Session = setup_session()
    imprint_store._set_session_factory(Session)

    a1 = imprint_store.save_imprint("u1", 1, guardian_name="P1", status="draft")
    a2 = imprint_store.save_imprint("u1", 2, guardian_name="P2", status="draft")
    imprint_store.activate_imprint(a1.id)
    imprint_store.activate_imprint(a2.id)

    fetched_p1 = imprint_store.get_active_imprint("u1", 1)
    fetched_p2 = imprint_store.get_active_imprint("u1", 2)
    assert fetched_p1.guardian_name == "P1"
    assert fetched_p2.guardian_name == "P2"


def test_persona_set_deactivates_prior():
    Session = setup_session()
    persona_store._set_session_factory(Session)

    p1 = persona_store.set_persona("u1", None, body="first")
    assert p1.is_active

    p2 = persona_store.set_persona("u1", None, body="second", source="user")
    assert p2.is_active

    fetched = persona_store.get_active_persona("u1", None)
    assert fetched.body == "second"


def test_system_docs_links_and_globals():
    Session = setup_session()
    system_doc_store._set_session_factory(Session)

    with Session() as session:
        global_doc = SystemDoc(
            scope="global",
            slug="g1",
            title="Global Doc",
            content="global",
            is_enabled=True,
        )
        linked_doc = SystemDoc(
            scope="user",
            owner_user_id="u1",
            slug="l1",
            title="Linked",
            content="linked",
            is_enabled=True,
        )
        disabled_doc = SystemDoc(
            scope="user",
            owner_user_id="u1",
            slug="d1",
            title="Disabled",
            content="nope",
            is_enabled=False,
        )
        session.add_all([global_doc, linked_doc, disabled_doc])
        session.commit()

        link = SystemDocLink(
            user_id="u1",
            project_id=None,
            system_doc_id=linked_doc.id,
            is_enabled=True,
        )
        session.add(link)
        session.commit()

    docs = system_doc_store.get_docs_for("u1", None)
    titles = {d.title for d in docs}
    assert "Global Doc" in titles
    assert "Linked" in titles
    assert "Disabled" not in titles
