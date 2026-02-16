from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class WorkspaceRoot:
    root: Path


class WorkspaceRootManager:
    """Resolve and validate paths against a single workspace root."""

    def __init__(self, root: Path | None = None) -> None:
        self._workspace_root: WorkspaceRoot | None = None
        if root is not None:
            self.register_root(root)

    @staticmethod
    def detect_project_root(start: Path | None = None) -> Path:
        """Detect project root via marker, then git, then cwd fallback.

        Rule order:
        1) Prefer explicit Codexify marker file `.codexify_root` (for init flows).
        2) Otherwise use the nearest `.git` ancestor.
        3) Fallback to the current working directory.
        """

        start_path = (start or Path.cwd()).resolve()
        for candidate in (start_path, *start_path.parents):
            if (candidate / ".codexify_root").is_file():
                return candidate
            if (candidate / ".git").exists():
                return candidate
        return start_path

    @property
    def workspace_root(self) -> WorkspaceRoot:
        if self._workspace_root is None:
            raise RuntimeError("workspace root has not been registered")
        return self._workspace_root

    def register_root(self, path: str | Path | None = None) -> WorkspaceRoot:
        root_path = (
            Path(path) if path is not None else self.detect_project_root()
        )
        workspace_root = WorkspaceRoot(root=root_path.resolve())
        self._workspace_root = workspace_root
        return workspace_root

    def resolve_under_root(self, path: str | Path) -> Path:
        root = self.workspace_root.root
        candidate = Path(path)
        normalized = (
            candidate if candidate.is_absolute() else (root / candidate)
        )
        resolved = normalized.resolve(strict=False)
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise PermissionError(
                f"path '{path}' resolves outside workspace root '{root}'"
            ) from exc
        return resolved

    def validate_read(self, path: str | Path) -> Path:
        return self.resolve_under_root(path)

    def validate_write(self, path: str | Path) -> Path:
        return self.resolve_under_root(path)

    def validate_exec(self, path: str | Path) -> Path:
        return self.resolve_under_root(path)


@dataclass(frozen=True)
class CommandDefinition:
    id: str
    executable: str
    args_template: tuple[str, ...] = ()
    allowed_params: frozenset[str] = field(default_factory=frozenset)
    timeout_seconds: int = 60
    max_output_kb: int = 512
    requires_network: bool = False
    allowed_paths: tuple[str, ...] = ()
    path_params: tuple[str, ...] = ()


class CommandCatalog:
    def __init__(
        self, definitions: dict[str, CommandDefinition] | None = None
    ) -> None:
        self._definitions = definitions or {}

    def get(self, command_id: str) -> CommandDefinition:
        try:
            return self._definitions[command_id]
        except KeyError as exc:
            raise KeyError(f"Unknown command_id '{command_id}'") from exc

    def ids(self) -> list[str]:
        return sorted(self._definitions)

    @classmethod
    def default(cls, root: Path | None = None) -> CommandCatalog:
        definitions: dict[str, CommandDefinition] = {
            "git_status": CommandDefinition(
                id="git_status",
                executable="git",
                args_template=("status", "--short"),
            ),
            "git_diff": CommandDefinition(
                id="git_diff",
                executable="git",
                args_template=("diff", "--", "{path}"),
                allowed_params=frozenset({"path"}),
                allowed_paths=(".",),
                path_params=("path",),
            ),
            "pytest": CommandDefinition(
                id="pytest",
                executable="pytest",
                args_template=("-q", "{target}"),
                allowed_params=frozenset({"target"}),
                allowed_paths=(".",),
                path_params=("target",),
                timeout_seconds=300,
                max_output_kb=2048,
            ),
        }

        root_path = root.resolve() if root is not None else None
        if root_path is not None and (root_path / "pnpm-lock.yaml").exists():
            definitions["pnpm_test"] = CommandDefinition(
                id="pnpm_test",
                executable="pnpm",
                args_template=("test", "--", "{target}"),
                allowed_params=frozenset({"target"}),
                allowed_paths=(".",),
                path_params=("target",),
                timeout_seconds=300,
                max_output_kb=2048,
            )

        return cls(definitions=definitions)


class CommandExecutor:
    """Execute cataloged commands inside a registered workspace root."""

    def __init__(
        self,
        workspace_root_manager: WorkspaceRootManager,
        command_catalog: CommandCatalog | None = None,
        run_command: Callable[
            ..., subprocess.CompletedProcess[str]
        ] = subprocess.run,
    ) -> None:
        self._workspace_root_manager = workspace_root_manager
        self._command_catalog = command_catalog or CommandCatalog.default()
        self._run_command = run_command

    def execute(
        self,
        command_id: str,
        params: dict[str, Any] | None = None,
        *,
        workspace_root: Path | None = None,
        allow_network: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        root = self._workspace_root_manager.register_root(workspace_root).root
        definition = self._command_catalog.get(command_id)
        if definition.requires_network and not allow_network:
            raise PermissionError(
                f"command '{command_id}' requires network but network egress is disabled"
            )

        normalized_params = self._validate_params(definition, params or {})
        command_args = self._render_args(definition, normalized_params, root)
        env = dict(os.environ)
        env["CODEXIFY_NETWORK_EGRESS"] = (
            "enabled" if allow_network else "disabled"
        )

        completed = self._run_command(
            [definition.executable, *command_args],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            timeout=definition.timeout_seconds,
            env=env,
        )
        self._enforce_output_cap(completed, definition)
        return completed

    def _validate_params(
        self, definition: CommandDefinition, params: dict[str, Any]
    ) -> dict[str, Any]:
        unknown = sorted(set(params) - set(definition.allowed_params))
        if unknown:
            raise ValueError(
                f"Command '{definition.id}' does not accept params: {unknown}"
            )
        return dict(params)

    def _render_args(
        self,
        definition: CommandDefinition,
        params: dict[str, Any],
        root: Path,
    ) -> list[str]:
        rendered_args: list[str] = []
        for token in definition.args_template:
            if token.startswith("{") and token.endswith("}"):
                key = token[1:-1]
                value = params.get(key)
                if value in (None, ""):
                    continue
                rendered = str(value)
                if key in definition.path_params:
                    resolved = self._workspace_root_manager.resolve_under_root(
                        rendered
                    )
                    self._validate_allowed_path_prefix(
                        resolved, root, definition
                    )
                    rendered = str(resolved.relative_to(root))
                rendered_args.append(rendered)
                continue
            rendered_args.append(token)
        return rendered_args

    def _validate_allowed_path_prefix(
        self, resolved_path: Path, root: Path, definition: CommandDefinition
    ) -> None:
        if not definition.allowed_paths:
            return

        relative = resolved_path.relative_to(root)
        for raw_prefix in definition.allowed_paths:
            prefix = Path(raw_prefix)
            if str(prefix) == ".":
                return
            if relative == prefix or prefix in relative.parents:
                return
        raise PermissionError(
            f"path '{relative}' is not permitted for command '{definition.id}'"
        )

    @staticmethod
    def _enforce_output_cap(
        completed: subprocess.CompletedProcess[str],
        definition: CommandDefinition,
    ) -> None:
        max_bytes = definition.max_output_kb * 1024
        stdout_bytes = len((completed.stdout or "").encode("utf-8"))
        stderr_bytes = len((completed.stderr or "").encode("utf-8"))
        if stdout_bytes + stderr_bytes > max_bytes:
            raise RuntimeError(
                f"command '{definition.id}' exceeded max_output_kb={definition.max_output_kb}"
            )
