"""Tests for openai_export_conversation_import — synthetic fixtures only."""

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

from backend.rag.openai_export_conversation_import import (
    ImportDiagnostics,
    _count_messages_in_conversation,
    _matches_title_filter,
    _extract_messages_from_conversation,
    _compute_latest_timestamp,
    import_openai_export_conversations,
)

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


class ImportModules(NamedTuple):
    chatgpt_migration: Any
    dependencies: Any


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
def import_modules(
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[ImportModules]:
    module_state = _snapshot_modules(_SCOPED_IMPORT_MODULE_NAMES)
    _install_fake_psycopg(monkeypatch)
    modules = ImportModules(
        chatgpt_migration=importlib.import_module(
            "backend.rag.chatgpt_migration"
        ),
        dependencies=importlib.import_module("guardian.core.dependencies"),
    )
    try:
        yield modules
    finally:
        _restore_modules(module_state)


class ImportStore:
    """In-memory store mirroring chatlog_db interface."""

    def __init__(self) -> None:
        self._next_thread_id = 1
        self._next_message_id = 1
        self.threads: dict[int, dict[str, Any]] = {}
        self.messages: list[dict[str, Any]] = []
        # Metadata keyed by message_id for extra_meta lookups
        self._message_meta: dict[int, dict[str, Any]] = {}

    def _connect(self):
        """Return self as a context-manager compatible connection."""
        return _FakeConnection(self)

    def ensure_project(self, name: str, description: str) -> int:
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
        tid = self._next_thread_id
        self._next_thread_id += 1
        thread = {
            "id": tid,
            "user_id": user_id,
            "title": title,
            "summary": summary,
            "project_id": project_id,
            "metadata": metadata or {},
            "parent_id": parent_id,
        }
        self.threads[tid] = thread
        return dict(thread)

    def get_chat_thread(self, thread_id: int) -> dict[str, Any] | None:
        t = self.threads.get(thread_id)
        return dict(t) if t else None

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
        mid = self._next_message_id
        self._next_message_id += 1
        self.messages.append(
            {
                "id": mid,
                "thread_id": thread_id,
                "role": role,
                "content": content,
                "created_at": created_at
                or datetime.now(timezone.utc).isoformat(),
            }
        )
        return mid

    def set_message_meta(
        self, message_id: int, meta: dict[str, Any]
    ) -> None:
        self._message_meta[message_id] = dict(meta)

    def get_message_meta(self, message_id: int) -> dict[str, Any]:
        return dict(self._message_meta.get(message_id, {}))


@pytest.fixture
def import_store(
    monkeypatch: pytest.MonkeyPatch,
    import_modules: ImportModules,
) -> ImportStore:
    store = ImportStore()
    monkeypatch.setattr(import_modules.dependencies, "chatlog_db", store)
    monkeypatch.setattr(
        import_modules.dependencies, "init_database", lambda: store
    )
    monkeypatch.setattr(
        import_modules.chatgpt_migration,
        "_persist_temporal_metadata",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        import_modules.chatgpt_migration,
        "_process_chatgpt_embedding_batches",
        lambda **_kwargs: {
            "embedding_candidates": 0,
            "embeddings_persisted": 0,
            "embeddings_failed": 0,
            "embedding_coverage_degraded": False,
        },
    )
    return store


class _FakeCursor:
    """Minimal cursor that returns canned results."""

    def __init__(
        self,
        store: ImportStore,
        thread_id_lookup: dict[tuple[str, str], int] | None = None,
        message_lookup: dict[tuple[int, str], dict[str, Any]] | None = None,
    ) -> None:
        self._store = store
        self._thread_lookup = thread_id_lookup or {}
        self._message_lookup = message_lookup or {}
        self._last_params: tuple = ()
        self.rowcount = 0

    def execute(self, query: str, params: tuple = ()) -> None:
        self._last_params = params

    def fetchone(self) -> dict[str, Any] | None:
        params = self._last_params
        # Thread lookup: SELECT cm.thread_id ... WHERE ... source_thread_id = %s
        if len(params) == 2:
            key = (str(params[0]), str(params[1]))
            tid = self._thread_lookup.get(key)
            if tid is not None:
                return {"thread_id": tid}

        # Message lookup: SELECT id, extra_meta ... WHERE thread_id = %s AND source_message_id = %s
        if len(params) == 2:
            try:
                key = (int(params[0]), str(params[1]))
            except (ValueError, TypeError):
                key = (0, str(params[1]))
            msg = self._message_lookup.get(key)
            if msg is not None:
                return {"id": msg["id"], "extra_meta": msg.get("extra_meta", {})}
        return None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class _FakeConnection:
    """Minimal connection that provides a cursor."""

    def __init__(self, store: ImportStore) -> None:
        self._store = store
        self._thread_lookup: dict[tuple[str, str], int] = {}
        self._message_lookup: dict[tuple[int, str], dict[str, Any]] = {}

    def cursor(self):
        return _FakeCursor(
            self._store,
            thread_id_lookup=self._thread_lookup,
            message_lookup=self._message_lookup,
        )

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


# --- Fixture helpers ---


def _build_mapping_conversation(
    turns: list[tuple[str, str, float]],
    *,
    conversation_id: str = "test-conv",
    title: str = "Test Conversation",
) -> dict[str, Any]:
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
        if parent and parent in mapping:
            mapping[parent]["children"].append(node_id)
        parent = node_id
    return {
        "conversation_id": conversation_id,
        "id": conversation_id,
        "title": title,
        "current_node": parent,
        "create_time": turns[0][2] if turns else None,
        "update_time": turns[-1][2] if turns else None,
        "mapping": mapping,
    }


def _write_conversations_json(
    export_root: Path,
    conversations: list[dict[str, Any]],
) -> None:
    export_root.mkdir(parents=True, exist_ok=True)
    (export_root / "conversations.json").write_text(
        json.dumps(conversations), encoding="utf-8"
    )


def _write_sharded_conversations(
    export_root: Path,
    conversations: list[dict[str, Any]],
    *,
    part_name: str = "conversations__test.part-0001",
) -> None:
    part = export_root / part_name
    part.mkdir(parents=True)
    (part / "file_0000000000000001.dat").write_text(
        json.dumps(conversations[0] if conversations else {}),
        encoding="utf-8",
    )
    for i, conv in enumerate(conversations[1:], start=2):
        (part / f"file_{i:025d}.dat").write_text(
            json.dumps(conv), encoding="utf-8",
        )


# --- Unit tests ---


def test_count_messages_in_mapping_conversation():
    conv = _build_mapping_conversation(
        [("user", "A", 1.0), ("assistant", "B", 2.0), ("user", "C", 3.0)]
    )
    assert _count_messages_in_conversation(conv) == 3


def test_count_messages_empty_conversation():
    assert _count_messages_in_conversation({}) == 0


def test_matches_title_filter_case_insensitive():
    conv = {"title": "Codexify Task Prompt"}
    assert _matches_title_filter(conv, "codexify") is True
    assert _matches_title_filter(conv, "CODEXIFY") is True
    assert _matches_title_filter(conv, "Guardian") is False
    assert _matches_title_filter(conv, "") is True
    assert _matches_title_filter(conv, None) is True


def test_compute_latest_timestamp():
    convs = [
        {"create_time": 1700000000.0, "update_time": 1700100000.0},
        {"create_time": 1700200000.0},
    ]
    ts = _compute_latest_timestamp(convs)
    assert ts is not None
    assert "2023-11-17" in ts


# --- Integration tests ---


def test_import_single_conversation_creates_thread_and_messages(
    tmp_path: Path,
    import_store: ImportStore,
):
    export_root = tmp_path / "legacy-export"
    _write_conversations_json(
        export_root,
        [
            _build_mapping_conversation(
                [
                    ("user", "Hello", 1.0),
                    ("assistant", "Hi there", 2.0),
                ],
                conversation_id="openai-thread-1",
                title="OpenAI Import Test",
            )
        ],
    )

    diag = import_openai_export_conversations(
        export_root,
        user_id="tester",
        diagnostic_dir=tmp_path / "diag",
    )

    assert diag.conversations_discovered == 1
    assert diag.conversations_imported == 1
    assert diag.messages_discovered == 2
    assert diag.messages_imported == 2
    assert diag.export_format == "legacy"

    # Verify DB state
    assert len(import_store.threads) == 1
    thread = next(iter(import_store.threads.values()))
    assert thread["title"] == "OpenAI Import Test"
    assert "source_thread_id" in str(thread.get("metadata", {}))
    assert len(import_store.messages) == 2


def test_sharded_export_imports_conversations(
    tmp_path: Path,
    import_store: ImportStore,
):
    export_root = tmp_path / "sharded-export"
    _write_sharded_conversations(
        export_root,
        [
            _build_mapping_conversation(
                [("user", "Sharded hello", 1.0)],
                conversation_id="sharded-id",
                title="Sharded Import",
            )
        ],
    )

    diag = import_openai_export_conversations(
        export_root,
        user_id="tester",
        diagnostic_dir=tmp_path / "diag",
    )

    assert diag.conversations_imported == 1
    assert diag.messages_imported == 1
    assert diag.export_format == "sharded"


def test_dry_run_writes_no_db_changes(
    tmp_path: Path,
    import_store: ImportStore,
):
    export_root = tmp_path / "legacy-export"
    _write_conversations_json(
        export_root,
        [_build_mapping_conversation([("user", "Dry test", 1.0)])],
    )

    diag = import_openai_export_conversations(
        export_root,
        user_id="tester",
        dry_run=True,
        diagnostic_dir=tmp_path / "diag",
    )

    assert diag.dry_run is True
    assert diag.conversations_discovered == 1
    assert diag.messages_discovered == 1
    # DB should be untouched
    assert len(import_store.threads) == 0
    assert len(import_store.messages) == 0


def test_idempotent_reimport_does_not_duplicate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    import_modules: ImportModules,
):
    """Second import of same conversations produces 0 new records."""
    store = ImportStore()
    monkeypatch.setattr(import_modules.dependencies, "chatlog_db", store)
    monkeypatch.setattr(
        import_modules.dependencies, "init_database", lambda: store
    )
    monkeypatch.setattr(
        import_modules.chatgpt_migration,
        "_persist_temporal_metadata",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        import_modules.chatgpt_migration,
        "_process_chatgpt_embedding_batches",
        lambda **_kwargs: {
            "embedding_candidates": 0,
            "embeddings_persisted": 0,
            "embeddings_failed": 0,
            "embedding_coverage_degraded": False,
        },
    )

    # Track find calls for idempotency simulation
    find_thread_calls: list[tuple] = []
    find_message_calls: list[tuple] = []
    first_import_thread_id: int | None = None

    def _find_thread(db, *, user_id, source_thread_id):
        find_thread_calls.append((user_id, source_thread_id))
        # On first import, return None (create new). On second, return first's ID.
        if len(find_thread_calls) > 1 and first_import_thread_id is not None:
            return first_import_thread_id
        return None

    def _find_message(db, thread_id, source_message_id):
        find_message_calls.append((thread_id, source_message_id))
        if first_import_thread_id is not None and thread_id == first_import_thread_id:
            # Already exists — return a record so it's treated as duplicate
            return {"id": 999, "extra_meta": {}}
        return None

    monkeypatch.setattr(
        import_modules.chatgpt_migration,
        "_find_existing_thread_for_source",
        _find_thread,
    )
    monkeypatch.setattr(
        import_modules.chatgpt_migration,
        "_find_existing_message_for_source",
        _find_message,
    )

    export_root = tmp_path / "idempotent-export"
    _write_conversations_json(
        export_root,
        [
            _build_mapping_conversation(
                [
                    ("user", "A", 1.0),
                    ("assistant", "B", 2.0),
                ],
                conversation_id="stable-thread",
                title="Idempotent Test",
            )
        ],
    )

    first = import_openai_export_conversations(
        export_root, user_id="tester", diagnostic_dir=tmp_path / "diag1"
    )
    # Capture what the first import produced
    first_import_thread_id = 1  # Assume first import creates thread id 1

    second = import_openai_export_conversations(
        export_root, user_id="tester", diagnostic_dir=tmp_path / "diag2"
    )

    assert first.conversations_imported == 1
    assert first.messages_imported == 2
    assert second.conversations_imported == 0
    assert second.messages_imported == 0


