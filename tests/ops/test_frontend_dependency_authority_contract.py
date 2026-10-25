"""Contract: the root pnpm workspace is the single dependency installation root.

`frontend/` used to look like a second install root: it carried its own
`package.json` dependency list, a `frontend/.npmrc` that pinned
`lockfile-dir=.`, a `frontend/pnpm-lock.yaml`, and two npm lockfiles. None of
those were ever part of the pnpm workspace, so they drifted away from the
canonical root lockfile and every consumer that reached for them was reading
stale dependency truth.

These tests pin the retirement: one install root, one lockfile, and live
consumers that say so out loud.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
SELF = Path(__file__).resolve()

# Lockfiles and install-root shims that must not come back.
RETIRED_PATHS = (
    "frontend/pnpm-lock.yaml",
    "frontend/package-lock.json",
    "frontend/src/package-lock.json",
    "frontend/.npmrc",
)

# Dependencies that were declared on the retired `frontend/package.json` and
# now belong to the application manifest.
MOVED_DEPENDENCIES = ("@heroicons/react", "@radix-ui/react-visually-hidden")
MOVED_DEV_DEPENDENCIES = (
    "@google/gemini-cli",
    "@tailwindcss/cli",
    "@types/lodash-es",
    "@types/react",
    "@types/react-dom",
    "cypress",
    "postcss",
    "typescript",
)

# Live consumer surfaces. Historical records under docs/ and codex_tasks/ are
# deliberately excluded: they describe the past and are not consumers.
CONSUMER_GLOBS = (
    ".github/workflows/*.yml",
    "scripts/**/*.sh",
    "tests/ops/*.py",
    "Makefile",
    "README.md",
    "GEMINI.md",
    "SETUP_INSTRUCTIONS.md",
    "package.json",
    "docker-compose*.yml",
    "frontend/Dockerfile*",
)


def _manifest(relative_path: str) -> dict:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def _tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files"],
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout.splitlines()


def _lockfile() -> dict:
    return yaml.safe_load((ROOT / "pnpm-lock.yaml").read_text(encoding="utf-8"))


def test_frontend_is_not_a_pnpm_workspace_member() -> None:
    workspace = (ROOT / "pnpm-workspace.yaml").read_text(encoding="utf-8")

    assert "frontend/src" in workspace
    assert "edge/cloudflare-worker" in workspace
    # `frontend` itself must never become a workspace member: a member gets its
    # own importer and its own dependency installation.
    members = re.findall(r"^\s+-\s+(\S+)\s*$", workspace, flags=re.MULTILINE)
    assert "frontend" not in members
    assert "frontend/src" in members
    assert "edge/cloudflare-worker" in members


def test_retired_frontend_lockfiles_are_not_tracked() -> None:
    tracked = set(_tracked_files())
    for relative_path in RETIRED_PATHS:
        assert relative_path not in tracked, f"{relative_path} must not be tracked by git"


def test_frontend_manifest_is_a_script_hub_without_dependencies() -> None:
    manifest = _manifest("frontend/package.json")

    assert "scripts" in manifest
    assert "dependencies" not in manifest
    assert "devDependencies" not in manifest
    assert manifest.get("private") is True


def test_application_manifest_owns_the_moved_dependencies() -> None:
    manifest = _manifest("frontend/src/package.json")

    dependencies = manifest.get("dependencies", {})
    dev_dependencies = manifest.get("devDependencies", {})

    for name in MOVED_DEPENDENCIES:
        assert name in dependencies, f"{name} must be declared by frontend/src/package.json"
    for name in MOVED_DEV_DEPENDENCIES:
        assert name in dev_dependencies, f"{name} must be declared by frontend/src/package.json"


def test_root_lockfile_has_one_frontend_importer() -> None:
    lock = _lockfile()
    importers = lock["importers"]

    assert "frontend/src" in importers
    # The stale top-level `frontend:` importer is what kept the secondary
    # lockfile alive. It must not return.
    assert "frontend" not in importers

    importer = importers["frontend/src"]
    declared = set(importer.get("dependencies", {})) | set(importer.get("devDependencies", {}))
    for name in MOVED_DEPENDENCIES + MOVED_DEV_DEPENDENCIES:
        assert name in declared, f"{name} must be in the frontend/src importer"


def test_frontend_src_importer_matches_the_application_manifest() -> None:
    lock = _lockfile()
    importer = lock["importers"]["frontend/src"]
    manifest = _manifest("frontend/src/package.json")
    snapshots = lock.get("snapshots", {})

    for section in ("dependencies", "devDependencies"):
        declared = manifest.get(section, {}) or {}
        locked = importer.get(section, {}) or {}
        for name, specifier in declared.items():
            assert name in locked, f"{name} is declared but absent from the lockfile importer"
            assert locked[name]["specifier"] == specifier, (
                f"{name} specifier drifted: manifest={specifier!r} "
                f"lockfile={locked[name]['specifier']!r}"
            )
            version = locked[name]["version"]
            assert f"{name}@{version}" in snapshots, f"{name}@{version} missing from snapshots"


def test_no_live_consumer_references_the_retired_lockfiles() -> None:
    tracked = set(_tracked_files())
    offenders: list[str] = []

    for pattern in CONSUMER_GLOBS:
        for relative_path in sorted(tracked):
            if not relative_path or not Path(relative_path).match(pattern):
                continue
            if (ROOT / relative_path).resolve() == SELF:
                continue
            text = (ROOT / relative_path).read_text(encoding="utf-8", errors="ignore")
            for retired in RETIRED_PATHS:
                if retired in text:
                    offenders.append(f"{relative_path} references {retired}")

    assert not offenders, "Retired install-root artifacts are still referenced: " + "; ".join(offenders)


def test_self_heal_is_covered_by_the_live_consumer_scan() -> None:
    """The self-heal script restores canonical artifacts; it must stay scanned.

    It is the script that rebuilds the canonical manifests and lockfile, so
    it must not be able to drift back to the retired install root without the
    live-consumer scan noticing.
    """
    script = "scripts/dev/self_heal_frontend.sh"

    assert script in set(_tracked_files())
    assert any(Path(script).match(pattern) for pattern in CONSUMER_GLOBS)


def test_typecheck_script_covers_application_source() -> None:
    app_manifest = _manifest("frontend/src/package.json")
    root_manifest = _manifest("package.json")

    app_typecheck = app_manifest["scripts"]["typecheck"]
    assert "tsconfig.app.json" in app_typecheck, "Application source must be typechecked"
    assert "tsconfig.json" in app_typecheck, "Configuration checks must be preserved"

    assert "typecheck" in root_manifest["scripts"]
    assert root_manifest["scripts"]["typecheck"] == "pnpm --dir frontend typecheck"
