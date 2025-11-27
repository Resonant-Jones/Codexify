from __future__ import annotations

import os
from urllib.parse import urlparse

import pytest
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()


def _resolve_neo4j_config() -> tuple[str, tuple[str, str]]:
    # Prefer explicit bolt URL from env (supports both names)
    raw_url = (
        os.getenv("NEO4J_BOLT_URL")
        or os.getenv("BOLT_URL")
        or "bolt://localhost:7687"
    )

    # Accept both NEO4J_USER/NEO4J_USERNAME and NEO4J_PASS/NEO4J_PASSWORD
    env_user = os.getenv("NEO4J_USER") or os.getenv("NEO4J_USERNAME") or "neo4j"
    env_pass = (
        os.getenv("NEO4J_PASS") or os.getenv("NEO4J_PASSWORD") or "guardian"
    )

    parsed = urlparse(raw_url)
    # Strip any embedded credentials from URL and use them as auth if present
    user = parsed.username or env_user
    password = parsed.password or env_pass
    host_port = parsed.hostname or "localhost"
    if parsed.port:
        host_port = f"{host_port}:{parsed.port}"

    bolt_url = f"bolt://{host_port}"
    return bolt_url, (user, password)


@pytest.fixture(scope="module")
def neo4j_driver():
    bolt_url, auth = _resolve_neo4j_config()
    driver = GraphDatabase.driver(bolt_url, auth=auth)
    yield driver
    driver.close()


"""Note: seed is provided session-wide in guardian/conftest.py (seed_neo4j_graph)."""


def test_neo4j_connection(neo4j_driver):
    with neo4j_driver.session() as session:
        result = session.run("RETURN 1 AS result")
        assert result.single()["result"] == 1


def test_usernode_exists(neo4j_driver):
    with neo4j_driver.session() as session:
        result = session.run("MATCH (u:UserNode) RETURN count(u) AS count")
        count = result.single()["count"]
        assert count >= 1


def test_relationships_exist(neo4j_driver):
    with neo4j_driver.session() as session:
        # Canonical direction: (MessageNode)-[:SENT_BY]->(UserNode)
        result = session.run(
            "MATCH (m:MessageNode)-[:SENT_BY]->(u:UserNode) RETURN count(*) AS rels"
        )
        assert result.single()["rels"] >= 1


def test_seed_run():
    """
    Dummy test to validate that seed script runs without crashing.
    """
    try:
        from tests.db.test_seed import main

        main()
    except Exception as e:
        pytest.fail(f"Seeding failed with exception: {e}")
