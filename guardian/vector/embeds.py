import hashlib
import os
from typing import Iterable, List


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
        self.backend = os.getenv("EMBEDDING_BACKEND", "stub").strip().lower()
        self.dim = int(os.getenv("EMBEDDING_DIM", "128"))
        self._model = None
        if self.backend == "local":
            try:
                from sentence_transformers import SentenceTransformer  # type: ignore

                model_name = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
                self._model = SentenceTransformer(model_name)
                self.backend = "local"
            except Exception:
                # Fallback to stub if local model is unavailable/offline
                self.backend = "stub"

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
