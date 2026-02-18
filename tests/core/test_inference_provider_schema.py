from __future__ import annotations

from sqlalchemy import CheckConstraint, create_engine, inspect
from sqlalchemy.pool import StaticPool

from guardian.db.models import Base, InferenceProvider, InferenceProviderRuntime


def test_inference_provider_schema_contract() -> None:
    provider_cols = set(InferenceProvider.__table__.columns.keys())
    runtime_cols = set(InferenceProviderRuntime.__table__.columns.keys())

    assert provider_cols == {
        "provider_id",
        "display_name",
        "provider_type",
        "enabled",
        "priority",
        "default_model_id",
        "capabilities",
        "metadata",
        "created_at",
        "updated_at",
    }
    assert runtime_cols == {
        "provider_id",
        "health_status",
        "consecutive_failures",
        "last_success_at",
        "last_failure_at",
        "cooldown_until",
        "avg_latency_ms",
        "error_rate",
        "updated_at",
    }

    provider_indexes = {idx.name for idx in InferenceProvider.__table__.indexes}
    runtime_indexes = {
        idx.name for idx in InferenceProviderRuntime.__table__.indexes
    }
    assert "ix_inference_providers_enabled" in provider_indexes
    assert "ix_inference_providers_priority" in provider_indexes
    assert "ix_inference_provider_runtime_health_status" in runtime_indexes

    runtime_check_names = {
        c.name
        for c in InferenceProviderRuntime.__table__.constraints
        if isinstance(c, CheckConstraint) and c.name
    }
    assert "ck_inference_provider_runtime_health_status" in runtime_check_names


def test_inference_provider_tables_create_on_sqlite() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            InferenceProvider.__table__,
            InferenceProviderRuntime.__table__,
        ],
    )

    inspector = inspect(engine)
    assert "inference_providers" in inspector.get_table_names()
    assert "inference_provider_runtime" in inspector.get_table_names()
