import logging
import os
from functools import lru_cache

from guardian.utils.embed_paths import resolve_local_embed_model

logger = logging.getLogger(__name__)


def _is_local_embeddings_backend() -> bool:
    backend = (os.getenv("CODEXIFY_EMBEDDINGS_BACKEND") or "").strip().lower()
    return backend == "local"


def _get_local_embed_model(*, strict: bool) -> str | None:
    if strict:
        return resolve_local_embed_model(ValueError)
    model = (os.getenv("LOCAL_EMBED_MODEL") or "").strip()
    return model or None


class LocalEmbedder:
    def __init__(self, model_name: str | None = None):
        if model_name:
            logger.warning(
                "[memoryos] model override ignored; use LOCAL_EMBED_MODEL"
            )
        is_local = _is_local_embeddings_backend()
        model_name = _get_local_embed_model(strict=is_local)
        self.model = None

        if not is_local:
            logger.info(
                "[memoryos] skipping local embedder init; backend=%s",
                (os.getenv("CODEXIFY_EMBEDDINGS_BACKEND") or "")
                .strip()
                .lower()
                or "<unset>",
            )
            return

        logger.info("[memoryos] local embedding model=%s", model_name)
        try:
            from sentence_transformers import SentenceTransformer

            self.model = SentenceTransformer(model_name, local_files_only=True)
        except Exception as exc:
            raise RuntimeError(
                "LOCAL_EMBED_MODEL is set but could not be loaded from local cache."
            ) from exc
        _ = self.model.encode("preloading model")

    @lru_cache(maxsize=1024)
    def embed(self, text: str) -> list[float]:
        """
        Embed a single string of text using a sentence-transformers model.

        Args:
            text (str): The input text to embed.

        Returns:
            List[float]: The embedding vector as a list of floats.
        """
        if self.model is None:
            return []
        result = self.model.encode(text)
        return result.tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Embed a list of strings using the sentence-transformers model.

        Args:
            texts (list[str]): The list of texts to embed.

        Returns:
            list[list[float]]: List of embedding vectors for each input string.
        """
        if self.model is None:
            return [[] for _ in texts]
        results = self.model.encode(texts, convert_to_numpy=True)
        return [row.tolist() for row in results]
