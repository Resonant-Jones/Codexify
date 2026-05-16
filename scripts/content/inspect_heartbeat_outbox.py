#!/usr/bin/env python3
"""Inspect a staged heartbeat outbox directory.

Reads the staging manifest and staged files, prints a summary of what was
staged, and optionally validates the outbox content.  Does not publish,
schedule, or modify files.
"""

from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STAGED_DIR = REPO_ROOT / "docs" / "Heartbeat" / "staged"


def _find_staged_dir(date_str: str, staged_root: Path) -> Path:
    """Find the dated staged subdirectory."""
    expected = staged_root / date_str
    if expected.is_dir() and list(expected.iterdir()):
        return expected
    raise FileNotFoundError(
        f"no staged outbox found for {date_str} in {staged_root}"
    )


def _load_manifest(staged_dir: Path) -> dict[str, Any] | None:
    """Load manifest.json from the staged directory."""
    manifest_path = staged_dir / "manifest.json"
    if not manifest_path.is_file():
        return None
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError):
        return None


def inspect_outbox(
    *,
    date_str: str,
    staged_root: Path,
    strict: bool = False,
) -> dict[str, Any]:
    """Inspect a staged outbox for *date_str*.

    Returns a structured dict with summary and validation results.
    """
    result: dict[str, Any] = {
        "date": date_str,
        "staged_dir": None,
        "status": "passed",
        "manifest": None,
        "packages": [],
        "files": [],
        "drafts": [],
        "artifacts": [],
        "warnings": [],
        "failures": [],
    }

    # 1. Find the staged directory
    try:
        staged_dir = _find_staged_dir(date_str, staged_root)
        result["staged_dir"] = str(staged_dir)
    except FileNotFoundError as exc:
        result["status"] = "failed"
        result["failures"].append(str(exc))
        return result

    # 2. Load manifest
    manifest = _load_manifest(staged_dir)
    result["manifest"] = manifest

    if manifest is None:
        result["failures"].append("manifest.json not found in staged directory")

    # 3. List all files
    all_files = sorted(
        [f for f in staged_dir.iterdir() if f.is_file()],
        key=lambda f: f.name,
    )
    for f in all_files:
        result["files"].append(f.name)
        if f.name.endswith("-draft.md") or f.name in (
            "release-summary.md",
            "website-update.md",
            "substack-draft.md",
            "email-draft.md",
            "source-heartbeat.md",
        ):
            result["drafts"].append(f.name)
        elif f.name != "manifest.json" and not f.name.startswith("_"):
            result["artifacts"].append(f.name)

    # 4. Validate against manifest
    if manifest:
        # Check schema version
        if manifest.get("schema_version") != "heartbeat.outbox.v1":
            result["failures"].append(
                f"Unexpected schema_version: {manifest.get('schema_version')}"
            )
            result["status"] = "failed"

        # Check date matches directory name
        if manifest.get("date") != date_str:
            result["failures"].append(
                f"Manifest date ({manifest.get('date')}) does not match "
                f"directory name ({date_str})"
            )
            result["status"] = "failed"
        # Check publication is disabled
        pub = manifest.get("publication", {})
        if pub.get("enabled") is not False:
            result["failures"].append(
                f"publication.enabled is not false: {pub.get('enabled')}"
            )
            result["status"] = "failed"
        if pub.get("targets") != []:
            result["failures"].append(
                f"publication.targets is not empty: {pub.get('targets')}"
            )
            result["status"] = "failed"

        # Check review is required (unless explicitly skipped)
        if manifest.get("review_required") is not True:
            if not manifest.get("review_skipped"):
                result["failures"].append(
                    f"review_required is not true (got {manifest.get('review_required')})"
                )
                result["status"] = "failed"

        # Check review_status is present
        if manifest.get("review_status") is None:
            result["failures"].append("review_status is missing from manifest")
            result["status"] = "failed"

        expected_files = set(
            manifest.get("generated_files", manifest.get("files", []))
        )
        actual_files = set(result["files"])
        missing = expected_files - actual_files
        extra = actual_files - expected_files - {"manifest.json"}
        # Filter out warning files
        extra = {f for f in extra if not f.startswith("_")}

        if missing:
            result["failures"].append(
                f"Files listed in manifest but missing: {sorted(missing)}"
            )
            result["status"] = "failed"
        if extra:
            result["warnings"].append(
                f"Files present but not in manifest: {sorted(extra)}"
            )

    # 5. Check for skip-review warning
    skip_warning = staged_dir / "_SKIP_REVIEW_WARNING.txt"
    if skip_warning.is_file():
        result["warnings"].append(
            "Review gate was skipped during staging (_SKIP_REVIEW_WARNING.txt present)"
        )
        result["review_skipped"] = True
        result["status"] = (
            "warning" if result["status"] != "failed" else "failed"
        )
    else:
        result["review_skipped"] = False

    # 6. Check publication status
    if manifest and manifest.get("publication", {}).get("enabled") is True:
        result["warnings"].append(
            "Publication is enabled in manifest (unexpected)"
        )
        result["status"] = (
            "warning" if result["status"] != "failed" else "failed"
        )
    else:
        result["publication_enabled"] = False

    # If no failures or warnings, set to passed
    if (
        result["status"] == "passed"
        and not result["failures"]
        and not result["warnings"]
    ):
        pass
    elif result["status"] == "warning" and strict:
        result["status"] = "failed"
        result["failures"].append("Strict mode: warnings promoted to failures")
    elif result["status"] == "failed":
        pass
    elif result["failures"]:
        result["status"] = "failed"
    elif result["warnings"]:
        if strict:
            result["status"] = "failed"
            result["failures"].append(
                "Strict mode: warnings promoted to failures"
            )
        else:
            result["status"] = "warning"
    else:
        result["status"] = "passed"

    return result


