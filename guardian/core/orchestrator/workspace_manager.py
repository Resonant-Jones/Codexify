from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from guardian.core.orchestrator.cli_sandbox import (
    CommandCatalog,
    CommandExecutor,
    WorkspaceRootManager,
)


@dataclass
class WorkspaceManager:
    """Manage per-task git worktrees for isolated campaign execution."""

    repo_root: Path | None = None

    def __post_init__(self) -> None:
        root = self.repo_root if self.repo_root is not None else Path.cwd()
        self.repo_root = root.resolve()
        self._worktrees_root = self.repo_root / ".codexify" / "worktrees"
        self._command_catalog = CommandCatalog.default(root=self.repo_root)

    def create_worktree(
        self,
        task_id: str,
        base_branch: str,
        campaign_id: str,
        force: bool = False,
    ) -> Path:
        task_path = self._task_path(task_id)
        if task_path.exists():
            if not force:
                raise FileExistsError(
                    f"Worktree already exists for task '{task_id}': {task_path}"
                )
            self._force_remove_existing(task_id)

        task_path.parent.mkdir(parents=True, exist_ok=True)
        branch_name = self._branch_name(campaign_id, task_id)
        subprocess.run(
            [
                "git",
                "-C",
                str(self.repo_root),
                "worktree",
                "add",
                "-b",
                branch_name,
                str(task_path),
                base_branch,
            ],
            check=True,
        )

        task_path.mkdir(parents=True, exist_ok=True)
        self._write_manifest(
            task_id,
            {
                "task_id": task_id,
                "campaign_id": campaign_id,
                "base_branch": base_branch,
                "branch": branch_name,
                "path": str(task_path),
            },
        )
        return task_path

    def run_in_worktree(
        self,
        task_id: str,
        command_id: str,
        params: dict[str, Any] | None = None,
        *,
        allow_network: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        if not command_id or not isinstance(command_id, str):
            raise ValueError("command_id must be a non-empty string")
        manifest = self._load_manifest(task_id)
        task_path = Path(manifest["path"])
        root_manager = WorkspaceRootManager(task_path)
        executor = CommandExecutor(
            workspace_root_manager=root_manager,
            command_catalog=self._command_catalog,
            run_command=subprocess.run,
        )
        return executor.execute(
            command_id=command_id,
            params=params or {},
            workspace_root=task_path,
            allow_network=allow_network,
        )

    def list_command_ids(self) -> list[str]:
        return self._command_catalog.ids()

    def cleanup_worktree(self, task_id: str) -> None:
        task_path = self._task_path(task_id)
        manifest = self._load_manifest_if_exists(task_id)
        branch_name = manifest.get("branch") if manifest else None

        if task_path.exists():
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(self.repo_root),
                    "worktree",
                    "remove",
                    "--force",
                    str(task_path),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

        if branch_name:
            subprocess.run(
                ["git", "-C", str(self.repo_root), "branch", "-D", branch_name],
                check=False,
                capture_output=True,
                text=True,
            )

        if task_path.exists():
            shutil.rmtree(task_path, ignore_errors=True)

    def _force_remove_existing(self, task_id: str) -> None:
        self.cleanup_worktree(task_id)

    def _task_path(self, task_id: str) -> Path:
        if (
            not task_id
            or task_id in {".", ".."}
            or "/" in task_id
            or "\\" in task_id
        ):
            raise ValueError(f"Invalid task_id '{task_id}'")
        candidate = (self._worktrees_root / task_id).resolve()
        root = self._worktrees_root.resolve()
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise ValueError(f"Invalid task_id '{task_id}'") from exc
        return candidate

    def _manifest_path(self, task_id: str) -> Path:
        return self._task_path(task_id) / "manifest.json"

    def _write_manifest(self, task_id: str, payload: dict[str, str]) -> None:
        manifest_path = self._manifest_path(task_id)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )

    def _load_manifest(self, task_id: str) -> dict[str, str]:
        manifest = self._load_manifest_if_exists(task_id)
        if manifest is None:
            raise FileNotFoundError(
                f"manifest.json not found for task '{task_id}'"
            )
        return manifest

    def _load_manifest_if_exists(self, task_id: str) -> dict[str, str] | None:
        manifest_path = self._manifest_path(task_id)
        if not manifest_path.exists():
            return None
        return json.loads(manifest_path.read_text(encoding="utf-8"))

    @staticmethod
    def _branch_name(campaign_id: str, task_id: str) -> str:
        return f"campaign/{campaign_id}/{task_id}"
