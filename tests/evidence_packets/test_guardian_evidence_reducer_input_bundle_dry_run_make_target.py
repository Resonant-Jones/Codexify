import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MAKEFILE = ROOT / "Makefile"
TARGET = "guardian-evidence-reducer-input-bundle-dry-run"
COMMAND = "python3 scripts/guardian/reducer_dry_run.py --json --input-bundle docs/architecture/fixtures/guardian-evidence-reducer-input-bundle.local-tooling.v1.json"


def _target_block() -> str:
    lines = MAKEFILE.read_text().splitlines()
    start = next(index for index, line in enumerate(lines) if line.startswith(f"{TARGET}:"))
    block = []
    for line in lines[start:]:
        if block and not line and not line.startswith(("\t", " ")):
            break
        block.append(line)
    return "\n".join(block)


def _make(target: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["make", target], cwd=ROOT, capture_output=True, text=True, check=False)


def test_makefile_defines_and_marks_target_phony() -> None:
    text = MAKEFILE.read_text()
    assert f"{TARGET}:" in text
    assert TARGET in next(line for line in text.splitlines() if line.startswith(".PHONY:"))


def test_target_invokes_only_the_existing_loader_path() -> None:
    block = _target_block().lower()
    assert COMMAND.lower() in block
    for forbidden in (
        "validate_evidence_packet.py", "validate_evidence_packets.py",
        "validate_reducer_input_bundles.py", "codex runner", "codexrun",
        "docker", "receipt", "ci",
    ):
        assert forbidden not in block


def test_target_is_not_a_broad_prerequisite() -> None:
    text = MAKEFILE.read_text()
    for name in ("default", "all", "test", "check", "ci", "release", "preflight"):
        lines = [line for line in text.splitlines() if line.startswith(f"{name}:")]
        assert all(TARGET not in line for line in lines)


def test_make_target_returns_diagnostics_only() -> None:
    proc = _make(TARGET)
    assert proc.returncode == 0, proc.stderr
    output = proc.stdout[proc.stdout.index("{"):]
    result = json.loads(output)
    assert result["schema_version"] == "guardian_evidence_reducer_input_bundle_dry_run_result.v1"
    assert "input_bundle_validation_result" in result
    assert result["reducer_result"] is not None
    assert result["packet"] is None
    assert result["validation_result"] is None
    assert all(value is False for value in result["authority_state"].values())
    assert result["reducer_result"]["diagnostics"]["lifecycle_steps_completed"] == [
        "receive_bounded_evidence_input_set", "classify_input_classes", "stop"
    ]
    assert "no_source_ref_reads" in result["limits"]


def test_existing_local_targets_and_validators_remain_green() -> None:
    for target in (
        "guardian-evidence-packets-validate",
        "guardian-evidence-reducer-dry-run",
        "guardian-evidence-reducer-input-bundles-validate",
    ):
        proc = _make(target)
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
    assert bundles.returncode == 0
    assert json.loads(packet.stdout)["matched_count"] == 2
    paths = [entry["path"] for entry in json.loads(bundles.stdout)["files"]]
    assert any("guardian-evidence-reducer-input-bundle-template" in path for path in paths)
    assert any("guardian-evidence-reducer-input-bundle.local-tooling" in path for path in paths)
