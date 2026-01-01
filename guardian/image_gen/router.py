import os
from typing import Type

from fastapi import HTTPException

from guardian.image_gen.base import ImageGenProvider
from guardian.image_gen.providers.local import LocalImageGen
from guardian.image_gen.providers.openai import OpenAIImageGen
from guardian.image_gen.providers.stability import StabilityImageGen

_PROVIDERS: dict[str, Type[ImageGenProvider]] = {
    "openai": OpenAIImageGen,
    "local": LocalImageGen,
    "stability": StabilityImageGen,
}


def _resolve_provider(provider: str | None = None) -> str:
    provider_name = (
        (provider or os.getenv("IMAGE_GEN_PROVIDER") or "").strip().lower()
    )
    if not provider_name:
        raise HTTPException(
            status_code=400,
            detail=(
                "IMAGE_GEN_PROVIDER is not configured. "
                "Set IMAGE_GEN_PROVIDER to one of: openai, local, stability."
            ),
        )
    return provider_name


def _resolve_model(model: str | None = None) -> str:
    resolved = (model or os.getenv("IMAGE_GEN_MODEL") or "").strip()
    if not resolved:
        raise HTTPException(
            status_code=400,
            detail=(
                "IMAGE_GEN_MODEL is not configured and no model was provided. "
                "Set IMAGE_GEN_MODEL or pass a model in the request."
            ),
        )
    return resolved


def _validate_model(provider: ImageGenProvider, model: str) -> None:
    supported = getattr(provider, "supported_models", None)
    if supported is None:
        return
    if model not in supported:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Model '{model}' is not supported for provider '{provider.name}'."
            ),
        )


class ImageGenRouter:
    @staticmethod
    def get_provider(provider: str | None = None) -> ImageGenProvider:
        provider_name = _resolve_provider(provider)
        provider_cls = _PROVIDERS.get(provider_name)
        if not provider_cls:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Unsupported image gen provider: "
                    f"{provider_name}. Expected one of: openai, local, stability."
                ),
            )
        return provider_cls()

    @staticmethod
    def resolve_model(model: str | None = None) -> str:
        return _resolve_model(model)

    @staticmethod
    def generate(
        prompt: str,
        model: str | None = None,
        **kwargs,
    ) -> bytes:
        provider = ImageGenRouter.get_provider()
        resolved_model = _resolve_model(model)
        _validate_model(provider, resolved_model)
        return provider.generate(prompt, model=resolved_model, **kwargs)
