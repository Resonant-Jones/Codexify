import ast
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/guardian/generate_evidence_packet.py"
INPUT = "docs/architecture/fixtures/guardian-evidence-bounded-read.local-tooling.v1.json"


def _run(*extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["python3", str(SCRIPT), INPUT, "--json", *extra], cwd=ROOT, capture_output=True, text=True, check=False)


def test_generator_is_bounded_and_generates_valid_stdout_packet() -> None:
    assert SCRIPT.is_file()
    source = SCRIPT.read_text()
    tree = ast.parse(source)
    imports = {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    assert "scripts.guardian" in imports
    for forbidden in ("subprocess", "requests", "httpx", "docker", "fastapi", "scripts.guardian.read_bounded_evidence", "scripts.guardian.reducer_dry_run", "scripts.guardian.validate_reducer_input_bundle"):
        assert forbidden not in imports and forbidden not in source
    first = _run()
    second = _run()
    assert first.returncode == second.returncode == 0
    result = json.loads(first.stdout)
    repeat = json.loads(second.stdout)
    assert result == repeat
    assert result["schema_version"] == "guardian_evidence_packet_generator_result.v1"
    assert result["generator_contract_version"] == "guardian_evidence_packet_generator_contract.v1"
    assert result["bounded_read_result_ref"] == INPUT
    assert result["packet_validation_result"]["result"] in {"pass", "pass_with_warnings"}
    assert all(value is False for value in result["authority_state"].values())
    assert {"stdout_only", "no_fixture_write", "no_execution", "no_evidence_ingestion", "no_command_bus", "no_codex_runner", "no_pi_loop", "no_source_mutation", "no_provider_execution", "no_workorder_mutation", "no_execution_ledger_write"} <= set(result["limits"])
    packet = result["packet"]
    assert packet["schema_version"] == "guardian_evidence_packet.v1"
    assert {ref["uri_or_path"] for ref in packet["raw_evidence_refs"]} >= {"docs/architecture/guardian-evidence-packet-runtime-reducer-design-contract.md", "docs/architecture/fixtures/guardian-evidence-packet.local-validator-toolchain.v1.json"}
    assert any("skipped" in item["description"] for item in packet["uncertainty"])
    joined = json.dumps(packet).lower()
    for phrase in ("not authority", "not execution", "not evidence ingestion", "not source truth approval", "not receipt trust", "not workorder mutation", "not execution ledger write", "not release approval"):
        assert phrase in joined


def test_generator_rejects_invalid_inputs(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text('{"result":"fail"}', encoding="utf-8")
    proc = subprocess.run(["python3", str(SCRIPT), str(bad), "--json"], cwd=ROOT, capture_output=True, text=True, check=False)
    assert proc.returncode == 1


def test_generator_fails_closed_when_all_bounded_reads_are_skipped(tmp_path: Path) -> None:
    data = json.loads((ROOT / INPUT).read_text())
    for item in data["read_results"]:
        item["read_status"] = "skipped"
        item["content_hash"] = None
        item["content_excerpt"] = None
    path = tmp_path / "skipped-only.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    proc = subprocess.run(["python3", str(SCRIPT), str(path), "--json"], cwd=ROOT, capture_output=True, text=True, check=False)
    assert proc.returncode == 1
    output = json.loads(proc.stdout)
    assert output["result"] == "fail"
    assert output["errors"][0] == {"code": "no_usable_evidence_refs", "message": "bounded-read input contains no usable read evidence refs"}
    assert "packet" not in output


def test_generator_fails_closed_on_non_object_read_results_entry(tmp_path: Path) -> None:
    data = json.loads((ROOT / INPUT).read_text())
    data["read_results"].insert(1, None)
    path = tmp_path / "malformed-entry.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    proc = subprocess.run(["python3", str(SCRIPT), str(path), "--json"], cwd=ROOT, capture_output=True, text=True, check=False)
    assert proc.returncode == 1
    output = json.loads(proc.stdout)
    assert output["result"] == "fail"
    assert output["errors"][0]["code"] == "malformed_read_result_entry"
    assert "packet" not in output
    assert "Traceback" not in proc.stderr


def test_generator_docs_are_linked() -> None:
    for path in ("docs/architecture/guardian-evidence-packet-generator-contract.md", "docs/architecture/README.md", "docs/architecture/00-current-state.md"):
        assert "generate_evidence_packet.py" in (ROOT / path).read_text()
