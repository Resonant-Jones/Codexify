"""Read-only Worktree Lane operator route.

Exposes discovered worktree lanes as structured JSON for the Operator
Workbench. This route performs discovery + state collection on every call (an
explicit refresh action is provided as well) and never mutates the repo, the
index, branches, or files.

Only metadata is returned: path, branch, commit SHA, status counts, upstream
name, ahead/behind counts, and risk flags. No file contents or diffs are
inspected or exposed.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from guardian.core.dependencies import require_api_key
from guardian.worktrees.service import (
    REPO_PATH_ENV,
    discover_worktree_lanes,
    resolve_repo_path,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["worktrees"])


class WorktreeLaneModel(BaseModel):
    """API projection of a single worktree lane."""

    repo_path: str
    worktree_path: str
    branch: Optional[str] = None
    head_sha: Optional[str] = None
    detached: bool = False
    bare: bool = False
    dirty_file_count: int = 0
    staged_file_count: int = 0
    unstaged_file_count: int = 0
    untracked_file_count: int = 0
    upstream: Optional[str] = None
    ahead_count: Optional[int] = None
    behind_count: Optional[int] = None
    risk_flags: list[str] = Field(default_factory=list)
    exists: bool = True


class WorktreeLanesResponse(BaseModel):
    """Full operator worktree-lane discovery response."""

    repo_path: str
    repo_path_source: str
    lane_count: int
    lanes: list[WorktreeLaneModel]
    warnings: list[str] = Field(default_factory=list)


def _build_response(repo_path: str, source: str) -> WorktreeLanesResponse:
    discovery = discover_worktree_lanes(repo_path, repo_path_source=source)
    if discovery.errors:
        raise HTTPException(
            status_code=400,
            detail={
                "repo_path": discovery.repo_path,
                "errors": discovery.errors,
            },
        )
    lanes = [
        WorktreeLaneModel(
            repo_path=lane.repo_path,
            worktree_path=lane.worktree_path,
            branch=lane.branch,
            head_sha=lane.head_sha,
            detached=lane.detached,
            bare=lane.bare,
            dirty_file_count=lane.dirty_file_count,
            staged_file_count=lane.staged_file_count,
            unstaged_file_count=lane.unstaged_file_count,
            untracked_file_count=lane.untracked_file_count,
            upstream=lane.upstream,
            ahead_count=lane.ahead_count,
            behind_count=lane.behind_count,
            risk_flags=list(lane.risk_flags),
            exists=lane.exists,
        )
        for lane in discovery.lanes
    ]
    return WorktreeLanesResponse(
        repo_path=discovery.repo_path,
        repo_path_source=discovery.repo_path_source,
        lane_count=len(lanes),
        lanes=lanes,
        warnings=list(discovery.warnings),
    )


@router.get(
    "/api/worktrees/lanes",
    response_model=WorktreeLanesResponse,
    summary="List worktree lanes (read-only)",
)
async def list_worktree_lanes(
    repo_path: Optional[str] = Query(
        default=None,
        description=(
            "Repository path to inspect. Defaults to the " f"{REPO_PATH_ENV} env var."
        ),
    ),
    api_key: str = Depends(require_api_key),
) -> WorktreeLanesResponse:
    """Return the current operational state of every worktree lane.

    Re-runs discovery and read-only state collection on each call. Does not
    inspect or expose file contents.
    """
    _ = api_key
    resolved, source = resolve_repo_path(repo_path)
    assert resolved is not None  # resolve_repo_path always falls back
    return _build_response(resolved, source)


@router.post(
    "/api/worktrees/refresh",
    response_model=WorktreeLanesResponse,
    summary="Refresh worktree lanes (read-only)",
)
async def refresh_worktree_lanes(
    repo_path: Optional[str] = Query(default=None),
    api_key: str = Depends(require_api_key),
) -> WorktreeLanesResponse:
    """Explicit refresh action: re-run discovery and state collection.

    Identical to ``GET /api/worktrees/lanes`` and equally non-mutating.
    """
    _ = api_key
    resolved, source = resolve_repo_path(repo_path)
    assert resolved is not None
    return _build_response(resolved, source)
