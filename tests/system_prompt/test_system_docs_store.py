from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from codexify.system_docs import store as system_doc_store
from guardian.db.models import Base, SystemDoc, SystemDocLink


def setup_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(
        bind=engine, tables=[SystemDoc.__table__, SystemDocLink.__table__]
    )
    return sessionmaker(
        bind=engine, autoflush=False, autocommit=False, future=True
    )


def test_list_docs_with_links_and_toggle():
    Session = setup_session()
    system_doc_store._set_session_factory(Session)

    with Session() as session:
        d1 = SystemDoc(
            scope="global",
            slug="g",
            title="Global",
            content="g",
            is_enabled=True,
        )
        d2 = SystemDoc(
            scope="user",
            owner_user_id="u1",
            slug="u",
            title="UserDoc",
            content="u",
            is_enabled=True,
        )
        session.add_all([d1, d2])
        session.commit()
        d1_id, d2_id = d1.id, d2.id

    docs = system_doc_store.list_docs_with_links("u1", None)
    assert any(doc.id == d1_id and enabled for doc, enabled in docs)

    system_doc_store.set_doc_link("u1", None, d2_id, False)
    docs = system_doc_store.list_docs_with_links("u1", None)
    user_doc_entry = [enabled for doc, enabled in docs if doc.id == d2_id][0]
    assert user_doc_entry is False
