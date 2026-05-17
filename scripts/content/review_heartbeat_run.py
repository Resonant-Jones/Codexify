#!/usr/bin/env python3
"""Review a heartbeat run report for completeness and correctness.

Reads a heartbeat orchestrator report (Markdown), validates that
referenced artifacts exist on disk, scans for secret-like values,
and produces a structured review summary.
"""

from __future__ import annotations

import argparse
import datetime
import json as _json
import re
import sys
from pathlib import Path
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT_DIR = REPO_ROOT / "docs" / "Heartbeat" / "generated"

# Sensitive patterns to detect in reports (same as orchestrator sanitization)
_SECRET_PATTERNS = [
    (
        re.compile(
            r"(?:api[_-]?key|apikey|api_secret|secret_key|access_token|auth_token|bearer|oauth|cookie)\s*[:=]\s*\S+",
            re.IGNORECASE,
        ),
        "credential",
    ),
    (
        re.compile(r"Authorization\s*:\s*Bearer\s+\S+", re.IGNORECASE),
        "Authorization header",
    ),
    (re.compile(r"sk-[a-zA-Z0-9]{20,}"), "OpenAI API key"),
    (
        re.compile(r"(?:ghp|gho|ghu|ghs|ghr|github_pat)_[A-Za-z0-9]{36,}"),
        "GitHub token",
    ),
    (
        re.compile(r"(?:password|passwd|pwd)\s*[:=]\s*\S+", re.IGNORECASE),
        "password",
    ),
    (
        re.compile(
            r"-----BEGIN\s+(?:RSA|DSA|EC|OPENSSH|PGP)?\s*PRIVATE\s+KEY-----"
        ),
        "private key",
    ),
    (
        re.compile(r"eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"),
        "JWT",
    ),
]

# Valid review statuses
VALID_STATUSES = frozenset({"passed", "warning", "failed"})


def _find_report(date_str: str, report_dir: Path) -> Path:
    """Find the heartbeat report for *date_str* in *report_dir*."""
    expected = report_dir / f"{date_str}-heartbeat.md"
    if expected.is_file():
        return expected
    raise FileNotFoundError(
        f"no heartbeat report found for {date_str} in {report_dir}"
    )


def _parse_report(text: str) -> dict[str, Any]:
    """Parse the heartbeat report into structured sections."""
    sections: dict[str, Any] = {
        "title": None,
        "date": None,
        "generated": None,
        "repo_branch": None,
        "repo_head": None,
        "repo_clean": None,
        "run_summary": [],
        "artifacts": [],
        "skipped": [],
        "warnings": [],
        "failures": [],
        "next_actions": [],
    }

    # Title
    title_match = re.search(
        r"^# Heartbeat Orchestrator — (.+)$", text, re.MULTILINE
    )
    if title_match:
        sections["title"] = title_match.group(1)

    # Metadata
    date_match = re.search(r"\*\*Date:\*\*\s*(.+)", text)
    if date_match:
        sections["date"] = date_match.group(1).strip()

    gen_match = re.search(r"\*\*Generated:\*\*\s*(.+)", text)
    if gen_match:
        sections["generated"] = gen_match.group(1).strip()

    # Repo status
    branch_match = re.search(r"\*\*Branch:\*\*\s*`(.+?)`", text)
    if branch_match:
        sections["repo_branch"] = branch_match.group(1)

    head_match = re.search(r"\*\*Head:\*\*\s*`(.+?)`", text)
    if head_match:
        sections["repo_head"] = head_match.group(1)

    clean_match = re.search(r"\*\*Worktree clean:\*\*\s*(.+)", text)
    if clean_match:
        sections["repo_clean"] = clean_match.group(1).strip()

    # Run summary table
    table_match = re.search(
        r"\| Step \| Status \|.*?\n\|[-| ]+\n(.*?)(?=\n\n)", text, re.DOTALL
    )
    if table_match:
        rows = table_match.group(1).strip().splitlines()
        for row in rows:
            cells = [c.strip() for c in row.strip("|").split("|")]
            if len(cells) >= 3:
                sections["run_summary"].append(
                    {
                        "step": cells[0],
                        "status": cells[1].strip("`"),
                        "artifacts": cells[2] if len(cells) > 2 else "",
                        "notes": cells[3] if len(cells) > 3 else "",
                    }
                )

    # Generated artifacts section
    art_section = re.search(
        r"## Generated Artifacts\n\n(.*?)(?=\n## |\Z)", text, re.DOTALL
    )
    if art_section:
        for line in art_section.group(1).strip().splitlines():
            path_match = re.search(r"`(.+?)`", line)
            if path_match:
                sections["artifacts"].append(path_match.group(1))

    return sections


def _mark_issue(
    review: dict[str, Any], message: str, *, strict: bool = False
) -> None:
    """Record an issue.  Status set to 'failed' if strict, else 'warning'."""
    review["status"] = "failed" if strict else "warning"
    review["issues"].append(message)


