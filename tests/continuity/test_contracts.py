"""Pure contract tests for guardian.continuity.contracts.

These tests verify that the continuity contracts module is import-safe,
exports the expected public surfaces, produces correct candidate values,
and validates structures correctly — all without DB, Redis, graph,
provider, route, queue, or browser dependencies.
"""

from __future__ import annotations

import pytest

from guardian.continuity import contracts as c


# ── Module-level constants for easy assertion aggregation ───────────────────

# Each (domain_name, expected_value) pair verifies one candidate lookup.
_CANDIDATE_DOMAIN_CHECKS: list[tuple[str, str]] = [
    ("ContextPacketKind", "project_reality"),
    ("ContextPacketSensitivity", "syncable"),
    ("ContextPacketRetention", "exportable"),
    ("RealityScope", "dyad"),
    ("RealityCommitTrigger", "semantic_delta"),
    ("RealityCommitKind", "open_loop_added"),
    ("DiscoveryCommitTrigger", "concepts_merged"),
    ("OpenLoopStatus", "stale"),
    ("RejectedPathStatus", "do_not_reopen"),
    ("ProjectPulseSurfaceKind", "where_was_i"),
    ("BrowserContextPacketKind", "page_summary"),
    ("GraphMountMode", "disabled"),
    ("ContinuityCacheState", "fresh"),
    ("PinnedModelStateKind", "warm"),
    ("ContinuityImplementationGate", "token_domain_review"),
]


# ── 1. Import safety ────────────────────────────────────────────────────────

def test_import_succeeds():
    """Importing the contracts module must succeed without side effects."""
    assert c is not None


def test_public_helpers_exist():
    """Core public helpers must be importable."""
    assert callable(c.candidate_values_for)
    assert callable(c.is_candidate_value)
    assert callable(c.validate_context_packet)
    assert callable(c.validate_reality_state)
    assert callable(c.validate_reality_commit)


def test_public_dataclasses_exist():
    """Core dataclasses must be importable."""
    assert c.ContinuityScope is not None
    assert c.ContinuitySource is not None
    assert c.ContinuityProvenance is not None
    assert c.ContextPacket is not None
    assert c.DecisionRecord is not None
    assert c.OpenLoopRecord is not None
    assert c.RejectedPathRecord is not None
    assert c.RealityState is not None
    assert c.RealityCommit is not None


def test_import_does_not_load_runtime_modules():
    """The contracts module itself must not directly import runtime modules.

    We verify this by inspecting the contracts module's own source for
    forbidden import statements. This is more targeted than checking
    sys.modules, which may contain modules loaded by the test environment.
    """
    import ast
    import inspect

    runtime_import_smells = [
        "guardian.guardian_api",
        "guardian.db.models",
        "guardian.db",
        "guardian.queue",
        "guardian.core.chat_completion_service",
        "guardian.workers",
        "guardian.routes",
        "guardian.core.ai_router",
        "guardian.context.broker",
        "guardian.cognition.system_prompt_builder",
    ]

    source = inspect.getsource(c)
    tree = ast.parse(source)

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not any(
                    alias.name == smell or alias.name.startswith(smell + ".")
                    for smell in runtime_import_smells
                ), f"contracts imports runtime module: {alias.name!r}"
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                assert not any(
                    node.module == smell or node.module.startswith(smell + ".")
                    for smell in runtime_import_smells
                ), f"contracts imports-from runtime module: {node.module!r}"


# ── 2. Candidate values ─────────────────────────────────────────────────────

@pytest.mark.parametrize("domain_name,expected_value", _CANDIDATE_DOMAIN_CHECKS)
def test_candidate_value_is_in_domain(domain_name: str, expected_value: str):
    """Each checked candidate value must be returned by candidate_values_for."""
    values = c.candidate_values_for(domain_name)
    assert expected_value in values, (
        f"expected {expected_value!r} in {domain_name} values, got {values}"
    )


