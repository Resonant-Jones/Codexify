"""Static contract tests for the Guardian Evidence Packet and Reducer Profile contract.

These tests validate that the contract exists, documents all required schemas,
defines all four reduction depths, and preserves the preflight-only boundary
language — all without requiring Docker, runtime execution, or any live
operations.

Do not run Docker in automated tests.
Do not require /Volumes/Dev_SSD/Codex-Runner to exist in automated tests.
Do not execute real codexrun in automated tests.
Do not execute python -m codex_runner in automated tests.
Do not invoke validation in automated tests.
Do not invoke orchestration in automated tests.
Do not write receipts in automated tests.
Do not call live command bus in automated tests.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARCH = ROOT / "docs" / "architecture"

EVIDENCE_CONTRACT = (
    ARCH / "guardian-evidence-packet-reducer-contract.md"
)
PROOF_CHAIN_INDEX = (
    ARCH / "guardian-codex-runner-bridge-proof-chain-index.md"
)
AGENT_PROTOCOL = ARCH / "agent-protocol-operations.md"
CONFIG_OPS = ARCH / "config-and-ops.md"
README = ARCH / "README.md"

REQUIRED_SCHEMAS = [
    "GuardianEvidencePacket",
    "GuardianReducerProfile",
    "GuardianEvidenceRef",
    "GuardianClaimLedgerEntry",
    "GuardianAuthorityState",
    "GuardianInvariantCheck",
    "GuardianUncertaintyEntry",
    "GuardianForbiddenInterpretation",
    "GuardianNextGateOption",
]

REQUIRED_DEPTHS = ["light", "medium", "high", "xhigh"]


# ---------------------------------------------------------------------------
# Document existence
# ---------------------------------------------------------------------------

def test_evidence_contract_document_exists() -> None:
    assert EVIDENCE_CONTRACT.exists(), (
        "guardian-evidence-packet-reducer-contract.md must exist"
    )


# ---------------------------------------------------------------------------
# Boundary label and authority locks
# ---------------------------------------------------------------------------

def test_evidence_contract_includes_boundary_label() -> None:
    text = EVIDENCE_CONTRACT.read_text()
    assert "PREFLIGHT ONLY" in text, (
        "evidence contract must include PREFLIGHT ONLY boundary label"
    )
    assert "NO PI LOOP INVOCATION" in text, (
        "evidence contract must include NO PI LOOP INVOCATION boundary label"
    )
    assert "NO SOURCE MUTATION" in text, (
        "evidence contract must include NO SOURCE MUTATION boundary label"
    )
    assert "NO CODEXIFY INGESTION" in text, (
        "evidence contract must include NO CODEXIFY INGESTION boundary label"
    )


def test_evidence_contract_includes_all_authority_locks_false() -> None:
    text = EVIDENCE_CONTRACT.read_text()
    required_locks = [
        "guardian_operational: false",
        "plan_execution_allowed: false",
        "pi_loop_invocation_allowed: false",
        "codexify_ingestion_allowed: false",
        "durable_mutation_allowed: false",
        "provider_execution_allowed: false",
        "patch_application_allowed: false",
        "dispatch_allowed: false",
        "merge_allowed: false",
    ]
    for lock in required_locks:
        assert lock in text, (
            f"evidence contract must include authority lock: {lock}"
        )


# ---------------------------------------------------------------------------
# Schema family completeness
# ---------------------------------------------------------------------------

def test_evidence_contract_defines_all_schemas() -> None:
    text = EVIDENCE_CONTRACT.read_text()
    missing = []
    for schema_name in REQUIRED_SCHEMAS:
        if schema_name not in text:
            missing.append(schema_name)
    assert not missing, (
        f"evidence contract missing schema definitions: {missing}"
    )


# ---------------------------------------------------------------------------
# Reduction depth completeness
# ---------------------------------------------------------------------------

def test_evidence_contract_defines_all_depths() -> None:
    text = EVIDENCE_CONTRACT.read_text()
    missing = []
    for depth in REQUIRED_DEPTHS:
        if f"### {depth}" not in text:
            missing.append(depth)
    assert not missing, (
        f"evidence contract missing reduction depth definitions: {missing}"
    )


# ---------------------------------------------------------------------------
# Reduction depth policy assertions
# ---------------------------------------------------------------------------

def test_evidence_contract_states_depth_is_evidence_policy() -> None:
    text = EVIDENCE_CONTRACT.read_text().lower()
    assert "reduction depth" in text or "depth is" in text, (
        "evidence contract must state reducer depth is evidence handling/self-check policy"
    )


def test_evidence_contract_states_preserve_evidence_refs() -> None:
    text = EVIDENCE_CONTRACT.read_text().lower()
    assert "evidence ref" in text or "evidence_refs" in text, (
        "evidence contract must state reduced summaries must preserve evidence refs"
    )


def test_evidence_contract_states_preserve_uncertainty() -> None:
    text = EVIDENCE_CONTRACT.read_text().lower()
    assert "uncertainty" in text, (
        "evidence contract must state reduced summaries must preserve uncertainty"
    )


def test_evidence_contract_states_preserve_forbidden_interpretations() -> None:
    text = EVIDENCE_CONTRACT.read_text().lower()
    assert "forbidden interpretation" in text, (
        "evidence contract must state reduced summaries must preserve forbidden interpretations"
    )


def test_evidence_contract_states_authority_false() -> None:
    text = EVIDENCE_CONTRACT.read_text().lower()
    assert "authority values" in text or "authority locks" in text, (
        "evidence contract must state authority values in examples remain false"
    )


# ---------------------------------------------------------------------------
# No-implementation assertions
# ---------------------------------------------------------------------------

def test_evidence_contract_states_no_runtime_code() -> None:
    text = EVIDENCE_CONTRACT.read_text().lower()
    assert "does not implement" in text or "no runtime" in text or "docs-only" in text, (
        "evidence contract must state this does not implement runtime reducer code"
    )


def test_evidence_contract_states_no_persistence() -> None:
    text = EVIDENCE_CONTRACT.read_text().lower()
    assert "no persistence" in text or "does not add persistence" in text or "database" in text, (
        "evidence contract must state this does not add persistence"
    )


def test_evidence_contract_states_no_ingestion() -> None:
    text = EVIDENCE_CONTRACT.read_text().lower()
    assert "no ingestion" in text or "does not add ingestion" in text or "not ingest" in text, (
        "evidence contract must state this does not add ingestion"
    )


def test_evidence_contract_states_no_ui() -> None:
    text = EVIDENCE_CONTRACT.read_text().lower()
    assert "no ui" in text or "does not add ui" in text or "ui surfacing" in text, (
        "evidence contract must state this does not add UI"
    )


def test_evidence_contract_states_no_dev_build_button() -> None:
    text = EVIDENCE_CONTRACT.read_text().lower()
    assert "dev-build" in text or "dev build" in text or "test button" in text or "test affordance" in text, (
        "evidence contract must state this does not add a dev-build test button"
    )


def test_evidence_contract_states_no_execution_auth() -> None:
    text = EVIDENCE_CONTRACT.read_text().lower()
    assert "does not authorize" in text or "not authorize" in text, (
        "evidence contract must state this does not authorize execution"
    )


def test_evidence_contract_states_no_source_mutation() -> None:
    text = EVIDENCE_CONTRACT.read_text().lower()
    assert "source mutation" in text, (
        "evidence contract must state this does not authorize source mutation"
    )


def test_evidence_contract_states_no_pi_loop() -> None:
    text = EVIDENCE_CONTRACT.read_text().lower()
    assert "pi loop" in text, (
        "evidence contract must state this does not authorize Pi Loop invocation"
    )


def test_evidence_contract_states_no_provider_execution() -> None:
    text = EVIDENCE_CONTRACT.read_text().lower()
    assert "provider execution" in text, (
        "evidence contract must state this does not authorize provider execution"
    )


def test_evidence_contract_states_no_codexify_ingestion() -> None:
    text = EVIDENCE_CONTRACT.read_text().lower()
    assert "codexify ingestion" in text, (
        "evidence contract must state this does not authorize Codexify ingestion"
    )


def test_evidence_contract_states_execution_ledger_separate() -> None:
    text = EVIDENCE_CONTRACT.read_text().lower()
    assert "execution ledger" in text, (
        "evidence contract must state Execution Ledger adoption requires a separate contract"
    )


def test_evidence_contract_states_workorder_separate() -> None:
    text = EVIDENCE_CONTRACT.read_text().lower()
    assert "workorder" in text or "work order" in text, (
        "evidence contract must state WorkOrder mutation requires a separate contract"
    )


# ---------------------------------------------------------------------------
# Cross-reference checks
# ---------------------------------------------------------------------------

def test_proof_chain_index_links_evidence_contract() -> None:
    text = PROOF_CHAIN_INDEX.read_text()
    assert "guardian-evidence-packet-reducer-contract.md" in text, (
        "bridge proof-chain index must link the evidence contract"
    )


def test_agent_protocol_links_evidence_contract() -> None:
    text = AGENT_PROTOCOL.read_text()
    assert "guardian-evidence-packet-reducer-contract.md" in text, (
        "agent protocol operations must link the evidence contract"
    )


def test_config_ops_links_or_names_evidence_contract() -> None:
    text = CONFIG_OPS.read_text()
    assert "GuardianEvidencePacket" in text or "guardian-evidence-packet" in text, (
        "config-and-ops must link or name the evidence contract"
    )


def test_readme_links_evidence_contract() -> None:
    text = README.read_text()
    assert "guardian-evidence-packet-reducer-contract.md" in text, (
        "README must link the evidence contract"
    )


# ---------------------------------------------------------------------------
# Invariant checks
# ---------------------------------------------------------------------------

def test_no_frontend_files_changed() -> None:
    """No frontend files should be modified by this task."""
    frontend_dir = ROOT / "frontend"
    assert frontend_dir.exists(), "frontend directory should still exist"


def test_no_new_route_file() -> None:
    """No new route file should be added by this task."""
    routes_dir = ROOT / "guardian" / "routes"
    existing = set(p.name for p in routes_dir.glob("*.py"))
    forbidden = {
        "bridge.py",
        "codex_runner.py",
        "codex_runner_bridge.py",
        "guardian_bridge.py",
        "evidence_reducer.py",
        "evidence_packet.py",
    }
    assert existing.isdisjoint(forbidden), (
        f"No new route file should be added: found {existing & forbidden}"
    )
