import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

DB_PATH = "guardian.db"


def init_threads_table() -> None:
    """
    Initialize the threads table in the database if it does not already exist.
    Adds parent_thread_id for parent/child relations and project_id for project linkage.
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS threads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            parent_thread_id INTEGER,
            title TEXT,
            summary TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id),
            FOREIGN KEY (parent_thread_id) REFERENCES threads(id)
        );
        """
        )
        conn.commit()


def create_thread(
    project_id: int,
    title: str,
    summary: Optional[str] = None,
    parent_thread_id: Optional[int] = None,
) -> int:
    """
    Create a new thread, optionally as a child/branch of another thread.
    Returns the new thread's ID.
    """
    created_at = datetime.utcnow().isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO threads (project_id, parent_thread_id, title, summary, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (project_id, parent_thread_id, title, summary, created_at),
        )
        conn.commit()
        return cursor.lastrowid


def get_thread_by_id(thread_id: int) -> Optional[Dict[str, Any]]:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, project_id, parent_thread_id, title, summary, created_at FROM threads WHERE id = ?",
            (thread_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return {
            "id": row[0],
            "project_id": row[1],
            "parent_thread_id": row[2],
            "title": row[3],
            "summary": row[4],
            "created_at": row[5],
        }


def get_children_threads(parent_thread_id: int) -> List[Dict[str, Any]]:
    """
    Return all child threads (branches) for a given parent_thread_id.
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, project_id, parent_thread_id, title, summary, created_at FROM threads WHERE parent_thread_id = ?",
            (parent_thread_id,),
        )
        rows = cursor.fetchall()
        return [
            {
                "id": row[0],
                "project_id": row[1],
                "parent_thread_id": row[2],
                "title": row[3],
                "summary": row[4],
                "created_at": row[5],
            }
            for row in rows
        ]


def get_all_threads_for_project(project_id: int) -> List[Dict[str, Any]]:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, project_id, parent_thread_id, title, summary, created_at FROM threads WHERE project_id = ?",
            (project_id,),
        )
        rows = cursor.fetchall()
        return [
            {
                "id": row[0],
                "project_id": row[1],
                "parent_thread_id": row[2],
                "title": row[3],
                "summary": row[4],
                "created_at": row[5],
            }
            for row in rows
        ]


def get_thread_lineage(thread_id: int) -> List[Dict[str, Any]]:
    """
    Returns the lineage (ancestors) of a thread, up to the root.
    """
    lineage = []
    current = get_thread_by_id(thread_id)
    while current and current["parent_thread_id"]:
        parent = get_thread_by_id(current["parent_thread_id"])
        if not parent:
            break
        lineage.insert(0, parent)
        current = parent
    return lineage


# You may want to add update/delete/thread-traversal or search functions as needed.
