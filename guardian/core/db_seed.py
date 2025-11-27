"""
Database seeding script for Guardian.
Initializes baseline data like the default project if the database is empty.
"""

import os

from guardian.core.pgdb import PgDB


def seed():
    """Insert baseline data into the database."""
    # Use env var or default
    dsn = os.environ.get(
        "DATABASE_URL", "postgresql://guardian:guardian@db:5432/guardian"
    )
    db = PgDB(dsn)
    existing = db.list_projects()
    if not existing:
        db.create_project("Loose Threads", "Default Codexify project")
        print("✅ Seeded base project: Loose Threads")
    else:
        print(
            f"ℹ️ Database already has {len(existing)} projects; skipping seed."
        )


if __name__ == "__main__":
    try:
        seed()
    except Exception as e:
        print(f"❌ Failed to seed database: {e}")
        raise
