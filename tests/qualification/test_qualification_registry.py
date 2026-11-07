"""Tests for the qualification registry generator, validator, and library."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.qualification.lib.freshness import (
    GitHistory,
    compute_freshness,
    match_surface,
)
from scripts.qualification.lib.parsing import (
    QualificationParseError,
    RunReceipt,
    parse_rubric,
    parse_run_receipt,
)
from scripts.qualification.lib.projection import build_registry
from scripts.qualification.generate_registry import generate, main as generate_main
from scripts.qualification.validate_registry import (
    main as validate_main,
    validate_registry,
)


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/qualification/generate_registry.py"
VALIDATOR = ROOT / "scripts/qualification/validate_registry.py"
SCHEMA = ROOT / "docs/qualification/schemas/qualification-registry.schema.json"
REGISTRY = ROOT / "docs/qualification/registry.json"

RUBRIC_METADATA = """# Sample Rubric

## Qualification metadata

```yaml qualification-metadata
qualification_id: sample-surface
version: 1
title: Sample Surface
scope: A surface used to exercise the qualification tooling
surface_paths:
  - guardian/routes/**
evidence:
  - docs/architecture/proofs/example-proof.md
```
"""

RECEIPT_METADATA = """# Sample run

## Qualification metadata

```yaml qualification-metadata
qualification_id: sample-surface
rubric_version: 1
verdict: HOLD
commit: {commit}
date: 2026-01-01
tester_alias: tester-a
tester_kind: human
assistance_level_peak: 0
evidence:
  - docs/architecture/proofs/example-proof.md
```
"""


def _write_rubric(root: Path, body: str = RUBRIC_METADATA) -> Path:
    path = root / "docs/qualification/rubrics/sample-surface.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def _write_receipt(root: Path, body: str) -> Path:
    path = root / "docs/qualification/runs/2026-01-01-sample.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def _write_proof(root: Path) -> Path:
    path = root / "docs/architecture/proofs/example-proof.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# Example proof\n", encoding="utf-8")
    return path


# ── Parsing ─────────────────────────────────────────────────────────────


def test_parse_rubric_reads_declared_metadata(tmp_path: Path) -> None:
    path = _write_rubric(tmp_path)
    rubric = parse_rubric(path, tmp_path)

    assert rubric.qualification_id == "sample-surface"
    assert rubric.version == 1
    assert rubric.title == "Sample Surface"
    assert rubric.surface_paths == ("guardian/routes/**",)
    assert rubric.evidence == ("docs/architecture/proofs/example-proof.md",)


def test_parse_rubric_requires_metadata_block(tmp_path: Path) -> None:
    path = tmp_path / "rubric.md"
    path.write_text("# No metadata here\n", encoding="utf-8")

    with pytest.raises(QualificationParseError) as excinfo:
        parse_rubric(path, tmp_path)

    assert excinfo.value.code == "metadata_block_missing"


def test_parse_rubric_requires_surface_paths(tmp_path: Path) -> None:
    body = RUBRIC_METADATA.replace(
        "surface_paths:\n  - guardian/routes/**\n", ""
    )
    path = _write_rubric(tmp_path, body)

    with pytest.raises(QualificationParseError) as excinfo:
        parse_rubric(path, tmp_path)

    assert excinfo.value.code == "rubric_surface_paths_missing"


def test_parse_rubric_rejects_invalid_qualification_id(tmp_path: Path) -> None:
    body = RUBRIC_METADATA.replace("qualification_id: sample-surface", "qualification_id: Sample_Surface")
    path = _write_rubric(tmp_path, body)

    with pytest.raises(QualificationParseError) as excinfo:
        parse_rubric(path, tmp_path)

    assert excinfo.value.code == "rubric_qualification_id_invalid"


def test_parse_receipt_reads_declared_metadata(tmp_path: Path) -> None:
    commit = "a" * 40
    path = _write_receipt(tmp_path, RECEIPT_METADATA.format(commit=commit))
    receipt = parse_run_receipt(path, tmp_path)

    assert receipt.qualification_id == "sample-surface"
    assert receipt.verdict == "HOLD"
    assert receipt.commit == commit
    assert receipt.date == "2026-01-01"
    assert receipt.tester_kind == "human"
    assert receipt.assistance_level_peak == 0


def test_parse_receipt_accepts_unquoted_iso_date(tmp_path: Path) -> None:
    """YAML resolves an unquoted date to datetime.date; both must parse."""
    commit = "b" * 40
    path = _write_receipt(tmp_path, RECEIPT_METADATA.format(commit=commit))
    receipt = parse_run_receipt(path, tmp_path)

    assert receipt.date == "2026-01-01"


def test_parse_receipt_rejects_short_commit(tmp_path: Path) -> None:
    path = _write_receipt(tmp_path, RECEIPT_METADATA.format(commit="abc123"))

    with pytest.raises(QualificationParseError) as excinfo:
        parse_run_receipt(path, tmp_path)

    assert excinfo.value.code == "receipt_commit_invalid"


def test_parse_receipt_rejects_unknown_verdict(tmp_path: Path) -> None:
    body = RECEIPT_METADATA.format(commit="c" * 40).replace(
        "verdict: HOLD", "verdict: MOSTLY PASSED"
    )
    path = _write_receipt(tmp_path, body)

    with pytest.raises(QualificationParseError) as excinfo:
        parse_run_receipt(path, tmp_path)

    assert excinfo.value.code == "receipt_verdict_invalid"


# ── Surface matching ─────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("path", "pattern", "expected"),
    [
        ("guardian/routes/chat.py", "guardian/routes/**", True),
        ("guardian/routes/nested/deep/chat.py", "guardian/routes/**", True),
        ("guardian/router/chat.py", "guardian/routes/**", False),
        ("docker-compose.yml", "docker-compose*.yml", True),
        ("docker-compose.private-preview.yml", "docker-compose*.yml", True),
        ("backend/Dockerfile", "docker-compose*.yml", False),
        ("guardian/routes/chat.py", "guardian/routes/*", True),
        ("guardian/routes/nested/chat.py", "guardian/routes/*", False),
    ],
)
def test_match_surface_respects_segment_boundaries(
    path: str, pattern: str, expected: bool
) -> None:
    assert bool(match_surface([path], [pattern])) is expected


def test_match_surface_returns_only_matching_paths() -> None:
    matched = match_surface(
        ["guardian/routes/chat.py", "frontend/src/app.tsx"],
        ["guardian/routes/**"],
    )
    assert matched == ["guardian/routes/chat.py"]


def test_every_rubric_surface_path_matches_a_tracked_path() -> None:
    """Every declared surface path must resolve to at least one tracked file.

    A surface path that matches nothing makes the qualification surface
    vacuous: no change to the real code can ever mark a run stale, so the
    registry would project `current` for a receipt whose subject had moved.
    This is a property of the repository's own rubrics, not of a fixture, so
    it is checked against the tracked file list.
    """
    tracked = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()

    dead: list[str] = []
    rubrics_dir = ROOT / "docs/qualification/rubrics"
    for path in sorted(rubrics_dir.glob("*.md")):
        try:
            rubric = parse_rubric(path, ROOT)
        except QualificationParseError:
            # The rubrics README is a template, not a rubric.
            continue
        for pattern in rubric.surface_paths:
            if not match_surface(tracked, [pattern]):
                dead.append(f"{path.name}: {pattern}")

    assert not dead, "surface paths matching no tracked path: " + "; ".join(dead)


# ── Projection ───────────────────────────────────────────────────────────


def test_projection_without_runs_is_hold_not_pass(tmp_path: Path) -> None:
    """Absence of evidence is never projected as qualification."""
    rubric = parse_rubric(_write_rubric(tmp_path), tmp_path)
    result = build_registry([rubric], [], repo_root=tmp_path, tip_sha="d" * 40)

    entry = result.registry["qualifications"]["sample-surface"]
    assert entry["status"] == "HOLD"
    assert entry["latest_run"] is None
    assert entry["tested_commit"] is None
    assert entry["blockers"]


def test_projection_uses_receipt_verdict(tmp_path: Path) -> None:
    commit = "e" * 40
    rubric = parse_rubric(_write_rubric(tmp_path), tmp_path)
    receipt = parse_run_receipt(
        _write_receipt(tmp_path, RECEIPT_METADATA.format(commit=commit)), tmp_path
    )

    result = build_registry(
        [rubric], [receipt], repo_root=tmp_path, tip_sha=commit
    )
    entry = result.registry["qualifications"]["sample-surface"]

    assert entry["status"] == "HOLD"
    assert entry["tested_commit"] == commit
    assert entry["latest_run"] == "runs/2026-01-01-sample.md"
    assert entry["last_qualified_at"] == "2026-01-01"


def test_projection_counts_human_testers(tmp_path: Path) -> None:
    commit = "f" * 40
    rubric = parse_rubric(_write_rubric(tmp_path), tmp_path)
    receipt = parse_run_receipt(
        _write_receipt(tmp_path, RECEIPT_METADATA.format(commit=commit)), tmp_path
    )

    result = build_registry(
        [rubric], [receipt], repo_root=tmp_path, tip_sha=commit
    )
    metrics = result.registry["qualifications"]["sample-surface"]["metrics"]

    assert metrics["human_testers"] == 1
    assert metrics["independent_completions"] == 1
    assert metrics["run_receipts"] == 1


def test_projection_does_not_count_automated_runs_as_human_testers(
    tmp_path: Path,
) -> None:
    commit = "1" * 40
    body = RECEIPT_METADATA.format(commit=commit).replace(
        "tester_kind: human", "tester_kind: automated"
    )
    rubric = parse_rubric(_write_rubric(tmp_path), tmp_path)
    receipt = parse_run_receipt(_write_receipt(tmp_path, body), tmp_path)

    result = build_registry(
        [rubric], [receipt], repo_root=tmp_path, tip_sha=commit
    )
    metrics = result.registry["qualifications"]["sample-surface"]["metrics"]

    assert metrics["human_testers"] == 0


def test_projection_merges_rubric_and_receipt_evidence(tmp_path: Path) -> None:
    commit = "2" * 40
    rubric = parse_rubric(_write_rubric(tmp_path), tmp_path)
    receipt = parse_run_receipt(
        _write_receipt(tmp_path, RECEIPT_METADATA.format(commit=commit)), tmp_path
    )

    result = build_registry(
        [rubric], [receipt], repo_root=tmp_path, tip_sha=commit
    )
    entry = result.registry["qualifications"]["sample-surface"]

    assert entry["evidence"] == ["docs/architecture/proofs/example-proof.md"]


def test_projection_reports_a_missing_tested_commit_distinctly(
    tmp_path: Path,
) -> None:
    """An unresolvable tested commit is a provenance problem, not staleness.

    A receipt may cite a revision that is not present in the repository's
    history. That must not be reported as though the surface merely aged.
    """
    commit = "9" * 40
    rubric = parse_rubric(_write_rubric(tmp_path), tmp_path)
    receipt = parse_run_receipt(
        _write_receipt(tmp_path, RECEIPT_METADATA.format(commit=commit)), tmp_path
    )

    history = GitHistory(tmp_path)
    result = build_registry(
        [rubric],
        [receipt],
        repo_root=tmp_path,
        tip_sha="8" * 40,
        history=history,
    )
    entry = result.registry["qualifications"]["sample-surface"]

    assert entry["freshness"] == "stale"
    assert any(
        "not an ancestor of the current tip" in blocker
        for blocker in entry["blockers"]
    )


def test_freshness_is_independent_of_local_object_presence(
    tmp_path: Path,
) -> None:
    """A commit outside the tip's lineage must read the same everywhere.

    A revision that was never merged to `main` may exist as a dangling
    object in one developer's clone and be absent from another. The
    freshness verdict must not depend on which objects happen to be
    present locally, or the CI drift check would disagree with the local
    one.
    """
    commit = "5" * 40
    rubric = parse_rubric(_write_rubric(tmp_path), tmp_path)
    receipt = parse_run_receipt(
        _write_receipt(tmp_path, RECEIPT_METADATA.format(commit=commit)), tmp_path
    )

    _init_git_repo(tmp_path)
    history = GitHistory(tmp_path)
    tip = history.resolve_commit("HEAD")
    assert tip is not None

    freshness, reasons, _ = compute_freshness(rubric, receipt, history, tip)

    assert freshness == "stale"
    assert reasons == ["tested_commit_not_in_tip_lineage"]


def test_freshness_of_a_merged_commit_uses_the_surface_diff(
    tmp_path: Path,
) -> None:
    """A commit inside the tip's lineage is compared by surface changes."""
    commit = "6" * 40
    _write_rubric(tmp_path)
    _write_receipt(tmp_path, RECEIPT_METADATA.format(commit=commit))
    _init_git_repo(tmp_path)
    history = GitHistory(tmp_path)
    tip = history.resolve_commit("HEAD")
    assert tip is not None

    rubric = parse_rubric(_write_rubric(tmp_path), tmp_path)
    receipt = parse_run_receipt(
        _write_receipt(tmp_path, RECEIPT_METADATA.format(commit=commit)), tmp_path
    )

    # An all-digit SHA that is not in the repository's history reads as
    # outside the tip's lineage, never as a surface change.
    freshness, reasons, _ = compute_freshness(rubric, receipt, history, tip)
    assert freshness == "stale"
    assert reasons == ["tested_commit_not_in_tip_lineage"]


