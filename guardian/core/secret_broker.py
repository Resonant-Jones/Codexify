"""Secret broker abstraction and env-backed implementation."""

from __future__ import annotations

import os
import re
from typing import Protocol

_SECRET_PREFIX = "CODEXIFY_SECRET_"


class SecretBrokerError(RuntimeError):
    """Raised when secret access fails."""


class SecretBroker(Protocol):
    def get_secret(self, secret_id: str) -> str:
        ...

    def set_secret(self, secret_id: str, value: str) -> None:
        ...

    def is_available(self) -> bool:
        ...


def _normalize_secret_id(secret_id: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", (secret_id or "").strip())
    cleaned = cleaned.strip("_").upper()
    if not cleaned:
        raise SecretBrokerError("secret_id must be a non-empty identifier")
    return cleaned


def _env_var_name(secret_id: str) -> str:
    return f"{_SECRET_PREFIX}{_normalize_secret_id(secret_id)}"


class EnvSecretBroker:
    """Env-based secret broker for local/test deployments."""

    def get_secret(self, secret_id: str) -> str:
        env_name = _env_var_name(secret_id)
        value = os.getenv(env_name)
        if value is None or value.strip() == "":
            raise SecretBrokerError(
                f"secret '{secret_id}' is not configured (expected env: {env_name})"
            )
        return value

    def set_secret(self, secret_id: str, value: str) -> None:
        env_name = _env_var_name(secret_id)
        os.environ[env_name] = value

    def is_available(self) -> bool:
        return True


__all__ = [
    "EnvSecretBroker",
    "SecretBroker",
    "SecretBrokerError",
]
