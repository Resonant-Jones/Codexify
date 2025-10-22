# guardian/db/neo.py
from __future__ import annotations

import os
from uuid import uuid4
from datetime import datetime

# --- Neo4j Graph Schema for Relationship Tracking and User-Memory Graphing ---
from neomodel import (
    StructuredNode,
    StringProperty,
    DateTimeProperty,
    RelationshipTo,
    RelationshipFrom,
    UniqueIdProperty,
    StructuredRel,
    config,
)

# Resolve Bolt URL and credentials from environment (support common names)
# Precedence: explicit NEO4J_BOLT_URL or BOLT_URL (host:port), and creds from
# NEO4J_USER/NEO4J_PASS or NEO4J_USERNAME/NEO4J_PASSWORD. We keep the DATABASE_URL
# free of embedded credentials (neo4j python driver warns about username in URI
# for newer driver versions) and pass credentials to GraphDatabase.driver via
# basic_auth when available.

_raw_bolt = os.getenv("NEO4J_BOLT_URL") or os.getenv("BOLT_URL") or "bolt://localhost:7687"
_env_user = os.getenv("NEO4J_USER") or os.getenv("NEO4J_USERNAME")
_env_pass = os.getenv("NEO4J_PASS") or os.getenv("NEO4J_PASSWORD")


def _strip_creds_from_bolt(url: str) -> str:
    """Return the bolt URL with any embedded user:pass@ removed.

    Examples:
        bolt://user:pass@localhost:7687 -> bolt://localhost:7687
        bolt://localhost:7687 -> bolt://localhost:7687
    """
    try:
        scheme, rest = url.split("://", 1)
        if "@" in rest:
            hostpart = rest.split("@", 1)[1]
            return f"{scheme}://{hostpart}"
    except Exception:
        pass
    return url

_clean_url = _strip_creds_from_bolt(_raw_bolt)

# Tell neomodel the database URL (without embedded credentials)
config.DATABASE_URL = _clean_url


# Provide a helper to return a neo4j-driver session (context manager style).
# This will attempt to use env creds first; if none are present and the original
# raw bolt URL contained embedded creds, we will try to extract them as a
# fallback.
def get_session(**kwargs):
    """
    Return a neo4j driver session (context manager style) using resolved env creds.

    Usage:
        with get_session() as session:
            session.run("RETURN 1")
    """
    try:
        from neo4j import GraphDatabase
        # basic_auth exists in neo4j.driver API; import it if available
        try:
            from neo4j import basic_auth
        except Exception:
            basic_auth = None
    except Exception as e:
        raise RuntimeError("neo4j driver is required for get_session: " + str(e)) from e

    user = _env_user
    password = _env_pass

    # If env creds not set, try to parse them from the raw bolt URL (fallback)
    if (not user or not password) and "@" in _raw_bolt and ":" in _raw_bolt:
        try:
            scheme, rest = _raw_bolt.split("://", 1)
            creds, hostrest = rest.split("@", 1)
            if ":" in creds:
                user_parsed, pass_parsed = creds.split(":", 1)
                user = user or user_parsed
                password = password or pass_parsed
        except Exception:
            pass

    # Build auth token if we have credentials. Prefer basic_auth if available.
    auth = None
    if user and password:
        if basic_auth:
            auth = basic_auth(user, password)
        else:
            auth = (user, password)

    # Create the driver. The driver expects a URL without embedded username.
    driver = GraphDatabase.driver(_clean_url, auth=auth) if auth else GraphDatabase.driver(_clean_url)

    # Return a session context; caller should use `with get_session() as s:`
    return driver.session(**kwargs)


class RelationshipMeta(StructuredRel):
    label = StringProperty(required=True)  # e.g. "mother", "mentor", "nemesis"
    since = DateTimeProperty(default_now=True)
    notes = StringProperty()


class UserNode(StructuredNode):
    uid = UniqueIdProperty()
    name = StringProperty(required=True)
    email = StringProperty()
    created_at = DateTimeProperty(default_now=True)

    messages = RelationshipFrom("MessageNode", "SENT_BY")


class MessageNode(StructuredNode):
    message_id = StringProperty(unique_index=True, required=True)
    content = StringProperty()
    created_at = DateTimeProperty(default_now=True)

    user = RelationshipTo("UserNode", "SENT_BY")
    thread = RelationshipTo("ThreadNode", "PART_OF")


class ThreadNode(StructuredNode):
    uid = UniqueIdProperty()
    topic = StringProperty()
    created_at = DateTimeProperty(default_now=True)

    messages = RelationshipFrom("MessageNode", "PART_OF")