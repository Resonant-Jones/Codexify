
import os
import shutil
from dotenv import load_dotenv
from guardian.vector.store import VectorStore

# Load env vars
load_dotenv()

# Ensure we use the test database
os.environ["CODEXIFY_CHROMA_PATH"] = "./.chroma_test_store"
os.environ["CODEXIFY_COLLECTION"] = "codexify_vault_test_store"

def verify_store():
    print("Initializing VectorStore (Chroma)...")
    store = VectorStore()
    
    print("Adding test documents...")
    texts = ["The quick brown fox jumps over the lazy dog.", "Codexify is an AI memory system."]
    metas = [{"source": "test", "id": 1}, {"source": "test", "id": 2}]
    
    count = store.add_texts([{"text": t, "meta": m} for t, m in zip(texts, metas)])
    print(f"Added {count} documents.")
    
    print("Searching for 'fox'...")
    results = store.search("fox", k=1)
    print(f"Results: {results}")
    
    if results and "fox" in results[0]["text"]:
        print("✅ Verification Successful: Found 'fox'.")
    else:
        print("❌ Verification Failed: Did not find 'fox'.")

    print("Searching for 'memory'...")
    results = store.search("memory", k=1)
    print(f"Results: {results}")

    if results and "memory" in results[0]["text"]:
        print("✅ Verification Successful: Found 'memory'.")
    else:
        print("❌ Verification Failed: Did not find 'memory'.")

if __name__ == "__main__":
    # Clean up test db
    if os.path.exists("./.chroma_test_store"):
        shutil.rmtree("./.chroma_test_store")
        
    verify_store()
