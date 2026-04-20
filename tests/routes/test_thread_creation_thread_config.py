from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock

import pytest
from sqlalchemy import JSON, create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.core.dependencies import RequestUserScope
from guardian.core.pgdb import PgDB
from guardian.db.models import Base, ChatThread
from guardian.routes import chat as chat_routes
from tests.utils import get_test_user_id


@contextmanager
def _thread_config_session_factory():
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


class _ThreadConfigBackend(PgDB):
    def __init__(self, session_factory):
        self._SessionLocal = session_factory
        self.created_thread_calls: list[dict[str, object]] = []
        self.audit_log_calls: list[
            tuple[tuple[object, ...], dict[str, object]]
        ] = []

    @contextmanager
    def _sa_session(self):
        session = self._SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def ensure_default_project(self) -> int:
        return 1

    def get_recent_thread(self, user_id: str):
        return None

    def count_messages(self, thread_id: int) -> int:
        return 0

    def write_audit_log(self, *args, **kwargs):
        self.audit_log_calls.append((args, kwargs))
        return None

    def create_chat_thread(self, **kwargs):
        self.created_thread_calls.append(dict(kwargs))
        with self._sa_session() as session:
            thread = ChatThread(
                user_id=str(kwargs.get("user_id", "default")),
                title=str(kwargs.get("title", "New Chat")),
                summary=str(kwargs.get("summary", "")),
                project_id=kwargs.get("project_id"),
            )
            session.add(thread)
            session.flush()
            thread_id = int(thread.id)

        return {
            "id": thread_id,
            "user_id": str(kwargs.get("user_id", "default")),
            "title": str(kwargs.get("title", "New Chat")),
            "summary": str(kwargs.get("summary", "")),
            "project_id": kwargs.get("project_id"),
            "parent_id": None,
            "archived_at": None,
        }


@pytest.fixture
def thread_config_backend():
    with _thread_config_session_factory() as session_factory:
        yield _ThreadConfigBackend(session_factory), session_factory


def _fetch_thread(session_factory, thread_id: int) -> ChatThread:
    with session_factory() as session:
        thread = session.get(ChatThread, thread_id)
        assert thread is not None
        return thread


def _set_local_runtime_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(chat_routes, "CHAT_PROVIDER", "local", raising=False)
    monkeypatch.setattr(
        chat_routes, "DEFAULT_MODEL", "qwen3.5:14b", raising=False
    )
    monkeypatch.setattr(
        chat_routes.llm_settings, "LLM_PROVIDER", "local", raising=False
    )
    monkeypatch.setattr(
        chat_routes.llm_settings,
        "LOCAL_LLM_MODEL",
        "qwen3.5:14b",
        raising=False,
    )
    monkeypatch.setattr(
        chat_routes.llm_settings,
        "LOCAL_CHAT_MODEL",
        "qwen3.5:14b",
        raising=False,
    )
    monkeypatch.setattr(
        chat_routes.llm_settings,
        "DEFAULT_LOCAL_MODEL",
        "qwen3.5:14b",
        raising=False,
    )
    monkeypatch.setattr(
        chat_routes.llm_settings, "LLM_MODEL", "qwen3.5:14b", raising=False
    )
    monkeypatch.setattr(
        chat_routes.llm_settings,
        "LOCAL_DEFAULT_NO_THINK_ENABLED",
        True,
        raising=False,
    )


def _set_groq_runtime_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(chat_routes, "CHAT_PROVIDER", "groq", raising=False)
    monkeypatch.setattr(
        chat_routes,
        "DEFAULT_MODEL",
        "moonshotai/kimi-k2-instruct-0905",
        raising=False,
    )
    monkeypatch.setattr(
        chat_routes.llm_settings, "LLM_PROVIDER", "groq", raising=False
    )
    monkeypatch.setattr(
        chat_routes.llm_settings,
        "GROQ_MODEL",
        "moonshotai/kimi-k2-instruct-0905",
        raising=False,
    )
    monkeypatch.setattr(
        chat_routes.llm_settings,
        "DEFAULT_GROQ_MODEL",
        "moonshotai/kimi-k2-instruct-0905",
        raising=False,
    )


