"""Git utilities for audit infrastructure."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]


def run_git(args: list[str], cwd: Path | None = None) -> str:
    """Run a git command and return stdout.

    Raises RuntimeError on git failure so callers do not fabricate fallback
    results from invalid refs or broken repositories.
    """
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd or REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or e.stdout or "").strip()
        command = "git " + " ".join(args)
        message = f"{command} failed with exit code {e.returncode}"
        if stderr:
            message = f"{message}: {stderr}"
        raise RuntimeError(message) from e
    except FileNotFoundError:
        raise RuntimeError("git executable not found")


def get_changed_files(base: str = "main", head: str = "HEAD") -> list[str]:
    """Get list of files changed between base and head."""
    output = run_git(["diff", "--name-only", f"{base}...{head}"])
    files = [f.strip() for f in output.split("\n") if f.strip()]
    return files


def get_current_branch() -> str:
    """Get current git branch."""
    branch = run_git(["branch", "--show-current"]).strip()
    if not branch:
        # Detached HEAD
        head = run_git(["rev-parse", "--short", "HEAD"]).strip()
        return f"detached-{head}"
    return branch


def get_subsystems_touched(
    files: list[str], config: Any | None = None
) -> dict[str, dict[str, Any]]:
    """Classify changed files by subsystem."""
    from scripts.audit.lib.config import AuditConfig

    cfg = config or AuditConfig.from_file()
    buckets: dict[str, dict[str, Any]] = {}

    for file_path in files:
        subsystem = cfg.get_subsystem_for_path(file_path)
        if subsystem:
            if subsystem not in buckets:
                buckets[subsystem] = {"count": 0, "files": []}
            if file_path not in buckets[subsystem]["files"]:
                buckets[subsystem]["files"].append(file_path)
                buckets[subsystem]["count"] += 1
        else:
            # Unknown subsystem
            if "unknown" not in buckets:
                buckets["unknown"] = {"count": 0, "files": []}
            buckets["unknown"]["files"].append(file_path)
            buckets["unknown"]["count"] += 1

    return buckets


def classify_path(path: str, config: Any | None = None) -> str:
    """Classify a single path by subsystem."""
    from scripts.audit.lib.config import AuditConfig

    cfg = config or AuditConfig.from_file()
    return cfg.get_subsystem_for_path(path) or "unknown"


def is_test_file(path: str, config: Any | None = None) -> bool:
    """Check if path is a test file."""
    from scripts.audit.lib.config import AuditConfig

    cfg = config or AuditConfig.from_file()
    return cfg.is_test_file(path)


def is_migration_file(path: str, config: Any | None = None) -> bool:
    """Check if path is a migration file."""
    from scripts.audit.lib.config import AuditConfig

    cfg = config or AuditConfig.from_file()
    return cfg.is_migration_file(path)


def is_high_blast_radius(path: str, config: Any | None = None) -> bool:
    """Check if path is high blast radius."""
    from scripts.audit.lib.config import AuditConfig

    cfg = config or AuditConfig.from_file()
    return cfg.is_high_blast_radius(path)


def check_tests_touched(
    files: list[str], config: Any | None = None
) -> tuple[bool, list[str]]:
    """Check if any tests were touched for the given files."""
    tests: list[str] = []
    for f in files:
        if is_test_file(f, config):
            tests.append(f)
    return len(tests) > 0, tests


def check_migrations_present(
    files: list[str], config: Any | None = None
) -> tuple[bool, list[str]]:
    """Check if any migration files are present."""
    migrations: list[str] = []
    for f in files:
        if is_migration_file(f, config):
            migrations.append(f)
    return len(migrations) > 0, migrations


def check_risky_files_changed(
    files: list[str], config: Any | None = None
) -> tuple[bool, list[str]]:
    """Check if any high blast radius files were changed."""
    risky: list[str] = []
    for f in files:
        if is_high_blast_radius(f, config):
            risky.append(f)
    return len(risky) > 0, risky
