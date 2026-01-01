"""
Embedder Module
~~~~~~~~~~~~~~~

Local semantic embedder that combines SentenceTransformers with a vector store.
"""

from __future__ import annotations

import logging
import os
import uuid
from typing import Any, Dict, List, Optional

import numpy as np

try:
    from sentence_transformers import SentenceTransformer  # type: ignore
except Exception:
    SentenceTransformer = None  # type: ignore

try:
    import faiss  # type: ignore
except Exception:
    faiss = None  # type: ignore

try:
    import chromadb  # type: ignore
except Exception:
    chromadb = None  # type: ignore

logger = logging.getLogger(__name__)

DEFAULT_MODEL = os.getenv("CODEXIFY_LOCAL_MODEL") or os.getenv(
    "LOCAL_EMBED_MODEL"
)
DEFAULT_STORE = "faiss"


def _normalize_metadatas(
    metadatas: list[dict[str, Any]] | None, count: int
) -> list[dict[str, Any]]:
    if not metadatas:
        return [{} for _ in range(count)]
    cleaned: list[dict[str, Any]] = []
    for meta in list(metadatas)[:count]:
        cleaned.append(dict(meta) if isinstance(meta, dict) else {})
    while len(cleaned) < count:
        cleaned.append({})
    return cleaned


def _normalize_embeddings(arr: np.ndarray) -> np.ndarray:
    if arr.size == 0:
        return arr
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms[norms == 0.0] = 1.0
    return arr / norms