def test_candidate_values_for_context_packet_kind():
    values = c.candidate_values_for("ContextPacketKind")
    assert "project_reality" in values
    assert "thread" in values
    assert "browser" in values
    assert len(values) == 11


def test_candidate_values_for_reality_scope():
    values = c.candidate_values_for("RealityScope")
    assert "dyad" in values
    assert "project" in values
    assert len(values) == 8


def test_candidate_values_for_implementation_gate():
    values = c.candidate_values_for("ContinuityImplementationGate")
    assert "token_domain_review" in values
    assert len(values) == 10


def test_candidate_values_for_unknown_domain():
    """Unknown domains return an empty tuple."""
    assert c.candidate_values_for("NoSuchDomain") == ()
    assert c.candidate_values_for("") == ()


def test_is_candidate_value():
    assert c.is_candidate_value("ContextPacketKind", "thread") is True
    assert c.is_candidate_value("ContextPacketKind", "not_a_kind") is False
    assert c.is_candidate_value("NoSuchDomain", "anything") is False


# ── 3. Context packet validation ────────────────────────────────────────────

def _make_valid_packet(**overrides) -> c.ContextPacket:
    defaults = dict(
        packet_id="pkt-001",
        schema_version="1.0",
        kind="thread",
        scope=c.ContinuityScope(project_id="proj-1"),
        source=c.ContinuitySource(system="chat"),
        created_at="2026-06-25T00:00:00Z",
        summary="Test packet",
        payload={"key": "value"},
    )
    defaults.update(overrides)
    return c.ContextPacket(**defaults)


def test_valid_context_packet_passes():
    packet = _make_valid_packet()
    errors = c.validate_context_packet(packet)
    assert errors == (), f"expected no errors, got {errors}"


def test_empty_packet_id_fails():
    packet = _make_valid_packet(packet_id="")
    errors = c.validate_context_packet(packet)
    assert any("packet_id" in e for e in errors)


def test_invalid_kind_fails():
    packet = _make_valid_packet(kind="not_a_kind")  # type: ignore[arg-type]
    errors = c.validate_context_packet(packet)
    assert any("kind" in e for e in errors)


def test_invalid_sensitivity_fails():
    packet = _make_valid_packet(sensitivity="top_secret")  # type: ignore[arg-type]
    errors = c.validate_context_packet(packet)
    assert any("sensitivity" in e for e in errors)


# ── 4. Reality state validation ─────────────────────────────────────────────

def _make_valid_state(**overrides) -> c.RealityState:
    defaults = dict(
        state_id="state-001",
        schema_version="1.0",
        scope="project",
        compiled_at="2026-06-25T00:00:00Z",
        source_packet_ids=("pkt-001",),
    )
    defaults.update(overrides)
    return c.RealityState(**defaults)


def test_valid_reality_state_passes():
    state = _make_valid_state()
    errors = c.validate_reality_state(state)
    assert errors == (), f"expected no errors, got {errors}"


def test_empty_source_packet_ids_fails():
    state = _make_valid_state(source_packet_ids=())
    errors = c.validate_reality_state(state)
    assert any("source_packet_ids" in e for e in errors)


def test_confidence_below_zero_fails():
    state = _make_valid_state(confidence=-0.1)
    errors = c.validate_reality_state(state)
    assert any("confidence" in e for e in errors)


def test_confidence_above_one_fails():
    state = _make_valid_state(confidence=1.1)
    errors = c.validate_reality_state(state)
    assert any("confidence" in e for e in errors)


def test_confidence_none_passes():
    """None confidence is valid (means 'not assessed')."""
    state = _make_valid_state(confidence=None)
    errors = c.validate_reality_state(state)
    assert errors == (), f"expected no errors, got {errors}"


def test_invalid_scope_fails():
    state = _make_valid_state(scope="galaxy")  # type: ignore[arg-type]
    errors = c.validate_reality_state(state)
    assert any("scope" in e for e in errors)


