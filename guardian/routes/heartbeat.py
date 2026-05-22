"""
Heartbeat Status Route
~~~~~~~~~~~~~~~~~~~~~~

Read-only route that exposes the latest local Heartbeat pipeline status.
Reads repo-local artifact files only; does not run scripts, shell out,
publish, or schedule.
"""

from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(tags=["heartbeat"])

# Repo root — resolves to the Codexify repository root
_REPO_ROOT = Path(__file__).resolve().parents[2]

# Artifact directories
_HEARTBEAT_GENERATED = _REPO_ROOT / "docs" / "Heartbeat" / "generated"
_STAGED_ROOT = _REPO_ROOT / "docs" / "Heartbeat" / "staged"


# ---------------------------------------------------------------------------
# path helpers — prefer repo-relative in API responses
# ---------------------------------------------------------------------------


def _repo_rel(path: Path) -> str:
    """Return a path as repo-relative if inside the repo, absolute otherwise."""
    try:
        return path.relative_to(_REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


# ---------------------------------------------------------------------------
# discovery
# ---------------------------------------------------------------------------


def _discover_latest_report() -> Path | None:
    """Find the most recent heartbeat report."""
    if not _HEARTBEAT_GENERATED.is_dir():
        return None
    reports = sorted(
        _HEARTBEAT_GENERATED.glob("*-heartbeat.md"),
        key=lambda p: p.name,
        reverse=True,
    )
    return reports[0] if reports else None


def _discover_latest_staged() -> Path | None:
    """Find the most recent staged outbox directory that has a manifest."""
    if not _STAGED_ROOT.is_dir():
        return None
    dirs = sorted(
        [
            d
            for d in _STAGED_ROOT.iterdir()
            if d.is_dir() and (d / "manifest.json").is_file()
        ],
        key=lambda d: d.name,
        reverse=True,
    )
    return dirs[0] if dirs else None


def _extract_date_from_report_name(name: str) -> str:
    """Extract YYYY-MM-DD from heartbeat report filename."""
    # e.g. 2026-05-14-heartbeat.md -> 2026-05-14
    return name.split("-heartbeat")[0]


# ---------------------------------------------------------------------------
# status assembly
# ---------------------------------------------------------------------------


def _read_report_status(report_path: Path) -> dict[str, Any]:
    """Extract review status from a heartbeat report."""
    result: dict[str, Any] = {
        "review_status": "unknown",
        "warnings": [],
        "failures": [],
        "artifact_count": 0,
    }
    try:
        text = report_path.read_text(encoding="utf-8")
    except Exception:
        return result

    import re

    # Check for failed steps in the summary table
    has_failed = bool(re.search(r"\|\s+[^|]*\|\s+`failed`\s+\|", text))
    # Check for skipped steps
    has_skipped = bool(re.search(r"\|\s+[^|]*\|\s+`skipped`\s+\|", text))
    # Check for passed steps
    has_passed = bool(re.search(r"\|\s+[^|]*\|\s+`passed`\s+\|", text))

    if has_failed:
        result["review_status"] = "failed"
    elif has_skipped and not has_passed:
        result["review_status"] = "warning"
    elif has_passed:
        result["review_status"] = "passed"
    else:
        result["review_status"] = "unknown"

    # Extract artifact paths from Generated Artifacts section
    art_section = re.search(
        r"## Generated Artifacts\n\n(.*?)(?=\n## |\Z)", text, re.DOTALL
    )
    if art_section:
        for line in art_section.group(1).strip().splitlines():
            path_match = re.search(r"`(.+?)`", line)
            if path_match:
                result["artifact_count"] += 1

    # Extract warnings from Warnings section
    warn_section = re.search(
        r"## Warnings\n\n(.*?)(?=\n## |\Z)", text, re.DOTALL
    )
    if warn_section:
        for line in warn_section.group(1).strip().splitlines():
            stripped = line.strip("- ").strip()
            if stripped and stripped != "*(none)*":
                result["warnings"].append(stripped)

    # Extract failures from Failures section
    fail_section = re.search(
        r"## Failures\n\n(.*?)(?=\n## |\Z)", text, re.DOTALL
    )
    if fail_section:
        for line in fail_section.group(1).strip().splitlines():
            stripped = line.strip("- ").strip()
            if stripped and stripped != "*(none)*":
                result["failures"].append(stripped)

    return result


def _read_outbox_status(staged_dir: Path) -> dict[str, Any]:
    """Extract staging/outbox status from manifest.json and staged files."""
    result: dict[str, Any] = {
        "outbox_status": "unknown",
        "publication_enabled": False,
        "publication_targets": [],
        "generated_files": [],
        "total_files": 0,
        "review_skipped": False,
    }

    manifest_path = staged_dir / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, FileNotFoundError, ValueError):
        result["outbox_status"] = "warning"
        result["warnings"] = result.get("warnings", []) + [
            "Staged manifest is missing or invalid JSON"
        ]
        return result

    # Check schema
    if manifest.get("schema_version") != "heartbeat.outbox.v1":
        result["outbox_status"] = "warning"
        result["warnings"] = result.get("warnings", []) + [
            "Staged manifest schema_version mismatch"
        ]
        return result

    # Publication status
    pub = manifest.get("publication", {})
    result["publication_enabled"] = pub.get("enabled", False)
    result["publication_targets"] = pub.get("targets", [])

    # Generated files
    result["generated_files"] = manifest.get("generated_files", [])
    result["total_files"] = manifest.get(
        "total_files", len(result["generated_files"])
    )

    # Review skipped
    result["review_skipped"] = manifest.get("review_skipped", False)

    # Check for skip-review warning file
    if (staged_dir / "_SKIP_REVIEW_WARNING.txt").is_file():
        result["warnings"] = result.get("warnings", []) + [
            "Review gate was skipped during staging"
        ]

    # Determine outbox status
    if manifest.get("review_passed") is True and not result["review_skipped"]:
        result["outbox_status"] = "passed"
    elif manifest.get("review_passed") is True and result["review_skipped"]:
        result["outbox_status"] = "warning"
    elif manifest.get("review_passed") is False:
        result["outbox_status"] = "failed"
    else:
        result["outbox_status"] = "unknown"

    return result


