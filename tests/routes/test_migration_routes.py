"""Route tests for ChatGPT migration endpoint."""

from __future__ import annotations

from unittest.mock import patch


def _post_export(test_client, path: str):
    files = {"file": ("export.json", b"[]", "application/json")}
    return test_client.post(
        path,
        files=files,
        headers={"X-User-Id": "test_user"},
    )


def test_migration_endpoint_registered(test_client):
    with patch(
        "guardian.routes.migration.ingest_chatgpt_export"
    ) as mock_ingest:
        mock_ingest.return_value = {
            "threads_imported": 1,
            "messages_imported": 2,
        }
        canonical = _post_export(test_client, "/api/upload-chatgpt-export")
        legacy = _post_export(test_client, "/upload-chatgpt-export")

    assert canonical.status_code == 200
    assert legacy.status_code == 200

    for res in (canonical, legacy):
        data = res.json()
        assert data["threads_imported"] == 1
        assert data["messages_imported"] == 2


def test_migration_accepts_valid_content_even_with_non_json_filename(
    test_client,
):
    valid_payload = b"[]"
    files = {
        "file": (
            "totally_weird_name.txt",
            valid_payload,
            "application/octet-stream",
        )
    }

    with patch(
        "guardian.routes.migration.ingest_chatgpt_export"
    ) as mock_ingest:
        mock_ingest.return_value = {
            "threads_imported": 0,
            "messages_imported": 0,
        }
        response = test_client.post(
            "/api/upload-chatgpt-export",
            files=files,
            headers={"X-User-Id": "test_user"},
        )

    assert response.status_code == 200
    mock_ingest.assert_called_once()
