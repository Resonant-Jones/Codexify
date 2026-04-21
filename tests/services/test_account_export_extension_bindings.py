from __future__ import annotations

import json
import os
import zipfile
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

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
from guardian.services.account_export import build_account_export_zip
from guardian.services.account_restore import (
    RESTORE_ORDER,
    AccountRestoreService,
)

USER_ID = "user-123"


def _utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _manifest_payload() -> dict[str, object]:
    return {
        "manifest_version": "extension-proposal-manifest.v1",
        "target_surface": ExtensionTargetSurface.COMMAND_BUS.value,
        "scope": ExtensionProposalScope.PROJECT.value,
        "source_thread_id": 101,
        "source_message_id": 202,
        "project_id": 10,
        "profile_id": "profile-alpha",
        "summary": "Generate a bounded tool plugin",
        "description": "Draft a tool proposal without executing it.",
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
            "summary": "binding export coverage",
            "artifacts": [
                "tests/services/test_account_export_extension_bindings.py",
            ],
            "metadata": {},
        },
    }


def _build_rows() -> dict[str, list[dict[str, object]]]:
    manifest = _manifest_payload()
    requested_permissions = manifest["requested_permissions"]
    approved_permissions = requested_permissions
    return {
        "extension_proposals": [
            {
                "proposal_id": "proposal-1",
                "account_id": USER_ID,
                "project_id": 10,
                "profile_id": "profile-alpha",
                "source_thread_id": 101,
                "source_message_id": 202,
                "target_surface_token": ExtensionTargetSurface.COMMAND_BUS.value,
                "scope_token": ExtensionProposalScope.PROJECT.value,
                "status_token": ExtensionProposalStatus.ACCEPTED.value,
                "requested_permissions_json": requested_permissions,
                "declared_dependencies_json": manifest["declared_dependencies"],
                "rollback_metadata_json": manifest["rollback_metadata"],
                "test_evidence_json": manifest["test_evidence_metadata"],
                "manifest_json": manifest,
                "created_at": _utc("2026-03-14T00:00:00Z"),
                "updated_at": _utc("2026-03-14T01:00:00Z"),
            }
        ],
        "extension_install_gate_decisions": [
            {
                "decision_id": "decision-1",
                "account_id": USER_ID,
                "proposal_id": "proposal-1",
                "decision_token": InstallGateDecisionToken.APPROVED.value,
                "reason": "manual approval",
                "notes_json": {
                    "reviewer": "alice",
                    "note": "approved for testing",
                },
                "requested_permissions_json": requested_permissions,
                "approved_permissions_json": approved_permissions,
                "created_at": _utc("2026-03-14T02:00:00Z"),
                "updated_at": _utc("2026-03-14T02:01:00Z"),
            }
        ],
        "extension_registry_entries": [
            {
                "registry_id": "registry-1",
                "account_id": USER_ID,
                "proposal_id": "proposal-1",
                "decision_id": "decision-1",
                "project_id": 10,
                "profile_id": "profile-alpha",
                "source_thread_id": 101,
                "source_message_id": 202,
                "target_surface_token": ExtensionTargetSurface.COMMAND_BUS.value,
                "scope_token": ExtensionProposalScope.PROJECT.value,
                "status_token": CapabilityRegistryStatus.REGISTERED.value,
                "requested_permissions_json": requested_permissions,
                "approved_permissions_json": approved_permissions,
                "manifest_snapshot_json": manifest,
                "registration_metadata_json": {
                    "decision_id": "decision-1",
                    "decision_token": InstallGateDecisionToken.APPROVED.value,
                    "decision_reason": "manual approval",
                    "decision_notes": {
                        "reviewer": "alice",
                        "note": "approved for testing",
                    },
                    "proposal_id": "proposal-1",
                    "account_id": USER_ID,
                },
                "provenance_class_token": CapabilityEntryProvenanceClass.PROPOSAL_APPROVAL.value,
                "provenance_json": {
                    "provenance_class": CapabilityEntryProvenanceClass.PROPOSAL_APPROVAL.value,
                    "proposal_id": "proposal-1",
                    "decision_id": "decision-1",
                    "source_thread_id": 101,
                    "source_message_id": 202,
                    "target_surface": ExtensionTargetSurface.COMMAND_BUS.value,
                },
                "created_at": _utc("2026-03-14T02:00:00Z"),
                "updated_at": _utc("2026-03-14T02:01:00Z"),
            }
        ],
        "extension_install_bindings": [
            {
                "binding_id": "binding-1",
                "account_id": USER_ID,
                "registry_entry_id": "registry-1",
                "proposal_id": "proposal-1",
                "scope_token": ExtensionInstallBindingScope.PROJECT.value,
                "project_id": 10,
                "profile_id": None,
                "account_scope_target_id": None,
                "binding_status_token": ExtensionInstallBindingStatus.ACTIVE.value,
                "bind_reason": "manual binding",
                "bind_notes_json": {
                    "reviewer": "alice",
                    "note": "bound for testing",
                },
                "bind_metadata_json": {
                    "registry_entry_id": "registry-1",
                    "proposal_id": "proposal-1",
                    "scope_token": ExtensionInstallBindingScope.PROJECT.value,
                    "source_thread_id": 101,
                    "source_message_id": 202,
                },
                "unbind_metadata_json": {},
                "source_thread_id": 101,
                "source_message_id": 202,
                "created_at": _utc("2026-03-14T03:00:00Z"),
                "updated_at": _utc("2026-03-14T03:01:00Z"),
                "unbound_at": None,
            }
        ],
    }


