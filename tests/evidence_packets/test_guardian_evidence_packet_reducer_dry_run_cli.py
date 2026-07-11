"""Tests for the local reducer dry-run CLI wrapper."""

from __future__ import annotations

import json
import ast
import subprocess
import sys
from pathlib import Path

import pytest

from guardian.evidence_packets.contracts import REQUIRED_AUTHORITY_LOCKS
from guardian.evidence_packets.reducer import DRY_RUN_WARNING
from guardian.evidence_packets.reducer_contracts import reducer_limits

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "scripts" / "guardian" / "reducer_dry_run.py"


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_exists_and_has_only_allowed_imports() -> None:
    assert CLI.exists()
    tree = ast.parse(CLI.read_text())
    allowed = {
        "guardian.evidence_packets.contracts",
        "guardian.evidence_packets.reducer_contracts",
        "guardian.evidence_packets.reducer",
        "scripts.guardian.validate_evidence_packet",
        "scripts.guardian.validate_reducer_input_bundle",
    }
    forbidden = (
        "fastapi", "database", "command_bus", "codex_runner", "validate_reducer_input_bundles",
        "subprocess", "requests", "httpx", "docker",
    )
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    for name in imports:
        assert not any(fragment in name.lower() for fragment in forbidden)
        assert not name.startswith(("guardian.", "scripts.")) or name in allowed


def test_cli_json_defaults_to_diagnostics_only() -> None:
    proc = _run("--json")
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert data["schema_version"] == "guardian_evidence_packet_reducer_dry_run_result.v1"
    assert data["bundle_id"] == "reducer_dry_run"
    assert data["review_depth"] == "light"
    assert data["input_count"] == 0
    assert data["packet"] is None
    assert data["validation_result"] is None
    assert data["diagnostics"]["lifecycle_steps_completed"] == [
        "receive_bounded_evidence_input_set", "classify_input_classes", "stop"
    ]
    assert DRY_RUN_WARNING in data["diagnostics"]["warnings"]
    assert set(data["authority_state"]) == set(REQUIRED_AUTHORITY_LOCKS)
    assert all(value is False for value in data["authority_state"].values())
    assert all(limit in data["limits"] for limit in reducer_limits())


def test_cli_accepts_bundle_depth_and_input_without_reading_source() -> None:
    proc = _run(
        "--json", "--bundle-id", "operator-check", "--review-depth", "high",
        "--input", "readme:static_docs:docs/architecture/README.md",
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert data["bundle_id"] == "operator-check"
    assert data["review_depth"] == "high"
    assert data["input_count"] == 1
    assert data["packet"] is None
    assert data["validation_result"] is None


@pytest.mark.parametrize("args", [
    ("--review-depth", "extreme"),
    ("--input", "malformed"),
    ("--input", "id:not_allowed:source"),
])
def test_cli_rejects_invalid_arguments(args: tuple[str, ...]) -> None:
    proc = _run(*args)
    assert proc.returncode == 2
    assert proc.stderr


def test_cli_does_not_write_files_or_call_validator_scripts() -> None:
    before = {str(path.relative_to(ROOT)) for path in ROOT.glob("scripts/guardian/reducer_dry_run*")}
    proc = _run("--json", "--input", "missing:static_docs:does-not-exist.md")
    after = {str(path.relative_to(ROOT)) for path in ROOT.glob("scripts/guardian/reducer_dry_run*")}
    assert proc.returncode == 0
    assert before == after
    source = CLI.read_text()
    # The only allowed validate_evidence reference is the static packet validator.
    assert "from scripts.guardian.validate_evidence_packet" in source
    # No other validator scripts should be referenced.
    for forbidden_pattern in ("validate_reducer_input_bundles",):
        assert forbidden_pattern not in source
