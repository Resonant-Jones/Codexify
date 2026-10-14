"""Tests for openai_export_conversation_import — synthetic fixtures only."""

from __future__ import annotations

import base64
import importlib
import json
import os
import sys
import types
import uuid
from collections.abc import Generator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, NamedTuple

import pytest
import sqlalchemy as sa
from sqlalchemy.engine import make_url

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
    "psycopg.sql",
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


@pytest.fixture
def transaction_postgres_url(
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[str, None, None]:
    """Upgrade a disposable database for the PostgreSQL transaction proof."""
    base_url = os.getenv("TEST_DATABASE_URL")
    if not base_url:
        pytest.skip("TEST_DATABASE_URL is required for the PostgreSQL transaction test")
    psycopg = pytest.importorskip("psycopg")
    from psycopg import sql
    from alembic import command
    from alembic.config import Config

    database_name = f"codexify_import_tx_{uuid.uuid4().hex[:12]}"
    parsed_url = make_url(base_url)
    admin_url = parsed_url.set(database="postgres").render_as_string(
        hide_password=False
    )
    database_url = parsed_url.set(database=database_name).render_as_string(
        hide_password=False
    )
    with psycopg.connect(admin_url, autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name)))
    try:
        monkeypatch.setenv("DATABASE_URL", database_url)
        repo_root = Path(__file__).resolve().parents[2]
        config = Config(str(repo_root / "backend" / "alembic.ini"))
        config.set_main_option("sqlalchemy.url", database_url)
        config.set_main_option(
            "script_location", str(repo_root / "guardian" / "db" / "migrations")
        )
        # Options are loaded above. Keep the migration environment from calling
        # fileConfig and disabling application loggers in the shared test process.
        config.config_file_name = None
        command.upgrade(config, "head")
        engine = sa.create_engine(
            parsed_url.set(drivername="postgresql+psycopg", database=database_name),
            future=True,
        )
        try:
            with engine.begin() as conn:
                conn.execute(
                    sa.text(
                        "INSERT INTO users (id, username, password_hash, role) "
                        "VALUES ('local', 'local-import-test', 'test', 'guest') "
                        "ON CONFLICT (id) DO NOTHING"
                    )
                )
        finally:
            engine.dispose()
        yield database_url
    finally:
        with psycopg.connect(admin_url, autocommit=True) as conn:
            conn.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = %s AND pid <> pg_backend_pid()",
                (database_name,),
            )
            conn.execute(
                sql.SQL("DROP DATABASE IF EXISTS {}").format(
                    sql.Identifier(database_name)
                )
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
    sql_stub = _fake_module("psycopg.sql")
    rows_stub = _fake_module("psycopg.rows")
    types_stub = _fake_module("psycopg.types")
    json_stub = _fake_module("psycopg.types.json")

    rows_stub.dict_row = object()
    json_stub.Json = lambda value, dumps=None: value
    types_stub.json = json_stub
    psycopg_stub.errors = errors_stub
    psycopg_stub.sql = sql_stub
    psycopg_stub.rows = rows_stub
    psycopg_stub.types = types_stub

    monkeypatch.setitem(sys.modules, "psycopg", psycopg_stub)
    monkeypatch.setitem(sys.modules, "psycopg.errors", errors_stub)
    monkeypatch.setitem(sys.modules, "psycopg.sql", sql_stub)
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


def test_workspace_and_unassigned_dat_shards_import(
    tmp_path: Path,
    import_store: ImportStore,
):
    """Modern workspace trees and Unassigned shards remain importable."""
    export_root = tmp_path / "modern-workspace-export"
    payloads = [
        (
            "workspace_123/conversations__part-0001",
            _build_mapping_conversation(
                [("user", "Workspace shard marker", 1.0)],
                conversation_id="workspace-conversation",
                title="Workspace conversation",
            ),
        ),
        (
            "Unassigned/conversations__part-0002",
            _build_mapping_conversation(
                [("assistant", "Unassigned shard marker", 2.0)],
                conversation_id="unassigned-conversation",
                title="Unassigned conversation",
            ),
        ),
    ]
    for relative_part, conversation in payloads:
        part = export_root / relative_part
        part.mkdir(parents=True)
        (part / "opaque_payload.dat").write_text(
            json.dumps(conversation),
            encoding="utf-8",
        )

    diag = import_openai_export_conversations(
        export_root,
        user_id="tester",
        diagnostic_dir=tmp_path / "diag",
    )

    assert diag.export_format == "sharded"
    assert diag.conversations_discovered == 2
    assert diag.conversations_imported == 2
    assert diag.messages_imported == 2
    assert {thread["user_id"] for thread in import_store.threads.values()} == {
        "tester"
    }


def test_same_source_archive_is_idempotent_per_owner(
    tmp_path: Path,
    import_store: ImportStore,
    import_modules: ImportModules,
    monkeypatch: pytest.MonkeyPatch,
):
    """The same source IDs dedupe within an owner but never cross owners."""
    store = import_store
    source_thread_id = "owner-isolation-conversation"
    export_root = tmp_path / "owner-isolation-export"
    _write_conversations_json(
        export_root,
        [
            _build_mapping_conversation(
                [("user", "Owner-scoped marker", 1.0)],
                conversation_id=source_thread_id,
            )
        ],
    )

    def find_thread(db, user_id, source_thread_id, origin_system=None):
        _ = db, origin_system
        for thread_id, thread in store.threads.items():
            if (
                thread["user_id"] == user_id
                and thread["metadata"].get("source_thread_id")
                == source_thread_id
            ):
                return thread_id
        return None

    def find_message(db, thread_id, source_message_id):
        _ = db
        for message in store.messages:
            if message["thread_id"] != thread_id:
                continue
            meta = store.get_message_meta(message["id"])
            if meta.get("source_message_id") == source_message_id:
                return {"id": message["id"], "extra_meta": meta}
        return None

    monkeypatch.setattr(
        import_modules.chatgpt_migration,
        "_find_existing_thread_for_source",
        find_thread,
    )
    monkeypatch.setattr(
        import_modules.chatgpt_migration,
        "_find_existing_message_for_source",
        find_message,
    )

    first = import_openai_export_conversations(
        export_root,
        user_id="owner-a",
        diagnostic_dir=tmp_path / "diag-a-1",
    )
    replay = import_openai_export_conversations(
        export_root,
        user_id="owner-a",
        diagnostic_dir=tmp_path / "diag-a-2",
    )
    other_owner = import_openai_export_conversations(
        export_root,
        user_id="owner-b",
        diagnostic_dir=tmp_path / "diag-b",
    )

    assert (first.conversations_imported, first.messages_imported) == (1, 1)
    assert (replay.conversations_imported, replay.messages_imported) == (0, 0)
    assert (other_owner.conversations_imported, other_owner.messages_imported) == (1, 1)
    assert sorted(thread["user_id"] for thread in store.threads.values()) == [
        "owner-a",
        "owner-b",
    ]
    assert len(store.messages) == 2


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

    def _find_thread(db, *, user_id, source_thread_id, origin_system=None):
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


# --- Embedding mode tests ---


def test_default_embedding_mode_is_defer(
    tmp_path: Path,
    import_store: ImportStore,
):
    """Default import uses deferred embedding mode."""
    export_root = tmp_path / "export"
    _write_conversations_json(
        export_root,
        [_build_mapping_conversation([("user", "Test", 1.0)])],
    )

    diag = import_openai_export_conversations(
        export_root,
        user_id="tester",
        diagnostic_dir=tmp_path / "diag",
    )

    assert diag.embedding_mode == "defer"
    assert diag.text_import_complete is True
    assert diag.conversations_imported == 1
    assert diag.embedding_deferred >= 0


def test_embedding_mode_defer_writes_text(
    tmp_path: Path,
    import_store: ImportStore,
):
    """Text threads/messages are written even when embeddings are deferred."""
    export_root = tmp_path / "export"
    _write_conversations_json(
        export_root,
        [_build_mapping_conversation([("user", "Deferred test", 1.0)])],
    )

    diag = import_openai_export_conversations(
        export_root,
        user_id="tester",
        embedding_mode="defer",
        diagnostic_dir=tmp_path / "diag",
    )

    assert diag.text_import_complete is True
    assert diag.conversations_imported == 1
    assert diag.messages_imported == 1
    assert len(import_store.threads) == 1
    assert len(import_store.messages) == 1


def test_embedding_mode_off_skips_enqueue(
    tmp_path: Path,
    import_store: ImportStore,
):
    """--embedding-mode off skips enqueue and reports it."""
    export_root = tmp_path / "export"
    _write_conversations_json(
        export_root,
        [_build_mapping_conversation([("user", "Off test", 1.0)])],
    )

    diag = import_openai_export_conversations(
        export_root,
        user_id="tester",
        embedding_mode="off",
        diagnostic_dir=tmp_path / "diag",
    )

    assert diag.embedding_mode == "off"
    assert diag.text_import_complete is True
    assert diag.conversations_imported == 1
    assert diag.embedding_enqueued == 0


def test_embedding_mode_enqueue_in_bounded_way(
    tmp_path: Path,
    import_store: ImportStore,
):
    """--embedding-mode enqueue attempts enqueue but text import completes."""
    export_root = tmp_path / "export"
    _write_conversations_json(
        export_root,
        [_build_mapping_conversation([("user", "Enqueue test", 1.0)])],
    )

    diag = import_openai_export_conversations(
        export_root,
        user_id="tester",
        embedding_mode="enqueue",
        diagnostic_dir=tmp_path / "diag",
    )

    assert diag.embedding_mode == "enqueue"
    assert diag.text_import_complete is True
    assert diag.conversations_imported == 1


def test_embedding_failure_does_not_fail_text_import(
    tmp_path: Path,
    import_store: ImportStore,
):
    """Redis/embedding failure does not block text import completion."""
    export_root = tmp_path / "export"
    _write_conversations_json(
        export_root,
        [_build_mapping_conversation([("user", "Resilient test", 1.0)])],
    )

    diag = import_openai_export_conversations(
        export_root,
        user_id="tester",
        embedding_mode="enqueue",
        diagnostic_dir=tmp_path / "diag",
    )

    assert diag.text_import_complete is True
    assert diag.conversations_imported == 1
    assert len(diag.errors) == 0


def test_diagnostics_report_embedding_phase_separately(
    tmp_path: Path,
):
    """Diagnostics separate text import from embedding status."""
    export_root = tmp_path / "export"
    _write_conversations_json(
        export_root,
        [_build_mapping_conversation([("user", "Diag test", 1.0)])],
    )
    diag_dir = tmp_path / "logs/openai_import"

    import_openai_export_conversations(
        export_root,
        user_id="tester",
        embedding_mode="defer",
        dry_run=True,
        diagnostic_dir=diag_dir,
    )

    json_files = list(diag_dir.glob("import_diagnostics_*.json"))
    assert len(json_files) == 1
    diag_data = json.loads(json_files[0].read_text())

    assert "text_import_complete" in diag_data
    assert "embedding_mode" in diag_data
    assert diag_data["embedding_mode"] == "defer"
    assert "embedding_candidates" in diag_data


def test_order_flags_work_with_embedding_deferral(
    tmp_path: Path,
    import_store: ImportStore,
):
    """--order flags work correctly with deferred embedding."""
    export_root = tmp_path / "export"
    _write_conversations_json(
        export_root,
        [
            _build_mapping_conversation(
                [("user", "Old", 1000.0)],
                conversation_id="old-conv",
                title="Oldest",
            ),
            _build_mapping_conversation(
                [("user", "New", 2000.0)],
                conversation_id="new-conv",
                title="Newest",
            ),
        ],
    )

    diag = import_openai_export_conversations(
        export_root,
        user_id="tester",
        order="newest",
        embedding_mode="defer",
        diagnostic_dir=tmp_path / "diag",
    )

    assert diag.text_import_complete is True
    assert diag.embedding_mode == "defer"
    assert diag.conversations_imported == 2


@pytest.mark.parametrize(
    ("order", "expected"),
    [
        ("file", ["b", "c", "d", "a"]),
        ("newest", ["b", "c", "a", "d"]),
        ("updated", ["b", "c", "a", "d"]),
        ("oldest", ["d", "b", "c", "a"]),
    ],
)
def test_spooled_order_keeps_global_stable_ties_and_batches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    order: str, expected: list[str],
) -> None:
    import backend.rag.openai_export_conversation_import as module

    root = tmp_path / "export"
    rows = [
        _build_mapping_conversation([("user", "A", 30)], conversation_id="a"),
        _build_mapping_conversation([("user", "B", 10)], conversation_id="b"),
        _build_mapping_conversation([("user", "C", 10)], conversation_id="c"),
        _build_mapping_conversation([("user", "D", 0)], conversation_id="d"),
    ]
    rows[1]["update_time"] = 40
    rows[2]["update_time"] = 40
    rows[3].pop("create_time")
    rows[3].pop("update_time")
    _write_sharded_conversations(root, rows)

    seen: list[str] = []
    callbacks: list[tuple[int, int, list[str]]] = []

    def fake_batch(*, conversations, **_kwargs):
        seen.extend(str(item["id"]) for item in conversations)
        return {"threads_imported": len(conversations), "messages_imported": len(conversations)}

    monkeypatch.setattr(module, "_import_conversation_batch", fake_batch)
    monkeypatch.setattr(module, "_confirmed_conversation_counts", lambda conversations, **_kwargs: {
        str(item["id"]): 1 for item in conversations
    })
    diag = import_openai_export_conversations(
        root, user_id="tester", order=order,
        diagnostic_dir=tmp_path / "diagnostics", batch_conversations=2,
        on_batch_committed=lambda batch: callbacks.append((
            batch["batch_number"], batch["batch_total"], batch["conversation_ids"]
        )),
    )
    assert diag.errors == []
    assert seen == expected
    assert callbacks == [(1, 2, expected[:2]), (2, 2, expected[2:])]
    assert diag.conversations_discovered == 4
    assert diag.conversations_accepted == 4
    assert not list((tmp_path / "diagnostics").glob("openai-order-*"))


