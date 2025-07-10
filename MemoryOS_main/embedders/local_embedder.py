# local_embedder.py
from sentence_transformers import SentenceTransformer
from .base_embedders import BaseEmbedder

class LocalEmbedder(BaseEmbedder):
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)

    def embed(self, text: str) -> list[float]:
        return self.model.encode(text).tolist()