def test_state_with_decisions_and_loops_passes():
    state = _make_valid_state(
        accepted_decisions=(
            c.DecisionRecord(decision_id="d1", summary="Decided X"),
        ),
        open_loops=(
            c.OpenLoopRecord(loop_id="l1", summary="Pending Y", status="open"),
        ),
        rejected_paths=(
            c.RejectedPathRecord(path_id="r1", summary="Rejected Z", status="rejected"),
        ),
    )
    errors = c.validate_reality_state(state)
    assert errors == (), f"expected no errors, got {errors}"


# ── 5. Reality commit validation ────────────────────────────────────────────

def _make_valid_commit(**overrides) -> c.RealityCommit:
    defaults = dict(
        commit_id="commit-001",
        schema_version="1.0",
        scope="project",
        kind="state_update",
        trigger="manual",
        title="First commit",
        summary="Initial reality snapshot",
        created_at="2026-06-25T00:00:00Z",
        source_packet_ids=("pkt-001",),
    )
    defaults.update(overrides)
    return c.RealityCommit(**defaults)


def test_valid_reality_commit_passes():
    commit = _make_valid_commit()
    errors = c.validate_reality_commit(commit)
    assert errors == (), f"expected no errors, got {errors}"


def test_empty_title_fails():
    commit = _make_valid_commit(title="")
    errors = c.validate_reality_commit(commit)
    assert any("title" in e for e in errors)


def test_invalid_trigger_fails():
    commit = _make_valid_commit(trigger="alarm_clock")  # type: ignore[arg-type]
    errors = c.validate_reality_commit(commit)
    assert any("trigger" in e for e in errors)


def test_invalid_kind_fails():
    commit = _make_valid_commit(kind="lunch_order")  # type: ignore[arg-type]
    errors = c.validate_reality_commit(commit)
    assert any("kind" in e for e in errors)


def test_commit_with_provenance_but_no_source_packets_passes():
    """A commit with provenance references (but empty source_packet_ids) is valid."""
    commit = _make_valid_commit(
        source_packet_ids=(),
        provenance=c.ContinuityProvenance(
            source_commit_ids=("prior-commit",),
        ),
    )
    errors = c.validate_reality_commit(commit)
    assert errors == (), f"expected no errors, got {errors}"


def test_commit_with_no_sources_fails():
    """A commit with neither source_packet_ids nor provenance references fails."""
    commit = _make_valid_commit(
        source_packet_ids=(),
        provenance=c.ContinuityProvenance(),
    )
    errors = c.validate_reality_commit(commit)
    assert len(errors) > 0


def test_empty_commit_id_fails():
    commit = _make_valid_commit(commit_id="")
    errors = c.validate_reality_commit(commit)
    assert any("commit_id" in e for e in errors)


# ── 6. Frozen dataclass behaviour ───────────────────────────────────────────

def test_context_packet_is_frozen():
    packet = _make_valid_packet()
    with pytest.raises(Exception):
        packet.packet_id = "mutated"  # type: ignore[misc]


def test_reality_state_is_frozen():
    state = _make_valid_state()
    with pytest.raises(Exception):
        state.confidence = 0.9  # type: ignore[misc]


def test_reality_commit_is_frozen():
    commit = _make_valid_commit()
    with pytest.raises(Exception):
        commit.title = "mutated"  # type: ignore[misc]


# ── 7. No persistence side effects ──────────────────────────────────────────

def test_validation_does_not_write_to_db():
    """Validation must not create DB rows, files, queues, or network calls."""
    # This is structurally guaranteed because the helper functions only
    # perform in-memory string/list/tuple operations. We verify that no
    # unexpected IO modules are referenced.
    import inspect

    helpers = [
        c.validate_context_packet,
        c.validate_reality_state,
        c.validate_reality_commit,
        c.candidate_values_for,
        c.is_candidate_value,
    ]
    io_smells = {"sqlalchemy", "redis", "httpx", "requests", "socket", "subprocess"}

    for helper in helpers:
        source = inspect.getsource(helper)
        for smell in io_smells:
            assert smell not in source, (
                f"{helper.__name__} source contains IO module reference: {smell!r}"
            )
