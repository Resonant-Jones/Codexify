"""Focused inference accounting, missing-usage, idempotency, and isolation tests."""

from __future__ import annotations

from contextlib import contextmanager
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import JSON, create_engine, event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.db.models import (
    Base, ChatThread, InferenceUsageEvent, PersonaProfile,
    PersonaProfileRevision, Project, User,
)
from guardian.metering.ledger import (
    account_inference_totals,
    estimate_cost,
    extract_provider_usage,
    record_inference_attempt,
)
from guardian.metering.tokens import InferenceUsageSource


def _response(usage=None, *, request_id="provider-1"):
    return SimpleNamespace(raw_payload={"id": request_id, **(
        {"usage": usage} if usage is not None else {}
    )})


@contextmanager
def _sessions():
    column = InferenceUsageEvent.__table__.c.price_snapshot
    original_type = column.type
    thread_config_column = ChatThread.__table__.c.thread_config
    original_thread_type = thread_config_column.type
    column.type = JSON().with_variant(JSONB, "postgresql")
    thread_config_column.type = JSON().with_variant(JSONB, "postgresql")
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _connection_record):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")
    try:
        Base.metadata.create_all(
            engine, tables=[
                User.__table__, Project.__table__, PersonaProfile.__table__,
                PersonaProfileRevision.__table__, ChatThread.__table__,
                InferenceUsageEvent.__table__,
            ],
        )
        SessionLocal = sessionmaker(bind=engine, future=True)
        with SessionLocal.begin() as session:
            for account in ("one", "two"):
                session.add(User(
                    id=account, username=account,
                    password_hash="unused", role="guest",
                ))
                session.add(ChatThread(
                    id=1 if account == "one" else 2,
                    user_id=account, title="thread",
                ))
        yield SessionLocal
    finally:
        column.type = original_type
        thread_config_column.type = original_thread_type
        engine.dispose()


def test_provider_usage_and_price_snapshot():
    usage = extract_provider_usage(_response({
        "prompt_tokens": 1000, "completion_tokens": 200,
        "prompt_cache_hit_tokens": 300, "total_tokens": 1200,
    }))
    assert usage.source is InferenceUsageSource.PROVIDER_REPORTED
    cost, quote = estimate_cost(
        usage=usage, provider="deepseek", model="deepseek-chat",
        price_book={"deepseek:deepseek-chat": {
            "version": "manual-2026-11-01",
            "input_usd_per_million": "1",
            "output_usd_per_million": "2",
            "cached_input_usd_per_million": "0.1",
        }},
    )
    assert cost == Decimal("0.001130000")
    assert quote["version"] == "manual-2026-11-01"


def test_missing_and_partial_usage_never_invent_zero_cost():
    for payload, expected in [
        (_response(), InferenceUsageSource.UNAVAILABLE),
        (_response({"prompt_tokens": 12}), InferenceUsageSource.PARTIAL),
        (_response({"prompt_tokens": -1, "completion_tokens": True}), InferenceUsageSource.UNAVAILABLE),
    ]:
        usage = extract_provider_usage(payload)
        assert usage.source is expected
        cost, snapshot = estimate_cost(
            usage=usage, provider="deepseek", model="deepseek-chat",
            price_book={"deepseek:deepseek-chat": {
                "version": "v1", "input_usd_per_million": "1",
                "output_usd_per_million": "2",
            }},
        )
        assert cost is None
        assert snapshot == {}


def test_idempotency_isolation_and_aggregation():
    with _sessions() as SessionLocal:
        kwargs = dict(
            account_id="one", thread_id=1, request_id="request-1",
            provider_attempt_id="attempt-1",
            provider="deepseek", model="deepseek-chat",
            output=_response({"prompt_tokens": 100, "completion_tokens": 10}),
            price_book={"deepseek:deepseek-chat": {
                "version": "v1", "input_usd_per_million": "1",
                "output_usd_per_million": "2",
            }},
        )
        with SessionLocal.begin() as session:
            first = record_inference_attempt(session, **kwargs)
            assert first.input_tokens == 100
            first_id = first.id
        with SessionLocal.begin() as session:
            again = record_inference_attempt(session, **kwargs)
            assert again.id == first_id
        with SessionLocal.begin() as session:
            with pytest.raises(ValueError, match="idempotency_conflict"):
                record_inference_attempt(
                    session, **(kwargs | {
                        "output": _response({
                            "prompt_tokens": 101, "completion_tokens": 10,
                        })
                    })
                )
        with SessionLocal.begin() as session:
            with pytest.raises(PermissionError, match="account_thread_mismatch"):
                record_inference_attempt(
                    session, **(kwargs | {
                        "account_id": "two",
                        "provider_attempt_id": "attempt-2",
                    })
                )
        with SessionLocal.begin() as session:
            record_inference_attempt(
                session, **(kwargs | {
                    "account_id": "two", "thread_id": 2,
                    "provider_attempt_id": "attempt-2",
                    "output": _response(),
                })
            )
        with SessionLocal() as session:
            one = account_inference_totals(session, account_id="one")
            two = account_inference_totals(session, account_id="two")
            assert len(one) == len(two) == 1
            assert one[0]["attempts"] == 1
            assert one[0]["estimated_cost_usd"] == "0.000120000"
            assert one[0]["cost_is_complete"] is True
            assert two[0]["unpriced_attempts"] == 1
            assert two[0]["cost_is_complete"] is False
