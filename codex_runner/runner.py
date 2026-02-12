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
MEGA_AUDIT_SCHEMA_PATH = SCHEMA_DIR / "mega_audit_output.schema.json"

# Prompt tokens
REPO_ROOT_TOKEN = "<REPO_ROOT>"
MEGA_AUDIT_JSON_TOKEN = "<PASTE MEGA_AUDIT_OUTPUT_JSON_HERE>"

TASK_ID_INLINE_PATTERN = re.compile(
    r"task[-_\s]*id\s*[:：]\s*`?([A-Za-z0-9_+\-]+)`?",
    re.IGNORECASE,
)
TASK_ID_HEADING_PATTERN = re.compile(
    r"^\s*#+\s*task[-_\s]*id\s*$",
    re.IGNORECASE,
)
TASK_FILENAME_PATTERN = re.compile(
    r"^TASK_(\d{4})_(\d{2})_(\d{2})_(\d{3})_([a-z0-9_]+)\.md$"
)
TASK_RESULT_JSON_BLOCK_PATTERN = re.compile(
    r"(<summary>Structured task_result\.json</summary>\s*\n\n```json\n)"
    r"(\{.*?\})"
    r"(\n```)",
    re.DOTALL,
)


class RunnerError(RuntimeError):
    pass


# Logging helper: prints to STDERR
def log(message: str) -> None:
    print(message, file=sys.stderr)


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
        "campaign_markdown",
        "tasks",
    ]
    missing = [field for field in required_fields if field not in payload]
    if missing:
        raise RunnerError(f"Missing campaign fields: {', '.join(missing)}")

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


def write_text_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def append_text_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(content)


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


# -------- RUNNER ARTIFACT PATHS + PROMPT RENDERING HELPERS --------


