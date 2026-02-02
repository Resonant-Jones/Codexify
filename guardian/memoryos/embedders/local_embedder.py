import logging
from functools import lru_cache

from sentence_transformers import SentenceTransformer

from guardian.utils.embed_paths import resolve_local_embed_model

logger = logging.getLogger(__name__)


class LocalEmbedder:
    def __init__(self, model_name: str | None = None):
        if model_name:
            logger.warning(
                "[memoryos] model override ignored; use LOCAL_EMBED_MODEL"
            )
        model_name = resolve_local_embed_model(ValueError)
        logger.info("[memoryos] local embedding model=%s", model_name)
        try:
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
        results = self.model.encode(texts, convert_to_numpy=True)
        return [row.tolist() for row in results]
