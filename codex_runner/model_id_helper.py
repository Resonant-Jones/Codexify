#!/usr/bin/env python3
"""Deterministically emit a MODEL_ID value for Codex audit prompts."""

from __future__ import annotations

import os
from pathlib import Path


def _env_model() -> str | None:
    """Return an env-provided model id, honoring precedence requirements."""
    for key in ("CODEX_MODEL", "OPENAI_MODEL"):
        value = os.environ.get(key)
        if value:
            return value.strip()
    return None


def _config_model() -> str | None:
    """Load ~/.codex/config.toml if present and extract the default model."""
    config_path = Path.home() / ".codex" / "config.toml"
    if not config_path.is_file():
        return None

    try:
        try:
            import tomllib  # type: ignore
        except ModuleNotFoundError:  # pragma: no cover
            import tomli as tomllib  # type: ignore

        with config_path.open("rb") as fh:
            data = tomllib.load(fh)
    except Exception:
        return None

    value = data.get("model")
    if isinstance(value, str) and value.strip():
        return value.strip()

    return None


def main() -> None:
    model = _env_model() or _config_model() or "unknown"
    print(f"MODEL_ID={model}")


if __name__ == "__main__":
    main()
