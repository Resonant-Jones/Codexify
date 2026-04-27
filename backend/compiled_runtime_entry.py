from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path


def _run_backend() -> None:
    from backend.compiled_backend_entry import main as backend_main

    backend_main()


def _resolve_database_dsn() -> str | None:
    return (
        os.environ.get("DATABASE_URL")
        or os.environ.get("GUARDIAN_DATABASE_URL")
        or os.environ.get("GUARDIAN_DB_DSN")
    )


def _wait_for_db() -> str:
    dsn = _resolve_database_dsn()
    if not dsn:
        raise SystemExit(
            "[runtime] DATABASE_URL, GUARDIAN_DATABASE_URL, or GUARDIAN_DB_DSN is required"
        )

    try:
        import psycopg  # type: ignore[import]

        connect = psycopg.connect
    except Exception:
        import psycopg2  # type: ignore[import]

        connect = psycopg2.connect

    deadline = float(os.getenv("MIGRATOR_DB_TIMEOUT_SECONDS", "120"))
    delay = 1.0
    start = time.monotonic()
    while True:
        try:
            conn = connect(dsn)
            conn.close()
            return dsn
        except Exception as exc:
            if time.monotonic() - start >= deadline:
                raise SystemExit(f"[runtime] database unavailable: {exc}") from exc
            time.sleep(delay)


def _run_migrator() -> None:
    from alembic import command
    from alembic.config import Config

    cfg_path = Path(os.getenv("ALEMBIC_CONFIG", "/app/runtime/alembic.ini"))
    if not cfg_path.is_file():
        raise SystemExit(f"[runtime] missing Alembic config: {cfg_path}")

    _wait_for_db()
    command.upgrade(Config(str(cfg_path)), "heads")

    from backend.scripts.seed_defaults import main as seed_defaults_main

    rc = seed_defaults_main()
    if rc:
        raise SystemExit(rc)


def _run_model_prep() -> None:
    from guardian.scripts.ensure_embed_model import main as ensure_embed_model_main

    raise SystemExit(ensure_embed_model_main())


def _configure_worker_logging() -> None:
    import logging

    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))


def _run_worker(module: str) -> None:
    _configure_worker_logging()
    if module == "guardian.workers.chat_worker":
        from guardian.workers.chat_worker import run_forever
    elif module == "guardian.workers.document_embed_worker":
        from guardian.workers.document_embed_worker import run_forever
    elif module == "guardian.workers.chat_embedding_worker":
        from guardian.workers.chat_embedding_worker import run_forever
    elif module == "guardian.workers.warmup_worker":
        from guardian.workers.warmup_worker import run_forever
    else:
        raise SystemExit(f"[runtime] unknown worker module: {module}")
    run_forever()


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    role = (args[0] if args else "backend").strip().lower()

    if role in {"-h", "--help", "help"}:
        print(
            "Usage: codexify-runtime [backend|migrator|model-prep|worker-chat|worker-document-embed|worker-chat-embed|worker-warmup]",
            file=sys.stderr,
        )
        raise SystemExit(0)

    if role == "backend":
        _run_backend()
        return
    if role == "migrator":
        _run_migrator()
        return
    if role == "model-prep":
        _run_model_prep()
        return
    if role == "worker-chat":
        _run_worker("guardian.workers.chat_worker")
        return
    if role == "worker-document-embed":
        _run_worker("guardian.workers.document_embed_worker")
        return
    if role == "worker-chat-embed":
        _run_worker("guardian.workers.chat_embedding_worker")
        return
    if role == "worker-warmup":
        _run_worker("guardian.workers.warmup_worker")
        return

    raise SystemExit(f"[runtime] unknown role: {role}")


if __name__ == "__main__":
    main()
