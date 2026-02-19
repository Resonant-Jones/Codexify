from __future__ import annotations

import logging
import os

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()

"""
Seed a small set of nodes and relationships in the local Neo4j instance so we
can exercise the graph queries during development.
"""


from datetime import datetime, timezone

from neomodel import config, db

BOLT_URL = os.environ.get("BOLT_URL", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASS = os.environ.get("NEO4J_PASS", "guardian")

from guardian.db.neo import MessageNode, ThreadNode, UserNode


def configure_connection() -> None:
    """Load env vars and point neomodel at the configured Bolt URL."""
    # Resolve user / pass with common env var names and safe defaults
    user = os.getenv("NEO4J_USER") or os.getenv("NEO4J_USERNAME") or "neo4j"
    password = (
        os.getenv("NEO4J_PASS") or os.getenv("NEO4J_PASSWORD") or "guardian"
    )

    # Accept either NEO4J_BOLT_URL or BOLT_URL and fall back to localhost with creds
    bolt_url = (
        os.getenv("NEO4J_BOLT_URL")
        or os.getenv("BOLT_URL")
        or f"bolt://{user}:{password}@localhost:7687"
    )

    # If the URL has no embedded credentials, embed the resolved user/pass.
    # e.g. convert 'bolt://localhost:7687' -> 'bolt://user:pass@localhost:7687'
    if "@" not in bolt_url:
        if "://" in bolt_url:
            scheme, rest = bolt_url.split("://", 1)
            bolt_url = f"{scheme}://{user}:{password}@{rest}"
        else:
            bolt_url = f"bolt://{user}:{password}@{bolt_url}"

    # Tell neomodel the database URL and open the connection.
    # NOTE: neomodel's Database.set_connection expects only the URL (no `auth=` kwarg).
    config.DATABASE_URL = bolt_url
    db.set_connection(config.DATABASE_URL)


def ensure_user(name: str, email: str) -> UserNode:
    user = UserNode.nodes.filter(email=email).first()
    if user is None:
        user = UserNode(name=name, email=email)
        user.save()
    else:
        if user.name != name:
            user.name = name
            user.save()
    return user


def ensure_thread(topic: str) -> ThreadNode:
    thread = ThreadNode.nodes.filter(topic=topic).first()
    if thread is None:
        thread = ThreadNode(topic=topic)
        thread.save()
    return thread


def ensure_message(message_id: str, content: str) -> MessageNode:
    message = MessageNode.nodes.filter(message_id=message_id).first()
    if message is None:
        message = MessageNode(
            message_id=message_id,
            content=content,
            created_at=datetime.now(timezone.utc),
        ).save()
    else:
        updated = False
        if message.content != content:
            message.content = content
            updated = True
        if updated:
            message.save()
    return message


def main() -> None:
    configure_connection()

    user = ensure_user("Resonant Jones", "resonant@codexify.ai")
    thread = ensure_thread("Vision Planning")
    message = ensure_message(
        "msg_seed_001",
        "We need to finalize the companion schema for memory integrity.",
    )

    if not message.user.is_connected(user):
        message.user.connect(user)
    if not message.thread.is_connected(thread):
        message.thread.connect(thread)

    logger.info("Seed data inserted (or already present).")


if __name__ == "__main__":
    main()
