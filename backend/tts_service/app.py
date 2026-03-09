"""Codexify Local TTS Service - Standalone FastAPI application."""

import base64
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from .backends.base import TTSBackend
from .backends.huggingface_tts import HuggingFaceTTSBackend
from .config import DEFAULT_PROVIDER, TTS_PROVIDERS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

STARTUP_PHASE_PROCESS_STARTED = "process_started"
STARTUP_PHASE_MODEL_LOADING = "model_loading"
STARTUP_PHASE_MODEL_READY = "model_ready"
STARTUP_PHASE_STARTUP_FAILED = "startup_failed"

# Initialize FastAPI app
app = FastAPI(
    title="Codexify Local TTS Service",
    version="0.1.0",
    description="Local text-to-speech microservice for Codexify",
)


class TTSRequest(BaseModel):
    """Request model for TTS synthesis."""

    text: str
    provider: str
    voice: Optional[str] = None
    speed: Optional[float] = None
    ref_audio: Optional[str] = None
    ref_text: Optional[str] = None


class PluginInvokeError(BaseModel):
    code: str
    message: str
    retryable: bool = False


class PluginInvokeResponse(BaseModel):
    ok: bool
    output: dict | None = None
    error: PluginInvokeError | None = None


class PluginInvokeContext(BaseModel):
    request_id: str | None = None
    thread_id: str | None = None
    user_id: str | None = None


class PluginInvokeRequest(BaseModel):
    protocol_version: str
    plugin_id: str
    capability: str
    action: str
    input: dict = Field(default_factory=dict)
    context: PluginInvokeContext | None = None


@dataclass
class ProviderRuntimeState:
    phase: str = STARTUP_PHASE_PROCESS_STARTED
    ready: bool = False
    error: str | None = None
    last_transition_time: float = field(default_factory=time.time)


@dataclass
class TTSRuntimeState:
    startup_phase: str = STARTUP_PHASE_PROCESS_STARTED
    ready: bool = False
    startup_error: str | None = None
    started_at: float = field(default_factory=time.time)
    provider_states: dict[str, ProviderRuntimeState] = field(
        default_factory=dict
    )


_RUNTIME_LOCK = threading.Lock()
_BACKEND_CACHE: dict[str, TTSBackend] = {}
_LOAD_THREADS: dict[str, threading.Thread] = {}
_RUNTIME_STATE = TTSRuntimeState(
    provider_states={
        provider: ProviderRuntimeState() for provider in TTS_PROVIDERS
    }
)


def _health_status_for_phase(phase: str) -> str:
    if phase == STARTUP_PHASE_MODEL_READY:
        return "healthy"
    if phase == STARTUP_PHASE_STARTUP_FAILED:
        return "degraded"
    return "loading"


