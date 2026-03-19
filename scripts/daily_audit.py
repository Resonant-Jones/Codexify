#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
AUDIT_SCRIPT = REPO_ROOT / "scripts" / "audit_platform_readiness.py"
BASELINE_HISTORY_DIR = REPO_ROOT / "docs" / "audits" / "history"
DAILY_AUDIT_DIR = REPO_ROOT / "docs" / "audits" / "daily"
LATEST_JSON = REPO_ROOT / "docs" / "audits" / "latest.json"
LATEST_MD = REPO_ROOT / "docs" / "audits" / "latest.md"

BUCKET_ORDER = [
    "chat",
    "docs",
    "audit",
    "config",
    "providers",
    "ingestion",
    "tools",
    "command_bus",
    "frontend",
    "federation",
    "sync",
    "tests",
    "infra",
    "unknown",
]

RISK_FLAGS = [
    {
        "flag": "chat_depends_on_redis_and_workers",
        "active": True,
        "severity": "high",
        "evidence": [
            "docs/architecture/tech-debt-and-risks.md",
            "docs/architecture/roadmap-signals.md",
        ],
        "description": "Chat completion is queue-coupled and depends on Redis plus worker availability.",
    },
    {
        "flag": "config_split_brain_risk",
        "active": True,
        "severity": "high",
        "evidence": [
            "docs/architecture/tech-debt-and-risks.md",
            "docs/architecture/roadmap-signals.md",
        ],
        "description": "Canonical and legacy config paths still coexist, so startup and operator state can drift.",
    },
    {
        "flag": "legacy_tools_and_command_bus_duality",
        "active": True,
        "severity": "high",
        "evidence": [
            "docs/architecture/tech-debt-and-risks.md",
            "docs/architecture/roadmap-signals.md",
        ],
        "description": "Legacy /tools behavior and the command bus still overlap, which increases contract drift risk.",
    },
    {
        "flag": "sync_not_durable",
        "active": True,
        "severity": "medium",
        "evidence": [
            "docs/architecture/tech-debt-and-risks.md",
            "docs/architecture/roadmap-signals.md",
            "docs/architecture/data-and-storage.md",
        ],
        "description": "Sync subscriptions are still process-local rather than durable across restarts.",
    },
    {
        "flag": "federation_high_blast_radius",
        "active": True,
        "severity": "high",
        "evidence": [
            "docs/architecture/tech-debt-and-risks.md",
            "docs/architecture/roadmap-signals.md",
        ],
        "description": "Federation remains sensitive to trust policy, feature flags, and egress behavior.",
    },
]


@dataclass(slots=True)
class CommandResult:
    command: list[str]
    returncode: int
    stdout: str
    stderr: str


def command_string(command: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in command)


