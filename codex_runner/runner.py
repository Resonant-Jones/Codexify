#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path
from typing import Any

DEFAULT_CAMPAIGN_DIR = Path("docs/Campaign")
DEFAULT_TASKS_DIR = Path("docs/tasks")

CAMPAIGN_PATH_PATTERN = re.compile(
    r"^docs/Campaign/CAMPAIGN_\d{4}_\d{2}_\d{2}(?:_[A-Z0-9_+\-]+)?\.md$"
)
TASK_PATH_PATTERN = re.compile(
    r"^docs/tasks/TASK_\d{4}_\d{2}_\d{2}_\d{3}_[a-z0-9_]+\.md$"
)

SCRIPT_DIR = Path(__file__).resolve().parent
SCHEMA_DIR = SCRIPT_DIR / "schemas"
CAMPAIGN_SCHEMA_PATH = SCHEMA_DIR / "campaign_output.schema.json"
TASK_RESULT_SCHEMA_PATH = SCHEMA_DIR / "task_result.schema.json"


class RunnerError(RuntimeError):
    pass


def run_cmd(
    args: list[str], *, capture_output: bool = False
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        text=True,
        capture_output=capture_output,
        check=False,
    )


def git_status_porcelain() -> str:
    result = run_cmd(
        ["git", "status", "--porcelain", "-uall"], capture_output=True
    )
    if result.returncode != 0:
        raise RunnerError(f"git status failed: {result.stderr.strip()}")
    return result.stdout


def git_is_clean() -> bool:
    return git_status_porcelain().strip() == ""


def ensure_clean_git(context: str) -> None:
    if not git_is_clean():
        raise RunnerError(
            f"git tree is not clean ({context}). Commit or stash changes."
        )


