from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import JSON, create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.db.models import Base, ChatThread


@contextmanager
def _session_scope():
    original_type = ChatThread.__table__.c.thread_config.type
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    ChatThread.__table__.c.thread_config.type = JSON().with_variant(
        JSONB, "postgresql"
    )
    try:
        Base.metadata.create_all(bind=engine, tables=[ChatThread.__table__])
        yield sessionmaker(
            bind=engine, autoflush=False, autocommit=False, future=True
        )
    finally:
        ChatThread.__table__.c.thread_config.type = original_type
        engine.dispose()


def test_chat_thread_model_exposes_thread_config() -> None:
    assert "thread_config" in ChatThread.__table__.columns
    assert hasattr(ChatThread, "thread_config")


def test_chat_thread_thread_config_persists_json_object() -> None:
    thread_config = {
        "providerId": "local",
        "modelId": "qwen3.5:14b",
        "inferenceMode": "fast",
        "retrievalSource": "project",
        "personaId": None,
    }

    with _session_scope() as SessionLocal:
        with SessionLocal() as session:
            thread = ChatThread(
                user_id="u1",
                title="test",
                summary="",
                thread_config=thread_config,
            )
            session.add(thread)
            session.commit()
            session.refresh(thread)

            assert thread.thread_config == thread_config


def test_chat_thread_thread_config_can_be_null() -> None:
    with _session_scope() as SessionLocal:
        with SessionLocal() as session:
            thread = ChatThread(
                user_id="u1",
                title="test",
                summary="",
                thread_config=None,
            )
            session.add(thread)
            session.commit()
            session.refresh(thread)

            assert thread.thread_config is None


def test_chat_thread_creation_without_thread_config_remains_valid() -> None:
    with _session_scope() as SessionLocal:
        with SessionLocal() as session:
            thread = ChatThread(user_id="u1", title="test", summary="")
            session.add(thread)
            session.commit()
            session.refresh(thread)

            assert thread.thread_config is None
            assert thread.is_diary is False
            assert thread.diary_mode is False
            assert thread.exclude_from_identity is False
            assert thread.modeling_excluded is False
