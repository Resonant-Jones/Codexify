#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
CURRENT_STATE_PATH = REPO_ROOT / "docs" / "architecture" / "00-current-state.md"
AUDIT_SCRIPT_PATH = REPO_ROOT / "scripts" / "audit_platform_readiness.py"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "docs" / "audits" / "generated"
DEFAULT_CHANGELOG = REPO_ROOT / "CHANGELOG.beta.md"
GATE_STATUSES = {"proven", "warning", "blocked", "not_promised", "unknown"}


@dataclass
class Gate:
    name: str
    status: str
    evidence: str
    notes: str


def run_git(args: list[str]) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode != 0:
        stderr = (
            completed.stderr.strip()
            or completed.stdout.strip()
            or "unknown git error"
        )
        raise RuntimeError(f"git {' '.join(args)} failed: {stderr}")
    return completed.stdout


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate beta sentinel release evidence artifacts."
    )
    parser.add_argument("--date", help="Report date in YYYY-MM-DD.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--changelog", default=str(DEFAULT_CHANGELOG))
    parser.add_argument("--json-only", action="store_true")
    parser.add_argument("--markdown-only", action="store_true")
    return parser.parse_args()


def parse_report_date(raw: str | None) -> date:
    if raw is None:
        return datetime.now().astimezone().date()
    return datetime.strptime(raw, "%Y-%m-%d").date()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def extract_release_checklist(current_state_text: str) -> list[dict[str, Any]]:
    start = current_state_text.find("## Release definition right now")
    if start < 0:
        return []
    body = current_state_text[start:].split("\n## ", 1)[0]
    items: list[dict[str, Any]] = []
    for line in body.splitlines():
        m = re.match(r"^- \[(?P<mark>[ xX])\] (?P<label>.+)$", line.strip())
        if not m:
            continue
        items.append(
            {
                "item": m.group("label").strip(),
                "checked": m.group("mark").lower() == "x",
            }
        )
    return items


def collect_repo_status() -> dict[str, Any]:
    branch = run_git(["branch", "--show-current"]).strip()
    head = run_git(["rev-parse", "HEAD"]).strip()
    if not branch:
        branch = f"detached@{head[:7]}"
    dirty = True
    status_lines: list[str] = []
    status_error = ""
    try:
        status_output = run_git(["status", "--short", "--untracked-files=all"])
        status_lines = [ln for ln in status_output.splitlines() if ln.strip()]
        dirty = bool(status_lines)
    except RuntimeError as exc:
        message = str(exc)
        if "git-lfs" in message and "filter-process" in message:
            status_error = message
        else:
            raise
    return {
        "branch": branch,
        "head": head,
        "worktree_clean": not dirty if not status_error else False,
        "status_lines": status_lines,
        "status_error": status_error,
    }


def discover_previous_report(date_str: str, output_dir: Path) -> Path | None:
    if not output_dir.exists():
        return None
    candidates = sorted(output_dir.glob("*-beta-sentinel.json"))
    eligible = [
        p for p in candidates if p.name < f"{date_str}-beta-sentinel.json"
    ]
    return eligible[-1] if eligible else None


def commit_subjects_since(previous_report: Path | None) -> list[str]:
    rev_range = None
    if previous_report and previous_report.exists():
        try:
            payload = json.loads(read_text(previous_report))
            previous_head = str(payload.get("head", "")).strip()
            if previous_head:
                rev_range = f"{previous_head}..HEAD"
        except json.JSONDecodeError:
            rev_range = None
    args = ["log", "--no-merges", "--format=%s"]
    if rev_range:
        args.append(rev_range)
    else:
        args.extend(["-n", "15"])
    output = run_git(args)
    return [ln.strip() for ln in output.splitlines() if ln.strip()]


def run_platform_readiness() -> tuple[dict[str, Any] | None, str | None]:
    if not AUDIT_SCRIPT_PATH.exists():
        return None, "Platform readiness audit script is missing."
    cmd = [sys.executable, str(AUDIT_SCRIPT_PATH), "--json"]
    run = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if run.returncode != 0:
        return (
            None,
            f"Platform readiness audit failed with exit code {run.returncode}.",
        )
    try:
        return json.loads(run.stdout), None
    except json.JSONDecodeError:
        return None, "Platform readiness audit did not return valid JSON."


def build_release_gates(
    checklist: list[dict[str, Any]],
    audit_summary: dict[str, Any] | None,
    audit_warning: str | None,
) -> list[Gate]:
    gates: list[Gate] = []
    for item in checklist:
        status = "proven" if item["checked"] else "warning"
        gates.append(
            Gate(
                name=item["item"],
                status=status,
                evidence="docs/architecture/00-current-state.md",
                notes="Checklist item from current state.",
            )
        )
    if audit_warning:
        gates.append(
            Gate(
                name="Platform readiness audit execution",
                status="warning",
                evidence="scripts/audit_platform_readiness.py",
                notes=audit_warning,
            )
        )
    elif audit_summary is not None:
        gates.append(
            Gate(
                name="Platform readiness audit execution",
                status="proven",
                evidence="scripts/audit_platform_readiness.py",
                notes="Audit script executed and returned JSON summary.",
            )
        )
    return gates


def validate_gate_statuses(gates: list[Gate]) -> None:
    for gate in gates:
        if gate.status not in GATE_STATUSES:
            raise ValueError(f"Invalid gate status: {gate.status}")


