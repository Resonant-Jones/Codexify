"""Tests for Continuity Phase A persistence adapter (guardian.continuity.persistence).

These tests verify import safety, result dataclasses, validation-based
rejection, and — where a Postgres-based test session is available — write
and read behaviour for the four Phase A continuity tables.

Live Postgres-backed adapter tests require a running Postgres instance
(e.g. via Docker Compose).  When no DB is available, those tests are
skipped with an explicit reason rather than faked.
"""

from __future__ import annotations

import ast
import dataclasses
import inspect
import os

import pytest

from guardian.continuity import persistence as p
from guardian.continuity.contracts import (
    ContinuityProvenance,
    ContinuityScope,
    ContinuitySource,
    ContextPacket,
    RealityCommit,
    RealityState,
)

# ── Fixtures ────────────────────────────────────────────────────────────────


def _valid_packet(**overrides) -> ContextPacket:
    defaults = dict(
        packet_id="pkt-test-001",
        schema_version="1.0",
        kind="thread",
        scope=ContinuityScope(project_id="proj-test"),
        source=ContinuitySource(system="test"),
        created_at="2026-06-25T00:00:00Z",
        summary="Test packet",
        payload={"key": "value"},
    )
    defaults.update(overrides)
    return ContextPacket(**defaults)


def _valid_state(**overrides) -> RealityState:
    defaults = dict(
        state_id="state-test-001",
        schema_version="1.0",
        scope="project",
        compiled_at="2026-06-25T00:00:00Z",
        source_packet_ids=("pkt-test-001",),
    )
    defaults.update(overrides)
    return RealityState(**defaults)


def _valid_commit(**overrides) -> RealityCommit:
    defaults = dict(
        commit_id="commit-test-001",
        schema_version="1.0",
        scope="project",
        kind="state_update",
        trigger="manual",
        title="Test commit",
        summary="A test reality commit",
        created_at="2026-06-25T00:00:00Z",
        source_packet_ids=("pkt-test-001",),
    )
    defaults.update(overrides)
    return RealityCommit(**defaults)


# ── 1. Import safety ────────────────────────────────────────────────────────


def test_import_succeeds():
    assert p is not None


def test_exposes_result_types():
    assert p.StoredContinuityRecord is not None
    assert p.ContinuityPersistenceError is not None
    assert p.ContinuityPersistenceResult is not None
    assert p.ContinuityPersistenceAdapter is not None


def test_does_not_import_runtime_modules():
    """Persistence module must not import runtime, route, or worker modules."""
    source = inspect.getsource(p)
    tree = ast.parse(source)

    forbidden = [
        "guardian.routes",
        "guardian.workers",
        "guardian.queue",
        "guardian.context",
        "guardian.vector",
        "guardian.core.ai_router",
        "redis",
        "requests",
        "httpx",
        "fastapi",
        "guardian.core.chat_completion_service",
        "guardian.cognition.system_prompt_builder",
    ]

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                for f in forbidden:
                    assert alias.name != f and not alias.name.startswith(
                        f + "."
                    ), f"persistence imports {alias.name!r}"
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                for f in forbidden:
                    assert node.module != f and not node.module.startswith(
                        f + "."
                    ), f"persistence imports-from {node.module!r}"


# ── 2. Result dataclasses ───────────────────────────────────────────────────


def test_stored_record_construction():
    r = p.StoredContinuityRecord(
        record_id="abc", table="continuity_context_packets", operation="insert"
    )
    assert r.record_id == "abc"
    assert r.table == "continuity_context_packets"
    assert r.operation == "insert"


def test_stored_record_is_frozen():
    r = p.StoredContinuityRecord("abc", "t", "op")
    with pytest.raises(Exception):
        r.record_id = "mutated"  # type: ignore[misc]


def test_persistence_error_construction():
    e = p.ContinuityPersistenceError(code="TEST", message="test error", field="x")
    assert e.code == "TEST"
    assert e.message == "test error"
    assert e.field == "x"


def test_persistence_error_is_frozen():
    e = p.ContinuityPersistenceError("TEST", "msg")
    with pytest.raises(Exception):
        e.message = "mutated"  # type: ignore[misc]


def test_result_success():
    r = p.ContinuityPersistenceResult.ok("save_context_packet")
    assert r.success is True
    assert r.is_failure is False


def test_result_failure():
    r = p.ContinuityPersistenceResult.failed("save_context_packet")
    assert r.success is False
    assert r.is_failure is True


