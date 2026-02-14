"""codex_runner README (Python)

This file exists to provide a *discoverable*, executable help page for the
Campaign Runner without requiring packaging/entrypoints.

- Human-friendly docs should live in: codex_runner/README.md
- This module is an executable help page: `python -m codex_runner.README`

It mirrors the flags and behavior of `codex_runner/runner.py`.
"""

from __future__ import annotations

import argparse
import textwrap


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m codex_runner.README",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Codex Runner — Campaign Runner (help)",
        epilog=textwrap.dedent(
            """
            QUICK START

              # 1) Generate campaign + task artifacts (no execution)
              python codex_runner/runner.py \
                --mega-audit-prompt-file docs/prompts/mega_audit.md \
                --campaign-compiler-prompt-file codex_runner/prompts/audit_report_to_campaign_runner.md \
                --dry-run

              # 2) Generate artifacts + execute tasks sequentially
              python codex_runner/runner.py \
                --mega-audit-prompt-file docs/prompts/mega_audit.md \
                --campaign-compiler-prompt-file codex_runner/prompts/audit_report_to_campaign_runner.md \
                --execute

            INVOCATION OPTIONS

              # Run as a script
              python codex_runner/runner.py --help

              # Run as a module
              python -m codex_runner.runner --help

            NOTES

            - The runner uses a branch-per-campaign workflow: `campaign/YYYY-MM-DD/<slug>`.
            - By default it auto-commits generated artifacts and receipt updates.
            - For true parallelism, use separate clones/worktrees (Git will serialize changes
              in a single workdir).
            """
        ),
    )

    parser.add_argument(
        "--show-runner-help",
        action="store_true",
        help="Print the full runner.py CLI help (same as `python codex_runner/runner.py --help`).",
    )

    parser.add_argument(
        "--show-examples",
        action="store_true",
        help="Print additional usage examples.",
    )

    return parser


def _examples() -> str:
    return textwrap.dedent(
        """
        EXAMPLES

          # Run 2 audit cycles and stay on the campaign branch
          python codex_runner/runner.py \
            --mega-audit-prompt-file docs/prompts/mega_audit.md \
            --campaign-compiler-prompt-file codex_runner/prompts/audit_report_to_campaign_runner.md \
            --cycles 2 \
            --no-return-to-base-branch \
            --dry-run

          # Keep git hooks enabled
          python codex_runner/runner.py \
            --mega-audit-prompt-file docs/prompts/mega_audit.md \
            --campaign-compiler-prompt-file codex_runner/prompts/audit_report_to_campaign_runner.md \
            --verify \
            --dry-run

          # Disable auto-commit (runner will error if it dirties the tree)
          python codex_runner/runner.py \
            --mega-audit-prompt-file docs/prompts/mega_audit.md \
            --campaign-compiler-prompt-file codex_runner/prompts/audit_report_to_campaign_runner.md \
            --no-auto-commit \
            --dry-run
        """
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.show_examples:
        print(_examples())
        return 0

    if args.show_runner_help:
        # Import lazily so README.py stays lightweight.
        from codex_runner import runner

        runner_parser = runner.parse_args  # type: ignore[attr-defined]
        # runner.parse_args reads sys.argv; we want the help text, so we just call
        # the runner file via argparse by emulating `--help`.
        try:
            runner.parse_args.__wrapped__  # type: ignore[attr-defined]
        except Exception:
            pass

        # The cleanest: invoke runner as a module argument vector.
        import subprocess
        import sys

        cmd = [sys.executable, "-m", "codex_runner.runner", "--help"]
        subprocess.run(cmd, check=False)
        return 0

    # Default: print this module's help.
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
