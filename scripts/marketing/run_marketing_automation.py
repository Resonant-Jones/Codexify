#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.marketing.pipeline import (
    DEFAULT_CHANNELS,
    generate_marketing_artifacts,
)


def _normalize_date_token(raw: str) -> str:
    token = raw.strip().replace("-", "_")
    parts = token.split("_")
    if len(parts) != 3 or any(not part.isdigit() for part in parts):
        raise ValueError("date must be formatted as YYYY-MM-DD or YYYY_MM_DD")
    year, month, day = parts
    if len(year) != 4 or len(month) != 2 or len(day) != 2:
        raise ValueError("date must use zero-padded month/day")
    return token


def _default_date_token() -> str:
    return datetime.now().astimezone().strftime("%Y_%m_%d")


def _build_campaign_id(date_token: str, suffix: str) -> str:
    normalized_suffix = suffix.strip().replace("-", "_")
    if not normalized_suffix:
        raise ValueError("campaign suffix cannot be empty")
    return f"CAMPAIGN_{date_token}_{normalized_suffix}"


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Automation wrapper for draft-only marketing generation. "
            "Builds deterministic campaign IDs and invokes generate-marketing."
        )
    )
    parser.add_argument(
        "--campaign-id",
        default=None,
        help="Explicit campaign id override (default derives from date + suffix)",
    )
    parser.add_argument(
        "--date",
        default=None,
        help="Date token for campaign id (YYYY-MM-DD or YYYY_MM_DD)",
    )
    parser.add_argument(
        "--campaign-suffix",
        default="MARKETING_V1",
        help="Suffix used when campaign-id is auto-built",
    )
    parser.add_argument(
        "--audience",
        default="local-first-builders",
        help="Audience slug (default: local-first-builders)",
    )
    parser.add_argument(
        "--channels",
        default=",".join(DEFAULT_CHANNELS),
        help="Comma-separated channels (default: website,social,community)",
    )
    parser.add_argument(
        "--mode",
        default="draft",
        choices=["draft"],
        help="Generation mode (v1 supports draft only)",
    )
    parser.add_argument(
        "--source-root",
        default=str(REPO_ROOT),
        help="Repository root path",
    )
    parser.add_argument(
        "--output-root",
        default=None,
        help="Optional output root override",
    )
    parser.add_argument(
        "--max-claims",
        default=24,
        type=int,
        help="Maximum claims to include in evidence ledger",
    )
    parser.add_argument(
        "--generated-at",
        default=None,
        help="Optional fixed timestamp for deterministic runs (testing only)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and render payload without writing output",
    )
    return parser.parse_args(argv)


def run(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    if args.campaign_id:
        campaign_id = args.campaign_id
        campaign_id_source = "explicit"
    else:
        date_token = (
            _normalize_date_token(args.date)
            if args.date
            else _default_date_token()
        )
        campaign_id = _build_campaign_id(date_token, args.campaign_suffix)
        campaign_id_source = "derived"

    channels = [
        item.strip() for item in args.channels.split(",") if item.strip()
    ]
    source_root = Path(args.source_root).resolve()
    output_root = Path(args.output_root).resolve() if args.output_root else None

    try:
        result = generate_marketing_artifacts(
            source_root=source_root,
            campaign_id=campaign_id,
            audience=args.audience,
            channels=channels,
            mode=args.mode,
            output_root=output_root,
            max_claims=args.max_claims,
            generated_at=args.generated_at,
            write_output=not args.dry_run,
        )
    except Exception as exc:
        print(f"run-marketing-automation failed: {exc}", file=sys.stderr)
        return 1

    payload = {
        "ok": True,
        "wrapper": "marketing-automation-v1",
        "campaign_id": campaign_id,
        "campaign_id_source": campaign_id_source,
        "audience": args.audience,
        "channels": sorted(set(channels)),
        "mode": args.mode,
        "approval_state": "draft",
        "dry_run": bool(args.dry_run),
        **result,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
