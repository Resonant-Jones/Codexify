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
GATE_STATUSES = {"checked", "proven", "warning"}


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
        stderr = completed.stderr.strip() or "unknown git error"
        raise RuntimeError(f"git {' '.join(args)} failed: {stderr}")
    return completed.stdout


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate beta release sentinel artifacts."
    )
    parser.add_argument("--date", help="Report date in YYYY-MM-DD.")
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory for generated beta sentinel artifacts.",
    )
    parser.add_argument(
        "--changelog",
        default=str(DEFAULT_CHANGELOG),
        help="Path to the beta changelog file.",
    )
    parser.add_argument(
        "--json-only",
        action="store_true",
        help="Write only the JSON artifact content to stdout.",
    )
    parser.add_argument(
        "--markdown-only",
        action="store_true",
        help="Write only the markdown artifact content to stdout.",
    )
    return parser.parse_args(argv)


def parse_report_date(raw: str | None) -> date:
    if raw is None:
        return datetime.now().astimezone().date()
    return datetime.strptime(raw, "%Y-%m-%d").date()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def extract_release_checklist(current_state_text: str) -> list[dict[str, str]]:
    start = current_state_text.find("## Release definition right now")
    if start == -1:
        return []
    body = current_state_text[start:].split("\n## ", 1)[0]
    items: list[dict[str, str]] = []
    for line in body.splitlines():
        match = re.match(r"^- \[(?P<mark>[ xX])\] (?P<label>.+)$", line)
        if match is not None:
            items.append(
                {
                    "mark": match.group("mark").strip().lower(),
                    "label": match.group("label").strip(),
                }
            )
    return items


def collect_repo_status() -> dict[str, Any]:
    branch = run_git(["branch", "--show-current"]).strip()
    head = run_git(["rev-parse", "HEAD"]).strip()
    dirty = False
    status_lines: list[str] = []
    status_error = ""

    if not branch and head:
        branch = f"detached@{head[:7]}"

    try:
        status_output = run_git(["status", "--short", "--untracked-files=all"])
        status_lines = [
            line.rstrip() for line in status_output.splitlines() if line.strip()
        ]
        dirty = bool(status_lines)
    except RuntimeError as exc:
        status_error = str(exc)

    return {
        "branch": branch,
        "head": head,
        "dirty": dirty,
        "status_lines": status_lines,
        "status_error": status_error,
    }


def discover_previous_report(date_str: str, output_dir: Path) -> Path | None:
    eligible = sorted(output_dir.glob("*-beta-sentinel.json"))
    if not eligible:
        return None
    target_prefix = date_str[:10]
    prior = [path for path in eligible if path.name[:10] <= target_prefix]
    if prior:
        return prior[-1]
    return eligible[-1]


