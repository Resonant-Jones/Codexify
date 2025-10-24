# scripts/chatgpt_import/import_chatgpt.py

import json
from pathlib import Path
from neo4j import GraphDatabase
from datetime import datetime

NEO4J_URL = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASS = "your-password-here"  # replace or load from env

# Path to your exported ChatGPT JSON
INPUT_FILE = Path("chatgpt_migrations/conversation.json")

def parse_timestamp(ts):
    try:
        return datetime.utcfromtimestamp(ts).isoformat()
    except Exception:
        return None

def import_chatgpt():
    data = json.loads(INPUT_FILE.read_text())

    driver = GraphDatabase.driver(NEO4J_URL, auth=(NEO4J_USER, NEO4J_PASS))

    with driver.session() as session:
        for convo in data:
            title = convo.get("title", "Untitled Thread")
            convo_id = f"thread:{convo['mapping'].get('id') or hash(title)}"
            session.run(
                """
                MERGE (t:Thread {id: $id})
                SET t.title = $title
                """,
                id=convo_id,
                title=title,
            )

            # Traverse messages
            for msg_id, node in convo["mapping"].items():
                msg = node.get("message")
                if not msg: continue
                content = msg.get("content", {}).get("parts", [""])[0]
                role = msg.get("author", {}).get("role", "unknown")
                created = parse_timestamp(msg.get("create_time"))

                # Create message node
                session.run(
                    """
                    MERGE (m:Message {id: $id})
                    SET m.content = $content,
                        m.role = $role,
                        m.timestamp = $created
                    """,
                    id=msg_id,
                    content=content,
                    role=role,
                    created=created,
                )

                # Link to thread
                session.run(
                    """
                    MATCH (m:Message {id: $mid}), (t:Thread {id: $tid})
                    MERGE (t)-[:CONTAINS]->(m)
                    """,
                    mid=msg_id,
                    tid=convo_id,
                )

                # Link parent-child
                parent = node.get("parent")
                if parent:
                    session.run(
                        """
                        MATCH (m1:Message {id: $p}), (m2:Message {id: $c})
                        MERGE (m1)-[:REPLIED_WITH]->(m2)
                        """,
                        p=parent,
                        c=msg_id,
                    )

    print("✅ Import complete!")

if __name__ == "__main__":
    import_chatgpt()