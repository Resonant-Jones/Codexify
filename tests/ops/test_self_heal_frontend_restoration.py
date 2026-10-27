"""Behavioral regression tests for ``scripts/dev/self_heal_frontend.sh``.

The self-heal script restores the canonical dependency artifacts from a Git
revision. Two failure modes make that dangerous, and both are exercised here
against an isolated fixture:

* **Git LFS can hand back an unresolved pointer.** ``git lfs smudge`` copies
  the pointer to stdout unchanged and still exits zero when
  ``GIT_LFS_SKIP_SMUDGE=1`` is set, and a failed download can leave partial
  output behind. A non-empty result is therefore *not* evidence that the
  object was materialized, and accepting it overwrites a manifest with
  unusable content while reporting a successful recovery.
* **A failed frozen install used to fall back to a mutable install.**
  ``pnpm install`` can rewrite the canonical root lockfile, so dependency
  resolution could change during an operation whose whole purpose was to
  restore the existing state.

The fixture is a plain directory tree plus ``git``/``pnpm`` test doubles, so
the repository's own manifests are never read or written by these tests.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "dev" / "self_heal_frontend.sh"

LFS_POINTER = (
    "version https://git-lfs.github.com/spec/v1\n"
    "oid sha256:" + ("1" * 64) + "\n"
    "size 42\n"
)

MANIFEST = json.dumps({"name": "guardian-monorepo", "private": True}, indent=2) + "\n"
WORKSPACE = "packages:\n  - frontend/src\n  - edge/cloudflare-worker\n"
LOCKFILE = (
    "lockfileVersion: '9.0'\n"
    "\n"
    "settings:\n"
    "  autoInstallPeers: true\n"
    "\n"
    "importers:\n"
    "  .: {}\n"
    "\n"
    "packages: {}\n"
    "\n"
    "snapshots: {}\n"
)

# The artifacts the script is responsible for, and the validation kind each
# one is held to.
JSON_ARTIFACTS = ("package.json", "frontend/src/package.json", "frontend/package.json")
YAML_ARTIFACTS = ("pnpm-workspace.yaml", "pnpm-lock.yaml")

GIT_DOUBLE = """#!/usr/bin/env bash
# Test double for git. Emulates only the invocations the self-heal script
# makes: rev-parse --show-toplevel, show <ref>:<path>, lfs smudge, lfs pull.
set -u

FIXTURE="${SELF_HEAL_FIXTURE:?}"
LOG="${SELF_HEAL_GIT_LOG:?}"

printf '%s\\n' "$*" >> "$LOG"

case "${1:-}" in
  rev-parse)
    printf '%s\\n' "$FIXTURE"
    exit 0
    ;;
  show)
    target="${2##*:}"
    if [ -f "$FIXTURE/tracked/$target" ]; then
      cat "$FIXTURE/tracked/$target"
      exit 0
    fi
    echo "fatal: path '$target' does not exist in 'origin/main'" >&2
    exit 1
    ;;
  lfs)
    shift
    case "${1:-}" in
      smudge)
        pointer="$(cat)"
        if [ "${GIT_LFS_SKIP_SMUDGE:-0}" = "1" ]; then
          # git-lfs passes skipped pointers through unchanged and exits zero.
          printf '%s' "$pointer"
          exit 0
        fi
        case "${SELF_HEAL_LFS_MODE:-content}" in
          content)
            cat "$FIXTURE/lfs/content.json"
            exit 0
            ;;
          pointer)
            printf '%s' "$pointer"
            exit 0
            ;;
          fail)
            echo "git-lfs: failed to retrieve object" >&2
            exit 1
            ;;
          truncated)
            # Half a manifest, then a failure.
            head -c 12 "$FIXTURE/lfs/content.json"
            exit 1
            ;;
          exit_failure)
            # Syntactically valid content, but the command failed.
            cat "$FIXTURE/lfs/content.json"
            exit 1
            ;;
          malformed)
            printf '{"name": "broken",,}\\n'
            exit 0
            ;;
          empty)
            exit 0
            ;;
        esac
        exit 0
        ;;
      pull)
        exit "${SELF_HEAL_LFS_PULL_EXIT:-0}"
        ;;
    esac
    exit 0
    ;;
esac
exit 0
"""

PNPM_DOUBLE = """#!/usr/bin/env bash
# Test double for pnpm. Records every invocation so the tests can assert that
# no mutable install was ever attempted.
set -u

