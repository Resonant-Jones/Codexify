from __future__ import annotations

import json
import os
from pathlib import Path


def get_local_embed_model(*, strict: bool) -> str | None:
    """Return LOCAL_EMBED_MODEL if set, otherwise None.

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
                "LOCAL_EMBED_MODEL is not set. Set LOCAL_EMBED_MODEL to a local model id or path."
            )
        return None

    if strict:
        path = Path(model_name).expanduser()
        if not path.is_absolute():
            raise RuntimeError(
                "LOCAL_EMBED_MODEL must be an absolute path (e.g. /models/bge-large-en-v1.5)."
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


def resolve_local_embed_dimension(*, strict: bool = False) -> int | None:
    """Return the configured local embedding model's own vector dimension.

    The dimension is read from the model's own config (``hidden_size`` for a
    BERT-family encoder), so it describes the model that will actually produce
    vectors. It is deliberately derived from the model rather than hardcoded:
    ``bge-large-en-v1.5`` is 1024-dimensional, while 384 is the dimension of
    ``bge-small-en-v1.5`` and of Chroma's default embedding function.

    Returns ``None`` when the model is not configured as a local path or its
    config cannot be read. With ``strict=True`` an unresolvable dimension is
    an error instead.
    """

    model_name = get_local_embed_model(strict=strict)
    if not model_name:
        if strict:
            raise RuntimeError(
                "LOCAL_EMBED_MODEL is not set, so the embedding dimension "
                "cannot be resolved."
            )
        return None

    config_path = Path(model_name).expanduser() / "config.json"
    try:
        raw = config_path.read_text(encoding="utf-8")
    except OSError:
        if strict:
            raise RuntimeError(
                f"Could not read embedding model config at {config_path}."
            )
        return None

    try:
        config = json.loads(raw)
    except ValueError:
        if strict:
            raise RuntimeError(
                f"Embedding model config at {config_path} is not valid JSON."
            )
        return None

    for key in ("hidden_size", "dim", "embedding_size"):
        value = config.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, int) and value > 0:
            return value

    if strict:
        raise RuntimeError(
            f"Embedding model config at {config_path} declares no dimension."
        )
    return None


def resolve_local_embed_model(
    exc_type: type[Exception] = RuntimeError,
) -> str:
    """Backward-compatible alias for older call sites.

    Historically this function raised immediately if LOCAL_EMBED_MODEL was not
    set and required it to be an absolute path. We now keep that behavior but
    route through the strict accessor to share validation.
    """

    try:
        return require_local_embed_model()
    except Exception as e:  # pragma: no cover
        # Preserve the historical ability to customize exception type.
        if exc_type is RuntimeError:
            raise
        raise exc_type(str(e)) from e
