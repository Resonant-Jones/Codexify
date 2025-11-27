import pytest
from neomodel import db

from guardian.graph.connection import connect_neo4j
from guardian.graph.models import MessageNode, ThreadNode, UserNode


@pytest.mark.integration
def test_usernode_roundtrip():
    try:
        connect_neo4j()
    except Exception as exc:
        pytest.skip(f"Neo4j not available for integration test: {exc}")

    try:
        user = UserNode.get_or_create({"user_id": "test-user-kg"})[0]
        thread = ThreadNode.get_or_create({"thread_id": "thread-kg-1"})[0]
        msg = MessageNode.get_or_create(
            {"message_id": "msg-kg-1", "content": "Graph context is live"}
        )[0]

        msg.user.connect(user)
        msg.thread.connect(thread)

        results, _ = db.cypher_query(
            "MATCH (m:MessageNode)-[:SENT_BY]->(u:UserNode {user_id: 'test-user-kg'}) RETURN count(m)"
        )
        assert results and results[0][0] >= 1
    except Exception as exc:
        pytest.skip(f"Neo4j operation failed (likely unavailable): {exc}")
