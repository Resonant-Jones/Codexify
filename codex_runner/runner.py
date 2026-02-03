#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List

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


def ensure_clean_git() -> None:
    result = run_cmd(
        ["git", "status", "--porcelain", "-uall"], capture_output=True
    )
    if result.returncode != 0:
        raise RunnerError(f"git status failed: {result.stderr.strip()}")
    if result.stdout.strip():
        raise RunnerError(
            "git tree is not clean. Commit or stash changes before running the runner."
        )


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
    result = run_cmd(
        [
            "codex",
            "exec",
            "--output-schema",
            str(output_schema),
            "-o",
            str(output_path),
            "--prompt-file",
            str(prompt_file),
        ]
    )
    if result.returncode != 0:
        raise RunnerError("codex exec failed")


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
    ensure_clean_git()
    print(f"Starting cycle {cycle_index}...")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        output_path = tmp_path / "campaign_output.json"
        run_codex_exec(
            args.audit_prompt_file, CAMPAIGN_SCHEMA_PATH, output_path
        )
        payload = read_json_file(output_path)

    validate_campaign_payload(payload)

    if args.branch_per_campaign:
        campaign_slug = payload.get("campaign_slug", "")
        if not campaign_slug:
            raise RunnerError(
                "campaign_slug is required for branch-per-campaign"
            )
        switch_branch(campaign_slug)

    campaign_doc_path = Path(payload["campaign_doc_path"])
    write_text_file(campaign_doc_path, payload["campaign_markdown"])

    for task in payload["tasks"]:
        task_path = Path(task["task_artifact_path"])
        write_text_file(task_path, task["task_artifact_markdown"])

    if args.execute and not args.dry_run:
        for task in payload["tasks"]:
            print(f"Executing task {task.get('id', '')}...")
            execute_task(task)
    elif args.execute and args.dry_run:
        print("Dry run enabled: skipping task execution.")


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
        help="Create/switch to a branch per campaign using campaign_slug.",
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
