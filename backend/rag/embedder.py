"""
Embedder Module
~~~~~~~~~~~~~~~

Wrapper around CodexifyEmbedder for embedding documents and texts.
"""

from typing import Any, Dict, List, Optional

from guardian.runtime.embed.embedder import CodexifyEmbedder


class Embedder:
    """Wrapper around CodexifyEmbedder for embedding documents."""

    def __init__(
        self,
        use_openai: bool = True,
        model: Optional[str] = None,
        store: str = "chroma",
        chroma_path: str = "./.chroma",
        collection: str = "codexify_vault",
    ):
        """Initialize the embedder.

        Args:
            use_openai: Use OpenAI embeddings instead of local model
            model: Model name to use
            store: Vector store to use ('chroma' or 'faiss')
            chroma_path: Path to chroma database
            collection: Collection name for storage
        """
        self._embedder = CodexifyEmbedder(
            use_openai=use_openai,
            model=model,
            store=store,
            chroma_path=chroma_path,
            collection=collection,
        )

    def embed_documents(
        self,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids_prefix: str = "doc",
    ) -> List[Dict[str, Any]]:
        """Embed and index documents.

        Args:
            documents: List of document texts to embed
            metadatas: Optional list of metadata dicts for each document
            ids_prefix: Prefix for document IDs

        Returns:
            List of results dicts for each embedded document
        """
        result = self._embedder.embed_and_index(
            documents, metadatas=metadatas, ids_prefix=ids_prefix
        )
        return [result]  # Return as list for compatibility

    def embed_texts(
        self, texts: List[str], batch_size: int = 64
    ) -> List[List[float]]:
        """Embed texts and return embeddings.

        Args:
            texts: List of texts to embed
            batch_size: Batch size for embedding

        Returns:
            List of embedding vectors
        """
        return self._embedder.embed_texts(texts, batch_size=batch_size)