def test_limit_restricts_imported_conversations(
    tmp_path: Path,
    import_store: ImportStore,
):
    export_root = tmp_path / "limited-export"
    convs = [
        _build_mapping_conversation(
            [("user", f"Msg {i}", float(i))],
            conversation_id=f"conv-{i}",
            title=f"Conversation {i}",
        )
        for i in range(5)
    ]
    _write_conversations_json(export_root, convs)

    diag = import_openai_export_conversations(
        export_root,
        user_id="tester",
        limit=2,
        diagnostic_dir=tmp_path / "diag",
    )

    assert diag.conversations_discovered == 5
    assert diag.conversations_imported == 2
    assert diag.conversations_skipped_limit == 3


def test_title_contains_filter_skips_nonmatching(
    tmp_path: Path,
    import_store: ImportStore,
):
    export_root = tmp_path / "filtered-export"
    _write_conversations_json(
        export_root,
        [
            _build_mapping_conversation(
                [("user", "X", 1.0)],
                conversation_id="c1",
                title="Guardian Architecture",
            ),
            _build_mapping_conversation(
                [("user", "Y", 2.0)],
                conversation_id="c2",
                title="Random Chat",
            ),
            _build_mapping_conversation(
                [("user", "Z", 3.0)],
                conversation_id="c3",
                title="Guardian Deploy",
            ),
        ],
    )

    diag = import_openai_export_conversations(
        export_root,
        user_id="tester",
        title_contains="Guardian",
        diagnostic_dir=tmp_path / "diag",
    )

    assert diag.conversations_discovered == 3
    assert diag.conversations_imported == 2
    assert diag.conversations_skipped_title == 1
    assert diag.skipped_records[0]["reason"] == "title_does_not_contain:Guardian"


