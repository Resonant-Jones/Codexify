from neomodel import config, db
from dotenv import load_dotenv
import os
from pathlib import Path
import pytest


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

    # Grab the database URL from env
    database_url = os.getenv('BOLT_URL') or os.getenv('NEO4J_BOLT_URL')

    if not database_url:
        raise ValueError("BOLT_URL not found in environment variables.")

    # Set the neomodel connection config
    config.DATABASE_URL = database_url

    try:
        # Run a basic Cypher query
        results, meta = db.cypher_query("RETURN 1 AS result")
        if results[0][0] == 1:
            print("✅ Neo4j connection successful.")
        else:
            print("⚠️ Unexpected result from test query.")
    except Exception as e:
        print(f"❌ Neo4j connection failed: {e}")

if __name__ == "__main__":
    test_connection()