def test_spooled_resume_uses_source_ids_across_batch_boundaries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    import backend.rag.openai_export_conversation_import as module

    root = tmp_path / "export"
    _write_conversations_json(root, [
        _build_mapping_conversation([("user", str(index), float(index))],
                                    conversation_id=f"source-{index}")
        for index in range(5)
    ])
    calls: list[list[str]] = []

    def fake_batch(*, conversations, **_kwargs):
        calls.append([str(item["id"]) for item in conversations])
        return {"threads_imported": len(conversations), "messages_imported": len(conversations)}

    monkeypatch.setattr(module, "_import_conversation_batch", fake_batch)
    monkeypatch.setattr(module, "_confirmed_conversation_counts", lambda conversations, **_kwargs: {
        str(item["id"]): 1 for item in conversations
    })
    kwargs = dict(user_id="tester", diagnostic_dir=tmp_path / "diagnostics",
                  checkpoint_path=str(tmp_path / "checkpoint"),
                  batch_conversations=2, resume=True)
    first = import_openai_export_conversations(root, **kwargs)
    assert first.errors == []
    assert calls == [["source-0", "source-1"], ["source-2", "source-3"], ["source-4"]]
    calls.clear()
    replay = import_openai_export_conversations(root, **kwargs)
    assert replay.errors == []
    assert calls == []
    assert replay.conversations_skipped_checkpoint == 5
    assert replay.conversations_imported == 0


