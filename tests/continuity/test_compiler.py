"""Contract tests for guardian.continuity.compiler.

These tests verify that the Continuity Compiler contract harness is
deterministic, import-safe, handles edge cases correctly, and performs
no IO, persistence, provider calls, retrieval, or browser access.
"""

from __future__ import annotations

import ast
import inspect
import sys

import pytest

from guardian.continuity import compiler as cc
from guardian.continuity.contracts import (
    ContinuityProvenance,
    ContextPacket,
    DecisionRecord,
    OpenLoopRecord,
    RealityScope,
    RejectedPathRecord,
    validate_reality_state,
)


# ── Packet factories ────────────────────────────────────────────────────────


def _packet(
    packet_id: str = "pkt-001",
    created_at: str = "2026-06-25T00:00:00Z",
    kind: str = "thread",
    summary: str = "A packet",
    payload: dict | None = None,
    provenance: ContinuityProvenance | None = None,
) -> ContextPacket:
    from guardian.continuity.contracts import ContinuityScope, ContinuitySource

    return ContextPacket(
        packet_id=packet_id,
        schema_version="1.0",
        kind=kind,  # type: ignore[arg-type]
        scope=ContinuityScope(project_id="proj-1"),
        source=ContinuitySource(system="test"),
        created_at=created_at,
        summary=summary,
        payload=payload or {},
        provenance=provenance or ContinuityProvenance(),
    )


# ── 1. Import safety ────────────────────────────────────────────────────────


def test_import_succeeds():
    assert cc is not None


def test_public_exports_exist():
    assert callable(cc.compile_reality_state)
    assert callable(cc.packet_sort_key)
    assert callable(cc.extract_string_sequence)
    assert callable(cc.dedupe_preserving_order)
    assert callable(cc.derive_compiled_at)
    assert callable(cc.derive_state_id)
    assert cc.ContinuityCompileResult is not None


def test_does_not_import_runtime_modules():
    """Compiler source must not import DB, Redis, IO, route, or provider modules."""
    source = inspect.getsource(cc)
    tree = ast.parse(source)

    forbidden = [
        "sqlalchemy",
        "redis",
        "requests",
        "httpx",
        "fastapi",
        "guardian.core",
        "guardian.routes",
        "guardian.workers",
        "guardian.queue",
        "guardian.context",
        "guardian.vector",
    ]

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not any(
                    alias.name == f or alias.name.startswith(f + ".")
                    for f in forbidden
                ), f"compiler imports runtime module: {alias.name!r}"
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                assert not any(
                    node.module == f or node.module.startswith(f + ".")
                    for f in forbidden
                ), f"compiler imports-from runtime module: {node.module!r}"


# ── 2. Deterministic state ID ───────────────────────────────────────────────


def test_state_id_is_deterministic_same_packets_same_order():
    packets = [
        _packet(packet_id="a", created_at="2026-01-01T00:00:00Z"),
        _packet(packet_id="b", created_at="2026-01-02T00:00:00Z"),
    ]
    r1 = cc.compile_reality_state(packets, scope="project")
    r2 = cc.compile_reality_state(list(packets), scope="project")
    assert r1.state.state_id == r2.state.state_id


def test_state_id_is_deterministic_different_input_order():
    packets_a = [
        _packet(packet_id="a", created_at="2026-01-01T00:00:00Z"),
        _packet(packet_id="b", created_at="2026-01-02T00:00:00Z"),
    ]
    packets_b = [
        _packet(packet_id="b", created_at="2026-01-02T00:00:00Z"),
        _packet(packet_id="a", created_at="2026-01-01T00:00:00Z"),
    ]
    r1 = cc.compile_reality_state(packets_a, scope="project")
    r2 = cc.compile_reality_state(packets_b, scope="project")
    assert r1.state.state_id == r2.state.state_id


def test_state_id_changes_with_different_source_packets():
    r1 = cc.compile_reality_state(
        [_packet(packet_id="a")], scope="project"
    )
    r2 = cc.compile_reality_state(
        [_packet(packet_id="b")], scope="project"
    )
    assert r1.state.state_id != r2.state.state_id


def test_state_id_changes_with_different_scope():
    r1 = cc.compile_reality_state(
        [_packet(packet_id="a")], scope="project"
    )
    r2 = cc.compile_reality_state(
        [_packet(packet_id="a")], scope="thread"
    )
    assert r1.state.state_id != r2.state.state_id


