import ast
import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/guardian/validate_reducer_input_bundle.py"
FIXTURE = ROOT / "docs/architecture/fixtures/guardian-evidence-reducer-input-bundle.local-tooling.v1.json"
TEMPLATE = ROOT / "docs/architecture/templates/guardian-evidence-reducer-input-bundle-template.v1.json"
RESULT_SCHEMA = "guardian_evidence_reducer_input_bundle_static_validation_result.v1"
CONTRACT_VERSION = "guardian_evidence_reducer_input_bundle_static_validator_contract.v1"
ISSUE_CODES = (
    "bundle_json_invalid", "bundle_schema_version_missing", "bundle_schema_version_unsupported",
    "bundle_required_field_missing", "review_depth_invalid", "inputs_missing",
    "input_required_field_missing", "input_class_invalid", "source_ref_missing",
    "source_ref_absolute_path_warning", "source_ref_secret_risk", "source_ref_file_read_claim",
    "operator_context_not_list", "provenance_missing", "template_marker_missing",
    "static_fixture_marker_missing", "limits_missing", "boundary_language_missing",
    "evidence_ingestion_claim_risk", "packet_generation_claim_risk", "runtime_reducer_claim_risk",
    "execution_claim_risk", "ci_release_gate_claim_risk",
)


def _run(path: Path) -> tuple[subprocess.CompletedProcess[str], dict]:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), str(path), "--json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc, json.loads(proc.stdout)


def _bundle() -> dict:
    return json.loads(FIXTURE.read_text())


def _write(tmp_path: Path, bundle: object, name: str = "bundle.json") -> Path:
    path = tmp_path / name
    if isinstance(bundle, str):
        path.write_text(bundle)
    else:
        path.write_text(json.dumps(bundle))
    return path


def _codes(result: dict) -> set[str]:
    return {issue["code"] for issue in result["issues"]}


def test_script_exists_and_imports_without_side_effects() -> None:
    assert SCRIPT.is_file()
    spec = importlib.util.spec_from_file_location("validate_reducer_input_bundle", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)


def test_script_imports_only_stdlib_and_guardian_contract_modules() -> None:
    tree = ast.parse(SCRIPT.read_text())
    allowed_guardian = {"guardian.evidence_packets.contracts", "guardian.evidence_packets.reducer_contracts"}
    forbidden_fragments = ("fastapi", "database", "command_bus", "codex_runner", "scripts.guardian", "subprocess", "requests", "httpx", "docker")
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or ""]
        else:
            continue
        for name in names:
            assert not any(fragment in name.lower() for fragment in forbidden_fragments)
            assert not name.startswith("guardian.") or name in allowed_guardian


def test_fixture_result_has_required_shape() -> None:
    proc, result = _run(FIXTURE)
    assert proc.returncode == 0
    assert result["schema_version"] == RESULT_SCHEMA
    assert result["validator_contract_version"] == CONTRACT_VERSION
    for field in ("validated_bundle_ref", "result", "issue_count", "issues", "checked_at", "checked_by", "limits"):
        assert field in result
    assert result["issue_count"] == len(result["issues"])
    assert result["result"] in {"pass", "pass_with_warnings"}


def test_template_validates() -> None:
    proc, result = _run(TEMPLATE)
    assert proc.returncode == 0
    assert result["result"] in {"pass", "pass_with_warnings"}


def test_structural_errors(tmp_path: Path) -> None:
    cases = [
        ("{", "bundle_json_invalid", 1),
        ({"bundle_id": "x"}, "bundle_schema_version_missing", 1),
        ({**_bundle(), "schema_version": "wrong.v1"}, "bundle_schema_version_unsupported", 1),
        ({key: value for key, value in _bundle().items() if key != "bundle_id"}, "bundle_required_field_missing", 1),
        ({**_bundle(), "review_depth": "invalid"}, "review_depth_invalid", 1),
        ({**_bundle(), "inputs": []}, "inputs_missing", 1),
        ({**_bundle(), "inputs": [{"input_id": "only-id"}]}, "input_required_field_missing", 1),
        ({**_bundle(), "inputs": [{**_bundle()["inputs"][0], "input_class": "invalid"}]}, "input_class_invalid", 1),
        ({**_bundle(), "inputs": [{key: value for key, value in _bundle()["inputs"][0].items() if key != "source_ref"}]}, "source_ref_missing", 1),
        ({**_bundle(), "operator_context": "not-a-list"}, "operator_context_not_list", 1),
        ({key: value for key, value in _bundle().items() if key != "provenance"}, "provenance_missing", 1),
    ]
    for index, (bundle, code, expected_exit) in enumerate(cases):
        proc, result = _run(_write(tmp_path, bundle, f"case-{index}.json"))
        assert proc.returncode == expected_exit
        assert code in _codes(result)