def upper_snake(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", value.strip())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned.upper() or "CAMPAIGN"


def canonical_campaign_doc_path(campaign_slug: str) -> Path:
    today = date.today().strftime("%Y_%m_%d")
    return (
        DEFAULT_CAMPAIGN_DIR
        / f"CAMPAIGN_{today}_{upper_snake(campaign_slug)}.md"
    )


def normalize_task_id(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    return re.sub(r"-+", "-", cleaned).strip("-")


def normalize_task_slug(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", value.strip().lower())
    return re.sub(r"_+", "_", cleaned).strip("_")


def extract_task_date(task_id: str) -> str:
    m = re.search(r"(20\d{2})[-_](\d{2})[-_](\d{2})", task_id)
    if m:
        return f"{m.group(1)}_{m.group(2)}_{m.group(3)}"
    return date.today().strftime("%Y_%m_%d")


def extract_task_nnn(task_id: str) -> str:
    matches = re.findall(r"(?:^|[-_])(\d{3})(?=[-_]|$)", task_id)
    return matches[-1] if matches else ""


def extract_slug_from_task_id(task_id: str) -> str:
    m = re.search(r"(?:^|[-_])\d{3}[-_](.+)$", task_id)
    if not m:
        return ""
    return normalize_task_slug(m.group(1))


def canonical_task_artifact_path(task_id: str, task_slug: str) -> Path:
    nnn = extract_task_nnn(task_id) or "000"
    task_date = extract_task_date(task_id)
    safe_slug = normalize_task_slug(task_slug) or extract_slug_from_task_id(
        task_id
    )
    safe_slug = safe_slug or "task"
    return DEFAULT_TASKS_DIR / f"TASK_{task_date}_{nnn}_{safe_slug}.md"


def task_semantic_key(task_id: str, task_slug: str) -> str:
    nnn = extract_task_nnn(task_id)
    slug = normalize_task_slug(task_slug) or extract_slug_from_task_id(task_id)
    if not nnn or not slug:
        return ""
    return f"{nnn}:{slug}"


def extract_task_id_from_artifact(text: str) -> str:
    lines = text.splitlines()
    for line in lines:
        inline_match = TASK_ID_INLINE_PATTERN.search(line)
        if inline_match:
            return inline_match.group(1).strip()
    for idx, line in enumerate(lines):
        if not TASK_ID_HEADING_PATTERN.match(line):
            continue
        for candidate in lines[idx + 1 : idx + 6]:
            cleaned = candidate.strip().strip("`").strip("*").strip("-").strip()
            if re.fullmatch(r"[A-Za-z0-9_+\-]+", cleaned):
                return cleaned
    return ""


def task_semantic_key_from_path(path: Path) -> str:
    match = TASK_FILENAME_PATTERN.match(path.name)
    if not match:
        return ""
    return f"{match.group(4)}:{normalize_task_slug(match.group(5))}"


def resolve_task_artifact_path(
    task: dict[str, Any], existing_task_paths: list[Path]
) -> Path:
    task_id = str(task.get("id") or "")
    task_slug = str(task.get("slug") or "")
    declared_path = str(task.get("task_artifact_path") or "").strip()
    if declared_path and TASK_PATH_PATTERN.fullmatch(declared_path):
        preferred = Path(declared_path)
    else:
        preferred = canonical_task_artifact_path(task_id, task_slug)

    if preferred.exists():
        return preferred

    target_id = normalize_task_id(task_id)
    target_key = task_semantic_key(task_id, task_slug)

    exact_id_matches: list[Path] = []
    semantic_matches: list[Path] = []

    for candidate in sorted(existing_task_paths):
        if not candidate.exists() or not candidate.is_file():
            continue

        candidate_text = candidate.read_text(encoding="utf-8")
        embedded_task_id = extract_task_id_from_artifact(candidate_text)
        normalized_embedded = (
            normalize_task_id(embedded_task_id) if embedded_task_id else ""
        )

        if (
            target_id
            and normalized_embedded
            and normalized_embedded == target_id
        ):
            exact_id_matches.append(candidate)
            continue

        if target_key:
            # Collision guard: if this doc embeds a *different* task id, semantic
            # key fallback is not allowed.
            if (
                target_id
                and normalized_embedded
                and normalized_embedded != target_id
            ):
                continue
            if task_semantic_key_from_path(candidate) == target_key:
                semantic_matches.append(candidate)
                continue
            embedded_key = task_semantic_key(embedded_task_id, "")
            if embedded_key and embedded_key == target_key:
                semantic_matches.append(candidate)

    if exact_id_matches:
        return exact_id_matches[0]
    if semantic_matches:
        return semantic_matches[0]
    return preferred


def render_compiler_prompt(
    template_path: Path, repo_root: Path, mega_audit_payload: dict[str, Any]
) -> str:
    template_text = template_path.read_text(encoding="utf-8")
    rendered = template_text.replace(REPO_ROOT_TOKEN, str(repo_root))
    rendered = rendered.replace(
        MEGA_AUDIT_JSON_TOKEN, json.dumps(mega_audit_payload, indent=2)
    )
    return rendered


def update_campaign_mapping_line(
    campaign_doc: Path, task_id: str, impl_hash: str, receipt_hash: str
) -> None:
    line = f"{task_id} -> [{impl_hash}, {receipt_hash}]"
    text = (
        campaign_doc.read_text(encoding="utf-8")
        if campaign_doc.exists()
        else ""
    )
    pattern = re.compile(rf"^{re.escape(task_id)}\s*->\s*\[.*\]$", re.MULTILINE)
    if pattern.search(text):
        text = pattern.sub(line, text)
    else:
        # Append under a mapping header if present, otherwise append at end.
        if "## Task Mapping" in text:
            text = text.rstrip() + "\n" + line + "\n"
        else:
            text = text.rstrip() + "\n\n## Task Mapping\n\n" + line + "\n"
    write_text_file(campaign_doc, text)


def append_runner_completion_summary(
    task_artifact: Path,
    result: dict[str, Any],
    impl_hash: str,
    receipt_hash: str,
) -> None:
    render_result = dict(result)
    render_result["receipt_update_commit_hash"] = receipt_hash
    status = (result.get("status") or "unknown").strip()
    tests_ran = result.get("tests_ran")
    tests_line = "n/a"
    if isinstance(tests_ran, list):
        tests_line = (
            ", ".join(str(t) for t in tests_ran) if tests_ran else "(none)"
        )
    summary = (result.get("summary") or "").strip()
    notes = (result.get("notes") or "").strip()

    block = (
        "\n\n## Completion Summary (Runner)\n\n"
        f"- Status: {status}\n\n"
        f"- Summary: {summary if summary else '(none)'}\n\n"
        f"- Implementation commit hash: {impl_hash}\n\n"
        f"- Receipt update commit hash: {receipt_hash}\n\n"
        f"- Tests ran: {tests_line}\n"
    )
    if notes:
        block += f"\n- Notes: {notes}\n"

    block += (
        "\n<details>\n<summary>Structured task_result.json</summary>\n\n```json\n"
        + json.dumps(render_result, indent=2)
        + "\n```\n\n</details>\n"
    )

    append_text_file(task_artifact, block)


def replace_last_match(
    text: str, pattern: re.Pattern[str], replacement: str
) -> tuple[str, bool]:
    matches = list(pattern.finditer(text))
    if not matches:
        return text, False
    match = matches[-1]
    return text[: match.start()] + replacement + text[match.end() :], True


def update_task_artifact_receipt_hash(
    task_artifact: Path, receipt_hash: str
) -> bool:
    text = task_artifact.read_text(encoding="utf-8")
    changed = False

    # Update summary line.
    summary_line_pattern = re.compile(
        r"^- Receipt update commit hash: .*$", re.MULTILINE
    )
    summary_line = f"- Receipt update commit hash: {receipt_hash}"
    updated, replaced = replace_last_match(
        text, summary_line_pattern, summary_line
    )
    if replaced and updated != text:
        text = updated
        changed = True

    # Update latest structured task_result.json block.
    matches = list(TASK_RESULT_JSON_BLOCK_PATTERN.finditer(text))
    if matches:
        last_match = matches[-1]
        payload = json.loads(last_match.group(2))
        if payload.get("receipt_update_commit_hash") != receipt_hash:
            payload["receipt_update_commit_hash"] = receipt_hash
            replacement = (
                last_match.group(1)
                + json.dumps(payload, indent=2)
                + last_match.group(3)
            )
            text = (
                text[: last_match.start()]
                + replacement
                + text[last_match.end() :]
            )
            changed = True

    if changed:
        write_text_file(task_artifact, text)
    return changed


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
    switch_existing_branch(branch_name)


def switch_existing_branch(branch_name: str) -> None:
    switch_result = run_cmd(["git", "switch", branch_name], capture_output=True)
    if switch_result.returncode != 0:
        raise RunnerError(
            f"Unable to switch to existing branch '{branch_name}': "
            f"{switch_result.stderr.strip()}"
        )


def git_current_branch() -> str:
    result = run_cmd(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True
    )
    if result.returncode != 0:
        raise RunnerError(
            f"git rev-parse --abbrev-ref failed: {result.stderr.strip()}"
        )
    branch_name = result.stdout.strip()
    if not branch_name:
        raise RunnerError("Unable to determine current git branch.")
    return branch_name


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


def git_commit_amend(paths: list[str], no_verify: bool) -> str:
    if paths:
        add_result = run_cmd(["git", "add", *paths], capture_output=True)
        if add_result.returncode != 0:
            raise RunnerError(f"git add failed: {add_result.stderr.strip()}")
    commit_cmd = ["git", "commit", "--amend", "--no-edit"]
    if no_verify:
        commit_cmd.insert(2, "--no-verify")
    commit_result = run_cmd(commit_cmd, capture_output=True)
    if commit_result.returncode != 0:
        raise RunnerError(
            f"git commit --amend failed: {commit_result.stderr.strip()}"
        )
    return git_head_commit()


def execute_task(task: dict[str, Any]) -> dict[str, Any]:
    """Run a single task activation prompt via Codex and return the structured result.

    Note: the task agent may or may not perform the git commit itself. The runner is
    allowed to commit (auto-commit mode), so commit_hash validation/fill-in happens
    at the orchestration layer where we can compare HEAD before/after.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        prompt_path = tmp_path / "activation_prompt.md"
        output_path = tmp_path / "task_result.json"
        prompt_path.write_text(task["activation_prompt"], encoding="utf-8")
        run_codex_exec(prompt_path, TASK_RESULT_SCHEMA_PATH, output_path)
        return read_json_file(output_path)


def run_cycle(
    args: argparse.Namespace, cycle_index: int, base_branch: str
) -> None:
    ensure_clean_git("start of cycle")
    log(f"Starting cycle {cycle_index}...")
    log(
        "Note: concurrent campaigns in the same workdir will serialize in Git. "
        "Use separate clones/worktrees for true parallelism."
    )

    # Two-stroke pipeline: MEGA audit JSON -> campaign compiler JSON
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        mega_out = tmp_path / "mega_audit_output.json"
        run_codex_exec(
            args.mega_audit_prompt_file, MEGA_AUDIT_SCHEMA_PATH, mega_out
        )
        mega_payload = read_json_file(mega_out)

        compiler_prompt_text = render_compiler_prompt(
            args.campaign_compiler_prompt_file, Path.cwd(), mega_payload
        )
        compiler_prompt_path = tmp_path / "campaign_compiler_prompt.md"
        compiler_prompt_path.write_text(compiler_prompt_text, encoding="utf-8")

        campaign_out = tmp_path / "campaign_output.json"
        run_codex_exec(compiler_prompt_path, CAMPAIGN_SCHEMA_PATH, campaign_out)
        payload = read_json_file(campaign_out)

    validate_campaign_payload(payload)

    campaign_slug = payload.get("campaign_slug", "")
    if not campaign_slug:
        raise RunnerError("campaign_slug is required for branch-per-campaign")
    if not git_is_clean():
        raise RunnerError(
            "git tree is not clean before switching campaign branch"
        )
    campaign_branch = campaign_branch_name(campaign_slug)
    log(f"Switching to campaign branch: {campaign_branch}")
    switch_branch(campaign_branch)
    ensure_clean_git("after switching campaign branch")

    campaign_doc_path = canonical_campaign_doc_path(campaign_slug)
    write_text_file(campaign_doc_path, payload["campaign_markdown"])

    # Write task artifacts, reusing existing docs when an exact or semantic
    # match is found.
    task_artifact_paths: dict[str, Path] = {}
    task_path_to_id: dict[Path, str] = {}
    existing_task_paths = list(DEFAULT_TASKS_DIR.rglob("TASK_*.md"))
    for task in payload["tasks"]:
        task_id = str(task.get("id") or "")
        task_path = resolve_task_artifact_path(task, existing_task_paths)
        prior_task_id = task_path_to_id.get(task_path)
        if prior_task_id and prior_task_id != task_id:
            raise RunnerError(
                "Task artifact path collision detected between "
                f"{prior_task_id} and {task_id}: {task_path}"
            )
        task_path_to_id[task_path] = task_id
        task_artifact_paths[task_id] = task_path
        write_text_file(task_path, task["task_artifact_markdown"])
        if task_path not in existing_task_paths:
            existing_task_paths.append(task_path)

    campaign_id = payload.get("campaign_id", "campaign")
    artifact_paths = [str(campaign_doc_path)] + [
        str(p) for p in task_artifact_paths.values()
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
            task_id = str(task.get("id") or "")
            task_artifact_path = task_artifact_paths.get(
                task_id
            ) or resolve_task_artifact_path(
                task, list(DEFAULT_TASKS_DIR.rglob("TASK_*.md"))
            )

            head_before = git_head_commit()
            log(f"Executing task {task_id}...")
            result = execute_task(task)

            # If the agent left changes, the runner commits them as the implementation commit.
            if not git_is_clean():
                if args.auto_commit:
                    git_commit_all(task["commit_message"], args.no_verify)
                else:
                    raise RunnerError(
                        "Auto-commit disabled but task left the tree dirty."
                    )

            ensure_clean_git("after task implementation commit")
            impl_hash = git_head_commit()

            # Normalize implementation hash fields.
            reported = (
                result.get("implementation_commit_hash") or ""
            ).strip() or (result.get("commit_hash") or "").strip()
            if not reported and impl_hash != head_before:
                result["commit_hash"] = impl_hash
                result["implementation_commit_hash"] = impl_hash
            elif reported and reported != impl_hash:
                existing_notes = (result.get("notes") or "").strip()
                note = f"implementation commit mismatch: reported {reported}, head is {impl_hash}"
                result["notes"] = f"{existing_notes} {note}".strip()
                print(f"Warning: {note}", file=sys.stderr)
                result["implementation_commit_hash"] = impl_hash
                result["commit_hash"] = impl_hash
            else:
                # Keep consistent fields.
                result["implementation_commit_hash"] = reported or impl_hash
                result["commit_hash"] = reported or impl_hash

            # Receipt update commit (task artifact + campaign mapping).
            append_runner_completion_summary(
                task_artifact_path, result, impl_hash, "(pending)"
            )
            update_campaign_mapping_line(
                campaign_doc_path, task_id, impl_hash, "(pending)"
            )
            if args.auto_commit:
                receipt_commit_msg = f"{task_id}: receipt update"
                seed_receipt_hash = git_commit(
                    [str(task_artifact_path), str(campaign_doc_path)],
                    receipt_commit_msg,
                    args.no_verify,
                )
                update_task_artifact_receipt_hash(
                    task_artifact_path, seed_receipt_hash
                )
                update_campaign_mapping_line(
                    campaign_doc_path,
                    task_id,
                    impl_hash,
                    seed_receipt_hash,
                )
                receipt_hash = git_commit_amend(
                    [str(task_artifact_path), str(campaign_doc_path)],
                    args.no_verify,
                )
                ensure_clean_git("after task receipt commit")
            else:
                raise RunnerError(
                    "Auto-commit disabled but runner receipt update would dirty the tree."
                )

            result["receipt_update_commit_hash"] = receipt_hash

            if impl_hash == head_before and (result.get("status") != "success"):
                raise RunnerError(
                    f"Task {task_id} produced no implementation commit."
                )
    elif args.execute and args.dry_run:
        log("Dry run enabled: skipping task execution.")

    ensure_clean_git("end of cycle")

    if args.return_to_base_branch:
        ensure_clean_git("before returning to base branch")
        log(f"Returning to base branch: {base_branch}")
        switch_existing_branch(base_branch)
        ensure_clean_git("after returning to base branch")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Campaign Runner")
    parser.add_argument(
        "--mega-audit-prompt-file",
        type=Path,
        required=True,
        help="Path to the MEGA audit prompt file (outputs mega_audit_output JSON).",
    )
    parser.add_argument(
        "--campaign-compiler-prompt-file",
        type=Path,
        required=True,
        help="Path to the audit→campaign compiler prompt file (ingests MEGA audit JSON, outputs campaign_output JSON).",
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
    return_group = parser.add_mutually_exclusive_group()
    return_group.add_argument(
        "--return-to-base-branch",
        dest="return_to_base_branch",
        action="store_true",
        default=True,
        help="Return to the original base branch after each cycle (default).",
    )
    return_group.add_argument(
        "--no-return-to-base-branch",
        dest="return_to_base_branch",
        action="store_false",
        help="Stay on the campaign branch after each cycle.",
    )
    parser.add_argument(
        "--allow-detached-head",
        action="store_true",
        help="Allow running when the initial git HEAD is detached.",
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

    if not args.mega_audit_prompt_file.exists():
        raise RunnerError(
            f"MEGA audit prompt file not found: {args.mega_audit_prompt_file}"
        )
    if not args.campaign_compiler_prompt_file.exists():
        raise RunnerError(
            f"Campaign compiler prompt file not found: {args.campaign_compiler_prompt_file}"
        )

    base_branch = git_current_branch()
    if base_branch == "HEAD" and not args.allow_detached_head:
        raise RunnerError(
            "HEAD is detached. Pass --allow-detached-head to run anyway."
        )
    log(f"Base branch: {base_branch}")

    for cycle_index in range(1, args.cycles + 1):
        run_cycle(args, cycle_index, base_branch)

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except RunnerError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