def _normalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _normalize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, tuple):
        return [_normalize(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


class FakeAccountRestoreDB:
    PK_COLUMNS = {
        "extension_proposals": "proposal_id",
        "extension_install_gate_decisions": "decision_id",
        "extension_registry_entries": "registry_id",
        "extension_install_bindings": "binding_id",
    }

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.tables: dict[str, dict[Any, dict[str, Any]]] = {}

    def __getattr__(self, name: str):
        if not name.startswith("restore_account_export_"):
            raise AttributeError(name)
        family = name.removeprefix("restore_account_export_")

        def _restore(rows, *, conn=None):
            _ = conn
            self.calls.append(family)
            self.tables.setdefault(family, {})
            if not rows:
                return {
                    "imported": 0,
                    "skipped": 0,
                    "failed": 0,
                    "unresolved": 0,
                }
            pk_column = self.PK_COLUMNS.get(family, "id")
            imported = 0
            skipped = 0
            for raw_row in rows:
                row = dict(raw_row)
                normalized = {
                    column: _normalize(value) for column, value in row.items()
                }
                pk_value = normalized[pk_column]
                existing = self.tables[family].get(pk_value)
                if existing == normalized:
                    skipped += 1
                    continue
                self.tables[family][pk_value] = normalized
                imported += 1
            return {
                "imported": imported,
                "skipped": skipped,
                "failed": 0,
                "unresolved": 0,
            }

        return _restore


def test_account_export_and_restore_include_install_bindings(
    tmp_path: Path, monkeypatch
) -> None:
    storage_base = tmp_path / "storage"
    monkeypatch.setenv("STORAGE_BASE_PATH", str(storage_base))
    monkeypatch.setenv("STORAGE_URL_PREFIX", "/media")

    rows = _build_rows()

    def _fetch(user_id: str):
        assert user_id == USER_ID
        return rows

    db = SimpleNamespace(fetch_account_export_bundle_for_user=_fetch)
    archive_path = build_account_export_zip(db, SimpleNamespace(id=USER_ID))
    restore_db = FakeAccountRestoreDB()
    try:
        with zipfile.ZipFile(archive_path, "r") as archive:
            names = archive.namelist()
            assert "entities/extension_proposals.json" in names
            assert "entities/extension_install_gate_decisions.json" in names
            assert "entities/extension_registry_entries.json" in names
            assert "entities/extension_install_bindings.json" in names

            manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
            assert manifest["entity_counts"]["extension_proposals"] == 1
            assert (
                manifest["entity_counts"]["extension_install_gate_decisions"]
                == 1
            )
            assert manifest["entity_counts"]["extension_registry_entries"] == 1
            assert manifest["entity_counts"]["extension_install_bindings"] == 1

            binding_payload = json.loads(
                archive.read("entities/extension_install_bindings.json").decode(
                    "utf-8"
                )
            )
            assert binding_payload == [
                _normalize(rows["extension_install_bindings"][0])
            ]
            assert (
                binding_payload[0]["binding_status_token"]
                == ExtensionInstallBindingStatus.ACTIVE.value
            )
            assert (
                binding_payload[0]["bind_metadata_json"]["registry_entry_id"]
                == "registry-1"
            )

        report = AccountRestoreService(restore_db).restore_from_zip(
            Path(archive_path).read_bytes(),
            user_id=USER_ID,
        )

        assert restore_db.calls == list(RESTORE_ORDER)
        assert report["ok"] is True
        assert (
            restore_db.tables["extension_install_bindings"]["binding-1"][
                "registry_entry_id"
            ]
            == "registry-1"
        )
        assert (
            restore_db.tables["extension_install_bindings"]["binding-1"][
                "binding_status_token"
            ]
            == ExtensionInstallBindingStatus.ACTIVE.value
        )
        assert (
            restore_db.tables["extension_install_bindings"]["binding-1"][
                "source_thread_id"
            ]
            == 101
        )
        assert (
            restore_db.tables["extension_install_bindings"]["binding-1"][
                "bind_notes_json"
            ]["reviewer"]
            == "alice"
        )
    finally:
        if os.path.exists(archive_path):
            os.unlink(archive_path)