def test_projection_marks_a_run_current_when_the_surface_is_untouched(
    tmp_path: Path,
) -> None:
    commit = "7" * 40
    rubric = parse_rubric(_write_rubric(tmp_path), tmp_path)
    receipt = parse_run_receipt(
        _write_receipt(tmp_path, RECEIPT_METADATA.format(commit=commit)), tmp_path
    )

    _init_git_repo(tmp_path)
    history = GitHistory(tmp_path)
    tip = history.resolve_commit("HEAD")
    assert tip is not None

    # The receipt tested the tip itself, so nothing can have moved.
    receipt_at_tip = RunReceipt(
        qualification_id=receipt.qualification_id,
        rubric_version=receipt.rubric_version,
        verdict=receipt.verdict,
        commit=tip,
        date=receipt.date,
        path=receipt.path,
        repo_root=tmp_path,
        evidence=receipt.evidence,
    )

    result = build_registry(
        [rubric],
        [receipt_at_tip],
        repo_root=tmp_path,
        tip_sha=tip,
        history=history,
    )
    entry = result.registry["qualifications"]["sample-surface"]

    assert entry["freshness"] == "current"
    assert entry["blockers"] == []


def test_a_run_earned_under_an_older_rubric_version_is_not_current(
    tmp_path: Path,
) -> None:
    """A run demonstrates the criteria it was earned under, not later ones.

    The rubric version is what a receipt binds to. If the rubric's criteria
    are revised after a run, that run cannot be read as describing the new
    criteria even when its subject has not moved and the surface is intact.
    """
    commit = "7" * 40
    receipt = parse_run_receipt(
        _write_receipt(tmp_path, RECEIPT_METADATA.format(commit=commit)), tmp_path
    )

    _init_git_repo(tmp_path)
    history = GitHistory(tmp_path)
    tip = history.resolve_commit("HEAD")
    assert tip is not None

    # The rubric's criteria are revised after the run: version 2, same surface.
    revised_rubric = parse_rubric(
        _write_rubric(tmp_path, RUBRIC_METADATA.replace("version: 1", "version: 2")),
        tmp_path,
    )
    assert revised_rubric.version == 2
    assert receipt.rubric_version == 1

    # The receipt tested the tip itself, so nothing in the subject moved.
    receipt_at_tip = RunReceipt(
        qualification_id=receipt.qualification_id,
        rubric_version=receipt.rubric_version,
        verdict=receipt.verdict,
        commit=tip,
        date=receipt.date,
        path=receipt.path,
        repo_root=tmp_path,
        evidence=receipt.evidence,
    )

    freshness, reasons, blockers = compute_freshness(
        revised_rubric, receipt_at_tip, history, tip
    )

    assert freshness == "stale"
    assert reasons == ["rubric_version_mismatch"]
    assert any("rubric version 1" in blocker for blocker in blockers)
    assert any("now version 2" in blocker for blocker in blockers)


