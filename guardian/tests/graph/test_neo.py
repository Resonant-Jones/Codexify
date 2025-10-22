import os
from dotenv import load_dotenv
from neomodel import config, db

from db.neo import UserNode, MessageNode, ThreadNode


def _connect_neomodel() -> None:
    load_dotenv()
    bolt_url = os.getenv("NEO4J_BOLT_URL") or os.getenv("BOLT_URL") or "bolt://localhost:7687"
    user = os.getenv("NEO4J_USER") or os.getenv("NEO4J_USERNAME") or "neo4j"
    password = os.getenv("NEO4J_PASS") or os.getenv("NEO4J_PASSWORD") or "guardian"

    config.DATABASE_URL = bolt_url
    # If URL has no credentials, provide auth explicitly to the connection
    db.set_connection(url=config.DATABASE_URL, auth=(user, password))


def test_neomodel_basic_graph():
    _connect_neomodel()

    # Create nodes
    u = UserNode(name="Resonant Jones", email="resonant@codexify.ai").save()
    t = ThreadNode(topic="First Contact with Memory Graph").save()
    m = MessageNode(message_id="test_msg_1", content="The system now remembers...").save()

    # Link relationships if not already connected
    if not m.thread.is_connected(t):
        m.thread.connect(t)
    if not m.user.is_connected(u):
        m.user.connect(u)

    # Verify with a basic query (canonical direction: Message -> User)
    results, _ = db.cypher_query(
        "MATCH (m:MessageNode)-[:SENT_BY]->(u:UserNode) RETURN count(m)"
    )
    assert results and results[0][0] >= 1
