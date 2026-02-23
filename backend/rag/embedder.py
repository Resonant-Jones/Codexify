"""
Embedder Module
~~~~~~~~~~~~~~~

Local semantic embedder that combines SentenceTransformers with a vector store.

Environment Variables:
    CODEXIFY_EMBEDDINGS_BACKEND: Backend selection
        - "sentence_transformer" (default): Use local SentenceTransformers
        - "mock": Use MockEmbeddingBackend for tests/dev

    CODEXIFY_ALLOW_EMBEDDINGS_FALLBACK: Fallback behavior
        - "0" (default): Fail if SentenceTransformer init fails
        - "1": Fall back to MockEmbeddingBackend on init failure
"""

from __future__ import annotations

import logging
import os
import uuid
from typing import Any

import numpy as np

from guardian.utils.embed_paths import resolve_local_embed_model

try:
    from sentence_transformers import SentenceTransformer  # type: ignore
except Exception:
    SentenceTransformer = None  # type: ignore

try:
    from guardian.embeddings.mock_backend import MockEmbeddingBackend
except Exception:
    MockEmbeddingBackend = None  # type: ignore

try:
    import faiss  # type: ignore
except Exception:
    faiss = None  # type: ignore

try:
    import chromadb  # type: ignore
except Exception:
    chromadb = None  # type: ignore

logger = logging.getLogger(__name__)

DEFAULT_STORE = "faiss"

# Environment variable names
_ENV_BACKEND = "CODEXIFY_EMBEDDINGS_BACKEND"
_ENV_FALLBACK = "CODEXIFY_ALLOW_EMBEDDINGS_FALLBACK"

# Allowed backend values
_BACKEND_LOCAL = "local"
_BACKEND_SENTENCE_TRANSFORMER = "sentence_transformer"
_BACKEND_MOCK = "mock"
_ALLOWED_BACKENDS = {
    _BACKEND_LOCAL,
    _BACKEND_SENTENCE_TRANSFORMER,
    _BACKEND_MOCK,
}


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


