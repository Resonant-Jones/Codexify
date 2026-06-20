from __future__ import annotations

import json
import sys
import types
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

_numpy_stub = types.ModuleType("numpy")
_numpy_stub.ndarray = object
sys.modules.setdefault("numpy", _numpy_stub)

_psycopg_stub = types.ModuleType("psycopg")
_psycopg_stub.connect = lambda *_args, **_kwargs: None
_psycopg_errors_stub = types.ModuleType("psycopg.errors")
_psycopg_rows_stub = types.ModuleType("psycopg.rows")
_psycopg_rows_stub.dict_row = object()
_psycopg_types_stub = types.ModuleType("psycopg.types")
_psycopg_json_stub = types.ModuleType("psycopg.types.json")
_psycopg_json_stub.Json = lambda value, dumps=None: value
_psycopg_stub.errors = _psycopg_errors_stub
sys.modules.setdefault("psycopg", _psycopg_stub)
sys.modules.setdefault("psycopg.errors", _psycopg_errors_stub)
sys.modules.setdefault("psycopg.rows", _psycopg_rows_stub)
sys.modules.setdefault("psycopg.types", _psycopg_types_stub)
sys.modules.setdefault("psycopg.types.json", _psycopg_json_stub)

from backend.rag import chatgpt_migration
from backend.rag.openai_export_adapter import (
    OpenAIExportDetector,
    import_openai_export_path,
)
from guardian.core import dependencies


def _build_mainline_export(
    turns: list[tuple[str, str, float]],
    *,
    thread_id: str = "legacy-thread",
    title: str = "Legacy Import",
) -> list[dict[str, Any]]:
    mapping: dict[str, dict[str, Any]] = {}
    parent: str | None = None
    for idx, (role, text, create_time) in enumerate(turns, start=1):
        node_id = f"m{idx}"
        mapping[node_id] = {
            "id": node_id,
            "parent": parent,
            "children": [],
            "message": {
                "id": node_id,
                "author": {"role": role},
                "content": {"content_type": "text", "parts": [text]},
                "create_time": create_time,
            },
        }
        if parent:
            mapping[parent]["children"].append(node_id)
        parent = node_id
    return [
        {
            "id": thread_id,
            "title": title,
            "current_node": parent,
            "mapping": mapping,
        }
    ]


class OpenAIImportStore:
    def __init__(self) -> None:
        self._next_thread_id = 1
        self._next_message_id = 1
        self.threads: dict[int, dict[str, Any]] = {}
        self.messages: list[dict[str, Any]] = []

    def ensure_project(self, name: str, description: str) -> int:
        _ = name, description
        return 1

    def list_projects(self) -> list[dict[str, Any]]:
        return [{"id": 1, "name": "Imports"}]

    def create_chat_thread(
        self,
        *,
        user_id: str,
        title: str,
        summary: str = "",
        project_id: int | None = None,
        metadata: dict[str, Any] | None = None,
        parent_id: int | None = None,
    ) -> dict[str, Any]:
        thread_id = self._next_thread_id
        self._next_thread_id += 1
        thread = {
            "id": thread_id,
            "user_id": user_id,
            "title": title,
            "summary": summary,
            "project_id": project_id,
            "metadata": metadata or {},
            "parent_id": parent_id,
        }
        self.threads[thread_id] = thread
        return dict(thread)

    def get_chat_thread(self, thread_id: int) -> dict[str, Any] | None:
        thread = self.threads.get(thread_id)
        return dict(thread) if thread else None

    def update_thread_metadata(
        self, thread_id: int, metadata: dict[str, Any]
    ) -> bool:
        if thread_id not in self.threads:
            return False
        self.threads[thread_id]["metadata"] = dict(metadata)
        return True

    def create_message(
        self,
        thread_id: int,
        role: str,
        content: str,
        created_at: str | None = None,
    ) -> int:
        message_id = self._next_message_id
        self._next_message_id += 1
        self.messages.append(
            {
                "id": message_id,
                "thread_id": thread_id,
                "role": role,
                "content": content,
                "created_at": created_at
                or datetime.now(timezone.utc).isoformat(),
            }
        )
        return message_id


