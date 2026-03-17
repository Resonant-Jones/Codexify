#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

DEFAULT_AUDITS_DIR = Path("docs/_audits")
DEFAULT_CAMPAIGN_DIR = Path("docs/Campaign")
DEFAULT_TASKS_DIR = Path("docs/tasks")
DEFAULT_RUNS_DIR = Path("docs/_campaign_runs")
STATE_DIR = DEFAULT_RUNS_DIR / "state"
STATE_PATH = STATE_DIR / "state.json"
STATE_TRANSITIONS_PATH = STATE_DIR / "state_transitions.jsonl"

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_MEGA_AUDIT_SCHEMA_PATH = (
    SCRIPT_DIR / "schemas" / "mega_audit_output.schema.json"
)
DEFAULT_MEGA_AUDIT_PROMPT_PATH = SCRIPT_DIR / "prompts" / "mega_audit.md"
DEFAULT_CAMPAIGN_SET_SCHEMA_PATH = (
    SCRIPT_DIR / "schemas" / "campaign_set.schema.json"
)
DEFAULT_TASK_RESULT_SCHEMA_PATH = (
    SCRIPT_DIR / "schemas" / "task_result.schema.json"
)
DEFAULT_COMPILER_PROMPT_PATH = (
    SCRIPT_DIR / "prompts" / "audit_report_to_campaign_runner.md"
)
DEFAULT_COMPILER_JSON_TOKEN = "<PASTE MEGA_AUDIT_OUTPUT_JSON_HERE>"
DEFAULT_REPO_ROOT_TOKEN = "<REPO_ROOT>"
DEFAULT_AUDIT_ID_TOKEN = "<AUDIT_ID>"

CAMPAIGN_ID_PATTERN = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2})::(?P<slug>[a-z0-9_]+)::(?P<seq>\d{3})$"
)
TASK_ID_PATTERN = re.compile(r"^[A-Za-z0-9_:\-]+$")
TASK_SLUG_PATTERN = re.compile(r"^[a-z0-9_]+$")
RISK_VALUES = {"HIGH", "MED", "LOW"}
TASK_STATUS_VALUES = {"pending", "success", "failed", "blocked"}
TASK_RESULT_STATUS_VALUES = {"success", "failed", "blocked"}

MAPPING_START = "<!-- RUNNER_TASK_MAP -->"
MAPPING_END = "<!-- /RUNNER_TASK_MAP -->"


class RunnerError(RuntimeError):
    """Raised when deterministic runner constraints are violated."""


@dataclass
class StageHashes:
    audit_prompt_sha256: str
    audit_schema_sha256: str
    compiler_prompt_sha256: str
    campaign_set_schema_sha256: str


@dataclass
class SelectedCampaign:
    campaign_id: str
    campaign_slug: str
    reason: dict[str, Any]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def log(message: str) -> None:
    print(message, file=sys.stderr)


