"""Alembic migration smoke tests."""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import pytest

try:
    import psycopg  # type: ignore
except ImportError:  # pragma: no cover
    psycopg = None

from sqlalchemy import create_engine, inspect

from guardian.db.models import Base


def _build_database_url(base_url: str, database_name: str) -> str:
    parsed = urlparse(base_url)
    return urlunparse(parsed._replace(path=f"/{database_name}"))


def _admin_database_url(base_url: str) -> str:
    parsed = urlparse(base_url)
    return urlunparse(parsed._replace(path="/postgres"))


@pytest.mark.integration
def test_migrations_apply_cleanly(tmp_path, monkeypatch):
    if psycopg is None:
        pytest.skip("psycopg not installed")

    base_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not base_url:
        pytest.skip("TEST_DATABASE_URL or DATABASE_URL environment variable required")

    admin_url = _admin_database_url(base_url)
    db_name = f"codexify_migrate_{uuid.uuid4().hex[:12]}"
    temp_url = _build_database_url(base_url, db_name)

    try:
        admin_conn = psycopg.connect(admin_url, autocommit=True)
    except Exception as exc:  # pragma: no cover - environment-specific availability
        pytest.skip(f"Unable to connect to admin database: {exc}")
    try:
        with admin_conn.cursor() as cur:
            cur.execute(f"CREATE DATABASE {db_name}")
    except psycopg.Error as exc:  # pragma: no cover - environment specific
        admin_conn.close()
        pytest.skip(f"Unable to create test database: {exc.pgcode}")
    finally:
        admin_conn.close()

    from alembic.config import Config
    from alembic import command

    cfg_path = tmp_path / "alembic.ini"
    cfg_path.write_text(Path("backend/alembic.ini").read_text())
    cfg = Config(str(cfg_path))
    cfg.set_main_option("sqlalchemy.url", temp_url)
    cfg.set_main_option("script_location", "guardian/db/migrations")
    # Ensure Alembic can find scripts even when ini is copied to tmp
    repo_root = Path(__file__).resolve().parents[1]
    migrations_dir = repo_root / "guardian" / "db" / "migrations"
    cfg.set_main_option("script_location", str(migrations_dir))
    monkeypatch.setenv("DATABASE_URL", temp_url)

    engine = None
    try:
        command.upgrade(cfg, "head")

        engine = create_engine(temp_url)
        inspector = inspect(engine)
        expected_tables = set(Base.metadata.tables.keys()) | {"alembic_version"}
        existing_tables = set(inspector.get_table_names())

        missing = sorted(expected_tables - existing_tables)
        if missing:
            pytest.fail(f"Missing tables after migration: {missing}")

        unexpected = sorted(existing_tables - expected_tables)
        if unexpected:
            pytest.fail(f"Unexpected tables present: {unexpected}")

        print("✅ Alembic/ORM schema contract validated.")
    finally:
        if engine is not None:
            engine.dispose()

        # Use separate autocommit connections for cleanup
        cleanup_conn = psycopg.connect(admin_url, autocommit=True)
        try:
            with cleanup_conn.cursor() as cur:
                cur.execute(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s",
                    (db_name,),
                )
            # Open a one-off autocommit connection for DROP DATABASE
            drop_conn = psycopg.connect(admin_url, autocommit=True)
            try:
                with drop_conn.cursor() as cur:
                    cur.execute(f"DROP DATABASE IF EXISTS {db_name}")
            finally:
                drop_conn.close()
        finally:
            cleanup_conn.close()
