import base64
from typing import Any, Dict

from fastapi import HTTPException

from guardian.image_gen.base import ImageGenProvider

try:
    from openai import OpenAI  # type: ignore
except Exception:
    OpenAI = None  # type: ignore


class OpenAIImageGen(ImageGenProvider):
    name = "openai"

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        if OpenAI is None:
            raise HTTPException(
                status_code=500, detail="openai package not installed"
            )
        try:
            if api_key or base_url:
                self.client = OpenAI(api_key=api_key, base_url=base_url)
            else:
                self.client = OpenAI()
        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail="OpenAI API key is not configured",
            ) from exc

    def generate(
        self,
        prompt: str,
        model: str | None = None,
        **kwargs: Dict[str, Any],
    ) -> bytes:
        if not model:
            raise HTTPException(
                status_code=400,
                detail="Model is required for OpenAI image generation.",
            )
        size = kwargs.get("size", "1024x1024")
        try:
            result = self.client.images.generate(
                model=model,
                prompt=prompt,
                size=size,
                response_format="b64_json",
            )
        except Exception as exc:
            status = getattr(exc, "status_code", None)
            if status == 400:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            if status in (401, 403):
                raise HTTPException(
                    status_code=400,
                    detail="OpenAI API key is missing or invalid",
                ) from exc
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        data = getattr(result, "data", None) or []
        if not data or not getattr(data[0], "b64_json", None):
            raise HTTPException(
                status_code=502,
                detail="OpenAI image API returned no image data",
            )

        try:
            return base64.b64decode(data[0].b64_json)
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail="Failed to decode OpenAI image data",
            ) from exc
