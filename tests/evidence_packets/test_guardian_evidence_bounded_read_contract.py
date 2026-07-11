import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "docs/architecture/guardian-evidence-bounded-read-contract.md"

SECTIONS = (
    "Purpose", "Status", "Scope", "Current Truth", "Why This Exists",
    "Bounded Read Is Not Authority", "Bounded Read Is Not Execution",
    "Bounded Read Is Not Evidence Ingestion", "Bounded Read Is Not Packet Generation",
    "Allowed Read Sources", "Disallowed Read Sources", "Source Reference Resolution Rules",
    "Local Path Boundary", "Network Boundary", "Secret and Sensitive Content Boundary",
    "Size and Truncation Rules", "Content Hash and Provenance Rules", "Read Artifact Shape",
    "Read Result Semantics", "Error and Warning Semantics", "Relationship to ReducerInputBundle",
    "Relationship to Dry-Run Loader", "Relationship to Packet Generator",
    "Relationship to Static Packet Validation", "Relationship to Execution Ledger and WorkOrder",
    "Relationship to UI and CI", "Forbidden Interpretations", "Future Allowed Slices",
    "Bottom Line",
)


def test_bounded_read_contract_exists_and_has_required_sections() -> None:
    assert CONTRACT.is_file()
    text = CONTRACT.read_text()
    for index, section in enumerate(SECTIONS, start=1):
        assert f"## {index}. {section}" in text


def test_bounded_read_contract_preserves_docs_only_boundaries() -> None:
    text = CONTRACT.read_text()
    for phrase in (
        "This is a docs-only contract",
        "does not implement a bounded evidence reader",
        "does not read source references",
        "does not modify scripts",
        "does not modify Makefile",
        "does not read source_ref targets",
        "does not generate a `GuardianEvidencePacket` output",
        "does not add a runtime or operator read surface",
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
        "may read only explicitly allowed local source references",
        "must not follow network URLs",
        "must not read secrets",
        "must not call command bus",
        "must not call Codex Runner",
        "must not mutate WorkOrders",
        "must not write Execution Ledger entries",
    ):
        assert phrase in text


def test_allowed_and_disallowed_sources_are_documented() -> None:
    text = CONTRACT.read_text()
    for phrase in (
        "docs/architecture",
        "docs/architecture/fixtures",
        "docs/architecture/templates",
        "explicitly referenced by validated input bundles",
        "Test result summary files explicitly produced by local validation tasks",
        "Static proof index files explicitly named by a later implementation",
        "Absolute paths outside the repository",
        "Network URLs and network-backed references",
        "Secrets files and environment files such as `.env`",
        "Private key files and Git credentials",
        "Database files and Docker volumes",
        "Runtime logs unless a separate contract explicitly permits them",
        "User home directories outside the repository",
        "`/Volumes/Dev_SSD/Codex-Runner` unless a separate read contract explicitly",
        "Any file not explicitly referenced by a validated input bundle",
    ):
        assert phrase in text


def test_read_result_shape_statuses_and_diagnostics_are_documented() -> None:
    text = CONTRACT.read_text()
    for phrase in (
        "GuardianEvidenceBoundedReadResult",
        "schema_version", "read_contract_version", "input_bundle_ref", "source_ref",
        "resolved_repo_relative_path", "read_status", "content_hash", "content_excerpt",
        "excerpt_truncated", "omitted_content_reason", "warnings", "errors", "provenance",
        "limits", "`read`", "`skipped`", "`blocked`", "`missing`", "`too_large`",
        "`unsupported`", "source_ref_outside_repo", "source_ref_network_url_blocked",
        "source_ref_secret_risk_blocked", "source_ref_missing", "source_ref_too_large",
        "source_ref_unsupported_type", "source_ref_not_allowlisted", "content_truncated",
        "content_hash_unavailable", "Validated ReducerInputBundle",
        "future bounded evidence reader", "GuardianEvidencePacket", "static packet validator",
        "human/operator review", "not release approval",
    ):
        assert phrase in text


def test_cross_links_and_existing_tools_remain_green() -> None:
    generator = (ROOT / "docs/architecture/guardian-evidence-packet-generator-contract.md").read_text()
    reducer = (ROOT / "docs/architecture/guardian-evidence-packet-reducer-contract.md").read_text()
    runtime = (ROOT / "docs/architecture/guardian-evidence-packet-runtime-reducer-design-contract.md").read_text()
    loader = (ROOT / "docs/architecture/guardian-evidence-reducer-input-bundle-dry-run-loader-contract.md").read_text()
    validator = (ROOT / "docs/architecture/guardian-evidence-reducer-input-bundle-static-validator-contract.md").read_text()
    readme = (ROOT / "docs/architecture/README.md").read_text()
    current = (ROOT / "docs/architecture/00-current-state.md").read_text()

    assert "guardian-evidence-bounded-read-contract.md" in generator
    assert "guardian-evidence-bounded-read-contract.md" in reducer
    assert "guardian-evidence-bounded-read-contract.md" in runtime
    assert "loader success is not bounded reading" in loader
    assert "validator success is not read approval" in validator
    assert "guardian-evidence-bounded-read-contract.md" in readme
    assert "Guardian Evidence bounded read contract" in current

    for target in (
        "guardian-evidence-packets-validate",
        "guardian-evidence-reducer-dry-run",
        "guardian-evidence-reducer-input-bundles-validate",
        "guardian-evidence-reducer-input-bundle-dry-run",
    ):
        proc = subprocess.run(["make", target], cwd=ROOT, capture_output=True, text=True, check=False)
        assert proc.returncode == 0, proc.stderr

    packet = subprocess.run(
        ["python3", "scripts/guardian/validate_evidence_packets.py", "--json"],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    bundles = subprocess.run(
        ["python3", "scripts/guardian/validate_reducer_input_bundles.py", "--json"],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    assert packet.returncode == 0
    assert json.loads(packet.stdout)["matched_count"] == 3
    assert bundles.returncode == 0
    assert json.loads(bundles.stdout)["matched_count"] >= 2


def test_task_scope_does_not_add_reader_or_tooling_files() -> None:
    assert not (ROOT / "scripts/guardian/bounded_evidence_reader.py").exists()
    assert not (ROOT / "scripts/guardian/read_evidence.py").exists()
