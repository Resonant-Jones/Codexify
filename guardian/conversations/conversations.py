import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

DB_PATH = "guardian.db"


def init_conversations_table():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id INTEGER,
                parent_id INTEGER,
                title TEXT,
                summary TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (thread_id) REFERENCES threads(id),
                FOREIGN KEY (parent_id) REFERENCES conversations(id)
            )
        """
        )
        conn.commit()


def create_conversation(
    thread_id: Optional[int],
    parent_id: Optional[int],
    title: Optional[str],
    summary: Optional[str] = None,
) -> int:
    created_at = datetime.utcnow().isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO conversations (thread_id, parent_id, title, summary, created_at)
            VALUES (?, ?, ?, ?, ?)
        """,
            (thread_id, parent_id, title, summary, created_at),
        )
        conn.commit()
        return cursor.lastrowid


def get_conversation_by_id(convo_id: int) -> Optional[Dict[str, Any]]:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, thread_id, parent_id, title, summary, created_at
            FROM conversations
            WHERE id = ?
        """,
            (convo_id,),
        )
        row = cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "thread_id": row[1],
                "parent_id": row[2],
                "title": row[3],
                "summary": row[4],
                "created_at": row[5],
            }
    return None


def get_conversations_by_thread(thread_id: int) -> List[Dict[str, Any]]:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, thread_id, parent_id, title, summary, created_at
            FROM conversations
            WHERE thread_id = ?
            ORDER BY created_at ASC
        """,
            (thread_id,),
        )
        rows = cursor.fetchall()
        return [
            {
                "id": row[0],
                "thread_id": row[1],
                "parent_id": row[2],
                "title": row[3],
                "summary": row[4],
                "created_at": row[5],
            }
            for row in rows
        ]


def get_child_conversations(parent_id: int) -> List[Dict[str, Any]]:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, thread_id, parent_id, title, summary, created_at
            FROM conversations
            WHERE parent_id = ?
            ORDER BY created_at ASC
        """,
            (parent_id,),
        )
        rows = cursor.fetchall()
        return [
            {
                "id": row[0],
                "thread_id": row[1],
                "parent_id": row[2],
                "title": row[3],
                "summary": row[4],
                "created_at": row[5],
            }
            for row in rows
        ]


def has_children(convo_id: int) -> bool:
    """
    Determine if a conversation has children (i.e., is a root of a thread).
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM conversations
            WHERE parent_id = ?
        """,
            (convo_id,),
        )
        return cursor.fetchone()[0] > 0


def get_lineage(convo_id: int) -> Dict[str, Any]:
    """
    Recursively trace up to the root and down to all children from a given conversation.
    """

    def trace_up(cid: int):
        convo = get_conversation_by_id(cid)
        lineage = []
        while convo and convo["parent_id"]:
            convo = get_conversation_by_id(convo["parent_id"])
            if convo:
                lineage.insert(0, convo)
        return lineage

    def trace_down(cid: int):
        children = get_child_conversations(cid)
        lineage = []
        for child in children:
            lineage.append(child)
            lineage.extend(trace_down(child["id"]))
        return lineage

    origin = get_conversation_by_id(convo_id)
    return {
        "upstream": trace_up(convo_id),
        "current": origin,
        "downstream": trace_down(convo_id),
    }
