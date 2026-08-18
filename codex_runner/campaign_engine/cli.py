"""Thin CLI adapter for the provider-free Campaign Engine runtime.

This CLI invokes the runtime service only. It never invokes Pi, Coding Loop,
Guardian execution, the command bus, providers, Git, network, or a database.

Usage:

    python -m codex_runner.campaign_engine.cli run-provider-free \
        --campaign <campaign-fixture.json> \
        [--source-context <lineage-fixture.json>] \
        --output-root <dir> \
        [--json]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .errors import CampaignEngineError, format_issues
from .runtime import run_provider_free_campaign


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="codex_runner.campaign_engine.cli",
        description=(
            "Deterministic provider-free Campaign Engine runtime proof slice "
            "(ADR-066). Zero provider calls, zero source mutations; no Pi, "
            "Coding Loop, Guardian execution, command bus, provider, subprocess "
            "model, network, Git, or database interaction."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser(
        "run-provider-free",
        help="Run one deterministic provider-free Campaign Engine lifecycle slice.",
    )
    run_parser.add_argument(
        "--campaign", required=True, type=Path, help="Campaign Engine fixture document."
    )
    run_parser.add_argument(
        "--source-context",
        type=Path,
        default=None,
        help="Optional bounded source-selection lineage fixture (ARP-equivalent).",
    )
    run_parser.add_argument(
        "--output-root",
        required=True,
        type=Path,
        help="Output root; artifacts land under <output-root>/<campaign_id>/.",
    )
    run_parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the run-result envelope as JSON on stdout.",
    )
    return parser


def _human_summary(result) -> str:
    lines = [
        "Provider-free Campaign Engine run complete",
        f"  classification:     {result.classification}",
        f"  campaign_id:        {result.campaign_id}",
        f"  run_id:             {result.run_id}",
        f"  final campaign:     {result.final_campaign_state}",
        f"  final task:         {result.final_task_state}",
        f"  attempt:            {result.attempt_id} ({result.attempt_state})",
        f"  evaluation:         {result.evaluation_id} ({result.evaluation_verdict})",
        f"  receipt:            {result.receipt_id}",
        f"  bindings:           "
        + ", ".join(
            f"{role}={binding_id}"
            for role, binding_id in sorted(result.binding_ids_by_role.items())
        ),
        f"  output_dir:         {result.output_dir}",
        f"  provider calls:     {result.provider_calls}",
        f"  source mutations:   {result.source_mutations}",
        f"  decision gates:     {result.decision_gates_opened}",
        f"  source context:     "
        + (
            f"present ({result.source_context.get('packet_id')})"
            if result.source_context.get("present")
            else "absent (recorded honestly)"
        ),
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        result = run_provider_free_campaign(
            args.campaign,
            args.output_root,
            source_context_path=args.source_context,
        )
    except CampaignEngineError as exc:
        print(f"provider-free campaign failed: {exc}", file=sys.stderr)
        issues = getattr(exc, "issues", None)
        if issues:
            print(format_issues(issues), file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"provider-free campaign failed: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(_human_summary(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
