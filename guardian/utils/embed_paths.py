from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def get_local_embed_model(*, strict: bool) -> str | None:
    """
    Return LOCAL_EMBED_MODEL if set, otherwise None.

    If strict=True, enforce:
    - must be set
    - must be an absolute path
    - must exist and be a directory

    IMPORTANT: Call sites that are not explicitly selecting local embeddings
    should use strict=False to avoid import-time failures in non-local
    configurations.
    """
    model_name = (os.getenv("LOCAL_EMBED_MODEL") or "").strip()
    if not model_name:
        if strict:
            raise RuntimeError(
                "LOCAL_EMBED_MODEL is not set. Set LOCAL_EMBED_MODEL to a "
                "local model id or path."
            )
        return None

    if strict:
        path = Path(model_name).expanduser()
        if not path.is_absolute():
            raise RuntimeError(
                "LOCAL_EMBED_MODEL must be an absolute path (e.g. "
                "/models/bge-large-en-v1.5)."
            )
        if not path.exists() or not path.is_dir():
            raise RuntimeError(
                "LOCAL_EMBED_MODEL must point to a local directory, got: "
                f"{model_name}"
            )

    return model_name


def require_local_embed_model() -> str:
    """Strict accessor used only when local embeddings are selected."""
    value = get_local_embed_model(strict=True)
    assert value is not None
    return value
