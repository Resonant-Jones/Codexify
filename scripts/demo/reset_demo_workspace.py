#!/usr/bin/env python3
"""Reset only the dedicated Codexify Peekaboo demo account."""

from seed_demo_workspace import main


if __name__ == "__main__":
    import sys

    sys.argv = [sys.argv[0], "reset"]
    raise SystemExit(main())
