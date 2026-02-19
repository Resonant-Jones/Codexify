"""Ensure the local embedding model exists before app/worker startup."""

from __future__ import annotations

import fcntl
import os
import sys
import time
from pathlib import Path

DEFAULT_LOCAL_EMBED_MODEL = "/models/bge-large-en-v1.5"
DEFAULT_EMBED_MODEL_ID = "BAAI/bge-large-en-v1.5"
LOCK_PATH = Path("/models/.embed_model.lock")
SUCCESS_SENTINEL = ".codexify_model_ok"
CHECK_FILES = ("config.json", "model.safetensors", SUCCESS_SENTINEL)
MAX_ATTEMPTS = 3
BASE_BACKOFF_SECONDS = 2

try:
    from huggingface_hub import snapshot_download
except Exception as exc:  # pragma: no cover - import guard
    snapshot_download = None  # type: ignore[assignment]
    _IMPORT_ERROR = exc


def _env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is None:
        return default
    value = value.strip()
    if not value:
        return default
    return value


def _model_present(model_dir: Path) -> bool:
    return model_dir.is_dir() and any(
        (model_dir / filename).exists() for filename in CHECK_FILES
    )


def _download_model(
    model_dir: Path,
    model_id: str,
    revision: str | None,
    hf_token: str | None,
) -> None:
    kwargs: dict[str, object] = {
        "repo_id": model_id,
        "local_dir": str(model_dir),
        "local_dir_use_symlinks": False,
    }
    if revision:
        kwargs["revision"] = revision
    if hf_token:
        kwargs["token"] = hf_token

    snapshot_download(**kwargs)  # type: ignore[misc]
    (model_dir / SUCCESS_SENTINEL).write_text("ok\n", encoding="utf-8")


def main() -> int:
    """Ensure the local embedding model exists, downloading it if needed."""
    local_embed_model = _env("LOCAL_EMBED_MODEL", DEFAULT_LOCAL_EMBED_MODEL)
    if not local_embed_model:
        print("[embed-model] ERROR: LOCAL_EMBED_MODEL is not set", file=sys.stderr)
        return 1

    model_dir = Path(local_embed_model)
    model_id = _env("EMBED_MODEL_ID", DEFAULT_EMBED_MODEL_ID)
    revision = _env("EMBED_MODEL_REVISION")
    hf_token = _env("HF_TOKEN")
    hf_home = _env("HF_HOME")

    if not model_id:
        print("[embed-model] ERROR: EMBED_MODEL_ID is empty", file=sys.stderr)
        return 1

    if snapshot_download is None:
        import_error = str(_IMPORT_ERROR)
        print(
            f"[embed-model] ERROR: huggingface_hub import failed: {import_error}",
            file=sys.stderr,
        )
        return 1

    if _model_present(model_dir):
        print("model present")
        return 0

    model_dir.parent.mkdir(parents=True, exist_ok=True)
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)

    print(f"[embed-model] waiting for lock at {LOCK_PATH}")
    with LOCK_PATH.open("a+", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)

        if _model_present(model_dir):
            print("model present")
            return 0

        if hf_home:
            os.environ.setdefault("HF_HOME", hf_home)

        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                print(
                    "[embed-model] downloading model... "
                    f"repo={model_id} attempt={attempt}/{MAX_ATTEMPTS}"
                )
                _download_model(
                    model_dir=model_dir,
                    model_id=model_id,
                    revision=revision,
                    hf_token=hf_token,
                )
                print("[embed-model] download complete")
                return 0
            except Exception as exc:  # pragma: no cover - network/transient failures
                print(
                    "[embed-model] download failed "
                    f"attempt={attempt}/{MAX_ATTEMPTS}: {exc}",
                    file=sys.stderr,
                )
                if attempt == MAX_ATTEMPTS:
                    return 1
                backoff_seconds = BASE_BACKOFF_SECONDS * attempt
                print(f"[embed-model] retrying in {backoff_seconds}s")
                time.sleep(backoff_seconds)

    print("[embed-model] ERROR: failed to acquire download lock", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