def test_chat_thread_create_snapshots_runtime_defaults(
    monkeypatch: pytest.MonkeyPatch,
    thread_config_backend,
) -> None:
    backend, session_factory = thread_config_backend
    monkeypatch.setattr(chat_routes, "chatlog_db", backend)
    _set_local_runtime_defaults(monkeypatch)

    expected_user_id = get_test_user_id()
    result = chat_routes.chat_create_thread(
        {},
        api_key="test-api-key",
        request_user_scope=RequestUserScope(
            user_id=expected_user_id,
            account_id=expected_user_id,
            multi_user_enabled=False,
        ),
    )

    assert result["ok"] is True
    assert result["thread"]["user_id"] == expected_user_id
    assert backend.created_thread_calls
    assert "thread_config" not in backend.created_thread_calls[0]

    thread = _fetch_thread(session_factory, int(result["id"]))
    assert thread.thread_config == {
        "providerId": "local",
        "modelId": "qwen3.5:14b",
        "inferenceMode": "fast",
        "retrievalSource": "project",
        "personaId": None,
    }


def test_chat_thread_create_uses_explicit_thread_config_values(
    monkeypatch: pytest.MonkeyPatch,
    thread_config_backend,
) -> None:
    backend, session_factory = thread_config_backend
    monkeypatch.setattr(chat_routes, "chatlog_db", backend)
    _set_groq_runtime_defaults(monkeypatch)

    body = {
        "title": "Explicit config",
        "providerId": "local",
        "modelId": "qwen3.5:14b",
        "inferenceMode": "think",
        "retrievalSource": "global",
        "personaId": "persona-7",
    }

    expected_user_id = get_test_user_id()
    result = chat_routes.chat_create_thread(
        body,
        api_key="test-api-key",
        request_user_scope=RequestUserScope(
            user_id=expected_user_id,
            account_id=expected_user_id,
            multi_user_enabled=False,
        ),
    )

    assert result["ok"] is True
    assert result["thread"]["user_id"] == expected_user_id
    assert backend.created_thread_calls
    assert "thread_config" not in backend.created_thread_calls[0]

    thread = _fetch_thread(session_factory, int(result["id"]))
    assert thread.thread_config == {
        "providerId": "local",
        "modelId": "qwen3.5:14b",
        "inferenceMode": "think",
        "retrievalSource": "global",
        "personaId": "persona-7",
    }


def test_chat_thread_create_keeps_legacy_backend_working(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected_user_id = get_test_user_id()
    mock_db = MagicMock()
    mock_db.create_chat_thread.return_value = {
        "id": 17,
        "user_id": expected_user_id,
        "title": "Legacy Thread",
        "summary": "Legacy summary",
        "project_id": 1,
        "parent_id": None,
        "created_at": "2025-11-09T12:00:00",
        "updated_at": "2025-11-09T12:00:00",
        "archived_at": None,
    }
    mock_db.get_recent_thread.return_value = None
    mock_db.count_messages.return_value = 0
    mock_db.ensure_default_project.return_value = 1
    mock_db.write_audit_log.return_value = None

    monkeypatch.setattr(chat_routes, "chatlog_db", mock_db)

    result = chat_routes.chat_create_thread(
        {"title": "Legacy Thread"},
        api_key="test-api-key",
        request_user_scope=RequestUserScope(
            user_id=expected_user_id,
            account_id=expected_user_id,
            multi_user_enabled=False,
        ),
    )

    assert result["ok"] is True
    assert result["id"] == 17
    assert result["thread"]["user_id"] == expected_user_id
    mock_db.create_chat_thread.assert_called_once()
    assert "thread_config" not in mock_db.create_chat_thread.call_args.kwargs
