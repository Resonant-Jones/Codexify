#!/usr/bin/env python3
"""Local CLI wrapper for the pure Guardian Evidence Packet dry-run skeleton."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from guardian.evidence_packets.contracts import false_authority_state
from guardian.evidence_packets.reducer import (
    DRY_RUN_WARNING,
    dry_run_reducer,
)
from guardian.evidence_packets.reducer_contracts import (
    ALLOWED_REDUCER_INPUT_CLASSES,
    REDUCER_CONTRACT_VERSION,
    ReducerInputBundle,
    ReducerInputRef,
    reducer_limits,
)

DRY_RUN_RESULT_SCHEMA_VERSION = "guardian_evidence_packet_reducer_dry_run_result.v1"


def _parse_input(value: str) -> tuple[str, str, str]:
    """Parse an in-memory input descriptor without reading its source ref."""
    parts = value.split(":", 2)
    if len(parts) != 3 or not all(parts):
        raise argparse.ArgumentTypeError(
            "--input must use <input_id>:<input_class>:<source_ref>"
        )
    input_id, input_class, source_ref = parts
    if input_class not in ALLOWED_REDUCER_INPUT_CLASSES:
        raise argparse.ArgumentTypeError(
            f"disallowed reducer input class: {input_class!r}"
        )
    return input_id, input_class, source_ref


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the Guardian Evidence Packet reducer dry-run skeleton."
    )
    parser.add_argument("--json", action="store_true", help="Print diagnostics JSON")
    parser.add_argument("--bundle-id", default="reducer_dry_run")
    parser.add_argument(
        "--review-depth",
        default="light",
        choices=("light", "medium", "high", "xhigh"),
    )
    parser.add_argument(
        "--input",
        action="append",
        type=_parse_input,
        default=[],
        metavar="INPUT_ID:INPUT_CLASS:SOURCE_REF",
    )
    return parser


def _run(args: argparse.Namespace) -> dict[str, object]:
    refs = tuple(
        ReducerInputRef(
            input_id=input_id,
            input_class=input_class,
            source_ref=source_ref,
            evidence_posture="diagnostic",
            notes=(),
        )
        for input_id, input_class, source_ref in args.input
    )
    bundle = ReducerInputBundle(
        bundle_id=args.bundle_id,
        review_depth=args.review_depth,
        inputs=refs,
    )
    result = dry_run_reducer(bundle)
    return {
        "schema_version": DRY_RUN_RESULT_SCHEMA_VERSION,
        "bundle_id": bundle.bundle_id,
        "review_depth": bundle.review_depth,
        "input_count": len(bundle.inputs),
        "packet": result.packet,
        "validation_result": result.validation_result,
        "diagnostics": asdict(result.diagnostics),
        "authority_state": false_authority_state(),
        "limits": list(reducer_limits()),
    }


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    output = _run(args)
    if args.json:
        print(json.dumps(output, indent=2))
    else:
        print(
            f"Reducer dry-run stopped: bundle={output['bundle_id']} "
            f"inputs={output['input_count']} packet=None validation_result=None"
        )
        if DRY_RUN_WARNING not in output["diagnostics"]["warnings"]:  # pragma: no cover
            print(DRY_RUN_WARNING)
    return 0


if __name__ == "__main__":
    sys.exit(main())
