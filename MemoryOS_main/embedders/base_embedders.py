from abc import ABC, abstractmethod

class BaseEmbedder(ABC):
    """
    Abstract base class for all embedders.
    """

    @abstractmethod
    def embed(self, text: str) -> list:
        """
        Embed the given text and return a vector representation.
        """
        pass