import ast
import json
import subprocess
import sys
from pathlib import Path

import pytest

import scripts.guardian.reducer_dry_run as reducer_dry_run


ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "scripts/guardian/reducer_dry_run.py"
FIXTURE = ROOT / "docs/architecture/fixtures/guardian-evidence-packet.generated-local-tooling.v1.json"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(CLI), *args], cwd=ROOT, capture_output=True, text=True, check=False)


def _write(path: Path, value: object) -> Path:
    path.write_text(value if isinstance(value, str) else json.dumps(value))
    return path


def test_cli_import_boundary_includes_validate_evidence_packet() -> None:
    tree = ast.parse(CLI.read_text())
    allowed = {
        "guardian.evidence_packets.contracts",
        "guardian.evidence_packets.reducer_contracts",
        "guardian.evidence_packets.reducer",
        "scripts.guardian.validate_evidence_packet",
        "scripts.guardian.validate_reducer_input_bundle",
    }
    forbidden = (
        "fastapi", "database", "command_bus", "codex_runner", "validate_reducer_input_bundles",
        "subprocess", "requests", "httpx", "docker",
    )
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or ""]
        else:
            continue
        for name in names:
            assert not any(fragment in name.lower() for fragment in forbidden)
            assert not name.startswith(("guardian.", "scripts.")) or name in allowed


def test_evidence_packet_loader_returns_diagnostics_only() -> None:
    proc = _run("--json", "--evidence-packet", str(FIXTURE))
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert data["schema_version"] == "guardian_evidence_packet_dry_run_diagnostics.v1"
    assert data["evidence_packet_ref"].endswith("guardian-evidence-packet.generated-local-tooling.v1.json")
    assert data["packet_ref"] == data["evidence_packet_ref"]
    assert data["packet_loaded"] is True
    fixture = json.loads(FIXTURE.read_text())
    assert data["packet_id"] == fixture["packet_id"]
    assert data["packet_schema_version"] == fixture["schema_version"]
    assert data["packet_validation_result"] == data["validation_result"]
    expected_counts = {
        "raw_evidence_ref_count": len(fixture.get("raw_evidence_refs") or []),
        "claim_count": len(fixture.get("claim_ledger") or []),
        "uncertainty_count": len(fixture.get("uncertainty") or []),
        "forbidden_interpretation_count": len(fixture.get("forbidden_interpretations") or []),
    }
    for field, expected in expected_counts.items():
        assert isinstance(data[field], int)
        assert data[field] == expected
    assert data["packet_metadata"]["schema_version"] == "guardian_evidence_packet.v1"
    assert data["packet_metadata"]["packet_id"] is not None
    assert data["packet_metadata"]["created_at"] is not None
    assert data["packet_metadata"]["source_domain"] is not None
    assert data["packet_metadata"]["evidence_class"] is not None
    assert data["packet_metadata"]["review_depth"] is not None
    assert data["packet_metadata"]["subject"] is not None
    assert data["packet_metadata"]["reducer_profile_ref"] is not None
    assert data["validation_result"]["result"] in {"pass", "pass_with_warnings"}
    from guardian.evidence_packets.contracts import REQUIRED_AUTHORITY_LOCKS
    assert set(data["authority_state"]) == set(REQUIRED_AUTHORITY_LOCKS)
    assert all(value is False for value in data["authority_state"].values())
    assert data["diagnostics"]["lifecycle_steps_completed"] == [
        "receive_bounded_evidence_input_set", "classify_input_classes", "stop"
    ]
    assert "does not produce GuardianEvidencePacket output" in data["diagnostics"]["warnings"][0]
    for limit in (
        "no_execution_authority", "no_receipt_trust",
        "no_workorder_mutation", "no_execution_ledger_write",
    ):
        assert limit in data["limits"]


def test_combined_with_input_bundle_exits_with_error(tmp_path: Path) -> None:
    packet = _write(tmp_path / "packet.json", json.loads(FIXTURE.read_text()))
    bundle = tmp_path / "dummy.json"
    bundle.touch()
    proc = _run("--json", "--evidence-packet", str(packet), "--input-bundle", str(bundle))
    assert proc.returncode == 1
    assert "mutually exclusive" in proc.stderr


def test_combined_with_inline_input_exits_with_error(tmp_path: Path) -> None:
    packet = _write(tmp_path / "packet.json", json.loads(FIXTURE.read_text()))
    proc = _run("--json", "--evidence-packet", str(packet), "--input", "x:static_docs:ref")
    assert proc.returncode == 1
    assert "cannot be combined" in proc.stderr


def test_malformed_json_exits_with_bounded_failure(tmp_path: Path) -> None:
    path = _write(tmp_path / "malformed.json", "{invalid")
    proc = _run("--json", "--evidence-packet", str(path))
    assert proc.returncode == 1
    data = json.loads(proc.stdout)
    assert data["packet_loaded"] is False
    assert data["packet_metadata"] is None
    assert data["validation_result"]["result"] == "fail"
    assert any("packet_json_invalid" in issue["code"] for issue in data["validation_result"]["issues"])


def test_unreadable_file_exits_with_bounded_failure(tmp_path: Path) -> None:
    path = tmp_path / "nonexistent.json"
    proc = _run("--json", "--evidence-packet", str(path))
    assert proc.returncode == 1
    data = json.loads(proc.stdout)
    assert data["packet_loaded"] is False
    assert data["validation_result"]["result"] == "fail"


def test_wrong_schema_exits_with_bounded_failure(tmp_path: Path) -> None:
    packet = json.loads(FIXTURE.read_text())
    packet["schema_version"] = "wrong_schema.v1"
    path = _write(tmp_path / "wrong_schema.json", packet)
    proc = _run("--json", "--evidence-packet", str(path))
    assert proc.returncode == 1
    data = json.loads(proc.stdout)
    assert data["packet_loaded"] is False
    assert data["validation_result"]["result"] == "fail"
    assert any("packet_schema_version_unsupported" in issue["code"] for issue in data["validation_result"]["issues"])


def test_static_validation_failure_stops_before_diagnostics(tmp_path: Path) -> None:
    packet = json.loads(FIXTURE.read_text())
    packet.pop("reducer_profile_ref")
    path = _write(tmp_path / "invalid.json", packet)
    output, exit_code = reducer_dry_run._run_evidence_packet(type("Args", (), {"evidence_packet": path})())
    assert exit_code == 1
    assert output["packet_loaded"] is False
    assert output["packet_metadata"] is None
    assert output["validation_result"]["result"] == "fail"
    assert any("reducer_profile_ref" in issue["message"] or "reducer_profile" in issue["code"]
               for issue in output["validation_result"]["issues"])


def test_existing_no_input_mode_remains_unchanged() -> None:
    proc = _run("--json")
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert data["schema_version"] == "guardian_evidence_packet_reducer_dry_run_result.v1"
    assert data["bundle_id"] == "reducer_dry_run"
    assert data["packet"] is None
    assert data["validation_result"] is None


def test_existing_input_bundle_mode_remains_unchanged() -> None:
    bundle = ROOT / "docs/architecture/fixtures/guardian-evidence-reducer-input-bundle.local-tooling.v1.json"
    assert bundle.exists()
    proc = _run("--json", "--input-bundle", str(bundle))
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert data["schema_version"] == "guardian_evidence_reducer_input_bundle_dry_run_result.v1"


def test_existing_inline_input_mode_remains_unchanged() -> None:
    proc = _run("--json", "--input", "test:static_docs:docs/architecture/README.md")
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert data["input_count"] == 1
    assert data["packet"] is None
    assert data["validation_result"] is None
