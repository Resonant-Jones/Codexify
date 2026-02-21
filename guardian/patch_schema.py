import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = Path("guardian.db")


def patch_schema():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        try:
            cursor.execute(
                "ALTER TABLE memory ADD COLUMN type TEXT DEFAULT 'log'"
            )
        except sqlite3.OperationalError:
            logger.info("Column 'type' already exists.")

        try:
            cursor.execute("ALTER TABLE memory ADD COLUMN parent_id INTEGER")
        except sqlite3.OperationalError:
            logger.info("Column 'parent_id' already exists.")

        try:
            cursor.execute("ALTER TABLE memory ADD COLUMN source TEXT")
        except sqlite3.OperationalError:
            logger.info("Column 'source' already exists.")

        try:
            cursor.execute("ALTER TABLE memory ADD COLUMN related_to INTEGER")
        except sqlite3.OperationalError:
            logger.info("Column 'related_to' already exists.")

        try:
            cursor.execute(
                "ALTER TABLE memory ADD COLUMN priority INTEGER DEFAULT 1"
            )
        except sqlite3.OperationalError:
            logger.info("Column 'priority' already exists.")

        conn.commit()


if __name__ == "__main__":
    patch_schema()
