"""Module entrypoint for deterministic Campaign Runner v2."""

from __future__ import annotations

from . import runner


def main(argv: list[str] | None = None) -> int:
    return int(runner.main(argv))


if __name__ == "__main__":
    raise SystemExit(main())