printf '%s\\n' "$*" >> "${SELF_HEAL_PNPM_LOG:?}"
exit "${SELF_HEAL_PNPM_EXIT:-0}"
"""


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class Fixture:
    """An isolated repository-shaped directory the self-heal script can run in."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.bin = root / "bin"
        self.bin.mkdir(parents=True, exist_ok=True)
        _write(self.bin / "git", GIT_DOUBLE)
        _write(self.bin / "pnpm", PNPM_DOUBLE)
        os.chmod(self.bin / "git", 0o755)
        os.chmod(self.bin / "pnpm", 0o755)
        # A directory that shadows only pnpm, so the real git and the real
        # git-lfs can be exercised against a genuine repository.
        self.pnpm_bin = root / "pnpmbin"
        self.pnpm_bin.mkdir(parents=True, exist_ok=True)
        _write(self.pnpm_bin / "pnpm", PNPM_DOUBLE)
        os.chmod(self.pnpm_bin / "pnpm", 0o755)
        self.git_log = root / "git.log"
        self.pnpm_log = root / "pnpm.log"
        self.git_log.touch()
        self.pnpm_log.touch()

    # -- fixture construction ------------------------------------------------

    def tracked(self, relative_path: str, content: str) -> None:
        """Set the content `git show origin/main:<path>` will return."""
        _write(self.root / "tracked" / relative_path, content)

    def lfs_content(self, content: str) -> None:
        """Set the content a successful `git lfs smudge` will materialize."""
        _write(self.root / "lfs" / "content.json", content)

    def on_disk(self, relative_path: str, content: str) -> None:
        """Set the current (possibly damaged) state of a working-tree file."""
        _write(self.root / relative_path, content)

    def read(self, relative_path: str) -> str:
        return (self.root / relative_path).read_text(encoding="utf-8")

    def bytes_of(self, relative_path: str) -> bytes:
        return (self.root / relative_path).read_bytes()

    # -- execution -----------------------------------------------------------

    def run(
        self,
        env_overrides: dict[str, str] | None = None,
        *,
        real_git: bool = False,
    ) -> subprocess.CompletedProcess:
        env = os.environ.copy()
        prefix = self.pnpm_bin if real_git else self.bin
        env["PATH"] = f"{prefix}{os.pathsep}{env['PATH']}"
        env["SELF_HEAL_FIXTURE"] = str(self.root)
        env["SELF_HEAL_GIT_LOG"] = str(self.git_log)
        env["SELF_HEAL_PNPM_LOG"] = str(self.pnpm_log)
        env["SELF_HEAL_BASE_REF"] = "origin/main"
        env.pop("GIT_LFS_SKIP_SMUDGE", None)
        if env_overrides:
            env.update(env_overrides)
        return subprocess.run(
            ["bash", str(SCRIPT)],
            cwd=str(self.root),
            env=env,
            text=True,
            capture_output=True,
        )

    def pnpm_invocations(self) -> list[str]:
        return [line for line in self.pnpm_log.read_text(encoding="utf-8").splitlines() if line]

    def leftover_temp_files(self) -> list[str]:
        return [
            str(path.relative_to(self.root))
            for path in self.root.rglob("*.heal.*")
            if path.is_file()
        ]


@pytest.fixture
def fixture(tmp_path: Path) -> Fixture:
    """A healthy canonical tree whose JSON manifests are damaged LFS pointers."""
    built = Fixture(tmp_path / "repo")

    # The base revision tracks the JSON manifests through Git LFS.
    for artifact in JSON_ARTIFACTS:
        built.tracked(artifact, LFS_POINTER)
    built.tracked("pnpm-workspace.yaml", WORKSPACE)
    built.tracked("pnpm-lock.yaml", LOCKFILE)
    built.lfs_content(MANIFEST)

    # The working tree is damaged: the manifests hold unresolved pointers.
    for artifact in JSON_ARTIFACTS:
        built.on_disk(artifact, LFS_POINTER)
    built.on_disk("pnpm-workspace.yaml", WORKSPACE)
    built.on_disk("pnpm-lock.yaml", LOCKFILE)

    return built


def test_valid_lfs_materialization_is_restored_validated_and_installed(fixture: Fixture) -> None:
    result = fixture.run({"SELF_HEAL_LFS_MODE": "content"})

    assert result.returncode == 0, result.stderr
    for artifact in JSON_ARTIFACTS:
        assert fixture.read(artifact) == MANIFEST
        assert "git-lfs.github.com/spec/v1" not in fixture.read(artifact)
    assert fixture.pnpm_invocations() == ["install --frozen-lockfile"]
    assert fixture.leftover_temp_files() == []


