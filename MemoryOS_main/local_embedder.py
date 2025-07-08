# local_embedder.py
from sentence_transformers import SentenceTransformer
from embedding_provider import EmbeddingProvider

class LocalEmbedder(EmbeddingProvider):
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)

    def embed(self, text: str) -> list[float]:
        return self.model.encode(text).tolist()