#!/usr/bin/env python3
"""Verify the isolated Codexify Peekaboo demo account."""

from seed_demo_workspace import main


if __name__ == "__main__":
    import sys

    sys.argv = [sys.argv[0], "verify"]
    raise SystemExit(main())
