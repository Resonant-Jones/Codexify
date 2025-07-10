from .base_embedders import BaseEmbedder
import os


class AnthropicEmbedder(BaseEmbedder):
    """
    Placeholder for an Anthropic embedder.
    NOTE: Anthropic does not currently provide a public embedding API.
    """

    def __init__(self):
        """
        Initializes the embedder. An API key is checked for future-proofing,
        but the embed method is not implemented.
        """
        self.api_key = os.getenv("ANTHROPIC_API_KEY")

    def embed(self, text: str) -> list:
        """
        This method is not implemented as Anthropic does not offer a public embedding API.
        """
        raise NotImplementedError(
            "Anthropic does not provide a dedicated public embedding API."
        )
