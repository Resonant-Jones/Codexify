"""
SQLite Media Tables Setup for Guardian
=========================================

This module sets up the media management tables in SQLite for immediate use.
It creates the same schema structure as PostgreSQL but adapted for SQLite.
"""

import logging
import sqlite3
from pathlib import Path
from typing import Dict

logger = logging.getLogger(__name__)


class SQLiteMediaSetup:
    """Handles SQLite media table setup for Guardian."""

    def __init__(self, db_path: str = "guardian.db"):
        self.db_path = db_path

    def test_connection(self) -> bool:
        """Test connection to SQLite database."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Failed to connect to SQLite: {e}")
            return False

    def run_migration(self, migration_file: str) -> bool:
        """Run a SQL migration file adapted for SQLite."""
        try:
            # Read the PostgreSQL migration and adapt it for SQLite
            migration_path = Path(migration_file)
            if not migration_path.exists():
                logger.error(f"Migration file not found: {migration_file}")
                return False

            with open(migration_file) as f:
                sql_content = f.read()

            # Adapt PostgreSQL syntax to SQLite
            sqlite_content = self._adapt_postgres_to_sqlite(sql_content)

            # Execute the migration
            conn = sqlite3.connect(self.db_path)
            with conn:
                conn.executescript(sqlite_content)
            conn.close()

            logger.info(f"Migration '{migration_file}' executed successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to run migration: {e}")
            return False

    def _adapt_postgres_to_sqlite(self, postgres_sql: str) -> str:
        """Adapt PostgreSQL SQL to SQLite syntax."""
        sqlite_sql = postgres_sql

        # Replace PostgreSQL-specific syntax with SQLite equivalents
        replacements = {
            "UUID PRIMARY KEY DEFAULT gen_random_uuid()": "TEXT PRIMARY KEY",
            "UUID NOT NULL": "TEXT NOT NULL",
            "UUID": "TEXT",
            "TIMESTAMPTZ DEFAULT now()": "TEXT DEFAULT (datetime('now'))",
            "TIMESTAMPTZ": "TEXT",
            "BIGINT NOT NULL": "INTEGER NOT NULL",
            "BIGINT": "INTEGER",
            "CHECK (format IN ('txt', 'md', 'docx', 'pdf', 'html', 'json'))": "",  # Remove CHECK constraints for simplicity
            "USING GIN (to_tsvector('english', parsed_text))": "",  # Remove GIN index
            "to_tsvector('english', COALESCE(parsed_text, '')) @@ plainto_tsquery('english', ?)": "parsed_text LIKE '%' || ? || '%'",  # Simple text search
            "CREATE OR REPLACE FUNCTION update_updated_at_column()": "-- SQLite uses triggers differently",
            "language 'plpgsql'": "",
            "CREATE TRIGGER": "-- SQLite trigger syntax",
            "FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()": "",
            "gen_random_uuid()": "(lower(hex(randomblob(16))))",  # Simple UUID generation
        }

        for postgres_syntax, sqlite_syntax in replacements.items():
            sqlite_sql = sqlite_sql.replace(postgres_syntax, sqlite_syntax)

        # Remove PostgreSQL-specific commands
        lines = sqlite_sql.split("\n")
        filtered_lines = []
        for line in lines:
            # Skip PostgreSQL-specific lines
            if any(
                skip in line
                for skip in [
                    "CREATE OR REPLACE FUNCTION",
                    "language 'plpgsql'",
                    "RETURNS TRIGGER",
                    "CREATE TRIGGER",
                    "FOR EACH ROW EXECUTE FUNCTION",
                    "USING GIN",
                    "to_tsvector",
                    "plainto_tsquery",
                ]
            ):
                continue

            # Replace UUID generation in INSERT statements
            if "DEFAULT gen_random_uuid()" in line:
                line = line.replace(
                    "DEFAULT gen_random_uuid()",
                    "DEFAULT (lower(hex(randomblob(16))))",
                )

            filtered_lines.append(line)

        return "\n".join(filtered_lines)

    def create_media_tables(self) -> bool:
        """Create media tables directly in SQLite."""
        try:
            conn = sqlite3.connect(self.db_path)

            # Create generated_images table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS generated_images (
                    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
                    project_id TEXT NOT NULL,
                    thread_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    src_url TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    model TEXT NOT NULL,
                    created_at TEXT DEFAULT (datetime('now')),
                    updated_at TEXT DEFAULT (datetime('now')),
                    deleted_at TEXT DEFAULT NULL,

                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                    FOREIGN KEY (thread_id) REFERENCES threads(id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """
            )

            # Create uploaded_images table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS uploaded_images (
                    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
                    project_id TEXT NOT NULL,
                    thread_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    src_url TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    filesize INTEGER NOT NULL,
                    mime_type TEXT NOT NULL,
                    source_tag TEXT DEFAULT NULL,
                    created_at TEXT DEFAULT (datetime('now')),
                    updated_at TEXT DEFAULT (datetime('now')),
                    deleted_at TEXT DEFAULT NULL,

                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                    FOREIGN KEY (thread_id) REFERENCES threads(id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """
            )

            # Create generated_documents table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS generated_documents (
                    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
                    project_id TEXT NOT NULL,
                    thread_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    format TEXT NOT NULL,
                    model TEXT NOT NULL,
                    created_at TEXT DEFAULT (datetime('now')),
                    updated_at TEXT DEFAULT (datetime('now')),
                    deleted_at TEXT DEFAULT NULL,

                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                    FOREIGN KEY (thread_id) REFERENCES threads(id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """
            )

            # Create uploaded_documents table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS uploaded_documents (
                    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
                    project_id TEXT NOT NULL,
                    thread_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    filesize INTEGER NOT NULL,
                    mime_type TEXT NOT NULL,
                    src_url TEXT NOT NULL,
                    source_tag TEXT DEFAULT NULL,
                    parsed_text TEXT DEFAULT NULL,
                    created_at TEXT DEFAULT (datetime('now')),
                    updated_at TEXT DEFAULT (datetime('now')),
                    deleted_at TEXT DEFAULT NULL,

                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                    FOREIGN KEY (thread_id) REFERENCES threads(id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """
            )

            # Create indices for fast lookups
            tables = [
                "generated_images",
                "uploaded_images",
                "generated_documents",
                "uploaded_documents",
            ]
            for table in tables:
                conn.execute(
                    f"CREATE INDEX IF NOT EXISTS idx_{table}_project_id ON {table}(project_id) WHERE deleted_at IS NULL"
                )
                conn.execute(
                    f"CREATE INDEX IF NOT EXISTS idx_{table}_thread_id ON {table}(thread_id) WHERE deleted_at IS NULL"
                )
                conn.execute(
                    f"CREATE INDEX IF NOT EXISTS idx_{table}_user_id ON {table}(user_id) WHERE deleted_at IS NULL"
                )
                conn.execute(
                    f"CREATE INDEX IF NOT EXISTS idx_{table}_created_at ON {table}(created_at DESC) WHERE deleted_at IS NULL"
                )

            conn.close()

            logger.info("Media tables created successfully in SQLite")
            return True

        except Exception as e:
            logger.error(f"Failed to create media tables: {e}")
            return False

    def test_tables(self) -> Dict[str, bool]:
        """Test if all required tables exist."""
        required_tables = [
            "generated_images",
            "uploaded_images",
            "generated_documents",
            "uploaded_documents",
        ]

        results = {}

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            for table in required_tables:
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                    (table,),
                )
                exists = cursor.fetchone() is not None
                results[table] = exists

            conn.close()
            return results

        except Exception as e:
            logger.error(f"Failed to test tables: {e}")
            return {table: False for table in required_tables}


def setup_sqlite_media(db_path: str = "guardian.db") -> bool:
    """
    Complete SQLite media setup for Guardian.

    Args:
        db_path: Path to SQLite database file

    Returns:
        True if setup successful, False otherwise
    """
    setup = SQLiteMediaSetup(db_path)

    logger.info("Starting SQLite media setup for Guardian...")

    # Test connection
    if not setup.test_connection():
        logger.error("Cannot connect to SQLite database")
        return False

    # Create media tables
    if not setup.create_media_tables():
        logger.error("Failed to create media tables")
        return False

    logger.info("SQLite media setup completed successfully!")
    return True


def migrate_postgres_to_sqlite(
    postgres_migration_file: str, sqlite_db_path: str = "guardian.db"
) -> bool:
    """
    Migrate PostgreSQL schema to SQLite.

    Args:
        postgres_migration_file: Path to PostgreSQL migration file
        sqlite_db_path: Path to SQLite database

    Returns:
        True if migration successful, False otherwise
    """
    setup = SQLiteMediaSetup(sqlite_db_path)

    logger.info("Migrating PostgreSQL schema to SQLite...")

    if not setup.test_connection():
        logger.error("Cannot connect to SQLite database")
        return False

    if not setup.run_migration(postgres_migration_file):
        logger.error("Failed to run migration")
        return False

    logger.info("Migration completed successfully!")
    return True


if __name__ == "__main__":
    # Quick setup for immediate use
    success = setup_sqlite_media("guardian.db")

    if success:
        logger.info("SQLite media setup completed!")

        # Test the tables
        setup = SQLiteMediaSetup("guardian.db")
        results = setup.test_tables()
        for table, exists in results.items():
            status = "EXISTS" if exists else "MISSING"
            logger.info(f"{status}: {table}")
    else:
        logger.error("SQLite media setup failed!")
