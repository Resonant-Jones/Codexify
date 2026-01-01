from abc import ABC, abstractmethod
from typing import Any, Dict


class ImageGenProvider(ABC):
    name: str = ""
    supported_models: set[str] | None = None

    @abstractmethod
    def generate(
        self,
        prompt: str,
        model: str | None = None,
        **kwargs: Dict[str, Any],
    ) -> bytes:
        """
        Return raw image bytes (PNG/JPEG).
        Providers are responsible for any API calls or local execution.
        """