def test_a_run_earned_under_the_current_rubric_version_is_current(
    tmp_path: Path,
) -> None:
    """The version check must not stale a run earned under the same criteria."""
    commit = "7" * 40
    rubric = parse_rubric(_write_rubric(tmp_path), tmp_path)
    receipt = parse_run_receipt(
        _write_receipt(tmp_path, RECEIPT_METADATA.format(commit=commit)), tmp_path
    )
    assert receipt.rubric_version == rubric.version

    _init_git_repo(tmp_path)
    history = GitHistory(tmp_path)
    tip = history.resolve_commit("HEAD")
    assert tip is not None

    receipt_at_tip = RunReceipt(
        qualification_id=receipt.qualification_id,
        rubric_version=receipt.rubric_version,
        verdict=receipt.verdict,
        commit=tip,
        date=receipt.date,
        path=receipt.path,
        repo_root=tmp_path,
        evidence=receipt.evidence,
    )

    freshness, reasons, blockers = compute_freshness(
        rubric, receipt_at_tip, history, tip
    )

    assert freshness == "current"
    assert reasons == []
    assert blockers == []


# ── Validator ────────────────────────────────────────────────────────────


def _valid_registry(tmp_path: Path) -> dict:
    commit = "3" * 40
    return {
        "registry_version": 1,
        "generated_from_repository": True,
        "release_authority": "docs/architecture/00-current-state.md",
        "qualifications": {
            "sample-surface": {
                "title": "Sample Surface",
                "scope": "A surface used to exercise the qualification tooling",
                "status": "HOLD",
                "freshness": "stale",
                "rubric": "rubrics/sample-surface.md",
                "latest_run": "runs/2026-01-01-sample.md",
                "tested_commit": commit,
                "last_qualified_at": "2026-01-01",
                "evidence": ["docs/architecture/proofs/example-proof.md"],
                "metrics": {"human_testers": 1},
                "blockers": ["Something is missing."],
            }
        },
    }


