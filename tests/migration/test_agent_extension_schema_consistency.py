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

import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect

MERGE_HEAD_REVISION = "b3c4d5e6f7a8"


def _build_database_url(base_url: str, database_name: str) -> str:
    parsed = urlparse(base_url)
    return urlunparse(parsed._replace(path=f"/{database_name}"))


def _admin_database_url(base_url: str) -> str:
    parsed = urlparse(base_url)
    return urlunparse(parsed._replace(path="/postgres"))


@pytest.mark.integration
def test_agent_extension_schema_chain_merges_and_tables_exist(
    tmp_path, monkeypatch
):
    if psycopg is None:
        pytest.skip("psycopg not installed")

    base_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not base_url:
        pytest.skip(
            "TEST_DATABASE_URL or DATABASE_URL environment variable required"
        )

    admin_url = _admin_database_url(base_url)
    db_name = f"codexify_extension_schema_{uuid.uuid4().hex[:12]}"
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
        script = ScriptDirectory.from_config(cfg)
        assert set(script.get_heads()) == {MERGE_HEAD_REVISION}

        command.upgrade(cfg, "heads")

        engine = create_engine(temp_url)
        inspector = inspect(engine)
        existing_tables = set(inspector.get_table_names())

        expected_tables = {
            "agent_extension_proposals",
            "agent_extension_install_gate_decisions",
            "agent_extension_registry_entries",
            "agent_extension_install_bindings",
            "eval_trace_snapshots",
            "eval_verdicts",
        }
        assert expected_tables <= existing_tables

        with engine.connect() as connection:
            version_rows = connection.execute(
                sa.text("SELECT version_num FROM alembic_version")
            ).scalars()
            assert list(version_rows) == [MERGE_HEAD_REVISION]
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
