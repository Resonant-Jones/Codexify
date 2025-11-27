#!/usr/bin/env python3
"""
Introspect database schema and output as JSON for comparison.

Usage:
    python introspect_schema.py alembic > alembic_schema.json
    python introspect_schema.py guardiandb > guardiandb_schema.json
"""
import json
import os
import sys

from sqlalchemy import create_engine, inspect


def introspect_schema(db_url: str) -> dict:
    """Introspect database schema and return structured data."""
    engine = create_engine(db_url)
    inspector = inspect(engine)

    schema = {}
    for table_name in inspector.get_table_names():
        columns = {}
        for col in inspector.get_columns(table_name):
            columns[col["name"]] = {
                "type": str(col["type"]),
                "nullable": col["nullable"],
                "default": str(col.get("default"))
                if col.get("default")
                else None,
                "autoincrement": col.get("autoincrement", False),
            }

        indexes = []
        for idx in inspector.get_indexes(table_name):
            indexes.append(
                {
                    "name": idx["name"],
                    "columns": idx["column_names"],
                    "unique": idx.get("unique", False),
                }
            )

        foreign_keys = []
        for fk in inspector.get_foreign_keys(table_name):
            foreign_keys.append(
                {
                    "constrained_columns": fk["constrained_columns"],
                    "referred_table": fk["referred_table"],
                    "referred_columns": fk["referred_columns"],
                }
            )

        schema[table_name] = {
            "columns": columns,
            "indexes": indexes,
            "foreign_keys": foreign_keys,
        }

    return schema


def main():
    if len(sys.argv) < 2:
        print(
            "Usage: introspect_schema.py <alembic|guardiandb>", file=sys.stderr
        )
        sys.exit(1)

    mode = sys.argv[1]
    db_url = os.getenv("DATABASE_URL")

    if not db_url:
        print(
            "ERROR: DATABASE_URL environment variable not set", file=sys.stderr
        )
        sys.exit(1)

    if mode == "guardiandb":
        # Switch to guardiandb database
        db_url = db_url.replace("/guardian", "/guardian_raw")

    schema = introspect_schema(db_url)
    print(json.dumps(schema, indent=2))


if __name__ == "__main__":
    main()
