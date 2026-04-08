#!/usr/bin/env python3
"""Ritual automation for regression prevention audit.

Generates weekly, monthly, and quarterly ritual agendas based on current
risk matrix state and recent changes.

Usage:
  python scripts/audit/ritual.py --cadence weekly
  python scripts/audit/ritual.py --cadence monthly
  python scripts/audit/ritual.py --cadence quarterly
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

from scripts.audit.lib.config import DEFAULT_BASELINE_PATH, DEFAULT_CONFIG_PATH
from scripts.audit.lib.scoring import RiskEntry

DEFAULT_OUTPUT_DIR = REPO_ROOT / "docs" / "audits" / "regression"


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate ritual agendas.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --cadence weekly      # Generate weekly agenda
  %(prog)s --cadence monthly     # Generate monthly agenda
  %(prog)s --cadence quarterly   # Generate quarterly drill plan
        """,
    )
    parser.add_argument(
        "--cadence",
        choices=["weekly", "monthly", "quarterly"],
        required=True,
        help="Which ritual cadence to generate",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=DEFAULT_BASELINE_PATH,
        help="Path to risk baseline JSON (default: %(default)s)",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="Path to config JSON (default: %(default)s)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Output directory (default: %(default)s)",
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


def generate_weekly_agenda(risks: list[RiskEntry]) -> dict[str, Any]:
    """Generate weekly ritual agenda."""
    # Find stale entries
    stale = [r for r in risks if r.is_stale]

    # Find highest risks that need attention
    critical_high = [
        r
        for r in risks
        if r.band in ("Critical", "High") and r.status == "active"
    ]

    # Find risks missing owners
    missing_owners = [r for r in risks if not r.owner or r.owner == "TBD"]

    agenda = {
        "cadence": "weekly",
        "title": "Weekly Regression Review (30 minutes)",
        "generated_at": datetime.now().isoformat(),
        "agenda_items": [
            {
                "time": "5 min",
                "topic": "New Incidents or Near-Misses",
                "prompt": "Review any incidents since last week. Update risk matrix if needed.",
                "action": "File incident entries in docs/audits/regression/incidents/",
            },
            {
                "time": "5 min",
                "topic": "Highest Score Risks",
                "prompt": f"Review {len(critical_high[:3])} highest risks needing attention",
                "risks": [
                    {
                        "id": r.id,
                        "area": r.area,
                        "score": r.score,
                        "owner": r.owner,
                    }
                    for r in sorted(
                        critical_high, key=lambda x: x.score, reverse=True
                    )[:3]
                ],
            },
            {
                "time": "5 min",
                "topic": "Stale Entries",
                "prompt": f"{len(stale)} risks haven't been reviewed in their interval",
                "risks": [
                    {
                        "id": r.id,
                        "area": r.area,
                        "days_stale": r.days_since_review,
                    }
                    for r in stale[:5]
                ],
            },
            {
                "time": "5 min",
                "topic": "Subsystem Complexity Changes",
                "prompt": "Did any subsystems grow unexpectedly this week?",
                "action": "Review recent changes for complexity-creep indicators",
            },
            {
                "time": "5 min",
                "topic": "Changes Without Full Eval Coverage",
                "prompt": "Any high-blast-radius changes skip evaluation?",
                "action": "Check docs/audits/regression/traps-*.md for findings",
            },
            {
                "time": "5 min",
                "topic": "Simplification Candidates",
                "prompt": "What can be removed or simplified?",
                "action": "Identify at least one removal/simplification candidate",
            },
        ],
        "action_items": {
            "immediate": [
                {
                    "task": f"Review stale risk: {r.id}",
                    "owner": r.owner or "TBD",
                }
                for r in stale[:2]
            ],
            "this_week": [
                {"task": f"Update controls for {r.area}", "owner": r.owner}
                for r in critical_high[:2]
            ],
        },
        "risks": {
            "total": len(risks),
            "stale": len(stale),
            "critical_high": len(critical_high),
            "missing_owners": len(missing_owners),
        },
    }

    return agenda


def generate_monthly_agenda(risks: list[RiskEntry]) -> dict[str, Any]:
    """Generate monthly ritual agenda."""
    # Calculate band distribution
    by_band: dict[str, int] = {
        "Critical": 0,
        "High": 0,
        "Moderate": 0,
        "Low": 0,
    }
    for r in risks:
        by_band[r.band] = by_band.get(r.band, 0) + 1

    # Find temporary shims that may have become permanent
    # (risks with controls like "temporary" or "shim")
    potential_shims = [
        r
        for r in risks
        if any(
            "temp" in c.lower() or "shim" in c.lower()
            for c in r.current_controls
        )
    ]

    agenda = {
        "cadence": "monthly",
        "title": "Monthly Architecture Audit",
        "generated_at": datetime.now().isoformat(),
        "agenda_items": [
            {
                "time": "15 min",
                "topic": "Re-score Risk Matrix",
                "prompt": "Review and update all 18 risk scores based on current state",
                "action": "Update scripts/audit/data/risk_matrix_baseline.json",
                "current_distribution": by_band,
            },
            {
                "time": "10 min",
                "topic": "Review 'Temporary' Shims",
                "prompt": f"{len(potential_shims)} risks have temporary controls that may be permanent",
                "shims": [
                    {"id": r.id, "control": r.current_controls}
                    for r in potential_shims[:5]
                ],
                "action": "Convert or document permanent shims",
            },
            {
                "time": "10 min",
                "topic": "Provider Dependency Drift",
                "prompt": "Has dependency on any single provider increased?",
                "action": "Check for provider-specific code outside adapters",
            },
            {
                "time": "10 min",
                "topic": "Memory Portability Check",
                "prompt": "Can we still export all user context?",
                "action": "Verify export path works for new data types",
            },
            {
                "time": "10 min",
                "topic": "Orchestration Debt Review",
                "prompt": "Have retry/error handling patterns become inconsistent?",
                "action": "Review scripts/audit/traps-*.md for TRAP-8 findings",
            },
            {
                "time": "10 min",
                "topic": "Observability Gaps",
                "prompt": "Can we explain recent failures?",
                "action": "Review incident log for unexplained issues",
            },
            {
                "time": "15 min",
                "topic": "Subsystem Count Review",
                "prompt": "Are there subsystems that could be merged or removed?",
                "action": "Propose at least one simplification",
            },
        ],
        "action_items": {
            "this_month": [
                {"task": "Update risk matrix scores", "owner": "Architecture"},
                {
                    "task": "Document or remove temporary shims",
                    "owner": "Platform",
                },
                {"task": "Verify memory export path", "owner": "Memory"},
            ],
            "next_month": [
                {"task": "Plan quarterly migration drill", "owner": "Runtime"},
            ],
        },
        "metrics": {
            "critical_risks": by_band["Critical"],
            "high_risks": by_band["High"],
            "total_risks": len(risks),
            "potential_shims": len(potential_shims),
        },
    }

    return agenda


def generate_quarterly_agenda(risks: list[RiskEntry]) -> dict[str, Any]:
    """Generate quarterly ritual agenda."""
    # Pick a subsystem for the drill
    drill_candidates = [
        "embedding model swap",
        "provider disable simulation",
        "retrieval backend replacement",
        "queue implementation swap",
        "integration provider stub",
    ]

    # Find the highest score risk to potentially target
    highest_risk = max(risks, key=lambda r: r.score)

    agenda = {
        "cadence": "quarterly",
        "title": "Quarterly Forced Migration Drill",
        "generated_at": datetime.now().isoformat(),
        "drill": {
            "purpose": "Prove the system is actually portable, not merely described that way",
            "candidates": drill_candidates,
            "recommended": drill_candidates[0],
        },
        "agenda_items": [
            {
                "time": "30 min",
                "topic": "Drill Planning",
                "prompt": "Select one subsystem and plan the migration/failure drill",
                "action": "Use template: docs/audit-templates/migration-drill.md",
            },
            {
                "time": "2 hours",
                "topic": "Execute Drill",
                "prompt": "Perform the migration or failure simulation",
                "safety": "Have rollback plan ready, monitoring in place",
            },
            {
                "time": "30 min",
                "topic": "Document Results",
                "prompt": "What broke? What stayed stable?",
                "action": "File drill report in docs/audits/regression/drills/",
            },
            {
                "time": "30 min",
                "topic": "Cost Analysis",
                "prompt": "Actual migration cost vs. expectation",
                "action": "Update risk matrix with learnings",
            },
            {
                "time": "30 min",
                "topic": "Improvement Planning",
                "prompt": "What would reduce future migration cost?",
                "action": "Create tickets for improvements",
            },
        ],
        "outputs": [
            "Drill execution report",
            "Updated risk matrix (if scores changed)",
            "Improvement tickets created",
            "Next drill candidate selected",
        ],
        "highest_risk_context": {
            "id": highest_risk.id,
            "area": highest_risk.area,
            "score": highest_risk.score,
            "note": "Consider targeting this risk area for next drill",
        },
    }

    return agenda


def render_markdown(agenda: dict[str, Any]) -> str:
    """Render agenda as Markdown."""
    lines: list[str] = []

    lines.append(f"# {agenda['title']}")
    lines.append("")
    lines.append(f"**Generated:** {agenda['generated_at']}")
    lines.append("")

    # Summary metrics
    if "risks" in agenda:
        lines.append("## Summary")
        lines.append("")
        metrics = agenda["risks"]
        lines.append(f"- **Total Risks:** {metrics['total']}")
        lines.append(f"- **Stale Risks:** {metrics['stale']}")
        lines.append(f"- **Critical/High Risks:** {metrics['critical_high']}")
        if metrics.get("missing_owners"):
            lines.append(f"- **Missing Owners:** {metrics['missing_owners']}")
        lines.append("")

    if "metrics" in agenda:
        lines.append("## Current Metrics")
        lines.append("")
        metrics = agenda["metrics"]
        lines.append(f"- **Critical Risks:** {metrics['critical_risks']}")
        lines.append(f"- **High Risks:** {metrics['high_risks']}")
        lines.append(f"- **Total Risks:** {metrics['total_risks']}")
        if metrics.get("potential_shims"):
            lines.append(
                f"- **Potential Permanent Shims:** {metrics['potential_shims']}"
            )
        lines.append("")

    # Agenda items
    lines.append("## Agenda")
    lines.append("")

    for item in agenda["agenda_items"]:
        lines.append(f"### {item['topic']} ({item['time']})")
        lines.append("")
        lines.append(f"**Prompt:** {item['prompt']}")
        lines.append("")

        if "risks" in item:
            lines.append("**Risks to Review:**")
            for risk in item["risks"]:
                lines.append(
                    f"- `{risk['id']}`: {risk.get('area', 'N/A')} ({risk.get('score', 'N/A')})"
                )
            lines.append("")

        if "shims" in item:
            lines.append("**Potential Shims:**")
            for shim in item["shims"]:
                lines.append(f"- `{shim['id']}`: {shim['control']}")
            lines.append("")

        if "action" in item:
            lines.append(f"**Action:** {item['action']}")
            lines.append("")

        if "current_distribution" in item:
            lines.append("**Current Band Distribution:**")
            for band, count in item["current_distribution"].items():
                lines.append(f"- {band}: {count}")
            lines.append("")

    # Action items
    if "action_items" in agenda:
        lines.append("## Action Items")
        lines.append("")

        for category, items in agenda["action_items"].items():
            lines.append(f"### {category.replace('_', ' ').title()}")
            lines.append("")
            for item in items:
                lines.append(
                    f"- [ ] **{item['task']}** (Owner: {item.get('owner', 'TBD')})"
                )
            lines.append("")

    # Drill-specific sections
    if "drill" in agenda:
        lines.append("## Drill Candidates")
        lines.append("")
        lines.append("Select one for this quarter:")
        lines.append("")
        for i, candidate in enumerate(agenda["drill"]["candidates"], 1):
            marker = (
                " (RECOMMENDED)"
                if candidate == agenda["drill"]["recommended"]
                else ""
            )
            lines.append(f"{i}. {candidate}{marker}")
        lines.append("")

        lines.append("## Drill Purpose")
        lines.append("")
        lines.append(f"> {agenda['drill']['purpose']}")
        lines.append("")

    if "outputs" in agenda:
        lines.append("## Expected Outputs")
        lines.append("")
        for output in agenda["outputs"]:
            lines.append(f"- [ ] {output}")
        lines.append("")

    if "highest_risk_context" in agenda:
        lines.append("## Risk Context")
        lines.append("")
        risk = agenda["highest_risk_context"]
        lines.append(
            f"Current highest risk: `{risk['id']}` ({risk['area']}) - Score: {risk['score']}"
        )
        lines.append(f"*Note: {risk['note']}*")
        lines.append("")

    return "\n".join(lines)


def write_output(
    output_dir: Path, agenda: dict[str, Any], markdown: str
) -> tuple[Path, Path]:
    """Write JSON and Markdown output files."""
    output_dir.mkdir(parents=True, exist_ok=True)

    cadence = agenda["cadence"]
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    json_path = output_dir / f"ritual-{cadence}-{timestamp}.json"
    md_path = output_dir / f"ritual-{cadence}-{timestamp}.md"

    # Atomic write for JSON
    temp_json = json_path.with_suffix(".json.tmp")
    temp_json.write_text(
        json.dumps(agenda, indent=2, sort_keys=True, ensure_ascii=False),
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

    # Generate agenda based on cadence
    if args.cadence == "weekly":
        agenda = generate_weekly_agenda(risks)
    elif args.cadence == "monthly":
        agenda = generate_monthly_agenda(risks)
    elif args.cadence == "quarterly":
        agenda = generate_quarterly_agenda(risks)
    else:
        print(f"Error: Unknown cadence: {args.cadence}", file=sys.stderr)
        return 1

    # Render markdown
    markdown = render_markdown(agenda)

    # Output based on format
    if args.format == "json":
        print(json.dumps(agenda, indent=2, sort_keys=True, ensure_ascii=False))
    elif args.format == "md":
        print(markdown)
    else:
        # Write both files
        json_path, md_path = write_output(args.output_dir, agenda, markdown)
        print(f"Wrote {json_path.relative_to(REPO_ROOT)}")
        print(f"Wrote {md_path.relative_to(REPO_ROOT)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
