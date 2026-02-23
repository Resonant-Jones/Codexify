import hashlib
import logging
import os
from typing import Iterable, List

from guardian.utils.embed_paths import resolve_local_embed_model

logger = logging.getLogger(__name__)


def _resolve_embeddings_backend() -> str:
    backend = (os.getenv("CODEXIFY_EMBEDDINGS_BACKEND") or "").strip().lower()
    if backend:
        return backend
    return os.getenv("EMBEDDING_BACKEND", "stub").strip().lower()


def _is_local_backend(backend: str) -> bool:
    return (backend or "").strip().lower() == "local"


def _get_local_embed_model(*, strict: bool) -> str | None:
    if strict:
        return resolve_local_embed_model()
    model = (os.getenv("LOCAL_EMBED_MODEL") or "").strip()
    return model or None


def _stub_embed(text: str, dim: int = 128) -> List[float]:
    """Deterministic, offline stub embedding using token hashing into a fixed dim."""
    vec = [0.0] * dim
    for tok in text.split():
        h = int(hashlib.sha256(tok.encode("utf-8")).hexdigest(), 16)
        idx = h % dim
        vec[idx] += 1.0
    # L2 normalize
    import math

    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


class Embedder:
    def __init__(self) -> None:
        self.backend = _resolve_embeddings_backend()
        self.dim = int(os.getenv("EMBEDDING_DIM", "128"))
        self._model = None
        is_local = _is_local_backend(self.backend)
        if is_local:
            try:
                from sentence_transformers import (
                    SentenceTransformer,  # type: ignore
                )
            except Exception as exc:
                raise RuntimeError(
                    "sentence-transformers is required for EMBEDDING_BACKEND=local."
                ) from exc

            model_name = _get_local_embed_model(strict=True)
            logger.info("[embeds] local embedding model=%s", model_name)
            try:
                self._model = SentenceTransformer(
                    model_name, local_files_only=True
                )
            except Exception as exc:
                raise RuntimeError(
                    "LOCAL_EMBED_MODEL is set but could not be loaded from local cache."
                ) from exc

    def embed(self, texts: Iterable[str]) -> List[List[float]]:
        if self.backend == "local" and self._model is not None:
            import numpy as np  # type: ignore

            arr = self._model.encode(list(texts), convert_to_numpy=True)
            out: List[List[float]] = []
            for v in arr:
                norm = float(np.linalg.norm(v)) or 1.0
                out.append((v / norm).tolist())
            return out
        # stub
        return [_stub_embed(t, self.dim) for t in texts]
