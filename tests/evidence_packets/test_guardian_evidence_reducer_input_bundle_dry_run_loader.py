import ast
import copy
import json
import subprocess
import sys
from pathlib import Path

import scripts.guardian.reducer_dry_run as reducer_dry_run


ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "scripts/guardian/reducer_dry_run.py"
FIXTURE = ROOT / "docs/architecture/fixtures/guardian-evidence-reducer-input-bundle.local-tooling.v1.json"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(CLI), *args], cwd=ROOT, capture_output=True, text=True, check=False)


def _fixture() -> dict:
    return json.loads(FIXTURE.read_text())


def _write(path: Path, value: object) -> Path:
    path.write_text(value if isinstance(value, str) else json.dumps(value))
    return path


def test_cli_import_boundary_is_local_and_allowed() -> None:
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


def test_input_bundle_loader_returns_diagnostics_only() -> None:
    proc = _run(
        "--json", "--input-bundle",
        "docs/architecture/fixtures/guardian-evidence-reducer-input-bundle.local-tooling.v1.json",
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert data["schema_version"] == "guardian_evidence_reducer_input_bundle_dry_run_result.v1"
    assert data["input_bundle_ref"].endswith("guardian-evidence-reducer-input-bundle.local-tooling.v1.json")
    assert data["input_bundle_validation_result"]["result"] in {"pass", "pass_with_warnings"}
    assert data["reducer_result"] is not None
    assert data["packet"] is None
    assert data["validation_result"] is None
    assert data["reducer_result"]["packet"] is None
    assert data["reducer_result"]["validation_result"] is None
    assert data["reducer_result"]["diagnostics"]["lifecycle_steps_completed"] == [
        "receive_bounded_evidence_input_set", "classify_input_classes", "stop"
    ]
    assert all(value is False for value in data["authority_state"].values())
    assert data["limits"] == [
        "no_source_ref_reads", "no_evidence_ingestion", "no_packet_generation",
        "no_runtime_reducer_behavior", "no_command_bus", "no_codex_runner", "no_pi_loop",
        "no_provider_execution", "no_source_mutation", "no_workorder_mutation",
        "no_execution_ledger_write", "no_release_support_expansion",
    ]


def test_loader_preserves_bundle_metadata_without_reading_refs(tmp_path: Path) -> None:
    bundle = _fixture()
    missing_source = tmp_path / "source-that-must-not-be-read.json"
    for item in bundle["inputs"]:
        item["source_ref"] = str(missing_source)
    path = _write(tmp_path / "bundle.json", bundle)
    before = path.read_bytes()
    proc = _run("--json", "--input-bundle", str(path))
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert data["reducer_result"] is not None
    # The CLI only exposes diagnostics, so verify the loader's in-memory mapping directly.
    validation = reducer_dry_run.validate_bundle_file(path)
    assert validation["result"] == "pass_with_warnings"
    assert path.read_bytes() == before


def test_failed_validation_stops_before_dry_run(tmp_path: Path, monkeypatch) -> None:
    bundle = _fixture()
    bundle.pop("schema_version")
    path = _write(tmp_path / "invalid.json", bundle)
    called = False

    def fail_if_called(_bundle):
        nonlocal called
        called = True
        raise AssertionError("dry_run_reducer must not run after failed validation")

    monkeypatch.setattr(reducer_dry_run, "dry_run_reducer", fail_if_called)
    output, exit_code = reducer_dry_run._run_input_bundle(type("Args", (), {"input_bundle": path})())
    assert exit_code == 1
    assert output["input_bundle_validation_result"]["result"] == "fail"
    assert output["reducer_result"] is None
    assert output["packet"] is None
    assert output["validation_result"] is None
    assert called is False


def test_invalid_bundle_cli_and_argument_exits(tmp_path: Path) -> None:
    malformed = _write(tmp_path / "malformed.json", "{")
    proc = _run("--json", "--input-bundle", str(malformed))
    assert proc.returncode == 1
    data = json.loads(proc.stdout)
    assert data["input_bundle_validation_result"]["result"] == "fail"
    assert data["reducer_result"] is None

    proc = _run("--json", "--input-bundle", str(malformed), "--input", "x:static_docs:ref")
    assert proc.returncode == 2
    assert proc.stderr

    proc = _run("--json", "--input-bundle")
    assert proc.returncode == 2


def test_existing_cli_modes_and_local_targets_remain_green() -> None:
    assert _run("--json").returncode == 0
    assert _run("--json", "--input", "sample:static_docs:docs/architecture/README.md").returncode == 0
    for target in (
        "guardian-evidence-packets-validate",
        "guardian-evidence-reducer-dry-run",
        "guardian-evidence-reducer-input-bundles-validate",
    ):
        proc = subprocess.run(["make", target], cwd=ROOT, capture_output=True, text=True, check=False)
        assert proc.returncode == 0, proc.stderr


def test_source_and_fixture_files_are_not_mutated(tmp_path: Path) -> None:
    bundle = copy.deepcopy(_fixture())
    path = _write(tmp_path / "bundle.json", bundle)
    before_cli = CLI.read_bytes()
    before_bundle = path.read_bytes()
    proc = _run("--json", "--input-bundle", str(path))
    assert proc.returncode == 0
    assert CLI.read_bytes() == before_cli
    assert path.read_bytes() == before_bundle
