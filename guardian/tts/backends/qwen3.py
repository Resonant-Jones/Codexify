"""Qwen3-TTS backend island for Codexify's local TTS adapter."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
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
        python_ok = self._python_available()
        model_ok = self._model_path_available()
        script_ok = self._render_script_available()
        import_name = self._first_importable_module() if python_ok else None
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

        if not python_ok:
            status = TTSBackendStatus.UNAVAILABLE
            reason = "qwen3_python_missing"
        elif not model_ok:
            status = TTSBackendStatus.UNAVAILABLE
            reason = "qwen3_model_path_missing"
        elif not importable:
            status = TTSBackendStatus.UNAVAILABLE
            reason = "qwen3_runtime_not_importable"

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

    def render_many(self, requests: list[TTSRenderRequest]) -> list[TTSRenderResult]:
        if not requests:
            return []

        probe = self.health()
        if not probe.healthy:
            return [
                TTSRenderResult(
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
                for request in requests
            ]

        if any(request.dry_run for request in requests):
            return [
                TTSRenderResult(
                    backend_id=TTS_BACKEND_QWEN3,
                    status=TTSBackendStatus.HEALTHY,
                    output_path=request.output_path,
                    output_format=request.output_format,
                    voice_id=request.voice_id,
                    render_succeeded=False,
                    metadata={"dry_run": True, "health": probe.to_dict()},
                )
                for request in requests
            ]

        for request in requests:
            request.output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            if self.config.qwen3_render_script:
                for request in requests:
                    self._render_with_script(request)
            else:
                self._render_many_with_importable_module(requests)
        except Exception as exc:
            return [
                TTSRenderResult(
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
                for request in requests
            ]

        results: list[TTSRenderResult] = []
        for request in requests:
            size = request.output_path.stat().st_size if request.output_path.exists() else 0
            if size <= 0:
                results.append(
                    TTSRenderResult(
                        backend_id=TTS_BACKEND_QWEN3,
                        status=TTSBackendStatus.RENDER_FAILED,
                        output_path=None,
                        output_format=request.output_format,
                        voice_id=request.voice_id,
                        render_succeeded=False,
                        failure_reason="qwen3_render_empty_output",
                        setup_hint=_SETUP_HINT,
                    )
                )
                continue
            results.append(
                TTSRenderResult(
                    backend_id=TTS_BACKEND_QWEN3,
                    status=TTSBackendStatus.RENDER_SUCCEEDED,
                    output_path=request.output_path,
                    output_format=request.output_format,
                    voice_id=request.voice_id,
                    render_succeeded=True,
                    bytes_written=size,
                    metadata={"health": probe.to_dict()},
                )
            )
        return results

    def _model_path_available(self) -> bool:
        model_path = self.config.qwen3_model_path
        return bool(model_path and model_path.exists() and model_path.is_dir())

    def _render_script_available(self) -> bool:
        script = self.config.qwen3_render_script
        return bool(script and script.exists() and script.is_file())

    def _python_available(self) -> bool:
        python = (self.config.qwen3_python or "").strip()
        if not python:
            return False
        if os.sep in python:
            return Path(python).expanduser().exists()
        return shutil.which(python) is not None

    def _first_importable_module(self) -> str | None:
        if self.config.qwen3_python == sys.executable:
            for name in _IMPORT_CANDIDATES:
                try:
                    if importlib.util.find_spec(name) is not None:
                        return name
                except ModuleNotFoundError:
                    continue
        probe_code = """
import importlib.util
for name in ("qwen3_tts", "qwen_tts", "mlx_audio.tts"):
    try:
        if importlib.util.find_spec(name) is not None:
            print(name)
            raise SystemExit(0)
    except ModuleNotFoundError:
        pass
