import ast
import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/guardian/read_bounded_evidence.py"
CONTRACT = ROOT / "docs/architecture/guardian-evidence-bounded-read-contract.md"

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
EXPECTED_LIMITS = {
    "no_execution",
    "no_evidence_ingestion",
    "no_packet_generation",
    "no_command_bus",
    "no_codex_runner",
    "no_pi_loop",
    "no_source_mutation",
    "no_provider_execution",
    "no_workorder_mutation",
    "no_execution_ledger_write",
    "no_release_support_expansion",
}


def _bundle(tmp_path: Path, source_refs: list[str], *, valid: bool = True) -> Path:
    payload = {
        "schema_version": "guardian_evidence_reducer_input_bundle.v1",
        "bundle_id": "test-bounded-read",
        "review_depth": "light",
        "inputs": [
            {
                "input_id": f"input-{index}",
                "input_class": "static_docs",
                "source_ref": source_ref,
                "evidence_posture": "reference-only; not authority",
                "notes": ["Test reference only; does not authorize file reads."],
            }
            for index, source_ref in enumerate(source_refs)
        ],
        "operator_context": ["Temporary test bundle; not execution authority."],
        "provenance": {"test_fixture": True, "description": "temporary test input bundle"},
        "limits": [
            "This does not authorize file reads.",
            "This does not authorize evidence ingestion.",
            "This does not authorize packet generation.",
            "This does not authorize runtime reducer behavior.",
            "This does not authorize command bus calls.",
            "This does not authorize Codex Runner invocation.",
            "This does not authorize Pi Loop invocation.",
            "This does not authorize source mutation.",
            "This does not authorize provider execution.",
            "This does not authorize Execution Ledger writes.",
            "This does not authorize WorkOrder mutation.",
            "This does not widen release support.",
        ],
    }
    if not valid:
        del payload["inputs"]
    path_parent = tmp_path
    path_parent.mkdir(parents=True, exist_ok=True)
    path = path_parent / "bundle.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _run(bundle: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", str(SCRIPT), str(bundle), "--json", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def _output(proc: subprocess.CompletedProcess[str]) -> dict:
    assert proc.stdout, proc.stderr
    return json.loads(proc.stdout)


