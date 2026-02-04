"""Command-line entrypoint for the Codex Runner tool."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):
    # Allow running the module directly from the source tree.
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from codex_runner import runner


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser for Codex Runner."""
    parser = argparse.ArgumentParser(description="Codex Runner")
    parser.add_argument(
        "--repo-root",
        type=Path,
        required=True,
        help="Path to the target repository root.",
    )
    parser.add_argument(
        "--audit-prompt-file",
        type=Path,
        required=True,
        help="Path to the audit prompt file.",
    )
    parser.add_argument(
        "--cycles",
        type=int,
        default=1,
        help="Number of audit cycles to run.",
    )
    parser.add_argument(
        "--branch-per-campaign",
        action="store_true",
        default=True,
        help=(
            "Required. Create/switch to a branch per campaign using "
            "campaign_slug (default behavior)."
        ),
    )
    verify_group = parser.add_mutually_exclusive_group()
    verify_group.add_argument(
        "--no-verify",
        dest="no_verify",
        action="store_true",
        default=True,
        help="Skip git hooks for runner commits (default).",
    )
    verify_group.add_argument(
        "--verify",
        dest="no_verify",
        action="store_false",
        help="Run git hooks for runner commits.",
    )
    auto_commit_group = parser.add_mutually_exclusive_group()
    auto_commit_group.add_argument(
        "--auto-commit",
        dest="auto_commit",
        action="store_true",
        default=True,
        help="Auto-commit runner-generated changes (default).",
    )
    auto_commit_group.add_argument(
        "--no-auto-commit",
        dest="auto_commit",
        action="store_false",
        help="Disable auto-commit for runner-generated changes.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute tasks sequentially after generating artifacts.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate artifacts but skip task execution.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging for runner commands.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run Codex Runner from the command line."""
    args = build_parser().parse_args(argv)
    repo_root = args.repo_root.expanduser().resolve()
    audit_prompt_file = args.audit_prompt_file.expanduser().resolve()

    config = runner.RunnerConfig(
        repo_root=repo_root,
        audit_prompt_file=audit_prompt_file,
        cycles=args.cycles,
        execute=args.execute,
        dry_run=args.dry_run,
        branch_per_campaign=args.branch_per_campaign,
        no_verify=args.no_verify,
        auto_commit=args.auto_commit,
        debug=args.debug,
    )

    try:
        return runner.run(config)
    except runner.RunnerError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
