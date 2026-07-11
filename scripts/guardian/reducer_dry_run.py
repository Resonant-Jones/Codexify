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
from scripts.guardian.validate_evidence_packet import validate_packet_file
from scripts.guardian.validate_reducer_input_bundle import validate_bundle_file

DRY_RUN_RESULT_SCHEMA_VERSION = "guardian_evidence_packet_reducer_dry_run_result.v1"
INPUT_BUNDLE_DRY_RUN_RESULT_SCHEMA_VERSION = (
    "guardian_evidence_reducer_input_bundle_dry_run_result.v1"
)
EVIDENCE_PACKET_DRY_RUN_DIAGNOSTICS_SCHEMA_VERSION = (
    "guardian_evidence_packet_dry_run_diagnostics.v1"
)
INPUT_BUNDLE_DRY_RUN_LIMITS = (
    "no_source_ref_reads",
    "no_evidence_ingestion",
    "no_packet_generation",
    "no_runtime_reducer_behavior",
    "no_command_bus",
    "no_codex_runner",
    "no_pi_loop",
    "no_provider_execution",
    "no_source_mutation",
    "no_workorder_mutation",
    "no_execution_ledger_write",
    "no_release_support_expansion",
)
EVIDENCE_PACKET_DRY_RUN_LIMITS = (
    "no_source_ref_reads",
    "no_evidence_ingestion",
    "no_packet_generation",
    "no_runtime_reducer_behavior",
    "no_command_bus",
    "no_codex_runner",
    "no_pi_loop",
    "no_provider_execution",
    "no_source_mutation",
    "no_workorder_mutation",
    "no_execution_ledger_write",
    "no_release_support_expansion",
    "no_execution_authority",
    "no_receipt_trust",
)


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
    parser.add_argument(
        "--input-bundle",
        type=Path,
        help="Load one validated ReducerInputBundle JSON file for diagnostics-only dry-run",
    )
    parser.add_argument(
        "--evidence-packet",
        type=Path,
        help="Load one GuardianEvidencePacket fixture for diagnostics-only inspection",
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


def _run_input_bundle(args: argparse.Namespace) -> tuple[dict[str, object], int]:
    """Validate, map metadata, and run the diagnostics-only bundle dry-run."""
    bundle_path = args.input_bundle
    validation_result = validate_bundle_file(bundle_path)
    if validation_result["result"] == "fail":
        return (
            {
                "schema_version": INPUT_BUNDLE_DRY_RUN_RESULT_SCHEMA_VERSION,
                "input_bundle_ref": str(bundle_path),
                "input_bundle_validation_result": validation_result,
                "reducer_result": None,
                "packet": None,
                "validation_result": None,
                "authority_state": false_authority_state(),
                "limits": list(INPUT_BUNDLE_DRY_RUN_LIMITS),
            },
            1,
        )

    bundle_data = json.loads(bundle_path.read_text(encoding="utf-8"))
    refs = tuple(
        ReducerInputRef(
            input_id=item["input_id"],
            input_class=item["input_class"],
            source_ref=item["source_ref"],
            evidence_posture=item["evidence_posture"],
            notes=tuple(item["notes"]),
        )
        for item in bundle_data["inputs"]
    )
    bundle = ReducerInputBundle(
        bundle_id=bundle_data["bundle_id"],
        review_depth=bundle_data["review_depth"],
        inputs=refs,
        operator_context=tuple(bundle_data["operator_context"]),
    )
    result = dry_run_reducer(bundle)
    reducer_result = {
        "packet": result.packet,
        "validation_result": result.validation_result,
        "diagnostics": asdict(result.diagnostics),
    }
    return (
        {
            "schema_version": INPUT_BUNDLE_DRY_RUN_RESULT_SCHEMA_VERSION,
            "input_bundle_ref": str(bundle_path),
            "input_bundle_validation_result": validation_result,
            "reducer_result": reducer_result,
            "packet": None,
            "validation_result": None,
            "authority_state": false_authority_state(),
            "limits": list(INPUT_BUNDLE_DRY_RUN_LIMITS),
        },
        0,
    )


def _run_evidence_packet(args: argparse.Namespace) -> tuple[dict[str, object], int]:
    """Validate a GuardianEvidencePacket fixture and return diagnostics-only output."""
    packet_path = args.evidence_packet
    validation_result = validate_packet_file(packet_path)
    if validation_result["result"] == "fail":
        return (
            {
                "schema_version": EVIDENCE_PACKET_DRY_RUN_DIAGNOSTICS_SCHEMA_VERSION,
                "evidence_packet_ref": str(packet_path),
                "packet_loaded": False,
                "packet_metadata": None,
                "validation_result": validation_result,
                "authority_state": false_authority_state(),
                "diagnostics": None,
                "limits": list(EVIDENCE_PACKET_DRY_RUN_LIMITS),
            },
            1,
        )

    packet_data = json.loads(packet_path.read_text(encoding="utf-8"))
    packet_metadata = {
        "schema_version": packet_data.get("schema_version"),
        "packet_id": packet_data.get("packet_id"),
        "created_at": packet_data.get("created_at"),
        "source_domain": packet_data.get("source_domain"),
        "evidence_class": packet_data.get("evidence_class"),
        "review_depth": packet_data.get("review_depth"),
        "subject": packet_data.get("subject"),
        "reducer_profile_ref": packet_data.get("reducer_profile_ref"),
    }
    diagnostics = {
        "lifecycle_steps_completed": (
            "receive_bounded_evidence_input_set",
            "classify_input_classes",
            "stop",
        ),
        "warnings": (
            f"Evidence packet dry-run diagnostics only; "
            f"this does not produce GuardianEvidencePacket output.",
        ),
        "limits": list(EVIDENCE_PACKET_DRY_RUN_LIMITS),
    }
    return (
        {
            "schema_version": EVIDENCE_PACKET_DRY_RUN_DIAGNOSTICS_SCHEMA_VERSION,
            "evidence_packet_ref": str(packet_path),
            "packet_loaded": True,
            "packet_metadata": packet_metadata,
            "validation_result": validation_result,
            "authority_state": false_authority_state(),
            "diagnostics": diagnostics,
            "limits": list(EVIDENCE_PACKET_DRY_RUN_LIMITS),
        },
        0,
    )


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.evidence_packet is not None and args.input_bundle is not None:
        print("Error: --evidence-packet and --input-bundle are mutually exclusive", file=sys.stderr)
        return 1
    if args.evidence_packet is not None and args.input:
        print("Error: --evidence-packet cannot be combined with --input", file=sys.stderr)
        return 1
    if args.input_bundle is not None and args.input:
        _parser().error("--input-bundle cannot be combined with --input")
    if args.input_bundle is not None:
        output, exit_code = _run_input_bundle(args)
        if args.json:
            print(json.dumps(output, indent=2))
        else:
            print(
                f"Reducer input-bundle dry-run stopped: bundle={output['input_bundle_ref']} "
                f"validation={output['input_bundle_validation_result']['result']}"
            )
        return exit_code
    if args.evidence_packet is not None:
        output, exit_code = _run_evidence_packet(args)
        if args.json:
            print(json.dumps(output, indent=2))
        else:
            validation_status = output["validation_result"]["result"]
            print(
                f"Evidence packet dry-run stopped: packet={output['evidence_packet_ref']} "
                f"validation={validation_status} loaded={output['packet_loaded']}"
            )
        return exit_code
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
