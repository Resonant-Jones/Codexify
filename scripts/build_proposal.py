#!/usr/bin/env python3
"""Generate draft Build Proposal artifacts.

This script is deterministic within its inputs and current UTC timestamp. It
does not execute proposals, call workers, enqueue jobs, or contact the network.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SOURCE_KINDS = (
    "unity_audit",
    "user_request",
    "validation_failure",
    "operator_note",
    "manual",
)
ARCHITECTURE_IMPACTS = ("none", "possible", "yes")
RISKS = ("low", "medium", "high")


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "proposal"


def _build_proposal(args: argparse.Namespace, now: datetime) -> dict[str, Any]:
    slug = _slugify(args.title)
    timestamp = now.strftime("%Y%m%dT%H%M%S%fZ")
    proposal_id = f"{timestamp}-{slug}"
    summary = args.summary or args.title

    return {
        "schema_version": 1,
        "proposal_id": proposal_id,
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "title": args.title,
        "status": "draft",
        "source": {
            "kind": args.source_kind,
            "references": [],
        },
        "classification": {
            "architecture_impact": args.architecture_impact,
            "adr_impact": "aligned",
            "risk": args.risk,
        },
        "scope": {
            "files_allowed": _split_csv(args.files_allowed),
            "files_forbidden": [],
            "runtime_behavior_change": False,
            "release_scope_change": False,
        },
        "task": {
            "summary": summary,
            "instructions": [],
            "validation": _split_csv(args.validation),
            "commit_message": args.commit_message or "",
        },
        "review": {
            "required": True,
            "review_questions": [],
            "approved_by": None,
            "approved_at": None,
        },
        "execution": {
            "eligible": False,
            "eligible_after": [],
            "harness": "none",
            "run_id": None,
        },
        "proof": {
            "required_receipts": [],
            "result_commit": None,
            "validation_summary": None,
        },
        "lineage": {
            "origin_thread_id": None,
            "origin_message_id": None,
            "audit_artifact": None,
            "parent_proposal_id": None,
        },
    }


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a draft Guardian Build Proposal JSON artifact."
    )
    parser.add_argument("--title", required=True, help="Proposal title.")
    parser.add_argument(
        "--summary",
        help="Proposal summary. Defaults to the title when omitted.",
    )
    parser.add_argument(
        "--source-kind",
        default="manual",
        choices=SOURCE_KINDS,
        help="Governed source kind for the proposal.",
    )
    parser.add_argument(
        "--architecture-impact",
        default="possible",
        choices=ARCHITECTURE_IMPACTS,
        help="Architecture impact classification.",
    )
    parser.add_argument(
        "--risk",
        default="medium",
        choices=RISKS,
        help="Risk classification.",
    )
    parser.add_argument(
        "--files-allowed",
        help="Comma-separated repo paths allowed for this proposal.",
    )
    parser.add_argument(
        "--validation",
        help="Comma-separated validation commands or checks.",
    )
    parser.add_argument("--commit-message", help="Suggested commit message.")
    parser.add_argument(
        "--output-dir",
        default="docs/build-proposals",
        help="Output directory for proposal artifacts.",
    )
    parser.add_argument(
        "--print",
        action="store_true",
        dest="print_json",
        help="Print the generated JSON to stdout.",
    )
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="Do not write the proposal artifact to disk.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])
    now = datetime.now(timezone.utc)
    proposal = _build_proposal(args, now)
    json_payload = json.dumps(proposal, indent=2, sort_keys=True) + "\n"

    if args.print_json:
        sys.stdout.write(json_payload)

    if args.no_write:
        return 0

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{proposal['proposal_id']}.json"
    output_path.write_text(json_payload, encoding="utf-8")

    if not args.print_json:
        print(output_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
