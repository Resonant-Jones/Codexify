from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from guardian.core.orchestrator.workspace_manager import WorkspaceManager


def _manager(tmp_path: Path) -> WorkspaceManager:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True)
    return WorkspaceManager(repo_root=repo_root)


@pytest.mark.parametrize("task_id", ["", ".", "..", "a/b", r"a\b"])
def test_task_path_rejects_invalid_task_ids(tmp_path: Path, task_id: str):
    manager = _manager(tmp_path)
    with pytest.raises(ValueError):
        manager._task_path(task_id)


def test_cleanup_worktree_rejects_parent_dot_segment(tmp_path: Path):
    manager = _manager(tmp_path)
    with patch(
        "guardian.core.orchestrator.workspace_manager.shutil.rmtree"
    ) as rmtree_mock:
        with pytest.raises(ValueError):
            manager.cleanup_worktree("..")
        rmtree_mock.assert_not_called()


def test_task_path_stays_within_worktrees_root(tmp_path: Path):
    manager = _manager(tmp_path)
    task_path = manager._task_path("task-001")
    root = (manager.repo_root / ".codexify" / "worktrees").resolve()
    assert task_path.is_relative_to(root)
