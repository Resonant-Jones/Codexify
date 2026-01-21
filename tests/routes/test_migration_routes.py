"""Route tests for ChatGPT migration endpoint."""

from __future__ import annotations

from unittest.mock import patch


def test_migration_endpoint_registered(test_client):
    files = {"file": ("export.json", b"[]", "application/json")}
    with patch(
        "guardian.routes.migration.ingest_chatgpt_export"
    ) as mock_ingest:
        mock_ingest.return_value = {
            "threads_imported": 1,
            "messages_imported": 2,
        }
        res = test_client.post(
            "/api/upload-chatgpt-export",
            files=files,
            headers={"X-User-Id": "test_user"},
        )

    assert res.status_code == 200
    data = res.json()
    assert data["threads_imported"] == 1
    assert data["messages_imported"] == 2
