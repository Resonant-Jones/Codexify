"""Tests for the read-only worktree discovery service.

Uses an injected fake git runner so no subprocess is spawned. The fake runner
also asserts that only allowed read-only git commands are ever invoked, locking
in the non-mutation guarantee at test time.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from guardian.worktrees.model import WorktreeLane
from guardian.worktrees.service import (
    GitError,
    discover_worktree_lanes,
    resolve_repo_path,
    run_git,
)

# Allowed read-only commands per the MVP spec. Any other git subcommand would
# be a mutation and must fail the test.
ALLOWED_COMMANDS: set[tuple[str, ...]] = {
    ("worktree", "list", "--porcelain"),
    ("status", "--short"),
    ("branch", "--show-current"),
    ("rev-parse", "HEAD"),
    ("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"),
    ("rev-list", "--left-right", "--count", "HEAD...@{u}"),
}

# A responder maps a command signature + cwd to stdout (or raises GitError).
Responder = Callable[[tuple[str, ...], str], str]


class RoutingRunner:
    """Records calls, asserts only allowed commands run, routes to a responder."""

    def __init__(self, respond: Responder) -> None:
        self._respond = respond
        self.calls: list[tuple[tuple[str, ...], str]] = []

    def __call__(self, args: list[str], *, cwd: str) -> str:
        key = tuple(args)
        assert (
            key in ALLOWED_COMMANDS
        ), f"non-allowed or mutating git command invoked: {key}"
        self.calls.append((key, cwd))
        return self._respond(key, cwd)


def _make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    return repo


def test_run_git_disables_optional_locks(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_run(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return type(
            "Completed", (), {"returncode": 0, "stdout": "ok\n", "stderr": ""}
        )()

    monkeypatch.setattr("guardian.worktrees.service.subprocess.run", fake_run)

    assert run_git(["status", "--short"], cwd=str(tmp_path)) == "ok\n"

    kwargs = captured["kwargs"]
    assert isinstance(kwargs, dict)
    env = kwargs["env"]
    assert isinstance(env, dict)
    assert env["GIT_OPTIONAL_LOCKS"] == "0"


# ---------------------------------------------------------------------------
# resolve_repo_path
# ---------------------------------------------------------------------------


def test_resolve_repo_path_explicit_wins() -> None:
    path, source = resolve_repo_path(
        "/explicit", env={"CODEXIFY_WORKTREE_REPO_PATH": "/from/env"}
    )
    assert path == "/explicit"
    assert source == "query"


def test_resolve_repo_path_env_fallback() -> None:
    path, source = resolve_repo_path(
        None, env={"CODEXIFY_WORKTREE_REPO_PATH": "/from/env"}
    )
    assert path == "/from/env"
    assert source == "env"


def test_resolve_repo_path_dev_default_when_unset() -> None:
    path, source = resolve_repo_path(None, env={})
    assert source == "dev_default"
    assert path


# ---------------------------------------------------------------------------
# discover_worktree_lanes
# ---------------------------------------------------------------------------


def test_discover_collects_state_and_risk_flags(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    main_path = repo / "main"
    feat_path = repo / "feat"
    main_path.mkdir()
    feat_path.mkdir()

    porcelain = (
        f"worktree {main_path}\n"
        "HEAD aaa111\n"
        "branch refs/heads/main\n"
        "\n"
        f"worktree {feat_path}\n"
        "HEAD bbb222\n"
        "branch refs/heads/feat/lane\n"
    )

    def respond(args: tuple[str, ...], cwd: str) -> str:
        if args == ("worktree", "list", "--porcelain"):
            return porcelain
        if args == (
            "branch",
            "--show-current",
        ):
            return "main\n" if cwd == str(main_path) else "feat/lane\n"
        if args == ("rev-parse", "HEAD"):
            return "aaa111\n" if cwd == str(main_path) else "bbb222\n"
        if args == ("status", "--short"):
            # feat lane is dirty with one staged + one untracked.
            return "" if cwd == str(main_path) else "M  staged.py\n?? new.py\n"
        if args == ("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"):
            # main has upstream and is behind by 2; feat has no upstream.
            if cwd == str(feat_path):
                raise GitError("no upstream")
            return "origin/main\n"
        if args == ("rev-list", "--left-right", "--count", "HEAD...@{u}"):
            return "0\t2\n"
        return ""

    runner = RoutingRunner(respond)
    discovery = discover_worktree_lanes(str(repo), git_runner=runner)
    assert discovery.errors == []
    assert len(discovery.lanes) == 2

    main_lane = next(lane for lane in discovery.lanes if lane.branch == "main")
    feat_lane = next(lane for lane in discovery.lanes if lane.branch == "feat/lane")

    assert main_lane.dirty_file_count == 0
    assert main_lane.upstream == "origin/main"
    assert main_lane.behind_count == 2
    assert "behind_upstream" in main_lane.risk_flags
    assert "dirty_main" not in main_lane.risk_flags

    assert feat_lane.dirty_file_count == 2
    assert feat_lane.staged_file_count == 1
    assert feat_lane.untracked_file_count == 1
    assert feat_lane.upstream is None
    assert "no_upstream" in feat_lane.risk_flags
    assert "staged_changes" in feat_lane.risk_flags
    assert "untracked_files" in feat_lane.risk_flags
    assert "dirty_worktree" in feat_lane.risk_flags
    assert "git_state_error" not in feat_lane.risk_flags


def test_discover_detached_lane(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    detached_path = repo / "detached"
    detached_path.mkdir()

    porcelain = f"worktree {detached_path}\nHEAD cafe00\ndetached\n"

    def respond(args: tuple[str, ...], cwd: str) -> str:
        if args == ("worktree", "list", "--porcelain"):
            return porcelain
        if args == (
            "branch",
            "--show-current",
        ):
            return ""  # empty => detached
        if args == ("rev-parse", "HEAD"):
            return "cafe00\n"
        if args == ("status", "--short"):
            return ""
        return ""

    runner = RoutingRunner(respond)
    discovery = discover_worktree_lanes(str(repo), git_runner=runner)
    assert len(discovery.lanes) == 1
    lane = discovery.lanes[0]
    assert lane.detached is True
    assert lane.branch is None
    assert "detached_head" in lane.risk_flags
    assert "no_upstream" not in lane.risk_flags
    # No upstream rev-parse should be issued for a detached lane.
    invoked = {call[0] for call in runner.calls}
    assert (
        "rev-parse",
        "--abbrev-ref",
        "--symbolic-full-name",
        "@{u}",
    ) not in invoked


def test_discover_missing_worktree_folder_warns_not_crash(
    tmp_path: Path,
) -> None:
    repo = _make_repo(tmp_path)
    gone_path = repo / "gone"

    porcelain = (
        f"worktree {gone_path}\n" "HEAD dead00\n" "branch refs/heads/feat/missing\n"
    )

    def respond(args: tuple[str, ...], cwd: str) -> str:
        assert args == ("worktree", "list", "--porcelain")
        return porcelain

    runner = RoutingRunner(respond)
    discovery = discover_worktree_lanes(str(repo), git_runner=runner)
    assert discovery.errors == []
    assert len(discovery.lanes) == 1
    lane = discovery.lanes[0]
    assert lane.exists is False
    assert any("no longer exists" in w for w in discovery.warnings)
    # Only the porcelain command ran; no per-worktree git inside missing cwd.
    assert runner.calls == [(("worktree", "list", "--porcelain"), str(repo))]


def test_discover_repo_path_does_not_exist(tmp_path: Path) -> None:
    runner = RoutingRunner(lambda args, cwd: "")
    discovery = discover_worktree_lanes(str(tmp_path / "missing"), git_runner=runner)
    assert discovery.lanes == []
    assert discovery.errors
    assert "does not exist" in discovery.errors[0]
    assert runner.calls == []


def test_discover_not_a_git_repository(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)

    def respond(args: tuple[str, ...], cwd: str) -> str:
        raise GitError("fatal: not a git repository")

    runner = RoutingRunner(respond)
    discovery = discover_worktree_lanes(str(repo), git_runner=runner)
    assert discovery.lanes == []
    assert discovery.errors
    assert "not a Git repository" in discovery.errors[0]


def test_discover_no_worktrees_beyond_main_warns(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)

    def respond(args: tuple[str, ...], cwd: str) -> str:
        assert args == ("worktree", "list", "--porcelain")
        return ""

    runner = RoutingRunner(respond)
    discovery = discover_worktree_lanes(str(repo), git_runner=runner)
    assert discovery.lanes == []
    assert any("no worktrees" in w for w in discovery.warnings)


def test_unexpected_git_status_failure_sets_git_state_error(
    tmp_path: Path,
) -> None:
    repo = _make_repo(tmp_path)
    wt = repo / "wt"
    wt.mkdir()
    porcelain = f"worktree {wt}\nHEAD abc\nbranch refs/heads/feat/x\n"

    def respond(args: tuple[str, ...], cwd: str) -> str:
        if args == ("worktree", "list", "--porcelain"):
            return porcelain
        if args == ("status", "--short"):
            raise GitError("index.lock")
        if args == (
            "branch",
            "--show-current",
        ):
            return "feat/x\n"
        if args == ("rev-parse", "HEAD"):
            return "abc\n"
        if args == ("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"):
            return "origin/feat/x\n"
        return ""

    runner = RoutingRunner(respond)
    discovery = discover_worktree_lanes(str(repo), git_runner=runner)
    lane: WorktreeLane = discovery.lanes[0]
    assert "git_state_error" in lane.risk_flags
