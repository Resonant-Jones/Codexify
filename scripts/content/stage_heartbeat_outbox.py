#!/usr/bin/env python3
"""Stage heartbeat orchestration artifacts into a single outbox directory.

Reads a heartbeat report, verifies all listed artifacts exist, and copies
them into a flat staging directory.  Does not publish externally, schedule,
or activate any automation.
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import shutil
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_HEARTBEAT_DIR = REPO_ROOT / "docs" / "Heartbeat" / "generated"
DEFAULT_STAGED_DIR = REPO_ROOT / "docs" / "Heartbeat" / "staged"

# Review script
REVIEW_SCRIPT = REPO_ROOT / "scripts" / "content" / "review_heartbeat_run.py"


def _find_report(date_str: str, heartbeat_dir: Path) -> Path:
    expected = heartbeat_dir / f"{date_str}-heartbeat.md"
    if expected.is_file():
        return expected
    raise FileNotFoundError(
        f"no heartbeat report found for {date_str} in {heartbeat_dir}"
    )


def _extract_artifact_paths(report_text: str) -> list[str]:
    """Extract artifact paths from the Generated Artifacts section."""
    art_section = re.search(
        r"## Generated Artifacts\n\n(.*?)(?=\n## |\Z)",
        report_text,
        re.DOTALL,
    )
    if not art_section:
        return []

    paths: list[str] = []
    for line in art_section.group(1).strip().splitlines():
        path_match = re.search(r"`(.+?)`", line)
        if path_match:
            paths.append(path_match.group(1))
    return paths


def _resolve_artifact(raw: str) -> Path:
    """Resolve an artifact path to an absolute path."""
    p = Path(raw)
    if not p.is_absolute():
        p = (REPO_ROOT / p).resolve()
    return p.resolve()


def _derive_staged_name(raw: str, date_str: str) -> str:
    """Derive a staged filename with lane prefix to avoid collisions."""
    if "beta-sentinel" in raw:
        if raw.endswith(".json"):
            return f"{date_str}-beta-sentinel.json"
        return f"{date_str}-beta-sentinel.md"
    if "dev-blog" in raw:
        return f"{date_str}-dev-blog.md"
    if "daily-insights" in raw or "ResonantConstructs" in raw:
        return f"{date_str}-daily-insight.md"
    if "heartbeat" in raw:
        return f"{date_str}-heartbeat.md"
    # Fallback: use original filename
    return Path(raw).name


def _generate_drafts(
    date_str: str,
    dated_staged: Path,
    report_text: str,
    skip_review: bool,
) -> list[str]:
    """Generate templated content drafts in the staged directory.

    Returns list of paths to generated draft files.
    """
    drafts: list[str] = []

    def _write(name: str, content: str) -> str:
        p = dated_staged / name
        p.write_text(content, encoding="utf-8")
        drafts.append(str(p))
        return str(p)

    # Parse title from report
    title = f"Heartbeat Orchestrator — {date_str}"
    title_match = re.search(r"^# (.+)$", report_text, re.MULTILINE)
    if title_match:
        title = title_match.group(1).strip()

    # Extract run summary lines
    summary_lines: list[str] = []
    table_match = re.search(
        r"\| Step \| Status \|.*?\n\|[-| ]+\n(.*?)(?=\n\n)",
        report_text,
        re.DOTALL,
    )
    if table_match:
        for line in table_match.group(1).strip().splitlines():
            summary_lines.append(line.strip())

    warning_note = ""
    if skip_review:
        warning_note = (
            "\n> ⚠️  Review gate was skipped. These drafts have NOT been validated.\n"
            "> Re-stage with review enabled before publication.\n"
        )

    header = f"# {title}\n\n**Date:** {date_str}\n**Generated:** {datetime.datetime.now(datetime.UTC).isoformat()}\n"
    footer = (
        "\n---\n"
        "> This is a local draft generated from heartbeat artifacts.\n"
        "> It is not an external publication or release approval.\n"
    )

    # 1. Release summary
    summary = [
        header,
        warning_note,
        "## Run Summary\n",
        "| Step | Status |",
        "|------|--------|",
    ]
    for line in summary_lines:
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) >= 2:
            summary.append(f"| {cells[0]} | {cells[1]} |")
    summary.append("")
    summary.append(
        "## Notes\n\n"
        "This release summary is generated from the local heartbeat "
        "orchestrator run.  Review the source heartbeat report for full details.\n"
    )
    summary.append(footer)
    _write("release-summary.md", "\n".join(summary))

    # 2. Website update
    website_lines = [
        header,
        warning_note,
        "## Website Update Draft\n",
        "*This is a draft for the Codexify website dev-blog section.*\n",
        "### Heartbeat Status\n",
    ]
    for line in summary_lines:
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) >= 2:
            status_icon = (
                "✅"
                if "passed" in cells[1]
                else ("❌" if "failed" in cells[1] else "⏭️")
            )
            website_lines.append(f"- {status_icon} **{cells[0]}**: {cells[1]}")
    website_lines.append("")
    website_lines.append(
        "### Notes\n\n"
        "Generated from heartbeat run. See full report for details.\n"
    )
    website_lines.append(footer)
    _write("website-update.md", "\n".join(website_lines))

    # 3. Substack draft
    substack_lines = [
        header,
        warning_note,
        "## Substack Draft\n",
        "*This is a draft for Substack publication.*\n",
    ]
    substack_lines.append("### Heartbeat Status\n")
    for line in summary_lines:
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) >= 2:
            substack_lines.append(f"- **{cells[0]}**: {cells[1]}")
    substack_lines.append("")
    substack_lines.append(
        "### Notes\n\n"
        "This draft is generated from local heartbeat artifacts. "
        "It requires human review before publishing.\n"
    )
    substack_lines.append(footer)
    _write("substack-draft.md", "\n".join(substack_lines))

    # 4. Email draft
    email_lines = [
        header,
        warning_note,
        "## Email Draft\n",
        "*This is a draft for the daily heartbeat email.*\n",
        f"Subject: Heartbeat — {date_str}\n",
        "",
    ]
    for line in summary_lines:
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) >= 2:
            email_lines.append(f"- **{cells[0]}**: {cells[1]}")
    email_lines.append("")
    email_lines.append(
        "This email draft is generated from local heartbeat artifacts. "
        "Review before sending.\n"
    )
    email_lines.append(footer)
    _write("email-draft.md", "\n".join(email_lines))

    # 5. Source heartbeat (copy of report with staging header)
    source_lines = [
        f"# Heartbeat Source Report — {date_str}\n",
        f"**Staged:** {datetime.datetime.now(datetime.UTC).isoformat()}\n",
        "> This is a copy of the source heartbeat report staged for reference.\n",
        "> It is not an external publication.\n",
        "",
        report_text,
    ]
    _write("source-heartbeat.md", "\n".join(source_lines))

    return drafts


def stage_outbox(
    *,
    date_str: str,
    heartbeat_dir: Path,
    staged_dir: Path,
    dry_run: bool = False,
    force: bool = False,
    skip_review: bool = False,
) -> dict:
    """Stage heartbeat artifacts for *date_str* into *staged_dir*.

    Returns a dict with keys: ok, staged, skipped, errors, review_passed.
    """
    result: dict = {
        "ok": True,
        "date": date_str,
        "staged_dir": str(staged_dir),
        "staged": [],
        "skipped": [],
        "errors": [],
        "warnings": [],
        "review_passed": None,
    }

    # 1. Find the heartbeat report
    try:
        report_path = _find_report(date_str, heartbeat_dir)
    except FileNotFoundError as exc:
        result["ok"] = False
        result["errors"].append(str(exc))
        return result

    # 2. Run review unless skipped
    if not skip_review:
        review_result = subprocess.run(
            [
                sys.executable,
                str(REVIEW_SCRIPT),
                "--date",
                date_str,
                "--heartbeat-dir",
                str(heartbeat_dir),
                "--strict",
                "--json",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if review_result.returncode != 0 or review_result.stderr:
            # Try to parse JSON regardless
            pass

        try:
            review = json.loads(review_result.stdout)
            result["review_passed"] = review.get("status") == "passed"
            if not result["review_passed"]:
                result["ok"] = False
                result["errors"].append(
                    f"Review not passed (status={review.get('status')}). "
                    f"Issues: {review.get('issues', [])}"
                )
                return result
        except Exception:
            result["ok"] = False
            result["errors"].append(
                f"Review failed to produce valid JSON. "
                f"stderr: {review_result.stderr[:200]}"
            )
            return result

    # 3. Extract artifact paths from report
    report_text = report_path.read_text(encoding="utf-8")
    artifact_paths = _extract_artifact_paths(report_text)

    if not artifact_paths:
        result["ok"] = False
        result["errors"].append("No artifact paths found in heartbeat report")
        return result

    # 4. Verify artifacts exist and stage them
    dated_staged = staged_dir / date_str

    if dry_run:
        for raw in artifact_paths:
            art_path = _resolve_artifact(raw)
            if art_path.is_file():
                result["staged"].append(
                    f"[DRY RUN] {art_path} -> {dated_staged / _derive_staged_name(raw, date_str)}"
                )
            else:
                result["errors"].append(f"Artifact not found: {art_path}")
                result["ok"] = False
        return result

    # Create staging directory (date-specific subdirectory)
    dated_staged = staged_dir / date_str

    # If the dated subdirectory already exists and is non-empty, fail without --force
    if dated_staged.exists() and list(dated_staged.iterdir()) and not force:
        result["ok"] = False
        result["errors"].append(
            f"Staged directory {dated_staged} already exists and is non-empty. "
            f"Pass --force to overwrite."
        )
        return result

    dated_staged.mkdir(parents=True, exist_ok=True)

    if skip_review:
        # Write a visible warning file
        (dated_staged / "_SKIP_REVIEW_WARNING.txt").write_text(
            "WARNING: Review gate was skipped (--skip-review). "
            "These artifacts have NOT been validated for completeness or secret leakage. "
            "Re-stage with review enabled before any publication step.\n",
            encoding="utf-8",
        )
        result.setdefault("warnings", []).append(
            "Review gate was skipped. Artifacts are not validated. "
            "Re-stage with review enabled before publication."
        )

    for raw in artifact_paths:
        art_path = _resolve_artifact(raw)
        if not art_path.is_file():
            result["errors"].append(f"Artifact not found: {art_path}")
            result["ok"] = False
            continue

        dest = dated_staged / _derive_staged_name(raw, date_str)

        if dest.exists() and not force:
            result["skipped"].append(
                f"{art_path.name} (exists, use --force to overwrite)"
            )
            continue

        shutil.copy2(art_path, dest)
        result["staged"].append(str(dest))

    # Generate content drafts (before manifest so they appear in generated_files)
    draft_paths = _generate_drafts(
        date_str, dated_staged, report_text, skip_review
    )
    result["drafts"] = draft_paths

    # Scan staged drafts for secrets (same patterns as review)
    _DRAFT_SECRET_PATTERNS = [
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
            re.compile(
                r"eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"
            ),
            "JWT",
        ),
    ]
    for draft_path in draft_paths:
        draft_text = Path(draft_path).read_text(encoding="utf-8")
        for pattern, label in _DRAFT_SECRET_PATTERNS:
            if pattern.search(draft_text):
                Path(draft_path).unlink(missing_ok=True)
                result["drafts"].remove(draft_path)
                result["errors"].append(
                    f"Secret-like value ({label}) detected in draft {Path(draft_path).name}. Draft removed."
                )
                result["ok"] = False
                break

    # Collect all generated file names (artifacts + drafts)
    all_generated = [
        str(Path(s).relative_to(dated_staged)) for s in result["staged"]
    ]
    all_generated += [Path(p).name for p in result["drafts"]]

    # Write a staging manifest
    manifest = {
        "schema_version": "heartbeat.outbox.v1",
        "date": date_str,
        "generated_at": datetime.datetime.now(datetime.UTC).isoformat(),
        "review_required": not skip_review,
        "review_passed": result["review_passed"],
        "review_status": (
            "passed"
            if result["review_passed"]
            else ("skipped" if skip_review else "not_passed")
        ),
        "review_skipped": skip_review,
        "source_heartbeat_report": str(report_path),
        "source_artifacts": [
            str(_resolve_artifact(raw)) for raw in artifact_paths
        ],
        "generated_files": all_generated,
        "total_files": len(all_generated),
        "publication": {
            "enabled": False,
            "targets": [],
            "note": "Publication is deferred. This outbox is a local staging area only.",
        },
        "warnings": result.get("warnings", []),
    }
    (dated_staged / "manifest.json").write_text(
        json.dumps(manifest, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    result["manifest"] = str(dated_staged / "manifest.json")

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Stage heartbeat artifacts into a flat outbox directory."
    )
    parser.add_argument(
        "--date",
        default=None,
        help="Date of the heartbeat run (YYYY-MM-DD). Defaults to today.",
    )
    parser.add_argument(
        "--heartbeat-dir",
        type=Path,
        default=DEFAULT_HEARTBEAT_DIR,
        help="Directory containing heartbeat reports",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_STAGED_DIR,
        dest="staged_dir",
        help="Staging output directory",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned staging without copying files",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing files in staged directory",
    )
    parser.add_argument(
        "--skip-review",
        action="store_true",
        help="Skip the review gate before staging (not recommended)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    date_str = args.date or datetime.date.today().isoformat()

    try:
        datetime.date.fromisoformat(date_str)
    except (ValueError, TypeError) as exc:
        print(f"Error: invalid date {date_str!r}: {exc}", file=sys.stderr)
        return 1

    result = stage_outbox(
        date_str=date_str,
        heartbeat_dir=args.heartbeat_dir,
        staged_dir=args.staged_dir,
        dry_run=args.dry_run,
        force=args.force,
        skip_review=args.skip_review,
    )

    print(json.dumps(result, indent=2, default=str))

    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
