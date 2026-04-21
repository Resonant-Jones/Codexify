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

from guardian.db.models import (
    AgentExtensionInstallGateDecision,
    AgentExtensionProposal,
    AgentExtensionRegistryEntry,
)


def _build_database_url(base_url: str, database_name: str) -> str:
    parsed = urlparse(base_url)
    return urlunparse(parsed._replace(path=f"/{database_name}"))


def _admin_database_url(base_url: str) -> str:
    parsed = urlparse(base_url)
    return urlunparse(parsed._replace(path="/postgres"))


@pytest.mark.integration
def test_extension_registry_migration_round_trip(tmp_path, monkeypatch):
    if psycopg is None:
        pytest.skip("psycopg not installed")

    base_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not base_url:
        pytest.skip(
            "TEST_DATABASE_URL or DATABASE_URL environment variable required"
        )

    admin_url = _admin_database_url(base_url)
    db_name = f"codexify_extension_registry_{uuid.uuid4().hex[:12]}"
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
        command.upgrade(cfg, "head")

        engine = create_engine(temp_url)
        inspector = inspect(engine)

        assert (
            "agent_extension_install_gate_decisions"
            in inspector.get_table_names()
        )
        assert "agent_extension_registry_entries" in inspector.get_table_names()

        decision_columns = {
            column["name"]
            for column in inspector.get_columns(
                "agent_extension_install_gate_decisions"
            )
        }
        assert {
            "decision_id",
            "account_id",
            "proposal_id",
            "decision_token",
            "reason",
            "notes_json",
            "requested_permissions_json",
            "approved_permissions_json",
            "created_at",
            "updated_at",
        } <= decision_columns

        registry_columns = {
            column["name"]
            for column in inspector.get_columns(
                "agent_extension_registry_entries"
            )
        }
        assert {
            "registry_id",
            "account_id",
            "proposal_id",
            "decision_id",
            "project_id",
            "profile_id",
            "source_thread_id",
            "source_message_id",
            "target_surface_token",
            "scope_token",
            "status_token",
            "requested_permissions_json",
            "approved_permissions_json",
            "manifest_snapshot_json",
            "registration_metadata_json",
            "provenance_class_token",
            "provenance_json",
            "created_at",
            "updated_at",
        } <= registry_columns

        decision_indexes = {
            index["name"]
            for index in inspector.get_indexes(
                "agent_extension_install_gate_decisions"
            )
        }
        assert {
            "ix_agent_extension_install_gate_decisions_account_created_at",
            "ix_agent_extension_install_gate_decisions_proposal_created_at",
            "ix_agent_extension_install_gate_decisions_decision_created_at",
        } <= decision_indexes

        registry_indexes = {
            index["name"]
            for index in inspector.get_indexes(
                "agent_extension_registry_entries"
            )
        }
        assert {
            "ix_agent_extension_registry_entries_account_created_at",
            "ix_agent_extension_registry_entries_proposal_created_at",
            "ix_agent_extension_registry_entries_project_created_at",
            "ix_agent_extension_registry_entries_profile_created_at",
            "ix_agent_extension_registry_entries_status_created_at",
            "ix_agent_extension_registry_entries_decision_created_at",
        } <= registry_indexes

        Session = sessionmaker(bind=engine, future=True)
        with Session() as session:
            proposal = AgentExtensionProposal(
                proposal_id="proposal-1",
                account_id="user-123",
                project_id=17,
                profile_id="profile-alpha",
                source_thread_id=21,
                source_message_id=22,
                target_surface_token="command_bus",
                scope_token="project_scoped",
                status_token="accepted",
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
                    "summary": "registry migration smoke test",
                    "artifacts": [
                        "tests/migration/test_extension_registry_migration.py",
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
                        "summary": "registry migration smoke test",
                        "artifacts": [
                            "tests/migration/test_extension_registry_migration.py",
                        ],
                        "metadata": {},
                    },
                },
            )
            session.add(proposal)

            decision = AgentExtensionInstallGateDecision(
                decision_id="decision-1",
                account_id="user-123",
                proposal_id="proposal-1",
                decision_token="approved",
                reason="manual approval",
                notes_json={
                    "reviewer": "alice",
                    "note": "approved for testing",
                },
                requested_permissions_json=[
                    {
                        "permission": "command.run",
                        "resource": "command_bus",
                        "reason": "bounded command execution",
                        "metadata": {},
                    }
                ],
                approved_permissions_json=[
                    {
                        "permission": "command.run",
                        "resource": "command_bus",
                        "reason": "bounded command execution",
                        "metadata": {},
                    }
                ],
            )
            session.add(decision)

            registry = AgentExtensionRegistryEntry(
                registry_id="registry-1",
                account_id="user-123",
                proposal_id="proposal-1",
                decision_id="decision-1",
                project_id=17,
                profile_id="profile-alpha",
                source_thread_id=21,
                source_message_id=22,
                target_surface_token="command_bus",
                scope_token="project_scoped",
                status_token="registered",
                requested_permissions_json=[
                    {
                        "permission": "command.run",
                        "resource": "command_bus",
                        "reason": "bounded command execution",
                        "metadata": {},
                    }
                ],
                approved_permissions_json=[
                    {
                        "permission": "command.run",
                        "resource": "command_bus",
                        "reason": "bounded command execution",
                        "metadata": {},
                    }
                ],
                manifest_snapshot_json={
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
                },
                registration_metadata_json={
                    "decision_id": "decision-1",
                    "decision_token": "approved",
                    "decision_reason": "manual approval",
                    "decision_notes": {
                        "reviewer": "alice",
                        "note": "approved for testing",
                    },
                    "proposal_id": "proposal-1",
                    "account_id": "user-123",
                },
                provenance_class_token="proposal_approval",
                provenance_json={
                    "provenance_class": "proposal_approval",
                    "proposal_id": "proposal-1",
                    "decision_id": "decision-1",
                    "source_thread_id": 21,
                    "source_message_id": 22,
                    "target_surface": "command_bus",
                },
            )
            session.add(registry)
            session.commit()
            session.refresh(proposal)
            session.refresh(decision)
            session.refresh(registry)

        with Session() as session:
            loaded_decision = (
                session.query(AgentExtensionInstallGateDecision)
                .filter_by(decision_id="decision-1")
                .one()
            )
            loaded_registry = (
                session.query(AgentExtensionRegistryEntry)
                .filter_by(registry_id="registry-1")
                .one()
            )
            assert loaded_decision.account_id == "user-123"
            assert loaded_decision.proposal_id == "proposal-1"
            assert loaded_decision.decision_token == "approved"
            assert loaded_registry.account_id == "user-123"
            assert loaded_registry.proposal_id == "proposal-1"
            assert loaded_registry.decision_id == "decision-1"
            assert loaded_registry.status_token == "registered"
            assert (
                loaded_registry.manifest_snapshot_json["profile_id"]
                == "profile-alpha"
            )
            assert (
                loaded_registry.registration_metadata_json["decision_token"]
                == "approved"
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
