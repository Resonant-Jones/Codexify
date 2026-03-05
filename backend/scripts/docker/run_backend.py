from __future__ import annotations

import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import (
    ensure_symlink,
    execv,
    log,
    run,
    wait_for_postgres,
    wait_for_tcp,
)
from sqlalchemy import create_engine, text

REQUIRED_TABLES = [
    "public.alembic_version",
    "public.projects",
    "public.chat_threads",
    "public.chat_messages",
    "public.imprints",
    "public.system_docs",
    "public.system_doc_links",
    "public.events_outbox",
]


def resolve_database_dsn() -> str | None:
    return (
        os.environ.get("DATABASE_URL")
        or os.environ.get("GUARDIAN_DATABASE_URL")
        or os.environ.get("GUARDIAN_DB_DSN")
    )


def wait_for_db() -> str:
    dsn = resolve_database_dsn()
    if dsn:
        log("Backend", "Waiting for Postgres via DSN")
        wait_for_postgres(dsn, timeout_s=120)
        return dsn

    log(
        "Backend",
        "No DATABASE_URL/GUARDIAN_DATABASE_URL provided; falling back to TCP wait db:5432",
    )
    wait_for_tcp("db", 5432, timeout_s=120, sleep_s=1.0)
    raise SystemExit(
        "[Backend] DATABASE_URL or GUARDIAN_DATABASE_URL is required for schema probes"
    )


def verify_schema(dsn: str) -> None:
    log("Backend", "Verifying required tables + alembic_version")
    engine = create_engine(dsn)

    with engine.begin() as conn:
        missing: list[str] = []
        for table in REQUIRED_TABLES:
            regclass = conn.execute(
                text("SELECT to_regclass(:name)"), {"name": table}
            ).scalar()
            if regclass is None:
                missing.append(table)

        if missing:
            tables = conn.execute(
                text(
                    """
                    SELECT table_schema || '.' || table_name
                    FROM information_schema.tables
                    WHERE table_type = 'BASE TABLE'
                    ORDER BY 1
                    """
                )
            ).fetchall()
            table_list = (
                "\n  - ".join([row[0] for row in tables])
                if tables
                else "<none>"
            )
            raise SystemExit(
                "[Backend] ERROR: schema missing required tables:\n  - "
                + "\n  - ".join(missing)
                + "\n\n[Backend] Existing tables:\n  - "
                + table_list
            )

        version_num = conn.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar()

    log("Backend", f"OK: alembic_version={version_num}")


def main() -> int:
    try:
        ensure_symlink("/app/codexify", "/app/Codexify")
    except Exception as exc:  # noqa: BLE001
        log("Backend", f"WARN: unable to ensure /app/Codexify symlink: {exc}")

    dsn = wait_for_db()
    verify_schema(dsn)

    log("Backend", "Running seed defaults")
    run([sys.executable, "/app/backend/scripts/seed_defaults.py"])

    port = os.environ.get("PORT", "8888")
    execv(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "guardian.guardian_api:app",
            "--host",
            "0.0.0.0",
            "--port",
            str(port),
        ]
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
