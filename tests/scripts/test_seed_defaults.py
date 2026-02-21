"""Regression tests for default-project alias normalization during seeding."""

from __future__ import annotations

import importlib.util
import sqlite3
from pathlib import Path


def _load_seed_defaults_module():
    root = Path(__file__).resolve().parents[2]
    script_path = root / "backend" / "scripts" / "seed_defaults.py"
    spec = importlib.util.spec_from_file_location(
        "seed_defaults_module", script_path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to load seed_defaults module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


seed_defaults = _load_seed_defaults_module()


def _build_schema() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(
        """
        CREATE TABLE projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT
        );

        -- Intentionally no FK here to validate chat_threads fallback handling.
        CREATE TABLE chat_threads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER
        );

        CREATE TABLE generated_documents (
            id TEXT PRIMARY KEY,
            project_id INTEGER,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        );

        CREATE TABLE uploaded_images (
            id TEXT PRIMARY KEY,
            project_id INTEGER NOT NULL,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        );
        """
    )
    return conn


def _project_id(conn: sqlite3.Connection, name: str) -> int:
    row = conn.execute(
        "SELECT id FROM projects WHERE name = ?",
        (name,),
    ).fetchone()
    assert row is not None
    return int(row[0])


def test_dedupe_aliases_reassigns_project_owned_rows() -> None:
    conn = _build_schema()
    try:
        conn.execute(
            "INSERT INTO projects (name, description) VALUES (?, ?)",
            ("Loose Threads", "legacy default"),
        )
        conn.execute(
            "INSERT INTO projects (name, description) VALUES (?, ?)",
            ("General", "canonical default"),
        )
        loose_id = _project_id(conn, "Loose Threads")
        general_id = _project_id(conn, "General")

        conn.execute(
            "INSERT INTO chat_threads (project_id) VALUES (?)",
            (loose_id,),
        )
        conn.execute(
            "INSERT INTO generated_documents (id, project_id) VALUES (?, ?)",
            ("doc-1", loose_id),
        )
        conn.execute(
            "INSERT INTO uploaded_images (id, project_id) VALUES (?, ?)",
            ("img-1", loose_id),
        )
        conn.commit()

        (
            keep_id,
            remove_ids,
            _counts,
        ) = seed_defaults.dedupe_default_project_aliases(conn)

        assert keep_id == general_id
        assert remove_ids == [loose_id]
        assert (
            conn.execute(
                "SELECT project_id FROM chat_threads WHERE id = 1"
            ).fetchone()[0]
            == general_id
        )
        assert (
            conn.execute(
                "SELECT project_id FROM generated_documents WHERE id = ?",
                ("doc-1",),
            ).fetchone()[0]
            == general_id
        )
        assert (
            conn.execute(
                "SELECT project_id FROM uploaded_images WHERE id = ?",
                ("img-1",),
            ).fetchone()[0]
            == general_id
        )
        assert (
            conn.execute(
                "SELECT COUNT(*) FROM projects WHERE name = ?",
                ("Loose Threads",),
            ).fetchone()[0]
            == 0
        )
    finally:
        conn.close()


def test_dedupe_aliases_is_idempotent() -> None:
    conn = _build_schema()
    try:
        conn.execute(
            "INSERT INTO projects (name, description) VALUES (?, ?)",
            ("Loose Threads", "legacy default"),
        )
        conn.execute(
            "INSERT INTO projects (name, description) VALUES (?, ?)",
            ("General", "canonical default"),
        )
        loose_id = _project_id(conn, "Loose Threads")
        conn.execute(
            "INSERT INTO generated_documents (id, project_id) VALUES (?, ?)",
            ("doc-1", loose_id),
        )
        conn.commit()

        (
            first_keep,
            first_remove,
            _,
        ) = seed_defaults.dedupe_default_project_aliases(conn)
        (
            second_keep,
            second_remove,
            second_counts,
        ) = seed_defaults.dedupe_default_project_aliases(conn)

        assert first_keep == second_keep
        assert first_remove == [loose_id]
        assert second_remove == []
        assert second_counts == {}
        assert (
            conn.execute(
                "SELECT COUNT(*) FROM projects WHERE name = 'General'"
            ).fetchone()[0]
            == 1
        )
    finally:
        conn.close()
