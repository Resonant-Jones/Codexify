"""Codexify Local TTS Service - Standalone FastAPI application."""

import base64
import logging
from typing import Optional

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
    return {
        "status": "healthy",
        "service": "Codexify Local TTS Service",
        "version": "0.1.0",
        "default_provider": DEFAULT_PROVIDER,
        "providers": list(TTS_PROVIDERS.keys()),
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

    try:
        backend = _resolve_backend(provider)
    except ValueError as exc:
        logger.error("Plugin invoke backend resolution failed: %s", exc)
        return _invoke_error(
            "invalid_provider",
            str(exc),
            retryable=False,
        )

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
