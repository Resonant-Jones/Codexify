"""Central egress policy checks for outbound network calls."""

from __future__ import annotations

import os
from typing import Optional

from fastapi import HTTPException

from guardian.core.config import Settings

CLOUD_EGRESS_TARGETS = {"openai", "anthropic", "gemini", "groq", "minimax"}


class EgressDeniedError(RuntimeError):
    """Raised when outbound egress is blocked by security policy."""


def _env_bool(name: str, *, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _normalize_target(target: str) -> str:
    return (target or "").strip().lower()


def _resolve_local_only_mode(settings: Settings | None) -> bool:
    if settings is not None and hasattr(settings, "CODEXIFY_LOCAL_ONLY_MODE"):
        return bool(getattr(settings, "CODEXIFY_LOCAL_ONLY_MODE"))
    return _env_bool("CODEXIFY_LOCAL_ONLY_MODE", default=True)


def _resolve_allow_cloud_providers(settings: Settings | None) -> bool:
    if settings is not None and hasattr(settings, "ALLOW_CLOUD_PROVIDERS"):
        return bool(getattr(settings, "ALLOW_CLOUD_PROVIDERS"))
    return _env_bool("ALLOW_CLOUD_PROVIDERS", default=False)


def _resolve_allowlist(settings: Settings | None) -> set[str]:
    if settings is not None and hasattr(settings, "CODEXIFY_EGRESS_ALLOWLIST"):
        raw = str(getattr(settings, "CODEXIFY_EGRESS_ALLOWLIST") or "")
    else:
        raw = os.getenv("CODEXIFY_EGRESS_ALLOWLIST") or ""
    return {entry.strip().lower() for entry in raw.split(",") if entry.strip()}


def _denied(message: str) -> None:
    raise EgressDeniedError(message)


def assert_egress_allowed(
    target: str,
    *,
    settings: Settings | None = None,
) -> None:
    """Raise when outbound egress target is not explicitly allowed."""

    normalized = _normalize_target(target)
    if not normalized:
        _denied("Egress target is required.")

    if _resolve_local_only_mode(settings):
        _denied(
            f"Egress '{normalized}' blocked: CODEXIFY_LOCAL_ONLY_MODE=true."
        )

    allowlist = _resolve_allowlist(settings)
    if not allowlist:
        _denied(
            f"Egress '{normalized}' blocked: CODEXIFY_EGRESS_ALLOWLIST is empty."
        )
    if "*" not in allowlist and normalized not in allowlist:
        _denied(
            "Egress '{}' blocked: target not present in CODEXIFY_EGRESS_ALLOWLIST.".format(
                normalized
            )
        )

    if (
        normalized in CLOUD_EGRESS_TARGETS
        and not _resolve_allow_cloud_providers(settings)
    ):
        _denied(f"Egress '{normalized}' blocked: ALLOW_CLOUD_PROVIDERS=false.")


def require_egress_allowed(
    target: str,
    *,
    settings: Settings | None = None,
) -> None:
    """HTTP-aware wrapper around `assert_egress_allowed`."""

    try:
        assert_egress_allowed(target, settings=settings)
    except EgressDeniedError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


__all__ = [
    "EgressDeniedError",
    "assert_egress_allowed",
    "require_egress_allowed",
]
