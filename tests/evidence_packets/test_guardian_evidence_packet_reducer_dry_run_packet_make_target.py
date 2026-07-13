"""Tests for the local GuardianEvidencePacket inspection Make target."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MAKEFILE = ROOT / "Makefile"
TARGET = "guardian-evidence-packet-dry-run"
COMMAND = (
    "python3 scripts/guardian/reducer_dry_run.py --evidence-packet "
    "docs/architecture/fixtures/guardian-evidence-packet.generated-local-tooling.v1.json --json"
)


def _recipe() -> str:
    lines = MAKEFILE.read_text().splitlines()
    start = lines.index(f"{TARGET}:") + 1
    recipe: list[str] = []
    for line in lines[start:]:
        if line and not line.startswith(("\t", " ")):
            break
        recipe.append(line)
    return "\n".join(recipe)


def _make() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["make", TARGET], cwd=ROOT, capture_output=True, text=True, check=False
    )


def test_makefile_defines_exact_packet_dry_run_target() -> None:
    text = MAKEFILE.read_text()
    assert f"{TARGET}:" in text
    assert COMMAND in _recipe()
    assert TARGET in next(line for line in text.splitlines() if line.startswith(".PHONY:"))


def test_target_is_diagnostics_only_and_not_a_broad_prerequisite() -> None:
    recipe = _recipe().lower()
    for forbidden in (
        "generate_evidence_packet.py",
        "read_bounded_evidence.py",
        "validate_evidence_packets.py",
        "validate_reducer_input_bundles.py",
        "codex runner",
        "codexrun",
        "docker",
        "docker compose",
        "receipt",
        "ci",
        "workorder",
        "execution ledger",
    ):
        assert forbidden not in recipe

    broad_targets = {"default", "all", "test", "check", "ci", "release", "preflight"}
    for line in MAKEFILE.read_text().splitlines():
        if not line or line.startswith(("#", "\t", " ")) or ":" not in line:
            continue
        name, prerequisites = line.split(":", 1)
        if name.strip() in broad_targets:
            assert TARGET not in prerequisites.split()


def test_make_target_emits_packet_diagnostics_without_mutating_repo() -> None:
    tracked = (
        MAKEFILE,
        ROOT / "scripts/guardian/reducer_dry_run.py",
        ROOT / "docs/architecture/fixtures/guardian-evidence-packet.generated-local-tooling.v1.json",
    )
    before = {path: (path.stat().st_size, path.stat().st_mtime_ns) for path in tracked}
    proc = _make()
    after = {path: (path.stat().st_size, path.stat().st_mtime_ns) for path in tracked}
    assert proc.returncode == 0, proc.stderr
    assert before == after

    result = json.loads(proc.stdout[proc.stdout.index("{") :])
    assert result["packet_loaded"] is True
    assert result["packet_id"] == "guardian-evidence-packet.generated-local-tooling.v1"
    assert result["packet_validation_result"]
    for field in (
        "raw_evidence_ref_count",
        "claim_count",
        "uncertainty_count",
        "forbidden_interpretation_count",
    ):
        assert isinstance(result[field], int)
    assert all(value is False for value in result["authority_state"].values())
    assert result["diagnostics"]["lifecycle_steps_completed"] == [
        "receive_bounded_evidence_input_set",
        "classify_input_classes",
        "stop",
    ]
    assert "diagnostics only" in result["diagnostics"]["warnings"][0]
    assert not any(
        key in result
        for key in ("execution_authority", "receipt_trust", "workorder_mutation", "execution_ledger_write")
    )
