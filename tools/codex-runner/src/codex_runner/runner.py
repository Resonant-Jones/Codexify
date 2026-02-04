"""Codex Runner harness for generating campaigns and executing tasks."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterator

from importlib import resources

DEFAULT_CAMPAIGN_DIR = Path("docs/Campaign")
DEFAULT_TASKS_DIR = Path("docs/tasks")

CAMPAIGN_PATH_PATTERN = re.compile(
    r"^docs/Campaign/CAMPAIGN_\d{4}_\d{2}_\d{2}(?:_[A-Z0-9_+\-]+)?\.md$"
)
TASK_PATH_PATTERN = re.compile(
    r"^docs/tasks/TASK_\d{4}_\d{2}_\d{2}_\d{3}_[a-z0-9_]+\.md$"
)

CAMPAIGN_SCHEMA_RESOURCE = "resources/schemas/campaign_output.schema.json"
TASK_RESULT_SCHEMA_RESOURCE = "resources/schemas/task_result.schema.json"


class RunnerError(RuntimeError):
    """Raised when the Codex Runner encounters a fatal error."""


@dataclass(frozen=True)
class RunnerConfig:
    """Configuration for a Codex Runner invocation."""

    repo_root: Path
    audit_prompt_file: Path
    cycles: int = 1
    execute: bool = False
    dry_run: bool = False
    branch_per_campaign: bool = True
    no_verify: bool = True
    auto_commit: bool = True
    debug: bool = False
    campaign_schema_path: Path | None = None
    task_result_schema_path: Path | None = None


@dataclass(frozen=True)
class RunnerResources:
    """Resolved resource paths for the runner."""

    campaign_schema_path: Path
    task_result_schema_path: Path


def ensure_codex_available() -> None:
    """Ensure the Codex CLI is installed and on PATH."""
    if shutil.which("codex") is None:
        raise RunnerError(
            "codex executable not found on PATH. Install the Codex CLI "
            "and authenticate it before running codex-runner."
        )


def run_cmd(
    args: list[str],
    *,
    cwd: Path,
    capture_output: bool = False,
    debug: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Run a command, returning its completed process."""
    if debug:
        print(f"[debug] Running: {' '.join(args)} (cwd={cwd})", file=sys.stderr)
    try:
        result = subprocess.run(
            args,
            text=True,
            capture_output=capture_output,
            check=False,
            cwd=str(cwd),
        )
    except FileNotFoundError as exc:
        binary = args[0]
        if binary == "codex":
            raise RunnerError(
                "codex executable not found on PATH. Install the Codex CLI "
                "and authenticate it before running codex-runner."
            ) from exc
        if binary == "git":
            raise RunnerError(
                "git executable not found on PATH. Install Git to continue."
            ) from exc
        raise RunnerError(
            f"Required executable not found on PATH: {binary}"
        ) from exc

    if debug and capture_output:
        if result.stdout:
            print(f"[debug] stdout:\n{result.stdout}", file=sys.stderr)
        if result.stderr:
            print(f"[debug] stderr:\n{result.stderr}", file=sys.stderr)
    return result


def git_status_porcelain(repo_root: Path, debug: bool) -> str:
    """Return the porcelain git status for the repo."""
    result = run_cmd(
        ["git", "status", "--porcelain", "-uall"],
        capture_output=True,
        cwd=repo_root,
        debug=debug,
    )
    if result.returncode != 0:
        raise RunnerError(f"git status failed: {result.stderr.strip()}")
    return result.stdout


def git_is_clean(repo_root: Path, debug: bool) -> bool:
    """Return True when the git working tree is clean."""
    return git_status_porcelain(repo_root, debug).strip() == ""


def ensure_clean_git(context: str, repo_root: Path, debug: bool) -> None:
    """Ensure the git working tree is clean for a given context."""
    if not git_is_clean(repo_root, debug):
        raise RunnerError(
            f"git tree is not clean ({context}). Commit or stash changes."
        )


