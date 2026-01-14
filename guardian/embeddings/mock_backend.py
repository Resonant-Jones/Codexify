"""
Mock Embedding Backend
~~~~~~~~~~~~~~~~~~~~~~

Lightweight embedding backend for tests and development environments.
Produces deterministic vectors based on text hashing without requiring
any model files or network access.
"""

from __future__ import annotations

import hashlib
from typing import List, Union

import numpy as np


class MockEmbeddingBackend:
    """Mock embedding backend using deterministic text hashes.

    This backend is designed for:
    - Unit/integration tests that don't need real semantic similarity
    - Development environments without access to model files
    - CI pipelines where downloading large models is impractical

    Vectors are deterministic: same input text produces the same vector.
    """

    def __init__(self, dim: int = 384, normalize: bool = True) -> None:
        """Initialize the mock backend.

        Args:
            dim: Embedding dimension (default 384 matches bge-large-en-v1.5)
            normalize: Whether to L2-normalize output vectors (default True)
        """
        self.dim = dim
        self.normalize = normalize

    def encode(
        self,
        sentences: str | list[str],
        batch_size: int = 64,
        convert_to_numpy: bool = True,
        show_progress_bar: bool = False,
        **kwargs,
    ) -> np.ndarray:
        """Encode sentences to embedding vectors.

        Mimics the SentenceTransformer.encode() API for drop-in compatibility.

        Args:
            sentences: Single string or list of strings to encode
            batch_size: Ignored (included for API compatibility)
            convert_to_numpy: Ignored, always returns numpy (compatibility)
            show_progress_bar: Ignored (included for API compatibility)
            **kwargs: Additional arguments ignored for compatibility

        Returns:
            numpy array of shape (n_sentences, dim) with float32 dtype
        """
        if isinstance(sentences, str):
            sentences = [sentences]

        vectors = np.array(
            [self._hash_to_vector(text) for text in sentences],
            dtype="float32",
        )

        if self.normalize and vectors.size > 0:
            norms = np.linalg.norm(vectors, axis=1, keepdims=True)
            norms[norms == 0.0] = 1.0
            vectors = vectors / norms

        return vectors

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Public embed API for external callers.

        Args:
            texts: List of strings to embed

        Returns:
            List of embedding vectors as Python lists
        """
        vectors = self.encode(texts)
        return vectors.tolist() if vectors.size > 0 else []

    def _hash_to_vector(self, text: str) -> np.ndarray:
        """Convert text to a deterministic vector via hashing.

        Uses SHA-256 hash extended to the target dimension.
        Same text always produces the same vector.
        """
        if not text:
            return np.zeros(self.dim, dtype="float32")

        # Generate enough hash bytes for the full dimension
        hash_bytes = b""
        for i in range((self.dim * 4 // 32) + 1):
            hash_bytes += hashlib.sha256(f"{text}:{i}".encode()).digest()

        # Convert to uint8 first, then scale to float32 in [-1, 1] range
        # This avoids overflow issues with raw float32 interpretation
        raw = np.frombuffer(hash_bytes[: self.dim], dtype="uint8")
        arr = raw.astype("float32")
        arr = (arr / 127.5) - 1.0  # Scale from [0,255] to [-1,1]
        return arr