def _print_inspection(result: dict[str, Any]) -> None:
    """Print a human-readable inspection summary."""
    print(f"# Heartbeat Outbox Inspection — {result['date']}")
    print(f"Staged dir: {result.get('staged_dir', 'NOT FOUND')}")
    print()

    manifest = result.get("manifest")
    if manifest:
        print("## Manifest")
        print(f"  schema_version: {manifest.get('schema_version', '?')}")
        print(f"  review_passed: {manifest.get('review_passed', '?')}")
        print(f"  review_skipped: {manifest.get('review_skipped', '?')}")
        print(f"  total_files: {manifest.get('total_files', '?')}")
        pub = manifest.get("publication", {})
        print(f"  publication.enabled: {pub.get('enabled', '?')}")
        print()

    print("## Files")
    for f in result["files"]:
        tag = ""
        if f in result["drafts"]:
            tag = " [draft]"
        elif f in result["artifacts"]:
            tag = " [artifact]"
        elif f == "manifest.json":
            tag = " [manifest]"
        elif f.startswith("_"):
            tag = " [warning]"
        print(f"  {f}{tag}")
    print()

    if result.get("review_skipped"):
        print("## ⚠️  Review Gate Skipped")
        print("  Review was bypassed during staging. Artifacts not validated.")
        print()

    print("## Validation")
    if result["failures"]:
        print("### Failures")
        for i in result["failures"]:
            print(f"  - {i}")
    if result["warnings"]:
        print("### Warnings")
        for w in result["warnings"]:
            print(f"  - {w}")
    if not result["failures"] and not result["warnings"]:
        print("  ✅  No issues or warnings")
    print()

    overall = (
        "PASS"
        if result["status"] == "passed"
        else ("WARNING" if result["status"] == "warning" else "FAILED")
    )
    print(f"**Overall:** {overall}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inspect a staged heartbeat outbox directory."
    )
    parser.add_argument(
        "--date",
        default=None,
        help="Date of the staged outbox (YYYY-MM-DD). Defaults to today.",
    )
    parser.add_argument(
        "--staged-dir",
        type=Path,
        default=DEFAULT_STAGED_DIR,
        help="Root directory containing dated staged subdirectories",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output inspection as JSON",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as failures",
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

    result = inspect_outbox(
        date_str=date_str, staged_root=args.staged_dir, strict=args.strict
    )

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        _print_inspection(result)

    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