def parse_porcelain_paths(status: str) -> list[str]:
    """Parse git porcelain status output into a list of file paths."""
    paths: list[str] = []
    for line in status.splitlines():
        if not line:
            continue
        entry = line[3:]
        if " -> " in entry:
            entry = entry.split(" -> ", 1)[1]
        paths.append(entry)
    return paths


def read_json_file(path: Path) -> dict[str, Any]:
    """Load and parse a JSON file."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RunnerError(f"Expected output file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RunnerError(f"Invalid JSON in {path}: {exc}") from exc


def validate_campaign_payload(payload: dict[str, Any]) -> None:
    """Validate required campaign fields and path invariants."""
    required_fields = [
        "campaign_id",
        "campaign_slug",
        "campaign_doc_path",
        "campaign_markdown",
        "tasks",
    ]
    missing = [field for field in required_fields if field not in payload]
    if missing:
        raise RunnerError(f"Missing campaign fields: {', '.join(missing)}")

    campaign_path = payload["campaign_doc_path"]
    if not isinstance(
        campaign_path, str
    ) or not CAMPAIGN_PATH_PATTERN.fullmatch(campaign_path):
        raise RunnerError(
            "Invalid campaign_doc_path. Expected format "
            f"{DEFAULT_CAMPAIGN_DIR}/CAMPAIGN_YYYY_MM_DD[_SUFFIX].md"
        )

    tasks = payload["tasks"]
    if not isinstance(tasks, list):
        raise RunnerError("tasks must be an array")

    required_task_fields = [
        "id",
        "slug",
        "area",
        "files",
        "tests",
        "commit_message",
        "task_artifact_path",
        "task_artifact_markdown",
        "activation_prompt",
    ]

    for index, task in enumerate(tasks, start=1):
        if not isinstance(task, dict):
            raise RunnerError(f"Task {index} must be an object")
        missing_task_fields = [
            field for field in required_task_fields if field not in task
        ]
        if missing_task_fields:
            raise RunnerError(
                f"Task {index} missing fields: {', '.join(missing_task_fields)}"
            )
        task_path = task["task_artifact_path"]
        if not isinstance(task_path, str) or not TASK_PATH_PATTERN.fullmatch(
            task_path
        ):
            raise RunnerError(
                "Invalid task_artifact_path for task "
                f"{index}. Expected format {DEFAULT_TASKS_DIR}/"
                "TASK_YYYY_MM_DD_NNN_lower_snake_slug.md"
            )


def write_text_file(path: Path, content: str) -> None:
    """Write text to a file, creating parents as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def append_text_file(path: Path, content: str) -> None:
    """Append text to a file, creating parents as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(content)


@contextmanager
def resource_path(override: Path | None, relative_path: str) -> Iterator[Path]:
    """Resolve packaged resources while allowing optional overrides."""
    if override is not None:
        yield override
        return
    # Keep the resource in scope for the lifetime of the caller.
    with resources.as_file(resources.files("codex_runner") / relative_path) as path:
        yield path


@contextmanager
def load_resources(config: RunnerConfig) -> Iterator[RunnerResources]:
    """Load packaged resources needed for the runner."""
    with ExitStack() as stack:
        campaign_schema = stack.enter_context(
            resource_path(config.campaign_schema_path, CAMPAIGN_SCHEMA_RESOURCE)
        )
        task_result_schema = stack.enter_context(
            resource_path(config.task_result_schema_path, TASK_RESULT_SCHEMA_RESOURCE)
        )
        yield RunnerResources(
            campaign_schema_path=campaign_schema,
            task_result_schema_path=task_result_schema,
        )


def run_codex_exec(
    prompt_file: Path,
    output_schema: Path,
    output_path: Path,
    *,
    repo_root: Path,
    debug: bool,
) -> None:
    """Invoke the Codex CLI to produce schema-validated output."""
    prompt_text = prompt_file.read_text(encoding="utf-8")
    result = run_cmd(
        [
            "codex",
            "exec",
            "--output-schema",
            str(output_schema),
            "-o",
            str(output_path),
            prompt_text,
        ],
        capture_output=True,
        cwd=repo_root,
        debug=debug,
    )
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        stdout = (result.stdout or "").strip()
        raise RunnerError(
            "codex exec failed"
            + (f"\nSTDERR:\n{stderr}" if stderr else "")
            + (f"\nSTDOUT:\n{stdout}" if stdout else "")
        )


def slugify_branch(value: str) -> str:
    """Normalize campaign slugs into git-friendly branch names."""
    slug = re.sub(r"[^a-z0-9_-]+", "-", value.strip().lower())
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    if not slug:
        raise RunnerError("campaign_slug must contain valid characters")
    return slug


def campaign_branch_name(campaign_slug: str) -> str:
    """Build the branch name for a campaign."""
    safe_slug = slugify_branch(campaign_slug)
    today = date.today().strftime("%Y-%m-%d")
    return f"campaign/{today}/{safe_slug}"


def switch_branch(branch_name: str, repo_root: Path, debug: bool) -> None:
    """Switch to (or create) the branch used for a campaign."""
    create_result = run_cmd(
        ["git", "switch", "-c", branch_name],
        capture_output=True,
        cwd=repo_root,
        debug=debug,
    )
    if create_result.returncode == 0:
        return
    switch_result = run_cmd(
        ["git", "switch", branch_name],
        capture_output=True,
        cwd=repo_root,
        debug=debug,
    )
    if switch_result.returncode != 0:
        raise RunnerError(
            f"Unable to switch to branch '{branch_name}': "
            f"{switch_result.stderr.strip()}"
        )


def git_head_commit(repo_root: Path, debug: bool) -> str:
    """Return the current HEAD commit hash."""
    result = run_cmd(
        ["git", "rev-parse", "HEAD"],
        capture_output=True,
        cwd=repo_root,
        debug=debug,
    )
    if result.returncode != 0:
        raise RunnerError(f"git rev-parse failed: {result.stderr.strip()}")
    return result.stdout.strip()


def git_commit(
    paths: list[str],
    message: str,
    no_verify: bool,
    repo_root: Path,
    debug: bool,
) -> str:
    """Commit the provided paths with a message."""
    if not paths:
        raise RunnerError("git_commit requires at least one path")
    add_result = run_cmd(
        ["git", "add", *paths],
        capture_output=True,
        cwd=repo_root,
        debug=debug,
    )
    if add_result.returncode != 0:
        raise RunnerError(f"git add failed: {add_result.stderr.strip()}")
    commit_cmd = ["git", "commit", "-m", message]
    if no_verify:
        commit_cmd.insert(2, "--no-verify")
    commit_result = run_cmd(
        commit_cmd, capture_output=True, cwd=repo_root, debug=debug
    )
    if commit_result.returncode != 0:
        raise RunnerError(f"git commit failed: {commit_result.stderr.strip()}")
    return git_head_commit(repo_root, debug)


def git_commit_all(
    message: str,
    no_verify: bool,
    repo_root: Path,
    debug: bool,
) -> str:
    """Commit all staged changes with a message."""
    add_result = run_cmd(
        ["git", "add", "-A"],
        capture_output=True,
        cwd=repo_root,
        debug=debug,
    )
    if add_result.returncode != 0:
        raise RunnerError(f"git add -A failed: {add_result.stderr.strip()}")
    commit_cmd = ["git", "commit", "-m", message]
    if no_verify:
        commit_cmd.insert(2, "--no-verify")
    commit_result = run_cmd(
        commit_cmd, capture_output=True, cwd=repo_root, debug=debug
    )
    if commit_result.returncode != 0:
        raise RunnerError(f"git commit failed: {commit_result.stderr.strip()}")
    return git_head_commit(repo_root, debug)


def ensure_repo_root(repo_root: Path, debug: bool) -> None:
    """Ensure the repo root exists and is a git repository."""
    if not repo_root.exists():
        raise RunnerError(f"repo root does not exist: {repo_root}")
    if not repo_root.is_dir():
        raise RunnerError(f"repo root is not a directory: {repo_root}")
    result = run_cmd(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        cwd=repo_root,
        debug=debug,
    )
    if result.returncode != 0:
        raise RunnerError(f"repo root is not a git repository: {repo_root}")
    top_level = Path(result.stdout.strip()).resolve()
    if top_level != repo_root.resolve():
        raise RunnerError(
            "repo root must be the repository root (git rev-parse --show-toplevel)."
        )


def execute_task(
    task: dict[str, Any],
    *,
    task_schema_path: Path,
    repo_root: Path,
    no_verify: bool,
    debug: bool,
) -> dict[str, Any]:
    """Execute a single task via the Codex CLI."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        prompt_path = tmp_path / "activation_prompt.md"
        output_path = tmp_path / "task_result.json"
        prompt_path.write_text(task["activation_prompt"], encoding="utf-8")
        run_codex_exec(
            prompt_path,
            task_schema_path,
            output_path,
            repo_root=repo_root,
            debug=debug,
        )
        result = read_json_file(output_path)

    status = result.get("status")
    if status == "success":
        head_commit = git_head_commit(repo_root, debug)
        commit_hash = (result.get("commit_hash") or "").strip()
        if not commit_hash:
            note = f"missing commit_hash: head is {head_commit}"
            existing_notes = (result.get("notes") or "").strip()
            result["notes"] = f"{existing_notes} {note}".strip()
            print(f"Warning: {note}", file=sys.stderr)
        elif commit_hash != head_commit:
            note = (
                "commit_hash mismatch: reported "
                f"{commit_hash}, head is {head_commit}"
            )
            existing_notes = (result.get("notes") or "").strip()
            result["notes"] = f"{existing_notes} {note}".strip()
            print(f"Warning: {note}", file=sys.stderr)
    return result


