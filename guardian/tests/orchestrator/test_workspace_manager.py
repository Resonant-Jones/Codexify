import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from guardian.core.orchestrator.workspace_manager import WorkspaceManager


def test_create_worktree_creates_path_manifest_and_branch(tmp_path: Path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True)
    manager = WorkspaceManager(repo_root=repo_root)
    task_path = repo_root / ".codexify" / "worktrees" / "task-001"

    def fake_run(command, **kwargs):
        if command[:5] == ["git", "-C", str(repo_root), "worktree", "add"]:
            task_path.mkdir(parents=True, exist_ok=True)
        return subprocess.CompletedProcess(command, 0)

    with patch(
        "guardian.core.orchestrator.workspace_manager.subprocess.run",
        side_effect=fake_run,
    ) as run_mock:
        created_path = manager.create_worktree(
            task_id="task-001",
            base_branch="main",
            campaign_id="camp-2026",
        )

    assert created_path == task_path
    run_mock.assert_called_once_with(
        [
            "git",
            "-C",
            str(repo_root),
            "worktree",
            "add",
            "-b",
            "campaign/camp-2026/task-001",
            str(task_path),
            "main",
        ],
        check=True,
    )

    manifest = json.loads((task_path / "manifest.json").read_text())
    assert manifest["branch"] == "campaign/camp-2026/task-001"
    assert manifest["path"] == str(task_path)


def test_create_worktree_refuses_existing_path_without_force(tmp_path: Path):
    repo_root = tmp_path / "repo"
    task_path = repo_root / ".codexify" / "worktrees" / "task-001"
    task_path.mkdir(parents=True)
    manager = WorkspaceManager(repo_root=repo_root)

    with patch(
        "guardian.core.orchestrator.workspace_manager.subprocess.run"
    ) as run_mock:
        with pytest.raises(FileExistsError):
            manager.create_worktree(
                task_id="task-001",
                base_branch="main",
                campaign_id="camp-2026",
            )
        run_mock.assert_not_called()


def test_run_in_worktree_executes_with_task_working_directory(
    tmp_path: Path,
):
    repo_root = tmp_path / "repo"
    task_path = repo_root / ".codexify" / "worktrees" / "task-001"
    task_path.mkdir(parents=True)
    (task_path / "manifest.json").write_text(
        json.dumps(
            {
                "task_id": "task-001",
                "campaign_id": "camp-2026",
                "base_branch": "main",
                "branch": "campaign/camp-2026/task-001",
                "path": str(task_path),
            }
        ),
        encoding="utf-8",
    )
    manager = WorkspaceManager(repo_root=repo_root)
    completed = subprocess.CompletedProcess(
        args=["git", "status", "--short"],
        returncode=0,
        stdout="ok\n",
        stderr="",
    )

    with patch(
        "guardian.core.orchestrator.workspace_manager.subprocess.run",
        return_value=completed,
    ) as run_mock:
        result = manager.run_in_worktree("task-001", "git_status")

    assert result is completed
    run_mock.assert_called_once()
    args, kwargs = run_mock.call_args
    assert args[0] == ["git", "status", "--short"]
    assert kwargs["cwd"] == task_path
    assert kwargs["check"] is False
    assert kwargs["capture_output"] is True
    assert kwargs["text"] is True
    assert kwargs["timeout"] == 60
    assert kwargs["env"]["CODEXIFY_NETWORK_EGRESS"] == "disabled"
