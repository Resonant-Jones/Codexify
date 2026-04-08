#!/usr/bin/env python3
"""Risk matrix generator for regression prevention audit.

This script reads the baseline risk matrix, calculates scores, and generates
snapshot reports with optional delta from previous snapshots.

Exit codes:
  0 - Success (report-only mode)

Usage:
  python scripts/audit/risk_matrix.py
  python scripts/audit/risk_matrix.py --delta
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Add repo root to path for imports
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts.audit.lib.config import DEFAULT_BASELINE_PATH
from scripts.audit.lib.scoring import (
    RiskEntry,
    calculate_delta,
    calculate_risk_summary,
)

DEFAULT_OUTPUT_DIR = REPO_ROOT / "docs" / "audits" / "regression"


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate risk matrix snapshot from baseline.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                           # Generate current snapshot
  %(prog)s --delta                   # Include delta from previous
  %(prog)s --format md               # Output markdown to stdout only
        """,
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=DEFAULT_BASELINE_PATH,
        help="Path to baseline JSON (default: %(default)s)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Output directory (default: %(default)s)",
    )
    parser.add_argument(
        "--delta",
        action="store_true",
        help="Include delta from previous snapshot",
    )
    parser.add_argument(
        "--format",
        choices=["json", "md"],
        help="Output format to stdout (default: write both files)",
    )
    return parser.parse_args()


def load_baseline(path: Path) -> list[RiskEntry]:
    """Load risk entries from baseline JSON."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return [RiskEntry.from_dict(r) for r in data.get("risks", [])]


def find_previous_snapshot(output_dir: Path) -> Path | None:
    """Find the most recent previous snapshot."""
    if not output_dir.exists():
        return None

    snapshots = sorted(output_dir.glob("risk-matrix-*.json"))
    if not snapshots:
        return None

    return snapshots[-1]


def load_previous_snapshot(path: Path) -> list[RiskEntry]:
    """Load risk entries from previous snapshot."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return [RiskEntry.from_dict(r) for r in data.get("risks", [])]


def generate_snapshot(
    risks: list[RiskEntry],
    baseline_path: Path,
    include_delta: bool = False,
    previous_risks: list[RiskEntry] | None = None,
) -> dict[str, Any]:
    """Generate snapshot data structure."""
    generated_at = datetime.now().isoformat()
    summary = calculate_risk_summary(risks)

    snapshot = {
        "generated_at": generated_at,
        "baseline_source": str(baseline_path.relative_to(REPO_ROOT)),
        "version": "1.0",
        "risks": [r.to_dict() for r in risks],
        "summary": summary,
    }

    if include_delta and previous_risks:
        delta = calculate_delta(risks, previous_risks)
        snapshot["delta"] = delta
        # Mark newly worsened risks in summary
        summary["newly_worsened"] = [
            c["id"] for c in delta["score_changes"] if c["delta"] > 0
        ]
    else:
        snapshot["delta"] = None

    return snapshot


