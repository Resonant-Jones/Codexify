from abc import ABC, abstractmethod
from typing import Any, Dict


class ImageGenProvider(ABC):
    name: str = ""
    label: str = ""
    default_model: str = ""
    model_aliases: dict[str, str] = {}
    supported_models: set[str] | None = None
    catalog_models: set[str] | None = None

    @classmethod
    def unavailable_reason(cls) -> str | None:
        return "This image adapter is not implemented."

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
