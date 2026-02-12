"""Export FlowSpec v0.1 JSON Schemas."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from guardian.flows.spec import FLOW_SPEC_VERSION, FlowRun, FlowSpec


def build_schema_bundle() -> dict[str, Any]:
    """Return schema payload for FlowSpec and FlowRun."""
    return {
        "version": FLOW_SPEC_VERSION,
        "schemas": {
            "FlowSpec": FlowSpec.model_json_schema(),
            "FlowRun": FlowRun.model_json_schema(),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Export FlowSpec JSON Schemas.")
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Optional output file path. Prints to stdout when omitted.",
    )
    args = parser.parse_args()

    payload = json.dumps(build_schema_bundle(), indent=2, sort_keys=True)

    if args.out is None:
        print(payload)
        return 0

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(f"{payload}\n", encoding="utf-8")
    print(str(args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
