import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/guardian/generate_evidence_packet.py"
FIXTURE = "docs/architecture/fixtures/guardian-evidence-bounded-read.local-tooling.v1.json"


def _generator_stdout() -> dict:
    proc = subprocess.run(
        ["python3", str(SCRIPT), FIXTURE, "--json"], cwd=ROOT, capture_output=True, text=True, check=False
    )
    assert proc.returncode == 0
    return json.loads(proc.stdout)


def test_makefile_contains_target() -> None:
    text = (ROOT / "Makefile").read_text()
    assert "guardian-evidence-packet-generate" in text


def test_target_is_phony() -> None:
    text = (ROOT / "Makefile").read_text()
    lines = [l.strip() for l in text.splitlines()]
    phony = [l for l in lines if l.startswith(".PHONY:")]
    assert any("guardian-evidence-packet-generate" in l for l in phony)


def test_target_invokes_correct_command() -> None:
    text = (ROOT / "Makefile").read_text()
    assert "python3 scripts/guardian/generate_evidence_packet.py" in text
    assert FIXTURE in text
    assert "--json" in text


def test_target_does_not_invoke_forbidden_tools() -> None:
    text = (ROOT / "Makefile").read_text()
    for forbidden in (
        "read_bounded_evidence.py", "reducer_dry_run.py",
        "validate_reducer_input_bundle.py", "validate_reducer_input_bundles.py",
        "validate_evidence_packets.py",
        "codexrun", "docker", "docker compose",
        "receipt", "CI",
    ):
        section = text.split("guardian-evidence-packet-generate")[1]
        section = section.split("\n\n")[0]
        assert forbidden not in section, f"'{forbidden}' found in target body"


def test_target_not_dependency_of_default_all_test_check_ci_release_preflight() -> None:
    text = (ROOT / "Makefile").read_text()
    for dep in ("default", "all", "test", "check", "ci", "release", "preflight"):
        marker = f"\n{dep}:"
        if marker in text:
            dep_body = text.split(marker)[1].split("\n")[0]
            assert "guardian-evidence-packet-generate" not in dep_body, f"target is a dependency of {dep}"


def test_make_target_exits_zero() -> None:
    proc = subprocess.run(["make", "guardian-evidence-packet-generate"], cwd=ROOT, capture_output=True, text=True)
    assert proc.returncode == 0


def test_output_contains_required_fields() -> None:
    result = _generator_stdout()
    assert result["schema_version"] == "guardian_evidence_packet_generator_result.v1"
    assert result["generator_contract_version"] == "guardian_evidence_packet_generator_contract.v1"
    assert "bounded_read_result_ref" in result
    assert "packet" in result
    assert "packet_validation_result" in result
    assert "authority_state" in result
    assert "diagnostics" in result
    assert "limits" in result


def test_limits_include_stdout_only_and_no_fixture_write() -> None:
    result = _generator_stdout()
    assert "stdout_only" in result["limits"]
    assert "no_fixture_write" in result["limits"]
    assert "no_execution" in result["limits"]
    assert "no_evidence_ingestion" in result["limits"]


def test_result_or_validation_is_pass_or_pass_with_warnings() -> None:
    result = _generator_stdout()
    assert result["packet_validation_result"]["result"] in {"pass", "pass_with_warnings"}


def test_supported_claims_have_non_empty_evidence_refs() -> None:
    result = _generator_stdout()
    for claim in result["packet"]["claim_ledger"]:
        if claim["status"] == "supported":
            assert len(claim["evidence_refs"]) > 0


def test_deterministic_output() -> None:
    first = _generator_stdout()
    second = _generator_stdout()
    assert first == second


def test_existing_make_targets_exit_zero() -> None:
    for target in (
        "guardian-evidence-bounded-read",
        "guardian-evidence-packets-validate",
        "guardian-evidence-reducer-dry-run",
        "guardian-evidence-reducer-input-bundles-validate",
        "guardian-evidence-reducer-input-bundle-dry-run",
    ):
        proc = subprocess.run(["make", target], cwd=ROOT, capture_output=True, text=True)
        assert proc.returncode == 0, f"{target} exited {proc.returncode}"


def test_batch_validator_discovers_two_packet_fixtures() -> None:
    proc = subprocess.run(
        ["python3", "scripts/guardian/validate_evidence_packets.py", "--json"],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    assert proc.returncode == 0
    result = json.loads(proc.stdout)
    assert result["matched_count"] == 2


def test_input_bundle_validator_discovers_template_and_fixture() -> None:
    proc = subprocess.run(
        ["python3", "scripts/guardian/validate_reducer_input_bundles.py", "--json"],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    assert proc.returncode == 0
    result = json.loads(proc.stdout)
    assert result["matched_count"] == 2
