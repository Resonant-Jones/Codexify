import json
import sqlite3
from datetime import datetime
from typing import Any, Dict, Optional

DB_PATH = "guardian.db"


def init_users_table() -> None:
    """
    Initialize the users table in the database if it does not already exist.
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                extra_data TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def create_user(
    username: str, password: str, extra_data: Optional[Dict[str, Any]] = None
) -> int:
    """
    Create a new user in the database.
    Args:
        username (str): The username of the user (must be unique).
        password (str): The hashed password of the user.
        extra_data (dict, optional): Additional data to store for the user.
    Returns:
        int: The ID of the newly created user.
    Raises:
        sqlite3.IntegrityError: If the username already exists.
        Exception: For other database errors.
    """
    created_at = datetime.utcnow().isoformat()
    extra_data_json = json.dumps(extra_data) if extra_data is not None else None
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO users (username, password, extra_data, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (username, password, extra_data_json, created_at),
            )
            conn.commit()
            return cursor.lastrowid
    except sqlite3.IntegrityError as e:
        raise
    except Exception as e:
        raise


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """
    Retrieve a user from the database by their user ID.
    Args:
        user_id (int): The user's ID.
    Returns:
        dict or None: The user's data as a dictionary, or None if not found.
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, username, password, extra_data, created_at
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return {
            "id": row[0],
            "username": row[1],
            "password": row[2],
            "extra_data": json.loads(row[3]) if row[3] else None,
            "created_at": row[4],
        }


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a user from the database by their username.
    Args:
        username (str): The user's username.
    Returns:
        dict or None: The user's data as a dictionary, or None if not found.
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, username, password, extra_data, created_at
            FROM users
            WHERE username = ?
            """,
            (username,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return {
            "id": row[0],
            "username": row[1],
            "password": row[2],
            "extra_data": json.loads(row[3]) if row[3] else None,
            "created_at": row[4],
        }