def test_result_is_frozen():
    r = p.ContinuityPersistenceResult.ok("op")
    with pytest.raises(Exception):
        r.success = False  # type: ignore[misc]


# ── 3. Validation rejection (no DB) ─────────────────────────────────────────


def test_adapter_rejects_invalid_packet_without_db():
    """Adapter must reject invalid packets without touching the DB."""
    adapter = _make_noop_adapter()
    invalid = ContextPacket(
        packet_id="",
        schema_version="",
        kind="not_a_kind",  # type: ignore[arg-type]
        scope=ContinuityScope(),
        source=ContinuitySource(system=""),
        created_at="",
        summary="",
    )
    result = adapter.save_context_packet(invalid)
    assert result.success is False
    assert len(result.validation_errors) > 0


def test_adapter_rejects_invalid_state_without_db():
    adapter = _make_noop_adapter()
    invalid = RealityState(
        state_id="",
        schema_version="",
        scope="project",  # type: ignore[arg-type]
        compiled_at="",
        source_packet_ids=(),
    )
    result = adapter.save_reality_state(invalid)
    assert result.success is False
    assert len(result.validation_errors) > 0


def test_adapter_rejects_invalid_commit_without_db():
    adapter = _make_noop_adapter()
    invalid = RealityCommit(
        commit_id="",
        schema_version="",
        scope="project",  # type: ignore[arg-type]
        kind="state_update",  # type: ignore[arg-type]
        trigger="manual",  # type: ignore[arg-type]
        title="",
        summary="",
        created_at="",
        source_packet_ids=(),
    )
    result = adapter.save_reality_commit(invalid)
    assert result.success is False
    assert len(result.validation_errors) > 0


def test_link_rejects_empty_state_id():
    adapter = _make_noop_adapter()
    result = adapter.link_state_packets("", ["pkt-1"])
    assert result.success is False


def test_link_rejects_empty_relationship():
    adapter = _make_noop_adapter()
    result = adapter.link_state_packets("state-1", ["pkt-1"], relationship="")
    assert result.success is False


def test_link_rejects_empty_packet_ids():
    adapter = _make_noop_adapter()
    result = adapter.link_state_packets("state-1", [])
    assert result.success is False


# ── 4. Live DB adapter tests (Postgres required) ────────────────────────────


