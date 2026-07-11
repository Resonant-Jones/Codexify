import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "docs/architecture/guardian-evidence-reducer-input-bundle-dry-run-loader-contract.md"

SECTIONS = (
    "Purpose", "Status", "Scope", "Current Truth", "Why This Exists",
    "Loader Is Not Evidence Ingestion", "Loader Is Not Packet Generation",
    "Proposed Future CLI Surface", "Input-Bundle Validation Requirement",
    "Bundle-to-Reducer Mapping", "Source Reference Boundary", "Operator Context Handling",
    "Validation Result Handling", "Dry-Run Result Handling", "Output Shape Guidance",
    "Error and Exit Semantics", "Relationship to ReducerInputBundle Contracts",
    "Relationship to Input-Bundle Static Validator", "Relationship to Input-Bundle Batch Validator",
    "Relationship to Reducer Dry-Run CLI", "Relationship to Packet Validation",
    "Relationship to Runtime Reducer", "Relationship to Execution Ledger and WorkOrder",
    "Relationship to UI and CI", "Forbidden Interpretations", "Future Allowed Slices", "Bottom Line",
)


def test_loader_contract_exists_and_has_required_sections() -> None:
    assert CONTRACT.is_file()
    text = CONTRACT.read_text()
    for index, section in enumerate(SECTIONS, start=1):
        assert f"## {index}. {section}" in text


def test_loader_contract_preserves_docs_only_boundaries() -> None:
    text = CONTRACT.read_text()
    phrases = (
        "This is a docs-only contract",
        "does not implement an input-bundle loader",
        "does not change `reducer_dry_run.py`",
        "does not make the reducer CLI read bundle files",
        "does not implement runtime reducer behavior",
        "does not implement packet generation",
        "does not add persistence",
        "does not add ingestion",
        "does not add UI",
        "does not add CI/default release gating",
        "does not authorize execution",
        "does not authorize source mutation",
        "does not authorize Pi Loop invocation",
        "does not authorize provider execution",
        "does not authorize Codexify ingestion",
        "A future loader may read only the input-bundle JSON file passed to it.",
        "It must not read `source_ref` targets",
        "must not validate `GuardianEvidencePacket` fixtures",
        "must not call packet validators",
        "must not call command bus",
        "must not call Codex Runner",
        "must not invoke live validation",
        "must not invoke orchestration",
        "must not write receipts",
        "must not mutate WorkOrders",
        "must not write Execution Ledger entries",
    )
    for phrase in phrases:
        assert phrase in text


def test_loader_contract_documents_future_cli_sequence_and_output() -> None:
    text = CONTRACT.read_text()
    assert "reducer_dry_run.py --json --input-bundle" in text
    assert "single-file input-bundle static validation" in text
    assert "If validation returns `fail`, the loader must stop without calling `dry_run_reducer`." in text
    for step in (
        "1. Parse CLI arguments.",
        "2. Read only the input-bundle JSON file.",
        "3. Run single-file input-bundle static validation.",
        "4. If validation result is fail, stop without calling dry_run_reducer.",
        "5. If validation result is pass or pass_with_warnings, construct ReducerInputBundle.",
        "6. Map each JSON input object to ReducerInputRef without reading source_ref.",
        "7. Preserve bundle_id, review_depth, operator_context, input_id, input_class, source_ref, evidence_posture, and notes.",
        "8. Call dry_run_reducer.",
        "9. Return combined diagnostics.",
        "10. Stop.",
    ):
        assert step in text
    assert "GuardianEvidenceReducerInputBundleDryRunResult" in text
    assert '"packet": null' in text
    assert '"validation_result": null' in text
    assert "authority_state` must keep all authority locks false" in text
    assert "receive_bounded_evidence_input_set`, `classify_input_classes`, `stop" in text


def test_loader_contract_lists_future_allowed_slices_and_cross_links() -> None:
    text = CONTRACT.read_text()
    for phrase in (
        "reducer dry-run input-bundle loader implementation",
        "focused loader tests",
        "optional Make target for dry-run with static fixture",
        "pure reducer implementation contract",
        "pure reducer implementation",
        "packet generator contract",
        "packet generator implementation",
        "read-only operator surface contract",
        "Execution Ledger adoption contract",
        "WorkOrder mapping contract",
        "CI opt-in validation contract",
    ):
        assert phrase in text
    static_contract = (ROOT / "docs/architecture/guardian-evidence-reducer-input-bundle-static-validator-contract.md").read_text()
    runtime_contract = (ROOT / "docs/architecture/guardian-evidence-packet-runtime-reducer-design-contract.md").read_text()
    reducer_contract = (ROOT / "docs/architecture/guardian-evidence-packet-reducer-contract.md").read_text()
    readme = (ROOT / "docs/architecture/README.md").read_text()
    current = (ROOT / "docs/architecture/00-current-state.md").read_text()
    assert "guardian-evidence-reducer-input-bundle-dry-run-loader-contract.md" in static_contract
    assert "guardian-evidence-reducer-input-bundle-dry-run-loader-contract.md" in runtime_contract
    assert "guardian-evidence-reducer-input-bundle-dry-run-loader-contract.md" in reducer_contract
    assert "guardian-evidence-reducer-input-bundle-dry-run-loader-contract.md" in readme
    assert "input-bundle dry-run loader contract" in current


def test_existing_tools_remain_unchanged_and_green() -> None:
    for target in (
        "guardian-evidence-packets-validate",
        "guardian-evidence-reducer-dry-run",
        "guardian-evidence-reducer-input-bundles-validate",
    ):
        proc = subprocess.run(["make", target], cwd=ROOT, capture_output=True, text=True, check=False)
        assert proc.returncode == 0, proc.stderr
    packet_proc = subprocess.run(
        ["python3", "scripts/guardian/validate_evidence_packets.py", "--json"],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    bundle_proc = subprocess.run(
        ["python3", "scripts/guardian/validate_reducer_input_bundles.py", "--json"],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    assert packet_proc.returncode == 0
    assert bundle_proc.returncode == 0
    assert json.loads(packet_proc.stdout)["matched_count"] == 3
    bundle_result = json.loads(bundle_proc.stdout)
    assert bundle_result["matched_count"] >= 2
    assert any("guardian-evidence-reducer-input-bundle-template" in entry["path"] for entry in bundle_result["files"])
    assert any("guardian-evidence-reducer-input-bundle.local-tooling" in entry["path"] for entry in bundle_result["files"])
