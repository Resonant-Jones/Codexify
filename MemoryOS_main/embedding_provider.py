# embedding_provider.py
from abc import ABC, abstractmethod

class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """Convert text into an embedding vector."""
        pass