# ── 3. Empty compile ────────────────────────────────────────────────────────


def test_empty_packet_list_returns_errors():
    result = cc.compile_reality_state([], scope="project")
    assert len(result.errors) > 0
    assert "no valid packets" in result.errors[0].lower()
    assert result.state.source_packet_ids == ()


def test_empty_packet_list_does_not_raise():
    """Empty input must return a result, not raise."""
    result = cc.compile_reality_state([], scope="project")
    assert result.state is not None
    assert result.state.scope == "project"


def test_empty_compile_no_warnings_on_empty():
    result = cc.compile_reality_state([], scope="project")
    assert result.warnings == ()


# ── 4. Invalid packet handling ──────────────────────────────────────────────


def test_invalid_packet_is_ignored():
    from guardian.continuity.contracts import ContinuityScope, ContinuitySource

    invalid = ContextPacket(
        packet_id="bad-pkt",
        schema_version="",
        kind="not_a_kind",  # type: ignore[arg-type]
        scope=ContinuityScope(),
        source=ContinuitySource(system=""),
        created_at="",
        summary="",
    )
    valid = _packet(packet_id="good-pkt")
    result = cc.compile_reality_state([invalid, valid], scope="project")
    assert "bad-pkt" in result.ignored_packet_ids
    assert "good-pkt" in result.state.source_packet_ids


def test_invalid_packet_generates_warnings():
    from guardian.continuity.contracts import ContinuityScope, ContinuitySource

    invalid = ContextPacket(
        packet_id="bad-pkt",
        schema_version="",
        kind="not_a_kind",  # type: ignore[arg-type]
        scope=ContinuityScope(),
        source=ContinuitySource(system=""),
        created_at="",
        summary="",
    )
    valid = _packet(packet_id="good-pkt")
    result = cc.compile_reality_state([invalid, valid], scope="project")
    assert any("bad-pkt" in w for w in result.warnings)
    # Errors come from RealityState validation (valid state), not from invalid packets
    # Invalid packets go to warnings, not errors


def test_all_invalid_returns_no_valid_packets_error():
    from guardian.continuity.contracts import ContinuityScope, ContinuitySource

    invalid = ContextPacket(
        packet_id="bad",
        schema_version="",
        kind="not_a_kind",  # type: ignore[arg-type]
        scope=ContinuityScope(),
        source=ContinuitySource(system=""),
        created_at="",
        summary="",
    )
    result = cc.compile_reality_state([invalid], scope="project")
    assert len(result.errors) > 0
    assert "no valid packets" in result.errors[0].lower()
    assert result.state.source_packet_ids == ()


# ── 5. Simple field extraction ──────────────────────────────────────────────


def test_extracts_active_artifacts():
    p = _packet(
        payload={"active_artifacts": ["file-a.py", "file-b.ts"]}
    )
    result = cc.compile_reality_state([p], scope="project")
    assert result.errors == ()
    assert "file-a.py" in result.state.active_artifacts
    assert "file-b.ts" in result.state.active_artifacts


def test_extracts_assumptions():
    p = _packet(payload={"assumptions": "We use Postgres as canonical"})
    result = cc.compile_reality_state([p], scope="project")
    assert result.errors == ()
    assert "We use Postgres as canonical" in result.state.assumptions


def test_extracts_risks():
    p = _packet(payload={"risks": ["Risk 1", "Risk 2"]})
    result = cc.compile_reality_state([p], scope="project")
    assert result.errors == ()
    assert len(result.state.risks) == 2


def test_extracts_next_actions():
    p = _packet(payload={"next_actions": ["Do thing", "Check thing"]})
    result = cc.compile_reality_state([p], scope="project")
    assert result.errors == ()
    assert len(result.state.next_actions) == 2


def test_dedupe_preserves_first_occurrence_order():
    p1 = _packet(
        packet_id="a",
        created_at="2026-01-01T00:00:00Z",
        payload={"active_artifacts": ["first.py", "second.py"]},
    )
    p2 = _packet(
        packet_id="b",
        created_at="2026-01-02T00:00:00Z",
        payload={"active_artifacts": ["second.py", "third.py"]},
    )
    result = cc.compile_reality_state([p1, p2], scope="project")
    assert result.state.active_artifacts == ("first.py", "second.py", "third.py")


