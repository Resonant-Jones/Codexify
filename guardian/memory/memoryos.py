"""
MemoryOS Module
--------------
Core memory management system that integrates various memory services.
"""

import logging
import time
from typing import Dict, List, Optional, Union
from uuid import uuid4

from .codemap import load_codemap, query_codemap, format_results
from .conversation import Conversation, ConversationManager

# Configure logging
logger = logging.getLogger(__name__)


class MemoryOS:
    """Memory Operating System that manages various memory services."""

    def __init__(self, conversation_token_limit: int = 90_000):
        """
        Initialize MemoryOS with required services.

        Args:
            conversation_token_limit: Maximum tokens per conversation (default: 90,000)
        """
        # Load the codemap on initialization
        self.codemap = load_codemap()

        # Initialize conversation management
        self.conversation_token_limit = conversation_token_limit
        self.conversation_manager = ConversationManager()

        logger.info("MemoryOS initialized with codemap and conversation services")

    def query_codemap(self, term: str) -> List[Dict[str, Union[str, int]]]:
        """
        Query the loaded codemap with the provided term.

        Args:
            term (str): The search term to match against the codemap.

        Returns:
            list: List of matching codemap entries. Each entry is a dict with
                 keys: file, line, description. If no matches or errors occur,
                 returns a list with a single dict containing an error message.
        """
        try:
            # Pass the cached codemap to avoid reloading
            results = query_codemap(term, self.codemap)
            return results
        except Exception as e:
            logger.error(f"Error querying codemap: {e}")
            return [{"message": "An error occurred while querying the codemap"}]

    def format_codemap_results(self, results: List[Dict], explain: bool = False) -> str:
        """
        Format codemap query results for display.

        Args:
            results (list): The results from query_codemap
            explain (bool): Whether to include additional explanation

        Returns:
            str: Formatted string ready for display
        """
        return format_results(results, explain)

    def reload_codemap(self) -> bool:
        """
        Reload the codemap from disk.

        Returns:
            bool: True if reload was successful, False otherwise
        """
        try:
            self.codemap = load_codemap()
            return bool(self.codemap)
        except Exception as e:
            logger.error(f"Failed to reload codemap: {e}")
            return False

    def monitor_conversation_length(
        self, conversation_id: str
    ) -> Dict[str, Union[str, bool]]:
        """
        Monitor conversation token count and trigger summarization if needed.

        Args:
            conversation_id: ID of conversation to monitor

        Returns:
            dict: Status information including whether summarization was triggered
        """
        conversation = self.conversation_manager.load_conversation(conversation_id)
        if not conversation:
            return {
                "status": "error",
                "message": f"Conversation {conversation_id} not found",
            }

        # Calculate threshold for summarization (85% of limit)
        threshold = int(self.conversation_token_limit * 0.85)

        if conversation.token_count >= threshold:
            # Trigger summarization
            result = self.summarize_conversation(conversation_id)
            if result.get("status") == "success":
                return {
                    "status": "summarized",
                    "message": "Conversation summarized and branched",
                    "new_conversation_id": result.get("new_conversation_id"),
                }
            return {
                "status": "error",
                "message": f"Failed to summarize conversation: {result.get('message')}",
            }

        return {
            "status": "ok",
            "message": f"Current token count: {conversation.token_count}/{self.conversation_token_limit}",
        }

    def summarize_conversation(self, conversation_id: str) -> Dict[str, str]:
        """
        Summarize conversation and create a new branch.

        Args:
            conversation_id: ID of conversation to summarize

        Returns:
            dict: Status information including new conversation ID if successful
        """
        conversation = self.conversation_manager.load_conversation(conversation_id)
        if not conversation:
            return {
                "status": "error",
                "message": f"Conversation {conversation_id} not found",
            }

        if not conversation.messages:
            return {"status": "error", "message": "Nothing to summarize"}

        try:
            # Generate summary (stub for now, could use LLM if available)
            summary = self._generate_summary(conversation)
            conversation.summary = summary

            # Create child conversation
            child = self.conversation_manager.create_child_conversation(conversation_id)
            if not child:
                return {
                    "status": "error",
                    "message": "Failed to create child conversation",
                }

            # Save updated parent
            self.conversation_manager.save_conversation(conversation)

            logger.info(
                f"Summarized conversation {conversation_id}, created child {child.id}"
            )

            return {
                "status": "success",
                "message": "Conversation summarized and branched successfully",
                "new_conversation_id": child.id,
            }

        except Exception as e:
            logger.error(f"Error summarizing conversation {conversation_id}: {e}")
            return {"status": "error", "message": str(e)}

    def _generate_summary(self, conversation: Conversation) -> str:
        """
        Generate a summary of the conversation.

        Args:
            conversation: Conversation to summarize

        Returns:
            str: Generated summary

        Note: This is a stub implementation. In production, this could:
        1. Use a local LLM if available
        2. Extract key points from recent messages
        3. Include metadata about branching
        """
        try:
            # Try to use local LLM if available
            from guardian.llm import summarize_text

            messages = conversation.get_recent_messages()
            return summarize_text(messages)
        except ImportError:
            # Fallback to simple stub summary
            return (
                f"Conversation branched at {time.strftime('%Y-%m-%d %H:%M:%S')} "
                f"with {len(conversation.messages)} messages "
                f"and {conversation.token_count} tokens."
            )

    def create_conversation(self) -> Conversation:
        """
        Create a new conversation.

        Returns:
            Conversation: Newly created conversation instance
        """
        conversation_id = str(uuid4())
        conversation = Conversation(id=conversation_id)
        self.conversation_manager.save_conversation(conversation)
        return conversation
