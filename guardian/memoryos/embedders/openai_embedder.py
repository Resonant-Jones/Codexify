"""
OpenAI Embedder for MemoryOS
Uses OpenAI's embedding API for generating text embeddings
"""

import logging
import os
from functools import lru_cache
from typing import List, Optional

logger = logging.getLogger(__name__)


class OpenAIEmbedder:
    """
    Embedder that uses OpenAI's embedding API to generate text embeddings.
    The embedding model is resolved from environment variables or explicit args.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """
        Initialize OpenAI embedder.

        Args:
            api_key: OpenAI API key. If None, will try to get from OPENAI_API_KEY env var
            model: OpenAI embedding model to use
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = (
            model
            or os.getenv("OPENAI_EMBEDDING_MODEL")
            or os.getenv("OPENAI_EMBED_MODEL")
            or ""
        ).strip()
        if not self.model:
            raise ValueError(
                "OpenAI embedder requires OPENAI_EMBED_MODEL or OPENAI_EMBEDDING_MODEL."
            )

        if not self.api_key:
            raise ValueError(
                "OpenAI API key is required. Set OPENAI_API_KEY environment variable."
            )

        # Import OpenAI client lazily to avoid hard dependency
        try:
            from openai import OpenAI

            self.client = OpenAI(api_key=self.api_key)
        except ImportError:
            raise ImportError(
                "OpenAI package not installed. Run: pip install openai"
            )

        logger.info(f"OpenAIEmbedder initialized with model: {self.model}")

    @lru_cache(maxsize=1024)
    def embed(self, text: str) -> List[float]:
        """
        Embed a single string of text using OpenAI's embedding API.

        Args:
            text (str): The input text to embed.

        Returns:
            List[float]: The embedding vector as a list of floats.
        """
        try:
            response = self.client.embeddings.create(
                input=text, model=self.model
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating embedding with OpenAI: {e}")
            raise

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a list of strings using OpenAI's embedding API.

        Args:
            texts (List[str]): The list of texts to embed.

        Returns:
            List[List[float]]: List of embedding vectors for each input string.
        """
        try:
            response = self.client.embeddings.create(
                input=texts, model=self.model
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            logger.error(f"Error generating batch embeddings with OpenAI: {e}")
            raise

    def get_embedding_dimension(self) -> int:
        """
        Get the dimension of the embedding vectors for the current model.

        Returns:
            int: Dimension of embedding vectors
        """
        raise NotImplementedError(
            "Embedding dimension is model-dependent; infer from live embeddings instead of fixed mappings."
        )

    def __repr__(self):
        return f"OpenAIEmbedder(model='{self.model}')"
