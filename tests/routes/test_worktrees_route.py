"""Tests for the read-only worktree lane operator route.

Mounts only the worktrees router on a minimal FastAPI app (avoiding the full
guardian_api bootstrap) and overrides auth + discovery so no subprocess or DB
is required.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from guardian.routes import worktrees as worktrees_routes
from guardian.worktrees.model import WorktreeDiscovery, WorktreeLane


def _make_app(discovery: WorktreeDiscovery) -> FastAPI:
    app = FastAPI()
    app.include_router(worktrees_routes.router)
    app.dependency_overrides[worktrees_routes.require_api_key] = lambda: "key"
    worktrees_routes.discover_worktree_lanes = lambda *args, **kwargs: discovery
    return app


def _sample_discovery() -> WorktreeDiscovery:
    lanes = [
        WorktreeLane(
            repo_path="/repo",
            worktree_path="/repo",
            branch="main",
            head_sha="aaa111",
            upstream="origin/main",
            ahead_count=0,
            behind_count=0,
        ),
        WorktreeLane(
            repo_path="/repo",
            worktree_path="/repo/feat",
            branch="feat/lane",
            head_sha="bbb222",
            upstream="origin/feat/lane",
            ahead_count=1,
            behind_count=2,
            dirty_file_count=2,
            staged_file_count=1,
            untracked_file_count=1,
            risk_flags=[
                "dirty_worktree",
                "staged_changes",
                "untracked_files",
                "behind_upstream",
            ],
        ),
        WorktreeLane(
            repo_path="/repo",
            worktree_path="/repo/gone",
            branch=None,
            head_sha="ccc333",
            detached=True,
            risk_flags=["detached_head"],
            exists=False,
        ),
    ]
    return WorktreeDiscovery(
        repo_path="/repo",
        repo_path_source="query",
        lanes=lanes,
        warnings=["worktree path no longer exists: /repo/gone"],
    )


def test_list_lanes_returns_structured_state() -> None:
    app = _make_app(_sample_discovery())
    client = TestClient(app)
    resp = client.get("/api/worktrees/lanes", params={"repo_path": "/repo"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["repo_path"] == "/repo"
    assert body["repo_path_source"] == "query"
    assert body["lane_count"] == 3
    assert len(body["lanes"]) == 3

    main_lane = next(lane for lane in body["lanes"] if lane["worktree_path"] == "/repo")
    assert main_lane["branch"] == "main"
    assert main_lane["head_sha"] == "aaa111"
    assert main_lane["upstream"] == "origin/main"
    assert main_lane["risk_flags"] == []

    feat_lane = next(
        lane for lane in body["lanes"] if lane["worktree_path"] == "/repo/feat"
    )
    assert feat_lane["dirty_file_count"] == 2
    assert feat_lane["staged_file_count"] == 1
    assert feat_lane["untracked_file_count"] == 1
    assert feat_lane["ahead_count"] == 1
    assert feat_lane["behind_count"] == 2
    assert "behind_upstream" in feat_lane["risk_flags"]

    gone_lane = next(
        lane for lane in body["lanes"] if lane["worktree_path"] == "/repo/gone"
    )
    assert gone_lane["exists"] is False
    assert gone_lane["detached"] is True
    assert "detached_head" in gone_lane["risk_flags"]
    assert any("no longer exists" in w for w in body["warnings"])


def test_refresh_returns_same_shape() -> None:
    app = _make_app(_sample_discovery())
    client = TestClient(app)
    resp = client.post("/api/worktrees/refresh", params={"repo_path": "/repo"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["lane_count"] == 3
    assert body["repo_path_source"] == "query"


def test_discovery_errors_return_400() -> None:
    discovery = WorktreeDiscovery(
        repo_path="/nope",
        repo_path_source="env",
        errors=["repo_path does not exist or is not a directory"],
    )
    app = _make_app(discovery)
    client = TestClient(app)
    resp = client.get("/api/worktrees/lanes")
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert detail["repo_path"] == "/nope"
    assert any("does not exist" in e for e in detail["errors"])
