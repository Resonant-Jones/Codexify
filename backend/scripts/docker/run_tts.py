from __future__ import annotations

import os
import platform
import sys
from pathlib import Path

from common import execv, log, run


def install_runtime_dependencies() -> None:
    log("TTS", "Installing/upgrading qwen-tts")
    run([sys.executable, "-m", "pip", "install", "-U", "qwen-tts"])

    log("TTS", "Installing/upgrading safetensors")
    run([sys.executable, "-m", "pip", "install", "-U", "safetensors"])


def validate_transformers_pipeline() -> None:
    check_cmd = [
        sys.executable,
        "-c",
        "from transformers import pipeline; print('[TTS] OK: transformers.pipeline import works')",
    ]

    result = run(check_cmd, check=False)
    if result.returncode == 0:
        return

    log(
        "TTS",
        "transformers.pipeline import failed; attempting torchvision install",
    )
    run([sys.executable, "-m", "pip", "install", "-U", "torchvision"])

    retry = run(check_cmd, check=False)
    if retry.returncode != 0:
        raise SystemExit(
            "[TTS] FATAL: transformers.pipeline still not importable"
        )


def offline_cache_checks() -> None:
    offline = (
        os.environ.get("HF_HUB_OFFLINE") == "1"
        or os.environ.get("TRANSFORMERS_OFFLINE") == "1"
    )

    if not offline:
        log("TTS", "Online mode: models will download on first use")
        return

    hf_home = os.environ.get(
        "HF_HOME", str(Path.home() / ".cache" / "huggingface")
    )
    hub_dir = Path(hf_home) / "hub"

    if not hub_dir.is_dir():
        raise SystemExit(
            f"[TTS] WARNING: HF cache {hub_dir} missing. Run: docker compose run --rm hf-prefetch"
        )

    found = sorted(p.name for p in hub_dir.iterdir() if "Qwen3-TTS" in p.name)
    if not found:
        raise SystemExit(
            "[TTS] WARNING: No Qwen3-TTS models in cache. Run: docker compose run --rm hf-prefetch"
        )

    log("TTS", f"Cached models: {found}")


def main() -> int:
    log("TTS", f"python: {sys.version}")
    log("TTS", f"platform: {platform.platform()}")

    install_runtime_dependencies()
    validate_transformers_pipeline()
    offline_cache_checks()

    execv(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "backend.tts_service.app:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
        ]
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
