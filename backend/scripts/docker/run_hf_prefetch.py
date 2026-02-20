from __future__ import annotations

import os

from common import log
from huggingface_hub import snapshot_download


def main() -> int:
    raw_models = os.environ.get("HF_PREFETCH_MODELS", "")
    models = [model.strip() for model in raw_models.split(",") if model.strip()]
    if not models:
        raise SystemExit(
            "HF_PREFETCH_MODELS is empty. Set it to a comma-separated list, "
            "e.g. HF_PREFETCH_MODELS='coqui/XTTS-v2,facebook/mms-tts-eng'"
        )

    token = os.environ.get("HF_TOKEN") or None
    for repo_id in models:
        log("hf-prefetch", f"Downloading {repo_id} ...")
        snapshot_download(repo_id=repo_id, token=token)

    log("hf-prefetch", "Done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
