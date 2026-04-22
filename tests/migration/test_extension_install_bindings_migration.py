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
    AgentExtensionInstallBinding,
    AgentExtensionInstallGateDecision,
    AgentExtensionProposal,
    AgentExtensionRegistryEntry,
)
from guardian.extensions.tokens import (
    CapabilityEntryProvenanceClass,
    CapabilityRegistryStatus,
    ExtensionInstallBindingScope,
    ExtensionInstallBindingStatus,
    ExtensionProposalScope,
    ExtensionProposalStatus,
    ExtensionTargetSurface,
    InstallGateDecisionToken,
)


def _build_database_url(base_url: str, database_name: str) -> str:
    parsed = urlparse(base_url)
    return urlunparse(parsed._replace(path=f"/{database_name}"))


def _admin_database_url(base_url: str) -> str:
    parsed = urlparse(base_url)
    return urlunparse(parsed._replace(path="/postgres"))


@pytest.mark.integration
def test_extension_install_bindings_migration_round_trip(tmp_path, monkeypatch):
    if psycopg is None:
        pytest.skip("psycopg not installed")

    base_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not base_url:
        pytest.skip(
            "TEST_DATABASE_URL or DATABASE_URL environment variable required"
        )

    admin_url = _admin_database_url(base_url)
    db_name = f"codexify_extension_bindings_{uuid.uuid4().hex[:12]}"
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

        assert "agent_extension_install_bindings" in inspector.get_table_names()

        binding_columns = {
            column["name"]
            for column in inspector.get_columns(
                "agent_extension_install_bindings"
            )
        }
        assert {
            "binding_id",
            "account_id",
            "registry_entry_id",
            "proposal_id",
            "scope_token",
            "project_id",
            "profile_id",
            "account_scope_target_id",
            "binding_status_token",
            "bind_reason",
            "bind_notes_json",
            "bind_metadata_json",
            "unbind_metadata_json",
            "source_thread_id",
            "source_message_id",
            "created_at",
            "updated_at",
            "unbound_at",
        } <= binding_columns

        binding_indexes = {
            index["name"]
            for index in inspector.get_indexes(
                "agent_extension_install_bindings"
            )
        }
        assert {
            "ix_agent_extension_install_bindings_account_created_at",
            "ix_agent_extension_install_bindings_registry_created_at",
            "ix_agent_extension_install_bindings_scope_created_at",
            "ix_agent_extension_install_bindings_project_created_at",
            "ix_agent_extension_install_bindings_profile_created_at",
            "ix_agent_extension_install_bindings_account_target_created_at",
            "ix_agent_extension_install_bindings_status_created_at",
            "uq_agent_extension_install_bindings_active_tuple",
        } <= binding_indexes

        Session = sessionmaker(bind=engine, future=True)
        with Session() as session:
            proposal = AgentExtensionProposal(
                proposal_id="proposal-1",
                account_id="user-123",
                project_id=17,
                profile_id=None,
                source_thread_id=21,
                source_message_id=22,
                target_surface_token=ExtensionTargetSurface.COMMAND_BUS.value,
                scope_token=ExtensionProposalScope.PROJECT.value,
                status_token=ExtensionProposalStatus.ACCEPTED.value,
                requested_permissions_json=[
                    {
                        "permission": "command.run",
                        "resource": "command_bus",
                        "reason": "bounded command execution",
                        "metadata": {},
                    }
                ],
                declared_dependencies_json=[],
                rollback_metadata_json={},
                test_evidence_json={},
                manifest_json={
                    "manifest_version": "extension-proposal-manifest.v1",
                    "target_surface": ExtensionTargetSurface.COMMAND_BUS.value,
                    "scope": ExtensionProposalScope.PROJECT.value,
                    "source_thread_id": 21,
                    "source_message_id": 22,
                    "project_id": 17,
                    "profile_id": None,
                    "requested_permissions": [
                        {
                            "permission": "command.run",
                            "resource": "command_bus",
                            "reason": "bounded command execution",
                            "metadata": {},
                        }
                    ],
                    "declared_dependencies": [],
                },
            )
            session.add(proposal)

            decision = AgentExtensionInstallGateDecision(
                decision_id="decision-1",
                account_id="user-123",
                proposal_id="proposal-1",
                decision_token=InstallGateDecisionToken.APPROVED.value,
                reason="manual approval",
                notes_json={},
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
                profile_id=None,
                source_thread_id=21,
                source_message_id=22,
                target_surface_token=ExtensionTargetSurface.COMMAND_BUS.value,
                scope_token=ExtensionProposalScope.PROJECT.value,
                status_token=CapabilityRegistryStatus.REGISTERED.value,
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
                manifest_snapshot_json=proposal.manifest_json,
                registration_metadata_json={"decision_id": "decision-1"},
                provenance_class_token=CapabilityEntryProvenanceClass.PROPOSAL_APPROVAL.value,
                provenance_json={
                    "provenance_class": CapabilityEntryProvenanceClass.PROPOSAL_APPROVAL.value,
                    "proposal_id": "proposal-1",
                    "decision_id": "decision-1",
                    "source_thread_id": 21,
                    "source_message_id": 22,
                    "target_surface": ExtensionTargetSurface.COMMAND_BUS.value,
                },
            )
            session.add(registry)

            binding = AgentExtensionInstallBinding(
                binding_id="binding-1",
                account_id="user-123",
                registry_entry_id="registry-1",
                proposal_id="proposal-1",
                scope_token=ExtensionInstallBindingScope.PROJECT.value,
                project_id=17,
                profile_id=None,
                account_scope_target_id=None,
                binding_status_token=ExtensionInstallBindingStatus.ACTIVE.value,
                bind_reason="manual binding",
                bind_notes_json={"reviewer": "alice"},
                bind_metadata_json={"registry_entry_id": "registry-1"},
                unbind_metadata_json={},
                source_thread_id=21,
                source_message_id=22,
            )
            session.add(binding)
            session.commit()

        with Session() as session:
            row = session.get(AgentExtensionInstallBinding, "binding-1")
            assert row is not None
            assert (
                row.binding_status_token
                == ExtensionInstallBindingStatus.ACTIVE.value
            )
            assert row.registry_entry_id == "registry-1"
            assert row.project_id == 17
            assert row.source_thread_id == 21
            assert row.bind_notes_json["reviewer"] == "alice"
    finally:
        if engine is not None:
            engine.dispose()
        with psycopg.connect(admin_url, autocommit=True) as admin_conn:
            with admin_conn.cursor() as cur:
                cur.execute(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s",
                    (db_name,),
                )
                cur.execute(f"DROP DATABASE IF EXISTS {db_name}")
