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
from sqlalchemy.engine import make_url


def _build_database_url(base_url: str, database_name: str) -> str:
    parsed = urlparse(base_url)
    return urlunparse(parsed._replace(path=f"/{database_name}"))


def _admin_database_url(base_url: str) -> str:
    parsed = make_url(base_url)
    return parsed.set(
        drivername="postgresql", database="postgres"
    ).render_as_string(hide_password=False)


@pytest.mark.integration
def test_tool_jobs_cleanup_migration_round_trip(tmp_path, monkeypatch):
    if psycopg is None:
        pytest.skip("psycopg not installed")

    base_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not base_url:
        pytest.skip(
            "TEST_DATABASE_URL or DATABASE_URL environment variable required"
        )

    admin_url = _admin_database_url(base_url)
    db_name = f"codexify_tool_jobs_cleanup_{uuid.uuid4().hex[:12]}"
    temp_url = _build_database_url(base_url, db_name)

    try:
        admin_conn = psycopg.connect(admin_url, autocommit=True)
    except Exception as exc:  # pragma: no cover - env specific
        pytest.skip(f"Unable to connect to admin database: {exc}")
    try:
        with admin_conn.cursor() as cur:
            cur.execute(f"CREATE DATABASE {db_name}")
    except psycopg.Error as exc:  # pragma: no cover - environment specific
        admin_conn.close()
        pytest.skip(f"Unable to create test database: {exc.pgcode}")
    finally:
        admin_conn.close()

    from alembic import command
    from alembic.config import Config

    cfg_path = tmp_path / "alembic.ini"
    cfg_path.write_text(Path("backend/alembic.ini").read_text())
    cfg = Config(str(cfg_path))
    cfg.set_main_option("sqlalchemy.url", temp_url)
    repo_root = Path(__file__).resolve().parents[2]
    migrations_dir = repo_root / "backend" / "migrations"
    cfg.set_main_option("script_location", str(migrations_dir))
    monkeypatch.setenv("DATABASE_URL", temp_url)

    engine = None
    try:
        command.upgrade(cfg, "b3c4d5e6f7a8")

        engine = create_engine(temp_url)
        inspector = inspect(engine)

        tables_before_cleanup = set(inspector.get_table_names())
        assert "tool_jobs" in tables_before_cleanup
        assert "command_runs" in tables_before_cleanup
        assert "command_run_events" in tables_before_cleanup

        tool_job_columns = {
            column["name"] for column in inspector.get_columns("tool_jobs")
        }
        assert {
            "id",
            "tool_name",
            "status",
            "request_json",
            "result_json",
            "error",
            "error_json",
            "created_at",
            "updated_at",
        } <= tool_job_columns

        tool_job_indexes = {
            index["name"] for index in inspector.get_indexes("tool_jobs")
        }
        assert {
            "ix_tool_jobs_created_at",
            "ix_tool_jobs_status",
        } <= tool_job_indexes

        tool_job_constraints = {
            constraint["name"]
            for constraint in inspector.get_check_constraints("tool_jobs")
        }
        assert "tool_jobs_status_check" in tool_job_constraints

        command.upgrade(cfg, "head")

        inspector = inspect(engine)
        tables_after_cleanup = set(inspector.get_table_names())
        assert "tool_jobs" not in tables_after_cleanup
        assert "command_runs" in tables_after_cleanup
        assert "command_run_events" in tables_after_cleanup

        command.downgrade(cfg, "b3c4d5e6f7a8")

        inspector = inspect(engine)
        tables_after_downgrade = set(inspector.get_table_names())
        assert "tool_jobs" in tables_after_downgrade
        assert "command_runs" in tables_after_downgrade
        assert "command_run_events" in tables_after_downgrade

        restored_columns = {
            column["name"] for column in inspector.get_columns("tool_jobs")
        }
        assert tool_job_columns == restored_columns

        restored_indexes = {
            index["name"] for index in inspector.get_indexes("tool_jobs")
        }
        assert tool_job_indexes == restored_indexes

        restored_constraints = {
            constraint["name"]
            for constraint in inspector.get_check_constraints("tool_jobs")
        }
        assert tool_job_constraints == restored_constraints
    finally:
        if engine is not None:
            engine.dispose()

        cleanup_conn = psycopg.connect(admin_url, autocommit=True)
        try:
            with cleanup_conn.cursor() as cur:
                cur.execute(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s",
                    (db_name,),
                )
            drop_conn = psycopg.connect(admin_url, autocommit=True)
            try:
                with drop_conn.cursor() as cur:
                    cur.execute(f"DROP DATABASE IF EXISTS {db_name}")
            finally:
                drop_conn.close()
        finally:
            cleanup_conn.close()
