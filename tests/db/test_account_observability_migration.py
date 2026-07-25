"""Postgres migration round-trip tests for account observability foundation."""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import pytest
from sqlalchemy import create_engine, inspect, text

try:
    import psycopg  # type: ignore
except ImportError:  # pragma: no cover
    psycopg = None


BASELINE_REVISION = "a1c2d3e4f5b6"
FOUNDATION_TABLES = {
    "account_observability_invite_links",
    "account_observability_guest_identities",
    "account_observability_account_metadata",
    "account_observability_presence_sessions",
}
PROHIBITED_COLUMN_NAMES = {
    "raw_ip",
    "hashed_ip",
    "ip_address",
    "user_agent",
    "fingerprint",
    "page_path",
    "route_path",
    "message_id",
    "thread_id",
    "project_id",
    "prompt",
    "response_content",
    "referrer_url",
    "latitude",
    "longitude",
    "postal_code",
    "city",
    "asn",
    "isp",
}


def _build_database_url(base_url: str, database_name: str) -> str:
    parsed = urlparse(base_url)
    return urlunparse(parsed._replace(path=f"/{database_name}"))


def _admin_database_url(base_url: str) -> str:
    parsed = urlparse(base_url)
    return urlunparse(parsed._replace(path="/postgres"))


@pytest.mark.integration
def test_account_observability_migration_round_trip(tmp_path, monkeypatch):
    if psycopg is None:
        pytest.skip("psycopg not installed")

    base_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not base_url:
        pytest.skip(
            "TEST_DATABASE_URL or DATABASE_URL environment variable required"
        )

    admin_url = _admin_database_url(base_url)
    db_name = f"codexify_account_observability_{uuid.uuid4().hex[:12]}"
    temp_url = _build_database_url(base_url, db_name)

    try:
        admin_conn = psycopg.connect(admin_url, autocommit=True)
    except Exception as exc:  # pragma: no cover - environment-specific
        pytest.skip(f"Unable to connect to admin database: {exc}")
    try:
        with admin_conn.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE {db_name}")
    except psycopg.Error as exc:  # pragma: no cover - environment-specific
        admin_conn.close()
        pytest.skip(f"Unable to create test database: {exc.pgcode}")
    finally:
        admin_conn.close()

    from alembic import command
    from alembic.config import Config

    repo_root = Path(__file__).resolve().parents[2]
    cfg_path = tmp_path / "alembic.ini"
    cfg_path.write_text((repo_root / "backend" / "alembic.ini").read_text())
    cfg = Config(str(cfg_path))
    cfg.set_main_option("sqlalchemy.url", temp_url)
    cfg.set_main_option(
        "script_location", str(repo_root / "guardian" / "db" / "migrations")
    )
    monkeypatch.setenv("DATABASE_URL", temp_url)

    engine = None
    try:
        command.upgrade(cfg, BASELINE_REVISION)
        engine = create_engine(temp_url, future=True)
        baseline_tables = set(inspect(engine).get_table_names())
        assert not FOUNDATION_TABLES & baseline_tables

        command.upgrade(cfg, "head")
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        assert FOUNDATION_TABLES <= tables

        with engine.begin() as connection:
            assert connection.scalar(
                text("SELECT COUNT(*) FROM account_observability_account_metadata")
            ) == 0

        expected_indexes = {
            "uq_account_observability_invite_links_token_hash",
            "ix_account_observability_invite_links_status_created_at",
            "ix_account_observability_guest_identities_first_invite",
            "ix_account_observability_account_metadata_acquisition_invite",
            "ix_account_observability_presence_sessions_user_last_seen",
            "ix_account_observability_presence_sessions_guest_last_seen",
            "ix_account_observability_presence_sessions_invite_started",
            "ix_account_observability_presence_sessions_started_geo",
        }
        actual_indexes = {
            index["name"]
            for table_name in FOUNDATION_TABLES
            for index in inspector.get_indexes(table_name)
        }
        assert expected_indexes <= actual_indexes

        expected_checks = {
            "ck_account_observability_invite_links_status",
            "ck_account_observability_invite_links_lifecycle_timestamps",
            "ck_account_observability_account_metadata_attribution",
            "ck_account_observability_presence_sessions_exactly_one_subject",
            "ck_ao_presence_sessions_last_seen_after_start",
            "ck_ao_presence_sessions_end_after_start",
            "ck_ao_presence_sessions_region_requires_country",
            "ck_ao_presence_sessions_country_code_length",
        }
        actual_checks = {
            check["name"]
            for table_name in FOUNDATION_TABLES
            for check in inspector.get_check_constraints(table_name)
        }
        assert expected_checks <= actual_checks

        for table_name in FOUNDATION_TABLES:
            columns = {
                column["name"] for column in inspector.get_columns(table_name)
            }
            assert not PROHIBITED_COLUMN_NAMES & columns, table_name

        command.downgrade(cfg, BASELINE_REVISION)
        downgraded_tables = set(inspect(engine).get_table_names())
        assert downgraded_tables == baseline_tables
        assert {"users", "chat_threads", "chat_messages"} <= downgraded_tables

        command.upgrade(cfg, "head")
        assert FOUNDATION_TABLES <= set(inspect(engine).get_table_names())
    finally:
        if engine is not None:
            engine.dispose()

        cleanup_conn = psycopg.connect(admin_url, autocommit=True)
        try:
            with cleanup_conn.cursor() as cursor:
                cursor.execute(
                    "SELECT pg_terminate_backend(pid) "
                    "FROM pg_stat_activity WHERE datname = %s",
                    (db_name,),
                )
            drop_conn = psycopg.connect(admin_url, autocommit=True)
            try:
                with drop_conn.cursor() as cursor:
                    cursor.execute(f"DROP DATABASE IF EXISTS {db_name}")
            finally:
                drop_conn.close()
        finally:
            cleanup_conn.close()
