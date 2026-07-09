"""Tests for the docs-only GuardianEvidencePacket reducer design contract."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "docs/architecture/guardian-evidence-packet-runtime-reducer-design-contract.md"
REDUCER = ROOT / "docs/architecture/guardian-evidence-packet-reducer-contract.md"
VALIDATOR = ROOT / "docs/architecture/guardian-evidence-packet-static-validator-contract.md"
GUIDE = ROOT / "docs/architecture/guardian-evidence-packet-authoring-guide.md"
README = ROOT / "docs/architecture/README.md"
CURRENT = ROOT / "docs/architecture/00-current-state.md"

SECTIONS = [
    "Purpose", "Status", "Scope", "Why This Exists", "Current Truth",
    "Reducer Design Boundary", "Non-Goals", "Input Classes", "Output Classes",
    "Reducer Lifecycle", "Reduction Depth Semantics", "Bounded Self-Check Policy",
    "Evidence Reference Handling", "Claim Extraction Rules",
    "Claim-to-Evidence Binding Rules", "Contradiction Handling", "Missing-Proof Handling",
    "Authority Lock Rules", "Invariant Preservation Rules", "Forbidden Interpretation Rules",
    "Next Gate Selection Rules", "Provenance and Limits Rules", "Static Validation Handoff",
    "Human Review Handoff", "Relationship to Authoring Template and Guide",
    "Relationship to Existing Fixtures", "Relationship to Command Bus",
    "Relationship to Codex Runner Bridge", "Relationship to Runtime Tool Loop",
    "Relationship to Execution Ledger and WorkOrder", "Relationship to Future UI",
    "Relationship to CI and Release Gates", "Failure Modes", "Future Allowed Slices",
    "Forbidden Interpretations", "Bottom Line",
]
INPUT_CLASSES = [
    "static_docs", "static_fixtures", "validation_result", "command_run_snapshot",
    "command_run_event_snapshot", "receipt_metadata", "proof_index",
    "test_result_summary", "operator_supplied_context",
]
OUTPUT_CLASSES = [
    "GuardianEvidencePacket", "GuardianEvidencePacketStaticValidationResult",
    "reducer_diagnostics_summary",
]
AUTHORITY_LINES = [
    "guardian_operational: false", "plan_execution_allowed: false",
    "pi_loop_invocation_allowed: false", "codexify_ingestion_allowed: false",
    "durable_mutation_allowed: false", "provider_execution_allowed: false",
    "patch_application_allowed: false", "dispatch_allowed: false", "merge_allowed: false",
]
BOUNDARY = "PREFLIGHT ONLY\nNO PI LOOP INVOCATION\nNO SOURCE MUTATION\nNO CODEXIFY INGESTION"


def _text() -> str:
    return CONTRACT.read_text()


def test_design_contract_exists_and_has_all_sections() -> None:
    assert CONTRACT.exists()
    text = _text()
    for section in SECTIONS:
        assert section in text


def test_contract_is_docs_only_and_preserves_non_goals() -> None:
    text = _text().lower()
    required = (
        "this is a design contract only",
        "does not implement runtime reducer behavior",
        "does not implement packet generation",
        "does not add api routes",
        "does not add frontend ui",
        "does not add ingestion",
        "does not write receipts",
        "does not call command bus",
        "does not call codex runner",
        "does not invoke live validation",
        "does not invoke live orchestration",
        "does not invoke pi loop",
        "does not execute plans",
        "does not mutate source",
        "does not execute providers",
        "does not write execution ledger entries",
        "does not mutate workorders",
        "does not add ci/default release gating",
        "does not widen release support",
    )
    for phrase in required:
        assert phrase in text


def test_contract_defines_inputs_outputs_lifecycle_depth_and_loop_policy() -> None:
    text = _text()
    for value in INPUT_CLASSES + OUTPUT_CLASSES:
        assert value in text
    lifecycle = [
        "Receive bounded evidence input set.", "Classify input classes.",
        "Assign evidence refs.", "Extract candidate claims.",
        "Bind candidate claims to evidence refs.",
        "Mark unsupported, blocked, inferred, or not_evaluated claims honestly.",
        "Preserve uncertainty.", "Preserve forbidden interpretations.",
        "Set authority locks.", "Select next gate options.",
        "Produce GuardianEvidencePacket.", "Run static validation.",
        "Return packet plus validation result for human/operator review.", "Stop.",
    ]
    positions = [text.index(item) for item in lifecycle]
    assert positions == sorted(positions)
    for depth in ("light", "medium", "high", "xhigh"):
        assert f"`{depth}`" in text
    assert "failed self-check must produce uncertainty or blocked claims, not automatic repair" in text
    assert "recursive_autonomous_loop_allowed: false" in text


def test_contract_preserves_authority_and_exact_boundary() -> None:
    text = _text()
    for line in AUTHORITY_LINES:
        assert line in text
    assert BOUNDARY in text
    for phrase in (
        "no recursive autonomous loop", "no source mutation", "no command execution",
        "no receipt writing", "no ingestion", "no execution ledger write",
        "no workorder mutation", "GuardianEvidencePacket is the only packet output class currently allowed",
    ):
        assert phrase.lower() in text.lower()


def test_contract_lists_future_allowed_slices() -> None:
    text = _text()
    for slice_name in (
        "pure reducer library contract", "pure reducer library implementation",
        "reducer CLI dry-run", "packet generator contract", "packet generator implementation",
        "read-only operator surface contract", "dev-build-only bridge test affordance contract",
        "Execution Ledger adoption contract", "WorkOrder mapping contract",
        "CI opt-in validation contract",
    ):
        assert slice_name in text


def test_related_docs_link_design_contract() -> None:
    assert "guardian-evidence-packet-runtime-reducer-design-contract.md" in REDUCER.read_text()
    assert "future reducer outputs must pass static validation before operator surfacing" in VALIDATOR.read_text().lower()
    assert "runtime reducer design contract" in GUIDE.read_text()
    assert "guardian-evidence-packet-runtime-reducer-design-contract.md" in README.read_text()
    assert "future runtime reducer design contract" in CURRENT.read_text()


def test_existing_batch_validation_still_discovers_both_fixtures() -> None:
    proc = subprocess.run(
        ["make", "guardian-evidence-packets-validate"],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert '"matched_count": 2' in proc.stdout
    data = json.loads("\n".join(proc.stdout.splitlines()[1:]))
    assert data["matched_count"] >= 2
    assert data["result"] in {"pass", "pass_with_warnings"}
