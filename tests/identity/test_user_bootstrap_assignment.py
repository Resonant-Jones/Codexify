"""Bootstrap ownership assignment coverage."""

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

from sqlalchemy import create_engine, inspect, text


def _build_database_url(base_url: str, database_name: str) -> str:
    parsed = urlparse(base_url)
    return urlunparse(parsed._replace(path=f"/{database_name}"))


def _admin_database_url(base_url: str) -> str:
    parsed = urlparse(base_url)
    return urlunparse(parsed._replace(path="/postgres"))


def _insert_seed_rows(engine) -> dict[str, object]:
    with engine.begin() as conn:
        project_id = 4101
        thread_id = 4201
        message_id = 4301
        document_id = str(uuid.uuid4())
        memory_id = 4401
        persona_id = 4501

        conn.execute(
            text(
                """
                INSERT INTO projects (id, name, description, icon, created_at, updated_at)
                VALUES (:id, :name, :description, :icon, NOW(), NOW())
                """
            ),
            {
                "id": project_id,
                "name": "Seed Project",
                "description": "pre-bootstrap project",
                "icon": None,
            },
        )
        conn.execute(
            text(
                """
                INSERT INTO chat_threads (id, user_id, title, summary, project_id, created_at, updated_at)
                VALUES (:id, :user_id, :title, :summary, :project_id, NOW(), NOW())
                """
            ),
            {
                "id": thread_id,
                "user_id": "local",
                "title": "Seed Thread",
                "summary": "pre-bootstrap thread",
                "project_id": project_id,
            },
        )
        conn.execute(
            text(
                """
                INSERT INTO chat_messages (id, thread_id, role, content, created_at)
                VALUES (:id, :thread_id, :role, :content, NOW())
                """
            ),
            {
                "id": message_id,
                "thread_id": thread_id,
                "role": "user",
                "content": "seed message",
            },
        )
        conn.execute(
            text(
                """
                INSERT INTO uploaded_documents (
                    id,
                    project_id,
                    thread_id,
                    user_id,
                    filename,
                    filesize,
                    mime_type,
                    src_url,
                    parsed_text,
                    created_at,
                    updated_at
                )
                VALUES (
                    :id,
                    :project_id,
                    :thread_id,
                    NULL,
                    :filename,
                    :filesize,
                    :mime_type,
                    :src_url,
                    :parsed_text,
                    NOW(),
                    NOW()
                )
                """
            ),
            {
                "id": document_id,
                "project_id": project_id,
                "thread_id": thread_id,
                "filename": "seed.md",
                "filesize": 12,
                "mime_type": "text/markdown",
                "src_url": "/tmp/seed.md",
                "parsed_text": "seed document",
            },
        )
        conn.execute(
            text(
                """
                INSERT INTO memory_entries (
                    id, user_id, silo, content, tags, pinned, created_at, updated_at
                )
                VALUES (
                    :id, NULL, :silo, :content, :tags, FALSE, NOW(), NOW()
                )
                """
            ),
            {
                "id": memory_id,
                "silo": "midterm",
                "content": "seed memory",
                "tags": "seed",
            },
        )
        conn.execute(
            text(
                """
                INSERT INTO personas (
                    id, user_id, project_id, body, source, is_active, created_at, updated_at
                )
                VALUES (
                    :id, NULL, :project_id, :body, :source, TRUE, NOW(), NOW()
                )
                """
            ),
            {
                "id": persona_id,
                "project_id": project_id,
                "body": "seed persona",
                "source": "user",
            },
        )
    return {
        "project_id": project_id,
        "thread_id": thread_id,
        "message_id": message_id,
        "document_id": document_id,
        "memory_id": memory_id,
        "persona_id": persona_id,
    }


@pytest.mark.integration
def test_user_bootstrap_assignment(tmp_path, monkeypatch):
    if psycopg is None:
        pytest.skip("psycopg not installed")

    try:
        import alembic.command  # type: ignore
        from alembic.config import Config  # type: ignore
    except Exception as exc:  # pragma: no cover - environment-specific
        pytest.skip(f"Alembic unavailable: {exc}")

    base_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not base_url:
        pytest.skip(
            "TEST_DATABASE_URL or DATABASE_URL environment variable required"
        )

    admin_url = _admin_database_url(base_url)
    db_name = f"codexify_bootstrap_{uuid.uuid4().hex[:12]}"
    temp_url = _build_database_url(base_url, db_name)

    try:
        admin_conn = psycopg.connect(admin_url, autocommit=True)
    except Exception as exc:  # pragma: no cover - environment-specific
        pytest.skip(f"Unable to connect to admin database: {exc}")

    try:
        with admin_conn.cursor() as cur:
            cur.execute(f"CREATE DATABASE {db_name}")
    except psycopg.Error as exc:  # pragma: no cover - environment specific
        admin_conn.close()
        pytest.skip(f"Unable to create test database: {exc.pgcode}")
    finally:
        admin_conn.close()

    repo_root = Path(__file__).resolve().parents[2]
    migrations_dir = repo_root / "guardian" / "db" / "migrations"
    cfg_path = tmp_path / "alembic.ini"
    cfg_path.write_text((repo_root / "backend" / "alembic.ini").read_text())
    cfg = Config(str(cfg_path))
    cfg.set_main_option("sqlalchemy.url", temp_url)
    cfg.set_main_option("script_location", str(migrations_dir))
    monkeypatch.setenv("DATABASE_URL", temp_url)

    engine = None
    try:
        alembic.command.upgrade(cfg, "f2b3c4d5e6f7")
        engine = create_engine(temp_url)
        seed_ids = _insert_seed_rows(engine)

        alembic.command.upgrade(cfg, "head")

        inspector = inspect(engine)
        users = inspector.get_columns("users")
        user_columns = {column["name"]: column for column in users}
        assert "id" in user_columns
        assert "username" in user_columns
        assert "created_at" in user_columns

        with engine.connect() as conn:
            local_user_count = conn.execute(
                text("SELECT COUNT(*) FROM users WHERE id = 'local'")
            ).scalar_one()
            assert local_user_count == 1

            for table in (
                "projects",
                "chat_threads",
                "chat_messages",
                "uploaded_documents",
                "memory_entries",
                "personas",
            ):
                column = next(
                    column
                    for column in inspector.get_columns(table)
                    if column["name"] == "user_id"
                )
                assert column["nullable"] is False, table

                null_count = conn.execute(
                    text(f"SELECT COUNT(*) FROM {table} WHERE user_id IS NULL")
                ).scalar_one()
                assert null_count == 0, table

            assert (
                conn.execute(
                    text("SELECT user_id FROM projects WHERE id = :id"),
                    {"id": 4101},
                ).scalar_one()
                == "local"
            )
            assert (
                conn.execute(
                    text("SELECT user_id FROM chat_messages WHERE id = :id"),
                    {"id": 4301},
                ).scalar_one()
                == "local"
            )
            assert (
                conn.execute(
                    text(
                        "SELECT user_id FROM uploaded_documents WHERE id = :id"
                    ),
                    {"id": seed_ids["document_id"]},
                ).scalar_one_or_none()
                == "local"
            )
            assert (
                conn.execute(
                    text("SELECT user_id FROM memory_entries WHERE id = :id"),
                    {"id": seed_ids["memory_id"]},
                ).scalar_one()
                == "local"
            )
            assert (
                conn.execute(
                    text("SELECT user_id FROM personas WHERE id = :id"),
                    {"id": seed_ids["persona_id"]},
                ).scalar_one()
                == "local"
            )
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
