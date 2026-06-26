"""Tests for Continuity write-action service (guardian.continuity.write_actions).

These tests verify import safety, dataclass behaviour, receipt correctness,
and — using a fake adapter — that the four allowed write actions produce the
expected receipts without calling runtime modules, graph, or providers.

Live Postgres integration tests run when GUARDIAN_DATABASE_URL is available.
"""

from __future__ import annotations

import ast
import inspect
import os
from unittest.mock import MagicMock, call, patch

import pytest

from guardian.continuity import write_actions as wa
from guardian.continuity.contracts import (
    ContinuityProvenance,
    ContinuityScope,
    ContinuitySource,
    ContextPacket,
    RealityCommit,
    RealityState,
)
from guardian.continuity.persistence import (
    ContinuityPersistenceAdapter,
    ContinuityPersistenceError,
    ContinuityPersistenceResult,
    StoredContinuityRecord,
)


# ── Fixtures ────────────────────────────────────────────────────────────────


def _actor(**kw) -> wa.ContinuityActionActor:
    defaults = dict(actor_id="test-actor", actor_kind="user")
    defaults.update(kw)
    return wa.ContinuityActionActor(**defaults)


def _packet(**kw) -> ContextPacket:
    defaults = dict(
        packet_id="pkt-1",
        schema_version="1.0",
        kind="thread",
        scope=ContinuityScope(project_id="proj-1"),
        source=ContinuitySource(system="test"),
        created_at="2026-06-25T00:00:00Z",
        summary="Test packet",
        payload={"k": "v"},
    )
    defaults.update(kw)
    return ContextPacket(**defaults)


def _valid_commit(**kw) -> RealityCommit:
    defaults = dict(
        commit_id="commit-1",
        schema_version="1.0",
        scope="project",
        kind="state_update",
        trigger="manual",
        title="Test commit",
        summary="A test commit",
        created_at="2026-06-25T00:00:00Z",
        source_packet_ids=("pkt-1",),
    )
    defaults.update(kw)
    return RealityCommit(**defaults)


def _make_ok_result(**kw) -> ContinuityPersistenceResult:
    defaults = dict(
        success=True,
        operation="save",
        records=(
            StoredContinuityRecord(record_id="rec-1", table="t", operation="save"),
        ),
    )
    defaults.update(kw)
    return ContinuityPersistenceResult(**defaults)


def _make_fail_result(**kw) -> ContinuityPersistenceResult:
    defaults = dict(
        success=False,
        operation="save",
        db_errors=(
            ContinuityPersistenceError(code="DB_ERR", message="boom"),
        ),
    )
    defaults.update(kw)
    return ContinuityPersistenceResult(**defaults)


def _make_val_fail_result(**kw) -> ContinuityPersistenceResult:
    defaults = dict(
        success=False,
        operation="save",
        validation_errors=(
            ContinuityPersistenceError(code="VAL_ERR", message="bad packet"),
        ),
    )
    defaults.update(kw)
    return ContinuityPersistenceResult(**defaults)


@pytest.fixture
def mock_adapter():
    return MagicMock(spec=ContinuityPersistenceAdapter)


@pytest.fixture
def svc(mock_adapter):
    return wa.ContinuityWriteActionService(mock_adapter)


# ── 1. Import safety ────────────────────────────────────────────────────────


def test_import_succeeds():
    assert wa is not None


def test_exports_exist():
    assert wa.ContinuityWriteActionService is not None
    assert wa.ContinuityWriteReceipt is not None
    assert wa.RealityStampInput is not None
    assert wa.RealityStateWriteInput is not None
    assert wa.RealityCommitWriteInput is not None
    assert wa.StatePacketLinkInput is not None


def test_no_runtime_imports():
    source = inspect.getsource(wa)
    tree = ast.parse(source)
    forbidden = [
        "guardian.routes",
        "guardian.workers",
        "guardian.queue",
        "guardian.context",
        "guardian.vector",
        "guardian.core.ai_router",
        "redis",
        "neo4j",
        "requests",
        "httpx",
        "fastapi",
    ]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                for f in forbidden:
                    assert alias.name != f and not alias.name.startswith(f + ".")
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                for f in forbidden:
                    assert node.module != f and not node.module.startswith(f + ".")


