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

import hashlib
import logging
import os
import uuid
from typing import Any

import numpy as np

from guardian.utils.embed_paths import (
    get_local_embed_model,
    require_local_embed_model,
)

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
    from chromadb.config import Settings as ChromaSettings  # type: ignore
except Exception:
    chromadb = None  # type: ignore
    ChromaSettings = None  # type: ignore

logger = logging.getLogger(__name__)

# Default backend selection (kept compatible with legacy EMBEDDING_BACKEND)
DEFAULT_BACKEND = (
    (
        os.getenv("CODEXIFY_EMBEDDINGS_BACKEND")
        or os.getenv("EMBEDDING_BACKEND")
        or "sentence_transformer"
    )
    .strip()
    .lower()
)

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


def inspect_embedder_preflight(
    backend: str | None = None,
) -> dict[str, Any]:
    """Return a lightweight embedder readiness snapshot.

    This check is intentionally side-effect free:
    - no vector store initialization
    - no model download attempt
    - no mutation of embedder runtime state
    """

    resolved_backend = (
        backend
        or os.getenv(_ENV_BACKEND)
        or os.getenv("EMBEDDING_BACKEND")
        or _BACKEND_SENTENCE_TRANSFORMER
    )
    backend_value = str(resolved_backend or "").strip().lower()
    model_name = (os.getenv("LOCAL_EMBED_MODEL") or "").strip() or None

    logger.info(
        "[embedder] preflight backend=%s model=%s",
        backend_value,
        model_name or "<unset>",
    )

    if backend_value != _BACKEND_LOCAL:
        reason = (
            "local embedder preflight not applicable for stub backend"
            if backend_value == "stub"
            else (
                f"local embedder preflight not applicable for {backend_value or 'unset'} backend"
            )
        )
        return {
            "backend": backend_value or "unset",
            "model": model_name,
            "ready": True,
            "present": None,
            "reason": reason,
        }

    try:
        resolved_model = require_local_embed_model()
    except Exception as exc:
        logger.warning(
            "[embedder] preflight local backend not ready model=%s reason=%s",
            model_name or "<unset>",
            str(exc),
        )
        return {
            "backend": _BACKEND_LOCAL,
            "model": model_name,
            "ready": False,
            "present": False,
            "reason": (
                "configured local embedder not found in cache or invalid: "
                f"{exc}"
            ),
        }

    return {
        "backend": _BACKEND_LOCAL,
        "model": resolved_model,
        "ready": True,
        "present": True,
        "reason": "local embedder preflight passed",
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


def _normalize_embeddings(vectors: np.ndarray) -> np.ndarray:
    arr = np.asarray(vectors, dtype="float32")
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    if arr.size == 0:
        return arr
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms[norms == 0.0] = 1.0
    return (arr / norms).astype("float32")


def _normalize_namespace(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _namespace_matches(meta: dict[str, Any], namespace: str | None) -> bool:
    if namespace is None:
        return True
    return _normalize_namespace(meta.get("namespace")) == namespace


def _metadata_user_id(meta: dict[str, Any]) -> str | None:
    user_id = _normalize_namespace(meta.get("user_id"))
    if user_id:
        return user_id
    return _normalize_namespace(meta.get("owner_user_id"))


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
    """Return a local embedding model path if configured.

    - strict=True: require a valid local model (fail-closed)
    - strict=False: return the configured model if present, else None
    """
    if strict:
        return require_local_embed_model()
    return get_local_embed_model(strict=False)


def _create_chroma_client(chroma_path: str):
    if chromadb is None:
        raise RuntimeError("chromadb not installed.")
    settings = None
    if ChromaSettings is not None:
        settings = ChromaSettings(anonymized_telemetry=False)
    return chromadb.PersistentClient(path=chroma_path, settings=settings)


class LocalSemanticEmbedder:
    """Local embedder for embedding, indexing, and semantic search."""

    def __init__(
        self,
        model: str | None = None,
        store: str = DEFAULT_STORE,
        chroma_path: str = "./.chroma",
        collection: str = "codexify_vault_supported",
        backend: str | None = None,
    ) -> None:
        self._model_override = model

        self.store = (store or DEFAULT_STORE).strip().lower()
        self.chroma_path = chroma_path
        self.collection = collection
        configured_backend = (
            (backend or _get_embeddings_backend()).strip().lower()
        )
        if configured_backend not in _ALLOWED_BACKENDS:
            logger.warning(
                "[embedder] invalid backend=%s, falling back to %s",
                configured_backend,
                _BACKEND_SENTENCE_TRANSFORMER,
            )
            configured_backend = _BACKEND_SENTENCE_TRANSFORMER
        self._backend_type = configured_backend

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
            client = _create_chroma_client(self.chroma_path)
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
        # Prefer explicit override, then local model env (when strict), else default HF model.
        self.model_name = (
            self._model_override or ""
        ).strip() or _get_local_embed_model(strict=strict_local)
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
            model = self._load_sentence_transformer(
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
                return self._recover_local_model_once(exc)
            raise RuntimeError(
                f"SentenceTransformer could not be initialized for model '{self.model_name}'."
            ) from exc

    def _load_sentence_transformer(
        self,
        model_name: str,
        *,
        local_files_only: bool,
    ):
        assert SentenceTransformer is not None
        return SentenceTransformer(
            model_name,
            local_files_only=local_files_only,
        )

    def _attempt_local_model_autodownload(self, model_name: str):
        # Trigger SentenceTransformer/HF one-time fetch into local cache.
        return self._load_sentence_transformer(
            model_name,
            local_files_only=False,
        )

    def _recover_local_model_once(self, initial_exc: Exception):
        model_name = self.model_name or "UNKNOWN"
        logger.info(
            "[embedder] local model=%s missing from cache; attempting one-time auto-download",
            model_name,
        )
        try:
            self._attempt_local_model_autodownload(model_name)
        except Exception as download_exc:
            logger.error(
                "[embedder] local model=%s auto-download failed: %s",
                model_name,
                str(download_exc),
            )
            raise RuntimeError(
                f"LOCAL_EMBED_MODEL '{model_name}' could not be loaded from local cache. "
                "Auto-download was attempted and failed: "
                f"{download_exc}"
            ) from initial_exc

        try:
            model = self._load_sentence_transformer(
                model_name,
                local_files_only=True,
            )
            logger.info(
                "[embedder] local model=%s recovered after auto-download",
                model_name,
            )
            return model
        except Exception as retry_exc:
            logger.error(
                "[embedder] local model=%s still unavailable after auto-download: %s",
                model_name,
                str(retry_exc),
            )
            raise RuntimeError(
                f"LOCAL_EMBED_MODEL '{model_name}' could not be loaded from local cache. "
                "Auto-download was attempted, but initialization still failed: "
                f"{retry_exc}"
            ) from initial_exc

    def _embed_np(self, texts: list[str], batch_size: int = 64) -> np.ndarray:
        if not texts:
            return np.empty((0, 0), dtype="float32")

        model = self._model
        if model is None:
            return np.empty((0, 0), dtype="float32")

        # SentenceTransformer path
        if hasattr(model, "encode"):
            vectors = model.encode(
                texts,
                batch_size=batch_size,
                convert_to_numpy=True,
                show_progress_bar=False,
            )
        # MockEmbeddingBackend path (or any backend exposing embed_texts/embed)
        elif hasattr(model, "embed_texts"):
            vectors = np.asarray(model.embed_texts(texts), dtype="float32")
        elif hasattr(model, "embed"):
            vectors = np.asarray(model.embed(texts), dtype="float32")
        else:
            raise RuntimeError(
                "Unsupported embedding backend object; missing encode/embed APIs"
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
        ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Embed texts and store them in the configured vector store."""
        if not texts:
            return {"store": self.store, "count": 0}
        text_list = ["" if t is None else str(t) for t in texts]
        metas = _normalize_metadatas(metadatas, len(text_list))
        normalized_ids: list[str] | None = None
        if ids:
            if len(ids) != len(text_list):
                logger.warning(
                    "[embedder] ids length mismatch; ignoring provided ids"
                )
            else:
                cleaned = [str(value).strip() for value in ids]
                if all(cleaned):
                    normalized_ids = cleaned
                else:
                    logger.warning(
                        "[embedder] ids contain empty values; ignoring provided ids"
                    )

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
        if normalized_ids is None:
            normalized_ids = [
                f"{ids_prefix}_{uuid.uuid4().hex}"
                for _ in range(len(text_list))
            ]
            self._chroma_collection.add(
                documents=text_list,
                embeddings=vectors.tolist(),
                metadatas=metas,
                ids=normalized_ids,
            )
        else:
            self._chroma_collection.upsert(
                documents=text_list,
                embeddings=vectors.tolist(),
                metadatas=metas,
                ids=normalized_ids,
            )
        return {"store": "chroma", "count": len(text_list)}

    def search(
        self,
        query: str,
        k: int = 5,
        namespace: str | None = None,
        user_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search the configured vector store for semantically similar text."""
        if not query or not str(query).strip():
            return []
        if k <= 0:
            return []
        normalized_namespace = _normalize_namespace(namespace)
        normalized_user_id = _normalize_namespace(user_id)
        if not normalized_user_id:
            raise ValueError("Vector search requires user_id")

        if self.store == "faiss":
            if self._index is None or not self._texts:
                return []
            vectors = self._embed_np([str(query)])
            if vectors.size == 0:
                return []
            vectors = _normalize_embeddings(vectors)
            search_k = (
                len(self._texts)
                if normalized_namespace is not None
                or normalized_user_id is not None
                else k
            )
            scores, indices = self._index.search(vectors, search_k)
            results: list[dict[str, Any]] = []
            for idx, score in zip(indices[0], scores[0]):
                if idx < 0 or idx >= len(self._texts):
                    continue
                meta = self._metadatas[idx]
                if not _namespace_matches(meta, normalized_namespace):
                    continue
                if _metadata_user_id(meta) != normalized_user_id:
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
        where_clauses: list[dict[str, Any]] = [{"user_id": normalized_user_id}]
        if normalized_namespace is not None:
            where_clauses.append({"namespace": normalized_namespace})
        if len(where_clauses) == 1:
            query_kwargs["where"] = where_clauses[0]
        else:
            query_kwargs["where"] = {"$and": where_clauses}
        result = self._chroma_collection.query(**query_kwargs)
        docs = result.get("documents", [[]])[0] or []
        metas = result.get("metadatas", [[]])[0] or []
        distances = result.get("distances", [[]])[0] or []
        ids = result.get("ids", [[]])[0] or []
        matches: list[dict[str, Any]] = []
        for idx, doc in enumerate(docs):
            meta = metas[idx] if idx < len(metas) else {}
            if _metadata_user_id(meta) != normalized_user_id:
                continue
            if not _namespace_matches(meta, normalized_namespace):
                continue
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

    def get_ids(self, where: dict[str, Any]) -> list[str]:
        """Return ids matching a metadata filter (Chroma only)."""
        if self.store != "chroma" or self._chroma_collection is None:
            return []
        if not where:
            return []
        result = self._chroma_collection.get(where=where)
        ids = result.get("ids") or []
        return [str(value) for value in ids]

    def delete_by_ids(self, ids: list[str]) -> int:
        """Delete documents by id (Chroma only)."""
        if self.store != "chroma" or self._chroma_collection is None:
            return 0
        cleaned = [str(value).strip() for value in ids]
        cleaned = [value for value in cleaned if value]
        if not cleaned:
            return 0
        self._chroma_collection.delete(ids=cleaned)
        return len(cleaned)


class Embedder(LocalSemanticEmbedder):
    """Compatibility wrapper with document helpers used across the app."""

    def __init__(
        self,
        use_openai: bool = False,
        model: str | None = None,
        store: str = DEFAULT_STORE,
        chroma_path: str = "./.chroma",
        collection: str = "codexify_vault_supported",
    ) -> None:
        backend = (
            (
                os.getenv("CODEXIFY_EMBEDDINGS_BACKEND")
                or os.getenv("EMBEDDING_BACKEND")
                or DEFAULT_BACKEND
            )
            .strip()
            .lower()
        )

        if backend not in _ALLOWED_BACKENDS:
            logger.warning(
                "[embedder] invalid backend=%s, falling back to %s",
                backend,
                _BACKEND_SENTENCE_TRANSFORMER,
            )
            backend = _BACKEND_SENTENCE_TRANSFORMER

        # Safety gate: never allow an OpenAI embedding path to be selected unless a key is present.
        # MemoryOS/legacy integrations sometimes pass use_openai=True by default.
        openai_key = (os.getenv("OPENAI_API_KEY") or "").strip()
        if use_openai and not openai_key:
            logger.warning(
                "[embedder] use_openai=True requested but OPENAI_API_KEY is missing; "
                "forcing local embeddings for stability"
            )
            use_openai = False

        # This module implements local embeddings only (sentence-transformers / local cache / mock).
        # If callers request OpenAI embeddings, they must do so via the Guardian runtime embedder,
        # not this compatibility wrapper.
        if use_openai:
            logger.info(
                "[embedder] use_openai=True requested; "
                "this backend/rag embedder is local-only and will ignore OpenAI"
            )

        if backend != "local":
            _ = get_local_embed_model(strict=False)
        super().__init__(
            model=model,
            store=store,
            chroma_path=chroma_path,
            collection=collection,
            backend=backend,
        )

    def embed_documents(
        self,
        documents: list[str],
        metadatas: list[dict[str, Any]] | None = None,
        ids_prefix: str = "doc",
        ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Compatibility layer for document ingestion flows."""
        result = self.embed_and_index(
            documents, metadatas=metadatas, ids_prefix=ids_prefix, ids=ids
        )
        return [result]
