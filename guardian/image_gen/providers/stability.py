import base64
from typing import Any, Dict

from fastapi import HTTPException

from guardian.image_gen.base import ImageGenProvider

_PLACEHOLDER_PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8"
    "/x8AAwMCAO+XlX0AAAAASUVORK5CYII="
)


class StabilityImageGen(ImageGenProvider):
    name = "stability"

    def generate(
        self,
        prompt: str,
        model: str | None = None,
        **kwargs: Dict[str, Any],
    ) -> bytes:
        if not model:
            raise HTTPException(
                status_code=400,
                detail="Model is required for Stability image generation.",
            )
        return base64.b64decode(_PLACEHOLDER_PNG_BASE64)