# ── 2. Dataclasses and receipt ──────────────────────────────────────────────


def test_action_inputs_are_frozen():
    with pytest.raises(Exception):
        wa.RealityStampInput(
            action_id="a", actor=_actor(), packet_id="p", schema_version="1",
            scope=ContinuityScope(), source=ContinuitySource(system="t"),
            created_at="", summary="s",
        ).packet_id = "mutated"  # type: ignore[misc]


def test_receipt_defaults():
    r = wa.ContinuityWriteReceipt(
        action_id="a", action_kind="create_reality_stamp", success=True
    )
    assert r.graph_used is False
    assert r.runtime_event_published is False


def test_receipt_is_failure():
    ok = wa.ContinuityWriteReceipt(
        action_id="a", action_kind="create_reality_stamp", success=True
    )
    fail = wa.ContinuityWriteReceipt(
        action_id="a", action_kind="create_reality_stamp", success=False
    )
    assert ok.is_failure is False
    assert fail.is_failure is True


def test_receipt_is_frozen():
    r = wa.ContinuityWriteReceipt(
        action_id="a", action_kind="create_reality_stamp", success=True
    )
    with pytest.raises(Exception):
        r.success = False  # type: ignore[misc]


# ── 3. create_reality_stamp (fake adapter) ──────────────────────────────────


def test_stamp_success(mock_adapter, svc):
    mock_adapter.save_context_packet.return_value = _make_ok_result()
    action = wa.RealityStampInput(
        action_id="act-1", actor=_actor(), packet_id="pkt-1",
        schema_version="1.0", scope=ContinuityScope(project_id="p"),
        source=ContinuitySource(system="test"),
        created_at="2026-01-01T00:00:00Z", summary="Stamp",
    )
    receipt = svc.create_reality_stamp(action)
    assert receipt.success is True
    assert receipt.action_kind == "create_reality_stamp"
    assert len(receipt.created_packet_ids) > 0
    assert receipt.graph_used is False
    assert receipt.runtime_event_published is False


def test_stamp_adapter_failure(mock_adapter, svc):
    mock_adapter.save_context_packet.return_value = _make_fail_result()
    action = wa.RealityStampInput(
        action_id="act-1", actor=_actor(), packet_id="pkt-1",
        schema_version="1.0", scope=ContinuityScope(project_id="p"),
        source=ContinuitySource(system="test"),
        created_at="2026-01-01T00:00:00Z", summary="Stamp",
    )
    receipt = svc.create_reality_stamp(action)
    assert receipt.success is False
    assert len(receipt.persistence_errors) > 0


def test_stamp_validation_failure(mock_adapter, svc):
    mock_adapter.save_context_packet.return_value = _make_val_fail_result()
    action = wa.RealityStampInput(
        action_id="act-1", actor=_actor(), packet_id="pkt-1",
        schema_version="1.0", scope=ContinuityScope(project_id="p"),
        source=ContinuitySource(system="test"),
        created_at="2026-01-01T00:00:00Z", summary="Stamp",
    )
    receipt = svc.create_reality_stamp(action)
    assert receipt.success is False


# ── 4. compile_and_save_reality_state (fake adapter) ────────────────────────


def test_compile_save_success(mock_adapter, svc):
    mock_adapter.save_reality_state.return_value = _make_ok_result(
        records=(StoredContinuityRecord(record_id="state-1", table="t", operation="save"),)
    )
    mock_adapter.link_state_packets.return_value = _make_ok_result(
        records=(StoredContinuityRecord(record_id="link-1", table="t", operation="save"),)
    )
    action = wa.RealityStateWriteInput(
        action_id="act-2", actor=_actor(),
        packets=(_packet(),),
        scope="project",
    )
    receipt = svc.compile_and_save_reality_state_from_explicit_packets(action)
    assert receipt.success is True
    assert len(receipt.created_state_ids) == 1
    assert len(receipt.created_link_ids) == 1
    assert receipt.graph_used is False


