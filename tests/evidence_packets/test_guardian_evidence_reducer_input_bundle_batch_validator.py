import ast
import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/guardian/validate_reducer_input_bundles.py"
FIXTURE = ROOT / "docs/architecture/fixtures/guardian-evidence-reducer-input-bundle.local-tooling.v1.json"
TEMPLATE = ROOT / "docs/architecture/templates/guardian-evidence-reducer-input-bundle-template.v1.json"
RESULT_SCHEMA = "guardian_evidence_reducer_input_bundle_batch_validation_result.v1"
CONTRACT_VERSION = "guardian_evidence_reducer_input_bundle_static_validator_contract.v1"


def _run(*args: str) -> tuple[subprocess.CompletedProcess[str], dict]:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), *args, "--json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc, json.loads(proc.stdout)


def _fixture() -> dict:
    return json.loads(FIXTURE.read_text())


def _write(path: Path, bundle: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(bundle if isinstance(bundle, str) else json.dumps(bundle))
    return path


def test_batch_script_exists_and_imports_without_side_effects() -> None:
    assert SCRIPT.is_file()
    spec = importlib.util.spec_from_file_location("validate_reducer_input_bundles", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)


def test_batch_script_imports_only_allowed_modules() -> None:
    tree = ast.parse(SCRIPT.read_text())
    allowed = {
        "scripts.guardian.validate_reducer_input_bundle",
        "guardian.evidence_packets.contracts",
        "guardian.evidence_packets.reducer_contracts",
    }
    forbidden = ("fastapi", "database", "command_bus", "codex_runner", "subprocess", "requests", "httpx", "docker", "reducer_dry_run", "validate_evidence_packet")
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


def test_default_batch_output_discovers_only_input_bundles() -> None:
    proc, result = _run()
    assert proc.returncode == 0
    assert result["schema_version"] == RESULT_SCHEMA
    assert result["validator_contract_version"] == CONTRACT_VERSION
    for field in ("result", "matched_count", "pass_count", "warning_count", "fail_count", "issue_count", "validated_at", "checked_by", "files", "limits"):
        assert field in result
    paths = [entry["path"] for entry in result["files"]]
    assert result["matched_count"] >= 2
    assert any(Path(path).resolve() == TEMPLATE.resolve() for path in paths)
    assert any(Path(path).resolve() == FIXTURE.resolve() for path in paths)
    assert paths == sorted(paths)
    assert all("guardian-evidence-packet." not in path for path in paths)
    assert result["issue_count"] == sum(entry["issue_count"] for entry in result["files"])
    assert result["result"] in {"pass", "pass_with_warnings"}


def test_empty_discovery_fails_without_writing(tmp_path: Path) -> None:
    proc, result = _run("--templates-dir", str(tmp_path / "templates"), "--fixtures-dir", str(tmp_path / "fixtures"))
    assert proc.returncode == 1
    assert result["result"] == "fail"
    assert result["matched_count"] == 0
    assert result["issues"][0]["code"] == "input_bundle_files_missing"
    assert list(tmp_path.rglob("*")) == []


def test_custom_dirs_support_fail_and_warning_aggregation(tmp_path: Path) -> None:
    templates = tmp_path / "templates"
    fixtures = tmp_path / "fixtures"
    bad = _fixture()
    bad.pop("schema_version")
    _write(templates / "guardian-evidence-reducer-input-bundle-bad.json", bad)
    proc, result = _run("--templates-dir", str(templates), "--fixtures-dir", str(fixtures))
    assert proc.returncode == 1
    assert result["fail_count"] == 1
    assert result["files"][0]["result"] == "fail"

    warning = copy.deepcopy(_fixture())
    warning["inputs"][0]["source_ref"] = "/absolute/source-ref"
    _write(templates / "guardian-evidence-reducer-input-bundle-warning.json", warning)
    proc, result = _run("--templates-dir", str(templates), "--fixtures-dir", str(fixtures))
    assert proc.returncode == 1
    assert result["fail_count"] == 1

    bad_path = templates / "guardian-evidence-reducer-input-bundle-bad.json"
    bad_path.unlink()
    proc, result = _run("--templates-dir", str(templates), "--fixtures-dir", str(fixtures))
    assert proc.returncode == 0
    assert result["result"] == "pass_with_warnings"
    assert result["warning_count"] == 1


def test_batch_does_not_read_source_refs_or_write_files(tmp_path: Path) -> None:
    bundle = _fixture()
    bundle["inputs"][0]["source_ref"] = str(tmp_path / "must-not-be-read.json")
    path = _write(tmp_path / "templates" / "guardian-evidence-reducer-input-bundle-no-read.json", bundle)
    before = path.read_bytes()
    proc, result = _run("--templates-dir", str(path.parent), "--fixtures-dir", str(tmp_path / "empty"))
    assert proc.returncode == 0
    assert result["matched_count"] == 1
    assert path.read_bytes() == before


def test_batch_issue_code_is_not_a_runtime_token() -> None:
    for path in (
        ROOT / "guardian/protocol_tokens.py",
        ROOT / "guardian/evidence_packets/contracts.py",
        ROOT / "guardian/evidence_packets/reducer_contracts.py",
    ):
        assert "input_bundle_files_missing" not in path.read_text()


def test_existing_local_targets_and_packet_batch_validator_remain_green() -> None:
    for target in ("guardian-evidence-packets-validate", "guardian-evidence-reducer-dry-run"):
        proc = subprocess.run(["make", target], cwd=ROOT, capture_output=True, text=True, check=False)
        assert proc.returncode == 0, proc.stderr
    proc = subprocess.run(["python3", "scripts/guardian/validate_evidence_packets.py", "--json"], cwd=ROOT, capture_output=True, text=True, check=False)
    assert proc.returncode == 0
    assert json.loads(proc.stdout)["matched_count"] == 2
