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
from sqlalchemy.orm import sessionmaker

from guardian.db.models import AgentExtensionProposal


def _build_database_url(base_url: str, database_name: str) -> str:
    parsed = urlparse(base_url)
    return urlunparse(parsed._replace(path=f"/{database_name}"))


def _admin_database_url(base_url: str) -> str:
    parsed = urlparse(base_url)
    return urlunparse(parsed._replace(path="/postgres"))


@pytest.mark.integration
def test_agent_extension_proposals_migration_round_trip(tmp_path, monkeypatch):
    if psycopg is None:
        pytest.skip("psycopg not installed")

    base_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not base_url:
        pytest.skip(
            "TEST_DATABASE_URL or DATABASE_URL environment variable required"
        )

    admin_url = _admin_database_url(base_url)
    db_name = f"codexify_extension_{uuid.uuid4().hex[:12]}"
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
    cfg.set_main_option("script_location", "backend/migrations")
    repo_root = Path(__file__).resolve().parents[2]
    migrations_dir = repo_root / "backend" / "migrations"
    cfg.set_main_option("script_location", str(migrations_dir))
    monkeypatch.setenv("DATABASE_URL", temp_url)

    engine = None
    try:
        command.upgrade(cfg, "head")

        engine = create_engine(temp_url)
        inspector = inspect(engine)

        assert "agent_extension_proposals" in inspector.get_table_names()
        columns = {
            column["name"]
            for column in inspector.get_columns("agent_extension_proposals")
        }
        assert {
            "proposal_id",
            "account_id",
            "project_id",
            "profile_id",
            "source_thread_id",
            "source_message_id",
            "target_surface_token",
            "scope_token",
            "status_token",
            "requested_permissions_json",
            "declared_dependencies_json",
            "rollback_metadata_json",
            "test_evidence_json",
            "manifest_json",
            "created_at",
            "updated_at",
        } <= columns

        index_names = {
            index["name"]
            for index in inspector.get_indexes("agent_extension_proposals")
        }
        assert {
            "ix_agent_extension_proposals_account_created_at",
            "ix_agent_extension_proposals_project_created_at",
            "ix_agent_extension_proposals_profile_created_at",
            "ix_agent_extension_proposals_status_created_at",
        } <= index_names

        Session = sessionmaker(bind=engine, future=True)
        with Session() as session:
            row = AgentExtensionProposal(
                proposal_id="proposal-1",
                account_id="user-123",
                project_id=17,
                profile_id="profile-alpha",
                source_thread_id=21,
                source_message_id=22,
                target_surface_token="command_bus",
                scope_token="project_scoped",
                status_token="draft",
                requested_permissions_json=[
                    {
                        "permission": "command.run",
                        "resource": "command_bus",
                        "reason": "bounded command execution",
                        "metadata": {},
                    }
                ],
                declared_dependencies_json=[
                    {
                        "name": "httpx",
                        "version_spec": ">=0.28",
                        "source": "pypi",
                        "required": True,
                        "metadata": {},
                    }
                ],
                rollback_metadata_json={
                    "strategy": "disable_and_revert",
                    "rollback_ref": "ticket-123",
                    "can_rollback": True,
                    "metadata": {},
                },
                test_evidence_json={
                    "status": "passing",
                    "summary": "migration smoke test",
                    "artifacts": [
                        "tests/migration/test_agent_extension_proposals_migration.py",
                    ],
                    "metadata": {},
                },
                manifest_json={
                    "manifest_version": "extension-proposal-manifest.v1",
                    "target_surface": "command_bus",
                    "scope": "project_scoped",
                    "source_thread_id": 21,
                    "source_message_id": 22,
                    "project_id": 17,
                    "profile_id": "profile-alpha",
                    "requested_permissions": [
                        {
                            "permission": "command.run",
                            "resource": "command_bus",
                            "reason": "bounded command execution",
                            "metadata": {},
                        }
                    ],
                    "declared_dependencies": [
                        {
                            "name": "httpx",
                            "version_spec": ">=0.28",
                            "source": "pypi",
                            "required": True,
                            "metadata": {},
                        }
                    ],
                    "rollback_metadata": {
                        "strategy": "disable_and_revert",
                        "rollback_ref": "ticket-123",
                        "can_rollback": True,
                        "metadata": {},
                    },
                    "test_evidence_metadata": {
                        "status": "passing",
                        "summary": "migration smoke test",
                        "artifacts": [
                            "tests/migration/test_agent_extension_proposals_migration.py",
                        ],
                        "metadata": {},
                    },
                },
            )
            session.add(row)
            session.commit()
            session.refresh(row)

        with Session() as session:
            row = (
                session.query(AgentExtensionProposal)
                .filter_by(proposal_id="proposal-1")
                .one()
            )
            assert row.account_id == "user-123"
            assert row.project_id == 17
            assert row.profile_id == "profile-alpha"
            assert row.source_thread_id == 21
            assert row.source_message_id == 22
            assert row.target_surface_token == "command_bus"
            assert row.scope_token == "project_scoped"
            assert row.status_token == "draft"
            assert row.manifest_json["profile_id"] == "profile-alpha"
            assert (
                row.manifest_json["requested_permissions"][0]["permission"]
                == "command.run"
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
