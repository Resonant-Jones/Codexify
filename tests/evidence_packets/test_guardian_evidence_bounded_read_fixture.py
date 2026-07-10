import hashlib
import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "docs/architecture/fixtures/guardian-evidence-bounded-read.local-tooling.v1.json"
INPUT_BUNDLE_REF = "docs/architecture/fixtures/guardian-evidence-reducer-input-bundle.local-tooling.v1.json"
FIXED_TIMESTAMP = "2026-07-10T00:00:00+00:00"
REQUIRED_RESULT_FIELDS = {
    "schema_version",
    "read_contract_version",
    "input_bundle_ref",
    "input_id",
    "input_class",
    "source_ref",
    "resolved_repo_relative_path",
    "read_status",
    "content_hash",
    "content_excerpt",
    "excerpt_truncated",
    "omitted_content_reason",
    "warnings",
    "errors",
    "provenance",
    "limits",
}
STRUCTURAL_FIELDS = (
    "schema_version", "read_contract_version", "input_bundle_ref", "result", "source_count",
    "read_count", "skipped_count", "blocked_count", "missing_count", "too_large_count",
    "unsupported_count", "warning_count", "error_count",
)


def _fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _current_output() -> dict:
    proc = subprocess.run(
        [
            "python3", "scripts/guardian/read_bounded_evidence.py", INPUT_BUNDLE_REF, "--json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def _normalize_dynamic_fields(output: dict) -> dict:
    normalized = json.loads(json.dumps(output))
    normalized["input_bundle_validation_result"]["checked_at"] = FIXED_TIMESTAMP
    for result in normalized["read_results"]:
        result["provenance"]["read_at"] = FIXED_TIMESTAMP
    return normalized


def _make(target: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["make", target], cwd=ROOT, capture_output=True, text=True, check=False)


def test_bounded_read_fixture_exists_and_has_batch_shape() -> None:
    assert FIXTURE.is_file()
    fixture = _fixture()
    assert fixture["schema_version"] == "guardian_evidence_bounded_read_batch_result.v1"
    assert fixture["read_contract_version"] == "guardian_evidence_bounded_read_contract.v1"
    assert fixture["input_bundle_ref"] == INPUT_BUNDLE_REF
    assert "input_bundle_validation_result" in fixture
    assert "read_results" in fixture
    assert fixture["source_count"] == len(fixture["read_results"])
    assert fixture["read_results"]
    assert fixture["result"] in {"pass", "pass_with_warnings"}
    assert "packet" not in fixture
    assert fixture["source_count"] == 3
    assert fixture["read_count"] == 2
    assert fixture["skipped_count"] == 1
    assert fixture["blocked_count"] == 0
    assert fixture["missing_count"] == 0
    assert fixture["too_large_count"] == 0
    assert fixture["unsupported_count"] == 0
    assert fixture["error_count"] == 0
    assert fixture["warning_count"] >= 1


def test_fixture_preserves_safe_bounded_read_fields() -> None:
    fixture = _fixture()
    serialized = json.dumps(fixture)
    assert fixture["schema_version"] != "guardian_evidence_packet.v1"
    assert "/Volumes/" not in serialized
    assert "/Users/" not in serialized
    assert "/Volumes/Dev_SSD/Codex-Runner" not in serialized
    assert ".env" not in serialized.lower()
    assert "-----begin" not in serialized.lower()
    assert "git-credentials" not in serialized.lower()
    assert {"no_packet_generation", "no_execution", "no_evidence_ingestion", "no_source_mutation", "no_workorder_mutation", "no_execution_ledger_write"} <= set(fixture["limits"])

    for result in fixture["read_results"]:
        assert REQUIRED_RESULT_FIELDS <= set(result)
        assert result["schema_version"] == "guardian_evidence_bounded_read_result.v1"
        assert result["read_contract_version"] == "guardian_evidence_bounded_read_contract.v1"
        assert result["input_bundle_ref"] == INPUT_BUNDLE_REF
        if result["read_status"] == "read":
            assert re.fullmatch(r"[0-9a-f]{64}", result["content_hash"])
            assert len(result["content_excerpt"].encode("utf-8")) <= 12000
        assert set(result["limits"]) >= {"no_packet_generation", "no_execution", "no_evidence_ingestion"}


def test_fixture_matches_current_reader_output_after_timestamp_normalization() -> None:
    fixture = _fixture()
    current = _normalize_dynamic_fields(_current_output())
    assert fixture["schema_version"] == current["schema_version"]
    assert fixture["read_contract_version"] == current["read_contract_version"]
    for field in STRUCTURAL_FIELDS:
        assert fixture[field] == current[field]
    assert [item["source_ref"] for item in fixture["read_results"]] == [item["source_ref"] for item in current["read_results"]]
    assert [item["read_status"] for item in fixture["read_results"]] == [item["read_status"] for item in current["read_results"]]
    assert [item["content_hash"] for item in fixture["read_results"] if item["read_status"] == "read"] == [item["content_hash"] for item in current["read_results"] if item["read_status"] == "read"]
    assert fixture == current


def test_fixture_documents_static_only_boundaries_and_tools_remain_green() -> None:
    contract = (ROOT / "docs/architecture/guardian-evidence-bounded-read-contract.md").read_text()
    generator = (ROOT / "docs/architecture/guardian-evidence-packet-generator-contract.md").read_text()
    reducer = (ROOT / "docs/architecture/guardian-evidence-packet-reducer-contract.md").read_text()
    runtime = (ROOT / "docs/architecture/guardian-evidence-packet-runtime-reducer-design-contract.md").read_text()
    readme = (ROOT / "docs/architecture/README.md").read_text()
    current = (ROOT / "docs/architecture/00-current-state.md").read_text()
    fixture_path = "guardian-evidence-bounded-read.local-tooling.v1.json"
    assert fixture_path in contract
    assert "static proof fixture only" in contract
    assert fixture_path in generator and "separate generator implementation" in generator
    assert fixture_path in reducer
    assert fixture_path in runtime
    assert fixture_path in readme
    assert fixture_path in current

    for target in (
        "guardian-evidence-packets-validate",
        "guardian-evidence-reducer-dry-run",
        "guardian-evidence-reducer-input-bundles-validate",
        "guardian-evidence-reducer-input-bundle-dry-run",
        "guardian-evidence-bounded-read",
    ):
        proc = _make(target)
        assert proc.returncode == 0, proc.stderr

    packets = subprocess.run(
        ["python3", "scripts/guardian/validate_evidence_packets.py", "--json"],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    bundles = subprocess.run(
        ["python3", "scripts/guardian/validate_reducer_input_bundles.py", "--json"],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    assert packets.returncode == 0
    assert json.loads(packets.stdout)["matched_count"] == 2
    assert bundles.returncode == 0
    bundle_paths = [entry["path"] for entry in json.loads(bundles.stdout)["files"]]
    assert any("guardian-evidence-reducer-input-bundle-template" in path for path in bundle_paths)
    assert any("guardian-evidence-reducer-input-bundle.local-tooling" in path for path in bundle_paths)


def test_local_commands_do_not_mutate_scripts_makefile_or_packet_fixtures() -> None:
    paths = [
        ROOT / "Makefile",
        ROOT / "scripts/guardian/read_bounded_evidence.py",
        ROOT / "docs/architecture/fixtures/guardian-evidence-packet.codex-runner-bridge-proof-chain.v1.json",
        ROOT / "docs/architecture/fixtures/guardian-evidence-packet.local-validator-toolchain.v1.json",
    ]
    before = {path: (path.stat().st_size, path.stat().st_mtime_ns, hashlib.sha256(path.read_bytes()).hexdigest()) for path in paths}
    for target in ("guardian-evidence-bounded-read", "guardian-evidence-packets-validate"):
        proc = _make(target)
        assert proc.returncode == 0, proc.stderr
    after = {path: (path.stat().st_size, path.stat().st_mtime_ns, hashlib.sha256(path.read_bytes()).hexdigest()) for path in paths}
    assert before == after