def _normalize_namespace(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _namespace_matches(meta: dict[str, Any], namespace: str | None) -> bool:
    if namespace is None:
        return True
    return _normalize_namespace(meta.get("namespace")) == namespace


def _normalize_embeddings(arr: np.ndarray) -> np.ndarray:
    if arr.size == 0:
        return arr
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms[norms == 0.0] = 1.0
    return arr / norms


def _get_embeddings_backend() -> str:
    """Get the configured embeddings backend from environment."""
    backend = os.getenv(_ENV_BACKEND, _BACKEND_SENTENCE_TRANSFORMER)
    backend = backend.strip().lower()
    if backend not in _ALLOWED_BACKENDS:
        logger.warning(
            "[embedder] invalid backend=%s, falling back to %s",
            backend,
            _BACKEND_SENTENCE_TRANSFORMER,
        )
        backend = _BACKEND_SENTENCE_TRANSFORMER
    return backend


def _allow_fallback() -> bool:
    """Check if fallback to mock backend is allowed on init failure."""
    val = os.getenv(_ENV_FALLBACK, "0").strip().lower()
    return val in ("1", "true", "yes")


def _is_local_backend(value: str) -> bool:
    return (value or "").strip().lower() == _BACKEND_LOCAL


def _get_local_embed_model(*, strict: bool) -> str | None:
    if strict:
        return resolve_local_embed_model()
    model_name = (os.getenv("LOCAL_EMBED_MODEL") or "").strip()
    return model_name or None


class LocalSemanticEmbedder:
    """Local embedder for embedding, indexing, and semantic search."""

    def __init__(
        self,
        model: str | None = None,
        store: str = DEFAULT_STORE,
        chroma_path: str = "./.chroma",
        collection: str = "codexify_vault",
    ) -> None:
        if model:
            logger.warning(
                "[embedder] model override ignored; use LOCAL_EMBED_MODEL"
            )

        self.store = (store or DEFAULT_STORE).strip().lower()
        self.chroma_path = chroma_path
        self.collection = collection
        self._backend_type: str = _get_embeddings_backend()

        # Initialize embedding model based on backend selection
        self._model = self._init_embedding_model()

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

    def _init_embedding_model(self):
        """Initialize the embedding model based on backend configuration."""
        if self._backend_type == _BACKEND_MOCK:
            return self._init_mock_backend()

        return self._init_sentence_transformer(
            strict_local=_is_local_backend(self._backend_type)
        )

    def _init_mock_backend(self):
        """Initialize MockEmbeddingBackend."""
        if MockEmbeddingBackend is None:
            raise RuntimeError(
                "MockEmbeddingBackend not available. "
                "Ensure guardian.embeddings.mock_backend is importable."
            )
        # Use 384 dims to match bge-large-en-v1.5 default
        mock = MockEmbeddingBackend(dim=384, normalize=True)
        logger.info(
            "[embedder] backend=mock dim=%d normalize=%d",
            mock.dim,
            int(mock.normalize),
        )
        self.model_name = "mock"
        return mock

    def _init_sentence_transformer(self, *, strict_local: bool):
        """Initialize SentenceTransformer backend with optional fallback."""
        self.model_name = _get_local_embed_model(strict=strict_local)
        if not self.model_name:
            # Non-local backends can run without LOCAL_EMBED_MODEL configured.
            self.model_name = "BAAI/bge-large-en-v1.5"
        logger.info("[embedder] embedding model=%s", self.model_name)

        if SentenceTransformer is None:
            if _allow_fallback() and MockEmbeddingBackend is not None:
                logger.warning(
                    "[embedder] sentence-transformers not installed; "
                    "fallback to mock backend enabled"
                )
                return self._init_mock_backend()
            raise RuntimeError("sentence-transformers not installed.")

        try:
            model = SentenceTransformer(
                self.model_name,
                local_files_only=strict_local,
            )
            logger.info(
                "[embedder] backend=sentence_transformer model=%s",
                self.model_name,
            )
            return model
        except Exception as exc:
            if _allow_fallback() and MockEmbeddingBackend is not None:
                logger.warning(
                    "[embedder] SentenceTransformer init failed: %s; "
                    "falling back to mock backend",
                    str(exc),
                )
                return self._init_mock_backend()
            if strict_local:
                raise RuntimeError(
                    "LOCAL_EMBED_MODEL could not be loaded from local cache."
                ) from exc
            raise RuntimeError(
                f"SentenceTransformer could not be initialized for model '{self.model_name}'."
            ) from exc

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
        """Expose embeddings for external callers."""
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

    def search(
        self,
        query: str,
        k: int = 5,
        namespace: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search the configured vector store for semantically similar text."""
        if not query or not str(query).strip():
            return []
        if k <= 0:
            return []
        normalized_namespace = _normalize_namespace(namespace)

        if self.store == "faiss":
            if self._index is None or not self._texts:
                return []
            vectors = self._embed_np([str(query)])
            if vectors.size == 0:
                return []
            vectors = _normalize_embeddings(vectors)
            search_k = (
                len(self._texts) if normalized_namespace is not None else k
            )
            scores, indices = self._index.search(vectors, search_k)
            results: list[dict[str, Any]] = []
            for idx, score in zip(indices[0], scores[0]):
                if idx < 0 or idx >= len(self._texts):
                    continue
                meta = self._metadatas[idx]
                if not _namespace_matches(meta, normalized_namespace):
                    continue
                results.append(
                    {
                        "text": self._texts[idx],
                        "meta": meta,
                        "metadata": meta,
                        "score": float(score),
                    }
                )
                if len(results) >= k:
                    break
            return results

        if self._chroma_collection is None:
            return []
        vectors = self._embed_np([str(query)])
        if vectors.size == 0:
            return []
        query_kwargs: dict[str, Any] = {
            "query_embeddings": vectors.tolist(),
            "n_results": k,
        }
        if normalized_namespace is not None:
            query_kwargs["where"] = {"namespace": normalized_namespace}
        result = self._chroma_collection.query(**query_kwargs)
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