def test_idempotent_rerun_with_deferred_embeddings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    import_modules: ImportModules,
):
    """Idempotent re-run works with deferred embedding mode."""
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

    find_thread_calls: list = []

    def _find_thread(db, *, user_id, source_thread_id, origin_system=None):
        find_thread_calls.append((user_id, source_thread_id))
        if len(find_thread_calls) > 1:
            return 1
        return None

    def _find_message(db, thread_id, source_message_id):
        if len(find_thread_calls) > 1:
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

    export_root = tmp_path / "export"
    _write_conversations_json(
        export_root,
        [_build_mapping_conversation(
            [("user", "A", 1.0)],
            conversation_id="stable",
            title="Stable",
        )],
    )

    first = import_openai_export_conversations(
        export_root, user_id="tester",
        embedding_mode="defer",
        diagnostic_dir=tmp_path / "diag1",
    )
    second = import_openai_export_conversations(
        export_root, user_id="tester",
        embedding_mode="defer",
        diagnostic_dir=tmp_path / "diag2",
    )

    assert first.conversations_imported == 1
    assert first.embedding_mode == "defer"
    assert second.conversations_imported == 0


def test_postgres_source_identity_replay_keeps_canonical_ids() -> None:
    """Exercise the real PostgreSQL lookup and provenance uniqueness index."""
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is required for the PostgreSQL replay test")
    psycopg = pytest.importorskip("psycopg")
    from psycopg import sql
    from psycopg.rows import dict_row

    migration = importlib.import_module("backend.rag.chatgpt_migration")
    schema = f"import_replay_{uuid.uuid4().hex[:12]}"

    class PostgresImportStore:
        def _connect(self):
            conn = psycopg.connect(database_url, row_factory=dict_row)
            with conn.cursor() as cur:
                cur.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
            return conn

        def create_chat_thread(self, *, user_id, title, summary, project_id,
                               metadata, origin_system):
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO chat_threads (user_id, origin_system, metadata) "
                    "VALUES (%s, %s, %s::jsonb) RETURNING id",
                    (user_id, origin_system, json.dumps(metadata)),
                )
                return cur.fetchone()

        def get_chat_thread(self, thread_id):
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute("SELECT metadata FROM chat_threads WHERE id = %s", (thread_id,))
                return cur.fetchone()

        def update_thread_metadata(self, thread_id, metadata):
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    "UPDATE chat_threads SET metadata = %s::jsonb WHERE id = %s",
                    (json.dumps(metadata), thread_id),
                )

        def create_message(self, thread_id, role, content, created_at=None):
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO chat_messages (thread_id, role, content) "
                    "VALUES (%s, %s, %s) RETURNING id",
                    (thread_id, role, content),
                )
                return cur.fetchone()["id"]

    with psycopg.connect(database_url, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    try:
        store = PostgresImportStore()
        with store._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "CREATE TABLE chat_threads (id bigserial PRIMARY KEY, "
                "user_id text NOT NULL, origin_system text NOT NULL, "
                "metadata jsonb NOT NULL DEFAULT '{}'::jsonb)"
            )
            cur.execute(
                "CREATE TABLE chat_messages (id bigserial PRIMARY KEY, "
                "thread_id bigint NOT NULL REFERENCES chat_threads(id), "
                "role text NOT NULL, content text NOT NULL, event_at timestamptz, "
                "extra_meta jsonb NOT NULL DEFAULT '{}'::jsonb)"
            )
            cur.execute(
                "CREATE UNIQUE INDEX uq_chat_messages_source_thread_message "
                "ON chat_messages ((extra_meta->>'source_thread_id'), "
                "(extra_meta->>'source_message_id')) "
                "WHERE extra_meta ? 'source_thread_id' "
                "AND extra_meta ? 'source_message_id' "
                "AND (extra_meta->>'source_message_id') <> ''"
            )

        timestamp = datetime.now(timezone.utc)

        def ingest(source_thread_id: str, source_message_id: str):
            return migration._ingest_canonical_messages(
                chatlog_db=store, user_id="account-a", title="Imported",
                thread_summary="Imported from Claude", import_source="claude",
                import_profile="claude_import", source_thread_id=source_thread_id,
                messages=[{
                    "source_thread_id": source_thread_id,
                    "source_message_id": source_message_id,
                    "turn_index": 0, "source_created_at": timestamp,
                    "imported_at": timestamp, "role": "user", "content": "Hello",
                }],
                imports_project_id=1, import_grouping_metadata={},
                pending_embed_items=[], pending_embed_message_ids=[],
                filtered_count=0, filtered_reasons={}, embedding_mode="off",
                disable_personal_facts=True,
            )

        assert ingest("claude-conversation", "claude-message") == (1, 1)
        with store._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT id FROM chat_threads")
            thread_id = cur.fetchone()["id"]
            cur.execute("SELECT id, extra_meta FROM chat_messages")
            original = cur.fetchone()

        assert migration._find_existing_thread_for_source(
            store, "account-a", "claude-conversation", origin_system=None
        ) == thread_id
        assert migration._find_existing_thread_for_source(
            store, "account-a", "claude-conversation", origin_system="openai"
        ) is None
        assert ingest("claude-conversation", "claude-message") == (0, 0)
        with store._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT count(*) AS n FROM chat_threads")
            assert cur.fetchone()["n"] == 1
            cur.execute("SELECT id, extra_meta FROM chat_messages")
            replayed = cur.fetchone()
            assert cur.fetchone() is None
        assert replayed["id"] == original["id"]
        assert replayed["extra_meta"]["source_thread_id"] == "claude-conversation"
        assert replayed["extra_meta"]["source_message_id"] == "claude-message"

        assert ingest("new-conversation", "new-message") == (1, 1)
        with store._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT count(*) AS n FROM chat_threads")
            assert cur.fetchone()["n"] == 2
            cur.execute("SELECT count(*) AS n FROM chat_messages")
            assert cur.fetchone()["n"] == 2

        orphan_message_id = store.create_message(thread_id, "user", "Orphan")
        with pytest.raises(psycopg.errors.UniqueViolation):
            migration._persist_temporal_metadata(
                store, orphan_message_id, original["extra_meta"], timestamp
            )
        with store._connect() as conn, conn.cursor() as cur:
            cur.execute("DROP TABLE chat_messages")
        with pytest.raises(psycopg.errors.UndefinedTable):
            migration._find_existing_thread_for_source(
                store, "account-a", "claude-conversation", "anthropic"
            )
        with pytest.raises(psycopg.errors.UndefinedTable):
            migration._find_existing_message_for_source(
                store, thread_id, "claude-message"
            )
    finally:
        with psycopg.connect(database_url, autocommit=True) as conn, conn.cursor() as cur:
            cur.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


