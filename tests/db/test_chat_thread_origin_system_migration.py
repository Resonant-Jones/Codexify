"""PostgreSQL regression proof for the conversation-origin migration."""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

try:
    import psycopg  # type: ignore
except ImportError:  # pragma: no cover
    psycopg = None


BASELINE_REVISION = "9d4c2a7e1b6f"
TARGET_REVISION = "1c0a2b3c4d5e"
EXPECTED_ORIGINS = {
    "chatgpt": "openai",
    "openai": "openai",
    "claude": "anthropic",
    "anthropic": "anthropic",
    "native": "codexify",
    "unrelated": "codexify",
}


def _build_database_url(base_url: str, database_name: str) -> str:
    parsed = urlparse(base_url)
    return urlunparse(parsed._replace(path=f"/{database_name}"))


def _admin_database_url(base_url: str) -> str:
    parsed = urlparse(base_url)
    return urlunparse(parsed._replace(path="/postgres"))


def _psycopg_connection_url(database_url: str) -> str:
    """Convert an explicit SQLAlchemy driver URL to a psycopg URI."""

    parsed = urlparse(database_url)
    if parsed.scheme.startswith("postgresql+"):
        return urlunparse(parsed._replace(scheme="postgresql"))
    return database_url


@pytest.mark.integration
def test_chat_thread_origin_system_migration_uses_psycopg3_expanding_binds(
    tmp_path, monkeypatch
):
    """Upgrade actual legacy rows through the target revision on PostgreSQL."""

    if psycopg is None:
        pytest.skip("psycopg not installed")
    assert psycopg.__version__.split(".")[0] == "3"

    base_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not base_url:
        pytest.skip("TEST_DATABASE_URL or DATABASE_URL environment variable required")

    try:
        from alembic import command
        from alembic.config import Config
    except ImportError:  # pragma: no cover - environment-specific
        pytest.skip("Alembic not installed")

    db_name = f"codexify_origin_system_{uuid.uuid4().hex[:12]}"
    temp_url = _build_database_url(base_url, db_name)
    admin_url = _psycopg_connection_url(_admin_database_url(base_url))

    try:
        admin_conn = psycopg.connect(admin_url, autocommit=True)
    except psycopg.Error as exc:  # pragma: no cover - environment-specific
        pytest.skip(f"Unable to connect to admin database: {exc}")
    try:
        with admin_conn.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE {db_name}")
    except psycopg.Error as exc:  # pragma: no cover - environment-specific
        admin_conn.close()
        pytest.skip(f"Unable to create test database: {exc.pgcode}")
    finally:
        admin_conn.close()

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
    expected_metadata = {
        "chatgpt": {"import_source": "chatgpt", "source_thread_id": "chatgpt-1"},
        "openai": {"import_source": "openai", "source_thread_id": "openai-1"},
        "claude": {"import_source": "claude", "source_thread_id": "claude-1"},
        "anthropic": {
            "import_source": "anthropic",
            "source_thread_id": "anthropic-1",
        },
        "native": {"source_thread_id": "native-1"},
        "unrelated": {
            "import_source": "unrelated",
            "source_thread_id": "unrelated-1",
        },
    }
    try:
        command.upgrade(cfg, BASELINE_REVISION)
        engine = create_engine(temp_url, future=True)
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO users (id, username, password_hash)
                    VALUES (
                        'origin-system-migration-proof',
                        'origin-system-migration-proof',
                        'not-a-real-password'
                    )
                    """
                )
            )
            for title, metadata in expected_metadata.items():
                connection.execute(
                    text(
                        """
                        INSERT INTO chat_threads (user_id, title, summary, metadata)
                        VALUES (:user_id, :title, '', CAST(:metadata AS jsonb))
                        """
                    ),
                    {
                        "user_id": "origin-system-migration-proof",
                        "title": title,
                        "metadata": json.dumps(metadata),
                    },
                )

        command.upgrade(cfg, TARGET_REVISION)
        inspector = inspect(engine)

        origin_column = next(
            column
            for column in inspector.get_columns("chat_threads")
            if column["name"] == "origin_system"
        )
        assert origin_column["nullable"] is False
        assert getattr(origin_column["type"], "length", None) == 32
        assert "codexify" in str(origin_column["default"])

        checks = {
            check["name"]: check["sqltext"]
            for check in inspector.get_check_constraints("chat_threads")
        }
        canonical_check = checks["ck_chat_threads_origin_system_canonical"]
        assert all(origin in canonical_check for origin in EXPECTED_ORIGINS.values())

        user_origin_index = next(
            index
            for index in inspector.get_indexes("chat_threads")
            if index["name"] == "ix_chat_threads_user_origin"
        )
        assert user_origin_index["column_names"] == ["user_id", "origin_system"]

        with engine.begin() as connection:
            actual_rows = {
                row["title"]: {
                    "origin_system": row["origin_system"],
                    "metadata": json.loads(row["metadata_json"]),
                }
                for row in connection.execute(
                    text(
                        """
                        SELECT title, origin_system, metadata::text AS metadata_json
                        FROM chat_threads
                        ORDER BY title
                        """
                    )
                ).mappings()
            }
            default_origin = connection.scalar(
                text(
                    """
                    INSERT INTO chat_threads (user_id, title, summary, metadata)
                    VALUES (
                        'origin-system-migration-proof',
                        'post-upgrade-default',
                        '',
                        '{}'::jsonb
                    )
                    RETURNING origin_system
                    """
                )
            )
            assert (
                connection.scalar(text("SELECT version_num FROM alembic_version"))
                == TARGET_REVISION
            )

        assert default_origin == "codexify"
        assert actual_rows == {
            title: {
                "origin_system": EXPECTED_ORIGINS[title],
                "metadata": metadata,
            }
            for title, metadata in expected_metadata.items()
        }

        with pytest.raises(IntegrityError), engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO chat_threads
                        (user_id, title, summary, metadata, origin_system)
                    VALUES
                        ('origin-system-migration-proof', 'invalid-origin', '',
                         '{}'::jsonb, 'unsupported')
                    """
                )
            )
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
