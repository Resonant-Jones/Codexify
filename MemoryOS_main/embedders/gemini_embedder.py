from .base_embedders import BaseEmbedder
import os
import requests


class GeminiEmbedder(BaseEmbedder):
    """
    Embedder that uses the Gemini LLM API to generate embeddings.
    """

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.api_url = "https://generativelanguage.googleapis.com/v1beta/models/embedding-001:embedText"
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")

    def embed(self, text: str) -> list:
        payload = {"model": "embedding-001", "content": {"parts": [{"text": text}]}}
        headers = {"Content-Type": "application/json"}
        params = {"key": self.api_key}
        response = requests.post(
            self.api_url, json=payload, headers=headers, params=params
        )
        response.raise_for_status()
        result = response.json()
        return result["embedding"]["values"]
