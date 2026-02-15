#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from datetime import date, datetime
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


# Helper: Parse Codex API error payloads from stderr/stdout (429, usage_limit, etc)
def _maybe_parse_codex_error_payload(text: str) -> dict[str, Any] | None:
    """Best-effort extraction of Codex API error JSON embedded in stderr/stdout.

    Codex sometimes prints an escaped JSON payload inside a wrapper like:
      http 429 Too Many Requests: Some("{\"error\":{...}}")

    This returns the decoded JSON dict if found, otherwise None.
    """
    if not text:
        return None

    # 1) Try to find a raw JSON object that contains an "error" key.
    json_match = re.search(r"(\{\s*\"error\"\s*:\s*\{.*\}\s*\})", text)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # 2) Try to find an escaped JSON payload inside Some("...")
    some_match = re.search(r"Some\\(\"(?P<payload>\\{.*?\\})\"\\)", text)
    if some_match:
        payload_escaped = some_match.group("payload")
        try:
            # The payload is typically backslash-escaped.
            payload = payload_escaped.encode("utf-8").decode("unicode_escape")
            return json.loads(payload)
        except Exception:
            return None

    return None


def _format_codex_usage_limit_note(payload: dict[str, Any] | None) -> str:
    if not payload:
        return ""
    err = payload.get("error")
    if not isinstance(err, dict):
        return ""
    if err.get("type") != "usage_limit_reached":
        return ""

    resets_at = err.get("resets_at")
    resets_in = err.get("resets_in_seconds")
    plan_type = err.get("plan_type")

    parts: list[str] = []
    if plan_type:
        parts.append(f"plan_type={plan_type}")

    if isinstance(resets_at, int):
        try:
            dt = datetime.fromtimestamp(resets_at)
            parts.append(
                f"resets_at={dt.isoformat(sep=' ', timespec='seconds')}"
            )
        except Exception:
            parts.append(f"resets_at={resets_at}")

    if isinstance(resets_in, int):
        parts.append(f"resets_in_seconds={resets_in}")

    return (
        "\nNOTE: usage_limit_reached (" + ", ".join(parts) + ")"
        if parts
        else "\nNOTE: usage_limit_reached"
    )


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
    prompt_file: Path,
    output_schema: Path,
    output_path: Path,
    *,
    model: str | None = None,
    config_overrides: list[str] | None = None,
) -> None:
    prompt_text = prompt_file.read_text(encoding="utf-8")

    cmd: list[str] = ["codex"]
    if model:
        cmd.extend(["--model", model])
    if config_overrides:
        for cfg in config_overrides:
            if cfg:
                cmd.extend(["--config", cfg])

    cmd.extend(
        [
            "exec",
            "--output-schema",
            str(output_schema),
            "-o",
            str(output_path),
            prompt_text,
        ]
    )

    result = run_cmd(cmd, capture_output=True)
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        stdout = (result.stdout or "").strip()
        combined = "\n".join([s for s in [stderr, stdout] if s])
        parsed = _maybe_parse_codex_error_payload(combined)
        note = _format_codex_usage_limit_note(parsed)
        raise RunnerError(
            "codex exec failed"
            + (f"\nSTDERR:\n{stderr}" if stderr else "")
            + (f"\nSTDOUT:\n{stdout}" if stdout else "")
            + (
                f"\nPARSED_ERROR:\n{json.dumps(parsed, indent=2)}"
                if parsed
                else ""
            )
            + note
        )


# --------- Model selection helper for tasks ---------


def select_task_model(
    args: argparse.Namespace, task: dict[str, Any]
) -> str | None:
    """Pick the Codex model for a task.

    Priority:
      1) risk-specific flags if task includes a risk field (HIGH|MED|LOW)
      2) --codex-model-task
      3) --codex-model (global)
    """
    risk = str(task.get("risk") or "").strip().lower()
    if risk in {"high", "h"} and getattr(args, "task_model_high", None):
        return args.task_model_high
    if risk in {"med", "medium", "m"} and getattr(args, "task_model_med", None):
        return args.task_model_med
    if risk in {"low", "l"} and getattr(args, "task_model_low", None):
        return args.task_model_low

    return getattr(args, "codex_model_task", None) or getattr(
        args, "codex_model", None
    )


