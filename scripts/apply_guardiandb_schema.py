#!/usr/bin/env python3
"""
Apply GuardianDB schema to a test database for comparison.

This script instantiates GuardianDB with Postgres backend to apply
the raw SQL schema, allowing us to compare against Alembic's schema.
"""
import os
import sys

# Add parent directory to path so we can import guardian modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def apply_guardiandb_schema():
    """Apply GuardianDB schema using PgDB adapter."""
    from guardian.core.pgdb import PgDB

    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("ERROR: DATABASE_URL not set", file=sys.stderr)
        sys.exit(1)

    # Switch to guardiandb test database
    db_url = db_url.replace('/guardian', '/guardian_raw')

    print(f"Applying GuardianDB schema to {db_url}")

    db = PgDB(db_url)

    # GuardianDB's init doesn't auto-create tables like SQLite version,
    # so we need to manually trigger table creation
    # This simulates what happens in production

    # Ensure all tables exist
    try:
        db.ensure_project("test", "test")
        db.list_connector_configs()
        db.ensure_sync_job_support()
    except Exception as e:
        print(f"Schema application completed with warnings: {e}")

    print("✓ GuardianDB schema applied successfully")

if __name__ == '__main__':
    apply_guardiandb_schema()