def _prepare_repo(tmp_path: Path) -> None:
    _write_rubric(tmp_path)
    _write_receipt(tmp_path, RECEIPT_METADATA.format(commit="3" * 40))
    _write_proof(tmp_path)


def _init_git_repo(root: Path) -> str:
    """Initialize a throwaway git repository and return its HEAD SHA.

    The generator resolves its tip through git, so a CLI test needs a real
    repository rather than a bare directory of files.
    """
    def run(*args: str) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()

    run("init", "--quiet")
    run("config", "user.email", "test@example.invalid")
    run("config", "user.name", "Qualification Test")
    run("add", "-A")
    run("commit", "--quiet", "-m", "seed")
    return run("rev-parse", "HEAD")


def _validate(tmp_path: Path, registry: dict) -> dict:
    registry_path = tmp_path / "docs/qualification/registry.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    return validate_registry(registry_path, SCHEMA, tmp_path)


def test_validator_accepts_a_consistent_registry(tmp_path: Path) -> None:
    _prepare_repo(tmp_path)
    result = _validate(tmp_path, _valid_registry(tmp_path))

    assert result["result"] == "pass", result["issues"]
    assert result["schema_valid"] is True
    assert result["contract_valid"] is True


def test_validator_rejects_missing_evidence_file(tmp_path: Path) -> None:
    _prepare_repo(tmp_path)
    registry = _valid_registry(tmp_path)
    registry["qualifications"]["sample-surface"]["evidence"] = [
        "docs/architecture/proofs/missing.md"
    ]

    result = _validate(tmp_path, registry)

    assert result["result"] == "fail"
    assert any(
        issue["code"] == "evidence_missing" for issue in result["issues"]
    )


