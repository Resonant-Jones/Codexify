import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from guardian.core import dependencies

logger = logging.getLogger(__name__)

def ingest_chatgpt_export(content: bytes, user_id: str = "default") -> Dict[str, int]:
    """
    Ingest a ChatGPT export (JSON bytes) into the database and vector store.
    Returns stats: {"threads": count, "messages": count}.
    """
    chatlog_db = dependencies.chatlog_db
    _vector_store = dependencies._vector_store
    
    if not chatlog_db:
        # Try to init if not ready (e.g. in tests)
        chatlog_db = dependencies.init_database()
        
    if not chatlog_db:
        raise RuntimeError("Database not available")
    
    # Initialize vector store if not already done
    if not _vector_store:
        from guardian.vector.store import VectorStore
        _vector_store = VectorStore()
        dependencies._vector_store = _vector_store
        logger.info("Initialized VectorStore for migration")

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON file")

    if not isinstance(data, list):
        raise ValueError("Expected a list of conversations")

    threads_count = 0
    messages_count = 0

    for conv in data:
        try:
            # Extract thread metadata
            title = conv.get("title") or "Imported Chat"
            
            # Create thread
            thread_record = chatlog_db.create_chat_thread(
                user_id=user_id,
                title=title,
                summary="Imported from ChatGPT",
                project_id=1, # Default to Loose Threads
            )
            thread_id = thread_record["id"]
            threads_count += 1

            # Process messages
            mapping = conv.get("mapping", {})
            
            # Linearize messages
            messages = []
            for node_id, node in mapping.items():
                message = node.get("message")
                if not message:
                    continue
                
                author = message.get("author", {})
                role = author.get("role") or message.get("role")
                content_parts = message.get("content", {}).get("parts", [])
                create_time = message.get("create_time")
                
                if not content_parts or not role:
                    continue
                
                text_content = ""
                for part in content_parts:
                    if isinstance(part, str):
                        text_content += part
                    elif isinstance(part, dict):
                        pass
                
                if not text_content.strip():
                    continue
                
                # Map roles
                if role == "assistant":
                    guardian_role = "assistant"
                elif role == "user":
                    guardian_role = "user"
                elif role == "system":
                    guardian_role = "system"
                else:
                    guardian_role = "user"

                messages.append({
                    "role": guardian_role,
                    "content": text_content,
                    "timestamp": create_time or 0
                })

            # Sort by timestamp
            messages.sort(key=lambda x: x["timestamp"])

            # Insert messages
            for msg in messages:
                mid = chatlog_db.create_message(
                    thread_id,
                    msg["role"],
                    msg["content"]
                )
                messages_count += 1
                
                # Embed message
                if _vector_store:
                    try:
                        meta = {
                            "thread_id": thread_id,
                            "role": msg["role"],
                            "message_id": mid,
                            "timestamp": datetime.utcfromtimestamp(msg["timestamp"]).isoformat() if msg["timestamp"] else datetime.utcnow().isoformat(),
                            "source": "chatgpt_import"
                        }
                        _vector_store.add_texts([{"text": msg["content"], "meta": meta}])
                    except Exception as e:
                        logger.warning(f"Failed to embed imported message {mid}: {e}")

        except Exception as e:
            logger.error(f"Failed to import conversation: {e}")
            continue

    return {"threads": threads_count, "messages": messages_count}