def test_compile_error_prevents_persistence(mock_adapter, svc):
    # Compiler errors come from invalid packets handled by the pure compiler.
    # Even with a working adapter, invalid input to compile_reality_state
    # prevents persistence.
    action = wa.RealityStateWriteInput(
        action_id="act-2", actor=_actor(),
        packets=(),  # empty packets → compile error
        scope="project",
    )
    receipt = svc.compile_and_save_reality_state_from_explicit_packets(action)
    assert receipt.success is False
    mock_adapter.save_reality_state.assert_not_called()


def test_compile_save_adapter_failure(mock_adapter, svc):
    mock_adapter.save_reality_state.return_value = _make_fail_result()
    action = wa.RealityStateWriteInput(
        action_id="act-2", actor=_actor(),
        packets=(_packet(),),
        scope="project",
    )
    receipt = svc.compile_and_save_reality_state_from_explicit_packets(action)
    assert receipt.success is False
    mock_adapter.link_state_packets.assert_not_called()


def test_compile_save_link_failure(mock_adapter, svc):
    mock_adapter.save_reality_state.return_value = _make_ok_result(
        records=(StoredContinuityRecord(record_id="state-1", table="t", operation="save"),)
    )
    mock_adapter.link_state_packets.return_value = _make_fail_result()
    action = wa.RealityStateWriteInput(
        action_id="act-2", actor=_actor(),
        packets=(_packet(),),
        scope="project",
    )
    receipt = svc.compile_and_save_reality_state_from_explicit_packets(action)
    assert receipt.success is False


# ── 5. create_reality_commit (fake adapter) ─────────────────────────────────


def test_commit_success(mock_adapter, svc):
    mock_adapter.save_reality_commit.return_value = _make_ok_result(
        records=(StoredContinuityRecord(record_id="commit-1", table="t", operation="save"),)
    )
    action = wa.RealityCommitWriteInput(
        action_id="act-3", actor=_actor(),
        commit=_valid_commit(),
    )
    receipt = svc.create_reality_commit(action)
    assert receipt.success is True
    assert len(receipt.created_commit_ids) == 1
    assert receipt.graph_used is False


def test_commit_adapter_failure(mock_adapter, svc):
    mock_adapter.save_reality_commit.return_value = _make_fail_result()
    action = wa.RealityCommitWriteInput(
        action_id="act-3", actor=_actor(),
        commit=_valid_commit(),
    )
    receipt = svc.create_reality_commit(action)
    assert receipt.success is False


def test_commit_with_links(mock_adapter, svc):
    mock_adapter.save_reality_commit.return_value = _make_ok_result(
        records=(StoredContinuityRecord(record_id="commit-1", table="t", operation="save"),)
    )
    mock_adapter.link_state_packets.return_value = _make_ok_result(
        records=(StoredContinuityRecord(record_id="link-1", table="t", operation="save"),)
    )
    commit = _valid_commit(new_state_id="state-1")
    action = wa.RealityCommitWriteInput(
        action_id="act-3", actor=_actor(),
        commit=commit,
        link_packet_ids=("pkt-1",),
    )
    receipt = svc.create_reality_commit(action)
    assert receipt.success is True
    assert len(receipt.created_commit_ids) == 1
    assert len(receipt.created_link_ids) == 1


def test_commit_link_failure(mock_adapter, svc):
    mock_adapter.save_reality_commit.return_value = _make_ok_result(
        records=(StoredContinuityRecord(record_id="commit-1", table="t", operation="save"),)
    )
    mock_adapter.link_state_packets.return_value = _make_fail_result()
    commit = _valid_commit(new_state_id="state-1")
    action = wa.RealityCommitWriteInput(
        action_id="act-3", actor=_actor(),
        commit=commit,
        link_packet_ids=("pkt-1",),
    )
    receipt = svc.create_reality_commit(action)
    assert receipt.success is False


# ── 6. link_state_to_packets (fake adapter) ─────────────────────────────────


def test_link_success(mock_adapter, svc):
    mock_adapter.link_state_packets.return_value = _make_ok_result(
        records=(StoredContinuityRecord(record_id="link-1", table="t", operation="save"),)
    )
    action = wa.StatePacketLinkInput(
        action_id="act-4", actor=_actor(),
        state_id="state-1", packet_ids=("pkt-1",),
    )
    receipt = svc.link_state_to_packets(action)
    assert receipt.success is True
    assert len(receipt.created_link_ids) == 1