raise SystemExit(1)
"""
        try:
            proc = subprocess.run(
                [self.config.qwen3_python, "-c", probe_code],
                capture_output=True,
                text=True,
                check=False,
                env=self._subprocess_env(),
            )
        except OSError:
            return None
        if proc.returncode == 0:
            return proc.stdout.strip().splitlines()[-1]
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
        self._render_many_with_importable_module([request])

    def _render_many_with_importable_module(self, requests: list[TTSRenderRequest]) -> None:
        code = _module_render_code()
        payload = {
            "model_path": str(self.config.qwen3_model_path),
            "requests": [
                {
                    "text": request.text,
                    "output_path": str(request.output_path),
                    "voice": request.voice_id,
                    "voice_sample_path": (
                        str(request.voice_sample_path)
                        if request.voice_sample_path
                        else None
                    ),
                }
                for request in requests
            ],
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
        numba_cache = env.get("NUMBA_CACHE_DIR") or str(
            Path(tempfile.gettempdir()) / "codexify-numba-cache"
        )
        Path(numba_cache).mkdir(parents=True, exist_ok=True)
        env.setdefault("NUMBA_CACHE_DIR", numba_cache)
        env.setdefault("CODEXIFY_TTS_QWEN3_DEVICE", "cpu")
        env.setdefault("CODEXIFY_TTS_QWEN3_DTYPE", "float32")
        env.setdefault("CODEXIFY_TTS_QWEN3_LANGUAGE", "english")
        env.setdefault("CODEXIFY_TTS_QWEN3_DEFAULT_SPEAKER", "ryan")
        env.setdefault("CODEXIFY_TTS_QWEN3_BATCH_SIZE", "4")
        env.setdefault("CODEXIFY_TTS_QWEN3_MAX_NEW_TOKENS", "512")
        env.setdefault("CODEXIFY_TTS_QWEN3_DISABLE_MLX_PROBE", "true")
        return env


def _module_render_code() -> str:
    return r'''
import importlib
import json
import os
import sys

payload = json.loads(sys.stdin.read())
requests = payload.get("requests") or [payload]


def _disable_transformers_mlx_probe():
    if os.getenv("CODEXIFY_TTS_QWEN3_DISABLE_MLX_PROBE", "true").lower() not in {
        "1",
        "true",
        "yes",
        "on",
    }:
        return
    try:
        import transformers.utils.generic as transformers_generic
    except Exception:
        return
    transformers_generic.is_mlx_available = lambda: False
    transformers_generic.is_mlx_array = lambda _value: False


def _torch_dtype():
    try:
        import torch
    except Exception:
        return None
    raw = os.getenv("CODEXIFY_TTS_QWEN3_DTYPE", "float32").strip().lower()
    if raw in {"bf16", "bfloat16"}:
        return torch.bfloat16
    if raw in {"fp16", "float16", "half"}:
        return torch.float16
    if raw in {"fp32", "float32"}:
        return torch.float32
    return torch.float32


def _render_with_official_qwen_tts(module):
    model_cls = getattr(module, "Qwen3TTSModel", None)
    if model_cls is None:
        return False

    import soundfile as sf

    load_kwargs = {}
    device = os.getenv("CODEXIFY_TTS_QWEN3_DEVICE", "cpu").strip()
    if device and device.lower() not in {"none", "unset"}:
        load_kwargs["device_map"] = device
    dtype = _torch_dtype()
    if dtype is not None:
        load_kwargs["dtype"] = dtype

    model = model_cls.from_pretrained(payload["model_path"], **load_kwargs)
    language = os.getenv("CODEXIFY_TTS_QWEN3_LANGUAGE", "english").strip() or "english"
    default_speaker = (
        os.getenv("CODEXIFY_TTS_QWEN3_DEFAULT_SPEAKER", "ryan").strip() or "ryan"
    )
    speakers = []
    for request in requests:
        requested_voice = (request.get("voice") or "default").strip()
        speakers.append(default_speaker if requested_voice == "default" else requested_voice)
    supported_speakers = model.get_supported_speakers()
    if supported_speakers:
        normalized = {str(item).lower(): str(item) for item in supported_speakers}
        resolved_speakers = []
        for speaker in speakers:
            lookup = speaker.lower()
            if lookup not in normalized:
                raise SystemExit(
                    "Unsupported Qwen3-TTS voice "
                    f"{speaker!r}. Supported speakers: {sorted(normalized)}"
                )
            resolved_speakers.append(normalized[lookup])
        speakers = resolved_speakers

    gen_kwargs = {}
    max_new_tokens = os.getenv("CODEXIFY_TTS_QWEN3_MAX_NEW_TOKENS")
    if max_new_tokens:
        gen_kwargs["max_new_tokens"] = int(max_new_tokens)

    if hasattr(model, "generate_custom_voice"):
        batch_size = max(int(os.getenv("CODEXIFY_TTS_QWEN3_BATCH_SIZE", "4")), 1)
        for start in range(0, len(requests), batch_size):
            batch = requests[start : start + batch_size]
            wavs, sample_rate = model.generate_custom_voice(
                text=[request["text"] for request in batch],
                language=[language] * len(batch),
                speaker=speakers[start : start + batch_size],
                **gen_kwargs,
            )
            for request, wav in zip(batch, wavs):
                sf.write(request["output_path"], wav, sample_rate)
        return True
    return False


_disable_transformers_mlx_probe()
module = None
for name in ("qwen3_tts", "qwen_tts", "mlx_audio.tts"):
    try:
        module = importlib.import_module(name)
        break
    except Exception:
        module = None
if module is None:
    raise SystemExit("No supported Qwen3-TTS module is importable")

if _render_with_official_qwen_tts(module):
    raise SystemExit(0)

kwargs = {
    "text": requests[0]["text"],
    "output_path": requests[0]["output_path"],
    "model_path": payload["model_path"],
    "voice": requests[0].get("voice") or "default",
}
if requests[0].get("voice_sample_path"):
    kwargs["voice_sample_path"] = requests[0]["voice_sample_path"]

for attr in ("synthesize_to_file", "render_to_file", "tts_to_file"):
    fn = getattr(module, attr, None)
    if callable(fn):
        fn(**kwargs)
        raise SystemExit(0)

cls = getattr(module, "Qwen3TTS", None) or getattr(module, "QwenTTS", None)
if cls is not None:
    engine = cls(model_path=payload["model_path"])
    for request in requests:
        for attr in ("synthesize_to_file", "render_to_file", "tts_to_file"):
            fn = getattr(engine, attr, None)
            if callable(fn):
                fn(
                    text=request["text"],
                    output_path=request["output_path"],
                    voice=request.get("voice") or "default",
                )
                break
        else:
            break
    else:
        raise SystemExit(0)

raise SystemExit(
    "Importable Qwen3-TTS module did not expose synthesize_to_file/render_to_file"
)
'''