def test_skip_smudge_pointer_is_rejected_and_destination_preserved(fixture: Fixture) -> None:
    before = {artifact: fixture.bytes_of(artifact) for artifact in JSON_ARTIFACTS}

    result = fixture.run({"SELF_HEAL_LFS_MODE": "content", "GIT_LFS_SKIP_SMUDGE": "1"})

    assert result.returncode != 0
    assert "package.json" in result.stderr
    for artifact in JSON_ARTIFACTS:
        assert fixture.bytes_of(artifact) == before[artifact]
    assert fixture.pnpm_invocations() == []
    assert fixture.leftover_temp_files() == []


def test_lfs_retrieval_failure_preserves_destination_and_skips_install(fixture: Fixture) -> None:
    before = {artifact: fixture.bytes_of(artifact) for artifact in JSON_ARTIFACTS}

    result = fixture.run({"SELF_HEAL_LFS_MODE": "fail"})

    assert result.returncode != 0
    for artifact in JSON_ARTIFACTS:
        assert fixture.bytes_of(artifact) == before[artifact]
    assert fixture.pnpm_invocations() == []


def test_smudge_failure_after_writing_output_is_rejected(fixture: Fixture) -> None:
    """Valid content plus a failing exit status must not be accepted."""
    before = {artifact: fixture.bytes_of(artifact) for artifact in JSON_ARTIFACTS}

    result = fixture.run({"SELF_HEAL_LFS_MODE": "exit_failure"})

    assert result.returncode != 0
    for artifact in JSON_ARTIFACTS:
        assert fixture.bytes_of(artifact) == before[artifact]
    assert fixture.pnpm_invocations() == []


def test_truncated_smudge_output_is_rejected(fixture: Fixture) -> None:
    before = {artifact: fixture.bytes_of(artifact) for artifact in JSON_ARTIFACTS}

    result = fixture.run({"SELF_HEAL_LFS_MODE": "truncated"})

    assert result.returncode != 0
    for artifact in JSON_ARTIFACTS:
        assert fixture.bytes_of(artifact) == before[artifact]
    assert fixture.pnpm_invocations() == []


def test_malformed_json_is_rejected_before_replacement(fixture: Fixture) -> None:
    before = {artifact: fixture.bytes_of(artifact) for artifact in JSON_ARTIFACTS}

    result = fixture.run({"SELF_HEAL_LFS_MODE": "malformed"})

    assert result.returncode != 0
    for artifact in JSON_ARTIFACTS:
        assert fixture.bytes_of(artifact) == before[artifact]
        assert "broken" not in fixture.read(artifact)
    assert fixture.pnpm_invocations() == []


def test_empty_smudge_output_is_rejected(fixture: Fixture) -> None:
    before = {artifact: fixture.bytes_of(artifact) for artifact in JSON_ARTIFACTS}

    result = fixture.run({"SELF_HEAL_LFS_MODE": "empty"})

    assert result.returncode != 0
    for artifact in JSON_ARTIFACTS:
        assert fixture.bytes_of(artifact) == before[artifact]
    assert fixture.pnpm_invocations() == []


def test_valid_json_is_restored_when_not_tracked_through_lfs(fixture: Fixture) -> None:
    """A manifest that is not LFS-tracked is validated and restored directly."""
    plain = json.dumps({"name": "guardian-monorepo", "version": "1.0.0"}, indent=2) + "\n"
    fixture.tracked("frontend/package.json", plain)
    fixture.on_disk("frontend/package.json", "{ this is not json")
    before = fixture.bytes_of("frontend/package.json")

    result = fixture.run({"SELF_HEAL_LFS_MODE": "content"})

    assert result.returncode == 0, result.stderr
    assert fixture.read("frontend/package.json") == plain
    assert fixture.bytes_of("frontend/package.json") != before
    assert fixture.pnpm_invocations() == ["install --frozen-lockfile"]


def test_restoration_preserves_destination_permission_bits(fixture: Fixture) -> None:
    fixture.on_disk("frontend/package.json", LFS_POINTER)
    os.chmod(fixture.root / "frontend" / "package.json", 0o644)

    result = fixture.run({"SELF_HEAL_LFS_MODE": "content"})

    assert result.returncode == 0, result.stderr
    mode = (fixture.root / "frontend" / "package.json").stat().st_mode & 0o777
    assert mode == 0o644


def test_frozen_install_failure_does_not_fall_back_to_a_mutable_install(fixture: Fixture) -> None:
    lockfile_before = fixture.bytes_of("pnpm-lock.yaml")

    result = fixture.run({"SELF_HEAL_LFS_MODE": "content", "SELF_HEAL_PNPM_EXIT": "1"})

    assert result.returncode != 0
    invocations = fixture.pnpm_invocations()
    assert invocations == ["install --frozen-lockfile"]
    # No mutable install may have been attempted.
    assert "install" not in invocations
    assert fixture.bytes_of("pnpm-lock.yaml") == lockfile_before