def test_bounded_read_script_exists_and_imports_without_side_effects() -> None:
    assert SCRIPT.is_file()
    spec = importlib.util.spec_from_file_location("bounded_read_under_test", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.DEFAULT_MAX_BYTES == 12000
    assert module.LIMITS[-1] == "no_release_support_expansion"


def test_bounded_read_script_imports_only_allowed_modules() -> None:
    tree = ast.parse(SCRIPT.read_text(), filename=str(SCRIPT))
    imported = {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    imported.update(
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    )
    forbidden = {
        "fastapi", "sqlalchemy", "psycopg", "asyncpg", "requests", "httpx", "docker",
        "subprocess", "guardian.routes.command_bus", "guardian.command_bus",
        "codex_runner", "scripts.guardian.validate_evidence_packet",
        "scripts.guardian.validate_evidence_packets",
        "scripts.guardian.validate_reducer_input_bundles",
        "scripts.guardian.reducer_dry_run",
    }
    assert not imported.intersection(forbidden)
    assert "scripts.guardian.validate_reducer_input_bundle" in imported


def test_local_tooling_bundle_returns_bounded_read_artifacts() -> None:
    bundle = ROOT / "docs/architecture/fixtures/guardian-evidence-reducer-input-bundle.local-tooling.v1.json"
    proc = _run(bundle)
    output = _output(proc)
    assert proc.returncode == 0, proc.stderr
    assert output["schema_version"] == "guardian_evidence_bounded_read_batch_result.v1"
    assert output["read_contract_version"] == "guardian_evidence_bounded_read_contract.v1"
    assert "input_bundle_validation_result" in output
    assert output["source_count"] == len(output["read_results"])
    assert output["read_results"]
    assert output["result"] == "pass_with_warnings"
    assert set(output["limits"]) >= EXPECTED_LIMITS
    for result in output["read_results"]:
        assert set(result) >= REQUIRED_RESULT_FIELDS
        assert result["schema_version"] == "guardian_evidence_bounded_read_result.v1"
        assert result["read_contract_version"] == "guardian_evidence_bounded_read_contract.v1"
        if result["read_status"] == "read":
            assert len(result["content_hash"]) == hashlib.sha256().digest_size * 2
            assert result["content_excerpt"]


def test_max_bytes_bounds_excerpt_and_emits_warning(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path, ["docs/architecture/README.md"])
    proc = _run(bundle, "--max-bytes", "64")
    output = _output(proc)
    result = output["read_results"][0]
    assert proc.returncode == 0, proc.stderr
    assert result["read_status"] == "read"
    assert len(result["content_excerpt"].encode("utf-8")) <= 64
    assert result["excerpt_truncated"] is True
    assert "content_truncated" in result["warnings"]
    assert output["warning_count"] >= 1


def test_blocked_and_error_reference_statuses(tmp_path: Path) -> None:
    cases = (
        ("missing", "docs/architecture/does-not-exist.md", "missing", "source_ref_missing"),
        ("network", "https://example.invalid/evidence.md", "blocked", "source_ref_network_url_blocked"),
        ("absolute", "/tmp/evidence.md", "blocked", "source_ref_outside_repo"),
        ("traversal", "../outside.md", "blocked", "source_ref_outside_repo"),
        ("env", "docs/architecture/.env", "blocked", "source_ref_secret_risk_blocked"),
        ("key", "docs/architecture/private-key.pem", "blocked", "source_ref_secret_risk_blocked"),
        ("unsupported", "docs/architecture/evidence.py", "unsupported", "source_ref_unsupported_type"),
        ("not-allowlisted", "tests/evidence_packets/test_guardian_evidence_packet_contracts.py", "skipped", "source_ref_not_allowlisted"),
    )
    for name, source_ref, status, diagnostic in cases:
        bundle = _bundle(tmp_path / name, [source_ref])
        proc = _run(bundle)
        output = _output(proc)
        result = output["read_results"][0]
        assert result["read_status"] == status
        assert diagnostic in result["errors"] or diagnostic in result["warnings"]
        assert proc.returncode == (0 if status == "skipped" else 1)


def test_invalid_bundle_stops_before_source_ref_read(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path, ["docs/architecture/README.md"], valid=False)
    proc = _run(bundle)
    output = _output(proc)
    assert proc.returncode == 1
    assert output["input_bundle_validation_result"]["result"] == "fail"
    assert output["read_results"] == []
    assert output["source_count"] == 0


def test_script_does_not_emit_packet_or_write_files(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path, ["docs/architecture/README.md"])
    before = sorted(path.name for path in tmp_path.iterdir())
    proc = _run(bundle)
    after = sorted(path.name for path in tmp_path.iterdir())
    output = _output(proc)
    assert proc.returncode == 0
    assert before == after
    serialized = json.dumps(output)
    assert '"packet"' not in serialized
    assert "GuardianEvidencePacket" not in serialized


def test_docs_and_existing_local_tools_remain_aligned() -> None:
    contract = CONTRACT.read_text()
    generator = (ROOT / "docs/architecture/guardian-evidence-packet-generator-contract.md").read_text()
    readme = (ROOT / "docs/architecture/README.md").read_text()
    current = (ROOT / "docs/architecture/00-current-state.md").read_text()
    assert "scripts/guardian/read_bounded_evidence.py" in contract
    assert "validates the bundle before reading source refs" in contract
    assert "bounded read artifacts" in contract
    assert "only through a separate generator implementation" in generator
    assert "scripts/guardian/read_bounded_evidence.py" in readme
    assert "local Guardian Evidence bounded-read tooling" in current

    for target in (
        "guardian-evidence-packets-validate",
        "guardian-evidence-reducer-dry-run",
        "guardian-evidence-reducer-input-bundles-validate",
        "guardian-evidence-reducer-input-bundle-dry-run",
    ):
        proc = subprocess.run(["make", target], cwd=ROOT, capture_output=True, text=True, check=False)
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
    assert json.loads(bundles.stdout)["matched_count"] >= 2
