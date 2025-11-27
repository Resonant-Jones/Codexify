#!/usr/bin/env python3
"""
Debug script to inspect ChromaDB contents
"""
import os

from dotenv import load_dotenv

load_dotenv()

# Use test DB path
os.environ["CODEXIFY_CHROMA_PATH"] = "./.chroma_test"
os.environ["CODEXIFY_COLLECTION"] = "codexify_vault_test"

import chromadb


def inspect_chroma():
    chroma_path = os.getenv("CODEXIFY_CHROMA_PATH", "./.chroma_test")
    collection_name = os.getenv("CODEXIFY_COLLECTION", "codexify_vault_test")

    print(f"Inspecting ChromaDB at: {chroma_path}")
    print(f"Collection: {collection_name}")
    print("-" * 60)

    client = chromadb.PersistentClient(path=chroma_path)
    collection = client.get_or_create_collection(name=collection_name)

    # Get all items
    results = collection.get()

    print(f"Total documents in collection: {len(results['ids'])}")
    print()

    if results["ids"]:
        for i, doc_id in enumerate(results["ids"]):
            print(f"Document {i+1}:")
            print(f"  ID: {doc_id}")
            print(f"  Text: {results['documents'][i][:100]}...")
            if results["metadatas"] and i < len(results["metadatas"]):
                print(f"  Metadata: {results['metadatas'][i]}")
            print()
    else:
        print("⚠️  Collection is empty!")


if __name__ == "__main__":
    inspect_chroma()