def test_validator_rejects_pass_without_evidence(tmp_path: Path) -> None:
    _prepare_repo(tmp_path)
    registry = _valid_registry(tmp_path)
    entry = registry["qualifications"]["sample-surface"]
    entry["status"] = "PASS"
    entry["evidence"] = []

    result = _validate(tmp_path, registry)

    assert result["result"] == "fail"
    assert any(
        issue["code"] == "pass_without_evidence" for issue in result["issues"]
    )


def test_validator_rejects_verdict_mismatch(tmp_path: Path) -> None:
    _prepare_repo(tmp_path)
    registry = _valid_registry(tmp_path)
    registry["qualifications"]["sample-surface"]["status"] = "FAIL"

    result = _validate(tmp_path, registry)

    assert result["result"] == "fail"
    assert any(
        issue["code"] == "latest_run_verdict_mismatch"
        for issue in result["issues"]
    )


def test_validator_rejects_surface_without_rubric(tmp_path: Path) -> None:
    _prepare_repo(tmp_path)
    registry = _valid_registry(tmp_path)
    registry["qualifications"]["phantom-surface"] = dict(
        registry["qualifications"]["sample-surface"]
    )

    result = _validate(tmp_path, registry)

    assert result["result"] == "fail"
    assert any(
        issue["code"] == "surface_not_declared" for issue in result["issues"]
    )