@pytest.fixture
def import_store(monkeypatch: pytest.MonkeyPatch) -> OpenAIImportStore:
    store = OpenAIImportStore()
    monkeypatch.setattr(dependencies, "chatlog_db", store)
    monkeypatch.setattr(dependencies, "init_database", lambda: store)
    monkeypatch.setattr(
        chatgpt_migration,
        "_persist_temporal_metadata",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        chatgpt_migration,
        "_process_chatgpt_embedding_batches",
        lambda **_kwargs: {
            "embedding_candidates": 0,
            "embeddings_persisted": 0,
            "embeddings_failed": 0,
            "embedding_coverage_degraded": False,
        },
    )
    return store


def test_legacy_export_folder_imports_conversations_json(
    tmp_path: Path,
    import_store: OpenAIImportStore,
) -> None:
    export_root = tmp_path / "legacy-export"
    export_root.mkdir()
    (export_root / "conversations.json").write_text(
        json.dumps(
            _build_mainline_export(
                [("user", "Legacy hello", 1), ("assistant", "Legacy hi", 2)]
            )
        ),
        encoding="utf-8",
    )

    stats = import_openai_export_path(
        export_root,
        user_id="tester",
        diagnostic_output_dir=tmp_path / "diagnostics",
    )

    assert stats["export_format"] == "legacy"
    assert stats["threads_imported"] == 1
    assert stats["messages_imported"] == 2
    assert Path(str(stats["diagnostic_report"])).exists()
    assert len(import_store.threads) == 1
    assert len(import_store.messages) == 2


def test_sharded_dat_json_imports_message_container(
    tmp_path: Path,
    import_store: OpenAIImportStore,
) -> None:
    export_root = tmp_path / "openai-export"
    part = export_root / "conversations__abcd.part-0001"
    part.mkdir(parents=True)
    (part / "file_0000000000000001.dat").write_text(
        json.dumps(
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
        ),
        encoding="utf-8",
    )

    stats = import_openai_export_path(export_root, user_id="tester")

    assert stats["export_format"] == "sharded"
    assert stats["conversation_records"] == 1
    assert stats["threads_imported"] == 1
    assert stats["messages_imported"] == 2
    thread = next(iter(import_store.threads.values()))
    assert thread["metadata"]["openai_export_format"] == "sharded"
    assert "conversations__abcd.part-0001" in thread["metadata"][
        "openai_export_source_path"
    ]


def test_sharded_dat_jsonl_groups_per_message_records(
    tmp_path: Path,
    import_store: OpenAIImportStore,
) -> None:
    export_root = tmp_path / "jsonl-export"
    part = export_root / "conversations__efgh.part-0002"
    part.mkdir(parents=True)
    lines = [
        {
            "conversation_id": "jsonl-thread",
            "message_id": "m1",
            "role": "user",
            "content": "JSONL hello",
            "create_time": 1,
        },
        {
            "conversation_id": "jsonl-thread",
            "message_id": "m2",
            "role": "assistant",
            "content": "JSONL hi",
            "create_time": 2,
        },
    ]
    (part / "file_0000000000000002.dat").write_text(
        "\n".join(json.dumps(line) for line in lines),
        encoding="utf-8",
    )

    inventory = OpenAIExportDetector().scan(export_root)
    record = inventory.files[0]
    assert record.detected_kind == "jsonl"
    assert record.parse_success is True
    assert "conversation_id" in record.top_level_json_keys

    stats = import_openai_export_path(export_root, user_id="tester")

    assert stats["threads_imported"] == 1
    assert stats["messages_imported"] == 2
    assert [message["content"] for message in import_store.messages] == [
        "JSONL hello",
        "JSONL hi",
    ]


def test_binary_and_unknown_dat_are_orphan_assets_without_crashing(
    tmp_path: Path,
    import_store: OpenAIImportStore,
) -> None:
    _ = import_store
    export_root = tmp_path / "asset-export"
    workspace = export_root / "workspace 2"
    unassigned = export_root / "Unassigned"
    workspace.mkdir(parents=True)
    unassigned.mkdir()
    (workspace / "file_0000000000000003.dat").write_bytes(
        b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
    )
    (unassigned / "file_0000000000000004.dat").write_bytes(b"\x00\x01opaque")

    stats = import_openai_export_path(
        export_root,
        user_id="tester",
        diagnose_only=True,
        diagnostic_output_dir=tmp_path / "diagnostics",
    )

    assert stats["export_format"] == "sharded"
    assert stats["threads_imported"] == 0
    assert stats["messages_imported"] == 0
    assert stats["orphaned_export_assets"] == 2

    diagnostic = json.loads(Path(str(stats["diagnostic_report"])).read_text())
    kinds = {item["detected_kind"] for item in diagnostic["files"]}
    assert {"image_png", "unknown_binary"} <= kinds


