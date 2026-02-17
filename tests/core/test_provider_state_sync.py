from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.core.provider_state import (
    LAUNCH_PROVIDER_IDS,
    provider_seed_rows_from_catalog,
    sync_inference_provider_rows,
)
from guardian.db.models import Base, InferenceProvider, InferenceProviderRuntime


def _catalog_payload() -> dict:
    return {
        "providers": [
            {
                "id": "openai",
                "displayName": "OpenAI",
                "enabled": False,
                "authorized": False,
                "available": False,
                "disabled_reason": "Missing provider credentials",
                "models": [
                    {
                        "id": "gpt-4o",
                        "capabilities": {
                            "vision": True,
                            "tools": True,
                            "streaming": True,
                        },
                    }
                ],
            },
            {
                "id": "groq",
                "displayName": "Groq",
                "enabled": True,
                "authorized": True,
                "available": True,
                "models": [
                    {
                        "id": "llama-3.1-70b-versatile",
                        "capabilities": {
                            "vision": False,
                            "tools": False,
                            "streaming": True,
                        },
                    }
                ],
            },
            {
                "id": "local",
                "displayName": "Local",
                "enabled": True,
                "authorized": True,
                "available": True,
                "models": [{"id": "qwen2.5:latest"}],
            },
            {
                "id": "minimax",
                "displayName": "MiniMax",
                "enabled": False,
                "authorized": False,
                "available": False,
                "models": [{"id": "minimax-text-01"}],
            },
        ]
    }


def _session_factory():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        bind=engine,
        tables=[
            InferenceProvider.__table__,
            InferenceProviderRuntime.__table__,
        ],
    )
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def test_provider_seed_rows_from_catalog_is_launch_scoped() -> None:
    rows = provider_seed_rows_from_catalog(_catalog_payload())
    assert [row["provider_id"] for row in rows] == list(LAUNCH_PROVIDER_IDS)

    by_id = {row["provider_id"]: row for row in rows}
    assert by_id["groq"]["enabled"] is True
    assert by_id["groq"]["priority"] == 10
    assert by_id["openai"]["enabled"] is False
    assert by_id["openai"]["default_model_id"] == "gpt-4o"
    assert by_id["openai"]["capabilities"]["vision"] is True
    assert by_id["anthropic"]["enabled"] is False
    assert by_id["gemini"]["enabled"] is False


def test_sync_inference_provider_rows_is_idempotent() -> None:
    SessionLocal = _session_factory()
    rows = provider_seed_rows_from_catalog(_catalog_payload())

    with SessionLocal() as session:
        first = sync_inference_provider_rows(session, rows)
        session.commit()
        assert first["provider_rows"] == 5
        assert first["providers_created"] == 5
        assert first["runtime_created"] == 5

    with SessionLocal() as session:
        groq_runtime = session.get(InferenceProviderRuntime, "groq")
        assert groq_runtime is not None
        groq_runtime.health_status = "degraded"
        groq_runtime.consecutive_failures = 3
        session.commit()

    with SessionLocal() as session:
        second = sync_inference_provider_rows(session, rows)
        session.commit()
        assert second["provider_rows"] == 5
        assert second["providers_created"] == 0
        assert second["runtime_created"] == 0

    with SessionLocal() as session:
        providers = session.query(InferenceProvider).all()
        runtime_rows = session.query(InferenceProviderRuntime).all()
        assert len(providers) == 5
        assert len(runtime_rows) == 5

        groq_runtime = session.get(InferenceProviderRuntime, "groq")
        assert groq_runtime is not None
        assert groq_runtime.health_status == "degraded"
        assert groq_runtime.consecutive_failures == 3
