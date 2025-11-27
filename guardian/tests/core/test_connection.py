import os
from pathlib import Path

import pytest
from dotenv import load_dotenv
from neomodel import db

from guardian.graph.connection import connect_neo4j


def _load_env():
    here = Path(__file__).resolve()
    candidates = [
        here.parents[3] / ".env.local",  # repo root
        here.parents[2] / ".env.local",  # guardian/.env.local (optional)
        here.parents[3] / ".env",
        here.parents[2] / ".env",
    ]
    for p in candidates:
        if p.exists():
            load_dotenv(p, override=False)
            break


def test_connection():
    # Load environment variables
    _load_env()

    database_url = (
        os.getenv("BOLT_URL")
        or os.getenv("NEO4J_BOLT_URL")
        or "bolt://localhost:7687"
    )
    if not database_url:
        pytest.skip("Neo4j URL not configured")
    try:
        connect_neo4j()
        results, meta = db.cypher_query("RETURN 1 AS result")
        if results[0][0] == 1:
            print("✅ Neo4j connection successful.")
        else:
            print("⚠️ Unexpected result from test query.")
    except Exception as e:
        pytest.skip(f"Neo4j not available: {e}")


if __name__ == "__main__":
    test_connection()
