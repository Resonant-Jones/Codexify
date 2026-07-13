"""Focused tests for the bounded canonical evidence identity collector."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.audit.collect_canonical_evidence_identity import (
    CollectorError,
    collect_identity,
)


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/audit/collect_canonical_evidence_identity.py"


def run_git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], check=True, text=True, capture_output=True)
    return result.stdout.strip()


def make_repo(tmp_path: Path, *, branch: str = "main") -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
    subprocess.run(["git", "init", "-b", branch, str(repo)], check=True, capture_output=True)
    run_git(repo, "config", "user.email", "test@example.invalid")
    run_git(repo, "config", "user.name", "Test User")
    (repo / "tracked.txt").write_text("identity\n", encoding="utf-8")
    run_git(repo, "add", "tracked.txt")
    run_git(repo, "commit", "-m", "fixture")
    run_git(repo, "remote", "add", "origin", str(remote))
    run_git(repo, "push", "-u", "origin", branch)
    return repo, remote


def collect(repo: Path, **kwargs: object) -> dict:
    return collect_identity(repo, hostname="fixture-host", **kwargs)


def test_clean_main_matching_upstream_is_deterministic_and_candidate(tmp_path: Path) -> None:
    repo, _ = make_repo(tmp_path)
    first = collect(repo, machine_id="local-test")
    second = collect(repo, machine_id="local-test")
    assert first == second
    assert first["observation_complete"] is True
    assert first["eligibility"]["repository_identity_complete"] is True
    assert first["eligibility"]["canonical_repository_candidate"] is True
    assert first["eligibility"]["canonical_machine_candidate"] is False
    assert "canonical_machine_authority_not_asserted" in first["eligibility"]["reason_codes"]
    assert str(repo) not in json.dumps(first)


@pytest.mark.parametrize(
    ("case", "expected"),
    [
        ("dirty", "dirty_worktree"),
        ("detached", "detached_head"),
        ("wrong_branch", "wrong_branch"),
        ("missing_upstream", "missing_upstream"),
        ("unresolved_upstream", "unresolved_upstream"),
        ("mismatch", "commit_upstream_mismatch"),
    ],
)
def test_ineligible_repository_states_are_visible(tmp_path: Path, case: str, expected: str) -> None:
    repo, remote = make_repo(tmp_path)
    if case == "dirty":
        (repo / "tracked.txt").write_text("changed\n", encoding="utf-8")
    elif case == "detached":
        run_git(repo, "checkout", "--detach", "HEAD")
    elif case == "wrong_branch":
        run_git(repo, "checkout", "-b", "feature")
    elif case == "missing_upstream":
        run_git(repo, "branch", "--unset-upstream")
    elif case == "unresolved_upstream":
        run_git(repo, "config", "branch.main.merge", "refs/heads/missing")
    elif case == "mismatch":
        (repo / "tracked.txt").write_text("new commit\n", encoding="utf-8")
        run_git(repo, "commit", "-am", "local divergence")
    result = collect(repo)
    assert expected in result["eligibility"]["reason_codes"]
    assert result["eligibility"]["canonical_repository_candidate"] is False


def test_explicit_canonical_machine_inputs_are_required(tmp_path: Path) -> None:
    repo, _ = make_repo(tmp_path)
    provisional = collect(repo, machine_id="vaultnode", machine_role="provisional_development_host")
    assert provisional["eligibility"]["canonical_machine_candidate"] is False
    unasserted = collect(repo, machine_id="vaultnode", machine_role="canonical_evidence_host")
    assert unasserted["machine"]["authority_assertion_complete"] is False
    assert unasserted["eligibility"]["canonical_machine_candidate"] is False
    assert "canonical_machine_authority_not_asserted" in unasserted["eligibility"]["reason_codes"]
    with pytest.raises(CollectorError) as error:
        collect(repo, machine_id="vaultnode", machine_role="provisional_development_host", assert_canonical_machine=True)
    assert error.value.code == "canonical_machine_authority_inconsistent"
    with pytest.raises(CollectorError) as error:
        collect(repo, machine_id="vaultnode", machine_role="canonical_evidence_host", assert_canonical_machine=True)
    assert error.value.code == "canonical_machine_authority_inconsistent"
    canonical = collect(repo, machine_id="vaultnode", machine_role="canonical_evidence_host", authority_basis="operator-confirmed", assert_canonical_machine=True)
    assert canonical["eligibility"]["canonical_machine_candidate"] is True


def test_invalid_role_and_non_worktree_fail_closed(tmp_path: Path) -> None:
    with pytest.raises(CollectorError) as error:
        collect_identity(tmp_path, machine_role="made_up_role")
    assert error.value.code == "invalid_machine_role"
    with pytest.raises(CollectorError) as error:
        collect_identity(tmp_path, hostname="fixture-host")
    assert error.value.code == "path_not_git_worktree"


def test_diagnostic_path_is_explicit_and_remote_credentials_are_not_emitted(tmp_path: Path) -> None:
    repo, _ = make_repo(tmp_path)
    run_git(repo, "remote", "set-url", "origin", "https://user:super-secret@example.invalid/org/repo.git")
    result = collect(repo, diagnostic_working_path=True)
    encoded = json.dumps(result)
    assert result["repository"]["diagnostic_working_path"] == str(repo)
    assert "super-secret" not in encoded
    assert "user:" not in encoded


def test_collection_does_not_mutate_git_state_or_tracked_contents(tmp_path: Path) -> None:
    repo, _ = make_repo(tmp_path)
    before = {
        "head": run_git(repo, "rev-parse", "HEAD"),
        "refs": run_git(repo, "show-ref"),
        "status": run_git(repo, "status", "--porcelain=v1"),
        "tracked": (repo / "tracked.txt").read_bytes(),
    }
    collect(repo)
    after = {
        "head": run_git(repo, "rev-parse", "HEAD"),
        "refs": run_git(repo, "show-ref"),
        "status": run_git(repo, "status", "--porcelain=v1"),
        "tracked": (repo / "tracked.txt").read_bytes(),
    }
    assert after == before


def test_cli_exit_codes_and_stable_json(tmp_path: Path) -> None:
    repo, _ = make_repo(tmp_path)
    args = [sys.executable, str(SCRIPT), "--repo", str(repo), "--machine-id", "local-test"]
    first = subprocess.run(args, check=False, capture_output=True, text=True)
    second = subprocess.run(args, check=False, capture_output=True, text=True)
    assert first.returncode == second.returncode == 0
    assert first.stdout == second.stdout
    parsed = json.loads(first.stdout)
    assert parsed["schema_version"] == "canonical_audit_evidence_identity_result.v1"
