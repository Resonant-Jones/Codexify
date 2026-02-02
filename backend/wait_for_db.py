#!/usr/bin/env python3
"""Wait for Postgres to become available.

This script is used by local/dev runners and some container entrypoints.
It intentionally degrades gracefully:
- If DATABASE_URL is not set, it exits 0 (skip wait).
- If neither psycopg (psycopg3) nor psycopg2 is installed, it exits 0 (skip wait).

Environment:
- DATABASE_URL: Postgres DSN
- DB_WAIT_SECONDS: total wait time (default 180)
- DB_WAIT_INTERVAL: sleep between attempts (default 2)
"""

from __future__ import annotations

import os
import sys
import time
from typing import Callable, Optional


def _connect_with_psycopg(dsn: str) -> None:
    import psycopg  # type: ignore

    conn = psycopg.connect(dsn)
    conn.close()


def _connect_with_psycopg2(dsn: str) -> None:
    import psycopg2  # type: ignore

    conn = psycopg2.connect(dsn)
    conn.close()


def _get_connector() -> Callable[[str], None] | None:
    """Return a connect() function using whichever driver is available."""
    try:
        import psycopg  # noqa: F401

        return _connect_with_psycopg
    except Exception:
        pass

    try:
        import psycopg2  # noqa: F401

        return _connect_with_psycopg2
    except Exception:
        return None


def main() -> int:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print(
            "[wait_for_db] DATABASE_URL not set; skipping DB wait",
            file=sys.stderr,
        )
        return 0

    connector = _get_connector()
    if connector is None:
        print(
            "[wait_for_db] No psycopg/psycopg2 installed; skipping active DB wait",
            file=sys.stderr,
        )
        return 0

    total_wait = int(os.environ.get("DB_WAIT_SECONDS", "180"))
    interval = float(os.environ.get("DB_WAIT_INTERVAL", "2"))
    attempts = max(1, int(total_wait // interval))

    last_err: BaseException | None = None
    for i in range(attempts):
        try:
            connector(dsn)
            print("[wait_for_db] Postgres is up")
            return 0
        except Exception as e:  # noqa: BLE001
            last_err = e
            print(
                f"[wait_for_db] Waiting for Postgres... attempt {i + 1}/{attempts}: {e}",
                file=sys.stderr,
            )
            time.sleep(interval)

    print(
        f"[wait_for_db] Postgres did not become available after ~{total_wait}s: {last_err}",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
