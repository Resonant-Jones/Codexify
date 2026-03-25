"""Ensure the local embedding model exists before app/worker startup."""

from __future__ import annotations

import fcntl
import os
import shutil
import sys
import time
from pathlib import Path

DEFAULT_LOCAL_EMBED_MODEL = "/models/bge-large-en-v1.5"
DEFAULT_EMBED_MODEL_ID = "BAAI/bge-large-en-v1.5"
LOCK_PATH = Path("/models/.embed_model.lock")
SUCCESS_SENTINEL = ".codexify_model_ok"
SENTENCE_TRANSFORMER_MARKERS = (
    "modules.json",
    "sentence_bert_config.json",
    "config_sentence_transformers.json",
)
WEIGHT_FILES = ("model.safetensors", "pytorch_model.bin")
WEIGHT_SUBDIRS = ("0_Transformer",)
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


def _has_sentence_transformer_config(model_dir: Path) -> bool:
    return any(
        (model_dir / filename).is_file()
        for filename in SENTENCE_TRANSFORMER_MARKERS
    )


def _has_weight_file(model_dir: Path) -> bool:
    for filename in WEIGHT_FILES:
        if (model_dir / filename).is_file():
            return True
    for subdir in WEIGHT_SUBDIRS:
        subdir_path = model_dir / subdir
        if not subdir_path.is_dir():
            continue
        for filename in WEIGHT_FILES:
            if (subdir_path / filename).is_file():
                return True
    return False


def _model_status(model_dir: Path) -> tuple[bool, str]:
    if not model_dir.exists():
        return False, "model directory missing"
    if not model_dir.is_dir():
        return False, "model path is not a directory"
    if not _has_sentence_transformer_config(model_dir):
        return (
            False,
            "missing sentence-transformer config "
            "(modules.json, sentence_bert_config.json, or config_sentence_transformers.json)",
        )
    if not _has_weight_file(model_dir):
        return (
            False,
            "missing model weights (model.safetensors or pytorch_model.bin)",
        )
    return True, "model ready"


def _model_present(model_dir: Path) -> bool:
    return _model_status(model_dir)[0]


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
        print(
            "[embed-model] ERROR: LOCAL_EMBED_MODEL is not set", file=sys.stderr
        )
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

    present, reason = _model_status(model_dir)
    if present:
        print("model present")
        return 0

    model_dir.parent.mkdir(parents=True, exist_ok=True)
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)

    print(f"[embed-model] waiting for lock at {LOCK_PATH}")
    with LOCK_PATH.open("a+", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)

        present, reason = _model_status(model_dir)
        if present:
            print("model present")
            return 0

        if model_dir.exists():
            print(
                f"[embed-model] invalid model cache at {model_dir}: {reason}",
                file=sys.stderr,
            )
            print(
                f"[embed-model] removing incomplete cache at {model_dir}",
                file=sys.stderr,
            )
            if model_dir.is_dir():
                shutil.rmtree(model_dir)
            else:
                model_dir.unlink()

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
                present, reason = _model_status(model_dir)
                if not present:
                    print(
                        f"[embed-model] ERROR: download incomplete at {model_dir}: {reason}",
                        file=sys.stderr,
                    )
                    if model_dir.exists():
                        shutil.rmtree(model_dir, ignore_errors=True)
                    return 1
                print("[embed-model] download complete")
                return 0
            except (
                Exception
            ) as exc:  # pragma: no cover - network/transient failures
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

    print(
        "[embed-model] ERROR: failed to acquire download lock", file=sys.stderr
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
