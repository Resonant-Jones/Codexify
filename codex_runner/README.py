"""Executable help page for deterministic Campaign Runner v2."""

from __future__ import annotations

import argparse
import textwrap


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m codex_runner.README",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Deterministic Campaign Runner v2",
        epilog=textwrap.dedent(
            """
            Canonical runtime:
              /Users/resonant_jones/Keep/Resonant_Constructs/Codexify/codex_runner

            Deterministic IDs:
              run_id   = sha256(canonical(run_inputs.json))[:12]
              audit_id = AUDIT_<run_id>

            Mapping block markers:
              <!-- RUNNER_TASK_MAP -->
              <!-- /RUNNER_TASK_MAP -->

            CI verify policy:
              local/dev default: --no-verify
              CI=true default:   --verify

            Commit policy:
              --no-auto-commit intentionally hard-fails in deterministic mode.
            """
        ),
    )
    parser.add_argument("--show-examples", action="store_true")
    return parser


def examples() -> str:
    return textwrap.dedent(
        """
        Example: dry-run deterministic pass

          python /Users/resonant_jones/Keep/Resonant_Constructs/Codexify/codex_runner/runner.py \
            --repo-root /Users/resonant_jones/Keep/Resonant_Constructs/Codexify \
            --audit-prompt-file /Users/resonant_jones/Keep/Resonant_Constructs/Codexify/codex_runner/prompts/mega_audit.md \
            --audit-schema-file /Users/resonant_jones/Keep/Resonant_Constructs/Codexify/codex_runner/schemas/mega_audit_output.schema.json \
            --compiler-prompt-file /Users/resonant_jones/Keep/Resonant_Constructs/Codexify/codex_runner/prompts/audit_report_to_campaign_runner.md \
            --campaign-set-schema-file /Users/resonant_jones/Keep/Resonant_Constructs/Codexify/codex_runner/schemas/campaign_set.schema.json \
            --dry-run

        Example: execute with explicit base ref

          python /Users/resonant_jones/Keep/Resonant_Constructs/Codexify/codex_runner/runner.py \
            --repo-root /Users/resonant_jones/Keep/Resonant_Constructs/Codexify \
            --audit-prompt-file /Users/resonant_jones/Keep/Resonant_Constructs/Codexify/codex_runner/prompts/mega_audit.md \
            --audit-schema-file /Users/resonant_jones/Keep/Resonant_Constructs/Codexify/codex_runner/schemas/mega_audit_output.schema.json \
            --compiler-prompt-file /Users/resonant_jones/Keep/Resonant_Constructs/Codexify/codex_runner/prompts/audit_report_to_campaign_runner.md \
            --campaign-set-schema-file /Users/resonant_jones/Keep/Resonant_Constructs/Codexify/codex_runner/schemas/campaign_set.schema.json \
            --base-ref HEAD \
            --execute
        """
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.show_examples:
        print(examples())
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
