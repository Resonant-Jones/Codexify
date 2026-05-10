from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from guardian.agents import commit_gate
from guardian.agents.commit_gate import commit_after_green
from guardian.protocol_tokens import ErrorCode


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )


def _init_git_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    assert _run(["git", "init"], path).returncode == 0
    assert (
        _run(
            ["git", "config", "user.email", "test@example.com"], path
        ).returncode
        == 0
    )
    assert (
        _run(["git", "config", "user.name", "Test User"], path).returncode == 0
    )


def _seed_initial_commit(path: Path) -> None:
    file_path = path / "README.md"
    file_path.write_text("baseline\n", encoding="utf-8")
    assert _run(["git", "add", "README.md"], path).returncode == 0
    assert _run(["git", "commit", "-m", "initial"], path).returncode == 0


def test_commit_after_green_creates_commit_and_reports_hash(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    _init_git_repo(repo)
    _seed_initial_commit(repo)

    changed = repo / "README.md"
    changed.write_text("baseline\nupdate\n", encoding="utf-8")

    result = commit_after_green(str(repo), "Commit after green", "codex/lease")

    assert result.attempted is True
    assert result.committed is True
    assert result.reason_code == ErrorCode.GIT_COMMIT_CREATED.value
    assert result.status == "committed"
    assert result.commit_hash is not None
    assert result.files_changed == ["README.md"]

    head = _run(["git", "rev-parse", "HEAD"], repo)
    assert head.returncode == 0
    assert head.stdout.strip() == result.commit_hash


def test_commit_after_green_no_changes_returns_skipped(tmp_path: Path) -> None:
    repo = tmp_path / "repo-no-changes"
    _init_git_repo(repo)
    _seed_initial_commit(repo)

    result = commit_after_green(str(repo), "No-op commit")

    assert result.attempted is True
    assert result.committed is False
    assert result.status == "skipped"
    assert result.reason_code == ErrorCode.GIT_NO_CHANGES_TO_COMMIT.value
    assert result.commit_hash is None
    assert result.files_changed == []


def test_commit_after_green_rejects_non_git_directory(tmp_path: Path) -> None:
    non_git = tmp_path / "not-a-repo"
    non_git.mkdir(parents=True, exist_ok=True)

    result = commit_after_green(str(non_git), "Should fail")

    assert result.attempted is True
    assert result.committed is False
    assert result.status == "failed"
    assert result.reason_code == ErrorCode.GIT_WORKTREE_INVALID.value


def test_commit_after_green_rejects_missing_path(tmp_path: Path) -> None:
    missing = tmp_path / "missing-repo"

    result = commit_after_green(str(missing), "Should fail")

    assert result.attempted is True
    assert result.committed is False
    assert result.status == "failed"
    assert result.reason_code == ErrorCode.GIT_WORKTREE_INVALID.value


def test_commit_after_green_failure_message_is_bounded(
    monkeypatch, tmp_path: Path
) -> None:
    repo = tmp_path / "repo-failure"
    _init_git_repo(repo)
    _seed_initial_commit(repo)
    (repo / "README.md").write_text("baseline\nupdate\n", encoding="utf-8")

    original_run_git = commit_gate._run_git

    def _fake_run_git(
        argv: list[str], *, cwd: str
    ) -> subprocess.CompletedProcess[str]:
        if argv and argv[0] == "commit":
            return subprocess.CompletedProcess(
                ["git", *argv],
                1,
                stdout="",
                stderr="x" * 2000,
            )
        return original_run_git(argv, cwd=cwd)

    monkeypatch.setattr(commit_gate, "_run_git", _fake_run_git)

    result = commit_after_green(str(repo), "Should bound failure")

    assert result.attempted is True
    assert result.committed is False
    assert result.reason_code == ErrorCode.GIT_COMMIT_FAILED.value
    assert result.message is not None
    assert len(result.message) <= 320


def test_commit_after_green_never_uses_push_merge_or_worktree_commands(
    monkeypatch, tmp_path: Path
) -> None:
    repo = tmp_path / "repo-command-scope"
    _init_git_repo(repo)
    _seed_initial_commit(repo)
    (repo / "README.md").write_text("baseline\nupdate\n", encoding="utf-8")

    seen_argv: list[list[str]] = []
    original_run_git = commit_gate._run_git

    def _spy_run_git(
        argv: list[str], *, cwd: str
    ) -> subprocess.CompletedProcess[str]:
        seen_argv.append(list(argv))
        return original_run_git(argv, cwd=cwd)

    monkeypatch.setattr(commit_gate, "_run_git", _spy_run_git)

    result = commit_after_green(str(repo), "Scoped commands")

    assert result.committed is True
    flattened = " ".join(" ".join(argv) for argv in seen_argv)
    assert "push" not in flattened
    assert "merge" not in flattened
    assert "worktree" not in flattened
