# openai_embedder.py
import openai
from .base_embedders import BaseEmbedder

class OpenAIEmbedder(BaseEmbedder):
    def __init__(self, api_key: str):
        openai.api_key = api_key

    def embed(self, text: str) -> list[float]:
        response = openai.Embedding.create(
            model="text-embedding-3-large",
            input=text
        )
        return response['data'][0]['embedding']