def generate_markdown(
    date_str: str,
    repo: dict[str, Any],
    release_gates: list[Gate],
    changelog_items: list[str],
    blockers: list[str],
    warnings: list[str],
    not_promised: list[str],
    json_path: Path,
) -> str:
    gate_lines = (
        "\n".join(f"- `{g.status}` {g.name} — {g.notes}" for g in release_gates)
        or "- `unknown` No gate evidence collected."
    )
    commit_lines = (
        "\n".join(f"- {item}" for item in changelog_items)
        or "- No new commit subjects found for this window."
    )
    blocker_lines = (
        "\n".join(f"- {item}" for item in blockers)
        or "- None currently listed."
    )
    warning_lines = "\n".join(f"- {item}" for item in warnings) or "- None."
    excluded_lines = "\n".join(f"- {item}" for item in not_promised)
    status_lines = (
        "\n".join(f"- `{line}`" for line in repo["status_lines"])
        if repo["status_lines"]
        else "- Worktree appears clean."
    )
    if repo["status_error"]:
        status_lines += (
            f"\n- Worktree status fallback warning: {repo['status_error']}"
        )
    return (
        f"# Beta Release Sentinel — {date_str}\n\n"
        "## Repo status\n"
        f"- Branch: `{repo['branch']}`\n"
        f"- Head: `{repo['head']}`\n"
        f"- Worktree clean: `{repo['worktree_clean']}`\n"
        f"{status_lines}\n\n"
        "## Current beta promise\n"
        "- Local-first beta hardening.\n"
        "- Supported path: local Docker Compose.\n"
        "- Supported beta posture: local-only.\n"
        "- Primary operator truth surfaces: `/health`, `/health/chat`, `/api/health/llm`, `/api/llm/catalog`.\n\n"
        "## Release gates\n"
        f"{gate_lines}\n\n"
        "## Evidence summary\n"
        f"{warning_lines}\n\n"
        "## Changelog draft\n"
        f"{commit_lines}\n\n"
        "## Blockers\n"
        f"{blocker_lines}\n\n"
        "## Warnings\n"
        f"{warning_lines}\n\n"
        "## Not promised / excluded surfaces\n"
        f"{excluded_lines}\n\n"
        "## Recommended next actions\n"
        "- Re-run sentinel after runtime changes on current tip.\n"
        "- Keep supported-profile contract and health/catalog surfaces aligned.\n"
        "- Treat this artifact as evidence, not release approval.\n\n"
        "## Machine-readable JSON artifact path\n"
        f"- `{json_path}`\n"
    )


def update_changelog(
    path: Path,
    date_str: str,
    items: list[str],
    blockers: list[str],
    warnings: list[str],
) -> None:
    if path.exists():
        existing = read_text(path).rstrip() + "\n\n"
    else:
        existing = (
            "# Beta Changelog\n\nEvidence-led beta readiness changes only.\n\n"
        )
    lines = [f"## {date_str}", "", "### Evidence", ""]
    if items:
        lines.extend(f"- {it}" for it in items)
    else:
        lines.append(
            "- No new commit subjects discovered for this sentinel window."
        )
    lines.extend(["", "### Blockers", ""])
    lines.extend([f"- {b}" for b in blockers] or ["- None."])
    lines.extend(["", "### Warnings", ""])
    lines.extend([f"- {w}" for w in warnings] or ["- None."])
    path.write_text(existing + "\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    if args.json_only and args.markdown_only:
        raise SystemExit("Cannot combine --json-only and --markdown-only.")
    run_date = parse_report_date(args.date)
    date_str = run_date.isoformat()
    output_dir = Path(args.output_dir)
    changelog_path = Path(args.changelog)
    output_dir.mkdir(parents=True, exist_ok=True)
    md_path = output_dir / f"{date_str}-beta-sentinel.md"
    json_path = output_dir / f"{date_str}-beta-sentinel.json"

    current_state = read_text(CURRENT_STATE_PATH)
    checklist = extract_release_checklist(current_state)
    repo = collect_repo_status()
    previous = discover_previous_report(date_str, output_dir)
    commits = commit_subjects_since(previous)
    audit_summary, audit_warning = run_platform_readiness()

    blockers = [g["item"] for g in checklist if not g["checked"]]
    warnings = [audit_warning] if audit_warning else []
    warnings.extend(
        ["Worktree is dirty; release evidence should use a clean tree."]
        if not repo["worktree_clean"]
        else []
    )
    not_promised = [
        "Cloud-provider beta support.",
        "Packaged desktop replacing local Compose as supported path.",
        "Command bus, delegation, federation, graph writes, or worker-control dispatch as public beta promise.",
        "External publication to email, Substack, or websites.",
    ]

    gates = build_release_gates(checklist, audit_summary, audit_warning)
    validate_gate_statuses(gates)

    payload = {
        "date": date_str,
        "branch": repo["branch"],
        "head": repo["head"],
        "worktree_clean": repo["worktree_clean"],
        "release_gates": [g.__dict__ for g in gates],
        "blockers": blockers,
        "warnings": warnings,
        "not_promised": not_promised,
        "changelog_items": commits,
        "audit_summary": audit_summary,
        "generated_files": {
            "markdown": str(md_path),
            "json": str(json_path),
            "changelog": str(changelog_path),
        },
    }

    if not args.markdown_only:
        json_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    if not args.json_only:
        md = generate_markdown(
            date_str,
            repo,
            gates,
            commits,
            blockers,
            warnings,
            not_promised,
            json_path,
        )
        md_path.write_text(md, encoding="utf-8")

    update_changelog(changelog_path, date_str, commits, blockers, warnings)

    print(
        json.dumps(
            {
                "markdown": str(md_path),
                "json": str(json_path),
                "changelog": str(changelog_path),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