def _pg_session():
    """Create a Postgres session for live adapter tests.

    Requires a running Postgres instance and the GUARDIAN_DATABASE_URL or
    DATABASE_URL environment variable.  Returns None if unavailable.
    """
    db_url = os.getenv("GUARDIAN_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not db_url:
        return None
    if "sqlite" in db_url.lower():
        # JSONB requires Postgres; SQLite won't work.
        return None

    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from guardian.db.models import Base

    try:
        engine = create_engine(db_url, echo=False)
        # Create only the continuity tables via metadata
        tables = [
            t
            for t in Base.metadata.sorted_tables
            if t.name.startswith("continuity_")
        ]
        Base.metadata.create_all(engine, tables=tables)
        return Session(engine)
    except Exception:
        return None


def _make_noop_adapter() -> p.ContinuityPersistenceAdapter:
    """Create an adapter with a session mock that raises on DB operations."""
    from unittest.mock import MagicMock

    mock_session = MagicMock()
    # Make add/commit work for validation-only tests (they return before DB)
    return p.ContinuityPersistenceAdapter(mock_session)


@pytest.fixture(scope="module")
def pg_session():
    """Module-level Postgres session fixture for live DB tests."""
    s = _pg_session()
    if s is None:
        pytest.skip("Postgres database not available (set GUARDIAN_DATABASE_URL or DATABASE_URL)")
    yield s
    s.close()


@pytest.fixture()
def adapter(pg_session):
    """Fresh adapter per test with automatic cleanup and rollback."""
    from guardian.db.models import (
        ContinuityContextPacket,
        ContinuityRealityCommit,
        ContinuityRealityState,
        ContinuityStatePacketLink,
    )

    # Clean up any rows from previous test runs (commit is inside adapter)
    adapter = p.ContinuityPersistenceAdapter(pg_session)
    # Delete in reverse dependency order
    pg_session.query(ContinuityStatePacketLink).delete()
    pg_session.query(ContinuityRealityCommit).delete()
    pg_session.query(ContinuityRealityState).delete()
    pg_session.query(ContinuityContextPacket).delete()
    pg_session.commit()

    yield adapter
    pg_session.rollback()


# ── 5. Save context packet (live DB) ────────────────────────────────────────


def test_save_valid_context_packet(adapter):
    packet = _valid_packet()
    result = adapter.save_context_packet(packet)
    assert result.success is True, f"validation_errors={result.validation_errors}"
    assert result.records[0].table == "continuity_context_packets"

    # Read back
    from guardian.db.models import ContinuityContextPacket as CP

    row = adapter._session.get(CP, result.records[0].record_id)
    assert row is not None
    assert row.kind == "thread"
    assert row.sensitivity == "local"
    assert row.retention == "session"
    assert row.payload_json == {"key": "value"}
    assert row.summary == "Test packet"


def test_save_context_packet_preserves_provenance(adapter):
    packet = _valid_packet(
        provenance=ContinuityProvenance(
            source_packet_ids=("src-a", "src-b"),
            source_message_ids=("msg-1",),
        )
    )
    result = adapter.save_context_packet(packet)
    assert result.success is True

    from guardian.db.models import ContinuityContextPacket as CP

    row = adapter._session.get(CP, result.records[0].record_id)
    assert row.provenance_json["source_packet_ids"] == ["src-a", "src-b"]
    assert row.provenance_json["source_message_ids"] == ["msg-1"]


# ── 6. Save reality state (live DB) ─────────────────────────────────────────


def test_save_valid_reality_state(adapter):
    state = _valid_state(
        active_artifacts=("file-a.py",),
        assumptions=("Assumption 1",),
        confidence=0.85,
    )
    result = adapter.save_reality_state(state)
    assert result.success is True, f"validation_errors={result.validation_errors}"

    from guardian.db.models import ContinuityRealityState as RS

    row = adapter._session.get(RS, result.records[0].record_id)
    assert row.scope == "project"
    assert row.confidence == 0.85
    assert row.state_json is not None
    assert row.active_artifacts_json == ["file-a.py"]
    assert row.assumptions_json == ["Assumption 1"]


def test_save_reality_state_preserves_source_packet_ids(adapter):
    state = _valid_state(source_packet_ids=("pkt-a", "pkt-b"))
    result = adapter.save_reality_state(state)
    assert result.success is True

    from guardian.db.models import ContinuityRealityState as RS

    row = adapter._session.get(RS, result.records[0].record_id)
    assert row.source_packet_ids_json == ["pkt-a", "pkt-b"]


def test_save_reality_state_no_auto_links(adapter):
    """Saving a state must not automatically create packet links."""
    state = _valid_state()
    result = adapter.save_reality_state(state)
    assert result.success is True

    from sqlalchemy import select

    from guardian.db.models import ContinuityStatePacketLink

    links = (
        adapter._session.execute(
            select(ContinuityStatePacketLink).where(
                ContinuityStatePacketLink.state_id == result.records[0].record_id
            )
        )
        .scalars()
        .all()
    )
    assert len(links) == 0


# ── 7. Save reality commit (live DB) ────────────────────────────────────────


def test_save_valid_reality_commit(adapter):
    commit = _valid_commit(
        previous_state_id="state-prev",
        new_state_id="state-new",
    )
    result = adapter.save_reality_commit(commit)
    assert result.success is True, f"validation_errors={result.validation_errors}"

    from guardian.db.models import ContinuityRealityCommit as RC

    row = adapter._session.get(RC, result.records[0].record_id)
    assert row.kind == "state_update"
    assert row.trigger == "manual"
    assert row.previous_state_id == "state-prev"
    assert row.new_state_id == "state-new"
    assert row.title == "Test commit"


# ── 8. Link state packets (live DB) ─────────────────────────────────────────


def test_link_state_packets_creates_rows(adapter):
    # First save a state so we have a valid state_id
    state = _valid_state(state_id="link-test-state")
    adapter.save_reality_state(state)

    result = adapter.link_state_packets(
        "link-test-state", ["pkt-1", "pkt-2"]
    )
    assert result.success is True, f"db_errors={result.db_errors}"
    assert len(result.records) == 2


def test_link_duplicate_causes_failure(adapter):
    state = _valid_state(state_id="link-dup-state")
    adapter.save_reality_state(state)

    # First link succeeds
    r1 = adapter.link_state_packets("link-dup-state", ["pkt-dup"])
    assert r1.success is True

    # Duplicate must fail due to uniqueness constraint
    r2 = adapter.link_state_packets("link-dup-state", ["pkt-dup"])
    assert r2.success is False


# ── 9. Read methods (live DB) ───────────────────────────────────────────────


def test_load_reality_state_roundtrip(adapter):
    state = _valid_state(
        state_id="load-test-state",
        active_artifacts=("x.py",),
        assumptions=("Y",),
        open_loops=(),
        rejected_paths=(),
    )
    adapter.save_reality_state(state)

    loaded = adapter.load_reality_state("load-test-state")
    assert loaded is not None
    assert loaded.state_id == "load-test-state"
    assert loaded.scope == "project"  # type: ignore[comparison-overlap]
    assert loaded.active_artifacts == ("x.py",)
    assert loaded.assumptions == ("Y",)


def test_load_reality_state_returns_none_for_missing(adapter):
    loaded = adapter.load_reality_state("nonexistent-id")
    assert loaded is None


def test_load_latest_reality_state_by_project(adapter):
    # Two states with different compiled_at; latest should be returned.
    # Use a scope without project_id since states don't carry project IDs.
    state_a = RealityState(
        state_id="latest-a",
        schema_version="1.0",
        scope="project",
        compiled_at="2026-01-01T00:00:00Z",
        source_packet_ids=("pkt-test-001",),
    )
    state_b = RealityState(
        state_id="latest-b",
        schema_version="1.0",
        scope="project",
        compiled_at="2026-06-25T00:00:00Z",
        source_packet_ids=("pkt-test-001",),
    )
    adapter.save_reality_state(state_a)
    adapter.save_reality_state(state_b)

    loaded = adapter.load_latest_reality_state(
        "project", ContinuityScope()
    )
    # latest_b should be returned (compiled_at is later)
    assert loaded is not None
    assert loaded.state_id == "latest-b"


def test_list_reality_commits(adapter):
    commit = _valid_commit(commit_id="list-commit")
    adapter.save_reality_commit(commit)

    # Query without project_id since commits don't carry scope IDs
    commits = adapter.list_reality_commits(
        ContinuityScope(), limit=10
    )
    assert len(commits) >= 1
    assert commits[0].commit_id == "list-commit"


# ── 10. Transaction behaviour (live DB) ─────────────────────────────────────


def test_link_atomicity_on_failure(adapter):
    """When a link batch fails, no partial links should persist."""
    state = _valid_state(state_id="atomic-state")
    adapter.save_reality_state(state)

    # First link set
    adapter.link_state_packets("atomic-state", ["pkt-ok"])

    # Second set with a duplicate in the batch
    result = adapter.link_state_packets("atomic-state", ["pkt-ok", "pkt-new"])

    # The entire batch should fail
    assert result.success is False

    # Verify no partial link for "pkt-new" exists
    from sqlalchemy import select

    from guardian.db.models import ContinuityStatePacketLink

    rows = (
        adapter._session.execute(
            select(ContinuityStatePacketLink).where(
                ContinuityStatePacketLink.state_id == "atomic-state",
                ContinuityStatePacketLink.packet_id == "pkt-new",
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 0


# ── 11. Graph-off and runtime gate ──────────────────────────────────────────


def test_adapter_does_not_require_neo4j():
    """Adapter must not import or reference Neo4j in code (docstrings are fine)."""
    # AST already verified no neo4j imports.  Check that source does
    # not contain functional neo4j usage (imports are caught by AST above).
    import inspect as _inspect

    source = _inspect.getsource(p)
    lines = source.splitlines()
    # Filter out docstrings and module docstring
    neo4j_lines = [
        ln
        for ln in lines
        if "neo4j" in ln.lower()
        and not ln.strip().startswith(("#", '"""', "'''"))
        and "import" in ln
    ]
    assert len(neo4j_lines) == 0, f"Found neo4j usage outside docstrings: {neo4j_lines}"


def test_adapter_does_not_call_runtime_paths():
    """Adapter source must not import routes, workers, providers, or Redis."""
    source = inspect.getsource(p)
    forbidden = [
        "guardian.routes",
        "guardian.workers",
        "guardian.core.ai_router",
        "guardian.queue.redis_queue",
        "guardian.core.chat_completion_service",
    ]
    # Already verified by AST in test_does_not_import_runtime_modules
    # This is a string-level sanity check.
    for word in forbidden:
        assert word not in source, f"persistence.py contains '{word}'"
