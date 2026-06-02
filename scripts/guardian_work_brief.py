from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = Path("docs/guardian/work-briefs")
CURRENT_STATE_PATH = Path("docs/architecture/00-current-state.md")
LATEST_AUDIT_JSON_PATH = Path("docs/audits/latest.json")
LATEST_AUDIT_MD_PATH = Path("docs/audits/latest.md")
MARKETING_HISTORY_PATH = Path("docs/Marketing/generated/history/run-history.jsonl")

GIT_LFS_SAFE_CONFIG = [
    "-c",
    "filter.lfs.process=",
    "-c",
    "filter.lfs.clean=cat",
    "-c",
    "filter.lfs.required=false",
]


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class GeneratedBrief:
    output_dir: str
    axis_brief: str
    codex_next_task: str
    truth_ledger: str
    decision_log: str


def relative(path: Path, repo_root: Path) -> str:
    try:
        return path.relative_to(repo_root).as_posix()
    except ValueError:
        return path.as_posix()


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def run_git(repo_root: Path, *args: str) -> CommandResult:
    completed = subprocess.run(
        ["git", *GIT_LFS_SAFE_CONFIG, *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return CommandResult(completed.returncode, completed.stdout, completed.stderr)


def markdown_section(text: str, heading: str) -> str:
    marker = f"## {heading}"
    start = text.find(marker)
    if start == -1:
        return ""
    body_start = text.find("\n", start)
    if body_start == -1:
        return ""
    next_heading = text.find("\n## ", body_start + 1)
    if next_heading == -1:
        return text[body_start + 1 :].strip()
    return text[body_start + 1 : next_heading].strip()


def bullet_lines(section: str) -> list[str]:
    lines: list[str] = []
    for raw_line in section.splitlines():
        line = raw_line.strip()
        if line.startswith("- "):
            lines.append(line[2:].strip())
        elif line.startswith(("1. ", "2. ", "3. ", "4. ", "5. ")):
            lines.append(line[3:].strip())
    return lines


def collect_current_state(repo_root: Path) -> dict[str, Any]:
    path = repo_root / CURRENT_STATE_PATH
    text = read_text(path)
    return {
        "path": relative(path, repo_root),
        "last_updated": markdown_section(text, "Last updated").strip(),
        "current_phase": markdown_section(text, "Current phase").strip(),
        "what_changed_recently": bullet_lines(
            markdown_section(text, "What changed recently")
        ),
        "current_supported_reality": bullet_lines(
            markdown_section(text, "Current supported reality")
        ),
        "do_not_assume": bullet_lines(
            markdown_section(text, "Not yet true / do not assume")
        ),
        "active_blockers": bullet_lines(markdown_section(text, "Active blockers")),
        "this_weeks_priorities": bullet_lines(
            markdown_section(text, "This week’s priorities")
        ),
        "release_definition": bullet_lines(
            markdown_section(text, "Release definition right now")
        ),
    }


def collect_repo_metadata(repo_root: Path) -> dict[str, Any]:
    branch = run_git(repo_root, "rev-parse", "--abbrev-ref", "HEAD")
    head = run_git(repo_root, "rev-parse", "--short", "HEAD")
    status = run_git(repo_root, "status", "--short", "--branch")
    upstream = run_git(repo_root, "rev-list", "--left-right", "--count", "@{upstream}...HEAD")

    ahead = 0
    behind = 0
    if upstream.returncode == 0:
        parts = upstream.stdout.strip().split()
        if len(parts) == 2:
            behind = int(parts[0])
            ahead = int(parts[1])

    status_lines = [line for line in status.stdout.splitlines() if line.strip()]
    changed_files = [
        line[3:].strip()
        for line in status_lines
        if line and not line.startswith("## ") and len(line) > 3
    ]

    return {
        "branch": branch.stdout.strip() if branch.returncode == 0 else "unknown",
        "head": head.stdout.strip() if head.returncode == 0 else "unknown",
        "ahead": ahead,
        "behind": behind,
        "status_lines": status_lines,
        "changed_files": changed_files,
        "status_error": status.stderr.strip(),
    }


def collect_latest_audit(repo_root: Path) -> dict[str, Any]:
    json_path = repo_root / LATEST_AUDIT_JSON_PATH
    if json_path.exists():
        try:
            payload = json.loads(read_text(json_path))
            parsed_text = payload.get("audit_cli", {}).get("parsed_text", {})
            summary = payload.get("summary") or parsed_text.get("summary_counts", {})
            return {
                "path": relative(json_path, repo_root),
                "format": "json",
                "summary": summary,
                "strongest_domains": payload.get("strongest_domains")
                or payload.get("summary", {}).get("strongest_domains", [])
                or parsed_text.get("strongest_domains", []),
                "weakest_domains": payload.get("weakest_domains")
                or payload.get("summary", {}).get("weakest_domains", [])
                or parsed_text.get("weakest_domains", []),
                "warnings": payload.get("warnings", []),
                "failures": payload.get("failures", []),
                "risk_flags": payload.get("risk_flags", []),
                "selected_mode": payload.get("audit_cli", {}).get("selected_mode"),
                "baseline": payload.get("baseline", {}),
            }
        except json.JSONDecodeError as exc:
            return {
                "path": relative(json_path, repo_root),
                "format": "json",
                "error": f"Could not parse latest audit JSON: {exc}",
            }

    md_path = repo_root / LATEST_AUDIT_MD_PATH
    return {
        "path": relative(md_path, repo_root),
        "format": "markdown" if md_path.exists() else "missing",
        "summary": {},
        "warnings": [],
        "failures": [],
    }


def collect_marketing_history(repo_root: Path, *, limit: int = 5) -> list[dict[str, Any]]:
    path = repo_root / MARKETING_HISTORY_PATH
    if not path.exists():
        return []

    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            records.append({"parse_error": line[:160]})
    return records[-limit:]


def classify_drift(
    repo: dict[str, Any],
    current_state: dict[str, Any],
    audit: dict[str, Any],
    marketing_history: list[dict[str, Any]],
) -> list[dict[str, str]]:
    drift: list[dict[str, str]] = []
    if repo.get("behind", 0):
        drift.append(
            {
                "kind": "repo_sync",
                "signal": f"Branch is behind upstream by {repo['behind']} commit(s).",
                "why_it_matters": "Release proof should be tied to the current main tip.",
            }
        )
    if repo.get("changed_files"):
        drift.append(
            {
                "kind": "dirty_worktree",
                "signal": f"{len(repo['changed_files'])} changed file(s) are present.",
                "why_it_matters": "Unclassified local changes can blur what is proven.",
            }
        )
    if current_state.get("do_not_assume"):
        drift.append(
            {
                "kind": "release_claim_boundary",
                "signal": current_state["do_not_assume"][0],
                "why_it_matters": "Axis and Codex should not steer from aspirational claims.",
            }
        )
    if audit.get("failures"):
        drift.append(
            {
                "kind": "audit_failure",
                "signal": f"{len(audit['failures'])} audit failure(s) reported.",
                "why_it_matters": "Failures need a repair task before wider planning.",
            }
        )
    draft_runs = [
        item
        for item in marketing_history
        if item.get("approval_state") == "draft" or item.get("mode") == "draft"
    ]
    if draft_runs:
        drift.append(
            {
                "kind": "draft_publication_boundary",
                "signal": f"{len(draft_runs)} recent marketing/history run(s) are draft.",
                "why_it_matters": "Draft packets are alignment inputs, not release proof.",
            }
        )
    return drift


def choose_decision(
    repo: dict[str, Any],
    current_state: dict[str, Any],
    drift: list[dict[str, str]],
) -> dict[str, Any]:
    if repo.get("behind", 0):
        focus = "Synchronize the working branch before making release claims."
        rationale = "The branch is behind upstream, so proof gathered here may be stale."
    elif repo.get("changed_files"):
        focus = "Classify local changes before starting a new implementation slice."
        rationale = "A dirty worktree makes it harder to know what Axis should trust."
    elif current_state.get("active_blockers"):
        focus = current_state["active_blockers"][0]
        rationale = "Current-state blockers are the strongest local steering input."
    else:
        focus = "Run one supported-path proof and record a go/hold decision."
        rationale = "No stronger blocker was detected from current-state or repo metadata."

    return {
        "focus": focus,
        "rationale": rationale,
        "next_task_type": "truth_closure",
        "drift_count": len(drift),
    }


def build_truth_ledger(repo_root: Path, brief_date: str) -> dict[str, Any]:
    current_state = collect_current_state(repo_root)
    repo = collect_repo_metadata(repo_root)
    audit = collect_latest_audit(repo_root)
    marketing_history = collect_marketing_history(repo_root)
    drift = classify_drift(repo, current_state, audit, marketing_history)
    decision = choose_decision(repo, current_state, drift)

    return {
        "schema_version": "guardian-work-brief/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "brief_date": brief_date,
        "purpose": (
            "Manual alignment packet for Axis plus a narrow Codex task packet "
            "for solo-builder steering."
        ),
        "repo": repo,
        "truth_sources": {
            "current_state": current_state["path"],
            "latest_audit": audit.get("path"),
            "marketing_history": relative(repo_root / MARKETING_HISTORY_PATH, repo_root),
        },
        "reality": {
            "current_phase": current_state.get("current_phase"),
            "current_supported_reality": current_state.get("current_supported_reality", []),
            "release_definition": current_state.get("release_definition", []),
            "audit_summary": audit.get("summary", {}),
            "strongest_domains": audit.get("strongest_domains", []),
            "weakest_domains": audit.get("weakest_domains", []),
        },
        "drift": drift,
        "risk": {
            "do_not_assume": current_state.get("do_not_assume", []),
            "active_blockers": current_state.get("active_blockers", []),
            "audit_warnings": audit.get("warnings", []),
            "audit_failures": audit.get("failures", []),
            "audit_risk_flags": audit.get("risk_flags", []),
        },
        "decision": decision,
        "recent_marketing_history": marketing_history,
        "human_closeout": {
            "finished_today": "",
            "blocked": "",
            "next_priority": decision["focus"],
            "axis_kb_note": "",
        },
    }


def format_list(items: list[Any], *, empty: str = "None recorded.") -> str:
    if not items:
        return f"- {empty}"
    lines = []
    for item in items:
        if isinstance(item, dict):
            label = item.get("signal") or item.get("label") or json.dumps(item, sort_keys=True)
            lines.append(f"- {label}")
        else:
            lines.append(f"- {item}")
    return "\n".join(lines)


def render_axis_brief(ledger: dict[str, Any]) -> str:
    repo = ledger["repo"]
    reality = ledger["reality"]
    risk = ledger["risk"]
    decision = ledger["decision"]

    return f"""# Guardian Work Brief - {ledger['brief_date']}

Purpose: manual transfer packet for Axis and steering packet for the next Codex task.

## Reality
- Branch: `{repo['branch']}` at `{repo['head']}`
- Upstream delta: behind `{repo['behind']}`, ahead `{repo['ahead']}`
- Latest audit: PASS `{reality.get('audit_summary', {}).get('pass', 'unknown')}`, WARN `{reality.get('audit_summary', {}).get('warn', 'unknown')}`, FAIL `{reality.get('audit_summary', {}).get('fail', 'unknown')}`
- Current phase: {reality.get('current_phase') or 'Unknown.'}

## Supported Truth
{format_list(reality.get('current_supported_reality', []))}

## Drift
{format_list(ledger.get('drift', []))}

## Risk
{format_list(risk.get('active_blockers', []))}

## Do Not Assume
{format_list(risk.get('do_not_assume', []))}

## Decision
- Focus: {decision['focus']}
- Rationale: {decision['rationale']}

## Manual Closeout
- Finished today:
- Blocked:
- Next priority: {ledger['human_closeout']['next_priority']}
- Axis KB note:
"""


def render_codex_task(ledger: dict[str, Any]) -> str:
    decision = ledger["decision"]
    risk = ledger["risk"]
    repo = ledger["repo"]

    return f"""# Codex Next Task - {ledger['brief_date']}

## Goal
{decision['focus']}

## Context
- Current branch: `{repo['branch']}` at `{repo['head']}`
- This task exists to turn the Guardian Work Brief into one narrow implementation or verification step.
- Treat `docs/architecture/00-current-state.md` as the release-truth gate.

## Constraints
- Do not widen the supported release promise.
- Do not treat draft marketing or audit artifacts as runtime proof.
- Preserve existing user changes unless explicitly asked to touch them.
- Keep the task bounded to the smallest change that resolves the stated focus.

## Current Risks To Respect
{format_list(risk.get('active_blockers', [])[:5])}

## Acceptance Criteria
- The work produces one clear `go`, `hold`, or `next-proof-needed` outcome.
- Files changed are limited to the stated implementation or verification slice.
- Validation commands and results are recorded.
- The final response includes what Axis should add to his KB.
"""


def render_decision_log(ledger: dict[str, Any]) -> str:
    decision = ledger["decision"]
    return f"""# Guardian Decision Log - {ledger['brief_date']}

## Decision
{decision['focus']}

## Why
{decision['rationale']}

## Inputs
- Current-state source: `{ledger['truth_sources']['current_state']}`
- Latest audit source: `{ledger['truth_sources']['latest_audit']}`
- Marketing history source: `{ledger['truth_sources']['marketing_history']}`

## Closeout
- Finished today:
- Blocked:
- Next priority: {ledger['human_closeout']['next_priority']}
- Axis KB note:
"""


def write_outputs(
    ledger: dict[str, Any],
    *,
    repo_root: Path,
    output_dir: Path,
) -> GeneratedBrief:
    dated_dir = output_dir / ledger["brief_date"]
    dated_dir.mkdir(parents=True, exist_ok=True)

    axis_path = dated_dir / "axis-brief.md"
    codex_path = dated_dir / "codex-next-task.md"
    ledger_path = dated_dir / "truth-ledger.json"
    decision_path = dated_dir / "decision-log.md"

    axis_text = render_axis_brief(ledger)
    codex_text = render_codex_task(ledger)
    decision_text = render_decision_log(ledger)

    axis_path.write_text(axis_text, encoding="utf-8")
    codex_path.write_text(codex_text, encoding="utf-8")
    ledger_path.write_text(
        json.dumps(ledger, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    decision_path.write_text(decision_text, encoding="utf-8")

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "latest-axis-brief.md").write_text(axis_text, encoding="utf-8")
    (output_dir / "latest-codex-next-task.md").write_text(
        codex_text,
        encoding="utf-8",
    )
    (output_dir / "latest-truth-ledger.json").write_text(
        json.dumps(ledger, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "latest-decision-log.md").write_text(
        decision_text,
        encoding="utf-8",
    )

    return GeneratedBrief(
        output_dir=relative(dated_dir, repo_root),
        axis_brief=relative(axis_path, repo_root),
        codex_next_task=relative(codex_path, repo_root),
        truth_ledger=relative(ledger_path, repo_root),
        decision_log=relative(decision_path, repo_root),
    )


def generate_work_brief(
    *,
    repo_root: Path,
    output_dir: Path,
    brief_date: str,
) -> GeneratedBrief:
    ledger = build_truth_ledger(repo_root, brief_date)
    resolved_output_dir = output_dir
    if not output_dir.is_absolute():
        resolved_output_dir = repo_root / output_dir
    return write_outputs(
        ledger,
        repo_root=repo_root,
        output_dir=resolved_output_dir,
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a Guardian Work Brief for Axis and Codex task steering."
    )
    parser.add_argument(
        "--date",
        default=date.today().isoformat(),
        help="Brief date in YYYY-MM-DD format. Defaults to today.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory for dated and latest brief artifacts.",
    )
    parser.add_argument(
        "--repo-root",
        default=str(REPO_ROOT),
        help="Repository root to inspect.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    generated = generate_work_brief(
        repo_root=Path(args.repo_root).resolve(),
        output_dir=Path(args.output_dir),
        brief_date=args.date,
    )
    print("Guardian Work Brief generated")
    print(f"  Axis brief: {generated.axis_brief}")
    print(f"  Codex next task: {generated.codex_next_task}")
    print(f"  Truth ledger: {generated.truth_ledger}")
    print(f"  Decision log: {generated.decision_log}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
