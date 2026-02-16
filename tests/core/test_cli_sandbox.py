from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from guardian.core.orchestrator.cli_sandbox import (
    CommandCatalog,
    CommandDefinition,
    CommandExecutor,
    WorkspaceRootManager,
)


def _fake_completed(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(command, 0, stdout="ok\n", stderr="")


def test_workspace_root_manager_rejects_path_traversal(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    manager = WorkspaceRootManager(root)

    with pytest.raises(PermissionError):
        manager.validate_read("../outside.txt")


def test_workspace_root_manager_rejects_absolute_path_outside_root(
    tmp_path: Path,
) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("x", encoding="utf-8")
    manager = WorkspaceRootManager(root)

    with pytest.raises(PermissionError):
        manager.validate_read(outside)


def test_workspace_root_manager_rejects_symlink_escape(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("x", encoding="utf-8")
    escape = root / "escape.txt"
    escape.symlink_to(outside)

    manager = WorkspaceRootManager(root)
    with pytest.raises(PermissionError):
        manager.validate_read(escape)


def test_workspace_root_manager_accepts_in_root_path(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    manager = WorkspaceRootManager(root)

    resolved = manager.validate_write("subdir/file.txt")
    assert resolved == (root / "subdir" / "file.txt").resolve()


def test_command_executor_rejects_unknown_command_id(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    manager = WorkspaceRootManager(root)
    executor = CommandExecutor(
        workspace_root_manager=manager,
        command_catalog=CommandCatalog.default(root),
    )

    with pytest.raises(KeyError):
        executor.execute("unknown_command", workspace_root=root)


def test_command_executor_runs_with_workspace_root_cwd(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    manager = WorkspaceRootManager(root)
    calls: dict[str, object] = {}

    def _run(command: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
        calls["command"] = command
        calls["kwargs"] = kwargs
        return _fake_completed(command)

    executor = CommandExecutor(
        workspace_root_manager=manager,
        command_catalog=CommandCatalog.default(root),
        run_command=_run,
    )

    completed = executor.execute("git_status", workspace_root=root)
    assert completed.returncode == 0
    assert calls["command"] == ["git", "status", "--short"]
    kwargs = calls["kwargs"]
    assert isinstance(kwargs, dict)
    assert kwargs["cwd"] == root.resolve()
    assert kwargs["env"]["CODEXIFY_NETWORK_EGRESS"] == "disabled"


def test_command_executor_rejects_network_command_by_default(
    tmp_path: Path,
) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    manager = WorkspaceRootManager(root)
    run_called = {"value": False}

    def _run(command: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
        run_called["value"] = True
        return _fake_completed(command)

    catalog = CommandCatalog(
        definitions={
            "net_probe": CommandDefinition(
                id="net_probe",
                executable="curl",
                args_template=("https://example.com",),
                requires_network=True,
            )
        }
    )
    executor = CommandExecutor(
        workspace_root_manager=manager,
        command_catalog=catalog,
        run_command=_run,
    )

    with pytest.raises(PermissionError):
        executor.execute("net_probe", workspace_root=root)
    assert run_called["value"] is False


def test_command_executor_rejects_out_of_root_path_params(
    tmp_path: Path,
) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    manager = WorkspaceRootManager(root)
    executor = CommandExecutor(
        workspace_root_manager=manager,
        command_catalog=CommandCatalog.default(root),
        run_command=lambda command, **kwargs: _fake_completed(command),
    )
    outside = tmp_path / "outside.py"
    outside.write_text("print('x')\n", encoding="utf-8")

    with pytest.raises(PermissionError):
        executor.execute(
            "git_diff",
            params={"path": "../outside.py"},
            workspace_root=root,
        )

    with pytest.raises(PermissionError):
        executor.execute(
            "git_diff",
            params={"path": str(outside)},
            workspace_root=root,
        )
