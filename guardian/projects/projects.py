import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "guardian.db")


def get_connection():
    """
    Establish and return a connection to the SQLite database.
    """
    return sqlite3.connect(DB_PATH)


def init_projects_table():
    """
    Create the 'projects' table in the database if it does not already exist.
    The table includes columns for id, name, description, and created_at timestamp.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        -- Other tables should include: project_id INTEGER, FOREIGN KEY(project_id) REFERENCES projects(id)
    """
    )
    conn.commit()
    conn.close()


def create_project(name: str, description: str = "") -> int:
    """
    Insert a new project into the 'projects' table.

    Args:
        name (str): The name of the project.
        description (str, optional): A description of the project. Defaults to "".

    Returns:
        int: The ID of the newly created project.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO projects (name, description)
        VALUES (?, ?)
    """,
        (name, description),
    )
    conn.commit()
    project_id = cursor.lastrowid
    conn.close()
    return project_id


def list_projects() -> list:
    """
    Retrieve all projects from the 'projects' table.

    Returns:
        list: A list of tuples, each containing (id, name, description, created_at).
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, description, created_at FROM projects")
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_project_by_id(project_id: int):
    """
    Retrieve a single project by its ID.

    Args:
        project_id (int): The ID of the project to retrieve.

    Returns:
        tuple or None: A tuple (id, name, description, created_at) if found, else None.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, description, created_at FROM projects WHERE id = ?",
        (project_id,),
    )
    project = cursor.fetchone()
    conn.close()
    return project


def delete_project(project_id: int) -> bool:
    """
    Delete a project from the 'projects' table by its ID.

    Args:
        project_id (int): The ID of the project to delete.

    Returns:
        bool: True if a project was deleted, False otherwise.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted
