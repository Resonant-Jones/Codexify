from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

CONNECTOR_NAME = "obsidian_local"


@pytest.fixture(autouse=True)
def _patch_obsidian_db(mock_db, monkeypatch):
    # Ensure routes use the in-memory mock DB instead of a real connection
    monkeypatch.setattr("guardian.routes.obsidian.chatlog_db", mock_db)
    monkeypatch.setattr("guardian.core.dependencies.chatlog_db", mock_db)
    return mock_db


def _mock_config(
    vault_root: Path,
    *,
    allowed_paths: list[str] | None = None,
    allowed_tags: list[str] | None = None,
    last_indexed_at: str | None = None,
    last_indexed_count: int | None = None,
    last_index_error: str | None = None,
) -> dict[str, Any]:
    return {
        "name": CONNECTOR_NAME,
        "type": "obsidian",
        "settings": {
            "vault_root": str(vault_root),
            "allowed_paths": allowed_paths if allowed_paths is not None else [],
            "allowed_tags": allowed_tags if allowed_tags is not None else [],
            "last_indexed_at": last_indexed_at,
            "last_indexed_count": last_indexed_count,
            "last_index_error": last_index_error,
        },
    }


def test_get_config_returns_stored_config(test_client, mock_db):
    settings = {
        "vault_root": "/vaults/obsidian",
        "allowed_paths": ["Projects"],
        "allowed_tags": ["codexify"],
    }
    mock_db.get_connector_config.return_value = {
        "name": CONNECTOR_NAME,
        "type": "obsidian",
        "settings": settings,
    }

    resp = test_client.get("/api/obsidian/config")

    assert resp.status_code == 200
    data = resp.json()
    assert data["config"] == settings
    mock_db.get_connector_config.assert_called_with(CONNECTOR_NAME)


def test_put_config_persists_validated_config(tmp_path, test_client, mock_db):
    vault = tmp_path / "vault"
    projects = vault / "Projects"
    projects.mkdir(parents=True)

    mock_db.get_connector_config.return_value = None

    def _create(name, type_, config):
        assert name == CONNECTOR_NAME
        assert type_ == "obsidian"
        assert config["vault_root"] == str(vault.resolve())
        assert config["allowed_paths"] == ["Projects"]
        assert config["allowed_tags"] == ["tagged"]
        return {"name": name, "type": type_, "settings": config}

    mock_db.create_connector_config.side_effect = _create

    resp = test_client.put(
        "/api/obsidian/config",
        json={
            "vault_root": str(vault),
            "allowed_paths": ["Projects"],
            "allowed_tags": ["tagged"],
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["config"]["vault_root"] == str(vault.resolve())
    assert data["config"]["allowed_paths"] == ["Projects"]
    assert data["config"]["allowed_tags"] == ["tagged"]


def test_preview_returns_deterministic_sample(tmp_path, test_client, mock_db):
    vault = tmp_path / "vault"
    projects = vault / "Projects"
    projects.mkdir(parents=True)

    # Create 25 markdown files to verify bounding to first 20 sorted paths
    for i in range(25):
        note = projects / f"Note_{i:02d}.md"
        note.write_text("---\ntags:\n- codexify\n---\nbody", encoding="utf-8")

    mock_db.get_connector_config.return_value = _mock_config(
        vault, allowed_paths=["Projects"], allowed_tags=["codexify"]
    )

    resp = test_client.post(
        "/api/obsidian/preview",
        json={"allowed_paths": ["Projects"], "allowed_tags": ["codexify"]},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["note_count"] == 25
    assert len(data["sample_paths"]) == 20
    assert data["sample_paths"][0].endswith("Note_00.md")
    assert data["sample_paths"][-1].endswith("Note_19.md")


def test_preview_rejects_paths_outside_vault(tmp_path, test_client, mock_db):
    vault = tmp_path / "vault"
    vault.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()

    mock_db.get_connector_config.return_value = _mock_config(
        vault, allowed_paths=["."]
    )

    resp = test_client.post(
        "/api/obsidian/preview", json={"allowed_paths": ["../outside"]}
    )

    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert "allowed_path_outside_vault" in detail["error"]


def test_index_invokes_indexer_and_updates_metadata(
    test_client, mock_db, monkeypatch
):
    settings = {
        "vault_root": "/vaults/obsidian",
        "allowed_paths": ["Projects"],
        "allowed_tags": ["codexify"],
    }
    mock_db.get_connector_config.return_value = {
        "name": CONNECTOR_NAME,
        "type": "obsidian",
        "settings": settings,
    }

    captured = {}

    def fake_index(vault_root, allowed_paths=None, allowed_tags=None):
        captured["args"] = (vault_root, allowed_paths, allowed_tags)
        return {
            "indexed": 3,
            "scanned": 5,
            "deleted": 1,
            "failures": [],
            "indexed_at": "2026-03-25T00:00:00Z",
        }

    monkeypatch.setattr(
        "guardian.routes.obsidian.index_obsidian_vault", fake_index
    )
    mock_db.update_connector_config.return_value = {"settings": settings}

    resp = test_client.post("/api/obsidian/index")

    assert resp.status_code == 200
    assert captured["args"] == (
        "/vaults/obsidian",
        ["Projects"],
        ["codexify"],
    )
    cfg = mock_db.update_connector_config.call_args.kwargs["config"]
    assert cfg["last_indexed_at"] == "2026-03-25T00:00:00Z"
    assert cfg["last_indexed_count"] == 3
    assert cfg["last_index_error"] is None


def test_index_failure_sets_last_index_error(test_client, mock_db, monkeypatch):
    vault_root = "/vaults/obsidian"
    mock_db.get_connector_config.return_value = _mock_config(
        Path(vault_root), allowed_paths=["Projects"]
    )

    def boom(*_args, **_kwargs):
        raise RuntimeError("explode")

    monkeypatch.setattr("guardian.routes.obsidian.index_obsidian_vault", boom)
    mock_db.update_connector_config.return_value = {"settings": {}}

    resp = test_client.post("/api/obsidian/index")

    assert resp.status_code == 500
    cfg = mock_db.update_connector_config.call_args.kwargs["config"]
    assert cfg["last_index_error"] == "explode"
    assert cfg["vault_root"] == vault_root


def test_missing_config_errors_on_preview_and_index(test_client, mock_db):
    mock_db.get_connector_config.return_value = None

    resp_preview = test_client.post("/api/obsidian/preview", json={})
    assert resp_preview.status_code == 400
    assert resp_preview.json()["detail"]["error"] == "obsidian_config_missing"

    resp_index = test_client.post("/api/obsidian/index")
    assert resp_index.status_code == 400
    assert resp_index.json()["detail"]["error"] == "obsidian_config_missing"