def test_link_failure(mock_adapter, svc):
    mock_adapter.link_state_packets.return_value = _make_fail_result()
    action = wa.StatePacketLinkInput(
        action_id="act-4", actor=_actor(),
        state_id="state-1", packet_ids=("pkt-1",),
    )
    receipt = svc.link_state_to_packets(action)
    assert receipt.success is False


# ── 7. No automatic writes ──────────────────────────────────────────────────


def test_no_runtime_strings_in_source():
    source = inspect.getsource(wa)
    forbidden = [
        "guardian.routes",
        "guardian.workers",
        "guardian.queue",
        "guardian.context",
        "guardian.vector",
        "guardian.core.ai_router",
        "redis",
        "neo4j",
        "requests",
        "httpx",
        "fastapi",
    ]
    for word in forbidden:
        assert word not in source, f"write_actions.py contains '{word}'"


# ── 8. Live DB integration (Postgres required) ──────────────────────────────


def _pg_session():
    db_url = os.getenv("GUARDIAN_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not db_url or "sqlite" in db_url.lower():
        return None

    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from guardian.db.models import Base

    try:
        engine = create_engine(db_url, echo=False)
        tables = [
            t for t in Base.metadata.sorted_tables
            if t.name.startswith("continuity_")
        ]
        Base.metadata.create_all(engine, tables=tables)
        return Session(engine)
    except Exception:
        return None


@pytest.fixture(scope="module")
def pg_session():
    s = _pg_session()
    if s is None:
        pytest.skip("Postgres not available")
    yield s
    s.close()


@pytest.fixture
def live_svc(pg_session):
    from guardian.continuity.persistence import ContinuityPersistenceAdapter

    from guardian.db.models import (
        ContinuityContextPacket,
        ContinuityRealityCommit,
        ContinuityRealityState,
        ContinuityStatePacketLink,
    )

    adapter = ContinuityPersistenceAdapter(pg_session)
    # Clean up from any previous test run
    pg_session.query(ContinuityStatePacketLink).delete()
    pg_session.query(ContinuityRealityCommit).delete()
    pg_session.query(ContinuityRealityState).delete()
    pg_session.query(ContinuityContextPacket).delete()
    pg_session.commit()

    svc = wa.ContinuityWriteActionService(adapter)
    yield svc
    pg_session.rollback()


def test_live_reality_stamp(live_svc):
    action = wa.RealityStampInput(
        action_id="live-stamp-1",
        actor=_actor(),
        packet_id="live-pkt",
        schema_version="1.0",
        scope=ContinuityScope(project_id="live-proj"),
        source=ContinuitySource(system="test"),
        created_at="2026-06-25T00:00:00Z",
        summary="Live stamp test",
        payload={"test": True},
    )
    receipt = live_svc.create_reality_stamp(action)
    assert receipt.success is True, f"errors={receipt.persistence_errors}"
    assert len(receipt.created_packet_ids) == 1
    assert receipt.graph_used is False


def test_live_compile_and_save(live_svc):
    # First create a packet via stamp
    stamp = wa.RealityStampInput(
        action_id="live-compile-stamp",
        actor=_actor(),
        packet_id="live-compile-pkt",
        schema_version="1.0",
        scope=ContinuityScope(project_id="live-proj"),
        source=ContinuitySource(system="test"),
        created_at="2026-06-25T00:00:00Z",
        summary="Compile test packet",
    )
    live_svc.create_reality_stamp(stamp)

    # Now compile state from it
    packets = (_packet(packet_id="live-compile-pkt"),)
    action = wa.RealityStateWriteInput(
        action_id="live-compile-1",
        actor=_actor(),
        packets=packets,
        scope="project",
    )
    receipt = live_svc.compile_and_save_reality_state_from_explicit_packets(action)
    assert receipt.success is True, (
        f"validation={receipt.validation_errors} "
        f"persistence={receipt.persistence_errors}"
    )
    assert len(receipt.created_state_ids) == 1
    assert receipt.graph_used is False
