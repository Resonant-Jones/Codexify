from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "docs" / "build-proposals"
SOURCE_KIND_CHOICES = (
    "unity_audit",
    "user_request",
    "validation_failure",
    "operator_note",
    "manual",
)
ARCHITECTURE_IMPACT_CHOICES = ("none", "possible", "yes")
ADR_IMPACT_CHOICES = ("none", "aligned", "requires_new", "supersedes_existing")
RISK_CHOICES = ("low", "medium", "high")


def slugify(value: str) -> str:
    lowered = value.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    return slug or "proposal"


def parse_csv(raw: str | None) -> list[str]:
    if raw is None:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def make_proposal_id(title: str, created_at: datetime) -> str:
    return f"proposal-{created_at.strftime('%Y%m%dT%H%M%SZ')}-{slugify(title)}"


def build_review_questions(architecture_impact: str) -> list[str]:
    questions = [
        "What evidence justifies creating this proposal now?",
        "Is the file scope narrow enough for bounded review and execution later?",
        "What validation would distinguish a code-path-only change from runtime proof?",
    ]
    if architecture_impact in {"possible", "yes"}:
        questions.append(
            "Does this proposal require ADR alignment or a new architecture decision before approval?"
        )
    return questions


def default_required_receipts(validation: list[str]) -> list[str]:
    receipts: list[str] = ["human_review_decision"]
    if validation:
        receipts.append("validation_command_receipts")
    return receipts


def build_proposal(args: argparse.Namespace) -> dict[str, object]:
    created_at = utc_now()
    proposal_id = make_proposal_id(args.title, created_at)
    title = args.title.strip()
    summary = args.summary.strip() if args.summary else title
    files_allowed = parse_csv(args.files_allowed)
    validation = parse_csv(args.validation)
    source_references = parse_csv(args.source_references)

    proposal = {
        "schema_version": 1,
        "proposal_id": proposal_id,
        "created_at": created_at.isoformat().replace("+00:00", "Z"),
        "title": title,
        "status": "draft",
        "source": {
            "kind": args.source_kind,
            "references": source_references,
        },
        "classification": {
            "architecture_impact": args.architecture_impact,
            "adr_impact": args.adr_impact,
            "risk": args.risk,
        },
        "scope": {
            "files_allowed": files_allowed,
            "files_forbidden": [],
            "runtime_behavior_change": False,
            "release_scope_change": False,
        },
        "task": {
            "summary": summary,
            "instructions": [],
            "validation": validation,
            "commit_message": args.commit_message.strip()
            if args.commit_message
            else "",
        },
        "review": {
            "required": True,
            "review_questions": build_review_questions(
                args.architecture_impact
            ),
            "approved_by": None,
            "approved_at": None,
        },
        "execution": {
            "eligible": False,
            "eligible_after": ["human_review_approval"],
            "harness": "none",
            "run_id": None,
        },
        "proof": {
            "required_receipts": default_required_receipts(validation),
            "result_commit": None,
            "validation_summary": None,
        },
        "lineage": {
            "origin_thread_id": None,
            "origin_message_id": None,
            "audit_artifact": None,
            "parent_proposal_id": None,
        },
    }

    if args.source_kind == "unity_audit":
        proposal["execution"]["eligible_after"] = [
            "human_review_approval",
            "scope_confirmation",
        ]
    return proposal


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a draft Guardian Build Proposal artifact."
    )
    parser.add_argument("--title", help="Proposal title.")
    parser.add_argument(
        "--summary", help="Proposal summary; defaults to title."
    )
    parser.add_argument(
        "--source-kind",
        default="manual",
        choices=SOURCE_KIND_CHOICES,
        help="Proposal source kind.",
    )
    parser.add_argument(
        "--source-references",
        help="Comma-separated repo-local evidence references.",
    )
    parser.add_argument(
        "--architecture-impact",
        default="none",
        choices=ARCHITECTURE_IMPACT_CHOICES,
        help="Architecture impact classification.",
    )
    parser.add_argument(
        "--adr-impact",
        default="none",
        choices=ADR_IMPACT_CHOICES,
        help="ADR impact classification.",
    )
    parser.add_argument(
        "--risk",
        default="low",
        choices=RISK_CHOICES,
        help="Risk classification.",
    )
    parser.add_argument(
        "--files-allowed",
        help="Comma-separated allowed file paths.",
    )
    parser.add_argument(
        "--validation",
        help="Comma-separated validation commands.",
    )
    parser.add_argument(
        "--commit-message",
        help="Suggested commit message for the proposal's task section.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR.relative_to(REPO_ROOT)),
        help="Output directory for draft proposal artifacts.",
    )
    parser.add_argument(
        "--print",
        action="store_true",
        help="Print the generated JSON artifact to stdout.",
    )
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="Do not write the proposal artifact to disk.",
    )
    args = parser.parse_args()
    if not args.title or not args.title.strip():
        parser.error("--title is required")
    return args


def main() -> int:
    args = parse_args()
    proposal = build_proposal(args)
    rendered = json.dumps(proposal, indent=2) + "\n"

    output_dir = (REPO_ROOT / args.output_dir).resolve()
    output_path = output_dir / f"{proposal['proposal_id']}.json"

    if not args.no_write:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")

    if args.print:
        sys.stdout.write(rendered)
    elif not args.no_write:
        relative_output = output_path.relative_to(REPO_ROOT).as_posix()
        sys.stdout.write(f"Wrote {relative_output}\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