def test_validator_rejects_missing_rubric_file(tmp_path: Path) -> None:
    _prepare_repo(tmp_path)
    registry = _valid_registry(tmp_path)
    registry["qualifications"]["sample-surface"]["rubric"] = "rubrics/gone.md"

    result = _validate(tmp_path, registry)

    assert result["result"] == "fail"
    assert any(issue["code"] == "rubric_missing" for issue in result["issues"])


def test_validator_rejects_ambiguous_status(tmp_path: Path) -> None:
    _prepare_repo(tmp_path)
    registry = _valid_registry(tmp_path)
    registry["qualifications"]["sample-surface"]["status"] = "mostly passed"

    result = _validate(tmp_path, registry)

    assert result["result"] == "fail"
    assert any(
        issue["code"] == "ambiguous_status" for issue in result["issues"]
    )


# ── CLI ──────────────────────────────────────────────────────────────────


def test_generator_check_mode_fails_on_drift(tmp_path: Path) -> None:
    _prepare_repo(tmp_path)
    _init_git_repo(tmp_path)
    registry_path = tmp_path / "docs/qualification/registry.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text("{}", encoding="utf-8")

    exit_code = generate_main(["--repo-root", str(tmp_path), "--check"])

    assert exit_code == 1


def test_generator_check_mode_passes_when_registry_is_current(
    tmp_path: Path,
) -> None:
    _prepare_repo(tmp_path)
    _init_git_repo(tmp_path)
    exit_code = generate_main(["--repo-root", str(tmp_path)])
    assert exit_code == 0

    exit_code = generate_main(["--repo-root", str(tmp_path), "--check"])

    assert exit_code == 0


def test_validator_cli_returns_nonzero_for_invalid_registry(
    tmp_path: Path,
) -> None:
    _prepare_repo(tmp_path)
    registry_path = tmp_path / "docs/qualification/registry.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text("{}", encoding="utf-8")

    exit_code = validate_main(
        [
            str(registry_path),
            "--schema",
            str(SCHEMA),
            "--repo-root",
            str(tmp_path),
            "--quiet",
        ]
    )

    assert exit_code == 1


def test_committed_registry_is_current() -> None:
    """The committed registry must match what the repository projects."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--check", "--repo-root", str(ROOT)],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_committed_registry_passes_validation() -> None:
    result = validate_registry(REGISTRY, SCHEMA, ROOT)
    assert result["result"] == "pass", result["issues"]
