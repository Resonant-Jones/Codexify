"""Standalone voice-service HTTP API.

This service is orchestration-agnostic: only STT/TTS execution surfaces.
"""

from __future__ import annotations

import base64
import logging
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from guardian.voice.service import (
    VoiceProviderError,
    VoiceTimeoutError,
    VoiceValidationError,
    enforce_audio_input_limits,
    list_voice_models,
    synthesize_text,
    transcribe_audio,
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Codexify Voice Service",
    version="1.0.0",
    description="Model-agnostic STT/TTS provider service.",
)


class SynthesizeRequest(BaseModel):
    text: str
    provider: str | None = None
    voice: str | None = None
    output_format: str | None = None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/models")
def models() -> dict:
    return list_voice_models()


@app.post("/transcribe")
async def transcribe(
    audio_file: UploadFile = File(...),
    provider: str | None = Form(None),
) -> dict:
    try:
        audio_bytes = await audio_file.read()
        enforce_audio_input_limits(audio_bytes, audio_file.content_type)
        text = transcribe_audio(
            audio_bytes,
            audio_file.content_type,
            provider=provider,
        )
        return {"text": text, "provider": provider}
    except VoiceValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except VoiceTimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc))
    except VoiceProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@app.post("/synthesize")
def synthesize(request: SynthesizeRequest) -> dict:
    try:
        audio_bytes, fmt = synthesize_text(
            request.text,
            provider=request.provider,
            voice=request.voice,
            output_format=request.output_format,
        )
        return {
            "audio_b64": base64.b64encode(audio_bytes).decode("ascii"),
            "format": fmt,
            "provider": request.provider,
            "voice": request.voice,
        }
    except VoiceValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except VoiceTimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc))
    except VoiceProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
