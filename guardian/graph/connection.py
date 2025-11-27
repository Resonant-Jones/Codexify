"""Centralized Neo4j connection helper for neomodel."""
from __future__ import annotations

import os

from dotenv import load_dotenv
from neomodel import db


def connect_neo4j() -> None:
    """Configure neomodel's connection based on environment variables.

    Uses NEO4J_BOLT_URL or BOLT_URL, plus optional NEO4J_USER / NEO4J_PASS.
    If user/pass are provided and not already embedded, they are injected
    into the bolt URL (bolt://user:pass@host:port).
    """
    load_dotenv()

    bolt_url = (
        os.getenv("NEO4J_BOLT_URL")
        or os.getenv("BOLT_URL")
        or "bolt://localhost:7687"
    )
    user = os.getenv("NEO4J_USER") or os.getenv("NEO4J_USERNAME") or "neo4j"
    password = (
        os.getenv("NEO4J_PASS") or os.getenv("NEO4J_PASSWORD") or "guardian"
    )

    if (
        user
        and password
        and "@" not in bolt_url
        and bolt_url.startswith("bolt://")
    ):
        bolt_url = bolt_url.replace("bolt://", f"bolt://{user}:{password}@", 1)

    db.set_connection(url=bolt_url)