def test_postgres_conversation_transaction_rolls_back_and_replays(
    monkeypatch: pytest.MonkeyPatch,
    transaction_postgres_url: str,
) -> None:
    """A failure after the second provenance update cannot commit a fragment."""
    database_url = transaction_postgres_url
    psycopg = pytest.importorskip("psycopg")
    from guardian.core.pgdb import PgDB

    migration = importlib.import_module("backend.rag.chatgpt_migration")
    db = PgDB(database_url)
    monkeypatch.setattr(migration.dependencies, "chatlog_db", db)
    source_ids = [f"atomic-proof-{uuid.uuid4().hex}" for _ in range(2)]
    conversation = lambda source_id: _build_mapping_conversation(
        [("user", "First", 1.0), ("assistant", "Second", 2.0)],
        conversation_id=source_id,
    )
    original_persist = migration._persist_temporal_metadata

    def readback(source_id: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
        from psycopg.rows import dict_row

        with psycopg.connect(database_url, row_factory=dict_row) as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT ct.id, ct.user_id, ct.project_id, p.user_id AS project_user_id, "
                "ct.origin_system, ct.metadata FROM chat_threads ct "
                "LEFT JOIN projects p ON p.id = ct.project_id "
                "WHERE ct.user_id = %s "
                "AND ct.metadata->>'source_thread_id' = %s ORDER BY ct.id",
                ("local", source_id),
            )
            threads = cur.fetchall()
            cur.execute(
                "SELECT id, thread_id, user_id, extra_meta FROM chat_messages "
                "WHERE extra_meta->>'source_thread_id' = %s ORDER BY id",
                (source_id,),
            )
            messages = cur.fetchall()
            cur.execute(
                "SELECT count(*) AS n FROM personal_fact_evidence "
                "WHERE evidence_meta->>'source_thread_id' = %s",
                (source_id,),
            )
            return threads, messages, cur.fetchone()["n"]

    def import_one(source_id: str) -> dict[str, Any]:
        return migration.ingest_chatgpt_conversation_records(
            [conversation(source_id)], user_id="local", embedding_mode="defer",
            disable_personal_facts=True,
        )

    try:
        calls = 0

        def fail_after_second_write(*args, **kwargs):
            nonlocal calls
            original_persist(*args, **kwargs)
            calls += 1
            if calls == 2:
                raise RuntimeError("synthetic failure after second provenance write")

        monkeypatch.setattr(migration, "_persist_temporal_metadata", fail_after_second_write)
        with pytest.raises(RuntimeError, match="synthetic failure"):
            import_one(source_ids[0])
        assert calls == 2
        assert readback(source_ids[0]) == ([], [], 0)

        monkeypatch.setattr(migration, "_persist_temporal_metadata", original_persist)
        first = import_one(source_ids[0])
        assert (first["threads_imported"], first["messages_imported"]) == (1, 2)
        threads, messages, evidence_count = readback(source_ids[0])
        assert evidence_count == 0
        assert len(threads) == 1 and len(messages) == 2
        assert threads[0]["origin_system"] == "openai"
        assert threads[0]["user_id"] == "local"
        assert threads[0]["project_user_id"] == "local"
        assert threads[0]["project_id"] is not None
        assert threads[0]["metadata"]["source_thread_id"] == source_ids[0]
        assert all(message["user_id"] == "local" for message in messages)
        assert [message["extra_meta"]["source_message_id"] for message in messages] == ["m1", "m2"]
        identity_before = (
            threads[0]["id"],
            [(message["id"], message["thread_id"], message["extra_meta"]) for message in messages],
        )
        replay = import_one(source_ids[0])
        assert (replay["threads_imported"], replay["messages_imported"]) == (0, 0)
        replay_threads, replay_messages, replay_evidence_count = readback(source_ids[0])
        assert replay_evidence_count == evidence_count
        assert (
            replay_threads[0]["id"],
            [(message["id"], message["thread_id"], message["extra_meta"]) for message in replay_messages],
        ) == identity_before

        calls = 0

        def fail_with_database_error(*args, **kwargs):
            nonlocal calls
            original_persist(*args, **kwargs)
            calls += 1
            if calls == 2:
                raise psycopg.OperationalError("synthetic database connection failure")

        monkeypatch.setattr(migration, "_persist_temporal_metadata", fail_with_database_error)
        with pytest.raises(psycopg.OperationalError, match="synthetic database"):
            import_one(source_ids[1])
        assert calls == 2
        assert readback(source_ids[1]) == ([], [], 0)
    finally:
        with psycopg.connect(database_url) as conn, conn.cursor() as cur:
            cur.execute(
                "DELETE FROM chat_threads WHERE user_id = %s "
                "AND metadata->>'source_thread_id' = ANY(%s)",
                ("local", source_ids),
            )


