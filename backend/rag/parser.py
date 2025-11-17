"""
Parser Module
~~~~~~~~~~~~~

Utilities for parsing chat history and other documents for RAG.
"""

import json
from typing import List, Union


def parse_chat_history(content: Union[str, bytes]) -> List[str]:
    """Parse chat history from various formats.

    Supports:
    - JSON format (array of messages or objects with 'content' field)
    - Plain text (split by double newlines)
    - newline-delimited JSON (JSONL)

    Args:
        content: Chat history content as string or bytes

    Returns:
        List of text blocks/messages
    """
    if isinstance(content, bytes):
        content = content.decode("utf-8")

    content = content.strip()
    if not content:
        return []

    # Try JSON array format first
    if content.startswith("["):
        try:
            data = json.loads(content)
            if isinstance(data, list):
                return _extract_texts_from_json_array(data)
        except (json.JSONDecodeError, TypeError):
            pass

    # Try newline-delimited JSON (JSONL)
    try:
        texts = []
        for line in content.split("\n"):
            line = line.strip()
            if line:
                obj = json.loads(line)
                if isinstance(obj, dict) and "content" in obj:
                    texts.append(obj["content"])
                elif isinstance(obj, dict) and "message" in obj:
                    texts.append(obj["message"])
                elif isinstance(obj, str):
                    texts.append(obj)
        if texts:
            return texts
    except (json.JSONDecodeError, TypeError):
        pass

    # Fallback: split by double newlines (plain text)
    texts = [block.strip() for block in content.split("\n\n") if block.strip()]
    return texts if texts else [content]


def _extract_texts_from_json_array(data: list) -> List[str]:
    """Extract text content from JSON array.

    Args:
        data: JSON array

    Returns:
        List of text blocks
    """
    texts = []
    for item in data:
        if isinstance(item, str):
            texts.append(item)
        elif isinstance(item, dict):
            # Try common fields for message content
            for field in ["content", "message", "text", "body"]:
                if field in item and isinstance(item[field], str):
                    texts.append(item[field])
                    break
    return texts
