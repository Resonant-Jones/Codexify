import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MAKEFILE = ROOT / "Makefile"
TARGET = "guardian-evidence-bounded-read"
COMMAND = (
    "python3 scripts/guardian/read_bounded_evidence.py "
    "docs/architecture/fixtures/guardian-evidence-reducer-input-bundle.local-tooling.v1.json --json"
)


def _target_block() -> str:
    lines = MAKEFILE.read_text().splitlines()
    start = next(index for index, line in enumerate(lines) if line.startswith(f"{TARGET}:"))
    block: list[str] = []
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


def test_target_invokes_only_bounded_reader() -> None:
    block = _target_block().lower()
    assert COMMAND.lower() in block
    assert "Running Guardian Evidence bounded read...".lower() in block
    for forbidden in (
        "reducer_dry_run.py",
        "validate_evidence_packet.py",
        "validate_evidence_packets.py",
        "validate_reducer_input_bundles.py",
        "codex runner",
        "codexrun",
        "docker",
        "docker compose",
        "receipt",
        "ci",
    ):
        assert forbidden not in block


def test_target_is_not_a_broad_prerequisite() -> None:
    text = MAKEFILE.read_text()
    for name in ("default", "all", "test", "check", "ci", "release", "preflight"):
        lines = [line for line in text.splitlines() if line.startswith(f"{name}:")]
        assert all(TARGET not in line for line in lines)


def test_make_target_returns_bounded_read_json_without_mutation() -> None:
    tracked = (
        ROOT / "Makefile",
        ROOT / "scripts" / "guardian" / "read_bounded_evidence.py",
        ROOT / "docs" / "architecture" / "fixtures",
    )
    paths: list[Path] = []
    for root in tracked:
        paths.extend([root] if root.is_file() else root.rglob("*"))
    before = {
        str(path.relative_to(ROOT)): (path.stat().st_size, path.stat().st_mtime_ns)
        for path in paths
        if path.is_file()
    }
    proc = _make(TARGET)
    after = {
        str(path.relative_to(ROOT)): (path.stat().st_size, path.stat().st_mtime_ns)
        for path in paths
        if path.is_file()
    }
    assert proc.returncode == 0, proc.stderr
    assert "Running Guardian Evidence bounded read..." in proc.stdout
    output = json.loads(proc.stdout[proc.stdout.index("{"):])
    assert output["schema_version"] == "guardian_evidence_bounded_read_batch_result.v1"
    assert output["read_contract_version"] == "guardian_evidence_bounded_read_contract.v1"
    assert "input_bundle_validation_result" in output
    assert "read_results" in output
    assert "source_count" in output
    assert output["source_count"] == len(output["read_results"])
    assert "limits" in output
    assert "no_packet_generation" in output["limits"]
    assert "no_execution" in output["limits"]
    assert "no_evidence_ingestion" in output["limits"]
    assert "packet" not in output
    assert output["result"] in {"pass", "pass_with_warnings"}
    assert before == after


def test_existing_local_targets_and_validators_remain_green() -> None:
    for target in (
        "guardian-evidence-packets-validate",
        "guardian-evidence-reducer-dry-run",
        "guardian-evidence-reducer-input-bundles-validate",
        "guardian-evidence-reducer-input-bundle-dry-run",
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
    paths = [entry["path"] for entry in json.loads(bundles.stdout)["files"]]
    assert any("guardian-evidence-reducer-input-bundle-template" in path for path in paths)
    assert any("guardian-evidence-reducer-input-bundle.local-tooling" in path for path in paths)