def test_boundary_and_posture_warnings(tmp_path: Path) -> None:
    base = _bundle()
    cases = [
        ({**base, "inputs": [{**base["inputs"][0], "source_ref": "/absolute/path"}]}, "source_ref_absolute_path_warning"),
        ({**base, "inputs": [{**base["inputs"][0], "source_ref": "https://x.test?api_key=secret-value"}]}, "source_ref_secret_risk"),
        ({**base, "operator_context": ["The source reference was read before validation."]}, "source_ref_file_read_claim"),
        ({**base, "limits": []}, "limits_missing"),
    ]
    for index, (bundle, code) in enumerate(cases):
        proc, result = _run(_write(tmp_path, bundle, f"warning-{index}.json"))
        assert proc.returncode == 0
        assert result["result"] == "pass_with_warnings"
        assert code in _codes(result)

    no_marker_template = copy.deepcopy(base)
    no_marker_template["provenance"].pop("template", None)
    path = tmp_path / "docs" / "architecture" / "templates" / "template.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(no_marker_template))
    proc, result = _run(path)
    assert proc.returncode == 0 and "template_marker_missing" in _codes(result)

    no_marker_fixture = copy.deepcopy(base)
    no_marker_fixture["provenance"].pop("static_fixture", None)
    path = tmp_path / "docs" / "architecture" / "fixtures" / "fixture.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(no_marker_fixture))
    proc, result = _run(path)
    assert proc.returncode == 0 and "static_fixture_marker_missing" in _codes(result)


def test_positive_claim_warnings_and_negative_framing(tmp_path: Path) -> None:
    claims = (
        ("evidence ingestion is supported", "evidence_ingestion_claim_risk"),
        ("packet generation is supported", "packet_generation_claim_risk"),
        ("runtime reducer support is shipped", "runtime_reducer_claim_risk"),
        ("execution support is enabled", "execution_claim_risk"),
        ("CI/default release gating is enabled", "ci_release_gate_claim_risk"),
    )
    for index, (claim, code) in enumerate(claims):
        bundle = _bundle()
        bundle["operator_context"] = [claim]
        proc, result = _run(_write(tmp_path, bundle, f"claim-{index}.json"))
        assert proc.returncode == 0 and code in _codes(result)

    safe = _bundle()
    safe["operator_context"] = [
        "This does not authorize evidence ingestion, packet generation, runtime reducer behavior, execution support, or CI/default release gating.",
    ]
    proc, result = _run(_write(tmp_path, safe, "negative.json"))
    assert proc.returncode == 0
    assert not _codes(result).intersection({code for _, code in claims})


def test_validator_does_not_read_source_refs_or_write_repo_files(tmp_path: Path) -> None:
    bundle = _bundle()
    bundle["inputs"][0]["source_ref"] = str(tmp_path / "must-not-be-read.json")
    before = SCRIPT.read_bytes()
    proc, result = _run(_write(tmp_path, bundle, "no-read.json"))
    assert proc.returncode == 0
    assert "source_ref_missing" not in _codes(result)
    assert SCRIPT.read_bytes() == before


def test_issue_codes_stay_local_and_existing_targets_remain_green() -> None:
    for path in (ROOT / "guardian/protocol_tokens.py", ROOT / "guardian/evidence_packets/contracts.py", ROOT / "guardian/evidence_packets/reducer_contracts.py"):
        text = path.read_text()
        assert not any(code in text for code in ISSUE_CODES)
    for target in ("guardian-evidence-packets-validate", "guardian-evidence-reducer-dry-run"):
        proc = subprocess.run(["make", target], cwd=ROOT, capture_output=True, text=True, check=False)
        assert proc.returncode == 0, proc.stderr
    proc = subprocess.run(["python3", "scripts/guardian/validate_evidence_packets.py", "--json"], cwd=ROOT, capture_output=True, text=True, check=False)
    assert proc.returncode == 0
    assert json.loads(proc.stdout)["matched_count"] == 2
