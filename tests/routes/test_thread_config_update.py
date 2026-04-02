from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace

import pytest
from sqlalchemy import JSON, create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.core.chat_completion_service import (
    resolve_thread_completion_settings,
)
from guardian.core.pgdb import PgDB
from guardian.db.models import Base, ChatThread
from guardian.routes import chat as chat_routes


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


class _ThreadConfigRouteBackend(PgDB):
    def __init__(self, session_factory):
        self._SessionLocal = session_factory
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

    def get_chat_thread(self, thread_id: int):
        with self._sa_session() as session:
            thread = session.get(ChatThread, thread_id)
            if thread is None:
                return None
            return {
                "id": thread.id,
                "user_id": thread.user_id,
                "title": thread.title,
                "summary": thread.summary,
                "project_id": thread.project_id,
                "parent_id": thread.parent_id,
                "archived_at": thread.archived_at,
                "thread_config": thread.thread_config,
                "created_at": thread.created_at,
                "updated_at": thread.updated_at,
            }

    def write_audit_log(self, *args, **kwargs):
        self.audit_log_calls.append((args, kwargs))
        return None


@pytest.fixture
def thread_config_backend():
    with _thread_config_session_factory() as session_factory:
        yield _ThreadConfigRouteBackend(session_factory), session_factory


def _seed_thread(
    session_factory,
    *,
    thread_config,
    title: str = "Seed Thread",
) -> int:
    with session_factory() as session:
        thread = ChatThread(
            user_id="test_user",
            title=title,
            summary="Seed summary",
            project_id=None,
            thread_config=thread_config,
        )
        session.add(thread)
        session.flush()
        thread_id = int(thread.id)
        session.commit()
        return thread_id


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
        "DEFAULT_LOCAL_MODEL",
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


def test_thread_config_patch_persists_full_update_and_drives_completion_settings(
    test_client,
    thread_config_backend,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend, session_factory = thread_config_backend
    monkeypatch.setattr(chat_routes, "chatlog_db", backend)
    _set_groq_runtime_defaults(monkeypatch)

    thread_id = _seed_thread(session_factory, thread_config=None)
    payload = {
        "providerId": "local",
        "modelId": "qwen3.5:14b",
        "inferenceMode": "fast",
        "retrievalSource": "project",
        "personaId": "persona-7",
    }

    response = test_client.patch(
        f"/chat/threads/{thread_id}/config",
        json=payload,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["thread_id"] == thread_id
    assert data["thread_config"] == payload

    thread = _fetch_thread(session_factory, thread_id)
    assert thread.thread_config == payload

    resolved = resolve_thread_completion_settings(
        {
            "id": thread_id,
            "thread_config": thread.thread_config,
        },
        requested_provider="groq",
        requested_model="override-model",
        requested_reasoning_mode="think",
        requested_source_mode="personal_knowledge",
        settings=SimpleNamespace(
            LLM_PROVIDER="groq",
            LOCAL_LLM_MODEL="runtime-local-model",
            DEFAULT_LOCAL_MODEL="runtime-local-model",
            LLM_MODEL="runtime-local-model",
        ),
    )

    assert resolved.provider == "local"
    assert resolved.model == "qwen3.5:14b"
    assert resolved.reasoning_mode == "fast"
    assert resolved.source_mode == "project"
    assert resolved.persona_id == "persona-7"
    assert resolved.has_thread_config is True


def test_thread_config_patch_preserves_existing_fields_on_partial_update(
    test_client,
    thread_config_backend,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend, session_factory = thread_config_backend
    monkeypatch.setattr(chat_routes, "chatlog_db", backend)
    _set_local_runtime_defaults(monkeypatch)

    initial_config = {
        "providerId": "local",
        "modelId": "qwen3.5:14b",
        "inferenceMode": "fast",
        "retrievalSource": "project",
        "personaId": "persona-7",
    }
    thread_id = _seed_thread(session_factory, thread_config=initial_config)

    response = test_client.patch(
        f"/chat/threads/{thread_id}/config",
        json={"modelId": "qwen3.5:0.8b"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["thread_config"] == {
        "providerId": "local",
        "modelId": "qwen3.5:0.8b",
        "inferenceMode": "fast",
        "retrievalSource": "project",
        "personaId": "persona-7",
    }

    thread = _fetch_thread(session_factory, thread_id)
    assert thread.thread_config == {
        "providerId": "local",
        "modelId": "qwen3.5:0.8b",
        "inferenceMode": "fast",
        "retrievalSource": "project",
        "personaId": "persona-7",
    }


def test_thread_config_patch_null_existing_config_merges_backend_defaults(
    test_client,
    thread_config_backend,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend, session_factory = thread_config_backend
    monkeypatch.setattr(chat_routes, "chatlog_db", backend)
    _set_local_runtime_defaults(monkeypatch)

    thread_id = _seed_thread(session_factory, thread_config=None)

    response = test_client.patch(
        f"/chat/threads/{thread_id}/config",
        json={"personaId": None},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["thread_config"] == {
        "providerId": "local",
        "modelId": "qwen3.5:14b",
        "inferenceMode": "fast",
        "retrievalSource": "project",
        "personaId": None,
    }

    thread = _fetch_thread(session_factory, thread_id)
    assert thread.thread_config == {
        "providerId": "local",
        "modelId": "qwen3.5:14b",
        "inferenceMode": "fast",
        "retrievalSource": "project",
        "personaId": None,
    }


@pytest.mark.parametrize(
    "payload",
    [
        {"unexpected": "value"},
        {"providerId": 123},
    ],
)
def test_thread_config_patch_rejects_invalid_payload_shapes(
    test_client,
    thread_config_backend,
    monkeypatch: pytest.MonkeyPatch,
    payload,
) -> None:
    backend, session_factory = thread_config_backend
    monkeypatch.setattr(chat_routes, "chatlog_db", backend)
    _set_local_runtime_defaults(monkeypatch)

    thread_id = _seed_thread(session_factory, thread_config=None)

    response = test_client.patch(
        f"/chat/threads/{thread_id}/config",
        json=payload,
    )

    assert response.status_code == 422