def test_failed_recovery_never_starts_package_installation(fixture: Fixture) -> None:
    result = fixture.run({"SELF_HEAL_LFS_MODE": "fail"})

    assert result.returncode != 0
    assert fixture.pnpm_invocations() == []
    assert "Self-heal aborted" in result.stderr


def test_damaged_canonical_lockfile_is_healed_from_the_base_ref(fixture: Fixture) -> None:
    """The root lockfile is the only lockfile, and self-heal must heal it."""
    fixture.on_disk("pnpm-lock.yaml", "lockfileVersion: '9.0'\nimporters:\n  .: {}\nBROKEN")

    result = fixture.run({"SELF_HEAL_LFS_MODE": "content"})

    assert result.returncode == 0, result.stderr
    assert fixture.read("pnpm-lock.yaml") == LOCKFILE
    assert fixture.pnpm_invocations() == ["install --frozen-lockfile"]


def test_structurally_invalid_lockfile_is_rejected_and_preserved(fixture: Fixture) -> None:
    fixture.tracked("pnpm-lock.yaml", "this is not a pnpm lockfile\n")
    fixture.on_disk("pnpm-lock.yaml", "lockfileVersion: '9.0'\nimporters:\n  .: {}\nBROKEN")
    before = fixture.bytes_of("pnpm-lock.yaml")

    result = fixture.run({"SELF_HEAL_LFS_MODE": "content"})

    assert result.returncode != 0
    assert fixture.bytes_of("pnpm-lock.yaml") == before
    assert fixture.pnpm_invocations() == []


@pytest.mark.skipif(shutil.which("git-lfs") is None, reason="git-lfs is not installed")
def test_real_git_lfs_skip_smudge_pointer_is_rejected(tmp_path: Path) -> None:
    """The reported finding, proven against the real tool rather than a double.

    git-lfs copies a skipped pointer to stdout unchanged and still exits zero,
    so a restoration that trusts a non-empty result installs the pointer over a
    manifest and reports a successful recovery.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "."], cwd=repo, check=True)
    subprocess.run(
        ["git", "config", "user.email", "self-heal@example.invalid"], cwd=repo, check=True
    )
    subprocess.run(["git", "config", "user.name", "Self Heal Test"], cwd=repo, check=True)

    for relative_path, content in {
        "package.json": LFS_POINTER,
        "pnpm-workspace.yaml": WORKSPACE,
        "frontend/src/package.json": LFS_POINTER,
        "frontend/package.json": LFS_POINTER,
        "pnpm-lock.yaml": LOCKFILE,
    }.items():
        _write(repo / relative_path, content)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "fixture"], cwd=repo, check=True)
    subprocess.run(["git", "update-ref", "refs/remotes/origin/main", "HEAD"], cwd=repo, check=True)

    # The working tree holds unresolved pointers, exactly as a damaged checkout
    # would.
    for artifact in JSON_ARTIFACTS:
        _write(repo / artifact, LFS_POINTER)
    before = {artifact: (repo / artifact).read_bytes() for artifact in JSON_ARTIFACTS}

    # Premise: real git-lfs, pointer passed through unchanged, exit zero.
    smudge_env = os.environ.copy()
    smudge_env["GIT_LFS_SKIP_SMUDGE"] = "1"
    smudge = subprocess.run(
        ["git", "lfs", "smudge"],
        input=LFS_POINTER,
        text=True,
        capture_output=True,
        cwd=repo,
        env=smudge_env,
    )
    assert smudge.returncode == 0, smudge.stderr
    assert "git-lfs.github.com/spec/v1" in smudge.stdout

    # The script must reject that output and leave the destination untouched.
    pnpm_bin = tmp_path / "pnpmbin"
    pnpm_bin.mkdir()
    _write(pnpm_bin / "pnpm", PNPM_DOUBLE)
    os.chmod(pnpm_bin / "pnpm", 0o755)
    pnpm_log = tmp_path / "pnpm.log"
    pnpm_log.touch()

    run_env = os.environ.copy()
    run_env["PATH"] = f"{pnpm_bin}{os.pathsep}{run_env['PATH']}"
    run_env["GIT_LFS_SKIP_SMUDGE"] = "1"
    run_env["SELF_HEAL_PNPM_LOG"] = str(pnpm_log)
    run_env["SELF_HEAL_BASE_REF"] = "origin/main"

    result = subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=str(repo),
        env=run_env,
        text=True,
        capture_output=True,
    )

    assert result.returncode != 0
    for artifact in JSON_ARTIFACTS:
        assert (repo / artifact).read_bytes() == before[artifact]
    assert pnpm_log.read_text(encoding="utf-8").strip() == ""
