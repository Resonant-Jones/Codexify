"""Voice model manifest loader/validator/downloader."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

from guardian.voice.config import VoiceRuntimeConfig, get_voice_runtime_config

logger = logging.getLogger(__name__)

MANIFEST_PATH = Path(__file__).with_name("model-manifest.json")


def load_manifest(path: Path | None = None) -> dict[str, Any]:
    manifest_path = path or MANIFEST_PATH
    with manifest_path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    models = data.get("models")
    if not isinstance(models, list):
        raise RuntimeError("voice model manifest missing models[]")
    return data


def _models_for_provider(
    manifest: dict[str, Any], provider: str
) -> list[dict[str, Any]]:
    target = provider.strip().lower()
    return [
        m
        for m in manifest.get("models", [])
        if str(m.get("provider") or "").strip().lower() == target
    ]


def _required_local_providers(config: VoiceRuntimeConfig) -> set[str]:
    required: set[str] = set()
    if config.mode in {"local", "cloud"}:
        if config.stt_provider == "whisper_local":
            required.add("whisper_local")
        if config.tts_provider in {
            "local_openai_compatible",
            "coqui",
            "qwen_local",
            "lfm_local",
        }:
            required.add(config.tts_provider)
    return required


def _path_requires_artifact(model_entry: dict[str, Any]) -> bool:
    source = model_entry.get("source") or {}
    source_type = str(source.get("type") or "").strip().lower()
    return source_type in {"huggingface", "hf", "http", "https", "file"}


def validate_manifest_for_runtime(
    config: VoiceRuntimeConfig | None = None,
    *,
    manifest_path: Path | None = None,
) -> tuple[bool, list[str]]:
    cfg = config or get_voice_runtime_config()
    manifest = load_manifest(manifest_path)
    errors: list[str] = []

    required_providers = _required_local_providers(cfg)
    for provider in sorted(required_providers):
        models = _models_for_provider(manifest, provider)
        if not models:
            errors.append(f"manifest_missing_provider:{provider}")
            continue

        artifact_models = [m for m in models if _path_requires_artifact(m)]
        for model in artifact_models:
            model_path = str(model.get("path") or "").strip()
            if not model_path:
                errors.append(
                    f"manifest_missing_path:{provider}:{model.get('id') or '<unknown>'}"
                )
                continue
            path = Path(model_path).expanduser()
            if not path.exists():
                errors.append(
                    f"missing_model_artifact:{provider}:{model.get('id')}:{path}"
                )

    return (len(errors) == 0, errors)


def _resolve_model_path(
    model_entry: dict[str, Any], models_dir: str | None
) -> Path:
    declared = Path(
        str(model_entry.get("path") or "").strip() or "/models/voice"
    )
    if models_dir:
        root = Path(models_dir)
        root.mkdir(parents=True, exist_ok=True)
        return root / declared.name
    return declared


def pull_manifest_models(
    *,
    models_dir: str | None = None,
    manifest_path: Path | None = None,
) -> None:
    manifest = load_manifest(manifest_path)

    for model in manifest.get("models", []):
        source = model.get("source") or {}
        source_type = str(source.get("type") or "").strip().lower()
        target_path = _resolve_model_path(model, models_dir)
        model_id = str(model.get("id") or target_path.name)

        if target_path.exists() and any(target_path.iterdir()):
            logger.info(
                "[voice-manifest] model present id=%s path=%s",
                model_id,
                target_path,
            )
            continue

        if source_type in {"huggingface", "hf"}:
            repo_id = str(source.get("repo_id") or "").strip()
            if not repo_id:
                raise RuntimeError(
                    f"manifest missing source.repo_id for model={model_id}"
                )

            revision = str(source.get("revision") or "").strip() or None
            token = (os.getenv("HF_TOKEN") or "").strip() or None
            target_path.mkdir(parents=True, exist_ok=True)

            try:
                from huggingface_hub import snapshot_download
            except Exception as exc:  # pragma: no cover - dependency guard
                raise RuntimeError(
                    "huggingface_hub is required for manifest pull"
                ) from exc

            logger.info(
                "[voice-manifest] downloading model id=%s repo=%s revision=%s",
                model_id,
                repo_id,
                revision or "<default>",
            )
            snapshot_download(
                repo_id=repo_id,
                revision=revision,
                local_dir=str(target_path),
                local_dir_use_symlinks=False,
                token=token,
            )
            continue

        if source_type in {"external", "runtime"}:
            logger.info(
                "[voice-manifest] external model id=%s provider=%s (no artifact pull)",
                model_id,
                model.get("provider"),
            )
            continue

        logger.info(
            "[voice-manifest] skipping unsupported source type=%s id=%s",
            source_type or "<unset>",
            model_id,
        )


def _cmd_validate(_: argparse.Namespace) -> int:
    ok, errors = validate_manifest_for_runtime()
    if ok:
        print("[voice-manifest] validation ok")
        return 0

    print("[voice-manifest] validation failed", file=sys.stderr)
    for err in errors:
        print(f"  - {err}", file=sys.stderr)
    return 1


def _cmd_pull(args: argparse.Namespace) -> int:
    pull_manifest_models(models_dir=args.models_dir)
    ok, errors = validate_manifest_for_runtime()
    if ok:
        print("[voice-manifest] pull complete")
        return 0

    print(
        "[voice-manifest] pull finished with missing artifacts", file=sys.stderr
    )
    for err in errors:
        print(f"  - {err}", file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Voice model manifest utility")
    sub = parser.add_subparsers(dest="command", required=True)

    p_validate = sub.add_parser(
        "validate", help="Validate runtime manifest requirements"
    )
    p_validate.set_defaults(func=_cmd_validate)

    p_pull = sub.add_parser(
        "pull", help="Download local artifacts from manifest"
    )
    p_pull.add_argument("--models-dir", default=None)
    p_pull.set_defaults(func=_cmd_pull)

    args = parser.parse_args(argv)
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
