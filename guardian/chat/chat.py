import sqlite3
from sqlite3 import Error

DB_PATH = "guardian_chat.db"


def init_chat_tables():
    """
    Initialize the database tables for threads and messages.
    Creates 'threads' and 'messages' tables if they do not exist.
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS threads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    user_id INTEGER
                )
            """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    thread_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    parent_id INTEGER,
                    user_id INTEGER,
                    FOREIGN KEY(thread_id) REFERENCES threads(id),
                    FOREIGN KEY(parent_id) REFERENCES messages(id)
                )
            """
            )
            conn.commit()
    except Error as e:
        # Basic error handling - could be extended to logging
        pass


def create_thread(project_id: int, title: str, user_id: int = None) -> int:
    """
    Create a new thread for a project.

    Args:
        project_id (int): The ID of the project.
        title (str): The title of the thread.
        user_id (int, optional): The ID of the user creating the thread.

    Returns:
        int: The ID of the created thread, or -1 if an error occurred.
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO threads (project_id, title, user_id)
                VALUES (?, ?, ?)
            """,
                (project_id, title, user_id),
            )
            conn.commit()
            return cursor.lastrowid
    except Error:
        return -1


def list_threads(project_id: int) -> list:
    """
    List all threads for a given project.

    Args:
        project_id (int): The ID of the project.

    Returns:
        list: A list of dictionaries representing threads.
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, project_id, title, user_id
                FROM threads
                WHERE project_id = ?
            """,
                (project_id,),
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    except Error:
        return []


def create_message(
    thread_id: int, role: str, content: str, parent_id: int = None, user_id: int = None
) -> int:
    """
    Create a new message in a thread.

    Args:
        thread_id (int): The ID of the thread.
        role (str): The role of the message sender (e.g., 'user', 'system').
        content (str): The content of the message.
        parent_id (int, optional): The ID of the parent message if this is a reply.
        user_id (int, optional): The ID of the user sending the message.

    Returns:
        int: The ID of the created message, or -1 if an error occurred.
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO messages (thread_id, role, content, parent_id, user_id)
                VALUES (?, ?, ?, ?, ?)
            """,
                (thread_id, role, content, parent_id, user_id),
            )
            conn.commit()
            return cursor.lastrowid
    except Error:
        return -1


def list_messages(thread_id: int) -> list:
    """
    List all messages for a given thread.

    Args:
        thread_id (int): The ID of the thread.

    Returns:
        list: A list of dictionaries representing messages.
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, thread_id, role, content, parent_id, user_id
                FROM messages
                WHERE thread_id = ?
                ORDER BY id ASC
            """,
                (thread_id,),
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    except Error:
        return []
