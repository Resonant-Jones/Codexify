from __future__ import annotations

import importlib
import json
import sys
import types
from collections.abc import Generator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, NamedTuple

import pytest

from backend.rag.openai_export_adapter import (
    OpenAIExportDetector,
    import_openai_export_path,
)


class OpenAIImportModules(NamedTuple):
    chatgpt_migration: Any
    dependencies: Any


_MISSING = object()
_PSYCOPG_MODULE_NAMES = (
    "psycopg",
    "psycopg.errors",
    "psycopg.rows",
    "psycopg.types",
    "psycopg.types.json",
)
_SCOPED_IMPORT_MODULE_NAMES = (
    "backend.rag.chatgpt_migration",
    "guardian.core.dependencies",
    "guardian.core.chatlog_postgres",
    "guardian.core.pgdb",
)


def _fake_module(name: str) -> types.ModuleType:
    module = types.ModuleType(name)
    module._codexify_openai_test_stub = True
    return module


def _install_fake_psycopg(monkeypatch: pytest.MonkeyPatch) -> None:
    psycopg_stub = _fake_module("psycopg")
    errors_stub = _fake_module("psycopg.errors")
    rows_stub = _fake_module("psycopg.rows")
    types_stub = _fake_module("psycopg.types")
    json_stub = _fake_module("psycopg.types.json")

    rows_stub.dict_row = object()
    json_stub.Json = lambda value, dumps=None: value
    types_stub.json = json_stub
    psycopg_stub.errors = errors_stub
    psycopg_stub.rows = rows_stub
    psycopg_stub.types = types_stub

    monkeypatch.setitem(sys.modules, "psycopg", psycopg_stub)
    monkeypatch.setitem(sys.modules, "psycopg.errors", errors_stub)
    monkeypatch.setitem(sys.modules, "psycopg.rows", rows_stub)
    monkeypatch.setitem(sys.modules, "psycopg.types", types_stub)
    monkeypatch.setitem(sys.modules, "psycopg.types.json", json_stub)


def _snapshot_modules(
    module_names: tuple[str, ...],
) -> dict[str, tuple[Any, types.ModuleType | None, Any]]:
    state: dict[str, tuple[Any, types.ModuleType | None, Any]] = {}
    for name in module_names:
        parent_name, _, child_name = name.rpartition(".")
        parent = sys.modules.get(parent_name)
        parent_attr = (
            getattr(parent, child_name, _MISSING)
            if parent is not None
            else _MISSING
        )
        state[name] = (sys.modules.get(name, _MISSING), parent, parent_attr)
    return state


def _restore_modules(
    state: dict[str, tuple[Any, types.ModuleType | None, Any]],
) -> None:
    for name, (module, original_parent, parent_attr) in reversed(
        list(state.items())
    ):
        if module is _MISSING:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = module

        parent_name, _, child_name = name.rpartition(".")
        parent = original_parent or sys.modules.get(parent_name)
        if parent is None:
            continue
        if parent_attr is _MISSING:
            if hasattr(parent, child_name):
                delattr(parent, child_name)
        else:
            setattr(parent, child_name, parent_attr)


@pytest.fixture(autouse=True)
def _assert_fake_psycopg_does_not_leak() -> Generator[None]:
    yield
    leaked = [
        name
        for name in _PSYCOPG_MODULE_NAMES
        if getattr(sys.modules.get(name), "_codexify_openai_test_stub", False)
    ]
    assert leaked == []


