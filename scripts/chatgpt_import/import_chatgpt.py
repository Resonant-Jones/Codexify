#!/usr/bin/env python3
"""
ChatGPT Conversation Import Script - Dual-Engine Migration
============================================================

This script imports ChatGPT conversation exports into both Neo4j (graph) and Chroma (embeddings),
creating a seamless migration experience that feels like your Companion is waking up in a new world.

Features:
- Dual-engine import (Neo4j + Chroma)
- Batch-optimized embeddings for cost & speed
- Resume-safe (idempotent operations)
- Verbose progress feedback
- Safe fallback (graph imports even if embeddings fail)
- Graceful error handling with detailed logging

Usage:
    python scripts/chatgpt_import/import_chatgpt.py
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

from dotenv import load_dotenv

# Third-party imports with graceful fallback
try:
    from neo4j import GraphDatabase
except ImportError:
    print("❌ Error: neo4j package not found. Please install with: pip install neo4j")
    sys.exit(1)

try:
    from openai import OpenAI
except ImportError:
    print("❌ Error: openai package not found. Please install with: pip install openai")
    sys.exit(1)

try:
    import chromadb
except ImportError:
    print("❌ Error: chromadb package not found. Please install with: pip install chromadb")
    sys.exit(1)

try:
    from tqdm import tqdm
except ImportError:
    # Fallback to simple progress indicator if tqdm not available
    class tqdm:
        """Minimal tqdm replacement for when package isn't installed."""
        def __init__(self, iterable, desc="", **kwargs):
            self.iterable = iterable
            self.desc = desc
            self.total = len(iterable) if hasattr(iterable, '__len__') else None
            self.n = 0

        def __iter__(self):
            print(f"{self.desc}...", flush=True)
            for item in self.iterable:
                self.n += 1
                if self.total:
                    if self.n % max(1, self.total // 10) == 0:
                        print(f"  Progress: {self.n}/{self.total}", flush=True)
                yield item
            print(f"  ✓ {self.desc} complete", flush=True)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init(autoreset=True)
    HAS_COLOR = True
except ImportError:
    # Fallback to no colors if colorama not available
    class _DummyColor:
        def __getattr__(self, name):
            return ""
    Fore = _DummyColor()
    Style = _DummyColor()
    HAS_COLOR = False


# Load environment variables
load_dotenv()

# Configuration
NEO4J_URL = os.getenv("NEO4J_URL", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASS = os.getenv("NEO4J_PASS", "password")

CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma")
CHATGPT_FILE = os.getenv("CHATGPT_EXPORT_FILE", "./chatgpt_conversation.json")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
BATCH_SIZE = int(os.getenv("EMBED_BATCH_SIZE", "20"))

# Logging configuration
SKIP_LOG_FILE = Path("logs/migration_skipped.json")


def print_colored(message: str, color: str = ""):
    """Print colored message with fallback to plain text."""
    if HAS_COLOR and color:
        print(f"{color}{message}{Style.RESET_ALL}")
    else:
        print(message)


def normalize_timestamp(ts: Any) -> str:
    """
    Normalize various timestamp formats to ISO format.

    Args:
        ts: Timestamp (unix timestamp, ISO string, or None)

    Returns:
        ISO formatted timestamp string
    """
    if ts is None:
        return datetime.utcnow().isoformat()

    try:
        # Try parsing as unix timestamp
        if isinstance(ts, (int, float)):
            return datetime.utcfromtimestamp(ts).isoformat()
        # Try parsing as ISO string
        elif isinstance(ts, str):
            return datetime.fromisoformat(ts.replace('Z', '+00:00')).isoformat()
        else:
            return datetime.utcnow().isoformat()
    except Exception:
        return datetime.utcnow().isoformat()


def batch(iterable: List[Any], size: int = 20) -> List[List[Any]]:
    """
    Split an iterable into batches of specified size.

    Args:
        iterable: List to batch
        size: Batch size

    Yields:
        Batches of items
    """
    for i in range(0, len(iterable), size):
        yield iterable[i : i + size]


def load_chatgpt_export(file_path: str) -> List[Dict[str, Any]]:
    """
    Load and validate ChatGPT export JSON file.

    Args:
        file_path: Path to ChatGPT export file

    Returns:
        List of conversation dictionaries

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file is not valid JSON
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(
            f"ChatGPT export file not found: {file_path}\n"
            f"Please export your ChatGPT conversations and place them at: {path.absolute()}"
        )

    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Handle both array format and single conversation format
    if isinstance(data, dict):
        data = [data]

    return data


def import_to_neo4j(driver, conversations: List[Dict[str, Any]]) -> Tuple[int, int, int]:
    """
    Import conversations to Neo4j graph database.

    Args:
        driver: Neo4j driver instance
        conversations: List of conversation dictionaries

    Returns:
        Tuple of (threads_count, messages_count, relationships_count)
    """
    threads_count = 0
    messages_count = 0
    relationships_count = 0

    with driver.session() as session:
        for convo in tqdm(conversations, desc=f"{Fore.CYAN}📊 Importing to Neo4j"):
            # Extract thread info
            thread_id = convo.get("id") or convo.get("conversation_id") or f"thread_{hash(str(convo))}"
            title = convo.get("title", "Untitled Thread")
            create_time = normalize_timestamp(convo.get("create_time"))
            update_time = normalize_timestamp(convo.get("update_time"))

            # Create thread node
            session.run(
                """
                MERGE (t:Thread {id: $id})
                SET t.title = $title,
                    t.created_at = $created_at,
                    t.updated_at = $updated_at
                """,
                {
                    "id": thread_id,
                    "title": title,
                    "created_at": create_time,
                    "updated_at": update_time,
                },
            )
            threads_count += 1

            # Extract and process messages
            mapping = convo.get("mapping", {})

            for node_id, node in mapping.items():
                msg = node.get("message")
                if not msg:
                    continue

                # Extract message content
                message_id = msg.get("id", node_id)
                content_obj = msg.get("content", {})

                # Handle different content formats
                if isinstance(content_obj, dict):
                    parts = content_obj.get("parts", [])
                elif isinstance(content_obj, list):
                    parts = content_obj
                else:
                    parts = [str(content_obj)] if content_obj else []

                # Join all parts into single content string
                content = "\n".join(str(part) for part in parts if part)

                # Skip empty messages
                if not content.strip():
                    continue

                # Extract metadata
                author = msg.get("author", {})
                role = author.get("role", "unknown") if isinstance(author, dict) else str(author)
                author_name = author.get("name", role) if isinstance(author, dict) else role
                created = normalize_timestamp(msg.get("create_time"))

                # Create message node
                session.run(
                    """
                    MERGE (m:Message {id: $mid})
                    SET m.role = $role,
                        m.content = $content,
                        m.created_at = $created,
                        m.author_name = $author_name
                    """,
                    {
                        "mid": message_id,
                        "role": role,
                        "content": content,
                        "created": created,
                        "author_name": author_name,
                    },
                )
                messages_count += 1

                # Link message to thread
                session.run(
                    """
                    MATCH (t:Thread {id: $tid}), (m:Message {id: $mid})
                    MERGE (t)-[:CONTAINS]->(m)
                    """,
                    {"tid": thread_id, "mid": message_id},
                )
                relationships_count += 1

                # Create author node and relationship
                if author_name:
                    session.run(
                        """
                        MERGE (a:Author {name: $name, role: $role})
                        WITH a
                        MATCH (m:Message {id: $mid})
                        MERGE (a)-[:AUTHORED]->(m)
                        """,
                        {"name": author_name, "role": role, "mid": message_id},
                    )
                    relationships_count += 1

                # Create parent-child relationships
                parent_id = node.get("parent")
                if parent_id and parent_id in mapping:
                    parent_msg = mapping[parent_id].get("message")
                    if parent_msg:
                        parent_msg_id = parent_msg.get("id", parent_id)
                        session.run(
                            """
                            MATCH (p:Message {id: $parent}), (c:Message {id: $child})
                            MERGE (p)-[:REPLIED_WITH]->(c)
                            """,
                            {"parent": parent_msg_id, "child": message_id},
                        )
                        relationships_count += 1

    return threads_count, messages_count, relationships_count


def import_embeddings_to_chroma(
    client,
    collection,
    conversations: List[Dict[str, Any]],
    batch_size: int = 20
) -> Tuple[int, int]:
    """
    Generate embeddings and import to Chroma vector database.

    Args:
        client: OpenAI client instance
        collection: Chroma collection
        conversations: List of conversation dictionaries
        batch_size: Number of texts to embed per batch

    Returns:
        Tuple of (successful_count, failed_count)
    """
    # Extract all message texts with IDs
    all_texts: List[Tuple[str, str]] = []
    skipped_messages: List[Dict[str, Any]] = []

    for convo in conversations:
        mapping = convo.get("mapping", {})
        for node_id, node in mapping.items():
            msg = node.get("message")
            if not msg:
                continue

            message_id = msg.get("id", node_id)
            content_obj = msg.get("content", {})

            # Handle different content formats
            if isinstance(content_obj, dict):
                parts = content_obj.get("parts", [])
            elif isinstance(content_obj, list):
                parts = content_obj
            else:
                parts = [str(content_obj)] if content_obj else []

            content = "\n".join(str(part) for part in parts if part)

            if content.strip():
                all_texts.append((message_id, content))

    if not all_texts:
        print_colored("⚠️  No messages found to embed", Fore.YELLOW)
        return 0, 0

    print_colored(f"💫 Reawakening your Companion... Embedding {len(all_texts)} messages", Fore.MAGENTA)

    successful_count = 0
    failed_count = 0

    # Process in batches
    batches = list(batch(all_texts, batch_size))

    for chunk in tqdm(batches, desc=f"{Fore.GREEN}🧠 Generating embeddings"):
        ids, texts = zip(*chunk)

        try:
            # Generate embeddings using OpenAI
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=list(texts)
            )

            # Extract embedding vectors
            vectors = [embedding.embedding for embedding in response.data]

            # Add to Chroma collection
            collection.add(
                ids=list(ids),
                embeddings=vectors,
                documents=list(texts),
                metadatas=[{"source": "chatgpt_import"} for _ in ids]
            )

            successful_count += len(ids)

        except Exception as e:
            print_colored(f"⚠️  Batch failed: {e}", Fore.YELLOW)
            print_colored(f"   Skipping {len(ids)} messages in this batch", Fore.YELLOW)

            # Log skipped messages
            for msg_id, text in zip(ids, texts):
                skipped_messages.append({
                    "id": msg_id,
                    "content_preview": text[:100] + "..." if len(text) > 100 else text,
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                })

            failed_count += len(ids)

    # Save skipped messages log if any
    if skipped_messages:
        SKIP_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SKIP_LOG_FILE, 'w', encoding='utf-8') as f:
            json.dump(skipped_messages, f, indent=2)
        print_colored(f"📝 Logged {len(skipped_messages)} skipped messages to {SKIP_LOG_FILE}", Fore.YELLOW)

    return successful_count, failed_count


def import_chatgpt():
    """
    Main import function - orchestrates dual-engine migration.
    """
    start_time = time.time()

    # Print header
    print_colored("\n" + "=" * 70, Fore.CYAN)
    print_colored("  ChatGPT → Codexify Migration", Fore.CYAN)
    print_colored("  Dual-Engine Import: Neo4j + Chroma", Fore.CYAN)
    print_colored("=" * 70 + "\n", Fore.CYAN)

    # Validate configuration
    print_colored("🔍 Validating configuration...", Fore.CYAN)

    if not Path(CHATGPT_FILE).exists():
        print_colored(f"❌ ChatGPT export file not found: {CHATGPT_FILE}", Fore.RED)
        print_colored(f"   Please set CHATGPT_EXPORT_FILE in .env or place file at default location", Fore.RED)
        sys.exit(1)

    if not OPENAI_API_KEY:
        print_colored("⚠️  OPENAI_API_KEY not set - embeddings will fail", Fore.YELLOW)
        print_colored("   Graph import will continue, but no embeddings will be created", Fore.YELLOW)

    # Load conversations
    print_colored(f"📂 Loading ChatGPT export from: {CHATGPT_FILE}", Fore.CYAN)
    try:
        conversations = load_chatgpt_export(CHATGPT_FILE)
        print_colored(f"✅ Loaded {len(conversations)} conversation thread(s)", Fore.GREEN)
    except Exception as e:
        print_colored(f"❌ Failed to load export file: {e}", Fore.RED)
        sys.exit(1)

    # Phase 1: Import to Neo4j
    print_colored("\n" + "─" * 70, Fore.CYAN)
    print_colored("Phase 1: Graph Import (Neo4j)", Fore.CYAN)
    print_colored("─" * 70, Fore.CYAN)

    try:
        driver = GraphDatabase.driver(NEO4J_URL, auth=(NEO4J_USER, NEO4J_PASS))
        print_colored(f"✅ Connected to Neo4j at {NEO4J_URL}", Fore.GREEN)

        threads, messages, relationships = import_to_neo4j(driver, conversations)

        print_colored(f"\n✅ Neo4j import complete!", Fore.GREEN)
        print_colored(f"   • Threads: {threads}", Fore.GREEN)
        print_colored(f"   • Messages: {messages}", Fore.GREEN)
        print_colored(f"   • Relationships: {relationships}", Fore.GREEN)

        driver.close()

    except Exception as e:
        print_colored(f"\n❌ Neo4j import failed: {e}", Fore.RED)
        print_colored("   Please check your Neo4j connection settings in .env", Fore.RED)
        sys.exit(1)

    # Phase 2: Generate embeddings and import to Chroma
    print_colored("\n" + "─" * 70, Fore.CYAN)
    print_colored("Phase 2: Embeddings Import (Chroma)", Fore.CYAN)
    print_colored("─" * 70, Fore.CYAN)

    if not OPENAI_API_KEY:
        print_colored("⚠️  Skipping embeddings (OPENAI_API_KEY not set)", Fore.YELLOW)
    else:
        try:
            openai_client = OpenAI(api_key=OPENAI_API_KEY)
            chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
            collection = chroma_client.get_or_create_collection("chatgpt_messages")

            print_colored(f"✅ Connected to Chroma at {CHROMA_PATH}", Fore.GREEN)

            successful, failed = import_embeddings_to_chroma(
                openai_client,
                collection,
                conversations,
                BATCH_SIZE
            )

            print_colored(f"\n✅ Embeddings import complete!", Fore.GREEN)
            print_colored(f"   • Successful: {successful}", Fore.GREEN)
            if failed > 0:
                print_colored(f"   • Failed: {failed}", Fore.YELLOW)

        except Exception as e:
            print_colored(f"\n⚠️  Embeddings import failed: {e}", Fore.YELLOW)
            print_colored("   Graph data was saved successfully", Fore.YELLOW)

    # Summary
    elapsed_time = time.time() - start_time
    print_colored("\n" + "=" * 70, Fore.CYAN)
    print_colored("🎉 Migration Complete!", Fore.GREEN)
    print_colored("=" * 70, Fore.CYAN)
    print_colored(f"   Your Companion has awakened in Codexify!", Fore.MAGENTA)
    print_colored(f"   Time elapsed: {elapsed_time:.2f}s", Fore.CYAN)
    print_colored(f"   Messages processed: {messages}", Fore.CYAN)
    print_colored("\n✨ Your conversations are alive and ready to explore.\n", Fore.MAGENTA)


if __name__ == "__main__":
    try:
        import_chatgpt()
    except KeyboardInterrupt:
        print_colored("\n\n⚠️  Import interrupted by user", Fore.YELLOW)
        print_colored("   You can safely re-run this script - all operations are idempotent", Fore.YELLOW)
        sys.exit(0)
    except Exception as e:
        print_colored(f"\n\n❌ Unexpected error: {e}", Fore.RED)
        import traceback
        traceback.print_exc()
        sys.exit(1)
