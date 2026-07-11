import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "docs/architecture/guardian-evidence-reducer-input-bundle-static-validator-contract.md"

REQUIRED_SECTIONS = (
    "Purpose", "Status", "Scope", "Why This Exists", "Current Truth",
    "Validation Is Not Authority", "Input-Bundle Files Covered",
    "Input-Bundle Files Not Covered", "Validator Output Shape", "Validation Phases",
    "Required Top-Level Bundle Checks", "Review Depth Checks", "Input Class Checks",
    "Input Object Field Checks", "Source Reference Rules", "Operator Context Rules",
    "Provenance Rules", "Limits and Boundary Rules", "Template vs Fixture Rules",
    "Pass / Fail / Warning Semantics", "Candidate Issue Code Vocabulary",
    "Relationship to ReducerInputBundle Contracts", "Relationship to Reducer Dry-Run CLI",
    "Relationship to Packet Validation", "Relationship to Future Input-Bundle Loader",
    "Relationship to Runtime Reducer", "Relationship to Execution Ledger and WorkOrder",
    "Relationship to UI and CI", "Failure Modes", "Future Allowed Slices",
    "Forbidden Interpretations", "Bottom Line",
)

REVIEW_DEPTHS = ("light", "medium", "high", "xhigh")
INPUT_CLASSES = (
    "static_docs", "static_fixtures", "validation_result", "command_run_snapshot",
    "command_run_event_snapshot", "receipt_metadata", "proof_index",
    "test_result_summary", "operator_supplied_context",
)
INPUT_FIELDS = ("input_id", "input_class", "source_ref", "evidence_posture", "notes")
TOP_LEVEL_FIELDS = (
    "schema_version", "bundle_id", "review_depth", "inputs", "operator_context",
    "provenance", "limits",
)
ISSUE_CODES = (
    "bundle_json_invalid", "bundle_schema_version_missing",
    "bundle_schema_version_unsupported", "bundle_required_field_missing",
    "review_depth_invalid", "inputs_missing", "input_required_field_missing",
    "input_class_invalid", "source_ref_missing", "source_ref_absolute_path_warning",
    "source_ref_secret_risk", "source_ref_file_read_claim", "operator_context_not_list",
    "provenance_missing", "template_marker_missing", "static_fixture_marker_missing",
    "limits_missing", "boundary_language_missing", "evidence_ingestion_claim_risk",
    "packet_generation_claim_risk", "runtime_reducer_claim_risk", "execution_claim_risk",
    "ci_release_gate_claim_risk",
)


def test_contract_exists_and_has_required_sections() -> None:
    assert CONTRACT.is_file()
    text = CONTRACT.read_text()
    for section in REQUIRED_SECTIONS:
        assert f"## {REQUIRED_SECTIONS.index(section) + 1}. {section}" in text


def test_contract_states_docs_only_boundaries() -> None:
    text = CONTRACT.read_text()
    required_phrases = (
        "static validation doctrine only",
        "does not implement a validator",
        "does not implement an input-bundle loader",
        "does not make the reducer CLI read bundle files",
        "does not implement runtime reducer behavior",
        "does not implement packet generation",
        "does not add ingestion",
        "does not add UI",
        "does not add CI/default release gating",
        "does not authorize execution",
        "does not authorize source mutation",
        "does not authorize Pi Loop invocation",
        "does not authorize provider execution",
        "does not authorize Codexify ingestion",
        "does not prove source reference truth",
        "does not authorize reading source-reference targets",
        "does not generate GuardianEvidencePacket output",
        "does not mutate WorkOrders",
        "does not write Execution Ledger entries",
    )
    for phrase in required_phrases:
        assert phrase in text


def test_contract_documents_bundle_vocabularies_and_result_shape() -> None:
    text = CONTRACT.read_text()
    assert "guardian_evidence_reducer_input_bundle.v1" in text
    for field in TOP_LEVEL_FIELDS + INPUT_FIELDS + REVIEW_DEPTHS + INPUT_CLASSES:
        assert field in text
    assert "GuardianEvidenceReducerInputBundleStaticValidationResult" in text
    for value in ("pass", "pass_with_warnings", "fail", "error", "warning", "info"):
        assert f'"{value}"' in text
    for code in ISSUE_CODES:
        assert f"`{code}`" in text
    assert "not runtime protocol tokens" in text


def test_contract_documents_conceptual_flow_and_future_slices() -> None:
    text = CONTRACT.read_text()
    for phrase in (
        "ReducerInputBundle template or fixture",
        "static input-bundle validator",
        "GuardianEvidenceReducerInputBundleStaticValidationResult",
        "human/operator review",
        "future input-bundle loader, reducer, UI, Execution Ledger, or WorkOrder work",
        "input-bundle static validator implementation",
        "input-bundle batch validator implementation",
        "input-bundle Make target",
        "reducer dry-run input-bundle loader contract",
        "reducer dry-run input-bundle loader implementation",
        "pure reducer library implementation",
        "packet generator contract",
        "packet generator implementation",
        "read-only operator surface contract",
        "Execution Ledger adoption contract",
        "WorkOrder mapping contract",
        "CI opt-in validation contract",
    ):
        assert phrase in text


def test_existing_local_make_targets_and_packet_batch_validation_remain_green() -> None:
    for target in ("guardian-evidence-packets-validate", "guardian-evidence-reducer-dry-run"):
        proc = subprocess.run(
            ["make", target], cwd=ROOT, capture_output=True, text=True, check=False
        )
        assert proc.returncode == 0, proc.stderr

    proc = subprocess.run(
        ["python3", "scripts/guardian/validate_evidence_packets.py", "--json"],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    assert proc.returncode == 0, proc.stderr
    result = json.loads(proc.stdout)
    assert result["matched_count"] == 3