def test_mixed_export_writes_diagnostic_report(tmp_path: Path) -> None:
    export_root = tmp_path / "mixed-export"
    part = export_root / "conversations__mixed.part-0001"
    workspace = export_root / "workspace"
    part.mkdir(parents=True)
    workspace.mkdir()
    (export_root / "conversations.json").write_text(
        json.dumps(_build_mainline_export([("user", "Legacy", 1)])),
        encoding="utf-8",
    )
    (export_root / "report.html").write_text("<html>report</html>")
    (part / "file_0000000000000005.dat").write_text(
        json.dumps({"title": "Candidate", "mapping": {}}),
        encoding="utf-8",
    )
    (workspace / "file_0000000000000006.dat").write_bytes(b"GIF89a123")

    stats = import_openai_export_path(
        export_root,
        user_id="tester",
        diagnose_only=True,
        diagnostic_output_dir=tmp_path / "diagnostics",
    )
    diagnostic_path = Path(str(stats["diagnostic_report"]))
    summary_path = Path(str(stats["diagnostic_summary"]))

    assert stats["export_format"] == "mixed"
    assert diagnostic_path.exists()
    assert summary_path.exists()
    payload = json.loads(diagnostic_path.read_text())
    assert payload["detected_format"] == "mixed"
    conversations_file = next(
        item for item in payload["files"] if item["path"] == "conversations.json"
    )
    assert conversations_file["detected_kind"] == "json_array"
    assert conversations_file["parse_success"] is True
    assert "mapping" in conversations_file["top_level_json_keys"]


def test_sharded_import_is_idempotent_on_reimport(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = OpenAIImportStore()
    monkeypatch.setattr(dependencies, "chatlog_db", store)
    monkeypatch.setattr(dependencies, "init_database", lambda: store)
    monkeypatch.setattr(
        chatgpt_migration,
        "_persist_temporal_metadata",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        chatgpt_migration,
        "_process_chatgpt_embedding_batches",
        lambda **_kwargs: {
            "embedding_candidates": 0,
            "embeddings_persisted": 0,
            "embeddings_failed": 0,
            "embedding_coverage_degraded": False,
        },
    )

    source_to_thread: dict[str, int] = {}
    source_to_message: dict[tuple[int, str], int] = {}
    last_message_source = {"value": ""}

    def find_thread(_db, user_id, source_thread_id):
        _ = user_id
        return source_to_thread.get(source_thread_id)

    def find_message(_db, thread_id, source_message_id):
        last_message_source["value"] = source_message_id
        message_id = source_to_message.get((thread_id, source_message_id))
        if message_id is None:
            return None
        return {"id": message_id, "extra_meta": {}}

    original_create_thread = store.create_chat_thread
    original_create_message = store.create_message

    def create_thread(**kwargs):
        thread = original_create_thread(**kwargs)
        metadata = kwargs.get("metadata") or {}
        source_to_thread[str(metadata["source_thread_id"])] = int(thread["id"])
        return thread

    def create_message(thread_id, role, content, created_at=None):
        message_id = original_create_message(
            thread_id, role, content, created_at=created_at
        )
        source_to_message[(thread_id, last_message_source["value"])] = message_id
        return message_id

    store.create_chat_thread = create_thread  # type: ignore[method-assign]
    store.create_message = create_message  # type: ignore[method-assign]
    monkeypatch.setattr(
        chatgpt_migration,
        "_find_existing_thread_for_source",
        find_thread,
    )
    monkeypatch.setattr(
        chatgpt_migration,
        "_find_existing_message_for_source",
        find_message,
    )

    export_root = tmp_path / "idempotent-export"
    part = export_root / "conversations__idem.part-0001"
    part.mkdir(parents=True)
    (part / "file_0000000000000007.dat").write_text(
        json.dumps(
            {
                "conversation_id": "stable-thread",
                "title": "Stable",
                "messages": [
                    {"message_id": "stable-1", "role": "user", "content": "A"},
                    {
                        "message_id": "stable-2",
                        "role": "assistant",
                        "content": "B",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    first = import_openai_export_path(export_root, user_id="tester")
    second = import_openai_export_path(export_root, user_id="tester")

    assert first["threads_imported"] == 1
    assert first["messages_imported"] == 2
    assert second["threads_imported"] == 0
    assert second["messages_imported"] == 0
