"""
Provider registry/factory with soft dependencies.
"""

# SPDX-License-Identifier: MIT
import os
from typing import Dict, Optional

from .base import ChatProvider, EmbeddingsProvider


class ProviderRegistry:
    def __init__(self):
        self._chat: Dict[str, ChatProvider] = {}
        self._emb: Dict[str, EmbeddingsProvider] = {}

        # OpenAI (chat + embeddings)
        try:
            if os.getenv("OPENAI_API_KEY"):
                from .openai_adapter import OpenAIChat, OpenAIEmbeddings

                self._chat["openai"] = OpenAIChat()
                self._emb["openai"] = OpenAIEmbeddings()
        except Exception:
            pass

        # Groq (chat only)
        try:
            if os.getenv("GROQ_API_KEY"):
                from .groq_adapter import GroqChat

                self._chat["groq"] = GroqChat()
        except Exception:
            pass

        # Gemini (chat only)
        try:
            if os.getenv("GEMINI_API_KEY"):
                from .gemini_adapter import GeminiChat

                self._chat["gemini"] = GeminiChat()
        except Exception:
            pass

    def get_chat(self, provider: Optional[str]) -> ChatProvider:
        p = (provider or os.getenv("GUARDIAN_PROVIDER") or "openai").lower()
        if p not in self._chat:
            raise ValueError(f"Chat provider '{p}' not configured")
        return self._chat[p]

    def get_embeddings(self, provider: Optional[str]) -> EmbeddingsProvider:
        p = (provider or os.getenv("GUARDIAN_EMBEDDER") or "openai").lower()
        if p not in self._emb:
            raise ValueError(f"Embeddings provider '{p}' not configured")
        return self._emb[p]

    def capabilities(self):
        return {
            "chat": sorted(self._chat.keys()),
            "embeddings": sorted(self._emb.keys()),
        }
