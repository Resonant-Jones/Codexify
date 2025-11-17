"""
RAG (Retrieval-Augmented Generation) Module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This module provides embedder and parser utilities for RAG functionality.
"""

from .embedder import Embedder
from .parser import parse_chat_history

__all__ = ["Embedder", "parse_chat_history"]