def test_single_string_accepted():
    p = _packet(payload={"assumptions": "Just one"})
    result = cc.compile_reality_state([p], scope="project")
    assert result.state.assumptions == ("Just one",)


def test_empty_strings_filtered():
    p = _packet(payload={"risks": ["  ", "real risk", ""]})
    result = cc.compile_reality_state([p], scope="project")
    assert result.state.risks == ("real risk",)


# ── 6. Accepted decisions ───────────────────────────────────────────────────


def test_accepted_decisions_become_decision_records():
    p = _packet(payload={"accepted_decisions": ["We chose Postgres", "We chose Redis"]})
    result = cc.compile_reality_state([p], scope="project")
    assert result.errors == ()
    assert len(result.state.accepted_decisions) == 2
    assert result.state.accepted_decisions[0].summary == "We chose Postgres"
    assert result.state.accepted_decisions[1].summary == "We chose Redis"


def test_decision_ids_are_deterministic():
    p = _packet(payload={"accepted_decisions": ["A", "B"]})
    r1 = cc.compile_reality_state([p], scope="project")
    r2 = cc.compile_reality_state([p], scope="project")
    assert r1.state.accepted_decisions[0].decision_id == r2.state.accepted_decisions[0].decision_id
    assert r1.state.accepted_decisions[1].decision_id == r2.state.accepted_decisions[1].decision_id


def test_decision_provenance_includes_source_packet_id():
    p = _packet(packet_id="src-42", payload={"accepted_decisions": ["A"]})
    result = cc.compile_reality_state([p], scope="project")
    assert "src-42" in result.state.accepted_decisions[0].provenance.source_packet_ids


def test_decision_accepted_at_uses_packet_created_at():
    p = _packet(created_at="2026-06-25T12:00:00Z", payload={"accepted_decisions": ["A"]})
    result = cc.compile_reality_state([p], scope="project")
    assert result.state.accepted_decisions[0].accepted_at == "2026-06-25T12:00:00Z"


# ── 7. Open loops ───────────────────────────────────────────────────────────


def test_open_loops_become_open_loop_records():
    p = _packet(payload={"open_loops": ["Need to decide on auth strategy"]})
    result = cc.compile_reality_state([p], scope="project")
    assert result.errors == ()
    assert len(result.state.open_loops) == 1
    assert result.state.open_loops[0].summary == "Need to decide on auth strategy"
    assert result.state.open_loops[0].status == "open"


def test_open_loop_provenance_includes_source_packet_id():
    p = _packet(packet_id="src-open", payload={"open_loops": ["Unresolved issue"]})
    result = cc.compile_reality_state([p], scope="project")
    assert "src-open" in result.state.open_loops[0].provenance.source_packet_ids


# ── 8. Rejected paths ───────────────────────────────────────────────────────


def test_rejected_paths_become_rejected_path_records():
    p = _packet(payload={"rejected_paths": ["MongoDB instead of Postgres"]})
    result = cc.compile_reality_state([p], scope="project")
    assert result.errors == ()
    assert len(result.state.rejected_paths) == 1
    assert result.state.rejected_paths[0].summary == "MongoDB instead of Postgres"
    assert result.state.rejected_paths[0].status == "rejected"


def test_rejected_path_provenance_includes_source_packet_id():
    p = _packet(packet_id="src-reject", payload={"rejected_paths": ["Abandoned idea"]})
    result = cc.compile_reality_state([p], scope="project")
    assert "src-reject" in result.state.rejected_paths[0].provenance.source_packet_ids


# ── 9. No inference from summary ────────────────────────────────────────────


def test_summary_does_not_create_decision():
    """A summary mentioning a decision must not create a DecisionRecord."""
    p = _packet(
        summary="We decided to use Postgres",
        payload={},  # no accepted_decisions key
    )
    result = cc.compile_reality_state([p], scope="project")
    assert len(result.state.accepted_decisions) == 0


def test_summary_does_not_create_open_loop():
    p = _packet(
        summary="Still need to figure out auth",
        payload={},
    )
    result = cc.compile_reality_state([p], scope="project")
    assert len(result.state.open_loops) == 0


