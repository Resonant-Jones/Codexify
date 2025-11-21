import asyncio
import os
import shutil
from dotenv import load_dotenv

# Load env for API keys
load_dotenv()

from guardian.vector.store import VectorStore
from guardian.context.broker import ContextBroker

# Mock ChatDB
class MockChatDB:
    def last_messages(self, thread_id, n=6):
        return []

async def test_chat_memory():
    # Clean up previous test runs
    if os.path.exists("./.chroma_chat_test"):
        shutil.rmtree("./.chroma_chat_test")
        
    # Set env vars for test
    os.environ["CODEXIFY_CHROMA_PATH"] = "./.chroma_chat_test"
    os.environ["CODEXIFY_COLLECTION"] = "test_chat_collection"
    
    print("Initializing components...")
    vector_store = VectorStore()
    chat_db = MockChatDB()
    broker = ContextBroker(chat_db, vector_store)
    
    # Simulate chat loop: User sends a message, it gets embedded
    print("Simulating chat message embedding...")
    message_text = "My favorite color is blue."
    meta = {"role": "user", "timestamp": "2023-01-01T00:00:00"}
    vector_store.add_texts([{"text": message_text, "meta": meta}])
    
    # Simulate retrieval: User asks a question
    print("Simulating retrieval...")
    query = "What is my favorite color?"
    context = await broker.assemble(thread_id=1, query=query, depth="deep")
    
    print("Context retrieved:", context.keys())
    
    # Check if memory contains the message
    found = False
    if "semantic" in context:
        for item in context["semantic"]:
            print(f"Found semantic item: {item}")
            if "blue" in item.get("text", "").lower():
                found = True
                
    if "memory" in context:
        for item in context["memory"]:
            print(f"Found memory item: {item}")
            if "blue" in item.get("text", "").lower():
                found = True

    if found:
        print("✅ Verification Successful: Memory retrieved.")
    else:
        print("❌ Verification Failed: Memory NOT retrieved.")
        
    # Cleanup
    if os.path.exists("./.chroma_chat_test"):
        shutil.rmtree("./.chroma_chat_test")

if __name__ == "__main__":
    asyncio.run(test_chat_memory())
