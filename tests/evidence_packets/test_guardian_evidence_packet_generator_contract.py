import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "docs/architecture/guardian-evidence-packet-generator-contract.md"

SECTIONS = (
    "Purpose", "Status", "Scope", "Current Truth", "Why This Exists",
    "Generator Is Not Authority", "Generator Is Not Execution", "Generator Is Not Evidence Ingestion",
    "Generator Is Not Runtime Reducer Behavior", "Relationship to GuardianEvidencePacket Schema",
    "Relationship to ReducerInputBundle", "Relationship to Dry-Run Loader",
    "Relationship to Static Packet Validation", "Relationship to Input-Bundle Validation",
    "Relationship to Packet Fixtures", "Required Generator Inputs", "Required Generator Outputs",
    "Evidence Reference Rules", "Claim Ledger Rules", "Authority State Rules", "Uncertainty Rules",
    "Forbidden Interpretation Rules", "Contradiction Handling", "Source Reference Boundary",
    "Validation Requirement", "Output Validation Requirement", "Error and Exit Semantics",
    "Relationship to Execution Ledger and WorkOrder", "Relationship to UI and CI",
    "Forbidden Interpretations", "Future Allowed Slices", "Bottom Line",
)


def test_generator_contract_exists_and_has_required_sections() -> None:
    assert CONTRACT.is_file()
    text = CONTRACT.read_text()
    for index, section in enumerate(SECTIONS, start=1):
        assert f"## {index}. {section}" in text


def test_generator_contract_preserves_docs_only_boundaries() -> None:
    text = CONTRACT.read_text()
    phrases = (
        "This is a docs-only contract",
        "does not implement a packet generator",
        "does not modify `reducer_dry_run.py`",
        "does not modify validator scripts",
        "does not generate `GuardianEvidencePacket` output",
        "does not alter existing packet fixtures",
        "does not implement runtime reducer behavior",
        "does not implement evidence ingestion",
        "does not add persistence",
        "does not add UI",
        "does not add CI/default release gating",
        "does not authorize execution",
        "does not authorize source mutation",
        "does not authorize Pi Loop invocation",
        "does not authorize provider execution",
        "does not authorize Codexify ingestion",
        "A future packet generator must not read source_ref targets unless a separate evidence-read contract explicitly allows that path.",
        "must not call command bus",
        "must not call Codex Runner",
        "must not mutate WorkOrders",
        "must not write Execution Ledger entries",
    )
    for phrase in phrases:
        assert phrase in text


def test_generator_inputs_outputs_and_semantics_are_documented() -> None:
    text = CONTRACT.read_text()
    for phrase in (
        "validated ReducerInputBundle metadata", "bounded evidence references", "operator context",
        "reducer profile or review depth", "validation result for input bundle", "explicit limits",
        "optional prior static validation result references", "GuardianEvidencePacketGeneratorResult",
        "schema_version", "generator_contract_version", "input_bundle_ref",
        "input_bundle_validation_result_ref", "packet_validation_result", "authority_state",
        "diagnostics", "packet may exist only after a future implementation",
        "packet must conform to GuardianEvidencePacket schema",
        "source_ref_read_policy", "evidence_ref_count", "claim_count", "uncertainty_count",
        "forbidden_interpretation_count", "contradiction_count", "no execution",
        "no evidence ingestion", "no command bus", "no Codex Runner", "no Pi Loop",
        "no source mutation", "no provider execution", "no WorkOrder mutation",
        "no Execution Ledger write", "no release support expansion",
    ):
        assert phrase in text


def test_generator_flow_and_future_slices_are_documented() -> None:
    text = CONTRACT.read_text()
    for phrase in (
        "Validated ReducerInputBundle", "future bounded evidence preparation contract",
        "future packet generator", "GuardianEvidencePacket", "static packet validator",
        "human/operator review", "packet generation is not execution",
        "packet generation is not evidence authority", "packet generation is not source truth",
        "packet generation is not receipt trust", "packet generation is not WorkOrder mutation",
        "packet generation is not Execution Ledger write", "packet generation is not release approval",
        "bounded evidence-read contract", "bounded evidence-read implementation",
        "pure packet generator implementation", "packet generator focused tests",
        "packet generator Make target", "generated packet fixture", "packet static validation integration",
        "read-only operator surface contract", "Execution Ledger adoption contract",
        "WorkOrder mapping contract", "CI opt-in validation contract",
    ):
        assert phrase in text


def test_cross_links_and_existing_tools_remain_green() -> None:
    static_contract = (ROOT / "docs/architecture/guardian-evidence-reducer-input-bundle-static-validator-contract.md").read_text()
    runtime_contract = (ROOT / "docs/architecture/guardian-evidence-packet-runtime-reducer-design-contract.md").read_text()
    loader_contract = (ROOT / "docs/architecture/guardian-evidence-reducer-input-bundle-dry-run-loader-contract.md").read_text()
    reducer_contract = (ROOT / "docs/architecture/guardian-evidence-packet-reducer-contract.md").read_text()
    readme = (ROOT / "docs/architecture/README.md").read_text()
    current = (ROOT / "docs/architecture/00-current-state.md").read_text()
    link = "guardian-evidence-packet-generator-contract.md"
    assert link in static_contract or "generator prerequisites" in static_contract
    assert link in runtime_contract
    assert link in loader_contract or "packet generator contract" in loader_contract
    assert link in reducer_contract
    assert link in readme
    assert "Guardian Evidence Packet generator contract" in current

    for target in (
        "guardian-evidence-packets-validate",
        "guardian-evidence-reducer-dry-run",
        "guardian-evidence-reducer-input-bundles-validate",
        "guardian-evidence-reducer-input-bundle-dry-run",
    ):
        proc = subprocess.run(["make", target], cwd=ROOT, capture_output=True, text=True, check=False)
        assert proc.returncode == 0, proc.stderr
    packet = subprocess.run(["python3", "scripts/guardian/validate_evidence_packets.py", "--json"], cwd=ROOT, capture_output=True, text=True, check=False)
    bundles = subprocess.run(["python3", "scripts/guardian/validate_reducer_input_bundles.py", "--json"], cwd=ROOT, capture_output=True, text=True, check=False)
    assert packet.returncode == 0 and json.loads(packet.stdout)["matched_count"] == 2
    bundle_result = json.loads(bundles.stdout)
    assert bundles.returncode == 0
    assert bundle_result["matched_count"] >= 2
