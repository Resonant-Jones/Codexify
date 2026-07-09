"""Tests for the local GuardianEvidencePacket fixture Makefile target."""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAKEFILE = ROOT / "Makefile"
TARGET = "guardian-evidence-packets-validate"
COMMAND = "python3 scripts/guardian/validate_evidence_packets.py --json"


def _target_recipe() -> str:
    lines = MAKEFILE.read_text().splitlines()
    start = lines.index(f"{TARGET}:") + 1
    recipe: list[str] = []
    for line in lines[start:]:
        if line and not line.startswith(("\t", " ")):
            break
        recipe.append(line)
    return "\n".join(recipe)


def _target_prerequisites() -> str:
    lines = MAKEFILE.read_text().splitlines()
    target_line = next(line for line in lines if line.startswith(f"{TARGET}:"))
    return target_line.split(":", 1)[1].strip()


def _repo_snapshot() -> dict[str, tuple[int, int]]:
    roots = (
        ROOT / "Makefile",
        ROOT / "scripts" / "guardian",
        ROOT / "docs" / "architecture" / "fixtures",
    )
    paths: list[Path] = []
    for root in roots:
        paths.extend([root] if root.is_file() else root.rglob("*"))
    return {
        str(path.relative_to(ROOT)): (path.stat().st_size, path.stat().st_mtime_ns)
        for path in paths
        if path.is_file()
    }


def test_makefile_exists() -> None:
    assert MAKEFILE.exists()


def test_makefile_defines_guardian_evidence_packet_target() -> None:
    assert f"{TARGET}:" in MAKEFILE.read_text()


def test_target_runs_batch_validator_json_command() -> None:
    assert COMMAND in _target_recipe()


def test_target_has_no_runtime_or_write_commands() -> None:
    recipe = _target_recipe().lower()
    forbidden = (
        "docker",
        "docker compose",
        "codexrun",
        "python -m codex_runner",
        "command_bus",
        "--write",
        "--write-receipt",
        "--receipt",
        "--output",
        "--apply",
        "--mutate",
        "orchestrate",
        "orchestration",
    )
    for token in forbidden:
        assert token not in recipe, f"Make target must not include {token!r}"


def test_target_is_not_a_prerequisite_of_broad_gates() -> None:
    broad_targets = {"all", "test", "lint", "docs", "validate", "preflight", "release", "ci"}
    lines = MAKEFILE.read_text().splitlines()
    for line in lines:
        if not line or line.startswith(("#", "\t", " ")) or ":" not in line:
            continue
        name, prerequisites = line.split(":", 1)
        names = {part.strip() for part in name.split()}
        if names & broad_targets:
            assert TARGET not in prerequisites.split()


def test_make_target_passes_current_fixture_set_without_writing_files() -> None:
    before = _repo_snapshot()
    proc = subprocess.run(
        ["make", TARGET], cwd=ROOT, capture_output=True, text=True, check=False
    )
    after = _repo_snapshot()
    assert proc.returncode == 0, proc.stderr
    assert "guardian_evidence_packet_batch_validation_result.v1" in proc.stdout
    assert '"result": "pass' in proc.stdout
    assert before == after