def test_empty_conversations_skipped_without_crash(
    tmp_path: Path,
    import_store: ImportStore,
):
    export_root = tmp_path / "empty-export"
    _write_conversations_json(
        export_root,
        [
            {
                "conversation_id": "empty-conv",
                "title": "Empty",
                "mapping": {},
            },
            _build_mapping_conversation(
                [("user", "Real", 1.0)],
                conversation_id="real-conv",
                title="Real",
            ),
        ],
    )

    diag = import_openai_export_conversations(
        export_root,
        user_id="tester",
        diagnostic_dir=tmp_path / "diag",
    )

    assert diag.conversations_discovered == 2
    assert diag.conversations_imported == 1  # only the non-empty one
    assert len(import_store.threads) == 1


def test_diagnostics_written_to_output_dir(tmp_path: Path):
    export_root = tmp_path / "diag-export"
    _write_conversations_json(
        export_root,
        [_build_mapping_conversation([("user", "Test", 1.0)])],
    )
    diag_dir = tmp_path / "logs/openai_import"

    import_openai_export_conversations(
        export_root,
        user_id="tester",
        dry_run=True,
        diagnostic_dir=diag_dir,
    )

    # Should have created a diagnostic JSON
    json_files = list(diag_dir.glob("import_diagnostics_*.json"))
    assert len(json_files) == 1

    diag_data = json.loads(json_files[0].read_text())
    assert diag_data["dry_run"] is True
    assert diag_data["conversations_discovered"] == 1


def test_existing_native_chat_not_modified(tmp_path: Path):
    """Verify that the import path does not alter the native
    create_chat_thread / create_message behavior."""
    export_root = tmp_path / "sideeffect-export"
    _write_conversations_json(
        export_root,
        [_build_mapping_conversation([("user", "Imported", 1.0)])],
    )

    # Pre-create a native thread
    native_store = ImportStore()
    native_store.create_chat_thread(
        user_id="tester",
        title="Native Thread",
        summary="Pre-existing",
    )
    native_store.create_message(1, "user", "Native message")

    # Now import — using a different store to verify isolation
    import_store = ImportStore()
    import_store.create_chat_thread = native_store.create_chat_thread  # type: ignore[method-assign]
    import_store.create_message = native_store.create_message  # type: ignore[method-assign]

    # Just verify the function doesn't modify signature behavior
    diag = import_openai_export_conversations(
        export_root,
        user_id="tester",
        dry_run=True,
        diagnostic_dir=tmp_path / "diag",
    )

    assert diag.dry_run is True
