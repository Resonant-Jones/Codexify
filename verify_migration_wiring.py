import json
import os
import sys
from unittest.mock import MagicMock, patch

from dotenv import load_dotenv

# Load env vars
load_dotenv()

# Ensure we use the test database
os.environ["CODEXIFY_CHROMA_PATH"] = "./.chroma_test"
os.environ["CODEXIFY_COLLECTION"] = "codexify_vault_test"

# Mock Neo4j before importing the migration module
sys.modules["guardian.db.neo"] = MagicMock()
sys.modules[
    "guardian.db.neo"
].get_session.return_value.__enter__.return_value = MagicMock()

from backend.rag.chatgpt_migration import ingest_chatgpt_export
from guardian.core.dependencies import init_database
from guardian.vector.store import VectorStore

# Initialize DB for test
init_database()


def verify_migration():
    print("Creating mock ChatGPT export...")
    mock_export = [
        {
            "title": "Test Thread",
            "create_time": 1672531200,
            "mapping": {
                "msg_1": {
                    "message": {
                        "id": "msg_1",
                        "role": "user",
                        "content": {"parts": ["Hello from ChatGPT migration"]},
                        "create_time": 1672531200,
                    }
                },
                "msg_2": {
                    "message": {
                        "id": "msg_2",
                        "role": "assistant",
                        "content": {"parts": ["I am a migrated memory"]},
                        "create_time": 1672531205,
                    }
                },
            },
        }
    ]

    export_bytes = json.dumps(mock_export).encode("utf-8")

    print("Running ingestion...")
    try:
        stats = ingest_chatgpt_export(export_bytes, user_id="test_user")
        print(f"Ingestion stats: {stats}")
    except Exception as e:
        print(f"Ingestion failed: {e}")
        # If it failed due to Neo4j mock issues, we might still want to check Chroma
        pass

    print("Verifying retrieval from VectorStore...")
    store = VectorStore()

    # Search for the migrated content
    results = store.search("migrated memory", k=5)
    print(f"Search results: {results}")

    if results and len(results) > 0:
        print(
            "✅ Verification Successful: Migrated content found in VectorStore."
        )
        print(f"   Found {len(results)} results")
        for i, r in enumerate(results[:3]):
            print(f"   Result {i+1}: {r['text'][:60]}...")
    else:
        print("❌ Verification Failed: Migrated content NOT found.")


if __name__ == "__main__":
    # Clean up test db
    import shutil

    if os.path.exists("./.chroma_test"):
        shutil.rmtree("./.chroma_test")

    verify_migration()
