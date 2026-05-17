#!/usr/bin/env python3
"""Heartbeat Orchestrator — run local heartbeat scripts and emit a single report.

This orchestrator invokes three existing repo-local scripts as subprocesses:
  1. Beta Release Sentinel (scripts/release/beta_release_sentinel.py)
  2. Daily Dev Blog ingestion  (scripts/content/ingest_daily_dev_blog.py)
  3. Resonant Constructs Daily Insight (scripts/content/generate_resonant_daily_insight.py)

It produces a dated Markdown heartbeat report under docs/Heartbeat/generated/.
No scheduling, deployment, email, Substack, website publishing, external
automation, or command-bus integration is performed.
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]

# Child script paths (repo-relative to REPO_ROOT)
SENTINEL_SCRIPT = Path("scripts/release/beta_release_sentinel.py")
DEV_BLOG_SCRIPT = Path("scripts/content/ingest_daily_dev_blog.py")
DAILY_INSIGHT_SCRIPT = Path(
    "scripts/content/generate_resonant_daily_insight.py"
)

# Default output directories for child scripts
DEFAULT_SENTINEL_OUTPUT = "docs/audits/generated"
DEFAULT_DEV_BLOG_OUTPUT = "docs/Website/dev-blog/generated"
DEFAULT_INSIGHT_OUTPUT = "docs/ResonantConstructs/daily-insights/generated"

# Orchestrator report output
DEFAULT_OUTPUT_DIR = Path("docs/Heartbeat/generated")

# Allowed step statuses
ALLOWED_STATUSES = frozenset({"passed", "failed", "skipped"})

# Sensitive patterns to sanitize from captured output
_SANITIZE_PATTERNS = [
    # API keys / tokens
    (
        re.compile(
            r"(?:api[_-]?key|apikey|api_secret|secret_key|access_token|auth_token|bearer)\s*[:=]\s*\S+",
            re.IGNORECASE,
        ),
        "[REDACTED: credential]",
    ),
    (re.compile(r"sk-[a-zA-Z0-9]{20,}"), "[REDACTED: api key]"),
    (
        re.compile(r"(?:ghp|gho|ghu|ghs|ghr|github_pat)_[A-Za-z0-9]{36,}"),
        "[REDACTED: github token]",
    ),
    # Passwords
    (
        re.compile(r"(?:password|passwd|pwd)\s*[:=]\s*\S+", re.IGNORECASE),
        "[REDACTED: password]",
    ),
    # Private keys
    (
        re.compile(
            r"-----BEGIN\s+(?:RSA|DSA|EC|OPENSSH|PGP)?\s*PRIVATE\s+KEY-----"
        ),
        "[REDACTED: private key]",
    ),
    # JWT tokens
    (
        re.compile(r"eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"),
        "[REDACTED: jwt]",
    ),
]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _sanitize_output(text: str) -> str:
    """Remove obvious secret-like values from captured output."""
    for pattern, replacement in _SANITIZE_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def _truncate(text: str, max_lines: int = 40) -> str:
    """Truncate text to *max_lines* with a truncation notice."""
    lines = text.splitlines()
    if len(lines) <= max_lines:
        return text
    return (
        "\n".join(lines[:max_lines])
        + f"\n... (truncated, {len(lines)} total lines)"
    )


def _format_timestamp(dt: datetime.datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_child(
    args: list[str],
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Run a child process and return structured result.

    Returns dict with keys: returncode, stdout, stderr, success, error
    """
    if dry_run:
        return {
            "returncode": 0,
            "stdout": "",
            "stderr": "",
            "success": True,
            "error": None,
            "dry_run": True,
        }

    result = subprocess.run(
        args,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    return {
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "success": result.returncode == 0,
        "error": None
        if result.returncode == 0
        else f"Exit code {result.returncode}",
        "dry_run": False,
    }


# ---------------------------------------------------------------------------
# repo status
# ---------------------------------------------------------------------------


def _collect_repo_status() -> dict[str, Any]:
    """Collect basic git repository status for the report."""
    status: dict[str, Any] = {
        "branch": "unknown",
        "head": "unknown",
        "worktree_clean": None,
        "error": None,
    }

    def _git(args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )

    try:
        branch_result = _git(["branch", "--show-current"])
        if branch_result.returncode == 0:
            status["branch"] = branch_result.stdout.strip() or "detached"
    except Exception:
        pass

    try:
        head_result = _git(["rev-parse", "HEAD"])
        if head_result.returncode == 0:
            status["head"] = head_result.stdout.strip()
    except Exception:
        pass

    try:
        dirty_result = _git(["status", "--short", "--untracked-files=normal"])
        if dirty_result.returncode == 0:
            status_lines = [
                ln for ln in dirty_result.stdout.splitlines() if ln.strip()
            ]
            status["worktree_clean"] = len(status_lines) == 0
            status["status_line_count"] = len(status_lines)
    except Exception:
        pass

    return status


# ---------------------------------------------------------------------------
# step runners
# ---------------------------------------------------------------------------


def _run_sentinel(
    date_str: str,
    output_dir: Path,
    dry_run: bool,
    force: bool,
) -> dict[str, Any]:
    """Run Beta Release Sentinel.  Does NOT pass --force (sentinel doesn't support it)."""
    step = {
        "name": "Beta Release Sentinel",
        "script": str(SENTINEL_SCRIPT),
        "status": "skipped",
        "artifacts": [],
        "output": "",
    }

    if dry_run:
        step["status"] = "skipped"
        step["notes"] = "Would run (dry-run)"
        return step

    sentinel_output = REPO_ROOT / DEFAULT_SENTINEL_OUTPUT
    cmd = [
        sys.executable,
        str(REPO_ROOT / SENTINEL_SCRIPT),
        "--date",
        date_str,
        "--output-dir",
        str(sentinel_output),
    ]

    result = _run_child(cmd, dry_run=False)
    sanitized_stdout = _sanitize_output(result["stdout"])
    sanitized_stderr = _sanitize_output(result["stderr"])

    step["output"] = _truncate(sanitized_stdout)

    if result["success"]:
        step["status"] = "passed"
        # Try to extract artifact paths from JSON output
        try:
            payload = json.loads(sanitized_stdout.strip().splitlines()[-1])
            if isinstance(payload, dict):
                for key in ("markdown", "json", "changelog"):
                    if key in payload:
                        step["artifacts"].append(str(payload[key]))
        except (json.JSONDecodeError, IndexError):
            pass
        if not step["artifacts"]:
            step["artifacts"].append(
                f"{sentinel_output}/{date_str}-beta-sentinel.md"
            )
            step["artifacts"].append(
                f"{sentinel_output}/{date_str}-beta-sentinel.json"
            )
    else:
        step["status"] = "failed"
        step["error"] = sanitized_stderr or result["error"]

    return step


def _run_dev_blog(
    date_str: str,
    source_path: Path,
    output_dir: Path,
    dry_run: bool,
    force: bool,
) -> dict[str, Any]:
    """Run Daily Dev Blog ingestion."""
    step = {
        "name": "Daily Dev Blog Ingestion",
        "script": str(DEV_BLOG_SCRIPT),
        "status": "skipped",
        "artifacts": [],
        "output": "",
    }

    if dry_run:
        step["status"] = "skipped"
        step["notes"] = "Would run (dry-run)"
        return step

    dev_blog_output = REPO_ROOT / DEFAULT_DEV_BLOG_OUTPUT
    cmd = [
        sys.executable,
        str(REPO_ROOT / DEV_BLOG_SCRIPT),
        "--date",
        date_str,
        "--source",
        str(source_path),
        "--output-dir",
        str(dev_blog_output),
    ]
    if force:
        cmd.append("--force")

    result = _run_child(cmd, dry_run=False)
    sanitized_stdout = _sanitize_output(result["stdout"])
    sanitized_stderr = _sanitize_output(result["stderr"])

    step["output"] = _truncate(sanitized_stdout)

    if result["success"]:
        step["status"] = "passed"
        step["artifacts"].append(f"{dev_blog_output}/{date_str}.md")
        # Try to parse JSON summary
        try:
            payload = json.loads(sanitized_stdout.strip())
            if isinstance(payload, dict) and "target_path" in payload:
                step["artifacts"] = [str(payload["target_path"])]
        except (json.JSONDecodeError, ValueError):
            pass
        if "written" not in step:
            step["notes"] = "Ingestion completed"
    else:
        step["status"] = "failed"
        step["error"] = sanitized_stderr or result["error"]

    return step


def _run_daily_insight(
    date_str: str,
    source_paths: list[Path],
    output_dir: Path,
    dry_run: bool,
    force: bool,
) -> dict[str, Any]:
    """Run Resonant Constructs Daily Insight generator."""
    step = {
        "name": "Resonant Constructs Daily Insight",
        "script": str(DAILY_INSIGHT_SCRIPT),
        "status": "skipped",
        "artifacts": [],
        "output": "",
    }

    if dry_run:
        step["status"] = "skipped"
        step["notes"] = "Would run (dry-run)"
        return step

    insight_output = REPO_ROOT / DEFAULT_INSIGHT_OUTPUT
    cmd = [
        sys.executable,
        str(REPO_ROOT / DAILY_INSIGHT_SCRIPT),
        "--date",
        date_str,
        "--output-dir",
        str(insight_output),
    ]
    for src in source_paths:
        cmd.extend(["--source", str(src)])
    if force:
        cmd.append("--force")

    result = _run_child(cmd, dry_run=False)
    sanitized_stdout = _sanitize_output(result["stdout"])
    sanitized_stderr = _sanitize_output(result["stderr"])

    step["output"] = _truncate(sanitized_stdout)

    if result["success"]:
        step["status"] = "passed"
        step["artifacts"].append(f"{insight_output}/{date_str}.md")
    else:
        step["status"] = "failed"
        step["error"] = sanitized_stderr or result["error"]

    return step


# ---------------------------------------------------------------------------
# report building
# ---------------------------------------------------------------------------


def _build_report(
    *,
    date_str: str,
    generated_at: str,
    repo_status: dict[str, Any],
    steps: list[dict[str, Any]],
    skipped_steps: list[str],
    warnings: list[str],
    output_path: Path,
) -> str:
    """Build the heartbeat Markdown report."""

    # --- Title & header ---
    lines = [
        f"# Heartbeat Orchestrator — {date_str}",
        "",
        f"**Date:** {date_str}",
        f"**Generated:** {generated_at}",
        "",
    ]

    # --- Repo status ---
    branch = repo_status.get("branch", "unknown")
    head = repo_status.get("head", "unknown")
    clean = repo_status.get("worktree_clean")
    clean_str = (
        "yes" if clean is True else ("no" if clean is False else "unknown")
    )

    lines.extend(
        [
            "## Repo Status",
            "",
            f"- **Branch:** `{branch}`",
            f"- **Head:** `{head}`",
            f"- **Worktree clean:** {clean_str}",
        ]
    )
    if repo_status.get("status_line_count"):
        lines.append(
            f"- **Uncommitted changes:** {repo_status['status_line_count']} lines in git status"
        )
    lines.append("")

    # --- Run summary table ---
    lines.extend(
        [
            "## Run Summary",
            "",
            "| Step | Status | Artifacts | Notes |",
            "|------|--------|-----------|-------|",
        ]
    )

    for step in steps:
        status = step.get("status", "unknown")
        artifacts = ", ".join(step.get("artifacts", [])) or "—"
        notes = step.get("notes", "")
        error = step.get("error", "")
        if error:
            notes = f"{notes} Error: {error}".strip()
        if not notes:
            notes = "—"
        # Escape pipes in notes for Markdown table
        notes = notes.replace("|", "\\|")
        artifacts = artifacts.replace("|", "\\|")
        lines.append(f"| {step['name']} | `{status}` | {artifacts} | {notes} |")

    lines.append("")

    # --- Generated artifact paths ---
    all_artifacts: list[str] = []
    for step in steps:
        all_artifacts.extend(step.get("artifacts", []))

    lines.append("## Generated Artifacts")
    lines.append("")
    if all_artifacts:
        for a in all_artifacts:
            lines.append(f"- `{a}`")
    else:
        lines.append("- *(none)*")
    lines.append("")

    # --- Skipped steps ---
    lines.append("## Skipped Steps")
    lines.append("")
    if skipped_steps:
        for s in skipped_steps:
            lines.append(f"- {s}")
    else:
        lines.append("- *(none)*")
    lines.append("")

    # --- Warnings ---
    lines.append("## Warnings")
    lines.append("")
    if warnings:
        for w in warnings:
            lines.append(f"- {w}")
    else:
        lines.append("- *(none)*")
    lines.append("")

    # --- Failures ---
    failures = [s for s in steps if s.get("status") == "failed"]
    lines.append("## Failures")
    lines.append("")
    if failures:
        for f_step in failures:
            lines.append(f"### {f_step['name']}")
            lines.append("")
            error_text = f_step.get("error", "(no error details)")
            lines.append(f"**Error:** {error_text}")
            lines.append("")
            output_text = f_step.get("output", "").strip()
            if output_text:
                lines.append("**Captured output (sanitized, truncated):**")
                lines.append("")
                lines.append("```")
                lines.append(output_text)
                lines.append("```")
            lines.append("")
    else:
        lines.append("- *(none)*")
    lines.append("")

    # --- Next suggested manual action ---
    lines.append("## Next Suggested Manual Action")
    lines.append("")
    if failures:
        lines.append("- Review failure details in the Failures section above.")
        lines.append(
            "- Re-run individual failing scripts directly with `--force` after addressing errors."
        )
    else:
        lines.append("- Review generated artifacts for accuracy.")
        lines.append(
            "- This report is a local operational artifact, not release approval by itself."
        )
    lines.append(
        "- Commit generated artifacts if they represent desired state."
    )
    lines.append("")

    # --- Footer ---
    lines.extend(
        [
            "---",
            "",
            "> This heartbeat report is generated from local source material and script outputs only.",
            "> It is not an external announcement or release approval.",
            "> Scheduling, deployment, email, Substack, website publishing, command-bus integration,",
            "> and cron integration are intentionally deferred to later tasks.",
            "",
        ]
    )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# main orchestrator
# ---------------------------------------------------------------------------


def run_orchestrator(
    *,
    date_str: str,
    dev_blog_source: Path | None,
    insight_sources: list[Path],
    output_dir: Path,
    dry_run: bool,
    force: bool,
    skip_sentinel: bool,
    skip_dev_blog: bool,
    skip_daily_insight: bool,
) -> str:
    """Run the heartbeat orchestrator and write the report.

    Returns the path of the generated (or would-be generated) report.
    Raises ValueError for invalid inputs, FileExistsError if report exists
    without --force.
    """
    # --- Validate date ---
    try:
        datetime.date.fromisoformat(date_str)
    except (ValueError, TypeError) as exc:
        raise ValueError(
            f"invalid date {date_str!r}: expected YYYY-MM-DD"
        ) from exc

    # --- Validate inputs for non-skipped steps ---
    if not skip_dev_blog and dev_blog_source is None:
        raise ValueError(
            "--dev-blog-source is required unless --skip-dev-blog is passed"
        )
    if not skip_daily_insight and not insight_sources:
        raise ValueError(
            "at least one --insight-source is required unless --skip-daily-insight is passed"
        )

    # --- Compute report path ---
    report_path = output_dir / f"{date_str}-heartbeat.md"

    # --- Handle existing report ---
    if report_path.exists() and not force:
        raise FileExistsError(
            f"heartbeat report already exists: {report_path} (pass --force to overwrite)"
        )

    # --- Dry run ---
    if dry_run:
        return _report_dry_run(
            date_str=date_str,
            output_dir=output_dir,
            report_path=report_path,
            skip_sentinel=skip_sentinel,
            skip_dev_blog=skip_dev_blog,
            skip_daily_insight=skip_daily_insight,
            dev_blog_source=dev_blog_source,
            insight_sources=insight_sources,
        )

    # --- Run steps ---
    generated_at = _format_timestamp(
        datetime.datetime.now(datetime.timezone.utc)
    )
    repo_status = _collect_repo_status()
    steps: list[dict[str, Any]] = []
    skipped_steps: list[str] = []
    warnings: list[str] = []

    if repo_status.get("error"):
        warnings.append(
            f"Repo status collection degraded: {repo_status['error']}"
        )

    # 1. Beta Release Sentinel
    if skip_sentinel:
        skipped_steps.append("Beta Release Sentinel (--skip-beta-sentinel)")
        steps.append(
            {
                "name": "Beta Release Sentinel",
                "script": str(SENTINEL_SCRIPT),
                "status": "skipped",
                "artifacts": [],
                "notes": "Skipped by --skip-beta-sentinel",
            }
        )
    else:
        sentinel_step = _run_sentinel(
            date_str=date_str,
            output_dir=output_dir,
            dry_run=False,
            force=force,
        )
        steps.append(sentinel_step)
        if sentinel_step["status"] == "failed":
            warnings.append(
                "Beta Release Sentinel failed — see Failures section."
            )

    # 2. Daily Dev Blog Ingestion
    if skip_dev_blog:
        skipped_steps.append("Daily Dev Blog Ingestion (--skip-dev-blog)")
        steps.append(
            {
                "name": "Daily Dev Blog Ingestion",
                "script": str(DEV_BLOG_SCRIPT),
                "status": "skipped",
                "artifacts": [],
                "notes": "Skipped by --skip-dev-blog",
            }
        )
    else:
        assert dev_blog_source is not None
        dev_blog_step = _run_dev_blog(
            date_str=date_str,
            source_path=dev_blog_source,
            output_dir=output_dir,
            dry_run=False,
            force=force,
        )
        steps.append(dev_blog_step)
        if dev_blog_step["status"] == "failed":
            warnings.append(
                "Daily Dev Blog ingestion failed — see Failures section."
            )

    # 3. Resonant Constructs Daily Insight
    if skip_daily_insight:
        skipped_steps.append(
            "Resonant Constructs Daily Insight (--skip-daily-insight)"
        )
        steps.append(
            {
                "name": "Resonant Constructs Daily Insight",
                "script": str(DAILY_INSIGHT_SCRIPT),
                "status": "skipped",
                "artifacts": [],
                "notes": "Skipped by --skip-daily-insight",
            }
        )
    else:
        insight_step = _run_daily_insight(
            date_str=date_str,
            source_paths=insight_sources,
            output_dir=output_dir,
            dry_run=False,
            force=force,
        )
        steps.append(insight_step)
        if insight_step["status"] == "failed":
            warnings.append(
                "Resonant Constructs Daily Insight failed — see Failures section."
            )

    # --- Build and write report ---
    report = _build_report(
        date_str=date_str,
        generated_at=generated_at,
        repo_status=repo_status,
        steps=steps,
        skipped_steps=skipped_steps,
        warnings=warnings,
        output_path=report_path,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    print(f"Heartbeat report written: {report_path}")

    return str(report_path)


def _report_dry_run(
    *,
    date_str: str,
    output_dir: Path,
    report_path: Path,
    skip_sentinel: bool,
    skip_dev_blog: bool,
    skip_daily_insight: bool,
    dev_blog_source: Path | None,
    insight_sources: list[Path],
) -> str:
    """Print planned commands and return without writing."""
    print(f"[DRY RUN] Heartbeat Orchestrator — {date_str}")
    print(f"[DRY RUN] Report would be written to: {report_path}")
    print()

    def _plan(script: Path, cmd: list[str]) -> None:
        print(f"[DRY RUN] Would run: {' '.join(str(c) for c in cmd)}")

    sentinel_output = REPO_ROOT / DEFAULT_SENTINEL_OUTPUT
    dev_blog_output = REPO_ROOT / DEFAULT_DEV_BLOG_OUTPUT
    insight_output = REPO_ROOT / DEFAULT_INSIGHT_OUTPUT

    if skip_sentinel:
        print("[DRY RUN] Beta Release Sentinel: SKIPPED")
    else:
        _plan(
            SENTINEL_SCRIPT,
            [
                sys.executable,
                str(REPO_ROOT / SENTINEL_SCRIPT),
                "--date",
                date_str,
                "--output-dir",
                str(sentinel_output),
            ],
        )

    if skip_dev_blog:
        print("[DRY RUN] Daily Dev Blog Ingestion: SKIPPED")
    elif dev_blog_source:
        cmd = [
            sys.executable,
            str(REPO_ROOT / DEV_BLOG_SCRIPT),
            "--date",
            date_str,
            "--source",
            str(dev_blog_source),
            "--output-dir",
            str(dev_blog_output),
        ]
        _plan(DEV_BLOG_SCRIPT, cmd)
    else:
        print("[DRY RUN] Daily Dev Blog Ingestion: NO SOURCE PROVIDED")

    if skip_daily_insight:
        print("[DRY RUN] Resonant Constructs Daily Insight: SKIPPED")
    elif insight_sources:
        cmd = [
            sys.executable,
            str(REPO_ROOT / DAILY_INSIGHT_SCRIPT),
            "--date",
            date_str,
            "--output-dir",
            str(insight_output),
        ]
        for src in insight_sources:
            cmd.extend(["--source", str(src)])
        _plan(DAILY_INSIGHT_SCRIPT, cmd)
    else:
        print(
            "[DRY RUN] Resonant Constructs Daily Insight: NO SOURCES PROVIDED"
        )

    print()
    print("[DRY RUN] No files were written.")
    return str(report_path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Heartbeat Orchestrator — run local heartbeat scripts and emit a report."
    )
    parser.add_argument(
        "--date",
        required=True,
        help="Date for the heartbeat run (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--dev-blog-source",
        type=Path,
        default=None,
        help="Path to the Daily Dev Blog Markdown source file",
    )
    parser.add_argument(
        "--insight-source",
        type=Path,
        action="append",
        dest="insight_sources",
        default=[],
        help="Path to a Resonant Constructs insight source file (repeatable)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / DEFAULT_OUTPUT_DIR,
        help="Output directory for the heartbeat report",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned commands and target path without executing or writing",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing heartbeat report if present",
    )
    parser.add_argument(
        "--skip-beta-sentinel",
        action="store_true",
        help="Skip the Beta Release Sentinel step",
    )
    parser.add_argument(
        "--skip-dev-blog",
        action="store_true",
        help="Skip the Daily Dev Blog ingestion step",
    )
    parser.add_argument(
        "--skip-daily-insight",
        action="store_true",
        help="Skip the Resonant Constructs Daily Insight step",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        output_path = run_orchestrator(
            date_str=args.date,
            dev_blog_source=args.dev_blog_source,
            insight_sources=args.insight_sources or [],
            output_dir=args.output_dir,
            dry_run=args.dry_run,
            force=args.force,
            skip_sentinel=args.skip_beta_sentinel,
            skip_dev_blog=args.skip_dev_blog,
            skip_daily_insight=args.skip_daily_insight,
        )
    except FileExistsError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    # Check for any failed steps
    if not args.dry_run:
        # Re-read the report to check for failures
        try:
            content = Path(output_path).read_text(encoding="utf-8")
            if "`failed`" in content:
                return 1
        except Exception:
            pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
