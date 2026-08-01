from __future__ import annotations

import sys
from pathlib import Path

import daily_audit


def main() -> int:
    daily_audit.AUDIT_SCRIPT = Path(__file__).resolve().with_name(
        "audit_platform_readiness_v2.py"
    )
    return daily_audit.main()


if __name__ == "__main__":
    sys.exit(main())
