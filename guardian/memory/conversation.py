"""
Conversation Management Module
--------------------------
Handles conversation data structures and token management.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import time
import logging
import json

logger = logging.getLogger(__name__)


@dataclass
class Conversation:
    """Represents a conversation with token limit management and lineage tracking."""

    id: str
    created_at: float = field(default_factory=time.time)
    messages: List[Dict] = field(default_factory=list)
    token_count: int = 0
    summary: Optional[str] = None
    parent_id: Optional[str] = None
    child_ids: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert conversation to dictionary format."""
        return {
            "id": self.id,
            "created_at": self.created_at,
            "messages": self.messages,
            "token_count": self.token_count,
            "summary": self.summary,
            "parent_id": self.parent_id,
            "child_ids": self.child_ids,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Conversation":
        """Create conversation instance from dictionary."""
        return cls(
            id=data["id"],
            created_at=data.get("created_at", time.time()),
            messages=data.get("messages", []),
            token_count=data.get("token_count", 0),
            summary=data.get("summary"),
            parent_id=data.get("parent_id"),
            child_ids=data.get("child_ids", []),
            metadata=data.get("metadata", {}),
        )

    def add_message(self, message: Dict, token_count: int) -> None:
        """
        Add a message to the conversation.

        Args:
            message: The message to add
            token_count: Number of tokens in the message
        """
        self.messages.append(message)
        self.token_count += token_count

    def get_recent_messages(self, n: int = 10) -> List[Dict]:
        """Get the n most recent messages."""
        return self.messages[-n:] if self.messages else []

    def save(self, path: str) -> None:
        """Save conversation to JSON file."""
        try:
            with open(path, "w") as f:
                json.dump(self.to_dict(), f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save conversation {self.id}: {e}")

    @classmethod
    def load(cls, path: str) -> Optional["Conversation"]:
        """Load conversation from JSON file."""
        try:
            with open(path, "r") as f:
                data = json.load(f)
            return cls.from_dict(data)
        except Exception as e:
            logger.error(f"Failed to load conversation: {e}")
            return None


class ConversationManager:
    """Manages conversation storage and retrieval."""

    def __init__(self, storage_dir: str = "guardian/memory/conversations"):
        """
        Initialize conversation manager.

        Args:
            storage_dir: Directory for storing conversation files
        """
        self.storage_dir = storage_dir
        self._ensure_storage_dir()

    def _ensure_storage_dir(self) -> None:
        """Ensure storage directory exists."""
        import os

        os.makedirs(self.storage_dir, exist_ok=True)

    def _get_conversation_path(self, conversation_id: str) -> str:
        """Get path for conversation file."""
        return f"{self.storage_dir}/{conversation_id}.json"

    def save_conversation(self, conversation: Conversation) -> bool:
        """
        Save conversation to storage.

        Args:
            conversation: Conversation instance to save

        Returns:
            bool: True if save successful, False otherwise
        """
        try:
            path = self._get_conversation_path(conversation.id)
            conversation.save(path)
            return True
        except Exception as e:
            logger.error(f"Failed to save conversation {conversation.id}: {e}")
            return False

    def load_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """
        Load conversation from storage.

        Args:
            conversation_id: ID of conversation to load

        Returns:
            Optional[Conversation]: Loaded conversation or None if not found
        """
        path = self._get_conversation_path(conversation_id)
        return Conversation.load(path)

    def create_child_conversation(self, parent_id: str) -> Optional[Conversation]:
        """
        Create a child conversation from a parent.

        Args:
            parent_id: ID of parent conversation

        Returns:
            Optional[Conversation]: New child conversation or None if parent not found
        """
        parent = self.load_conversation(parent_id)
        if not parent:
            logger.error(f"Parent conversation {parent_id} not found")
            return None

        # Create child ID by incrementing parent ID
        child_id = f"{parent_id}-{len(parent.child_ids) + 1}"

        # Create child conversation
        child = Conversation(
            id=child_id,
            parent_id=parent_id,
            metadata=parent.metadata.copy(),  # Copy relevant context
        )

        # Update parent's child IDs
        parent.child_ids.append(child_id)
        self.save_conversation(parent)

        # Save child conversation
        self.save_conversation(child)

        return child
