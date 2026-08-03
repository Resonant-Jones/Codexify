#!/usr/bin/env python3
"""Report the canonical Pi readiness posture for worker-coding."""

from __future__ import annotations

import argparse

from guardian.agents.pi_readiness import evaluate_pi_readiness


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--format",
        choices=("human", "json"),
        default="human",
        help="output format (default: human)",
    )
    args = parser.parse_args()

    report = evaluate_pi_readiness()
    print(report.to_json() if args.format == "json" else report.to_human())
    return 0 if report.can_consume_tasks else 78


if __name__ == "__main__":
    raise SystemExit(main())
