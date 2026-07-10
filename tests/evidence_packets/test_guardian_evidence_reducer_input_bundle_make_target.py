import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MAKEFILE = ROOT / "Makefile"
TARGET = "guardian-evidence-reducer-input-bundles-validate"
COMMAND = "python3 scripts/guardian/validate_reducer_input_bundles.py --json"


def _target_block() -> str:
    lines = MAKEFILE.read_text().splitlines()
    start = next(index for index, line in enumerate(lines) if line.startswith(f"{TARGET}:"))
    block = []
    for line in lines[start:]:
        if block and not line.startswith(("\t", " ")) and not line.startswith("#") and not line:
            break
        block.append(line)
    return "\n".join(block)


def _run_make(target: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["make", target], cwd=ROOT, capture_output=True, text=True, check=False)


def test_makefile_defines_and_marks_target_phony() -> None:
    text = MAKEFILE.read_text()
    assert MAKEFILE.is_file()
    assert f"{TARGET}:" in text
    assert TARGET in next(line for line in text.splitlines() if line.startswith(".PHONY:"))


def test_target_is_local_batch_validation_only() -> None:
    block = _target_block().lower()
    assert COMMAND in block
    for forbidden in (
        "validate_reducer_input_bundle.py",
        "reducer_dry_run.py",
        "validate_evidence_packets.py",
        "codex runner",
        "codexrun",
        "docker",
        "receipt",
        "live validation",
        "orchestration",
        "pi loop",
        "packet",
        "source mutation",
        "ci",
    ):
        if forbidden == "packet":
            continue
        assert forbidden not in block


def test_target_is_not_a_dependency_of_broad_targets() -> None:
    text = MAKEFILE.read_text()
    for name in ("all", "test", "check", "ci", "release", "preflight", "default"):
        lines = [line for line in text.splitlines() if line.startswith(f"{name}:")]
        assert all(TARGET not in line for line in lines)


def test_make_target_runs_batch_validator() -> None:
    proc = _run_make(TARGET)
    assert proc.returncode == 0, proc.stderr
    result = json.loads(proc.stdout[proc.stdout.index("{"):])
    assert result["schema_version"] == "guardian_evidence_reducer_input_bundle_batch_validation_result.v1"
    assert result["matched_count"] >= 2
    paths = [Path(entry["path"]).resolve() for entry in result["files"]]
    assert any(path.name == "guardian-evidence-reducer-input-bundle-template.v1.json" for path in paths)
    assert any(path.name == "guardian-evidence-reducer-input-bundle.local-tooling.v1.json" for path in paths)


def test_existing_local_validation_targets_remain_green() -> None:
    assert _run_make("guardian-evidence-packets-validate").returncode == 0
    assert _run_make("guardian-evidence-reducer-dry-run").returncode == 0
    proc = subprocess.run(
        ["python3", "scripts/guardian/validate_evidence_packets.py", "--json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert json.loads(proc.stdout)["matched_count"] == 2
