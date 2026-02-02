from __future__ import annotations

import os
from typing import Type


def resolve_local_embed_model(
    exc_type: type[Exception] = RuntimeError,
) -> str:
    model_name = (os.getenv("LOCAL_EMBED_MODEL") or "").strip()
    if not model_name:
        raise exc_type(
            "LOCAL_EMBED_MODEL is not set. Set LOCAL_EMBED_MODEL to a local model id or path."
        )
    if not os.path.isabs(model_name):
        raise exc_type(
            "LOCAL_EMBED_MODEL must be an absolute path (e.g. /models/bge-large-en-v1.5)."
        )
    return model_name
