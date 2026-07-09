import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MAKEFILE = ROOT / "Makefile"
TARGET = "guardian-evidence-reducer-dry-run"
COMMAND = "python3 scripts/guardian/reducer_dry_run.py --json"


def _make() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["make", TARGET], cwd=ROOT, capture_output=True, text=True, check=False
    )


def _recipe() -> str:
    text = MAKEFILE.read_text()
    start = text.index(f"{TARGET}:")
    end = text.find("\n\n", start)
    return text[start:] if end == -1 else text[start:end]


def test_makefile_defines_local_reducer_dry_run_target() -> None:
    assert MAKEFILE.is_file()
    recipe = _recipe()
    assert f"{TARGET}:" in recipe
    assert COMMAND in recipe


def test_target_has_no_runtime_or_write_side_effects() -> None:
    recipe = _recipe().lower()
    forbidden = (
        "docker", "docker compose", "codexrun", "python -m codex_runner",
        "command_bus", "receipt", "output", "orchestrate", "validate_evidence",
    )
    assert not any(token in recipe for token in forbidden)


def test_target_is_not_a_broad_prerequisite() -> None:
    text = MAKEFILE.read_text()
    for name in ("all", "test", "lint", "docs", "validate", "preflight", "release", "ci"):
        lines = [line for line in text.splitlines() if line.startswith(f"{name}:")]
        if lines:
            line = lines[0]
            assert TARGET not in line


def test_target_returns_diagnostics_only() -> None:
    proc = _make()
    assert proc.returncode == 0, proc.stderr
    result = json.loads(proc.stdout[proc.stdout.index("{"):])
    assert result["schema_version"] == "guardian_evidence_packet_reducer_dry_run_result.v1"
    assert result["packet"] is None
    assert result["validation_result"] is None
    assert all(value is False for value in result["authority_state"].values())
    assert result["diagnostics"]["lifecycle_steps_completed"] == [
        "receive_bounded_evidence_input_set", "classify_input_classes", "stop"
    ]


def test_target_does_not_write_files() -> None:
    paths = (MAKEFILE, ROOT / "scripts/guardian/reducer_dry_run.py")
    before = {path: (path.stat().st_size, path.stat().st_mtime_ns) for path in paths}
    proc = _make()
    after = {path: (path.stat().st_size, path.stat().st_mtime_ns) for path in paths}
    assert proc.returncode == 0, proc.stderr
    assert before == after