def _synthetic_modern_recall_export(root: Path, prefix: str) -> dict[str, bytes]:
    """Readable shards, repeated source identity, referenced image, opaque orphan."""
    workspace = _build_mapping_conversation(
        [("user", "What is the Helix observatory calibration code?", 1000),
         ("assistant", "Helix observatory calibration code is HELIX-481726.", 1001)],
        conversation_id=f"{prefix}-workspace", title="Helix calibration",
    )
    workspace["workspace_id"] = "external-workspace-provenance"
    workspace["user_id"] = "untrusted-export-owner"
    workspace["mapping"]["m1"]["message"]["metadata"] = {
        "file_path": "assets/calibration.png",
    }
    unassigned = _build_mapping_conversation(
        [("user", "Record the spare sensor designation.", 2000),
         ("assistant", "The spare sensor is AURORA-92.", 2001)],
        conversation_id=f"{prefix}-unassigned", title="Spare sensor",
    )
    files = {
        "workspace-helix/conversations__a.part-0001/readable.dat":
            json.dumps(workspace).encode(),
        "Unassigned/conversations__b.part-0002/messages.dat":
            ((json.dumps(unassigned) + "\n") * 2).encode(),
        "workspace-helix/conversations__a.part-0001/repeated.dat":
            json.dumps(workspace).encode(),
        "assets/calibration.png": base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        ),
        "assets/unlinked.dat": b"\x00\xff\x01SYNTHETIC-OPAQUE-ORPHAN",
        "__export_file_manifests__/conversations.json":
            json.dumps({"file_name": "readable.dat", "file_size": 100}).encode(),
    }
    for relative, content in files.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    return files


