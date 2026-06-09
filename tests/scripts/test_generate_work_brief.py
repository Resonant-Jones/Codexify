from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts/guardian/generate_work_brief.py"
EXPECTED_FILES = [
    "axis-brief.md",
    "codex-next-task-packet.md",
    "truth-ledger.md",
    "decision-log.md",
]


def run(command: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> str:
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    return completed.stdout


def write_architecture_docs(repo: Path) -> None:
    architecture = repo / "docs/architecture"
    (architecture / "adr").mkdir(parents=True)
    (architecture / "00-current-state.md").write_text(
        """## Last updated
2026-06-08

## Current phase
Codexify remains local-first beta hardening on `main`.

## Current supported reality
- Local Docker Compose remains the supported install path.
- Chat completion works only when separately proven.

## Not yet true / do not assume
- Do not assume cloud-provider beta support.
- Do not assume delegation or federation are release-supported.

## Active blockers
- Queue-coupled chat still depends on Redis plus worker health.
- Federation remains a high-blast-radius area.
""",
        encoding="utf-8",
    )
    (architecture / "README.md").write_text(
        "# Codexify Architecture KB\n\nStart with `00-current-state.md`.\n",
        encoding="utf-8",
    )
    (architecture / "agent-protocol-operations.md").write_text(
        "# Agent Protocol Operations Index\n",
        encoding="utf-8",
    )
    (architecture / "config-and-ops.md").write_text(
        "# Config and Ops\n",
        encoding="utf-8",
    )
    (architecture / "adr/adr-index.md").write_text("# ADR Index\n", encoding="utf-8")


def init_temp_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    git = shutil.which("git")
    assert git

    run([git, "init", "-b", "main"], cwd=repo)
    run([git, "config", "user.email", "guardian@example.test"], cwd=repo)
    run([git, "config", "user.name", "Guardian Test"], cwd=repo)
    write_architecture_docs(repo)
    run([git, "add", "."], cwd=repo)
    run([git, "commit", "-m", "seed architecture docs"], cwd=repo)

    remote = tmp_path / "remote.git"
    run([git, "init", "--bare", str(remote)], cwd=tmp_path)
    run([git, "remote", "add", "origin", str(remote)], cwd=repo)
    run([git, "push", "-u", "origin", "main"], cwd=repo)

    (repo / "scratch.md").write_text("dirty state\n", encoding="utf-8")
    return repo


def env_for(repo: Path, date: str, extra: dict[str, str] | None = None) -> dict[str, str]:
    env = os.environ.copy()
    env["GUARDIAN_BRIEF_REPO_ROOT"] = str(repo)
    env["GUARDIAN_BRIEF_DATE"] = date
    if extra:
        env.update(extra)
    return env


def test_generator_creates_expected_files_and_reports_repo_state(tmp_path: Path) -> None:
    repo = init_temp_repo(tmp_path)

    stdout = run(
        [sys.executable, str(SCRIPT)],
        cwd=repo,
        env=env_for(repo, "2026-06-08"),
    )

    output_dir = repo / "docs/guardian/work-briefs/2026-06-08"
    assert sorted(path.name for path in output_dir.iterdir()) == sorted(EXPECTED_FILES)
    for filename in EXPECTED_FILES:
        assert f"docs/guardian/work-briefs/2026-06-08/{filename}" in stdout

    combined = "\n".join((output_dir / filename).read_text() for filename in EXPECTED_FILES)
    assert "Branch: `main`" in combined
    assert "HEAD:" in combined or "Head:" in combined
    assert "Upstream:" in combined
    assert "git status --short --branch --untracked-files=all" in combined
    assert "?? scratch.md" in combined
    assert "`docs/architecture/00-current-state.md`: present" in combined
    assert "`docs/architecture/adr/ADR Index.md`: missing" in combined
    assert "`docs/architecture/adr/adr-index.md`: present" in combined


def test_generated_files_keep_no_runtime_proof_boundary(tmp_path: Path) -> None:
    repo = init_temp_repo(tmp_path)

    run([sys.executable, str(SCRIPT)], cwd=repo, env=env_for(repo, "2026-06-08"))

    output_dir = repo / "docs/guardian/work-briefs/2026-06-08"
    combined = "\n".join((output_dir / filename).read_text() for filename in EXPECTED_FILES)
    assert "Runtime paths were not re-proven by this generator." in combined
    assert "No backend runtime path was exercised." in combined
    assert "Code-Path Only / Not Re-Proven Today" in combined
    assert "No release claim expansion" in combined
    assert "runtime proof was rerun" not in combined.lower()
    assert "runtime proof was re-run" not in combined.lower()


def test_generator_does_not_require_forbidden_commands(tmp_path: Path) -> None:
    repo = init_temp_repo(tmp_path)
    real_git = shutil.which("git")
    assert real_git
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log_path = tmp_path / "commands.log"
    fake_git = bin_dir / "git"
    fake_git.write_text(
        f"""#!/bin/sh
printf '%s\\n' "$*" >> "{log_path}"
exec "{real_git}" "$@"
""",
        encoding="utf-8",
    )
    fake_git.chmod(0o755)

    env = env_for(repo, "2026-06-08", {"PATH": str(bin_dir)})
    run([sys.executable, str(SCRIPT)], cwd=repo, env=env)

    commands = log_path.read_text(encoding="utf-8")
    assert "rev-parse" in commands
    forbidden = [
        "docker",
        "backend",
        "frontend",
        "redis",
        "postgres",
        "worker",
        "provider",
        "marketing",
        "audit",
        "heartbeat",
        "public-export",
        "make",
    ]
    for command in forbidden:
        assert command not in commands


def test_environment_date_override_and_repeat_run_are_idempotent_enough(
    tmp_path: Path,
) -> None:
    repo = init_temp_repo(tmp_path)
    env = env_for(repo, "2026-06-09")

    run([sys.executable, str(SCRIPT)], cwd=repo, env=env)
    run([sys.executable, str(SCRIPT)], cwd=repo, env=env)

    output_dir = repo / "docs/guardian/work-briefs/2026-06-09"
    assert sorted(path.name for path in output_dir.iterdir()) == sorted(EXPECTED_FILES)
    assert (output_dir / "axis-brief.md").read_text(encoding="utf-8").startswith(
        "# Guardian Work Brief - Axis Brief - 2026-06-09"
    )