class LocalSemanticEmbedder:
    """Local embedder that supports embedding, indexing, and semantic search."""

    def __init__(
        self,
        model: str | None = None,
        store: str = DEFAULT_STORE,
        chroma_path: str = "./.chroma",
        collection: str = "codexify_vault",
    ) -> None:
        self.model_name = model or DEFAULT_MODEL
        if not self.model_name or not os.path.isdir(self.model_name):
            raise RuntimeError(
                f"LOCAL_EMBED_MODEL must point to a local directory, got: {self.model_name}"
            )
        self.store = (store or DEFAULT_STORE).strip().lower()
        self.chroma_path = chroma_path
        self.collection = collection

        if SentenceTransformer is None:
            raise RuntimeError("sentence-transformers not installed.")
        self._model = SentenceTransformer(
            self.model_name,
            local_files_only=True,
        )

        self._index = None
        self._index_dim: int | None = None
        self._texts: list[str] = []
        self._metadatas: list[dict[str, Any]] = []
        self._chroma_collection = None

        if self.store == "faiss":
            if faiss is None:
                raise RuntimeError("faiss not installed.")
        elif self.store == "chroma":
            if chromadb is None:
                raise RuntimeError("chromadb not installed.")
            client = chromadb.PersistentClient(path=self.chroma_path)
            self._chroma_collection = client.get_or_create_collection(
                name=self.collection
            )
        else:
            raise ValueError("Vector store must be 'faiss' or 'chroma'.")

    def _embed_np(self, texts: list[str], batch_size: int = 64) -> np.ndarray:
        if not texts:
            return np.empty((0, 0), dtype="float32")
        vectors = self._model.encode(
            texts,
            batch_size=batch_size,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        if vectors.ndim == 1:
            vectors = vectors.reshape(1, -1)
        return vectors.astype("float32")

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Expose embeddings for external callers (health checks, utilities)."""
        return self.embed_texts(texts)

    def embed_texts(
        self, texts: list[str], batch_size: int = 64
    ) -> list[list[float]]:
        """Embed texts to vectors for indexing or downstream use."""
        text_list = ["" if t is None else str(t) for t in texts]
        vectors = self._embed_np(text_list, batch_size=batch_size)
        return [] if vectors.size == 0 else vectors.tolist()

    def embed_and_index(
        self,
        texts: list[str],
        metadatas: list[dict[str, Any]] | None = None,
        ids_prefix: str = "doc",
    ) -> dict[str, Any]:
        """Embed texts and store them in the configured vector store."""
        if not texts:
            return {"store": self.store, "count": 0}
        text_list = ["" if t is None else str(t) for t in texts]
        metas = _normalize_metadatas(metadatas, len(text_list))

        if self.store == "faiss":
            if faiss is None:
                raise RuntimeError("faiss not installed.")
            vectors = self._embed_np(text_list)
            if vectors.size == 0:
                return {"store": "faiss", "count": 0}
            vectors = _normalize_embeddings(vectors)
            dim = int(vectors.shape[1])
            if self._index is None or self._index_dim != dim:
                if self._index is not None and self._index_dim != dim:
                    logger.warning(
                        "[embedder] FAISS dim changed; resetting index"
                    )
                    self._texts = []
                    self._metadatas = []
                self._index = faiss.IndexFlatIP(dim)
                self._index_dim = dim
            self._index.add(vectors)
            self._texts.extend(text_list)
            self._metadatas.extend(metas)
            return {"store": "faiss", "count": len(text_list)}

        if self._chroma_collection is None:
            raise RuntimeError("Chroma collection not initialized.")
        vectors = self._embed_np(text_list)
        if vectors.size == 0:
            return {"store": "chroma", "count": 0}
        ids = [
            f"{ids_prefix}_{uuid.uuid4().hex}" for _ in range(len(text_list))
        ]
        self._chroma_collection.add(
            documents=text_list,
            embeddings=vectors.tolist(),
            metadatas=metas,
            ids=ids,
        )
        return {"store": "chroma", "count": len(text_list)}

    def search(self, query: str, k: int = 5) -> list[dict[str, Any]]:
        """Search the configured vector store for semantically similar text."""
        if not query or not str(query).strip():
            return []
        if k <= 0:
            return []

        if self.store == "faiss":
            if self._index is None or not self._texts:
                return []
            vectors = self._embed_np([str(query)])
            if vectors.size == 0:
                return []
            vectors = _normalize_embeddings(vectors)
            scores, indices = self._index.search(vectors, k)
            results: list[dict[str, Any]] = []
            for idx, score in zip(indices[0], scores[0]):
                if idx < 0 or idx >= len(self._texts):
                    continue
                meta = self._metadatas[idx]
                results.append(
                    {
                        "text": self._texts[idx],
                        "meta": meta,
                        "metadata": meta,
                        "score": float(score),
                    }
                )
            return results

        if self._chroma_collection is None:
            return []
        vectors = self._embed_np([str(query)])
        if vectors.size == 0:
            return []
        result = self._chroma_collection.query(
            query_embeddings=vectors.tolist(), n_results=k
        )
        docs = result.get("documents", [[]])[0] or []
        metas = result.get("metadatas", [[]])[0] or []
        distances = result.get("distances", [[]])[0] or []
        ids = result.get("ids", [[]])[0] or []
        matches: list[dict[str, Any]] = []
        for idx, doc in enumerate(docs):
            meta = metas[idx] if idx < len(metas) else {}
            dist = float(distances[idx]) if idx < len(distances) else 0.0
            score = 1.0 - dist
            entry: dict[str, Any] = {
                "text": doc,
                "meta": meta,
                "metadata": meta,
                "score": score,
            }
            if idx < len(ids):
                entry["id"] = ids[idx]
            matches.append(entry)
        return matches


class Embedder(LocalSemanticEmbedder):
    """Compatibility wrapper with document helpers used across the app."""

    def __init__(
        self,
        use_openai: bool = False,
        model: str | None = None,
        store: str = DEFAULT_STORE,
        chroma_path: str = "./.chroma",
        collection: str = "codexify_vault",
    ) -> None:
        if use_openai:
            logger.info("[embedder] use_openai ignored; local-only embedder")
        super().__init__(
            model=model,
            store=store,
            chroma_path=chroma_path,
            collection=collection,
        )

    def embed_documents(
        self,
        documents: list[str],
        metadatas: list[dict[str, Any]] | None = None,
        ids_prefix: str = "doc",
    ) -> list[dict[str, Any]]:
        """Compatibility layer for document ingestion flows."""
        result = self.embed_and_index(
            documents, metadatas=metadatas, ids_prefix=ids_prefix
        )
        return [result]