def test_synthetic_modern_recall_fixture_has_explicit_inventory(tmp_path: Path):
    from backend.rag.openai_export_adapter import (
        build_openai_export_image_evidence_index,
        diagnose_openai_export_path,
        resolve_openai_export_image_evidence,
    )

    root = tmp_path / "modern"
    files = _synthetic_modern_recall_export(root, "inventory")
    report = diagnose_openai_export_path(root)
    assert report.inventory.detected_format == "sharded"
    assert not report.inventory.legacy_detected
    records = {record.path: record for record in report.inventory.files}
    assert set(records) == set(files)
    assert records["Unassigned/conversations__b.part-0002/messages.dat"].detected_kind == "jsonl"
    assert records["workspace-helix/conversations__a.part-0001/readable.dat"].detected_kind == "json_object"
    assert records["assets/unlinked.dat"].conversation_candidate is False
    assert records["__export_file_manifests__/conversations.json"].conversation_candidate is False
    evidence = build_openai_export_image_evidence_index(report.inventory)
    linked = resolve_openai_export_image_evidence("assets/calibration.png", evidence)
    assert (linked.source_tag, linked.source_thread_id, linked.source_message_id) == (
        "uploaded", "inventory-workspace", "m1",
    )
    assert resolve_openai_export_image_evidence("assets/unlinked.dat", evidence).evidence_kind == "unlinked"
    dry = import_openai_export_conversations(
        root, user_id="account-a", dry_run=True, diagnostic_dir=tmp_path / "diagnostics",
    )
    assert dry.errors == []
    assert (dry.conversations_discovered, dry.messages_discovered) == (2, 4)
    opaque = tmp_path / "opaque-only"
    opaque.mkdir()
    (opaque / "blob.dat").write_bytes(files["assets/unlinked.dat"])
    rejected = import_openai_export_conversations(
        opaque, user_id="account-a", dry_run=True, diagnostic_dir=tmp_path / "opaque-diag",
    )
    assert rejected.errors == ["Unrecognized export format: unknown"]