def parse_porcelain_paths(status: str) -> list[str]:
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
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RunnerError(f"Expected output file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RunnerError(f"Invalid JSON in {path}: {exc}") from exc


def validate_campaign_payload(payload: dict[str, Any]) -> None:
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
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def run_codex_exec(
    prompt_file: Path, output_schema: Path, output_path: Path
) -> None:
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
    slug = re.sub(r"[^a-z0-9_-]+", "-", value.strip().lower())
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    if not slug:
        raise RunnerError("campaign_slug must contain valid characters")
    return slug


def campaign_branch_name(campaign_slug: str) -> str:
    safe_slug = slugify_branch(campaign_slug)
    today = date.today().strftime("%Y-%m-%d")
    return f"campaign/{today}/{safe_slug}"


def switch_branch(branch_name: str) -> None:
    create_result = run_cmd(
        ["git", "switch", "-c", branch_name], capture_output=True
    )
    if create_result.returncode == 0:
        return
    switch_result = run_cmd(["git", "switch", branch_name], capture_output=True)
    if switch_result.returncode != 0:
        raise RunnerError(
            f"Unable to switch to branch '{branch_name}': "
            f"{switch_result.stderr.strip()}"
        )


def git_head_commit() -> str:
    result = run_cmd(["git", "rev-parse", "HEAD"], capture_output=True)
    if result.returncode != 0:
        raise RunnerError(f"git rev-parse failed: {result.stderr.strip()}")
    return result.stdout.strip()


def git_commit(paths: list[str], message: str, no_verify: bool) -> str:
    if not paths:
        raise RunnerError("git_commit requires at least one path")
    add_result = run_cmd(["git", "add", *paths], capture_output=True)
    if add_result.returncode != 0:
        raise RunnerError(f"git add failed: {add_result.stderr.strip()}")
    commit_cmd = ["git", "commit", "-m", message]
    if no_verify:
        commit_cmd.insert(2, "--no-verify")
    commit_result = run_cmd(commit_cmd, capture_output=True)
    if commit_result.returncode != 0:
        raise RunnerError(f"git commit failed: {commit_result.stderr.strip()}")
    return git_head_commit()


def git_commit_all(message: str, no_verify: bool) -> str:
    add_result = run_cmd(["git", "add", "-A"], capture_output=True)
    if add_result.returncode != 0:
        raise RunnerError(f"git add -A failed: {add_result.stderr.strip()}")
    commit_cmd = ["git", "commit", "-m", message]
    if no_verify:
        commit_cmd.insert(2, "--no-verify")
    commit_result = run_cmd(commit_cmd, capture_output=True)
    if commit_result.returncode != 0:
        raise RunnerError(f"git commit failed: {commit_result.stderr.strip()}")
    return git_head_commit()


def execute_task(task: dict[str, Any]) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        prompt_path = tmp_path / "activation_prompt.md"
        output_path = tmp_path / "task_result.json"
        prompt_path.write_text(task["activation_prompt"], encoding="utf-8")
        run_codex_exec(prompt_path, TASK_RESULT_SCHEMA_PATH, output_path)
        result = read_json_file(output_path)

    status = result.get("status")
    if status == "success":
        head_commit = git_head_commit()
        commit_hash = result.get("commit_hash", "")
        if commit_hash != head_commit:
            note = (
                "commit_hash mismatch: expected "
                f"{head_commit}, got {commit_hash}"
            )
            existing_notes = result.get("notes", "")
            result["notes"] = f"{existing_notes} {note}".strip()
            print(f"Warning: {note}", file=sys.stderr)
    return result


def run_cycle(args: argparse.Namespace, cycle_index: int) -> None:
    ensure_clean_git("start of cycle")
    print(f"Starting cycle {cycle_index}...")
    print(
        "Note: concurrent campaigns in the same workdir will serialize in Git. "
        "Use separate clones/worktrees for true parallelism."
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        output_path = tmp_path / "campaign_output.json"
        run_codex_exec(
            args.audit_prompt_file, CAMPAIGN_SCHEMA_PATH, output_path
        )
        payload = read_json_file(output_path)

    validate_campaign_payload(payload)

    campaign_slug = payload.get("campaign_slug", "")
    if not campaign_slug:
        raise RunnerError("campaign_slug is required for branch-per-campaign")
    if not git_is_clean():
        raise RunnerError(
            "git tree is not clean before switching campaign branch"
        )
    switch_branch(campaign_branch_name(campaign_slug))
    ensure_clean_git("after switching campaign branch")

    campaign_doc_path = Path(payload["campaign_doc_path"])
    write_text_file(campaign_doc_path, payload["campaign_markdown"])

    for task in payload["tasks"]:
        task_path = Path(task["task_artifact_path"])
        write_text_file(task_path, task["task_artifact_markdown"])

    campaign_id = payload.get("campaign_id", "campaign")
    artifact_paths = [str(campaign_doc_path)] + [
        task["task_artifact_path"] for task in payload["tasks"]
    ]

    if args.auto_commit:
        git_commit(
            artifact_paths,
            f"Docs: add {campaign_id} campaign + tasks",
            args.no_verify,
        )
        ensure_clean_git("after campaign artifact commit")
    elif not git_is_clean():
        raise RunnerError(
            "Auto-commit disabled but campaign artifacts changed the tree."
        )

    if args.execute and not args.dry_run:
        for task in payload["tasks"]:
            ensure_clean_git("start of task")
            head_before = git_head_commit()
            print(f"Executing task {task.get('id', '')}...")
            execute_task(task)

            if not git_is_clean():
                if args.auto_commit:
                    git_commit_all(task["commit_message"], args.no_verify)
                else:
                    raise RunnerError(
                        "Auto-commit disabled but task left the tree dirty."
                    )

            ensure_clean_git("after task commit")
            head_after = git_head_commit()
            if head_after == head_before:
                raise RunnerError(
                    f"Task {task.get('id', '')} produced no commit."
                )
    elif args.execute and args.dry_run:
        print("Dry run enabled: skipping task execution.")

    status = git_status_porcelain()
    if status.strip():
        dirty_paths = parse_porcelain_paths(status)
        campaign_path_str = str(campaign_doc_path)
        if dirty_paths == [campaign_path_str]:
            if args.auto_commit:
                git_commit(
                    [campaign_path_str],
                    f"Docs: finalize {campaign_id} campaign",
                    args.no_verify,
                )
                ensure_clean_git("after campaign finalize commit")
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Codex Runner")
    parser.add_argument(
        "--audit-prompt-file",
        type=Path,
        required=True,
        help="Path to the audit prompt file.",
    )
    parser.add_argument(
        "--cycles",
        type=int,
        default=1,
        help="Number of audit cycles to run.",
    )
    parser.add_argument(
        "--branch-per-campaign",
        action="store_true",
        default=True,
        help=(
            "Required. Create/switch to a branch per campaign using "
            "campaign_slug (default behavior)."
        ),
    )
    verify_group = parser.add_mutually_exclusive_group()
    verify_group.add_argument(
        "--no-verify",
        dest="no_verify",
        action="store_true",
        default=True,
        help="Skip git hooks for runner commits (default).",
    )
    verify_group.add_argument(
        "--verify",
        dest="no_verify",
        action="store_false",
        help="Run git hooks for runner commits.",
    )
    auto_commit_group = parser.add_mutually_exclusive_group()
    auto_commit_group.add_argument(
        "--auto-commit",
        dest="auto_commit",
        action="store_true",
        default=True,
        help="Auto-commit runner-generated changes (default).",
    )
    auto_commit_group.add_argument(
        "--no-auto-commit",
        dest="auto_commit",
        action="store_false",
        help="Disable auto-commit for runner-generated changes.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute tasks sequentially after generating artifacts.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate artifacts but skip task execution.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.cycles < 1:
        raise RunnerError("--cycles must be >= 1")

    if not args.audit_prompt_file.exists():
        raise RunnerError(
            f"Audit prompt file not found: {args.audit_prompt_file}"
        )

    for cycle_index in range(1, args.cycles + 1):
        run_cycle(args, cycle_index)

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except RunnerError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
