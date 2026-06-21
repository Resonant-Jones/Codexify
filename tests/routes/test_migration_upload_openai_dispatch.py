"""Dispatch tests for the migration upload route."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

SERVER_USER_ID = "local_user"


@pytest.fixture(autouse=True)
def _single_user_identity_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CODEXIFY_SINGLE_USER_ID", SERVER_USER_ID)
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("LOCAL_DEV", "false")


def _stats(
    *,
    threads: int = 1,
    messages: int = 2,
    conversation_records: int | None = None,
) -> dict[str, object]:
    stats: dict[str, object] = {
        "threads_imported": threads,
        "messages_imported": messages,
        "embedding_candidates": 0,
        "embeddings_persisted": 0,
        "embeddings_failed": 0,
        "embedding_coverage_degraded": False,
    }
    if conversation_records is not None:
        stats["conversation_records"] = conversation_records
    return stats


def _legacy_chatgpt_export() -> bytes:
    return json.dumps(
        [
            {
                "id": "legacy-thread",
                "title": "Legacy Import",
                "current_node": "m2",
                "mapping": {
                    "m1": {
                        "id": "m1",
                        "parent": None,
                        "children": ["m2"],
                        "message": {
                            "id": "m1",
                            "author": {"role": "user"},
                            "content": {"parts": ["Legacy hello"]},
                            "create_time": 1,
                        },
                    },
                    "m2": {
                        "id": "m2",
                        "parent": "m1",
                        "children": [],
                        "message": {
                            "id": "m2",
                            "author": {"role": "assistant"},
                            "content": {"parts": ["Legacy reply"]},
                            "create_time": 2,
                        },
                    },
                },
            }
        ]
    ).encode("utf-8")


def _claude_export() -> bytes:
    return json.dumps(
        [
            {
                "uuid": "claude-thread",
                "name": "Claude Import",
                "chat_messages": [
                    {
                        "uuid": "claude-message-1",
                        "sender": "human",
                        "text": "Claude hello",
                        "created_at": "2026-01-01T00:00:00Z",
                    }
                ],
            }
        ]
    ).encode("utf-8")


def _sharded_dat_export() -> bytes:
    return json.dumps(
        {
            "conversation_id": "sharded-thread",
            "title": "Sharded Thread",
            "messages": [
                {
                    "id": "msg-user",
                    "author": {"role": "user"},
                    "content": "Hello from a dat file",
                    "create_time": 1,
                },
                {
                    "id": "msg-assistant",
                    "role": "assistant",
                    "content": {"parts": ["Dat reply"]},
                    "create_time": 2,
                },
            ],
        }
    ).encode("utf-8")


def _post_upload(
    test_client,
    *,
    filename: str,
    content: bytes,
    content_type: str,
):
    return test_client.post(
        "/api/upload-chatgpt-export",
        files={"file": (filename, content, content_type)},
        headers={"X-User-Id": "spoofed_user"},
    )


def test_legacy_chatgpt_json_dispatches_to_legacy_importer(test_client):
    content = _legacy_chatgpt_export()

    with patch(
        "guardian.routes.migration.ingest_chatgpt_export",
        return_value=_stats(),
    ) as legacy_import, patch(
        "guardian.routes.migration.ingest_claude_export"
    ) as claude_import, patch(
        "guardian.routes.migration.import_openai_export_path"
    ) as openai_import:
        response = _post_upload(
            test_client,
            filename="conversations.json",
            content=content,
            content_type="application/json",
        )

    assert response.status_code == 200
    assert response.json()["threads_imported"] == 1
    legacy_import.assert_called_once_with(content, user_id=SERVER_USER_ID)
    claude_import.assert_not_called()
    openai_import.assert_not_called()


def test_claude_json_still_dispatches_to_claude_importer(test_client):
    content = _claude_export()

    with patch(
        "guardian.routes.migration.ingest_chatgpt_export"
    ) as legacy_import, patch(
        "guardian.routes.migration.ingest_claude_export",
        return_value=_stats(threads=1, messages=1),
    ) as claude_import, patch(
        "guardian.routes.migration.import_openai_export_path"
    ) as openai_import:
        response = _post_upload(
            test_client,
            filename="claude.json",
            content=content,
            content_type="application/json",
        )

    assert response.status_code == 200
    assert response.json()["messages_imported"] == 1
    claude_import.assert_called_once_with(content, user_id=SERVER_USER_ID)
    legacy_import.assert_not_called()
    openai_import.assert_not_called()


def test_modern_openai_dat_dispatches_to_openai_export_adapter(test_client):
    content = _sharded_dat_export()

    with patch(
        "guardian.routes.migration.ingest_chatgpt_export"
    ) as legacy_import, patch(
        "guardian.routes.migration.ingest_claude_export"
    ) as claude_import, patch(
        "guardian.routes.migration.import_openai_export_path",
        return_value=_stats(conversation_records=1),
    ) as openai_import:
        response = _post_upload(
            test_client,
            filename="file_0000000000000001.dat",
            content=content,
            content_type="application/octet-stream",
        )

    assert response.status_code == 200
    assert response.json()["messages_imported"] == 2
    openai_import.assert_called_once()
    upload_path = Path(openai_import.call_args.args[0])
    assert upload_path.name == "file_0000000000000001.dat"
    assert openai_import.call_args.kwargs["user_id"] == SERVER_USER_ID
    legacy_import.assert_not_called()
    claude_import.assert_not_called()


def test_unsupported_dat_upload_fails_before_import(test_client):
    with patch(
        "guardian.routes.migration.import_openai_export_path"
    ) as openai_import:
        response = _post_upload(
            test_client,
            filename="file_0000000000000999.dat",
            content=json.dumps({"not": "a conversation"}).encode("utf-8"),
            content_type="application/octet-stream",
        )

    assert response.status_code == 400
    assert "not a readable JSON/JSONL conversation shard" in response.json()[
        "detail"
    ]
    openai_import.assert_not_called()


def test_ambiguous_json_upload_fails_without_guessing_importer(test_client):
    with patch(
        "guardian.routes.migration.ingest_chatgpt_export"
    ) as legacy_import, patch(
        "guardian.routes.migration.ingest_claude_export"
    ) as claude_import, patch(
        "guardian.routes.migration.import_openai_export_path"
    ) as openai_import:
        response = _post_upload(
            test_client,
            filename="unknown.json",
            content=json.dumps({"items": [{"text": "no lineage"}]}).encode(
                "utf-8"
            ),
            content_type="application/json",
        )

    assert response.status_code == 400
    assert "Unsupported or ambiguous migration upload" in response.json()[
        "detail"
    ]
    legacy_import.assert_not_called()
    claude_import.assert_not_called()
    openai_import.assert_not_called()