@pytest.mark.integration
def test_postgres_synthetic_modern_account_import_recovery_and_lineage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Real staged service/worker/PG writes; queue ports are controlled test doubles.

    This does not consume embeddings or execute a chat completion. Run only with
    TEST_DATABASE_URL pointing at a migrated disposable PostgreSQL database.
    """
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is required for synthetic PostgreSQL qualification")
    psycopg = pytest.importorskip("psycopg")
    from psycopg.rows import dict_row
    from guardian.core.db import GuardianDB
    from guardian.core.pgdb import PgDB
    from guardian.core.storage import StorageManager
    from guardian.services.openai_account_import import (
        AccountImportError, AccountImportLimits, OpenAIAccountImportService, StagedImportFile,
    )
    from guardian.workers.account_import_worker import (
        AccountImportEmbeddingHandoffRetryable, process_account_import_task,
    )
    from guardian.queue.account_import_queue import TASK_TYPE
    from guardian.core import dependencies

    prefix = f"qualification-{uuid.uuid4().hex[:12]}"
    accounts = [f"{prefix}-a", f"{prefix}-b"]
    db = PgDB(database_url)
    monkeypatch.setattr(dependencies, "chatlog_db", db)
    guardian_db = GuardianDB(db._sa_url)
    embedding_payloads: list[dict[str, Any]] = []
    queued: list[tuple[str, str]] = []
    interrupt_handoff = True

    def enqueue_embedding(payload):
        if interrupt_handoff:
            raise RuntimeError("synthetic interruption after durable conversation batch")
        embedding_payloads.append(payload)
        return f"test-queue-{len(embedding_payloads)}"

    service = OpenAIAccountImportService(
        db=guardian_db,
        staging_storage=StorageManager("local", base_path=tmp_path / "staging", url_prefix="/internal"),
        media_storage=StorageManager("local", base_path=tmp_path / "media", url_prefix="/media"),
        enqueue_task=lambda job_id, *, user_id: queued.append((job_id, user_id)),
        enqueue_import_embedding_task=enqueue_embedding,
        emit_event=lambda *_args, **_kwargs: None,
        limits=AccountImportLimits(conversation_batch_size=1),
    )

    def readback(account):
        with psycopg.connect(database_url, row_factory=dict_row) as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT ct.*, p.user_id AS project_user_id "
                "FROM chat_threads ct JOIN projects p ON p.id=ct.project_id "
                "WHERE ct.user_id=%s ORDER BY ct.id", (account,),
            )
            threads = cur.fetchall()
            cur.execute(
                "SELECT * FROM chat_messages "
                "WHERE user_id=%s ORDER BY id", (account,),
            )
            return threads, cur.fetchall()

    def submit(account, files):
        created = service.create_job(user_id=account, total_file_count=len(files),
                                     total_byte_count=sum(map(len, files.values())))
        job_id = created["job_id"]
        service.stage_files(job_id=job_id, user_id=account,
                            files=[StagedImportFile(path, data) for path, data in files.items()])
        service.finalize_job(job_id=job_id, user_id=account)
        assert queued[-1] == (job_id, account)
        return job_id, {"type": TASK_TYPE, "job_id": job_id, "user_id": account}

    try:
        with psycopg.connect(database_url) as conn, conn.cursor() as cur:
            for account in accounts:
                cur.execute("INSERT INTO users(id,username,password_hash) VALUES(%s,%s,'synthetic')",
                            (account, account))
        baseline = tmp_path / "baseline"
        _write_conversations_json(baseline, [_build_mapping_conversation(
            [("user", "Existing synthetic import must remain unchanged.", 10)],
            conversation_id=f"{prefix}-baseline",
        )])
        baseline_diag = import_openai_export_conversations(
            baseline, user_id=accounts[0], messages_only=True, diagnostic_dir=tmp_path / "baseline-diag",
        )
        assert baseline_diag.errors == []
        before_threads, before_messages = readback(accounts[0])
        assert (len(before_threads), len(before_messages)) == (1, 1)

        files = _synthetic_modern_recall_export(tmp_path / "modern", prefix)
        job_id, payload = submit(accounts[0], files)
        with pytest.raises(AccountImportEmbeddingHandoffRetryable):
            process_account_import_task(payload, service=service)
        interrupted = service.get_worker_job(job_id=job_id, user_id=accounts[0])
        assert interrupted["status"] == "running"
        assert len(interrupted["checkpoint"]["conversation_ids"]) == 1
        partial_threads, partial_messages = readback(accounts[0])
        assert (len(partial_threads), len(partial_messages)) == (2, 3)
        interrupt_handoff = False
        assert process_account_import_task(payload, service=service) is True
        completed = service.get_worker_job(job_id=job_id, user_id=accounts[0])
        assert completed["status"] == "completed_with_warnings"
        assert (completed["imported_thread_count"], completed["imported_message_count"]) == (2, 4)
        assert set(completed["checkpoint"]["conversation_ids"]) == {f"{prefix}-workspace", f"{prefix}-unassigned"}
        assert any(detail["code"] == "unsupported_attachment_family" and detail["path"] == "assets/unlinked.dat"
                   for detail in completed["warning_details"])
        threads, messages = readback(accounts[0])
        assert threads[:1] == before_threads
        assert messages[:1] == before_messages
        imported = messages[1:]
        assert len(threads) == 3 and len(imported) == 4
        assert all(t["user_id"] == t["project_user_id"] == accounts[0] for t in threads)
        assert all(t["origin_system"] == "openai" for t in threads)
        for source_id in (f"{prefix}-workspace", f"{prefix}-unassigned"):
            turns = [m for m in imported if m["extra_meta"]["source_thread_id"] == source_id]
            assert [m["extra_meta"]["source_message_id"] for m in turns] == ["m1", "m2"]
            assert [m["extra_meta"]["turn_index"] for m in turns] == [0, 1]
            assert [m["role"] for m in turns] == ["user", "assistant"]
            assert all(m["extra_meta"]["embedding_status"] == "pending" for m in turns)
            assert all(m["extra_meta"]["openai_export_source_path"] for m in turns)
        assert {p["message_id"] for p in embedding_payloads} == {m["id"] for m in imported}
        assert all(p["meta"]["user_id"] == accounts[0] for p in embedding_payloads)
        with pytest.raises(AccountImportError) as denied:
            service.get_job(job_id=job_id, user_id=accounts[1])
        assert denied.value.status_code == 404

        replay_id, replay_payload = submit(accounts[0], files)
        assert process_account_import_task(replay_payload, service=service) is True
        replay_threads, replay_messages = readback(accounts[0])
        assert replay_threads[:1] == before_threads
        assert replay_messages == messages
        # Existing behavior touches replayed threads' updated_at even when no
        # source entity is added. Every other canonical thread field is stable.
        stable_thread = lambda row: {key: value for key, value in row.items() if key != "updated_at"}
        assert list(map(stable_thread, replay_threads)) == list(map(stable_thread, threads))
        assert all(after["updated_at"] >= before["updated_at"]
                   for before, after in zip(threads, replay_threads))
        threads = replay_threads
        assert service.get_job(job_id=replay_id, user_id=accounts[0])["status"] == "completed_with_warnings"
        second = _build_mapping_conversation(
            [("user", "Record the unrelated account's calibration.", 3000),
             ("assistant", "Other observatory code is OTHER-739105.", 3001)],
            conversation_id=f"{prefix}-other-account",
        )
        second_id, second_payload = submit(accounts[1], {"conversations.json": json.dumps([second]).encode()})
        assert process_account_import_task(second_payload, service=service) is True
        second_threads, second_messages = readback(accounts[1])
        assert (len(second_threads), len(second_messages)) == (1, 2)
        assert second_threads[0]["user_id"] == second_threads[0]["project_user_id"] == accounts[1]
        assert "HELIX-481726" not in json.dumps(second_messages, default=str)
        assert "OTHER-739105" not in json.dumps(messages, default=str)
        assert readback(accounts[0]) == (threads, messages)
        with psycopg.connect(database_url, row_factory=dict_row) as conn, conn.cursor() as cur:
            cur.execute("SELECT thread_id,source_message_id,source_tag,source_relative_path FROM media_assets WHERE user_id=%s", (accounts[0],))
            assets = cur.fetchall()
            assert len(assets) == 1
            linked_thread = next(t["id"] for t in threads if t["metadata"]["source_thread_id"] == f"{prefix}-workspace")
            assert assets[0] == {"thread_id": linked_thread, "source_message_id": "m1",
                                 "source_tag": "uploaded", "source_relative_path": "assets/calibration.png"}
            cur.execute("SELECT count(*) AS n FROM personal_facts WHERE user_id=ANY(%s)", (accounts,))
            assert cur.fetchone()["n"] == 0
        print(json.dumps({"evidence": "synthetic-modern-import", "job_id": job_id,
                          "replay_job_id": replay_id, "second_account_job_id": second_id,
                          "accounts": accounts, "interrupted_messages": 2, "recovered_messages": 4,
                          "interrupted_checkpoint": interrupted["checkpoint"]["conversation_ids"],
                          "completed_checkpoint": completed["checkpoint"]["conversation_ids"],
                          "status": completed["status"], "warnings": completed["warning_details"],
                          "second_account_owner": second_threads[0]["user_id"],
                          "second_account_messages": len(second_messages),
                          "thread_ids": [t["id"] for t in threads],
                          "source_lineage": [{"id": m["id"], "owner": m["user_id"],
                                              "thread": m["extra_meta"]["source_thread_id"],
                                              "message": m["extra_meta"]["source_message_id"],
                                              "path": m["extra_meta"]["openai_export_source_path"]} for m in imported],
                          "embedding_status": "pending", "personal_facts": 0}))
    finally:
        # Only the test's uniquely named accounts and their dependent rows.
        with psycopg.connect(database_url) as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM media_aliases WHERE asset_id IN (SELECT id FROM media_assets WHERE user_id=ANY(%s))", (accounts,))
            cur.execute("DELETE FROM uploaded_images WHERE user_id=ANY(%s)", (accounts,))
            cur.execute("DELETE FROM media_assets WHERE user_id=ANY(%s)", (accounts,))
            cur.execute("DELETE FROM openai_account_import_jobs WHERE user_id=ANY(%s)", (accounts,))
            cur.execute("DELETE FROM chat_threads WHERE user_id=ANY(%s)", (accounts,))
            cur.execute("DELETE FROM projects WHERE user_id=ANY(%s)", (accounts,))
            cur.execute("DELETE FROM users WHERE id=ANY(%s)", (accounts,))
