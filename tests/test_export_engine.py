import os
import pytest
from unittest.mock import patch
from guardian.export_engine import (
    export_markdown,
    export_csv,
    export_json,
    export_to_notion
)

# === Test basic format exports ===

def test_export_markdown_basic():
    records = [{"timestamp": "now", "command": "hello world"}]
    output = export_markdown(records)
    assert "**now**: hello world" in output

def test_export_csv_basic():
    records = [{"timestamp": "now", "command": "hello"}]
    output = export_csv(records)
    assert "timestamp,command" in output
    assert "now,hello" in output

def test_export_json_basic():
    records = [{"timestamp": "now", "command": "test"}]
    output = export_json(records)
    assert '"timestamp": "now"' in output

# === Test Notion export with mock ===

@patch("notion_client.Client")
def test_export_to_notion_mock(client_mock):
    mock_instance = client_mock.return_value
    mock_instance.pages.create.return_value = {"url": "https://notion.so/fake-page"}

    records = [{"timestamp": "now", "command": "test"}]
    result = export_to_notion(
        records=records,
        parent_id="mock-page-id",
        notion_token="mock-token",
        parent_type="page"
    )

    assert result == "https://notion.so/fake-page"
    mock_instance.pages.create.assert_called_once()

@patch("notion_client.Client")
def test_export_to_notion_failure(client_mock):
    mock_instance = client_mock.return_value
    mock_instance.pages.create.side_effect = Exception("mock error")

    with pytest.raises(RuntimeError, match="mock error"):
        export_to_notion(
            records=[{"timestamp": "fail"}],
            parent_id="bad-id",
            notion_token="bad-token",
            parent_type="page"
        )