def canonical_json(value: Any) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def json_read(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RunnerError(f"Missing required JSON file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RunnerError(f"Invalid JSON in {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise RunnerError(f"Expected object JSON at {path}")
    return data


def json_write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def text_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def text_append(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(content)


def run_cmd(
    args: list[str],
    *,
    cwd: Path,
    capture_output: bool = False,
    debug: bool = False,
) -> subprocess.CompletedProcess[str]:
    if debug:
        log(f"[debug] cwd={cwd} cmd={' '.join(args)}")
    try:
        result = subprocess.run(
            args,
            cwd=str(cwd),
            text=True,
            capture_output=capture_output,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RunnerError(f"Executable not found: {args[0]}") from exc

    if debug and capture_output:
        if result.stdout:
            log(f"[debug] stdout:\n{result.stdout}")
        if result.stderr:
            log(f"[debug] stderr:\n{result.stderr}")
    return result


def git_status_porcelain(repo_root: Path, debug: bool) -> str:
    result = run_cmd(
        ["git", "status", "--porcelain", "-uall"],
        cwd=repo_root,
        capture_output=True,
        debug=debug,
    )
    if result.returncode != 0:
        raise RunnerError(f"git status failed: {result.stderr.strip()}")
    return result.stdout


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


def git_changed_paths(repo_root: Path, debug: bool) -> list[str]:
    return parse_porcelain_paths(git_status_porcelain(repo_root, debug))


def git_is_clean(repo_root: Path, debug: bool) -> bool:
    return git_status_porcelain(repo_root, debug).strip() == ""


def ensure_clean_git(context: str, repo_root: Path, debug: bool) -> None:
    if not git_is_clean(repo_root, debug):
        raise RunnerError(f"git tree is not clean ({context})")


def git_head(repo_root: Path, debug: bool) -> str:
    result = run_cmd(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        capture_output=True,
        debug=debug,
    )
    if result.returncode != 0:
        raise RunnerError(f"git rev-parse HEAD failed: {result.stderr.strip()}")
    return result.stdout.strip()


def git_resolve_ref(repo_root: Path, ref: str, debug: bool) -> str:
    result = run_cmd(
        ["git", "rev-parse", ref],
        cwd=repo_root,
        capture_output=True,
        debug=debug,
    )
    if result.returncode != 0:
        raise RunnerError(
            f"Unable to resolve git ref '{ref}': {result.stderr.strip()}"
        )
    return result.stdout.strip()


def git_current_branch(repo_root: Path, debug: bool) -> str:
    result = run_cmd(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=repo_root,
        capture_output=True,
        debug=debug,
    )
    if result.returncode != 0:
        raise RunnerError(f"git branch lookup failed: {result.stderr.strip()}")
    branch = result.stdout.strip()
    if not branch:
        raise RunnerError("Unable to determine current branch")
    return branch


def git_switch(repo_root: Path, branch: str, create: bool, debug: bool) -> None:
    args = (
        ["git", "switch", "-c", branch] if create else ["git", "switch", branch]
    )
    result = run_cmd(args, cwd=repo_root, capture_output=True, debug=debug)
    if result.returncode == 0:
        return
    if create:
        fallback = run_cmd(
            ["git", "switch", branch],
            cwd=repo_root,
            capture_output=True,
            debug=debug,
        )
        if fallback.returncode == 0:
            return
        raise RunnerError(
            f"Unable to switch branch '{branch}': {fallback.stderr.strip()}"
        )
    raise RunnerError(
        f"Unable to switch branch '{branch}': {result.stderr.strip()}"
    )


def git_commit(
    repo_root: Path, paths: list[str], message: str, verify: bool, debug: bool
) -> str:
    if not paths:
        raise RunnerError("git_commit called with empty path set")
    add = run_cmd(
        ["git", "add", *paths], cwd=repo_root, capture_output=True, debug=debug
    )
    if add.returncode != 0:
        raise RunnerError(f"git add failed: {add.stderr.strip()}")
    cmd = ["git", "commit", "-m", message]
    if not verify:
        cmd.insert(2, "--no-verify")
    commit = run_cmd(cmd, cwd=repo_root, capture_output=True, debug=debug)
    if commit.returncode != 0:
        raise RunnerError(f"git commit failed: {commit.stderr.strip()}")
    return git_head(repo_root, debug)


def sanitize_cli_args(argv: list[str]) -> list[str]:
    redacted_markers = {"token", "secret", "password", "key"}
    sanitized: list[str] = []
    i = 0
    while i < len(argv):
        part = argv[i]
        lowered = part.lower()
        if part.startswith("--") and "=" in part:
            flag, value = part.split("=", 1)
            if any(marker in flag.lower() for marker in redacted_markers):
                sanitized.append(f"{flag}=<redacted>")
            else:
                sanitized.append(f"{flag}={value}")
            i += 1
            continue
        if part.startswith("--") and any(
            marker in lowered for marker in redacted_markers
        ):
            sanitized.append(part)
            if i + 1 < len(argv) and not argv[i + 1].startswith("--"):
                sanitized.append("<redacted>")
                i += 2
                continue
        sanitized.append(part)
        i += 1
    return sanitized


def ensure_repo_root(repo_root: Path, debug: bool) -> None:
    if not repo_root.exists() or not repo_root.is_dir():
        raise RunnerError(
            f"repo root does not exist or is not a directory: {repo_root}"
        )

    result = run_cmd(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=repo_root,
        capture_output=True,
        debug=debug,
    )
    if result.returncode != 0:
        raise RunnerError(f"repo root is not a git repository: {repo_root}")

    resolved = Path(result.stdout.strip()).resolve()
    if resolved != repo_root.resolve():
        raise RunnerError(
            f"repo root must be repository top-level. expected={resolved} got={repo_root.resolve()}"
        )


def ensure_provider_available(provider: str) -> None:
    binaries = {
        "codex": "codex",
        "claude": "claude",
    }
    binary = binaries.get(provider)
    if not binary:
        raise RunnerError(f"Unsupported provider: {provider}")
    if not shutil_which(binary):
        raise RunnerError(
            f"{provider} executable ('{binary}') not found on PATH"
        )


def shutil_which(binary: str) -> str | None:
    for folder in os.environ.get("PATH", "").split(os.pathsep):
        candidate = Path(folder) / binary
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def normalize_repo_relative_path(raw_path: str) -> str:
    candidate = raw_path.replace("\\", "/").strip()
    if not candidate:
        raise RunnerError("task file entry cannot be empty")

    if candidate.startswith("/"):
        raise RunnerError(f"absolute task file path is not allowed: {raw_path}")

    drive_match = re.match(r"^[A-Za-z]:", candidate)
    if drive_match:
        raise RunnerError(f"absolute task file path is not allowed: {raw_path}")

    pure = PurePosixPath(candidate)
    if any(part == ".." for part in pure.parts):
        raise RunnerError(f"task file path cannot contain '..': {raw_path}")

    if pure.is_absolute() or str(pure) in {"", "."}:
        raise RunnerError(f"invalid task file path: {raw_path}")

    return str(pure)


def normalize_task(task: dict[str, Any], campaign_slug: str) -> dict[str, Any]:
    required = [
        "id",
        "slug",
        "area",
        "risk",
        "files",
        "tests",
        "commit_message",
        "task_artifact_markdown",
        "activation_prompt",
        "dependencies",
    ]
    missing = [field for field in required if field not in task]
    if missing:
        raise RunnerError(f"Task missing required fields: {', '.join(missing)}")

    task_id = str(task["id"]).strip()
    task_slug = str(task["slug"]).strip()
    if not task_id or not TASK_ID_PATTERN.fullmatch(task_id):
        raise RunnerError(f"Invalid task.id: {task_id}")
    if not task_slug or not TASK_SLUG_PATTERN.fullmatch(task_slug):
        raise RunnerError(f"Invalid task.slug: {task_slug}")

    risk = str(task["risk"]).strip().upper()
    if risk not in RISK_VALUES:
        raise RunnerError(f"Invalid task.risk for task {task_id}: {risk}")

    files_raw = task["files"]
    if not isinstance(files_raw, list):
        raise RunnerError(f"Task files must be an array: {task_id}")
    files = [normalize_repo_relative_path(str(entry)) for entry in files_raw]

    tests_raw = task["tests"]
    if not isinstance(tests_raw, list):
        raise RunnerError(f"Task tests must be an array: {task_id}")
    tests = [str(item) for item in tests_raw]

    dependencies_raw = task["dependencies"]
    if not isinstance(dependencies_raw, list):
        raise RunnerError(f"Task dependencies must be an array: {task_id}")
    dependencies = [str(item) for item in dependencies_raw]

    normalized = {
        "id": task_id,
        "slug": task_slug,
        "area": str(task["area"]).strip(),
        "risk": risk,
        "files": files,
        "tests": tests,
        "commit_message": str(task["commit_message"]).strip(),
        "task_artifact_markdown": str(task["task_artifact_markdown"]),
        "activation_prompt": str(task["activation_prompt"]),
        "dependencies": dependencies,
        "campaign_slug": campaign_slug,
    }
    if not normalized["commit_message"]:
        raise RunnerError(f"Task commit_message cannot be empty: {task_id}")

    return normalized


def task_hash(task: dict[str, Any]) -> str:
    payload = {
        "id": task["id"],
        "slug": task["slug"],
        "area": task["area"],
        "risk": task["risk"],
        "files": task["files"],
        "tests": task["tests"],
        "commit_message": task["commit_message"],
        "task_artifact_markdown": task["task_artifact_markdown"],
        "activation_prompt": task["activation_prompt"],
        "dependencies": task["dependencies"],
    }
    return sha256_text(canonical_json(payload))


def parse_campaign_id(campaign_id: str) -> tuple[str, str, str]:
    match = CAMPAIGN_ID_PATTERN.fullmatch(campaign_id)
    if not match:
        raise RunnerError(
            f"Invalid campaign_id '{campaign_id}'. Expected YYYY-MM-DD::campaign_slug::seq3"
        )
    return match.group("date"), match.group("slug"), match.group("seq")


def load_state(repo_root: Path) -> dict[str, Any]:
    path = repo_root / STATE_PATH
    if not path.exists():
        return {
            "version": 1,
            "campaigns": {},
            "task_index_by_id": {},
            "task_index_by_slug": {},
        }

    state = json_read(path)
    for key in (
        "version",
        "campaigns",
        "task_index_by_id",
        "task_index_by_slug",
    ):
        if key not in state:
            raise RunnerError(f"Invalid state file missing key: {key}")
    return state


def state_hash(state: dict[str, Any]) -> str:
    return sha256_text(canonical_json(state))


def append_transition(
    repo_root: Path,
    *,
    run_id: str,
    pass_index: int,
    reason: str,
    previous_state_sha: str,
    post_state_sha: str,
) -> None:
    payload = {
        "timestamp": now_iso(),
        "run_id": run_id,
        "pass_index": pass_index,
        "reason": reason,
        "previous_state_sha": previous_state_sha,
        "post_state_sha": post_state_sha,
    }
    transition_path = repo_root / STATE_TRANSITIONS_PATH
    transition_path.parent.mkdir(parents=True, exist_ok=True)
    with transition_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def save_state(repo_root: Path, state: dict[str, Any]) -> None:
    json_write(repo_root / STATE_PATH, state)


def merge_campaign_set(
    state: dict[str, Any],
    stage_b_payload: dict[str, Any],
    *,
    audit_id: str,
) -> dict[str, Any]:
    campaigns = stage_b_payload.get("campaigns")
    if not isinstance(campaigns, list):
        raise RunnerError("campaign_set payload missing campaigns[]")

    additions = {"campaigns": 0, "tasks": 0}

    for campaign in campaigns:
        if not isinstance(campaign, dict):
            raise RunnerError("campaign entry must be an object")

        campaign_id = str(campaign.get("campaign_id") or "").strip()
        campaign_slug = str(campaign.get("campaign_slug") or "").strip()
        if not campaign_id or not campaign_slug:
            raise RunnerError("campaign requires campaign_id and campaign_slug")

        campaign_date, slug_from_id, campaign_seq = parse_campaign_id(
            campaign_id
        )
        if slug_from_id != campaign_slug:
            raise RunnerError(
                f"campaign_id slug mismatch for {campaign_id}: expected {slug_from_id}, got {campaign_slug}"
            )

        depends_on_raw = campaign.get("depends_on", [])
        if not isinstance(depends_on_raw, list):
            raise RunnerError(
                f"campaign depends_on must be an array: {campaign_id}"
            )
        depends_on = [
            str(item).strip() for item in depends_on_raw if str(item).strip()
        ]
        for dep in depends_on:
            parse_campaign_id(dep)

        campaign_markdown = str(campaign.get("campaign_markdown") or "")
        tasks_raw = campaign.get("tasks")
        if not isinstance(tasks_raw, list):
            raise RunnerError(f"campaign.tasks must be an array: {campaign_id}")

        discovery_reason = campaign.get("discovery_reason")
        if len(tasks_raw) == 0:
            if (
                not isinstance(discovery_reason, str)
                or not discovery_reason.strip()
            ):
                raise RunnerError(
                    f"campaign {campaign_id} has empty tasks but no non-empty discovery_reason"
                )

        existing = state["campaigns"].get(campaign_id)
        if existing is None:
            existing = {
                "campaign_id": campaign_id,
                "campaign_slug": campaign_slug,
                "campaign_date": campaign_date,
                "campaign_seq": campaign_seq,
                "depends_on": depends_on,
                "campaign_markdown": campaign_markdown,
                "discovery_reason": discovery_reason
                if isinstance(discovery_reason, str)
                else None,
                "tasks": {},
                "status": "open",
                "source_audit_ids": [audit_id],
                "materialized": {
                    "campaign_doc_path": None,
                    "task_artifact_paths": {},
                },
            }
            state["campaigns"][campaign_id] = existing
            additions["campaigns"] += 1
        else:
            immutable_pairs = [
                (existing["campaign_slug"], campaign_slug, "campaign_slug"),
                (existing["campaign_date"], campaign_date, "campaign_date"),
                (existing["campaign_seq"], campaign_seq, "campaign_seq"),
            ]
            for previous, incoming, field_name in immutable_pairs:
                if previous != incoming:
                    raise RunnerError(
                        f"campaign mutation detected for {campaign_id} field {field_name}"
                    )
            if existing.get("depends_on") != depends_on:
                raise RunnerError(
                    f"campaign mutation detected for depends_on: {campaign_id}"
                )
            if existing.get("campaign_markdown") != campaign_markdown:
                raise RunnerError(
                    f"campaign mutation detected for campaign_markdown: {campaign_id}"
                )
            if isinstance(discovery_reason, str):
                previous_reason = existing.get("discovery_reason")
                if previous_reason is None:
                    existing["discovery_reason"] = discovery_reason
                elif previous_reason != discovery_reason:
                    raise RunnerError(
                        f"campaign mutation detected for discovery_reason: {campaign_id}"
                    )
            if audit_id not in existing["source_audit_ids"]:
                existing["source_audit_ids"].append(audit_id)

        seen_ids: set[str] = set()
        seen_slugs: set[str] = set()
        for raw_task in tasks_raw:
            if not isinstance(raw_task, dict):
                raise RunnerError(
                    f"task entry must be object in campaign {campaign_id}"
                )
            normalized_task = normalize_task(raw_task, campaign_slug)
            task_id = normalized_task["id"]
            task_slug = normalized_task["slug"]

            if task_id in seen_ids:
                raise RunnerError(
                    f"duplicate task.id in campaign payload: {campaign_id}/{task_id}"
                )
            seen_ids.add(task_id)
            if task_slug in seen_slugs:
                raise RunnerError(
                    f"duplicate task.slug in campaign payload: {campaign_id}/{task_slug}"
                )
            seen_slugs.add(task_slug)

            digest = task_hash(normalized_task)
            by_id = state["task_index_by_id"].get(task_id)
            if by_id and by_id["content_hash"] != digest:
                raise RunnerError(
                    f"task mutation conflict on id {task_id}: existing hash differs"
                )

            by_slug_key = f"{campaign_slug}::{task_slug}"
            by_slug = state["task_index_by_slug"].get(by_slug_key)
            if by_slug and by_slug["content_hash"] != digest:
                raise RunnerError(
                    f"task mutation conflict on slug {campaign_slug}/{task_slug}: existing hash differs"
                )

            existing_task = existing["tasks"].get(task_id)
            if existing_task is None:
                existing_task = {
                    **normalized_task,
                    "content_hash": digest,
                    "status": "pending",
                    "implementation_commit": None,
                    "receipt_commit": None,
                    "result": None,
                }
                existing["tasks"][task_id] = existing_task
                additions["tasks"] += 1
            else:
                if existing_task.get("content_hash") != digest:
                    raise RunnerError(
                        f"task mutation conflict on id {task_id} in campaign {campaign_id}"
                    )

            state["task_index_by_id"][task_id] = {
                "campaign_id": campaign_id,
                "content_hash": digest,
            }
            state["task_index_by_slug"][by_slug_key] = {
                "campaign_id": campaign_id,
                "task_id": task_id,
                "content_hash": digest,
            }

    return additions


def campaign_is_completed(campaign: dict[str, Any]) -> bool:
    tasks: dict[str, dict[str, Any]] = campaign.get("tasks", {})
    if not tasks:
        return False
    return all(task.get("status") == "success" for task in tasks.values())


def selectable_campaigns(state: dict[str, Any]) -> list[dict[str, Any]]:
    campaigns: list[dict[str, Any]] = []
    for campaign in state["campaigns"].values():
        if campaign.get("status") == "completed":
            continue
        campaigns.append(campaign)
    return campaigns


def dependencies_satisfied(
    state: dict[str, Any], campaign: dict[str, Any]
) -> bool:
    for dep in campaign.get("depends_on", []):
        dep_campaign = state["campaigns"].get(dep)
        if dep_campaign is None:
            return False
        if dep_campaign.get("status") != "completed":
            return False
    return True


def high_risk_count(campaign: dict[str, Any]) -> int:
    total = 0
    for task in campaign.get("tasks", {}).values():
        if task.get("status") == "success":
            continue
        if str(task.get("risk") or "").upper() == "HIGH":
            total += 1
    return total


def select_campaign(state: dict[str, Any]) -> SelectedCampaign | None:
    candidates: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
    for campaign in selectable_campaigns(state):
        if not dependencies_satisfied(state, campaign):
            continue
        campaign_date = campaign["campaign_date"]
        campaign_slug = campaign["campaign_slug"]
        score = (-high_risk_count(campaign), campaign_date, campaign_slug)
        candidates.append((score, campaign))

    if not candidates:
        return None

    candidates.sort(key=lambda item: item[0])
    _, winner = candidates[0]
    return SelectedCampaign(
        campaign_id=winner["campaign_id"],
        campaign_slug=winner["campaign_slug"],
        reason={
            "rule": "highest_high_risk_then_date_then_slug",
            "high_risk_count": high_risk_count(winner),
            "campaign_date": winner["campaign_date"],
            "campaign_slug": winner["campaign_slug"],
        },
    )


def to_upper_snake(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", value.strip())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned.upper() or "CAMPAIGN"


def to_lower_snake(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", value.strip().lower())
    return re.sub(r"_+", "_", cleaned).strip("_") or "task"


def safe_task_id_for_path(task_id: str) -> str:
    lowered = task_id.lower()
    safe = re.sub(r"[^a-z0-9_-]+", "-", lowered)
    safe = re.sub(r"-{2,}", "-", safe).strip("-") or "task"
    if safe != lowered:
        safe = f"{safe}-{sha256_text(task_id)[:8]}"
    return safe


def ensure_mapping_block(text: str) -> str:
    if MAPPING_START in text and MAPPING_END in text:
        return text
    base = text.rstrip()
    return f"{base}\n\n{MAPPING_START}\n{MAPPING_END}\n"


def parse_mapping_entries(block: str) -> dict[str, tuple[str, str]]:
    entries: dict[str, tuple[str, str]] = {}
    for line in block.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        match = re.fullmatch(
            r"([^\s]+)\s*->\s*\[([^,]+),\s*([^\]]+)\]", stripped
        )
        if not match:
            continue
        entries[match.group(1)] = (
            match.group(2).strip(),
            match.group(3).strip(),
        )
    return entries


def update_mapping_block(
    campaign_doc_path: Path, task_id: str, impl_hash: str, receipt_hash: str
) -> None:
    content = (
        campaign_doc_path.read_text(encoding="utf-8")
        if campaign_doc_path.exists()
        else ""
    )
    content = ensure_mapping_block(content)

    start_idx = content.find(MAPPING_START)
    end_idx = content.find(MAPPING_END)
    if start_idx == -1 or end_idx == -1 or end_idx < start_idx:
        raise RunnerError(f"Invalid mapping block in {campaign_doc_path}")

    block_start = start_idx + len(MAPPING_START)
    current_block = content[block_start:end_idx]
    entries = parse_mapping_entries(current_block)
    entries[task_id] = (impl_hash, receipt_hash)

    lines = [
        f"{key} -> [{value[0]}, {value[1]}]"
        for key, value in sorted(entries.items())
    ]
    new_block = "\n" + "\n".join(lines) + ("\n" if lines else "")
    updated = content[:block_start] + new_block + content[end_idx:]
    text_write(campaign_doc_path, updated)


def materialize_campaign_artifacts(
    repo_root: Path, campaign: dict[str, Any]
) -> list[str]:
    touched: list[str] = []
    date_underscore = campaign["campaign_date"].replace("-", "_")
    slug = campaign["campaign_slug"]
    seq = campaign["campaign_seq"]

    campaign_doc_name = (
        f"CAMPAIGN_{date_underscore}_{to_upper_snake(slug)}_{seq}.md"
    )
    campaign_doc_path = repo_root / DEFAULT_CAMPAIGN_DIR / campaign_doc_name
    campaign_doc_content = ensure_mapping_block(campaign["campaign_markdown"])
    if not campaign_doc_path.exists():
        text_write(campaign_doc_path, campaign_doc_content)
        touched.append(
            str((DEFAULT_CAMPAIGN_DIR / campaign_doc_name).as_posix())
        )

    campaign["materialized"]["campaign_doc_path"] = str(
        (DEFAULT_CAMPAIGN_DIR / campaign_doc_name).as_posix()
    )

    task_dir_rel = DEFAULT_TASKS_DIR / f"{slug}_{date_underscore}_{seq}"
    task_dir_abs = repo_root / task_dir_rel
    task_dir_abs.mkdir(parents=True, exist_ok=True)

    for task in sorted(campaign["tasks"].values(), key=lambda item: item["id"]):
        task_id = str(task["id"])
        safe_task_id = safe_task_id_for_path(task_id)
        task_file_name = (
            f"TASK_{safe_task_id}_{to_lower_snake(task['slug'])}.md"
        )
        task_rel = task_dir_rel / task_file_name
        task_abs = repo_root / task_rel
        if not task_abs.exists():
            content = task["task_artifact_markdown"].rstrip() + "\n"
            text_write(task_abs, content)
            touched.append(str(task_rel.as_posix()))
        campaign["materialized"]["task_artifact_paths"][task_id] = str(
            task_rel.as_posix()
        )

    return touched


def branch_name_for_campaign(campaign: dict[str, Any]) -> str:
    safe_slug = re.sub(r"[^a-z0-9_-]+", "-", campaign["campaign_slug"].lower())
    safe_slug = re.sub(r"-{2,}", "-", safe_slug).strip("-") or "campaign"
    return f"campaign/{campaign['campaign_date']}/{safe_slug}-{campaign['campaign_seq']}"


def allowed_path(path: str, allowed_patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(path, pattern) for pattern in allowed_patterns)


def enforce_scope_guard(
    repo_root: Path,
    task: dict[str, Any],
    *,
    task_artifact_path: str,
    run_artifact_allowlist: list[str],
    debug: bool,
) -> list[str]:
    changed = git_changed_paths(repo_root, debug)
    allowed_patterns = (
        list(task["files"]) + [task_artifact_path] + run_artifact_allowlist
    )

    out_of_scope = [
        path for path in changed if not allowed_path(path, allowed_patterns)
    ]
    if out_of_scope:
        raise RunnerError(
            "out-of-scope files changed for task "
            f"{task['id']}: {', '.join(out_of_scope)}"
        )
    return changed


def render_audit_prompt(
    template: str, repo_root: Path, audit_id: str, run_id: str
) -> str:
    rendered = template
    rendered = rendered.replace(DEFAULT_REPO_ROOT_TOKEN, str(repo_root))
    rendered = rendered.replace(DEFAULT_AUDIT_ID_TOKEN, audit_id)
    rendered = rendered.replace("{{AUDIT_ID}}", audit_id)
    rendered = rendered.replace("<RUN_ID>", run_id)
    rendered = rendered.replace("{{RUN_ID}}", run_id)

    if (
        DEFAULT_AUDIT_ID_TOKEN not in template
        and "{{AUDIT_ID}}" not in template
    ):
        rendered = (
            "Runner Constraints:\n"
            f"- audit_id must equal {audit_id}\n"
            "- Output JSON only\n\n" + rendered
        )
    return rendered


def render_compiler_prompt(
    template: str, repo_root: Path, mega_payload: dict[str, Any]
) -> str:
    mega_json = json.dumps(mega_payload, indent=2, ensure_ascii=False)
    rendered = template.replace(DEFAULT_REPO_ROOT_TOKEN, str(repo_root))
    rendered = rendered.replace(DEFAULT_COMPILER_JSON_TOKEN, mega_json)
    rendered = rendered.replace("<AUDIT_JSON>", mega_json)
    if (
        DEFAULT_COMPILER_JSON_TOKEN not in template
        and "<AUDIT_JSON>" not in template
    ):
        rendered = rendered + "\n\nMEGA_AUDIT_JSON:\n" + mega_json
    return rendered


def _schema_required_keys(schema: dict[str, Any]) -> set[str]:
    required = schema.get("required")
    if not isinstance(required, list):
        return set()
    keys: set[str] = set()
    for key in required:
        if isinstance(key, str) and key:
            keys.add(key)
    return keys


def _strip_schema_keyword(
    value: Any, *, keyword: str, removed: dict[str, int]
) -> Any:
    if isinstance(value, dict):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if key == keyword:
                removed[keyword] = removed.get(keyword, 0) + 1
                _strip_schema_keyword(item, keyword=keyword, removed=removed)
                continue
            normalized[key] = _strip_schema_keyword(
                item, keyword=keyword, removed=removed
            )
        return normalized
    if isinstance(value, list):
        return [
            _strip_schema_keyword(item, keyword=keyword, removed=removed)
            for item in value
        ]
    return value


def codex_compat_schema(
    schema_payload: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, int]]:
    """
    OpenAI response-format schema support rejects some JSON-Schema keywords
    (notably allOf). We strip unsupported keys for provider-side validation;
    runner merge validation still enforces deterministic constraints.
    """
    removed: dict[str, int] = {}
    normalized = _strip_schema_keyword(
        schema_payload, keyword="allOf", removed=removed
    )
    if not isinstance(normalized, dict):
        raise RunnerError("Expected schema payload to remain an object")
    return normalized, removed


def ensure_response_format_schema_compat(
    schema_payload: dict[str, Any]
) -> None:
    """
    OpenAI response_format requires every object that defines `properties`
    to list all of those keys in `required`.
    """

    violations: list[tuple[str, list[str]]] = []

    def walk(value: Any, path: str) -> None:
        if isinstance(value, dict):
            properties = value.get("properties")
            if isinstance(properties, dict):
                property_keys = sorted(
                    key for key in properties.keys() if isinstance(key, str)
                )
                required = value.get("required")
                required_keys = (
                    {key for key in required if isinstance(key, str) and key}
                    if isinstance(required, list)
                    else set()
                )
                missing = [
                    key for key in property_keys if key not in required_keys
                ]
                if missing:
                    violations.append((path, missing))

            for key, item in value.items():
                next_path = f"{path}.{key}" if path != "$" else f"$.{key}"
                walk(item, next_path)
            return

        if isinstance(value, list):
            for idx, item in enumerate(value):
                walk(item, f"{path}[{idx}]")

    walk(schema_payload, "$")

    if violations:
        details = "; ".join(
            f"{path} missing required keys: {', '.join(missing)}"
            for path, missing in violations
        )
        raise RunnerError(
            "Schema is incompatible with OpenAI response_format: "
            "every object with properties must include all property keys "
            f"in required. {details}"
        )


def _parse_json_with_fallback(raw_output: str, provider: str) -> Any:
    text = raw_output.strip()
    if not text:
        raise RunnerError(f"{provider} returned empty output")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        decoder = json.JSONDecoder()
        best: Any = None
        for idx, char in enumerate(text):
            if char not in "[{":
                continue
            try:
                value, _ = decoder.raw_decode(text[idx:])
            except json.JSONDecodeError:
                continue
            best = value
        if best is not None:
            return best
    raise RunnerError(
        f"{provider} output was not valid JSON. "
        "Expected structured JSON because schema output is required."
    )


def _candidate_payload_dicts(raw_value: Any) -> list[dict[str, Any]]:
    queue: list[Any] = [raw_value]
    seen_objects: set[int] = set()
    seen_strings: set[str] = set()
    candidates: list[dict[str, Any]] = []

    while queue:
        current = queue.pop(0)
        if isinstance(current, dict):
            marker = id(current)
            if marker in seen_objects:
                continue
            seen_objects.add(marker)
            candidates.append(current)
            for key in ("result", "output", "response", "data", "message"):
                if key in current:
                    queue.append(current[key])
            if "content" in current:
                queue.append(current["content"])
            continue
        if isinstance(current, list):
            queue.extend(current)
            continue
        if isinstance(current, str):
            text = current.strip()
            if not text or text in seen_strings or text[0] not in "{[":
                continue
            seen_strings.add(text)
            try:
                queue.append(json.loads(text))
            except json.JSONDecodeError:
                continue
    return candidates


def _select_payload(
    candidates: list[dict[str, Any]],
    required_keys: set[str],
) -> dict[str, Any]:
    if not candidates:
        raise RunnerError("No JSON object payload found in provider response")

    def score(payload: dict[str, Any]) -> int:
        keys = set(payload.keys())
        value = len(required_keys & keys) * 10
        if required_keys and required_keys.issubset(keys):
            value += 1000
        for hint in ("status", "campaigns", "audit_id"):
            if hint in payload:
                value += 3
        if required_keys and not required_keys.issubset(keys):
            if {"type", "id", "usage", "session_id"} & keys:
                value -= 2
        return value

    chosen = max(candidates, key=score)
    if required_keys and not required_keys.issubset(chosen.keys()):
        missing = sorted(required_keys - set(chosen.keys()))
        raise RunnerError(
            "Provider output missing required keys from schema: "
            + ", ".join(missing)
        )
    return chosen


def run_codex_exec(
    repo_root: Path,
    *,
    prompt_text: str,
    output_schema: Path,
    output_path: Path,
    model: str | None,
    configs: list[str],
    debug: bool,
) -> None:
    schema_payload = json_read(output_schema)
    schema_for_codex, removed = codex_compat_schema(schema_payload)
    ensure_response_format_schema_compat(schema_for_codex)
    effective_schema_path = output_schema
    tmp_schema_dir: tempfile.TemporaryDirectory[str] | None = None
    if removed.get("allOf", 0) > 0:
        tmp_schema_dir = tempfile.TemporaryDirectory(
            prefix="codex_schema_compat_"
        )
        effective_schema_path = (
            Path(tmp_schema_dir.name)
            / f"{output_schema.stem}.codex_compat.schema.json"
        )
        json_write(effective_schema_path, schema_for_codex)
        if debug:
            log(
                "[debug] codex schema compatibility rewrite: "
                f"removed allOf={removed['allOf']} from {output_schema}"
            )

    cmd: list[str] = ["codex"]
    if model:
        cmd.extend(["--model", model])
    for config in configs:
        cmd.extend(["--config", config])

    cmd.extend(
        [
            "exec",
            "--output-schema",
            str(effective_schema_path),
            "-o",
            str(output_path),
            prompt_text,
        ]
    )
    try:
        result = run_cmd(cmd, cwd=repo_root, capture_output=True, debug=debug)
    finally:
        if tmp_schema_dir is not None:
            tmp_schema_dir.cleanup()
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        stdout = (result.stdout or "").strip()
        raise RunnerError(
            "codex exec failed"
            + (f"\nSTDERR:\n{stderr}" if stderr else "")
            + (f"\nSTDOUT:\n{stdout}" if stdout else "")
        )


def run_claude_exec(
    repo_root: Path,
    *,
    prompt_text: str,
    output_schema: Path,
    output_path: Path,
    model: str | None,
    settings: list[str],
    debug: bool,
) -> None:
    schema_payload = json_read(output_schema)
    required_keys = _schema_required_keys(schema_payload)
    schema_json = canonical_json(schema_payload)

    cmd: list[str] = [
        "claude",
        "-p",
        "--output-format",
        "json",
        "--json-schema",
        schema_json,
    ]
    if model:
        cmd.extend(["--model", model])
    for setting in settings:
        cmd.extend(["--settings", setting])
    cmd.append(prompt_text)

    result = run_cmd(cmd, cwd=repo_root, capture_output=True, debug=debug)
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        stdout = (result.stdout or "").strip()
        raise RunnerError(
            "claude exec failed"
            + (f"\nSTDERR:\n{stderr}" if stderr else "")
            + (f"\nSTDOUT:\n{stdout}" if stdout else "")
        )

    parsed = _parse_json_with_fallback(result.stdout or "", "claude")
    payload = _select_payload(_candidate_payload_dicts(parsed), required_keys)
    json_write(output_path, payload)


def run_provider_exec(
    repo_root: Path,
    *,
    provider: str,
    prompt_text: str,
    output_schema: Path,
    output_path: Path,
    model: str | None,
    settings: list[str],
    debug: bool,
) -> None:
    if provider == "codex":
        run_codex_exec(
            repo_root,
            prompt_text=prompt_text,
            output_schema=output_schema,
            output_path=output_path,
            model=model,
            configs=settings,
            debug=debug,
        )
        return
    if provider == "claude":
        run_claude_exec(
            repo_root,
            prompt_text=prompt_text,
            output_schema=output_schema,
            output_path=output_path,
            model=model,
            settings=settings,
            debug=debug,
        )
        return
    raise RunnerError(f"Unsupported provider: {provider}")


def append_implementation_receipt(
    task_artifact_abs: Path, run_id: str, task_id: str, status_hint: str
) -> None:
    block = (
        "\n\n## Implementation Receipt (Runner)\n\n"
        f"- run_id: {run_id}\n"
        f"- task_id: {task_id}\n"
        f"- status_hint: {status_hint}\n"
        "- implementation_commit_hash: (pending)\n"
    )
    text_append(task_artifact_abs, block)


def append_completion_summary(
    task_artifact_abs: Path,
    *,
    status: str,
    tests_ran: list[str],
    implementation_commit_hash: str,
    receipt_commit_hash: str,
    summary: str,
    notes: str,
) -> None:
    tests_line = ", ".join(tests_ran) if tests_ran else "(none)"
    block = (
        "\n\n## Completion Summary (Runner)\n\n"
        f"- status: {status}\n"
        f"- tests_ran: {tests_line}\n"
        f"- implementation_commit_hash: {implementation_commit_hash}\n"
        f"- receipt_commit_hash: {receipt_commit_hash}\n"
        f"- summary: {summary or '(none)'}\n"
        f"- notes: {notes or '(none)'}\n"
    )
    text_append(task_artifact_abs, block)


def default_verify(ci_env: str | None) -> bool:
    if not ci_env:
        return False
    return ci_env.strip().lower() in {"1", "true", "yes", "on"}


def provider_settings(args: argparse.Namespace) -> list[str]:
    if args.provider == "codex":
        return list(args.codex_config)
    if args.provider == "claude":
        return list(args.claude_settings)
    raise RunnerError(f"Unsupported provider: {args.provider}")


def provider_model_for_stage(
    args: argparse.Namespace, stage: str
) -> str | None:
    if args.provider == "codex":
        if stage == "audit":
            return args.codex_model_audit or args.codex_model
        if stage == "compiler":
            return args.codex_model_compiler or args.codex_model
        if stage == "task":
            return args.codex_model_task or args.codex_model
    if args.provider == "claude":
        if stage == "audit":
            return args.claude_model_audit or args.claude_model
        if stage == "compiler":
            return args.claude_model_compiler or args.claude_model
        if stage == "task":
            return args.claude_model_task or args.claude_model
    raise RunnerError(
        f"Unsupported provider/stage combination: {args.provider}/{stage}"
    )


def provider_model_map(args: argparse.Namespace) -> dict[str, str | None]:
    default_model = (
        args.codex_model if args.provider == "codex" else args.claude_model
    )
    return {
        "default": default_model,
        "audit": provider_model_for_stage(args, "audit"),
        "compiler": provider_model_for_stage(args, "compiler"),
        "task": provider_model_for_stage(args, "task"),
    }


def sanitize_provider_settings(settings: list[str]) -> list[str]:
    redacted_markers = {"token", "secret", "password", "key"}
    sanitized: list[str] = []
    for entry in settings:
        lowered = entry.lower()
        if any(marker in lowered for marker in redacted_markers):
            if "=" in entry:
                key = entry.split("=", 1)[0]
                sanitized.append(f"{key}=<redacted>")
            else:
                sanitized.append("<redacted>")
            continue
        sanitized.append(entry)
    return sanitized


def run_inputs_payload(
    *,
    repo_root: Path,
    base_ref_sha: str,
    hashes: StageHashes,
    pass_index: int,
    execute_mode: str,
    provider: str,
) -> dict[str, Any]:
    return {
        "repo_root": str(repo_root.resolve()),
        "base_ref": base_ref_sha,
        "provider": provider,
        "audit_prompt_sha256": hashes.audit_prompt_sha256,
        "audit_schema_sha256": hashes.audit_schema_sha256,
        "compiler_prompt_sha256": hashes.compiler_prompt_sha256,
        "campaign_set_schema_sha256": hashes.campaign_set_schema_sha256,
        "pass_index": pass_index,
        "execute_mode": execute_mode,
    }


def write_run_meta(
    path: Path,
    *,
    run_id: str,
    audit_id: str,
    base_ref_sha: str,
    hashes: StageHashes,
    audit_prompt_file: Path,
    audit_schema_file: Path,
    compiler_prompt_file: Path,
    campaign_set_schema_file: Path,
    cli_args: list[str],
    preflight_clean: bool,
    selected_campaign: str | None,
    selection_rationale: dict[str, Any] | None,
    termination_reason: str,
    provider: str,
    provider_models: dict[str, str | None],
    provider_settings_sanitized: list[str],
) -> None:
    payload = {
        "run_id": run_id,
        "audit_id": audit_id,
        "generated_at": now_iso(),
        "resolved_base_ref_sha": base_ref_sha,
        "inputs": {
            "audit_prompt_file": str(audit_prompt_file.resolve()),
            "audit_schema_file": str(audit_schema_file.resolve()),
            "compiler_prompt_file": str(compiler_prompt_file.resolve()),
            "campaign_set_schema_file": str(campaign_set_schema_file.resolve()),
            "audit_prompt_sha256": hashes.audit_prompt_sha256,
            "audit_schema_sha256": hashes.audit_schema_sha256,
            "compiler_prompt_sha256": hashes.compiler_prompt_sha256,
            "campaign_set_schema_sha256": hashes.campaign_set_schema_sha256,
        },
        "cli_args": cli_args,
        "preflight": {
            "git_clean": preflight_clean,
        },
        "selection": {
            "selected_campaign": selected_campaign,
            "rationale": selection_rationale,
        },
        "provider": {
            "name": provider,
            "models": provider_models,
            "settings": provider_settings_sanitized,
        },
        "termination_reason": termination_reason,
    }
    json_write(path, payload)


def run_task_agent(
    *,
    repo_root: Path,
    task: dict[str, Any],
    task_result_schema_file: Path,
    provider: str,
    model: str | None,
    settings: list[str],
    debug: bool,
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_root = Path(tmpdir)
        output = tmp_root / "task_result.json"
        run_provider_exec(
            repo_root,
            provider=provider,
            prompt_text=str(task["activation_prompt"]),
            output_schema=task_result_schema_file,
            output_path=output,
            model=model,
            settings=settings,
            debug=debug,
        )
        payload = json_read(output)

    status = str(payload.get("status") or "").strip().lower()
    if status not in TASK_RESULT_STATUS_VALUES:
        raise RunnerError(
            f"Invalid task_result status for task {task['id']}: {status}"
        )

    tests_ran = payload.get("tests_ran")
    if not isinstance(tests_ran, list):
        raise RunnerError(
            f"task_result.tests_ran must be array for task {task['id']}"
        )

    notes = str(payload.get("notes") or "")
    summary = str(payload.get("summary") or "")

    return {
        "status": status,
        "summary": summary,
        "tests_ran": [str(item) for item in tests_ran],
        "notes": notes,
    }


def ensure_audit_id(audit_payload: dict[str, Any], audit_id: str) -> None:
    observed = str(audit_payload.get("audit_id") or "").strip()
    if observed != audit_id:
        raise RunnerError(
            f"Stage A audit_id mismatch. expected={audit_id} got={observed}"
        )


def update_campaign_completion(campaign: dict[str, Any]) -> None:
    campaign["status"] = (
        "completed" if campaign_is_completed(campaign) else "open"
    )


def run_pass(
    args: argparse.Namespace,
    *,
    pass_index: int,
    base_ref_sha: str,
    cli_args: list[str],
) -> None:
    repo_root = args.repo_root
    active_settings = provider_settings(args)
    active_models = provider_model_map(args)
    active_settings_sanitized = sanitize_provider_settings(active_settings)
    preflight_clean = git_is_clean(repo_root, args.debug)
    if not preflight_clean:
        raise RunnerError("preflight failed: git tree is not clean")

    hashes = StageHashes(
        audit_prompt_sha256=sha256_file(args.audit_prompt_file),
        audit_schema_sha256=sha256_file(args.audit_schema_file),
        compiler_prompt_sha256=sha256_file(args.compiler_prompt_file),
        campaign_set_schema_sha256=sha256_file(args.campaign_set_schema_file),
    )

    run_inputs = run_inputs_payload(
        repo_root=repo_root,
        base_ref_sha=base_ref_sha,
        hashes=hashes,
        pass_index=pass_index,
        execute_mode="execute"
        if args.execute and not args.dry_run
        else "dry-run",
        provider=args.provider,
    )
    run_id = sha256_text(canonical_json(run_inputs))[:12]
    audit_id = f"AUDIT_{run_id}"

    today_iso = datetime.now(timezone.utc).date().isoformat()
    audit_dir_rel = DEFAULT_AUDITS_DIR / today_iso / audit_id
    audit_dir_abs = repo_root / audit_dir_rel
    audit_dir_abs.mkdir(parents=True, exist_ok=True)
    json_write(audit_dir_abs / "run_inputs.json", run_inputs)

    audit_prompt_template = args.audit_prompt_file.read_text(encoding="utf-8")
    audit_prompt_text = render_audit_prompt(
        audit_prompt_template, repo_root, audit_id, run_id
    )
    text_write(audit_dir_abs / "audit_input_prompt.md", audit_prompt_text)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_root = Path(tmpdir)
        stage_a_output_path = tmp_root / "audit_output.json"
        run_provider_exec(
            repo_root,
            provider=args.provider,
            prompt_text=audit_prompt_text,
            output_schema=args.audit_schema_file,
            output_path=stage_a_output_path,
            model=active_models["audit"],
            settings=active_settings,
            debug=args.debug,
        )
        audit_payload = json_read(stage_a_output_path)

    ensure_audit_id(audit_payload, audit_id)
    json_write(audit_dir_abs / "audit_output.json", audit_payload)

    compiler_template = args.compiler_prompt_file.read_text(encoding="utf-8")
    compiler_prompt_text = render_compiler_prompt(
        compiler_template, repo_root, audit_payload
    )
    text_write(audit_dir_abs / "compiler_input_prompt.md", compiler_prompt_text)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_root = Path(tmpdir)
        stage_b_output_path = tmp_root / "campaign_set_output.json"
        run_provider_exec(
            repo_root,
            provider=args.provider,
            prompt_text=compiler_prompt_text,
            output_schema=args.campaign_set_schema_file,
            output_path=stage_b_output_path,
            model=active_models["compiler"],
            settings=active_settings,
            debug=args.debug,
        )
        campaign_set_payload = json_read(stage_b_output_path)

    stage_b_audit_id = str(campaign_set_payload.get("audit_id") or "").strip()
    if stage_b_audit_id and stage_b_audit_id != audit_id:
        raise RunnerError(
            f"Stage B audit_id mismatch. expected={audit_id} got={stage_b_audit_id}"
        )

    json_write(audit_dir_abs / "campaign_set_output.json", campaign_set_payload)

    state = load_state(repo_root)
    previous_sha = state_hash(state)
    merge_stats = merge_campaign_set(
        state, campaign_set_payload, audit_id=audit_id
    )

    selection = select_campaign(state)
    selected_campaign_slug = selection.campaign_slug if selection else "none"
    selected_campaign_id = selection.campaign_id if selection else None
    selection_reason = selection.reason if selection else None

    run_dir_rel = DEFAULT_RUNS_DIR / today_iso / selected_campaign_slug / run_id
    run_dir_abs = repo_root / run_dir_rel
    run_dir_abs.mkdir(parents=True, exist_ok=True)

    json_write(run_dir_abs / "run_inputs.json", run_inputs)
    json_write(run_dir_abs / "campaign_set_output.json", campaign_set_payload)

    termination_reason = "in_progress"
    run_trace: dict[str, Any] = {
        "run_id": run_id,
        "audit_id": audit_id,
        "pass_index": pass_index,
        "base_ref_sha": base_ref_sha,
        "generated_at": now_iso(),
        "merge_stats": merge_stats,
        "selection": {
            "campaign_id": selected_campaign_id,
            "campaign_slug": selected_campaign_slug,
            "reason": selection_reason,
        },
        "events": [],
        "termination_reason": None,
    }

    run_meta_kwargs = dict(
        run_id=run_id,
        audit_id=audit_id,
        base_ref_sha=base_ref_sha,
        hashes=hashes,
        audit_prompt_file=args.audit_prompt_file,
        audit_schema_file=args.audit_schema_file,
        compiler_prompt_file=args.compiler_prompt_file,
        campaign_set_schema_file=args.campaign_set_schema_file,
        cli_args=cli_args,
        preflight_clean=preflight_clean,
        selected_campaign=selected_campaign_id,
        selection_rationale=selection_reason,
        termination_reason=termination_reason,
        provider=args.provider,
        provider_models=active_models,
        provider_settings_sanitized=active_settings_sanitized,
    )
    write_run_meta(audit_dir_abs / "run_meta.json", **run_meta_kwargs)
    write_run_meta(run_dir_abs / "run_meta.json", **run_meta_kwargs)

    materialized_paths: list[str] = []
    executed_tasks = 0

    if selection is None:
        if merge_stats["campaigns"] == 0 and merge_stats["tasks"] == 0:
            termination_reason = "no_campaigns_produced_this_pass"
        else:
            termination_reason = "no_eligible_campaigns_in_state"
        run_trace["events"].append(
            {"type": "termination", "reason": termination_reason}
        )
    else:
        campaign = state["campaigns"][selection.campaign_id]

        if args.branch_per_campaign:
            ensure_clean_git(
                "before campaign branch switch", repo_root, args.debug
            )
            branch_name = branch_name_for_campaign(campaign)
            git_switch(repo_root, branch_name, create=True, debug=args.debug)
            ensure_clean_git(
                "after campaign branch switch", repo_root, args.debug
            )
            run_trace["events"].append(
                {"type": "branch_switch", "branch": branch_name}
            )

        materialized_paths = materialize_campaign_artifacts(repo_root, campaign)

        task_ids = sorted(campaign["tasks"].keys())
        if not task_ids:
            if args.allow_discovery_fallback:
                discovery_task_id = (
                    f"discovery::{campaign['campaign_slug']}::{run_id}"
                )
                discovery_task = {
                    "id": discovery_task_id,
                    "slug": "discovery",
                    "area": "docs",
                    "risk": "LOW",
                    "files": [],
                    "tests": [],
                    "commit_message": f"runner: discovery placeholder {campaign['campaign_slug']}",
                    "task_artifact_markdown": (
                        f"# Discovery Task\n\n"
                        f"- campaign_id: {campaign['campaign_id']}\n"
                        f"- run_id: {run_id}\n\n"
                        f"Reason: {campaign.get('discovery_reason') or 'discovery fallback requested'}\n"
                    ),
                    "activation_prompt": "Discovery fallback task. Do not execute code changes.",
                    "dependencies": [],
                    "content_hash": sha256_text("discovery" + run_id),
                    "status": "pending",
                    "implementation_commit": None,
                    "receipt_commit": None,
                }
                campaign["tasks"][discovery_task_id] = discovery_task
                state["task_index_by_id"][discovery_task_id] = {
                    "campaign_id": campaign["campaign_id"],
                    "content_hash": discovery_task["content_hash"],
                }
                state["task_index_by_slug"][
                    f"{campaign['campaign_slug']}::discovery"
                ] = {
                    "campaign_id": campaign["campaign_id"],
                    "task_id": discovery_task_id,
                    "content_hash": discovery_task["content_hash"],
                }

                materialized_paths.extend(
                    materialize_campaign_artifacts(repo_root, campaign)
                )

                task_artifact_rel = campaign["materialized"][
                    "task_artifact_paths"
                ][discovery_task_id]
                task_artifact_abs = repo_root / task_artifact_rel
                append_implementation_receipt(
                    task_artifact_abs, run_id, discovery_task_id, "blocked"
                )
                impl_hash = git_commit(
                    repo_root,
                    [task_artifact_rel],
                    discovery_task["commit_message"],
                    args.verify,
                    args.debug,
                )

                discovery_task["status"] = "blocked"
                discovery_task["implementation_commit"] = impl_hash
                append_completion_summary(
                    task_artifact_abs,
                    status="blocked",
                    tests_ran=[],
                    implementation_commit_hash=impl_hash,
                    receipt_commit_hash="SELF",
                    summary="Discovery fallback created; user review required",
                    notes=str(
                        campaign.get("discovery_reason") or "No tasks generated"
                    ),
                )

                campaign_doc_rel = campaign["materialized"]["campaign_doc_path"]
                campaign_doc_abs = repo_root / campaign_doc_rel
                update_mapping_block(
                    campaign_doc_abs, discovery_task_id, impl_hash, "SELF"
                )

                save_state(repo_root, state)
                append_transition(
                    repo_root,
                    run_id=run_id,
                    pass_index=pass_index,
                    reason="discovery_fallback_blocked",
                    previous_state_sha=previous_sha,
                    post_state_sha=state_hash(state),
                )

                receipt_hash = git_commit(
                    repo_root,
                    [
                        task_artifact_rel,
                        campaign_doc_rel,
                        str(STATE_PATH.as_posix()),
                        str(STATE_TRANSITIONS_PATH.as_posix()),
                    ],
                    f"runner: receipt {discovery_task_id}",
                    args.verify,
                    args.debug,
                )
                discovery_task["receipt_commit"] = receipt_hash
                update_campaign_completion(campaign)
                executed_tasks += 1
                termination_reason = "discovery_fallback_blocked_for_review"
                run_trace["events"].append(
                    {
                        "type": "discovery_fallback",
                        "task_id": discovery_task_id,
                        "implementation_commit": impl_hash,
                        "receipt_commit": receipt_hash,
                    }
                )
            else:
                raise RunnerError(
                    f"selected campaign has zero tasks and fallback disabled: {campaign['campaign_id']}"
                )
        elif args.execute and not args.dry_run:
            for task_id in task_ids:
                task = campaign["tasks"][task_id]
                if task.get("status") == "success":
                    continue

                ensure_clean_git(f"pre-task {task_id}", repo_root, args.debug)
                task_artifact_rel = campaign["materialized"][
                    "task_artifact_paths"
                ][task_id]
                task_artifact_abs = repo_root / task_artifact_rel

                result = run_task_agent(
                    repo_root=repo_root,
                    task=task,
                    task_result_schema_file=args.task_result_schema_file,
                    provider=args.provider,
                    model=provider_model_for_stage(args, "task"),
                    settings=active_settings,
                    debug=args.debug,
                )

                enforce_scope_guard(
                    repo_root,
                    task,
                    task_artifact_path=task_artifact_rel,
                    run_artifact_allowlist=[],
                    debug=args.debug,
                )

                append_implementation_receipt(
                    task_artifact_abs, run_id, task_id, result["status"]
                )
                changed_for_impl = git_changed_paths(repo_root, args.debug)
                impl_hash = git_commit(
                    repo_root,
                    changed_for_impl,
                    task["commit_message"],
                    args.verify,
                    args.debug,
                )

                task["status"] = result["status"]
                task["implementation_commit"] = impl_hash
                task["result"] = result

                append_completion_summary(
                    task_artifact_abs,
                    status=result["status"],
                    tests_ran=result["tests_ran"],
                    implementation_commit_hash=impl_hash,
                    receipt_commit_hash="SELF",
                    summary=result["summary"],
                    notes=result["notes"],
                )

                campaign_doc_rel = campaign["materialized"]["campaign_doc_path"]
                campaign_doc_abs = repo_root / campaign_doc_rel
                update_mapping_block(
                    campaign_doc_abs, task_id, impl_hash, "SELF"
                )

                save_state(repo_root, state)
                append_transition(
                    repo_root,
                    run_id=run_id,
                    pass_index=pass_index,
                    reason=f"task_receipt:{task_id}",
                    previous_state_sha=previous_sha,
                    post_state_sha=state_hash(state),
                )
                previous_sha = state_hash(state)

                receipt_paths = [
                    task_artifact_rel,
                    campaign_doc_rel,
                    str(STATE_PATH.as_posix()),
                    str(STATE_TRANSITIONS_PATH.as_posix()),
                ]
                receipt_hash = git_commit(
                    repo_root,
                    receipt_paths,
                    f"runner: receipt {task_id}",
                    args.verify,
                    args.debug,
                )
                task["receipt_commit"] = receipt_hash
                executed_tasks += 1

                run_trace["events"].append(
                    {
                        "type": "task",
                        "task_id": task_id,
                        "status": result["status"],
                        "implementation_commit": impl_hash,
                        "receipt_commit": receipt_hash,
                    }
                )

                if result["status"] in {"failed", "blocked"}:
                    termination_reason = f"task_{result['status']}:{task_id}"
                    break

            if termination_reason == "in_progress":
                termination_reason = (
                    "campaign_execution_complete"
                    if campaign_is_completed(campaign)
                    else "campaign_execution_paused"
                )
        else:
            termination_reason = "dry_run_selected_campaign_materialized"

        update_campaign_completion(campaign)

    post_state_sha = state_hash(state)
    save_state(repo_root, state)
    append_transition(
        repo_root,
        run_id=run_id,
        pass_index=pass_index,
        reason="pass_complete",
        previous_state_sha=previous_sha,
        post_state_sha=post_state_sha,
    )

    run_trace["termination_reason"] = termination_reason
    json_write(run_dir_abs / "execution_trace.json", run_trace)

    run_meta_kwargs["termination_reason"] = termination_reason
    run_meta_kwargs["selected_campaign"] = selected_campaign_id
    run_meta_kwargs["selection_rationale"] = selection_reason
    write_run_meta(audit_dir_abs / "run_meta.json", **run_meta_kwargs)
    write_run_meta(run_dir_abs / "run_meta.json", **run_meta_kwargs)

    if args.auto_commit:
        changed = git_changed_paths(repo_root, args.debug)
        if changed:
            git_commit(
                repo_root,
                changed,
                f"runner: run receipt {run_id}",
                args.verify,
                args.debug,
            )

    ensure_clean_git("end_of_pass", repo_root, args.debug)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Deterministic Campaign Runner"
    )
    parser.add_argument(
        "--tui",
        action="store_true",
        help="Launch interactive TUI to configure and run",
    )
    parser.add_argument(
        "--provider",
        choices=["codex", "claude"],
        default="codex",
    )

    parser.add_argument(
        "--repo-root",
        type=Path,
        default=default_repo_root(Path.cwd()),
        help="Repo root (defaults to git top-level from current directory)",
    )
    parser.add_argument(
        "--audit-prompt-file", type=Path, default=DEFAULT_MEGA_AUDIT_PROMPT_PATH
    )
    parser.add_argument(
        "--audit-schema-file", type=Path, default=DEFAULT_MEGA_AUDIT_SCHEMA_PATH
    )
    parser.add_argument(
        "--compiler-prompt-file",
        type=Path,
        default=DEFAULT_COMPILER_PROMPT_PATH,
    )
    parser.add_argument(
        "--campaign-set-schema-file",
        type=Path,
        default=DEFAULT_CAMPAIGN_SET_SCHEMA_PATH,
    )
    parser.add_argument(
        "--task-result-schema-file",
        type=Path,
        default=DEFAULT_TASK_RESULT_SCHEMA_PATH,
    )

    parser.add_argument("--passes", type=int, default=1)
    parser.add_argument("--base-ref", default="HEAD")

    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--dry-run", action="store_true")

    branch_group = parser.add_mutually_exclusive_group()
    branch_group.add_argument(
        "--branch-per-campaign",
        dest="branch_per_campaign",
        action="store_true",
        default=True,
    )
    branch_group.add_argument(
        "--no-branch-per-campaign",
        dest="branch_per_campaign",
        action="store_false",
    )

    parser.add_argument("--allow-discovery-fallback", action="store_true")

    auto_commit_group = parser.add_mutually_exclusive_group()
    auto_commit_group.add_argument(
        "--auto-commit", dest="auto_commit", action="store_true", default=True
    )
    auto_commit_group.add_argument(
        "--no-auto-commit", dest="auto_commit", action="store_false"
    )

    verify_group = parser.add_mutually_exclusive_group()
    verify_group.add_argument("--verify", dest="verify", action="store_true")
    verify_group.add_argument(
        "--no-verify", dest="verify", action="store_false"
    )
    parser.set_defaults(verify=None)

    parser.add_argument("--codex-model", default=None)
    parser.add_argument("--codex-model-audit", default=None)
    parser.add_argument("--codex-model-compiler", default=None)
    parser.add_argument("--codex-model-task", default=None)
    parser.add_argument("--codex-config", action="append", default=[])

    parser.add_argument("--claude-model", default=None)
    parser.add_argument("--claude-model-audit", default=None)
    parser.add_argument("--claude-model-compiler", default=None)
    parser.add_argument("--claude-model-task", default=None)
    parser.add_argument("--claude-settings", action="append", default=[])

    parser.add_argument("--debug", action="store_true")

    return parser


def default_repo_root(cwd: Path | None = None) -> Path:
    probe = (cwd or Path.cwd()).expanduser().resolve()
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(probe),
            text=True,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError:
        return probe
    if result.returncode == 0 and result.stdout.strip():
        return Path(result.stdout.strip()).expanduser().resolve()
    return probe


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = build_parser()
    args = parser.parse_args(argv)

    args.repo_root = args.repo_root.expanduser().resolve()
    args.audit_prompt_file = args.audit_prompt_file.expanduser().resolve()
    args.audit_schema_file = args.audit_schema_file.expanduser().resolve()
    args.compiler_prompt_file = args.compiler_prompt_file.expanduser().resolve()
    args.campaign_set_schema_file = (
        args.campaign_set_schema_file.expanduser().resolve()
    )
    args.task_result_schema_file = (
        args.task_result_schema_file.expanduser().resolve()
    )

    if args.passes < 1:
        raise RunnerError("--passes must be >= 1")

    if args.verify is None:
        args.verify = default_verify(os.environ.get("CI"))

    if not args.auto_commit:
        raise RunnerError(
            "--no-auto-commit is not supported in deterministic mode. "
            "Use --auto-commit to preserve clean-tree invariants."
        )

    required_paths = [
        args.audit_prompt_file,
        args.audit_schema_file,
        args.compiler_prompt_file,
        args.campaign_set_schema_file,
        args.task_result_schema_file,
    ]
    for path in required_paths:
        if not path.exists():
            raise RunnerError(f"Required file not found: {path}")

    return args


def launch_tui(initial_args: list[str] | None = None) -> list[str] | None:
    try:
        from .tui_app import launch_tui as _launch_tui
    except ImportError:
        try:
            from tui_app import launch_tui as _launch_tui  # type: ignore
        except ImportError as exc:
            message = str(exc).lower()
            if "textual" in message:
                raise RunnerError(
                    "TUI dependency missing: install Textual to use interactive mode. "
                    "Example: `pip install textual`"
                ) from exc
            raise
    return _launch_tui(initial_args or [])


def is_interactive_terminal() -> bool:
    ci_mode = os.environ.get("CI", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if ci_mode:
        return False
    return sys.stdin.isatty() and sys.stdout.isatty()


def resolve_entry_argv(argv: list[str] | None = None) -> list[str] | None:
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    explicit_tui = "--tui" in raw_argv
    interactive = is_interactive_terminal()
    if explicit_tui and not interactive:
        raise RunnerError(
            "--tui requires an interactive terminal. "
            "Remove --tui or run with explicit CLI flags in non-interactive contexts."
        )
    if not raw_argv:
        if not interactive:
            return raw_argv
        return launch_tui([])
    if not explicit_tui:
        return raw_argv
    passthrough = [part for part in raw_argv if part != "--tui"]
    return launch_tui(passthrough)


def main(argv: list[str] | None = None) -> int:
    resolved_argv = resolve_entry_argv(argv)
    if resolved_argv is None:
        return 0

    args = parse_args(resolved_argv)

    ensure_repo_root(args.repo_root, args.debug)
    ensure_provider_available(args.provider)

    base_ref_sha = git_resolve_ref(args.repo_root, args.base_ref, args.debug)
    cli_args = sanitize_cli_args(resolved_argv)

    for pass_index in range(1, args.passes + 1):
        run_pass(
            args,
            pass_index=pass_index,
            base_ref_sha=base_ref_sha,
            cli_args=cli_args,
        )

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RunnerError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)