def commit_subjects_since(previous_report: Path | None) -> list[str]:
    if previous_report is None or not previous_report.exists():
        return []

    try:
        payload = json.loads(previous_report.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []

    previous_head = str(payload.get("repo", {}).get("head", "")).strip()
    if not previous_head:
        return []

    args = ["log", f"{previous_head}..HEAD", "-n", "15", "--format=%s"]
    output = run_git(args)
    return [line.strip() for line in output.splitlines() if line.strip()]


def run_platform_readiness() -> dict[str, Any]:
    if not AUDIT_SCRIPT_PATH.exists():
        raise SystemExit(f"Missing audit script: {AUDIT_SCRIPT_PATH}")

    completed = subprocess.run(
        [sys.executable, str(AUDIT_SCRIPT_PATH), "--json"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode != 0:
        raise SystemExit(
            "Platform readiness audit failed with exit code "
            f"{completed.returncode}."
        )

    try:
        parsed = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise SystemExit(
            "Platform readiness audit returned malformed JSON."
        ) from exc

    if not isinstance(parsed, dict):
        raise SystemExit("Platform readiness audit returned a non-object JSON payload.")
    return parsed


def build_release_gates(
    checklist: list[dict[str, str]],
    audit_summary: dict[str, Any],
    audit_warning: str | None,
) -> list[Gate]:
    gates: list[Gate] = []
    for item in checklist:
        status = "checked" if item.get("mark") == "x" else "warning"
        gates.append(
            Gate(
                name=item.get("label", "unknown"),
                status=status,
                evidence="docs/architecture/00-current-state.md",
                notes="Checklist item from current state.",
            )
        )

    audit_status = "proven"
    if audit_warning or audit_summary.get("summary", {}).get("overall_status") != "pass":
        audit_status = "warning"
    gates.append(
        Gate(
            name="Platform readiness audit execution",
            status=audit_status,
            evidence="scripts/audit_platform_readiness.py",
            notes="Audit script executed and returned JSON summary.",
        )
    )
    return gates


def validate_gate_statuses(gates: list[Gate]) -> None:
    for gate in gates:
        if gate.status not in GATE_STATUSES:
            raise ValueError(f"Invalid gate status: {gate.status}")


def _format_lines(items: list[str], *, empty_line: str) -> list[str]:
    return [f"- {item}" for item in items] if items else [empty_line]


def _display_path(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


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
    gate_lines = [
        f"- [{gate.status}] {gate.name} — {gate.evidence}"
        + (f" ({gate.notes})" if gate.notes else "")
        for gate in release_gates
    ]
    commit_lines = _format_lines(
        changelog_items, empty_line="- No new commit subjects found for this window."
    )
    blocker_lines = _format_lines(blockers, empty_line="- None currently listed.")
    warning_lines = _format_lines(warnings, empty_line="- None.")
    excluded_lines = _format_lines(not_promised, empty_line="- None.")
    status_lines = (
        [f"- `{' | '.join(repo.get('status_lines', []))}`"]
        if repo.get("status_lines")
        else ["- Worktree appears clean."]
    )
    if repo.get("status_error"):
        status_lines.append(
            f"\n- Worktree status fallback warning: {repo['status_error']}"
        )

    return (
        f"# Beta Release Sentinel — {date_str}\n\n"
        "## Repo status\n"
        f"- Branch: `{repo.get('branch') or 'unknown'}`\n"
        f"- Head: `{repo.get('head') or 'unknown'}`\n"
        f"- Worktree clean: `{not repo.get('dirty')}`\n"
        + "\n".join(status_lines)
        + "\n\n## Current beta promise\n"
        "- Local-first beta hardening.\n"
        "- Supported path: local Docker Compose.\n"
        "- Supported beta posture: local-only.\n"
        "- Primary operator truth surfaces: `/health`, `/health/chat`, `/api/health/llm`, `/api/llm/catalog`.\n"
        "\n## Release gates\n"
        + "\n".join(gate_lines or ["- `unknown` No gate evidence collected."])
        + "\n\n## Evidence summary\n"
        + "\n".join(commit_lines)
        + "\n\n## Changelog draft\n"
        + "\n".join(commit_lines)
        + "\n\n## Blockers\n"
        + "\n".join(blocker_lines)
        + "\n\n## Warnings\n"
        + "\n".join(warning_lines)
        + "\n\n## Not promised / excluded surfaces\n"
        + "\n".join(excluded_lines)
        + "\n\n## Recommended next actions\n"
        "- Re-run sentinel after runtime changes on current tip.\n"
        "- Keep supported-profile contract and health/catalog surfaces aligned.\n"
        "- Treat this artifact as evidence, not release approval.\n"
        "\n## Machine-readable JSON artifact path\n"
        f"- `{json_path.as_posix()}`\n"
    )


def update_changelog(
    path: Path,
    date_str: str,
    items: list[str],
    blockers: list[str],
    warnings: list[str],
) -> None:
    if path.exists():
        existing = read_text(path).rstrip()
    else:
        existing = "# Beta Changelog\n\nEvidence-led beta readiness changes only.\n"

    lines = [existing, "", f"## {date_str}", "", "### Evidence"]
    lines.extend(f"- {item}" for item in items or ["No new commit subjects discovered for this sentinel window."])
    lines.append("")
    lines.append("### Blockers")
    lines.extend(f"- {item}" for item in blockers or ["None."])
    lines.append("")
    lines.append("### Warnings")
    lines.extend(f"- {item}" for item in warnings or ["None."])
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.json_only and args.markdown_only:
        raise SystemExit("Cannot combine --json-only and --markdown-only.")

    run_date = parse_report_date(args.date)
    date_str = run_date.isoformat()
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = REPO_ROOT / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    changelog_path = Path(args.changelog)
    if not changelog_path.is_absolute():
        changelog_path = REPO_ROOT / changelog_path

    md_path = output_dir / f"{date_str}-beta-sentinel.md"
    json_path = output_dir / f"{date_str}-beta-sentinel.json"

    current_state = read_text(CURRENT_STATE_PATH)
    checklist = extract_release_checklist(current_state)
    repo = collect_repo_status()
    previous = discover_previous_report(date_str, output_dir)
    commits = commit_subjects_since(previous)
    audit_summary = run_platform_readiness()
    audit_warning = None
    blockers = [
        item.get("label", "unknown")
        for item in checklist
        if item.get("mark") != "x"
    ]
    warnings = [
        f"{entry.get('domain', 'unknown')}: {entry.get('label', 'unknown')}"
        for entry in audit_summary.get("warnings", [])
    ]
    not_promised = [
        "cloud-provider beta support",
        "public multi-user deployment",
        "federation durability",
        "graph-write release expansion",
        "unsupported provider paths",
    ]

    gates = build_release_gates(checklist, audit_summary, audit_warning)
    validate_gate_statuses(gates)

    payload = {
        "date": date_str,
        "repo": repo,
        "current_state": {
            "path": "docs/architecture/00-current-state.md",
            "checklist": checklist,
        },
        "audit": audit_summary,
        "release_gates": [gate.__dict__ for gate in gates],
        "commit_subjects": commits,
        "blockers": blockers,
        "warnings": warnings,
        "not_promised": not_promised,
        "generated": {
            "markdown": _display_path(md_path),
            "json": _display_path(json_path),
        },
    }

    md = generate_markdown(
        date_str,
        repo,
        gates,
        commits,
        blockers,
        warnings,
        not_promised,
        Path(_display_path(json_path)),
    )

    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    md_path.write_text(md, encoding="utf-8")
    update_changelog(changelog_path, date_str, commits, blockers, warnings)

    if args.json_only:
        sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True))
        sys.stdout.write("\n")
    elif args.markdown_only:
        sys.stdout.write(md)

    return 0


if __name__ == "__main__":
    sys.exit(main())