def slugify_branch(value: str) -> str:
    slug = re.sub(r"[^a-z0-9_-]+", "-", value.strip().lower())
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    if not slug:
        raise RunnerError("campaign_slug must contain valid characters")
    return slug


# -------- RUNNER ARTIFACT PATHS + PROMPT RENDERING HELPERS --------


def runner_failure_receipt_path(cycle_index: int) -> Path:
    today = date.today().strftime("%Y_%m_%d")
    return (
        Path("docs/reports/runner")
        / f"RUNNER_FAILURE_{today}_cycle_{cycle_index:03d}.md"
    )


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


# --- New runner receipt helpers ---
def append_runner_task_start_summary(
    task_artifact: Path,
    task_id: str,
    campaign_id: str,
    head_before: str,
) -> None:
    block = (
        "\n\n## Runner Receipt (Start)\n\n"
        f"- Campaign: {campaign_id}\n\n"
        f"- Task ID: {task_id}\n\n"
        f"- Head before: {head_before}\n"
    )
    append_text_file(task_artifact, block)


def append_runner_task_failure_summary(
    task_artifact: Path,
    task_id: str,
    campaign_id: str,
    head_before: str,
    error_message: str,
) -> None:
    block = (
        "\n\n## Completion Summary (Runner)\n\n"
        "- Status: failed\n\n"
        f"- Summary: (runner error)\n\n"
        f"- Head before: {head_before}\n\n"
        "- Implementation commit hash: (none)\n\n"
        "- Receipt update commit hash: (pending)\n\n"
        f"- Notes: {error_message.strip() if error_message else '(no details)'}\n"
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


# --------- Macro CLI (presets + loose tokens) ---------

PRESET_CHOICES = ("high", "medium", "low")

# Opinionated defaults. Power users can override any of these with explicit flags.
PRESET_DEFAULTS: dict[str, dict[str, Any]] = {
    # Highest quality / most expensive
    "high": {
        "codex_model": "gpt-5-codex",
        "codex_model_audit": None,
        "codex_model_compiler": None,
        "codex_model_task": None,
        # Config is appended; users can still pass their own --codex-config.
        "codex_config": ["model_reasoning_effort='\"high\"'"],
    },
    # Balanced: cheaper planning, strong task execution
    "medium": {
        "codex_model": None,
        "codex_model_audit": "gpt-4.1",
        "codex_model_compiler": "gpt-4.1",
        "codex_model_task": "gpt-5-codex",
        "codex_config": ["model_reasoning_effort='\"medium\"'"],
    },
    # Cheapest: mostly for quick iterations / wiring validation
    "low": {
        "codex_model": "gpt-4.1",
        "codex_model_audit": None,
        "codex_model_compiler": None,
        "codex_model_task": None,
        "codex_config": ["model_reasoning_effort='\"low\"'"],
    },
}


def normalize_macro_argv(argv: list[str]) -> list[str]:
    """Allow a loose, wordy CLI on top of argparse.

    Examples:
      codex_runner high cycles 4 no verify branch
      codex_runner medium execute dry-run

    This transforms common tokens into the canonical flags argparse understands.
    """
    if not argv:
        return argv

    out: list[str] = []
    i = 0
    while i < len(argv):
        tok = argv[i]
        low = tok.lower()

        # Preset as a bare token (only if it's the first non-flag-ish thing)
        if low in PRESET_CHOICES and not out:
            out.extend(["--preset", low])
            i += 1
            continue

        # Allow: cycles 4
        if low in {"cycles", "cycle"} and i + 1 < len(argv):
            out.extend(["--cycles", argv[i + 1]])
            i += 2
            continue

        # Allow: execute / run
        if low in {"execute", "run"}:
            out.append("--execute")
            i += 1
            continue

        # Allow: dry / dry-run
        if low in {"dry", "dry-run", "dryrun"}:
            out.append("--dry-run")
            i += 1
            continue

        # Allow: verify / no verify
        if low == "verify":
            out.append("--verify")
            i += 1
            continue
        if (
            low == "no"
            and i + 1 < len(argv)
            and argv[i + 1].lower() == "verify"
        ):
            out.append("--no-verify")
            i += 2
            continue
        if low in {"no-verify", "noverify", "nover"}:
            out.append("--no-verify")
            i += 1
            continue

        # Allow: branch (opinionated: stay on campaign branch after each cycle)
        if low in {"branch", "stay"}:
            out.append("--no-return-to-base-branch")
            i += 1
            continue
        if low in {"return", "base"}:
            out.append("--return-to-base-branch")
            i += 1
            continue

        out.append(tok)
        i += 1

    return out


def apply_preset(args: argparse.Namespace) -> None:
    """Apply --preset defaults without clobbering explicit user flags."""
    preset = (getattr(args, "preset", None) or "").strip().lower()
    if not preset:
        return
    if preset not in PRESET_DEFAULTS:
        raise RunnerError(f"Unknown preset: {preset}")

    defaults = PRESET_DEFAULTS[preset]

    # Models: only fill if user did not specify.
    if not args.codex_model and defaults.get("codex_model"):
        args.codex_model = defaults["codex_model"]
    if not args.codex_model_audit and defaults.get("codex_model_audit"):
        args.codex_model_audit = defaults["codex_model_audit"]
    if not args.codex_model_compiler and defaults.get("codex_model_compiler"):
        args.codex_model_compiler = defaults["codex_model_compiler"]
    if not args.codex_model_task and defaults.get("codex_model_task"):
        args.codex_model_task = defaults["codex_model_task"]

    # Config: preset config is prepended so user overrides can come later.
    preset_cfg = defaults.get("codex_config") or []
    if preset_cfg:
        merged: list[str] = []
        for item in list(preset_cfg) + list(args.codex_config or []):
            if item and item not in merged:
                merged.append(item)
        args.codex_config = merged


def execute_task(
    args: argparse.Namespace, task: dict[str, Any]
) -> dict[str, Any]:
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
        run_codex_exec(
            prompt_path,
            TASK_RESULT_SCHEMA_PATH,
            output_path,
            model=select_task_model(args, task),
            config_overrides=args.codex_config,
        )
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
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            mega_out = tmp_path / "mega_audit_output.json"
            run_codex_exec(
                args.mega_audit_prompt_file,
                MEGA_AUDIT_SCHEMA_PATH,
                mega_out,
                model=args.codex_model_audit or args.codex_model,
                config_overrides=args.codex_config,
            )
            mega_payload = read_json_file(mega_out)

            compiler_prompt_text = render_compiler_prompt(
                args.campaign_compiler_prompt_file, Path.cwd(), mega_payload
            )
            compiler_prompt_path = tmp_path / "campaign_compiler_prompt.md"
            compiler_prompt_path.write_text(
                compiler_prompt_text, encoding="utf-8"
            )

            campaign_out = tmp_path / "campaign_output.json"
            run_codex_exec(
                compiler_prompt_path,
                CAMPAIGN_SCHEMA_PATH,
                campaign_out,
                model=args.codex_model_compiler or args.codex_model,
                config_overrides=args.codex_config,
            )
            payload = read_json_file(campaign_out)
    except Exception as exc:
        # Always produce a deterministic receipt artifact for operators.
        receipt_path = runner_failure_receipt_path(cycle_index)
        head = git_head_commit()
        branch = git_current_branch()
        content = (
            "# Runner Failure Receipt\n\n"
            f"- Date: {date.today().isoformat()}\n"
            f"- Cycle: {cycle_index}\n"
            f"- Branch: {branch}\n"
            f"- Head: {head}\n\n"
            "## Error\n\n"
            f"```\n{str(exc)}\n```\n"
        )
        write_text_file(receipt_path, content)
        if args.auto_commit:
            git_commit(
                [str(receipt_path)],
                f"runner: failure receipt cycle {cycle_index:03d}",
                args.no_verify,
            )
            ensure_clean_git("after runner failure receipt commit")
        raise

    validate_campaign_payload(payload)

    campaign_slug = payload.get("campaign_slug", "")

    if args.branch_per_campaign:
        if not campaign_slug:
            raise RunnerError(
                "campaign_slug is required for branch-per-campaign"
            )
        if not git_is_clean():
            raise RunnerError(
                "git tree is not clean before switching campaign branch"
            )
        campaign_branch = campaign_branch_name(campaign_slug)
        log(f"Switching to campaign branch: {campaign_branch}")
        switch_branch(campaign_branch)
        ensure_clean_git("after switching campaign branch")

    safe_campaign_slug = (
        campaign_slug or payload.get("campaign_id", "campaign") or "campaign"
    )
    campaign_doc_path = canonical_campaign_doc_path(str(safe_campaign_slug))
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
        if task_path.exists():
            # Preserve any prior runner receipts; append the latest task markdown.
            append_text_file(
                task_path,
                "\n\n---\n\n" + task["task_artifact_markdown"],
            )
        else:
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
            append_runner_task_start_summary(
                task_artifact_path,
                task_id,
                str(campaign_id),
                head_before,
            )

            # Commit the start receipt immediately so we always have a trace.
            if args.auto_commit:
                git_commit(
                    [str(task_artifact_path)],
                    f"{task_id}: receipt start",
                    args.no_verify,
                )
                ensure_clean_git("after task receipt start commit")

            try:
                log(f"Executing task {task_id}...")
                result = execute_task(args, task)

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

                # Allow legitimate no-op/skip outcomes to have no impl commit.
                status_value = (result.get("status") or "").strip().lower()
                if impl_hash == head_before and status_value not in {
                    "success",
                    "no_op",
                    "noop",
                    "skipped",
                }:
                    raise RunnerError(
                        f"Task {task_id} produced no implementation commit."
                    )

            except Exception as exc:
                # Always write + commit a failure receipt before aborting.
                append_runner_task_failure_summary(
                    task_artifact_path,
                    task_id,
                    str(campaign_id),
                    head_before,
                    str(exc),
                )
                update_campaign_mapping_line(
                    campaign_doc_path, task_id, head_before, "(failed)"
                )
                if args.auto_commit:
                    git_commit(
                        [str(task_artifact_path), str(campaign_doc_path)],
                        f"{task_id}: receipt failed",
                        args.no_verify,
                    )
                    ensure_clean_git("after task failure receipt commit")
                raise
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
        "--preset",
        choices=PRESET_CHOICES,
        default=None,
        help=(
            "Optional macro preset for common configurations: high, medium, low. "
            "You can also pass the preset as a bare first token, e.g. `codex_runner high ...`."
        ),
    )
    parser.add_argument(
        "--codex-model",
        dest="codex_model",
        default=None,
        help=(
            "Optional. Codex model to use for all stages unless overridden by a stage-specific flag. "
            "Example: gpt-5-codex, gpt-5.2, gpt-4.1"
        ),
    )
    parser.add_argument(
        "--codex-model-audit",
        dest="codex_model_audit",
        default=None,
        help="Optional. Override model for the MEGA audit stage.",
    )
    parser.add_argument(
        "--codex-model-compiler",
        dest="codex_model_compiler",
        default=None,
        help="Optional. Override model for the campaign compiler stage.",
    )
    parser.add_argument(
        "--codex-model-task",
        dest="codex_model_task",
        default=None,
        help="Optional. Override model for task execution (unless risk-specific flags are used).",
    )
    parser.add_argument(
        "--task-model-high",
        dest="task_model_high",
        default=None,
        help="Optional. Model override when task risk is HIGH.",
    )
    parser.add_argument(
        "--task-model-med",
        dest="task_model_med",
        default=None,
        help="Optional. Model override when task risk is MED/MEDIUM.",
    )
    parser.add_argument(
        "--task-model-low",
        dest="task_model_low",
        default=None,
        help="Optional. Model override when task risk is LOW.",
    )
    parser.add_argument(
        "--codex-config",
        dest="codex_config",
        action="append",
        default=[],
        help=(
            "Optional. Pass-through Codex config override(s). Repeatable. "
            "Values are TOML, e.g. --codex-config model_reasoning_effort='\"low\"'"
        ),
    )
    parser.add_argument(
        "--cycles",
        type=int,
        default=1,
        help="Number of audit cycles to run.",
    )
    branch_group = parser.add_mutually_exclusive_group()
    branch_group.add_argument(
        "--branch-per-campaign",
        dest="branch_per_campaign",
        action="store_true",
        default=True,
        help=(
            "Create/switch to a branch per campaign using campaign_slug (default)."
        ),
    )
    branch_group.add_argument(
        "--no-branch-per-campaign",
        dest="branch_per_campaign",
        action="store_false",
        help="Disable branch-per-campaign behavior.",
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
    argv = normalize_macro_argv(sys.argv[1:])
    args = parser.parse_args(argv)
    apply_preset(args)
    return args


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
