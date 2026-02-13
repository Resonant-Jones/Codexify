"""Module entrypoint for Codex Runner.

Enables:

  python -m codex_runner --help

This delegates execution to `codex_runner.runner`.
"""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    """Run the campaign runner.

    Args:
        argv: Optional argv override (mainly for tests). If omitted, the
            underlying runner will read from `sys.argv`.
    """
    from . import runner

    if argv is not None:
        # Temporarily override sys.argv so runner.parse_args() sees our argv.
        old_argv = sys.argv
        sys.argv = [old_argv[0], *argv]
        try:
            return int(runner.main())
        finally:
            sys.argv = old_argv

    return int(runner.main())


if __name__ == "__main__":
    raise SystemExit(main())
