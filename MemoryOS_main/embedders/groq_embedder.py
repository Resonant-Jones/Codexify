

from .base_embedders import BaseEmbedder
import os
import requests

class GroqEmbedder(BaseEmbedder):
    """
    Embedder that uses the Groq API to generate embeddings.
    """

    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.api_url = "https://api.groq.com/openai/v1/embeddings"
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")

    def embed(self, text: str) -> list:
        payload = {
            "input": text,
            "model": "nomic-embed-text"
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        response = requests.post(self.api_url, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        return result["data"][0]["embedding"]