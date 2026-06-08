"""Headless local TTS routes."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from guardian.core.dependencies import RequestUserScope, get_request_user_scope
from guardian.tts.config import get_local_tts_config
from guardian.tts.renderer import render_voiceover

router = APIRouter(prefix="/api/tts", tags=["tts"])


class TTSRenderRequestBody(BaseModel):
    text: str = Field(min_length=1, max_length=20000)
    output: str | None = None
    backend: str | None = None
    voice: str | None = None
    format: Literal["wav", "mp3"] = "wav"
    dry_run: bool = False


@router.post("/render")
async def render_tts_voiceover(
    request: TTSRenderRequestBody,
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
):
    """Render local voiceover audio without chat, memory, retrieval, or persona."""

    _ = request_user_scope
    cfg = get_local_tts_config()
    output = (
        Path(request.output).expanduser()
        if request.output
        else cfg.output_dir / "api-voiceover.generated.wav"
    )
    if output.suffix:
        fmt = request.format or output.suffix.lstrip(".").lower()
    else:
        fmt = request.format
        output = output.with_suffix(f".{fmt}")

    result = render_voiceover(
        text=request.text,
        output_path=output,
        backend_id=request.backend,
        output_format=fmt,
        voice_id=request.voice,
        dry_run=request.dry_run,
        config=cfg,
    )
    if not result.render_succeeded and not request.dry_run:
        raise HTTPException(
            status_code=503,
            detail={
                "failure_reason": result.failure_reason,
                "setup_hint": result.setup_hint,
                "plan": result.plan.to_dict(),
            },
        )
    return result.to_dict()