def run_command(command: list[str]) -> CommandResult:
    try:
        completed = subprocess.run(
            command,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except OSError as exc:  # pragma: no cover - execution environment failure
        raise RuntimeError(
            f"Failed to run {command_string(command)}: {exc}"
        ) from exc
    return CommandResult(
        command, completed.returncode, completed.stdout, completed.stderr
    )


def run_git(args: list[str]) -> str:
    result = run_command(["git", *args])
    if result.returncode != 0:
        stderr = (
            result.stderr.strip()
            or result.stdout.strip()
            or "unknown git error"
        )
        raise RuntimeError(f"git {' '.join(args)} failed: {stderr}")
    return result.stdout


def iso_now() -> datetime:
    return datetime.now().astimezone()


def local_date() -> str:
    return iso_now().date().isoformat()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def find_latest_baseline_file() -> Path | None:
    if not BASELINE_HISTORY_DIR.exists():
        return None
    candidates = list(
        BASELINE_HISTORY_DIR.glob("*-platform-readiness-baseline.md")
    )
    if not candidates:
        return None
    return max(candidates, key=lambda path: (path.stat().st_mtime, path.name))


def parse_baseline_state() -> dict[str, Any]:
    baseline_path = find_latest_baseline_file()
    if baseline_path is None:
        return {
            "source": None,
            "scores": {},
            "summary": "",
            "phase_gate": {
                "label": "Early-Adopter Ready",
                "value": "",
                "ready": False,
            },
        }

    text = read_text(baseline_path)
    score_section = re.search(
        r"## 3\. Domain Scores \(Baseline\)\n(?P<body>.*?)(?:\n## |\Z)",
        text,
        re.S,
    )
    scores: dict[str, int] = {}
    if score_section is not None:
        for line in score_section.group("body").splitlines():
            match = re.match(
                r"^\| (?P<domain>[^|]+?) \| (?P<score>\d+) \| (?P<rationale>[^|]+?) \|$",
                line,
            )
            if match is None:
                continue
            domain = match.group("domain").strip()
            if domain.lower() == "domain":
                continue
            scores[domain] = int(match.group("score"))

    summary_section = re.search(
        r"## 4\. Summary Interpretation\n\n(?P<body>.*?)(?:\n## |\Z)",
        text,
        re.S,
    )
    summary = ""
    if summary_section is not None:
        body = summary_section.group("body").strip()
        if body:
            summary = " ".join(body.split("\n\n", 1)[0].splitlines()).strip()

    phase_match = re.search(r"Early-Adopter Ready:\s*(?P<value>.+)", text)
    phase_value = phase_match.group("value").strip() if phase_match else ""
    phase_ready = (
        "not yet" not in phase_value.lower() and "❌" not in phase_value
    )

    return {
        "source": baseline_path.relative_to(REPO_ROOT).as_posix(),
        "scores": scores,
        "summary": summary,
        "phase_gate": {
            "label": "Early-Adopter Ready",
            "value": phase_value,
            "ready": phase_ready,
        },
    }


def parse_audit_text(stdout: str) -> dict[str, Any]:
    def extract_count(label: str) -> int | None:
        match = re.search(rf"^\s*{re.escape(label)}:\s*(\d+)\s*$", stdout, re.M)
        return int(match.group(1)) if match else None

    suggested_scores: dict[str, str] = {}
    lines = stdout.splitlines()
    for index in range(1, len(lines) - 1):
        if not lines[index - 1].startswith("="):
            continue
        domain = lines[index].strip()
        next_line = lines[index + 1].strip()
        if not domain or domain.startswith("="):
            continue
        if next_line.startswith("Suggested score band: "):
            suggested_scores[domain] = next_line.split(": ", 1)[1].strip()

    strongest_match = re.search(
        r"^\s*Strongest objective evidence:\s*(?P<value>.+)\s*$",
        stdout,
        re.M,
    )
    weakest_match = re.search(
        r"^\s*Clearest structural weakness signals:\s*(?P<value>.+)\s*$",
        stdout,
        re.M,
    )

    def split_csv(value: str | None) -> list[str]:
        if not value:
            return []
        cleaned = value.strip()
        if cleaned.lower() == "none":
            return []
        return [part.strip() for part in cleaned.split(",") if part.strip()]

    return {
        "summary_counts": {
            "pass": extract_count("PASS"),
            "warn": extract_count("WARN"),
            "fail": extract_count("FAIL"),
        },
        "suggested_score_bands": suggested_scores,
        "strongest_domains": split_csv(
            strongest_match.group("value") if strongest_match else None
        ),
        "weakest_domains": split_csv(
            weakest_match.group("value") if weakest_match else None
        ),
    }


def run_audit_cli() -> dict[str, Any]:
    json_attempt = run_command([sys.executable, str(AUDIT_SCRIPT), "--json"])
    try:
        parsed_json = json.loads(json_attempt.stdout)
    except json.JSONDecodeError:
        parsed_json = None

    if parsed_json is not None:
        return {
            "selected_mode": "json",
            "attempts": [
                {
                    "command": command_string(json_attempt.command),
                    "exit_code": json_attempt.returncode,
                    "stdout_is_json": True,
                    "stderr": json_attempt.stderr.strip(),
                }
            ],
            "raw_output": json_attempt.stdout,
            "parsed_json": parsed_json,
        }

    plain_attempt = run_command([sys.executable, str(AUDIT_SCRIPT)])
    return {
        "selected_mode": "text_fallback",
        "attempts": [
            {
                "command": command_string(json_attempt.command),
                "exit_code": json_attempt.returncode,
                "stdout_is_json": False,
                "stderr": json_attempt.stderr.strip(),
            },
            {
                "command": command_string(plain_attempt.command),
                "exit_code": plain_attempt.returncode,
                "stderr": plain_attempt.stderr.strip(),
            },
        ],
        "raw_output": plain_attempt.stdout,
        "parsed_text": parse_audit_text(plain_attempt.stdout),
    }


def collect_repo_metadata(now: datetime) -> dict[str, Any]:
    branch = run_git(["branch", "--show-current"]).strip()
    head = run_git(["rev-parse", "HEAD"]).strip()
    if not branch:
        branch = f"detached@{head[:7]}"
    status_output = run_git(["status", "--short", "--untracked-files=all"])
    status_lines = [
        line.rstrip() for line in status_output.splitlines() if line.strip()
    ]
    return {
        "date": now.date().isoformat(),
        "branch": branch,
        "head": head,
        "dirty": bool(status_lines),
        "status_lines": status_lines,
    }


def collect_git_activity(now: datetime) -> dict[str, Any]:
    window_start = now - timedelta(hours=24)
    log_output = run_git(
        [
            "log",
            "--since=24 hours ago",
            "--no-merges",
            "--format=%H%x00%s%x00%x1e",
        ]
    )

    commits: list[dict[str, Any]] = []
    unique_files: list[str] = []
    seen_files: set[str] = set()

    for record in log_output.split("\x1e"):
        record = record.strip()
        if not record:
            continue
        parts = record.split("\x00")
        if len(parts) < 2:
            continue
        sha = parts[0].strip()
        subject = parts[1].strip()
        if not sha:
            continue

        files_output = run_git(
            [
                "show",
                "--pretty=format:",
                "--name-only",
                "-z",
                "--no-renames",
                sha,
            ]
        )
        commit_files: list[str] = []
        for file_name in files_output.split("\x00"):
            if not file_name:
                continue
            file_name = file_name.rstrip("\n")
            if file_name not in commit_files:
                commit_files.append(file_name)
            if file_name not in seen_files:
                seen_files.add(file_name)
                unique_files.append(file_name)

        commits.append({"sha": sha, "subject": subject, "files": commit_files})

    return {
        "window_hours": 24,
        "window_start": window_start.isoformat(),
        "window_end": now.isoformat(),
        "commit_count": len(commits),
        "commits": commits,
        "files_changed": unique_files,
    }


def classify_path(path: str) -> str:
    normalized = path.replace("\\", "/").lower()

    if (
        normalized.startswith("docs/audits/")
        or normalized.startswith("scripts/audit")
        or normalized.endswith("daily_audit.py")
        or "audit_platform_readiness" in normalized
    ):
        return "audit"

    if (
        normalized.startswith("guardian/routes/chat")
        or normalized.startswith("guardian/workers/chat")
        or normalized.startswith("docs/chat/")
    ):
        return "chat"

    if "command_bus" in normalized or "command-bus" in normalized:
        return "command_bus"

    if "federation" in normalized:
        return "federation"

    if re.search(r"(^|/)sync($|[._/-])", normalized):
        return "sync"

    if (
        re.search(r"(^|/)tools($|[._/-])", normalized)
        or "toolspec" in normalized
    ):
        return "tools"

    if (
        "provider" in normalized
        or "llm_catalog" in normalized
        or "ai_router" in normalized
        or "supported_profile" in normalized
        or "provider_state" in normalized
        or "provider_registry" in normalized
    ):
        return "providers"

    if (
        "ingest" in normalized
        or "embedding" in normalized
        or "document_embed" in normalized
        or normalized == "guardian/routes/media.py"
        or normalized.startswith("guardian/services/document_parsers/")
    ):
        return "ingestion"

    if (
        normalized.startswith("frontend/")
        or normalized.startswith("src-tauri/")
        or "/frontend/" in normalized
    ):
        return "frontend"

    if (
        re.search(r"(^|/)tests?/", normalized)
        or normalized.endswith("_test.py")
        or normalized.endswith("test.py")
        or re.search(r"(^|/)test_[^/]+\.py$", normalized)
    ):
        return "tests"

    if (
        normalized == "makefile"
        or normalized.startswith("requirements")
        or normalized == "pyproject.toml"
        or normalized == "package.json"
        or normalized == "pnpm-lock.yaml"
        or normalized == "poetry.lock"
        or normalized == ".pre-commit-config.yaml"
        or normalized.startswith(".env")
        or re.search(r"(^|/)(config|settings)/", normalized)
        or normalized.endswith("config.py")
    ):
        return "config"

    if (
        normalized.startswith("docker/")
        or normalized.startswith(".github/")
        or normalized.startswith("infra/")
        or normalized.startswith("terraform/")
        or normalized.startswith("k8s/")
        or normalized.startswith("scripts/maintenance/")
        or normalized.startswith("scripts/verification/")
        or normalized.startswith("scripts/security/")
        or normalized.startswith("scripts/dev/")
        or normalized == "docker-compose.yml"
        or normalized.startswith("docker-compose")
        or normalized.startswith("dockerfile")
    ):
        return "infra"

    if normalized.startswith("docs/"):
        return "docs"

    return "unknown"


def classify_files(files: list[str]) -> dict[str, dict[str, Any]]:
    buckets: dict[str, dict[str, Any]] = {
        bucket: {"count": 0, "files": []} for bucket in BUCKET_ORDER
    }

    for file_name in files:
        bucket = classify_path(file_name)
        entry = buckets[bucket]
        if file_name not in entry["files"]:
            entry["files"].append(file_name)
            entry["count"] += 1

    return {
        bucket: buckets[bucket]
        for bucket in BUCKET_ORDER
        if buckets[bucket]["count"]
    }


def prompt_optional(field_name: str) -> str:
    prompt = field_name.replace("_", " ").strip().capitalize()
    if not sys.stdin.isatty():
        return ""
    try:
        return input(f"{prompt} (optional): ").strip()
    except EOFError:
        return ""


def collect_manual_notes() -> dict[str, str]:
    return {
        "finished_today": prompt_optional("finished_today"),
        "blocked": prompt_optional("blocked"),
        "next_priority": prompt_optional("next_priority"),
    }


def json_safe_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)


