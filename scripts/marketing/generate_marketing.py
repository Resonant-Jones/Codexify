#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.marketing.pipeline import (
    DEFAULT_CHANNELS,
    generate_marketing_artifacts,
)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate draft marketing artifacts from canonical Codexify truth sources."
        )
    )
    parser.add_argument(
        "--campaign-id", required=True, help="Campaign identifier"
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
        default=str(Path(__file__).resolve().parents[2]),
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
        "--dry-run",
        action="store_true",
        help="Validate and render payload without writing output",
    )
    parser.add_argument(
        "--generated-at",
        default=None,
        help="Optional fixed timestamp for deterministic runs (testing only)",
    )
    return parser.parse_args(argv)


def run(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    source_root = Path(args.source_root).resolve()
    output_root = Path(args.output_root).resolve() if args.output_root else None

    channels = [
        item.strip() for item in args.channels.split(",") if item.strip()
    ]

    try:
        result = generate_marketing_artifacts(
            source_root=source_root,
            campaign_id=args.campaign_id,
            audience=args.audience,
            channels=channels,
            mode=args.mode,
            output_root=output_root,
            max_claims=args.max_claims,
            generated_at=args.generated_at,
            write_output=not args.dry_run,
        )
    except Exception as exc:
        print(f"generate-marketing failed: {exc}", file=sys.stderr)
        return 1

    if args.dry_run:
        print(
            json.dumps(
                {"ok": True, "dry_run": True, **result},
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    print(json.dumps({"ok": True, **result}, indent=2, sort_keys=True))
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
