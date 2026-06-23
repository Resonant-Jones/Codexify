#!/usr/bin/env python3
"""Explicit, operator-run guardrail metadata backfill for Personal Facts.

This script backfills ``guardrail_metadata`` on existing Personal Facts
candidate rows that were persisted before the guardrail classifier was
introduced (e.g., older imported candidates from ChatGPT exports).

**This is not an automatic startup path.**  It must be run explicitly by
an operator after verifying the dry-run output.

Usage::

    # Dry-run (default) – show what would change without writing.
    python scripts/personal_facts/backfill_guardrail_metadata.py

    # Apply – write guardrail_metadata updates.
    python scripts/personal_facts/backfill_guardrail_metadata.py --apply

    # Force – overwrite existing guardrail_metadata (otherwise skipped).
    python scripts/personal_facts/backfill_guardrail_metadata.py --apply --force

Environment::

    DATABASE_URL    Postgres connection string (required).
                    Also reads GUARDIAN_DATABASE_URL as fallback.

Behaviour::

    - Only rows with status 'candidate' or 'disputed' are eligible.
    - Verified, active, and archived facts are never backfilled.
    - Rows that already have non-empty guardrail_metadata are skipped
      unless ``--force`` is passed.
    - Backfilled metadata always sets ``runtime_eligible=false``.
    - No key, value, status, confidence, or evidence fields are changed.
    - No new revision rows are created by this backfill.
    - The ``backfilled=true`` marker is added so operators can distinguish
      backfill-derived metadata from import-time classification.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from typing import Any

# Ensure the repo root is on sys.path so guardian imports resolve.
_REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from guardian.core.db import GuardianDB
from guardian.personal_facts.guardrail_backfill import (
    plan_guardrail_metadata_backfill,
)

logger = logging.getLogger(__name__)


def _get_db() -> GuardianDB:
    db_url = os.getenv("GUARDIAN_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not db_url:
        print(
            "ERROR: No database URL found. Set DATABASE_URL or "
            "GUARDIAN_DATABASE_URL in the environment.",
            file=sys.stderr,
        )
        sys.exit(1)
    return GuardianDB(db_url)


def _fetch_rows(db: GuardianDB, user_id: str) -> list[dict[str, Any]]:
    """Fetch candidate-like rows that are eligible for backfill.

    Only rows with status 'candidate' or 'disputed' and NULL
    guardrail_metadata are returned.  For each row we also attach the
    first evidence row's metadata so the classifier has source-role /
    source-type context.
    """
    rows = db.list_candidate_facts_missing_guardrail(user_id)
    enriched: list[dict[str, Any]] = []

    for row in rows:
        fact_id = row.get("id")
        if fact_id is None:
            continue

        # Attach evidence context when available.
        try:
            evidence_rows = db.list_fact_evidence(fact_id)
        except Exception:
            evidence_rows = []

        if evidence_rows:
            first = evidence_rows[0]
            row["source_type"] = first.get("source_type")
            row["source_excerpt"] = first.get("excerpt")
            row["evidence_meta"] = first.get("evidence_meta")

        enriched.append(row)

    return enriched


def _print_dry_run_summary(summary_payload: dict[str, Any]) -> None:
    print("=== Guardrail Metadata Backfill — Dry Run ===")
    print(f"  Eligible rows (candidate/disputed, no metadata): "
          f"{summary_payload['total_eligible']}")
    print(f"  Rows that would be updated:                     "
          f"{summary_payload['total_would_update']}")
    print(f"  Skipped — already has metadata:                 "
          f"{summary_payload['skipped_already_has_metadata']}")
    print(f"  Skipped — not candidate-like:                   "
          f"{summary_payload['skipped_not_candidate_like']}")
    print(f"  Skipped — malformed:                            "
          f"{summary_payload['skipped_malformed']}")

    reason_counts = summary_payload.get("reason_counts", {})
    if reason_counts:
        print("\n  Reason-label counts:")
        for reason, count in sorted(reason_counts.items()):
            print(f"    {reason}: {count}")
    else:
        print("\n  (No reason labels produced)")

    if summary_payload.get("force"):
        print("\n  Mode: --force (existing metadata will be overwritten)")
    else:
        print("\n  Mode: default (existing metadata preserved)")

    print("\nRun with --apply to write updates.")


def _print_apply_summary(summary_payload: dict[str, Any], updated: int) -> None:
    print("=== Guardrail Metadata Backfill — Applied ===")
    print(f"  Rows updated:  {updated}")
    print(f"  Skipped — already has metadata:    "
          f"{summary_payload['skipped_already_has_metadata']}")
    print(f"  Skipped — not candidate-like:      "
          f"{summary_payload['skipped_not_candidate_like']}")
    print(f"  Skipped — malformed:               "
          f"{summary_payload['skipped_malformed']}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill guardrail_metadata on Personal Facts candidates.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        default=False,
        help="Write updates (default: dry-run only).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="Overwrite existing non-empty guardrail_metadata (default: skip).",
    )
    parser.add_argument(
        "--user-id",
        default="local",
        help="User ID to scope the backfill to (default: 'local').",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=False,
        help="Print per-row plan details.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    db = _get_db()
    rows = _fetch_rows(db, user_id=args.user_id)

    if not rows:
        print("No candidate rows eligible for backfill found.")
        return

    summary = plan_guardrail_metadata_backfill(rows, force=args.force)

    summary_payload: dict[str, Any] = {
        "total_eligible": summary.total_eligible,
        "total_would_update": summary.total_would_update,
        "skipped_already_has_metadata": summary.skipped_already_has_metadata,
        "skipped_not_candidate_like": summary.skipped_not_candidate_like,
        "skipped_malformed": summary.skipped_malformed,
        "reason_counts": dict(summary.reason_counts),
        "force": args.force,
    }

    if not args.apply:
        _print_dry_run_summary(summary_payload)

        if args.verbose:
            print("\nPer-row plans:")
            for plan in summary.plans:
                status = "UPDATE" if plan.eligible else f"SKIP ({plan.skip_reason})"
                print(
                    f"  fact_id={plan.fact_id:>6}  {status}"
                )
                if plan.eligible and plan.classification is not None:
                    print(
                        f"           disposition={plan.classification.disposition}"
                        f"  reasons={plan.classification.reasons}"
                    )
        return

    # ── apply mode ──────────────────────────────────────────────────────
    updated = 0
    for plan in summary.plans:
        if not plan.eligible:
            continue
        if plan.guardrail_metadata is None:
            continue

        try:
            ok = db.set_fact_guardrail_metadata(
                plan.fact_id, plan.guardrail_metadata
            )
            if ok:
                updated += 1
                if args.verbose:
                    print(
                        f"  Updated fact_id={plan.fact_id} "
                        f"disposition={plan.guardrail_metadata.get('disposition')}"
                    )
            else:
                logger.warning(
                    "set_fact_guardrail_metadata returned False for fact_id=%s",
                    plan.fact_id,
                )
        except Exception as exc:
            logger.error(
                "Failed to update fact_id=%s: %s", plan.fact_id, exc
            )

    _print_apply_summary(summary_payload, updated)
    print(
        "\nNote: guardrail_metadata only was updated. "
        "No revision rows were created by this backfill. "
        "Key, value, status, confidence, and evidence fields are unchanged."
    )


if __name__ == "__main__":
    main()