def backtick(value: str) -> str:
    escaped = value.replace("`", "\\`")
    return f"`{escaped}`"


def table_cell(value: str) -> str:
    return value.replace("|", "\\|")


def render_markdown(payload: dict[str, Any]) -> str:
    repo = payload["repo"]
    audit_cli = payload["audit_cli"]
    changes = payload["changes_last_24h"]
    subsystems = payload["subsystems_touched"]
    baseline = payload["baseline"]
    manual_notes = payload["manual_notes"]

    lines: list[str] = []
    lines.append(f"# Daily Audit — {payload['date']}")
    lines.append("")

    lines.append("## Repo Status")
    lines.append(f"- Date: {payload['date']}")
    lines.append(f"- Branch: {backtick(repo['branch'])}")
    lines.append(f"- HEAD: {backtick(repo['head'])}")
    lines.append(f"- Worktree: {'dirty' if repo['dirty'] else 'clean'}")
    if repo["status_lines"]:
        lines.append("- Status lines:")
        for line in repo["status_lines"]:
            lines.append(f"  - {backtick(line)}")
    lines.append("")

    lines.append("## Audit CLI Summary")
    lines.append(f"- Selected mode: {backtick(audit_cli['selected_mode'])}")
    attempts = audit_cli["attempts"]
    if attempts:
        lines.append("- Attempted commands:")
        for attempt in attempts:
            command = attempt["command"]
            exit_code = attempt["exit_code"]
            if attempt.get("stdout_is_json") is True:
                extra = "json"
            elif command.endswith("--json"):
                extra = "json probe"
            else:
                extra = "plain"
            lines.append(
                f"  - {backtick(command)} -> exit {exit_code} ({extra})"
            )
    parsed_text = audit_cli.get("parsed_text") or {}
    counts = parsed_text.get("summary_counts") or {}
    if counts and all(
        counts.get(key) is not None for key in ("pass", "warn", "fail")
    ):
        lines.append(
            "- Summary counts: PASS {pass_count}, WARN {warn_count}, FAIL {fail_count}".format(
                pass_count=counts.get("pass", "n/a"),
                warn_count=counts.get("warn", "n/a"),
                fail_count=counts.get("fail", "n/a"),
            )
        )
    strongest = parsed_text.get("strongest_domains") or []
    weakest = parsed_text.get("weakest_domains") or []
    if strongest:
        lines.append(
            f"- Strongest evidence: {', '.join(backtick(domain) for domain in strongest)}"
        )
    if weakest:
        lines.append(
            f"- Weakest signals: {', '.join(backtick(domain) for domain in weakest)}"
        )
    if parsed_text.get("suggested_score_bands"):
        lines.append("")
        lines.append("### Current Suggested Score Bands")
        lines.append("| Domain | Band |")
        lines.append("| --- | --- |")
        for domain, band in parsed_text["suggested_score_bands"].items():
            lines.append(
                f"| {backtick(table_cell(domain))} | {table_cell(band)} |"
            )

    lines.append("")
    lines.append("### Baseline Score State")
    if baseline["source"]:
        lines.append(f"- Source: {backtick(baseline['source'])}")
    if baseline.get("summary"):
        lines.append(f"- Summary: {baseline['summary']}")
    phase_gate = baseline.get("phase_gate") or {}
    if phase_gate:
        phase_value = phase_gate.get("value") or ""
        lines.append(
            f"- Phase gate: {phase_gate.get('label', 'Early-Adopter Ready')}: {phase_value or 'unknown'}"
        )
    if baseline.get("scores"):
        lines.append("")
        lines.append("| Domain | Baseline Score |")
        lines.append("| --- | --- |")
        for domain, score in baseline["scores"].items():
            lines.append(f"| {backtick(table_cell(domain))} | {score} |")
    lines.append("")

    lines.append("## Changes in Last 24 Hours")
    lines.append(f"- Commit count: {changes['commit_count']}")
    lines.append(f"- Unique files changed: {len(changes['files_changed'])}")
    if changes["files_changed"]:
        lines.append(
            "- Files changed: "
            + ", ".join(
                backtick(file_name) for file_name in changes["files_changed"]
            )
        )
    if changes["commits"]:
        lines.append("")
        lines.append("| SHA | Subject | Files |")
        lines.append("| --- | --- | --- |")
        for commit in changes["commits"]:
            files_display = (
                ", ".join(backtick(file_name) for file_name in commit["files"])
                or ""
            )
            lines.append(
                f"| {backtick(commit['sha'][:12])} | {table_cell(commit['subject'])} | {files_display} |"
            )
    else:
        lines.append("- No commits landed in the last 24 hours.")
    lines.append("")

    lines.append("## Subsystems Touched")
    if subsystems:
        lines.append("| Bucket | Count | Files |")
        lines.append("| --- | --- | --- |")
        for bucket in BUCKET_ORDER:
            entry = subsystems.get(bucket)
            if not entry:
                continue
            files_display = ", ".join(
                backtick(file_name) for file_name in entry["files"]
            )
            lines.append(
                f"| {backtick(bucket)} | {entry['count']} | {files_display} |"
            )
    else:
        lines.append("- No touched subsystems detected in the last 24 hours.")
    lines.append("")

    lines.append("## Risk Flags")
    for flag in payload["risk_flags"]:
        evidence = ", ".join(backtick(item) for item in flag["evidence"])
        lines.append(
            f"- {backtick(flag['flag'])}: {flag['description']} Evidence: {evidence}"
        )
    lines.append("")

    lines.append("## Manual Notes")
    lines.append(f"- Finished today: {manual_notes['finished_today']}")
    lines.append(f"- Blocked: {manual_notes['blocked']}")
    lines.append(f"- Next priority: {manual_notes['next_priority']}")
    lines.append("")

    return "\n".join(lines)


