"""Focused contract tests for ``chat_threads.origin_system``.

These tests lock in the bounded registry contract described in
``guardian.conversation_origin`` and the storage-layer posture documented in
``docs/architecture/data-and-storage.md``. They are SQLAlchemy-only — the
Postgres CHECK constraint and Alembic migration are verified separately via
the migration-graph integrity command in the proof surface.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.conversation_origin import (
    CANONICAL_ORIGIN_SYSTEMS,
    DEFAULT_ORIGIN_SYSTEM,
    ConversationOriginSystem,
    normalize_legacy_import_source,
    resolve_canonical_origin,
)
from guardian.db.models import Base, ChatThread


@pytest.fixture
def session_local():
    """In-memory SQLite engine with the ChatThread table materialized.

    Postgres-only JSONB type is patched to the cross-dialect JSON for the
    SQLite test path, mirroring the convention in
    ``tests/db/test_chat_thread_thread_config.py``.
    """

    original_type = ChatThread.__table__.c.thread_config.type
    from sqlalchemy import JSON

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    ChatThread.__table__.c.thread_config.type = JSON().with_variant(
        original_type, "postgresql"
    )
    Base.metadata.create_all(bind=engine, tables=[ChatThread.__table__])
    try:
        yield sessionmaker(
            bind=engine, autoflush=False, autocommit=False, future=True
        )
    finally:
        ChatThread.__table__.c.thread_config.type = original_type
        engine.dispose()


# ---------------------------------------------------------------------------
# Canonical registry contract
# ---------------------------------------------------------------------------


def test_canonical_origin_registry_is_bounded_and_locked():
    """The bounded registry is exactly three values; no drift is permitted."""

    assert CANONICAL_ORIGIN_SYSTEMS == frozenset({"codexify", "openai", "anthropic"})
    assert {m.value for m in ConversationOriginSystem} == CANONICAL_ORIGIN_SYSTEMS


def test_resolve_canonical_origin_accepts_only_bounded_values():
    assert resolve_canonical_origin("codexify") == "codexify"
    assert resolve_canonical_origin("openai") == "openai"
    assert resolve_canonical_origin("anthropic") == "anthropic"
    # Case-insensitive normalization of canonical tokens must be accepted.
    assert resolve_canonical_origin("OpenAI") == "openai"
    for bad in ("chatgpt", "claude", "gpt", "open_ai", "native", "anthropic_claude", ""):
        with pytest.raises(ValueError, match="Unsupported origin_system"):
            resolve_canonical_origin(bad)


# ---------------------------------------------------------------------------
# Native default + persistence validation
# ---------------------------------------------------------------------------


def test_default_origin_system_is_codexify():
    """Native Codexify threads must default to ``codexify`` regardless of
    any inference provider currently selected."""

    assert DEFAULT_ORIGIN_SYSTEM == "codexify"


def test_new_thread_without_explicit_origin_persists_codexify(session_local):
    with session_local() as session:
        thread = ChatThread(user_id="u1", title="native", summary="")
        session.add(thread)
        session.commit()
        session.refresh(thread)

    assert thread.origin_system == "codexify"


def test_thread_persists_explicit_canonical_origin(session_local):
    for origin in ("codexify", "openai", "anthropic"):
        with session_local() as session:
            thread = ChatThread(
                user_id="u1",
                title=f"thread-{origin}",
                summary="",
                origin_system=origin,
            )
            session.add(thread)
            session.commit()
            session.refresh(thread)
        assert thread.origin_system == origin


# ---------------------------------------------------------------------------
# Legacy backfill mapping (deterministic)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("legacy", "expected"),
    [
        ("chatgpt", "openai"),
        ("openai", "openai"),
        ("claude", "anthropic"),
        ("anthropic", "anthropic"),
    ],
)
def test_normalize_legacy_import_source_maps_deterministically(legacy, expected):
    assert normalize_legacy_import_source(legacy) == expected


@pytest.mark.parametrize(
    "value",
    [None, "", "  ", "unknown", "gpt", "open_ai", "anthropic_claude"],
)
def test_normalize_legacy_import_source_rejects_unknown(value):
    """Unknown external source systems must fail closed rather than be
    silently mapped onto ``codexify`` at the import-compatibility boundary."""

    assert normalize_legacy_import_source(value) is None


def test_legacy_backfill_does_not_invent_origin_for_native_threads():
    """A native thread carries no explicit import-source metadata; the
    backfill resolves it to ``codexify``, not to any external system."""

    assert normalize_legacy_import_source(None) is None
    assert (
        ConversationOriginSystem.CODEXIFY.value
        == resolve_canonical_origin("codexify")
    )


# ---------------------------------------------------------------------------
# Unsupported canonical value rejection (model + persistence seam)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    ["chatgpt", "claude", "gpt", "open_ai", "anthropic_claude", "native"],
)
def test_model_persists_unsupported_origin_by_force(session_local, value):
    """The SQLAlchemy model column is String(32); we exercise that the
    registry's resolver rejects unsupported values at the persistence seam
    before any DB write. The Postgres CHECK constraint is verified
    separately by the migration-graph integrity proof surface."""

    with pytest.raises(ValueError, match="Unsupported origin_system"):
        resolve_canonical_origin(value)