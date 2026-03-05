import os
import sys
from pathlib import Path

MODEL_DIR = Path(
    os.environ.get("CFY_EMBED_MODEL_DIR", "/models/bge-large-en-v1.5")
)
HF_REPO_ID = os.environ.get("CFY_EMBED_MODEL_REPO", "BAAI/bge-large-en-v1.5")
REVISION = os.environ.get("CFY_EMBED_MODEL_REVISION")  # optional


def main() -> int:
    # Fast-path: directory exists and is non-empty.
    if MODEL_DIR.exists() and any(MODEL_DIR.iterdir()):
        print(f"[model-prep] OK: model present at {MODEL_DIR}")
        return 0

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[model-prep] Downloading {HF_REPO_ID} -> {MODEL_DIR}")

    try:
        from huggingface_hub import snapshot_download
    except Exception as e:
        print(
            "[model-prep] ERROR: huggingface_hub not available in this image.",
            file=sys.stderr,
        )
        print(f"[model-prep] Detail: {e}", file=sys.stderr)
        return 2

    snapshot_download(
        repo_id=HF_REPO_ID,
        local_dir=str(MODEL_DIR),
        local_dir_use_symlinks=False,
        revision=REVISION,
    )

    # Minimal integrity check
    if not any(MODEL_DIR.iterdir()):
        print(
            "[model-prep] ERROR: download completed but directory is empty.",
            file=sys.stderr,
        )
        return 3

    print(f"[model-prep] DONE: model ready at {MODEL_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