def write_text_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f"{path.name}.tmp")
    temp_path.write_text(content, encoding="utf-8")
    temp_path.replace(path)


def build_payload() -> dict[str, Any]:
    now = iso_now()
    repo = collect_repo_metadata(now)
    audit_cli = run_audit_cli()
    parsed_text = audit_cli.get("parsed_text")
    if not parsed_text and audit_cli.get("selected_mode") == "json":
        parsed_text = {}
    changes = collect_git_activity(now)
    subsystems = classify_files(changes["files_changed"])
    baseline = parse_baseline_state()
    manual_notes = collect_manual_notes()

    payload = {
        "date": repo["date"],
        "generated_at": now.isoformat(),
        "repo": repo,
        "audit_cli": audit_cli,
        "changes_last_24h": changes,
        "subsystems_touched": subsystems,
        "baseline": baseline,
        "risk_flags": RISK_FLAGS,
        "manual_notes": manual_notes,
    }

    if parsed_text:
        payload["audit_cli"]["parsed_text"] = parsed_text

    return payload


def main() -> int:
    try:
        payload = build_payload()
        daily_json_path = DAILY_AUDIT_DIR / f"{payload['date']}-audit.json"
        daily_md_path = DAILY_AUDIT_DIR / f"{payload['date']}-audit.md"

        json_content = json.dumps(
            payload, indent=2, sort_keys=True, ensure_ascii=False
        )
        markdown_content = render_markdown(payload)

        write_text_file(daily_json_path, f"{json_content}\n")
        write_text_file(daily_md_path, f"{markdown_content}\n")
        write_text_file(LATEST_JSON, f"{json_content}\n")
        write_text_file(LATEST_MD, f"{markdown_content}\n")

        print(f"Wrote {daily_json_path.relative_to(REPO_ROOT)}")
        print(f"Wrote {daily_md_path.relative_to(REPO_ROOT)}")
        print(f"Updated {LATEST_JSON.relative_to(REPO_ROOT)}")
        print(f"Updated {LATEST_MD.relative_to(REPO_ROOT)}")
        return 0
    except Exception as exc:  # pragma: no cover - defensive exit path
        print(f"daily_audit.py failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