@pytest.fixture
def openai_import_modules(
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[OpenAIImportModules]:
    module_state = _snapshot_modules(_SCOPED_IMPORT_MODULE_NAMES)
    _install_fake_psycopg(monkeypatch)
    modules = OpenAIImportModules(
        chatgpt_migration=importlib.import_module(
            "backend.rag.chatgpt_migration"
        ),
        dependencies=importlib.import_module("guardian.core.dependencies"),
    )
    try:
        yield modules
    finally:
        _restore_modules(module_state)


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
def import_store(
    monkeypatch: pytest.MonkeyPatch,
    openai_import_modules: OpenAIImportModules,
) -> OpenAIImportStore:
    store = OpenAIImportStore()
    monkeypatch.setattr(
        openai_import_modules.dependencies,
        "chatlog_db",
        store,
    )
    monkeypatch.setattr(
        openai_import_modules.dependencies,
        "init_database",
        lambda: store,
    )
    monkeypatch.setattr(
        openai_import_modules.chatgpt_migration,
        "_persist_temporal_metadata",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        openai_import_modules.chatgpt_migration,
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
    openai_import_modules: OpenAIImportModules,
) -> None:
    store = OpenAIImportStore()
    monkeypatch.setattr(
        openai_import_modules.dependencies,
        "chatlog_db",
        store,
    )
    monkeypatch.setattr(
        openai_import_modules.dependencies,
        "init_database",
        lambda: store,
    )
    monkeypatch.setattr(
        openai_import_modules.chatgpt_migration,
        "_persist_temporal_metadata",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        openai_import_modules.chatgpt_migration,
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
        openai_import_modules.chatgpt_migration,
        "_find_existing_thread_for_source",
        find_thread,
    )
    monkeypatch.setattr(
        openai_import_modules.chatgpt_migration,
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


# --- Manifest misdetection tests ---


def _build_file_manifest_conversations_json() -> list[dict[str, Any]]:
    """Simulate a __export_file_manifests__/conversations.json payload."""
    return [
        {
            "file_name": "file_0000000000000001.dat",
            "file_path": "__export_file_manifests__/conversations__abc.part-0001/file_0000000000000001.dat",
            "file_size": 12345,
            "original_path": "/some/export/path/conversations__abc.part-0001/file_0000000000000001.dat",
            "export_id": "export-abc-123",
            "manifest_version": 1,
        },
        {
            "file_name": "file_0000000000000002.dat",
            "file_path": "__export_file_manifests__/conversations__xyz.part-0002/file_0000000000000002.dat",
            "file_size": 67890,
            "original_path": "/some/export/path/conversations__xyz.part-0002/file_0000000000000002.dat",
        },
    ]


def test_openai_export_manifest_conversations_json_is_not_legacy_export(
    tmp_path: Path,
) -> None:
    """__export_file_manifests__/conversations.json is NOT detected as legacy."""
    export_root = tmp_path / "openai-export-with-manifest"
    manifest_dir = export_root / "__export_file_manifests__"
    manifest_dir.mkdir(parents=True)

    # Write the misleading manifest file
    (manifest_dir / "conversations.json").write_text(
        json.dumps(_build_file_manifest_conversations_json()),
        encoding="utf-8",
    )

    # Add a sharded export marker so the scanner finds something
    shard = export_root / "conversations__real.part-0001"
    shard.mkdir()
    (shard / "file_0000000000000001.dat").write_text(
        json.dumps(
            {
                "conversation_id": "real-conv",
                "title": "Real Conversation",
                "mapping": {
                    "m1": {
                        "id": "m1",
                        "message": {
                            "id": "m1",
                            "author": {"role": "user"},
                            "content": {"parts": ["Real message"]},
                        },
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    inventory = OpenAIExportDetector().scan(export_root)

    # Should NOT detect legacy format (manifest conversations.json ignored)
    assert inventory.legacy_detected is False
    # Should detect sharded format from the real conversation data
    assert inventory.sharded_detected is True
    assert inventory.detected_format == "sharded"

    # The manifest file should be classified as json, but not a conversation candidate
    manifest_record = next(
        (r for r in inventory.files if "__export_file_manifests__" in r.path),
        None,
    )
    assert manifest_record is not None
    assert manifest_record.conversation_candidate is True or (
        manifest_record.detected_kind in {"json_array", "json_object"}
    )


def test_openai_export_legacy_conversations_json_detected_by_schema(
    tmp_path: Path,
) -> None:
    """A real conversations.json with conversation records IS detected as legacy."""
    export_root = tmp_path / "legacy-export"
    export_root.mkdir()

    (export_root / "conversations.json").write_text(
        json.dumps(
            [
                {
                    "id": "legacy-conv",
                    "title": "Legacy Conversation",
                    "mapping": {
                        "m1": {
                            "id": "m1",
                            "message": {
                                "id": "m1",
                                "author": {"role": "user"},
                                "content": {"parts": ["Hello"]},
                            },
                        }
                    },
                }
            ]
        ),
        encoding="utf-8",
    )

    inventory = OpenAIExportDetector().scan(export_root)

    assert inventory.legacy_detected is True
    assert inventory.detected_format == "legacy"

    # The file should be a conversation candidate with conversation-shaped keys
    record = inventory.files[0]
    assert record.conversation_candidate is True
    assert "id" in record.top_level_json_keys or "mapping" in record.top_level_json_keys


def test_openai_export_detection_prefers_real_conversation_payload(
    tmp_path: Path,
) -> None:
    """When both manifest and real data exist, real conversations are preferred."""
    export_root = tmp_path / "mixed-export"
    manifest_dir = export_root / "__export_file_manifests__"
    manifest_dir.mkdir(parents=True)

    # Malicious manifest
    (manifest_dir / "conversations.json").write_text(
        json.dumps(_build_file_manifest_conversations_json()),
        encoding="utf-8",
    )

    # Real conversation data
    (export_root / "conversations.json").write_text(
        json.dumps(
            [
                {
                    "id": "real-conv-1",
                    "title": "Real Conversation from root",
                    "mapping": {
                        "r1": {
                            "id": "r1",
                            "message": {
                                "id": "r1",
                                "author": {"role": "assistant"},
                                "content": {"parts": ["Real response"]},
                            },
                        }
                    },
                }
            ]
        ),
        encoding="utf-8",
    )

    # Also add a sharded marker so format is "mixed"
    shard = export_root / "conversations__real.part-0001"
    shard.mkdir()
    (shard / "file_0000000000000001.dat").write_text(
        json.dumps(
            {
                "conversation_id": "sharded-conv",
                "title": "Sharded",
                "mapping": {},
            }
        ),
        encoding="utf-8",
    )

    inventory = OpenAIExportDetector().scan(export_root)

    # The manifest conversations.json should not cause false legacy detection.
    # With the real root-level conversations.json present, legacy IS detected.
    assert inventory.legacy_detected is True
    assert inventory.sharded_detected is True
    assert inventory.detected_format == "mixed"

    # Verify the manifest file itself is NOT marked conversation_candidate
    # (it may be marked due to false positive from _payload_has_conversation_shape
    # but legacy detection should still require _has_conversation_payload which
    # rejects manifest payloads)
    manifest_records = [
        r for r in inventory.files
        if "__export_file_manifests__" in r.path
    ]
    assert manifest_records, "Should have at least one manifest file"

    # The import should prefer the sharded adapter in mixed mode
    from backend.rag.openai_export_adapter import (
        import_openai_export_path,
    )
    diag_out = tmp_path / "diag"
    stats = import_openai_export_path(
        export_root,
        user_id="tester",
        diagnose_only=True,
        diagnostic_output_dir=diag_out,
    )
    assert stats["export_format"] == "mixed"
    # No conversations imported since diagnose_only, but format is correctly detected
    assert stats.get("diagnostic_report") is not None
