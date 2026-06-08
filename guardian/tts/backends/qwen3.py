"""Qwen3-TTS backend island for Codexify's local TTS adapter."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from guardian.tts.backends.base import TTSBackend
from guardian.tts.config import LocalTTSConfig, get_local_tts_config
from guardian.tts.contracts import (
    TTS_BACKEND_QWEN3,
    TTSBackendInfo,
    TTSBackendStatus,
    TTSHealthProbe,
    TTSRenderRequest,
    TTSRenderResult,
)

_IMPORT_CANDIDATES = ("qwen3_tts", "qwen_tts", "mlx_audio.tts")
_SETUP_HINT = (
    "Install a local Qwen3-TTS runtime, set CODEXIFY_TTS_QWEN3_MODEL_PATH "
    "to the local model directory, and optionally set "
    "CODEXIFY_TTS_QWEN3_RENDER_SCRIPT to a local renderer script."
)


class Qwen3TTSBackend(TTSBackend):
    """Local-only Qwen3-TTS adapter.

    The adapter never downloads model weights. Rendering uses an operator-owned
    local script when configured, otherwise it attempts a small set of local
    Python module entrypoints.
    """

    def __init__(self, config: LocalTTSConfig | None = None):
        self.config = config or get_local_tts_config()

    def info(self) -> TTSBackendInfo:
        return TTSBackendInfo(
            backend_id=TTS_BACKEND_QWEN3,
            display_name="Qwen3-TTS",
            local_only=True,
            output_formats=("wav",),
            supports_voice_sample_path=True,
        )

    def health(self) -> TTSHealthProbe:
        python_ok = bool(self.config.qwen3_python)
        model_ok = self._model_path_available()
        script_ok = self._render_script_available()
        import_name = self._first_importable_module()
        importable = bool(import_name) or script_ok
        healthy = python_ok and model_ok and importable

        if healthy:
            return TTSHealthProbe(
                backend_id=TTS_BACKEND_QWEN3,
                status=TTSBackendStatus.HEALTHY,
                installed=True,
                model_files_available=True,
                importable=True,
                healthy=True,
                details={
                    "python": self.config.qwen3_python,
                    "model_path": str(self.config.qwen3_model_path),
                    "render_script": (
                        str(self.config.qwen3_render_script)
                        if self.config.qwen3_render_script
                        else None
                    ),
                    "import_module": import_name,
                },
            )

        if not model_ok:
            status = TTSBackendStatus.UNAVAILABLE
            reason = "qwen3_model_path_missing"
        elif not importable:
            status = TTSBackendStatus.UNAVAILABLE
            reason = "qwen3_runtime_not_importable"
        else:
            status = TTSBackendStatus.UNAVAILABLE
            reason = "qwen3_python_missing"

        return TTSHealthProbe(
            backend_id=TTS_BACKEND_QWEN3,
            status=status,
            installed=python_ok and importable,
            model_files_available=model_ok,
            importable=importable,
            healthy=False,
            failure_reason=reason,
            setup_hint=_SETUP_HINT,
            details={
                "python": self.config.qwen3_python,
                "model_path": (
                    str(self.config.qwen3_model_path)
                    if self.config.qwen3_model_path
                    else None
                ),
                "render_script": (
                    str(self.config.qwen3_render_script)
                    if self.config.qwen3_render_script
                    else None
                ),
                "import_candidates": list(_IMPORT_CANDIDATES),
            },
        )

    def render(self, request: TTSRenderRequest) -> TTSRenderResult:
        probe = self.health()
        if not probe.healthy:
            return TTSRenderResult(
                backend_id=TTS_BACKEND_QWEN3,
                status=TTSBackendStatus.RENDER_FAILED,
                output_path=None,
                output_format=request.output_format,
                voice_id=request.voice_id,
                render_succeeded=False,
                failure_reason=probe.failure_reason,
                setup_hint=probe.setup_hint,
                metadata={"health": probe.to_dict()},
            )

        request.output_path.parent.mkdir(parents=True, exist_ok=True)
        if request.dry_run:
            return TTSRenderResult(
                backend_id=TTS_BACKEND_QWEN3,
                status=TTSBackendStatus.HEALTHY,
                output_path=request.output_path,
                output_format=request.output_format,
                voice_id=request.voice_id,
                render_succeeded=False,
                metadata={"dry_run": True, "health": probe.to_dict()},
            )

        try:
            if self.config.qwen3_render_script:
                self._render_with_script(request)
            else:
                self._render_with_importable_module(request)
        except Exception as exc:
            return TTSRenderResult(
                backend_id=TTS_BACKEND_QWEN3,
                status=TTSBackendStatus.RENDER_FAILED,
                output_path=None,
                output_format=request.output_format,
                voice_id=request.voice_id,
                render_succeeded=False,
                failure_reason=f"qwen3_render_failed:{exc}",
                setup_hint=_SETUP_HINT,
                metadata={"health": probe.to_dict()},
            )

        size = request.output_path.stat().st_size if request.output_path.exists() else 0
        if size <= 0:
            return TTSRenderResult(
                backend_id=TTS_BACKEND_QWEN3,
                status=TTSBackendStatus.RENDER_FAILED,
                output_path=None,
                output_format=request.output_format,
                voice_id=request.voice_id,
                render_succeeded=False,
                failure_reason="qwen3_render_empty_output",
                setup_hint=_SETUP_HINT,
            )

        return TTSRenderResult(
            backend_id=TTS_BACKEND_QWEN3,
            status=TTSBackendStatus.RENDER_SUCCEEDED,
            output_path=request.output_path,
            output_format=request.output_format,
            voice_id=request.voice_id,
            render_succeeded=True,
            bytes_written=size,
            metadata={"health": probe.to_dict()},
        )

    def _model_path_available(self) -> bool:
        model_path = self.config.qwen3_model_path
        return bool(model_path and model_path.exists() and model_path.is_dir())

    def _render_script_available(self) -> bool:
        script = self.config.qwen3_render_script
        return bool(script and script.exists() and script.is_file())

    def _first_importable_module(self) -> str | None:
        for name in _IMPORT_CANDIDATES:
            try:
                if importlib.util.find_spec(name) is not None:
                    return name
            except ModuleNotFoundError:
                continue
        return None

    def _render_with_script(self, request: TTSRenderRequest) -> None:
        assert self.config.qwen3_render_script is not None
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as fp:
            fp.write(request.text)
            text_path = Path(fp.name)
        try:
            cmd = [
                self.config.qwen3_python,
                str(self.config.qwen3_render_script),
                "--input",
                str(text_path),
                "--output",
                str(request.output_path),
                "--model-path",
                str(self.config.qwen3_model_path),
                "--voice",
                request.voice_id,
            ]
            if request.voice_sample_path:
                cmd.extend(["--voice-sample", str(request.voice_sample_path)])
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                env=self._subprocess_env(),
            )
            if proc.returncode != 0:
                detail = (proc.stderr or proc.stdout or "").strip()
                raise RuntimeError(detail or f"renderer exited {proc.returncode}")
        finally:
            text_path.unlink(missing_ok=True)

    def _render_with_importable_module(self, request: TTSRenderRequest) -> None:
        code = _module_render_code()
        payload = {
            "text": request.text,
            "output_path": str(request.output_path),
            "model_path": str(self.config.qwen3_model_path),
            "voice": request.voice_id,
            "voice_sample_path": (
                str(request.voice_sample_path) if request.voice_sample_path else None
            ),
        }
        proc = subprocess.run(
            [self.config.qwen3_python, "-c", code],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            check=False,
            env=self._subprocess_env(),
        )
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or "").strip()
            raise RuntimeError(detail or f"qwen3 module exited {proc.returncode}")

    def _subprocess_env(self) -> dict[str, str]:
        env = os.environ.copy()
        env.setdefault("TOKENIZERS_PARALLELISM", "false")
        return env


def _module_render_code() -> str:
    return r'''
import importlib
import json
import sys

payload = json.loads(sys.stdin.read())
module = None
for name in ("qwen3_tts", "qwen_tts", "mlx_audio.tts"):
    try:
        module = importlib.import_module(name)
        break
    except Exception:
        module = None
if module is None:
    raise SystemExit("No supported Qwen3-TTS module is importable")

kwargs = {
    "text": payload["text"],
    "output_path": payload["output_path"],
    "model_path": payload["model_path"],
    "voice": payload.get("voice") or "default",
}
if payload.get("voice_sample_path"):
    kwargs["voice_sample_path"] = payload["voice_sample_path"]

for attr in ("synthesize_to_file", "render_to_file", "tts_to_file"):
    fn = getattr(module, attr, None)
    if callable(fn):
        fn(**kwargs)
        raise SystemExit(0)

cls = getattr(module, "Qwen3TTS", None) or getattr(module, "QwenTTS", None)
if cls is not None:
    engine = cls(model_path=payload["model_path"])
    for attr in ("synthesize_to_file", "render_to_file", "tts_to_file"):
        fn = getattr(engine, attr, None)
        if callable(fn):
            fn(
                text=payload["text"],
                output_path=payload["output_path"],
                voice=payload.get("voice") or "default",
            )
            raise SystemExit(0)

raise SystemExit(
    "Importable Qwen3-TTS module did not expose synthesize_to_file/render_to_file"
)
'''