def _startup_preload_enabled() -> bool:
    raw = (os.getenv("CODEXIFY_TTS_PRELOAD_ON_STARTUP") or "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _ensure_provider_state(provider: str) -> ProviderRuntimeState:
    return _RUNTIME_STATE.provider_states.setdefault(
        provider, ProviderRuntimeState()
    )


def _set_provider_phase(
    provider: str,
    phase: str,
    *,
    ready: bool,
    error: str | None = None,
) -> None:
    with _RUNTIME_LOCK:
        state = _ensure_provider_state(provider)
        state.phase = phase
        state.ready = ready
        state.error = error
        state.last_transition_time = time.time()
        if provider == DEFAULT_PROVIDER:
            _RUNTIME_STATE.startup_phase = phase
            _RUNTIME_STATE.ready = ready
            _RUNTIME_STATE.startup_error = error


def _provider_snapshot(provider: str) -> dict[str, Any]:
    with _RUNTIME_LOCK:
        state = _ensure_provider_state(provider)
        return {
            "phase": state.phase,
            "ready": state.ready,
            "error": state.error,
            "last_transition_time": state.last_transition_time,
        }


def _runtime_snapshot() -> dict[str, Any]:
    with _RUNTIME_LOCK:
        provider_states = {
            provider: {
                "phase": state.phase,
                "ready": state.ready,
                "error": state.error,
                "last_transition_time": state.last_transition_time,
            }
            for provider, state in _RUNTIME_STATE.provider_states.items()
        }
        return {
            "status": _health_status_for_phase(_RUNTIME_STATE.startup_phase),
            "ready": _RUNTIME_STATE.ready,
            "startup_phase": _RUNTIME_STATE.startup_phase,
            "startup_error": _RUNTIME_STATE.startup_error,
            "started_at": _RUNTIME_STATE.started_at,
            "provider_states": provider_states,
        }


def _get_ready_backend(provider: str) -> TTSBackend | None:
    with _RUNTIME_LOCK:
        state = _ensure_provider_state(provider)
        if not state.ready:
            return None
        return _BACKEND_CACHE.get(provider)


def _warm_backend(provider: str, backend: TTSBackend) -> None:
    logger.info("TTS model load begin: provider=%s", provider)
    pipeline = getattr(backend, "pipeline", None)
    if pipeline is not None:
        _ = pipeline
    logger.info("TTS model load end: provider=%s", provider)


def _load_provider_backend(provider: str, *, trigger: str) -> None:
    try:
        backend = _resolve_backend(provider)
        _warm_backend(provider, backend)
    except Exception as exc:
        logger.exception(
            "TTS startup failed: provider=%s trigger=%s error=%s",
            provider,
            trigger,
            exc,
        )
        _set_provider_phase(
            provider,
            STARTUP_PHASE_STARTUP_FAILED,
            ready=False,
            error=str(exc),
        )
        with _RUNTIME_LOCK:
            _LOAD_THREADS.pop(provider, None)
        return

    with _RUNTIME_LOCK:
        _BACKEND_CACHE[provider] = backend
        _LOAD_THREADS.pop(provider, None)
    _set_provider_phase(provider, STARTUP_PHASE_MODEL_READY, ready=True)
    logger.info("TTS model ready: provider=%s trigger=%s", provider, trigger)


def _start_provider_load(provider: str, *, trigger: str) -> None:
    with _RUNTIME_LOCK:
        state = _ensure_provider_state(provider)
        active = _LOAD_THREADS.get(provider)
        if state.ready or (active is not None and active.is_alive()):
            return
        state.phase = STARTUP_PHASE_MODEL_LOADING
        state.ready = False
        state.error = None
        state.last_transition_time = time.time()
        if provider == DEFAULT_PROVIDER:
            _RUNTIME_STATE.startup_phase = STARTUP_PHASE_MODEL_LOADING
            _RUNTIME_STATE.ready = False
            _RUNTIME_STATE.startup_error = None
        thread = threading.Thread(
            target=_load_provider_backend,
            kwargs={"provider": provider, "trigger": trigger},
            daemon=True,
            name=f"tts-load-{provider}",
        )
        _LOAD_THREADS[provider] = thread

    logger.info(
        "TTS startup phase=%s provider=%s trigger=%s",
        STARTUP_PHASE_MODEL_LOADING,
        provider,
        trigger,
    )
    thread.start()


def _not_ready_invoke_response(provider: str) -> PluginInvokeResponse:
    state = _provider_snapshot(provider)
    phase = state["phase"]
    error = state["error"]
    logger.warning(
        "TTS invoke rejected because provider is not ready: provider=%s phase=%s error=%s",
        provider,
        phase,
        error,
    )
    if phase == STARTUP_PHASE_STARTUP_FAILED:
        return _invoke_error(
            "service_startup_failed",
            (
                f"TTS provider '{provider}' failed during startup"
                + (f": {error}" if error else "")
            ),
            retryable=False,
        )
    return _invoke_error(
        "service_not_ready",
        f"TTS provider '{provider}' is still {phase}",
        retryable=True,
    )


def _reset_runtime_state_for_tests() -> None:
    with _RUNTIME_LOCK:
        _BACKEND_CACHE.clear()
        _LOAD_THREADS.clear()
        _RUNTIME_STATE.startup_phase = STARTUP_PHASE_PROCESS_STARTED
        _RUNTIME_STATE.ready = False
        _RUNTIME_STATE.startup_error = None
        _RUNTIME_STATE.started_at = time.time()
        _RUNTIME_STATE.provider_states = {
            provider: ProviderRuntimeState() for provider in TTS_PROVIDERS
        }


def _resolve_backend(provider: str) -> TTSBackend:
    """
    Resolve a provider name to a backend instance.

    Args:
        provider: Provider identifier from TTS_PROVIDERS

    Returns:
        TTSBackend instance

    Raises:
        ValueError: If provider is unknown or backend type is unsupported
    """
    if provider not in TTS_PROVIDERS:
        available = ", ".join(TTS_PROVIDERS.keys())
        raise ValueError(
            f"Unknown provider '{provider}'. Available providers: {available}"
        )

    config = TTS_PROVIDERS[provider]
    backend_type = config["backend"]

    if backend_type == "huggingface":
        model_id = config["model_id"]
        if model_id.startswith("REPLACE_WITH_"):
            raise ValueError(
                f"Provider '{provider}' has a placeholder model ID. "
                "This provider is not yet configured."
            )
        mode = config.get("mode", "custom_voice")
        return HuggingFaceTTSBackend(model_id=model_id, mode=mode)
    else:
        raise ValueError(f"Unsupported backend type: {backend_type}")


def _invoke_error(
    code: str,
    message: str,
    *,
    retryable: bool = False,
) -> PluginInvokeResponse:
    return PluginInvokeResponse(
        ok=False,
        output=None,
        error=PluginInvokeError(
            code=code,
            message=message,
            retryable=retryable,
        ),
    )


@app.on_event("startup")
def preload_default_provider() -> None:
    logger.info(
        "TTS startup phase=%s default_provider=%s preload_on_startup=%s",
        STARTUP_PHASE_PROCESS_STARTED,
        DEFAULT_PROVIDER,
        _startup_preload_enabled(),
    )
    if not _startup_preload_enabled():
        return
    _start_provider_load(DEFAULT_PROVIDER, trigger="startup")


@app.get("/")
def root():
    """Health check endpoint."""
    return {
        "service": "Codexify Local TTS Service",
        "version": "0.1.0",
        "providers": list(TTS_PROVIDERS.keys()),
    }


@app.post("/tts")
def synthesize_speech(request: TTSRequest):
    """
    Synthesize speech from text.

    Args:
        request: TTS request with text, provider, and optional parameters

    Returns:
        WAV audio bytes with X-Sampling-Rate header
    """
    logger.info(
        f"TTS request: provider={request.provider}, text_len={len(request.text)}"
    )

    try:
        # Resolve backend
        backend = _resolve_backend(request.provider)
    except ValueError as e:
        logger.error(f"Backend resolution failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    try:
        # Synthesize audio
        wav_bytes, sampling_rate = backend.synthesize(
            text=request.text,
            voice=request.voice,
            speed=request.speed,
            ref_audio=request.ref_audio,
            ref_text=request.ref_text,
        )
    except Exception as e:
        logger.error(f"Synthesis failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Synthesis failed: {str(e)}"
        )

    # Return WAV audio with sampling rate header
    return Response(
        content=wav_bytes,
        media_type="audio/wav",
        headers={
            "X-Sampling-Rate": str(sampling_rate),
        },
    )


@app.get("/health")
def health_check():
    """Kubernetes-style health check."""
    runtime = _runtime_snapshot()
    return {
        "status": runtime["status"],
        "ready": runtime["ready"],
        "startup_phase": runtime["startup_phase"],
        "startup_error": runtime["startup_error"],
        "service": "Codexify Local TTS Service",
        "version": "0.1.0",
        "default_provider": DEFAULT_PROVIDER,
        "providers": list(TTS_PROVIDERS.keys()),
        "provider_states": runtime["provider_states"],
    }


@app.post("/invoke", response_model=PluginInvokeResponse)
def invoke_plugin(request: PluginInvokeRequest):
    """
    Canonical service-plugin invocation endpoint.
    """
    if request.protocol_version != "1.0":
        return _invoke_error(
            "unsupported_protocol_version",
            f"Unsupported protocol_version: {request.protocol_version}",
            retryable=False,
        )
    if request.capability != "tts" or request.action != "speak":
        return _invoke_error(
            "unsupported_operation",
            f"Unsupported operation: {request.capability}.{request.action}",
            retryable=False,
        )

    text = request.input.get("text")
    if not isinstance(text, str) or not text.strip():
        return _invoke_error(
            "invalid_input",
            "input.text must be a non-empty string",
            retryable=False,
        )

    provider = request.input.get("provider") or DEFAULT_PROVIDER
    voice = request.input.get("voice")
    speed = request.input.get("speed")
    ref_audio = request.input.get("ref_audio")
    ref_text = request.input.get("ref_text")

    logger.info(
        "Plugin invoke: capability=%s action=%s provider=%s text_len=%d request_id=%s",
        request.capability,
        request.action,
        provider,
        len(text),
        request.context.request_id if request.context else None,
    )

    if provider not in TTS_PROVIDERS:
        available = ", ".join(TTS_PROVIDERS.keys())
        message = (
            f"Unknown provider '{provider}'. Available providers: {available}"
        )
        logger.error("Plugin invoke backend resolution failed: %s", message)
        return _invoke_error(
            "invalid_provider",
            message,
            retryable=False,
        )

    backend = _get_ready_backend(provider)
    if backend is None:
        state = _provider_snapshot(provider)
        if state["phase"] != STARTUP_PHASE_STARTUP_FAILED:
            _start_provider_load(provider, trigger="invoke")
        return _not_ready_invoke_response(provider)

    try:
        wav_bytes, sampling_rate = backend.synthesize(
            text=text,
            voice=voice,
            speed=speed,
            ref_audio=ref_audio,
            ref_text=ref_text,
        )
    except Exception as exc:
        logger.error("Plugin invoke synthesis failed: %s", exc, exc_info=True)
        return _invoke_error(
            "synthesis_failed",
            f"Synthesis failed: {exc}",
            retryable=False,
        )

    output = {
        "provider": provider,
        "format": "wav",
        "mime_type": "audio/wav",
        "sampling_rate": sampling_rate,
        "audio_base64": base64.b64encode(wav_bytes).decode("ascii"),
    }
    return PluginInvokeResponse(ok=True, output=output, error=None)
