import os
from functools import lru_cache

from guardian.utils.embed_paths import require_local_embed_model


class LocalEmbedder:
    def __init__(self, model_name: str | None = None):
        from sentence_transformers import SentenceTransformer

        from guardian.core.config import settings

        resolved_model = (
            model_name
            or os.getenv("LOCAL_EMBEDDER_MODEL")
            or settings.LOCAL_EMBEDDER_MODEL
        )
        if isinstance(resolved_model, str):
            resolved_model = resolved_model.strip()
        if not resolved_model:
            resolved_model = require_local_embed_model()

        self.model = SentenceTransformer(resolved_model)
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
