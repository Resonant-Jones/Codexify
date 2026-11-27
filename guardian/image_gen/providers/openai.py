import base64
import os
from typing import Any

from fastapi import HTTPException

from guardian.core.egress import EgressDeniedError, assert_egress_allowed
from guardian.image_gen.base import ImageGenProvider
from guardian.metering.runtime import deny_unqualified_spend

try:
    from openai import OpenAI  # type: ignore
except Exception:
    OpenAI = None  # type: ignore


class OpenAIImageGen(ImageGenProvider):
    name = "openai"
    label = "OpenAI"
    default_model = "gpt-image-2.6-sunburst"
    model_aliases = {"sunburst": default_model, "flare": "gpt-image-2.6-flare"}
    retired_models = frozenset(
        {
            "gpt-image-1",
            "gpt-image-1-mini",
            "gpt-image-1.5",
            "gpt-image-1.5-2025-12-16",
            "chatgpt-image-latest",
            "dall-e-3",
            "dall-e-2",
        }
    )
    supported_models = {
        *model_aliases.values(),
        "gpt-image-2.5-sunburst",
        "gpt-image-2.5-flare",
        "gpt-image-2",
    }

    @classmethod
    def unavailable_reason(cls) -> str | None:
        try:
            assert_egress_allowed(cls.name)
        except EgressDeniedError as exc:
            return str(exc)
        if OpenAI is None:
            return "The OpenAI image adapter is not installed."
        if not os.getenv("OPENAI_API_KEY", "").strip():
            return "OpenAI image generation is not configured."
        return None

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        try:
            assert_egress_allowed("openai")
        except EgressDeniedError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        if OpenAI is None:
            raise HTTPException(status_code=500, detail="openai package not installed")
        resolved_base = (
            (base_url or os.getenv("OPENAI_BASE_URL") or "").strip().rstrip("/")
        )
        # Guardian's shared OpenAI setting is an origin; the SDK expects /v1.
        if resolved_base == "https://api.openai.com":
            resolved_base += "/v1"
        try:
            if api_key or resolved_base:
                self.client = OpenAI(
                    api_key=api_key,
                    base_url=resolved_base or None,
                    timeout=180,
                    max_retries=0,
                )
            else:
                self.client = OpenAI(timeout=180, max_retries=0)
        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail="OpenAI API key is not configured",
            ) from exc

    def generate(
        self,
        prompt: str,
        model: str | None = None,
        **kwargs: dict[str, Any],
    ) -> bytes:
        deny_unqualified_spend()
        if not model:
            raise HTTPException(
                status_code=400,
                detail="Model is required for OpenAI image generation.",
            )
        size = kwargs.get("size", "1024x1024")
        try:
            params = dict(model=model, prompt=prompt, size=size, n=1)
            if model.startswith("gpt-image-"):
                # GPT Image always returns base64; legacy response_format is invalid.
                params.update(
                    output_format="png",
                    quality=kwargs.get("quality", "medium"),
                )
            else:
                params["response_format"] = "b64_json"
            result = self.client.images.generate(**params)
        except Exception as exc:
            status = getattr(exc, "status_code", None)
            if status == 400:
                raise HTTPException(
                    status_code=400,
                    detail="OpenAI rejected the image request. Check the prompt, model access, and generation settings.",
                ) from exc
            if status in (401, 403):
                raise HTTPException(
                    status_code=400,
                    detail="OpenAI image access was denied. Check credentials and model access.",
                ) from exc
            if status == 429:
                raise HTTPException(
                    status_code=429,
                    detail="OpenAI image rate or credit limit reached. Try again later.",
                ) from exc
            raise HTTPException(
                status_code=502,
                detail="OpenAI image generation failed. No automatic retry was made.",
            ) from exc

        data = getattr(result, "data", None) or []
        if not data or not getattr(data[0], "b64_json", None):
            raise HTTPException(
                status_code=502,
                detail="OpenAI image API returned no image data",
            )

        try:
            decoded = base64.b64decode(data[0].b64_json, validate=True)
            if not decoded:
                raise ValueError("Empty image")
            return decoded
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail="Failed to decode OpenAI image data",
            ) from exc
