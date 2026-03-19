"""
Database seeding script for Guardian.
Initializes baseline data like the default project if the database is empty.
"""

import logging
import os

from guardian.config.db_defaults import DEFAULT_PG_DSN
from guardian.core.default_project import (
    DEFAULT_PROJECT_DESCRIPTION,
    DEFAULT_PROJECT_NAME,
)
from guardian.core.pgdb import PgDB

logger = logging.getLogger(__name__)


def seed():
    """Insert baseline data into the database."""
    # Use env var or default
    dsn = os.environ.get("DATABASE_URL") or DEFAULT_PG_DSN
    db = PgDB(dsn)
    existing = db.list_projects()
    if not existing:
        db.create_project(DEFAULT_PROJECT_NAME, DEFAULT_PROJECT_DESCRIPTION)
        logger.info("Seeded base project: %s", DEFAULT_PROJECT_NAME)
    else:
        logger.info(
            f"Database already has {len(existing)} projects; skipping seed."
        )


if __name__ == "__main__":
    try:
        seed()
    except Exception as e:
        logger.error(f"Failed to seed database: {e}")
        raise