def run_cycle(config: RunnerConfig, resources: RunnerResources, cycle_index: int) -> None:
    """Run a single audit -> campaign -> task cycle."""
    ensure_clean_git("start of cycle", config.repo_root, config.debug)
    print(f"Starting cycle {cycle_index}...")
    print(
        "Note: concurrent campaigns in the same workdir will serialize in Git. "
        "Use separate clones/worktrees for true parallelism."
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        output_path = tmp_path / "campaign_output.json"
        run_codex_exec(
            config.audit_prompt_file,
            resources.campaign_schema_path,
            output_path,
            repo_root=config.repo_root,
            debug=config.debug,
        )
        payload = read_json_file(output_path)

    validate_campaign_payload(payload)

    if not config.branch_per_campaign:
        raise RunnerError("--branch-per-campaign is required for this runner.")

    campaign_slug = payload.get("campaign_slug", "")
    if not campaign_slug:
        raise RunnerError("campaign_slug is required for branch-per-campaign")
    if not git_is_clean(config.repo_root, config.debug):
        raise RunnerError(
            "git tree is not clean before switching campaign branch"
        )
    switch_branch(
        campaign_branch_name(campaign_slug),
        config.repo_root,
        config.debug,
    )
    ensure_clean_git("after switching campaign branch", config.repo_root, config.debug)

    campaign_doc_relative = payload["campaign_doc_path"]
    campaign_doc_path = config.repo_root / campaign_doc_relative
    write_text_file(campaign_doc_path, payload["campaign_markdown"])

    for task in payload["tasks"]:
        task_relative = task["task_artifact_path"]
        task_path = config.repo_root / task_relative
        write_text_file(task_path, task["task_artifact_markdown"])

    campaign_id = payload.get("campaign_id", "campaign")
    artifact_paths = [campaign_doc_relative] + [
        task["task_artifact_path"] for task in payload["tasks"]
    ]

    if config.auto_commit:
        git_commit(
            artifact_paths,
            f"Docs: add {campaign_id} campaign + tasks",
            config.no_verify,
            config.repo_root,
            config.debug,
        )
        ensure_clean_git("after campaign artifact commit", config.repo_root, config.debug)
    elif not git_is_clean(config.repo_root, config.debug):
        raise RunnerError(
            "Auto-commit disabled but campaign artifacts changed the tree."
        )

    if config.execute and not config.dry_run:
        for task in payload["tasks"]:
            ensure_clean_git("start of task", config.repo_root, config.debug)
            head_before = git_head_commit(config.repo_root, config.debug)
            print(f"Executing task {task.get('id', '')}...")
            result = execute_task(
                task,
                task_schema_path=resources.task_result_schema_path,
                repo_root=config.repo_root,
                no_verify=config.no_verify,
                debug=config.debug,
            )

            if not git_is_clean(config.repo_root, config.debug):
                if config.auto_commit:
                    git_commit_all(
                        task["commit_message"],
                        config.no_verify,
                        config.repo_root,
                        config.debug,
                    )
                else:
                    raise RunnerError(
                        "Auto-commit disabled but task left the tree dirty."
                    )

            ensure_clean_git("after task commit", config.repo_root, config.debug)
            head_after = git_head_commit(config.repo_root, config.debug)
            if head_after == head_before:
                # Task produced no changes/commit. For deterministic loops, record the
                # structured result into the task artifact and commit that receipt.
                if config.auto_commit and (result.get("status") == "success"):
                    task_artifact_path = config.repo_root / task["task_artifact_path"]
                    append_text_file(
                        task_artifact_path,
                        "\n\n## Runner Result\n\n```json\n"
                        + json.dumps(result, indent=2)
                        + "\n```\n",
                    )
                    git_commit(
                        [task["task_artifact_path"]],
                        task["commit_message"],
                        config.no_verify,
                        config.repo_root,
                        config.debug,
                    )
                    ensure_clean_git(
                        "after task receipt commit",
                        config.repo_root,
                        config.debug,
                    )
                    head_after = git_head_commit(
                        config.repo_root,
                        config.debug,
                    )
                else:
                    raise RunnerError(
                        f"Task {task.get('id', '')} produced no commit."
                    )
    elif config.execute and config.dry_run:
        print("Dry run enabled: skipping task execution.")

    status = git_status_porcelain(config.repo_root, config.debug)
    if status.strip():
        dirty_paths = parse_porcelain_paths(status)
        campaign_path_str = str(campaign_doc_relative)
        if dirty_paths == [campaign_path_str]:
            if config.auto_commit:
                git_commit(
                    [campaign_path_str],
                    f"Docs: finalize {campaign_id} campaign",
                    config.no_verify,
                    config.repo_root,
                    config.debug,
                )
                ensure_clean_git(
                    "after campaign finalize commit",
                    config.repo_root,
                    config.debug,
                )
            else:
                raise RunnerError(
                    "Auto-commit disabled but campaign summary updates "
                    "left the tree dirty."
                )
        else:
            raise RunnerError(
                "Unexpected dirty tree after cycle completion: "
                + ", ".join(dirty_paths)
            )


def run(config: RunnerConfig) -> int:
    """Run Codex Runner with the provided configuration."""
    if config.cycles < 1:
        raise RunnerError("--cycles must be >= 1")
    if not config.audit_prompt_file.exists():
        raise RunnerError(
            f"Audit prompt file not found: {config.audit_prompt_file}"
        )

    ensure_repo_root(config.repo_root, config.debug)
    ensure_codex_available()

    with load_resources(config) as resources:
        for cycle_index in range(1, config.cycles + 1):
            run_cycle(config, resources, cycle_index)

    return 0
