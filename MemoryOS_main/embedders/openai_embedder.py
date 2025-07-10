# openai_embedder.py
from openai import OpenAI
from .base_embedders import BaseEmbedder

class OpenAIEmbedder(BaseEmbedder):
    def __init__(self, api_key: str):
        # Instantiate a client instead of setting a global key for better practice.
        self.client = OpenAI(api_key=api_key)

    def embed(self, text: str) -> list[float]:
        # Use the new client-based API for embeddings
        response = self.client.embeddings.create(
            model="text-embedding-3-large",
            input=text
        )
        # The response object structure has also changed in v1.x
        return response.data[0].embedding