# ---------------------------------------------------------------------------
# Pydantic response model
# ---------------------------------------------------------------------------


class HeartbeatStatusResponse(BaseModel):
    latest_date: str | None = None
    heartbeat_report_path: str | None = None
    staged_outbox_path: str | None = None
    review_status: str = "missing"
    outbox_status: str = "missing"
    publication_enabled: bool = False
    publication_targets: list[str] = []
    generated_files: list[str] = []
    warnings: list[str] = []
    failures: list[str] = []
    manual_commands: list[str] = []


# ---------------------------------------------------------------------------
# route
# ---------------------------------------------------------------------------


@router.get("/api/heartbeat/status", response_model=HeartbeatStatusResponse)
async def heartbeat_status() -> HeartbeatStatusResponse:
    """Return the latest local Heartbeat pipeline status.

    Read-only.  Does not run scripts, shell out, publish, or schedule.
    """
    response_data: dict[str, Any] = {
        "latest_date": None,
        "heartbeat_report_path": None,
        "staged_outbox_path": None,
        "review_status": "missing",
        "outbox_status": "missing",
        "publication_enabled": False,
        "publication_targets": [],
        "generated_files": [],
        "warnings": [],
        "failures": [],
        "manual_commands": [],
    }

    # Discover latest report
    report_path = _discover_latest_report()
    if report_path:
        date_str = _extract_date_from_report_name(report_path.name)
        response_data["latest_date"] = date_str
        response_data["heartbeat_report_path"] = _repo_rel(report_path)

        report_status = _read_report_status(report_path)
        response_data["review_status"] = report_status["review_status"]
        response_data["warnings"] = report_status.get("warnings", [])
        response_data["failures"] = report_status.get("failures", [])

    # Discover latest staged outbox
    staged_dir = _discover_latest_staged()
    if staged_dir:
        response_data["staged_outbox_path"] = _repo_rel(staged_dir)

        outbox = _read_outbox_status(staged_dir)
        response_data["outbox_status"] = outbox["outbox_status"]
        response_data["publication_enabled"] = outbox["publication_enabled"]
        response_data["publication_targets"] = outbox["publication_targets"]
        response_data["generated_files"] = outbox.get("generated_files", [])

        # Merge warnings from outbox
        outbox_warnings = outbox.get("warnings", [])
        if outbox_warnings:
            response_data["warnings"].extend(outbox_warnings)

    # Build manual command hints
    commands = []
    if response_data["latest_date"]:
        commands.append(
            f"make heartbeat-full DEV_BLOG_SOURCE=docs/Website/dev-blog/README.md "
            f"INSIGHT_SOURCE=docs/ResonantConstructs/daily-insights/README.md FORCE=1"
        )
        commands.append("make heartbeat-outbox")
    else:
        commands.append(
            "make heartbeat-full DEV_BLOG_SOURCE=docs/Website/dev-blog/README.md "
            "INSIGHT_SOURCE=docs/ResonantConstructs/daily-insights/README.md FORCE=1"
        )
    response_data["manual_commands"] = commands

    return HeartbeatStatusResponse(**response_data)
