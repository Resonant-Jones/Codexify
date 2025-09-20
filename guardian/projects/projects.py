import sqlite3
from datetime import datetime, timezone
from typing import Dict, List, Optional

from guardian.config import get_settings


def _db_path() -> str:
    """
    Resolve DB path at call-time so it picks up whatever .env the API loaded.
    """
    settings = get_settings()
    return settings.GUARDIAN_DB_PATH


def get_connection():
    """
    Establish and return a connection to the SQLite database.

    Notes:
      * check_same_thread=False because FastAPI endpoints execute in a threadpool.
        We open a fresh connection per call, so this is safe and avoids thread checks.
    """
    return sqlite3.connect(_db_path(), check_same_thread=False)


def init_projects_table() -> None:
    """
    Ensure the 'projects' table exists.
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def create_project(name: str, description: str = "") -> int:
    """
    Insert a new project and return its integer id.
    """
    if not name or not name.strip():
        raise ValueError("Project name is required")

    init_projects_table()
    conn = get_connection()
    try:
        created_at = datetime.now(timezone.utc).isoformat()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO projects (name, description, created_at) VALUES (?, ?, ?)",
            (name.strip(), description or "", created_at),
        )
        conn.commit()
        pid = cur.lastrowid
        if pid is None:
            raise RuntimeError("Failed to obtain project id after insert")
        return int(pid)
    finally:
        conn.close()


def list_projects() -> List[Dict]:
    """
    Return all projects as list[dict].
    """
    init_projects_table()
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, name, description, created_at FROM projects ORDER BY id DESC"
        )
        rows = cur.fetchall()
        return [
            {
                "id": int(r[0]),
                "name": r[1],
                "description": (r[2] or ""),
                "created_at": r[3],
            }
            for r in rows
        ]
    finally:
        conn.close()


def get_project_by_id(project_id: int) -> Optional[Dict]:
    """
    Get a single project by id. Returns dict or None.
    """
    init_projects_table()
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, name, description, created_at FROM projects WHERE id = ?",
            (int(project_id),),
        )
        r = cur.fetchone()
        if not r:
            return None
        return {
            "id": int(r[0]),
            "name": r[1],
            "description": (r[2] or ""),
            "created_at": r[3],
        }
    finally:
        conn.close()


def delete_project(project_id: int) -> bool:
    """
    Delete a project by id. Returns True if a row was deleted.
    """
    init_projects_table()
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM projects WHERE id = ?", (int(project_id),))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()
