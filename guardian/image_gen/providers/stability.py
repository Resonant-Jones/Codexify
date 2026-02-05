from typing import Any, Dict

from fastapi import HTTPException

from guardian.image_gen.base import ImageGenProvider


class StabilityImageGen(ImageGenProvider):
    name = "stability"

    def generate(
        self,
        prompt: str,
        model: str | None = None,
        **kwargs: Dict[str, Any],
    ) -> bytes:
        raise HTTPException(
            status_code=503,
            detail=(
                "Stability image generation is not implemented. "
                "Configure IMAGE_GEN_PROVIDER=openai or add Stability support."
            ),
        )