def test_summary_does_not_create_rejected_path():
    p = _packet(
        summary="We rejected MongoDB",
        payload={},
    )
    result = cc.compile_reality_state([p], scope="project")
    assert len(result.state.rejected_paths) == 0


# ── 10. Confidence validation ───────────────────────────────────────────────


def test_valid_confidence_passes():
    p = _packet()
    result = cc.compile_reality_state([p], scope="project", confidence=0.85)
    assert result.errors == ()


def test_invalid_confidence_returns_errors():
    p = _packet()
    result = cc.compile_reality_state([p], scope="project", confidence=1.5)
    assert any("confidence" in e for e in result.errors)


def test_none_confidence_passes():
    p = _packet()
    result = cc.compile_reality_state([p], scope="project", confidence=None)
    assert result.errors == ()


# ── 11. Compiler I/O determinism ────────────────────────────────────────────


def test_compile_is_deterministic():
    packets = [
        _packet(
            packet_id="a",
            created_at="2026-01-01T00:00:00Z",
            payload={
                "assumptions": ["X"],
                "accepted_decisions": ["Y"],
                "open_loops": ["Z"],
            },
        ),
        _packet(
            packet_id="b",
            created_at="2026-01-02T00:00:00Z",
            payload={
                "active_artifacts": ["f.py"],
                "risks": ["R"],
            },
        ),
    ]
    r1 = cc.compile_reality_state(packets, scope="project")
    r2 = cc.compile_reality_state(list(packets), scope="project")

    assert r1.state.state_id == r2.state.state_id
    assert r1.state.source_packet_ids == r2.state.source_packet_ids
    assert r1.state.assumptions == r2.state.assumptions
    assert r1.state.open_loops == r2.state.open_loops
    assert len(r1.state.accepted_decisions) == len(r2.state.accepted_decisions)
    assert r1.errors == r2.errors


def test_non_string_payload_values_are_ignored():
    """Non-string values in payload lists are silently skipped."""
    p = _packet(payload={"assumptions": [123, True, None, "valid"]})
    result = cc.compile_reality_state([p], scope="project")
    assert result.state.assumptions == ("valid",)


# ── 12. No side effects ─────────────────────────────────────────────────────


def test_compile_does_not_write_to_db():
    """Compilation must not create DB rows, files, queues, or network calls."""
    source = inspect.getsource(cc.compile_reality_state)
    io_smells = {"sqlalchemy", "redis", "requests", "httpx", "open(", "socket", "subprocess"}

    for smell in io_smells:
        assert smell not in source, (
            f"compile_reality_state source contains IO module reference: {smell!r}"
        )


# ── 13. Packet sort key ─────────────────────────────────────────────────────


def test_packet_sort_key_uses_created_at_then_packet_id():
    p1 = _packet(packet_id="z", created_at="2026-01-01T00:00:00Z")
    p2 = _packet(packet_id="a", created_at="2026-01-01T00:00:00Z")
    p3 = _packet(packet_id="m", created_at="2026-01-02T00:00:00Z")

    sorted_packets = sorted([p2, p3, p1], key=cc.packet_sort_key)
    # Same created_at: sorted by packet_id (a < z)
    assert sorted_packets[0].packet_id == "a"
    assert sorted_packets[1].packet_id == "z"
    # Later created_at comes last
    assert sorted_packets[2].packet_id == "m"


def test_derive_compiled_at_returns_latest():
    p1 = _packet(created_at="2026-01-01T00:00:00Z")
    p2 = _packet(created_at="2026-06-25T12:00:00Z")
    p3 = _packet(created_at="2026-03-15T00:00:00Z")
    result = cc.derive_compiled_at([p1, p2, p3])
    assert result == "2026-06-25T12:00:00Z"


def test_derive_compiled_at_empty_returns_empty():
    assert cc.derive_compiled_at([]) == ""


# ── 14. dedupe_preserving_order ─────────────────────────────────────────────


def test_dedupe_preserves_order():
    assert cc.dedupe_preserving_order(["b", "a", "b", "c", "a"]) == ("b", "a", "c")


def test_dedupe_excludes_empty_strings():
    assert cc.dedupe_preserving_order(["a", "", "b", ""]) == ("a", "b")


def test_dedupe_empty_input():
    assert cc.dedupe_preserving_order([]) == ()
