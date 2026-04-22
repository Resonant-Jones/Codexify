from __future__ import annotations

import json
import os
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from guardian.services.account_export import build_account_export_zip

USER_ID = "user-123"


def _utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _manifest_payload() -> dict[str, object]:
    return {
        "manifest_version": "extension-proposal-manifest.v1",
        "target_surface": "command_bus",
        "scope": "project_scoped",
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
            "summary": "proposal draft coverage",
            "artifacts": [
                "tests/services/test_account_export_extension_proposals.py",
            ],
            "metadata": {},
        },
    }


def _build_rows() -> dict[str, list[dict[str, object]]]:
    return {
        "extension_proposals": [
            {
                "proposal_id": "proposal-1",
                "account_id": USER_ID,
                "project_id": 10,
                "profile_id": "profile-alpha",
                "source_thread_id": 101,
                "source_message_id": 202,
                "target_surface_token": "command_bus",
                "scope_token": "project_scoped",
                "status_token": "draft",
                "requested_permissions_json": [
                    {
                        "permission": "command.run",
                        "resource": "command_bus",
                        "reason": "bounded command execution",
                        "metadata": {},
                    }
                ],
                "declared_dependencies_json": [
                    {
                        "name": "httpx",
                        "version_spec": ">=0.28",
                        "source": "pypi",
                        "required": True,
                        "metadata": {},
                    }
                ],
                "rollback_metadata_json": {
                    "strategy": "disable_and_revert",
                    "rollback_ref": "ticket-123",
                    "can_rollback": True,
                    "metadata": {},
                },
                "test_evidence_json": {
                    "status": "passing",
                    "summary": "proposal draft coverage",
                    "artifacts": [
                        "tests/services/test_account_export_extension_proposals.py",
                    ],
                    "metadata": {},
                },
                "manifest_json": _manifest_payload(),
                "created_at": _utc("2026-03-14T00:00:00Z"),
                "updated_at": _utc("2026-03-14T01:00:00Z"),
            }
        ]
    }


def _normalize(value):
    if isinstance(value, dict):
        return {key: _normalize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, tuple):
        return [_normalize(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def test_account_export_includes_extension_proposal_family(
    tmp_path: Path, monkeypatch
) -> None:
    storage_root = tmp_path / "storage"
    monkeypatch.setenv("STORAGE_BASE_PATH", str(storage_root))
    monkeypatch.setenv("STORAGE_URL_PREFIX", "/media")

    rows = _build_rows()

    def _fetch_bundle(user_id: str):
        assert user_id == USER_ID
        return rows

    db = SimpleNamespace(fetch_account_export_bundle_for_user=_fetch_bundle)

    zip_path = build_account_export_zip(db, SimpleNamespace(id=USER_ID))
    try:
        with zipfile.ZipFile(zip_path, "r") as archive:
            names = archive.namelist()
            assert "manifest.json" in names
            assert "entities/extension_proposals.json" in names

            manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
            assert manifest["entity_counts"]["extension_proposals"] == 1

            payload = json.loads(
                archive.read("entities/extension_proposals.json").decode(
                    "utf-8"
                )
            )
            assert payload == _normalize(rows["extension_proposals"])
            row = payload[0]
            assert row["proposal_id"] == "proposal-1"
            assert row["account_id"] == USER_ID
            assert row["source_thread_id"] == 101
            assert row["source_message_id"] == 202
            assert row["manifest_json"]["target_surface"] == "command_bus"
            assert (
                row["manifest_json"]["requested_permissions"][0]["permission"]
                == "command.run"
            )
    finally:
        if os.path.exists(zip_path):
            os.unlink(zip_path)