def review_run(
    *,
    date_str: str,
    report_dir: Path,
    strict: bool = False,
) -> dict[str, Any]:
    """Review a heartbeat run for *date_str*.

    Returns a structured dict with keys: date, heartbeat_report, status,
    parsed, checks, issues, warnings.
    """
    review: dict[str, Any] = {
        "date": date_str,
        "heartbeat_report": None,
        "parsed": {},
        "checks": {},
        "issues": [],
        "warnings": [],
        "status": "passed",
    }

    # 1. Find the report
    try:
        report_path = _find_report(date_str, report_dir)
        review["heartbeat_report"] = str(report_path)
    except FileNotFoundError as exc:
        _mark_issue(review, str(exc), strict=strict)
        return review

    # 2. Parse it
    text = report_path.read_text(encoding="utf-8")
    parsed = _parse_report(text)
    review["parsed"] = parsed

    # 3. Check that at least the run summary exists
    if not parsed["run_summary"]:
        _mark_issue(
            review, "No run summary table found in report", strict=strict
        )
        return review

    # 3b. Verify report title matches expected format
    if parsed["title"] is None:
        _mark_issue(
            review,
            "Report title missing or does not match 'Heartbeat Orchestrator — YYYY-MM-DD'",
            strict=strict,
        )
    elif parsed["title"] != date_str:
        _mark_issue(
            review,
            f"Report title date mismatch: expected {date_str}, got {parsed['title']}",
            strict=strict,
        )

    # 4. Check for failures in the run summary
    failed_steps = [s for s in parsed["run_summary"] if s["status"] == "failed"]
    if failed_steps:
        _mark_issue(
            review,
            f"{len(failed_steps)} step(s) failed: {', '.join(s['step'] for s in failed_steps)}",
            strict=strict,
        )

    # 4b. In strict mode, non-passed steps (including skipped) are issues
    if strict:
        non_passed = [
            s for s in parsed["run_summary"] if s["status"] != "passed"
        ]
        if non_passed:
            _mark_issue(
                review,
                f"{len(non_passed)} step(s) not passed (strict): {', '.join(s['step'] + ':' + s['status'] for s in non_passed)}",
                strict=strict,
            )

    # 5. Check that artifacts are listed (warning, not failure)
    if not parsed["artifacts"]:
        review["warnings"].append("No generated artifacts listed in report")

    # 6. Validate each listed artifact exists on disk
    for art in parsed["artifacts"]:
        art_path = Path(art)
        if not art_path.is_absolute():
            art_path = REPO_ROOT / art_path
        exists = art_path.is_file()
        review["checks"][art] = exists
        if not exists:
            _mark_issue(
                review, f"Artifact not found on disk: {art}", strict=strict
            )

    # 7. Scan for secret-like values in the report
    secret_hits: list[str] = []
    for pattern, label in _SECRET_PATTERNS:
        if pattern.search(text):
            secret_hits.append(label)
    if secret_hits:
        _mark_issue(
            review,
            f"Secret-like values detected in report: {', '.join(sorted(set(secret_hits)))}",
            strict=strict,
        )

    return review


def _print_review(review: dict[str, Any]) -> None:
    """Print a human-readable review summary to stdout."""
    parsed = review.get("parsed", {})
    run_summary = parsed.get("run_summary", [])

    print(f"# Heartbeat Review — {review['date']}")
    print(f"Report: {review.get('heartbeat_report', 'NOT FOUND')}")
    print()

    # Run summary
    print("## Run Summary")
    for step in run_summary:
        status_mark = (
            "✅"
            if step["status"] == "passed"
            else ("❌" if step["status"] == "failed" else "⏭️")
        )
        print(f"  {status_mark} {step['step']}: {step['status']}")
    if not run_summary:
        print("  *(no steps found)*")
    print()

    # Skipped steps
    skipped = [s for s in run_summary if s["status"] == "skipped"]
    if skipped:
        print("## Skipped Steps")
        for s in skipped:
            notes = s.get("notes", "")
            extra = f" — {notes}" if notes and notes != "—" else ""
            print(f"  ⏭️  {s['step']}{extra}")
        print()

    # Warnings
    warnings = review.get("warnings", [])
    if warnings:
        print("## Warnings")
        for w in warnings:
            print(f"  - {w}")
        print()

    # Artifact checks
    if review.get("checks"):
        print("## Artifact Checks")
        for art, exists in review["checks"].items():
            mark = "✅" if exists else "❌"
            print(f"  {mark} {art}")
        print()

    # Issues
    print("## Issues")
    if review["issues"]:
        for issue in review["issues"]:
            print(f"  - {issue}")
    else:
        print("  *(none)*")
    print()

    # Overall
    overall = "PASS" if review["status"] == "passed" else "ISSUES FOUND"
    print(f"**Overall:** {overall}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Review a heartbeat orchestrator run report."
    )
    parser.add_argument(
        "--date",
        default=None,
        help="Date of the heartbeat run (YYYY-MM-DD). Defaults to today.",
    )
    parser.add_argument(
        "--heartbeat-dir",
        type=Path,
        default=DEFAULT_REPORT_DIR,
        help="Directory containing heartbeat reports",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output review as JSON instead of human-readable",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat skipped or non-passed steps as review failures",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    import json

    parser = _build_parser()
    args = parser.parse_args(argv)

    # Default date to today if omitted
    date_str = args.date or datetime.date.today().isoformat()

    # Validate date
    try:
        datetime.date.fromisoformat(date_str)
    except (ValueError, TypeError) as exc:
        print(f"Error: invalid date {date_str!r}: {exc}", file=sys.stderr)
        return 1

    try:
        review = review_run(
            date_str=date_str, report_dir=args.heartbeat_dir, strict=args.strict
        )
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(review, indent=2, sort_keys=True, default=str))
    else:
        _print_review(review)

    return 0 if review["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