def render_markdown(snapshot: dict[str, Any]) -> str:
    """Render snapshot as Markdown report."""
    lines: list[str] = []

    # Header
    lines.append("# Risk Matrix Snapshot")
    lines.append("")
    lines.append(f"**Generated:** {snapshot['generated_at']}")
    lines.append(f"**Baseline:** `{snapshot['baseline_source']}`")
    lines.append("")

    # Summary
    summary = snapshot["summary"]
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- **Total risks:** {summary['total']}")
    lines.append("")

    # By band
    lines.append("### By Risk Band")
    lines.append("")
    lines.append("| Band | Count |")
    lines.append("|------|-------|")
    for band in ["Critical", "High", "Moderate", "Low"]:
        count = summary["by_band"].get(band, 0)
        lines.append(f"| {band} | {count} |")
    lines.append("")

    # By owner
    lines.append("### By Owner")
    lines.append("")
    lines.append("| Owner | Count |")
    lines.append("|-------|-------|")
    for owner, count in sorted(summary["by_owner"].items()):
        lines.append(f"| {owner} | {count} |")
    lines.append("")

    # Stale entries
    if summary["stale_entries"]:
        lines.append("### Stale Entries (Review Overdue)")
        lines.append("")
        for risk_id in summary["stale_entries"]:
            lines.append(f"- `{risk_id}`")
        lines.append("")

    # Missing owners
    if summary["missing_owners"]:
        lines.append("### Missing Owners")
        lines.append("")
        for risk_id in summary["missing_owners"]:
            lines.append(f"- `{risk_id}`")
        lines.append("")

    # Highest risks
    lines.append("### Top 5 Highest Risks")
    lines.append("")
    for i, risk_id in enumerate(summary["highest_risks"][:5], 1):
        # Find the risk to get its score
        risk = next((r for r in snapshot["risks"] if r["id"] == risk_id), None)
        if risk:
            lines.append(
                f"{i}. **{risk['area']}** (`{risk_id}`) - Score: {risk['score']} ({risk['band']})"
            )
    lines.append("")

    # Delta
    if snapshot.get("delta"):
        delta = snapshot["delta"]
        lines.append("## Delta from Previous Snapshot")
        lines.append("")

        if delta.get("score_changes"):
            lines.append("### Score Changes")
            lines.append("")
            lines.append("| Risk | Old | New | Delta |")
            lines.append("|------|-----|-----|-------|")
            for change in delta["score_changes"]:
                delta_str = (
                    f"+{change['delta']}"
                    if change["delta"] > 0
                    else str(change["delta"])
                )
                lines.append(
                    f"| `{change['id']}` | {change['old']} | {change['new']} | {delta_str} |"
                )
            lines.append("")

        if delta.get("band_changes"):
            lines.append("### Band Changes")
            lines.append("")
            lines.append("| Risk | Old Band | New Band |")
            lines.append("|------|----------|----------|")
            for change in delta["band_changes"]:
                lines.append(
                    f"| `{change['id']}` | {change['old']} | {change['new']} |"
                )
            lines.append("")

        if delta.get("new_risks"):
            lines.append("### New Risks")
            lines.append("")
            for risk_id in delta["new_risks"]:
                lines.append(f"- `{risk_id}`")
            lines.append("")

        if delta.get("removed_risks"):
            lines.append("### Removed Risks")
            lines.append("")
            for risk_id in delta["removed_risks"]:
                lines.append(f"- `{risk_id}`")
            lines.append("")

    # Risk details
    lines.append("## Risk Details")
    lines.append("")

    # Sort by score descending
    sorted_risks = sorted(
        snapshot["risks"], key=lambda r: r["score"], reverse=True
    )

    for risk in sorted_risks:
        lines.append(f"### {risk['area']}")
        lines.append("")
        lines.append(f"**ID:** `{risk['id']}`")
        lines.append(f"**Failure Mode:** {risk['failure_mode']}")
        lines.append(f"**Score:** {risk['score']} ({risk['band']})")
        lines.append(f"**Owner:** {risk['owner']}")
        lines.append(f"**Status:** {risk['status']}")
        if risk.get("is_stale"):
            lines.append(
                f"**Review Status:** ⚠️ Stale ({risk['days_since_review']} days since last review)"
            )
        else:
            lines.append(
                f"**Review Status:** ✅ Current ({risk['days_since_review']} days since last review)"
            )
        lines.append("")
        lines.append("**Dimensions:**")
        lines.append(f"- Impact: {risk['impact']}")
        lines.append(f"- Likelihood: {risk['likelihood']}")
        lines.append(f"- Detectability: {risk['detectability']}")
        lines.append(f"- Recoverability: {risk['recoverability']}")
        lines.append("")
        lines.append(
            f"**Current Controls:** {', '.join(risk['current_controls'])}"
        )
        lines.append(f"**Next Control:** {risk['next_control']}")
        lines.append("")
        if risk.get("evidence"):
            lines.append("**Evidence:**")
            for ev in risk["evidence"]:
                lines.append(f"- `{ev}`")
            lines.append("")

    return "\n".join(lines)


def write_output(
    output_dir: Path, snapshot: dict[str, Any], markdown: str
) -> tuple[Path, Path]:
    """Write JSON and Markdown output files."""
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S_%f")
    json_path = output_dir / f"risk-matrix-{timestamp}.json"
    md_path = output_dir / f"risk-matrix-{timestamp}.md"

    # Atomic write for JSON
    temp_json = json_path.with_suffix(".json.tmp")
    temp_json.write_text(
        json.dumps(snapshot, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
    )
    temp_json.replace(json_path)

    # Atomic write for Markdown
    temp_md = md_path.with_suffix(".md.tmp")
    temp_md.write_text(markdown, encoding="utf-8")
    temp_md.replace(md_path)

    return json_path, md_path


def main() -> int:
    """Main entry point."""
    args = parse_args()

    # Load baseline
    try:
        risks = load_baseline(args.baseline)
    except FileNotFoundError:
        print(
            f"Error: Baseline file not found: {args.baseline}", file=sys.stderr
        )
        return 1
    except json.JSONDecodeError as e:
        print(f"Error: Invalid baseline JSON: {e}", file=sys.stderr)
        return 1

    # Find and load previous snapshot if requested
    previous_risks = None
    previous_snapshot_path = None
    if args.delta:
        previous_snapshot_path = find_previous_snapshot(args.output_dir)
        if previous_snapshot_path:
            try:
                previous_risks = load_previous_snapshot(previous_snapshot_path)
            except (FileNotFoundError, json.JSONDecodeError):
                pass

    # Generate snapshot
    snapshot = generate_snapshot(
        risks=risks,
        baseline_path=args.baseline,
        include_delta=args.delta,
        previous_risks=previous_risks,
    )

    # Render markdown
    markdown = render_markdown(snapshot)

    # Output based on format
    if args.format == "json":
        print(
            json.dumps(snapshot, indent=2, sort_keys=True, ensure_ascii=False)
        )
    elif args.format == "md":
        print(markdown)
    else:
        # Write both files
        json_path, md_path = write_output(args.output_dir, snapshot, markdown)
        print(f"Wrote {json_path.relative_to(REPO_ROOT)}")
        print(f"Wrote {md_path.relative_to(REPO_ROOT)}")

        # Also print summary to stdout
        summary = snapshot["summary"]
        print(f"\nRisk Matrix Summary:")
        print(f"  Total risks: {summary['total']}")
        print(f"  Critical: {summary['by_band'].get('Critical', 0)}")
        print(f"  High: {summary['by_band'].get('High', 0)}")
        print(f"  Moderate: {summary['by_band'].get('Moderate', 0)}")
        print(f"  Low: {summary['by_band'].get('Low', 0)}")
        if summary.get("stale_entries"):
            print(f"  Stale entries: {len(summary['stale_entries'])}")

    # Report-only mode always exits 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
