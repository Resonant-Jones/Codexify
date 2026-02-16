from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from guardian.db.models import Base, ChatThread


def test_chat_thread_defaults_diary_flags():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine, tables=[ChatThread.__table__])
    Session = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, future=True
    )

    with Session() as session:
        t = ChatThread(user_id="u1", title="test", summary="")
        session.add(t)
        session.commit()
        session.refresh(t)
        assert t.is_diary is False
        assert t.diary_mode is False
        assert t.exclude_from_identity is False
        assert t.modeling_excluded is False
