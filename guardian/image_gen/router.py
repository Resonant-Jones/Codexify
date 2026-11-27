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
    def catalog() -> dict:
        """Configuration evidence only; this does not probe paid model access."""
        providers = []
        for name, adapter in _PROVIDERS.items():
            reason = adapter.unavailable_reason()
            providers.append(
                {
                    "id": name,
                    "label": adapter.label or name,
                    "models": sorted(
                        adapter.catalog_models
                        if adapter.catalog_models is not None
                        else adapter.supported_models or []
                    ),
                    "default_model": adapter.default_model,
                    "model_aliases": adapter.model_aliases,
                    "available": reason is None,
                    "unavailable_reason": reason,
                }
            )
        default_provider = (
            (os.getenv("IMAGE_GEN_PROVIDER") or "openai").strip().lower()
        )
        default_adapter = _PROVIDERS.get(default_provider)
        return {
            "providers": providers,
            "default_provider": default_provider,
            "default_model": os.getenv("IMAGE_GEN_MODEL")
            or (default_adapter.default_model if default_adapter else ""),
        }

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
    def resolve_model(
        model: str | None = None, provider: str | None = None
    ) -> str:
        configured = (model or os.getenv("IMAGE_GEN_MODEL") or "").strip()
        if configured:
            return configured
        adapter = _PROVIDERS.get(_resolve_provider(provider))
        return _resolve_model(adapter.default_model if adapter else None)

    @staticmethod
    def generate(
        prompt: str,
        model: str | None = None,
        provider: str | None = None,
        **kwargs,
    ) -> bytes:
        provider = ImageGenRouter.get_provider(provider)
        resolved_model = ImageGenRouter.resolve_model(model, provider.name)
        _validate_model(provider, resolved_model)
        return provider.generate(prompt, model=resolved_model, **kwargs)
