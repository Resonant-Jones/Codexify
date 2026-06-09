"""Headless local TTS routes."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from guardian.core.db import GuardianDB
from guardian.core.dependencies import RequestUserScope, get_request_user_scope
from guardian.tts.backends.qwen3 import Qwen3TTSBackend
from guardian.tts.config import get_local_tts_config
from guardian.tts.profiles import (
    TTSVoiceProfileError,
    create_tts_voice_profile,
    delete_tts_voice_profile,
    get_tts_backend_control_schemas,
    get_tts_voice_profile,
    list_tts_voice_profiles,
    profile_to_render_kwargs,
    serialize_tts_voice_profile,
    set_default_tts_voice_profile,
    update_tts_voice_profile,
)
from guardian.tts.renderer import render_voiceover

router = APIRouter(prefix="/api/tts", tags=["tts"])
_db: GuardianDB | None = None


def configure_db(db: GuardianDB) -> None:
    """Configure database instance for TTS profile routes."""

    global _db
    _db = db


def _get_db() -> GuardianDB:
    if _db is None:
        raise RuntimeError("Database not configured for TTS profile router")
    return _db


class TTSRenderRequestBody(BaseModel):
    text: str = Field(min_length=1, max_length=20000)
    output: str | None = None
    backend: str | None = None
    voice: str | None = None
    format: Literal["wav", "mp3"] = "wav"
    dry_run: bool = False


class TTSVoiceProfileCreateBody(BaseModel):
    id: str | None = Field(default=None, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    backend_id: str = "qwen3_tts"
    is_default: bool = False
    description: str | None = None
    voice_mode: str = "preset"
    speaker: str | None = "default"
    voice_prompt: str | None = None
    style_instructions: str | None = None
    language: str | None = None
    speed: float | None = Field(default=1.0, gt=0, le=4.0)
    temperature: float | None = Field(default=None, ge=0, le=2.0)
    top_k: int | None = Field(default=None, ge=0)
    top_p: float | None = Field(default=None, ge=0, le=1.0)
    repetition_penalty: float | None = Field(default=None, gt=0)
    max_new_tokens: int | None = Field(default=None, gt=0)
    do_sample: bool | None = None
    backend_params: dict[str, Any] = Field(default_factory=dict)
    reference_audio_asset_id: str | None = None
    reference_text: str | None = None
    x_vector_only_mode: bool | None = None
    sample_rate: int | None = Field(default=None, gt=0)
    output_format: Literal["wav", "mp3"] | None = "wav"
    loudness_normalization: bool | None = None
    pause_profile: dict[str, Any] | None = None


class TTSVoiceProfilePatchBody(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    backend_id: str | None = None
    is_default: bool | None = None
    description: str | None = None
    voice_mode: str | None = None
    speaker: str | None = None
    voice_prompt: str | None = None
    style_instructions: str | None = None
    language: str | None = None
    speed: float | None = Field(default=None, gt=0, le=4.0)
    temperature: float | None = Field(default=None, ge=0, le=2.0)
    top_k: int | None = Field(default=None, ge=0)
    top_p: float | None = Field(default=None, ge=0, le=1.0)
    repetition_penalty: float | None = Field(default=None, gt=0)
    max_new_tokens: int | None = Field(default=None, gt=0)
    do_sample: bool | None = None
    backend_params: dict[str, Any] | None = None
    reference_audio_asset_id: str | None = None
    reference_text: str | None = None
    x_vector_only_mode: bool | None = None
    sample_rate: int | None = Field(default=None, gt=0)
    output_format: Literal["wav", "mp3"] | None = None
    loudness_normalization: bool | None = None
    pause_profile: dict[str, Any] | None = None


class TTSVoiceProfilePreviewBody(BaseModel):
    text: str = Field(min_length=1, max_length=1000)
    format: Literal["wav", "mp3"] | None = None
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


@router.get("/backends")
async def list_tts_backends(
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
):
    """Return local TTS backend controls without invoking synthesis."""

    _ = request_user_scope
    cfg = get_local_tts_config()
    backends = get_tts_backend_control_schemas(cfg.backend_id)
    qwen_health = Qwen3TTSBackend(cfg).health().to_dict()
    for backend in backends:
        if backend["backend_id"] == "qwen3_tts":
            backend["health"] = qwen_health
    return {
        "active_backend_id": cfg.backend_id,
        "local_only": cfg.local_only,
        "items": backends,
    }


@router.get("/profiles")
async def list_tts_profiles(
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
):
    """List persistent local TTS voice profiles."""

    _ = request_user_scope
    db = _get_db()
    with db.get_session() as session:
        rows = list_tts_voice_profiles(session)
        items = [serialize_tts_voice_profile(row) for row in rows]
    default_profile_id = next(
        (item["id"] for item in items if item.get("is_default")), None
    )
    return {"items": items, "default_profile_id": default_profile_id}


@router.post("/profiles", status_code=201)
async def create_tts_profile(
    body: TTSVoiceProfileCreateBody,
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
):
    """Create a persistent local TTS voice profile."""

    _ = request_user_scope
    db = _get_db()
    try:
        with db.get_session() as session:
            profile = create_tts_voice_profile(session, _body_dict(body))
            return serialize_tts_voice_profile(profile)
    except TTSVoiceProfileError as exc:
        _raise_profile_http_error(exc)


@router.get("/profiles/{profile_id}")
async def get_tts_profile(
    profile_id: str,
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
):
    """Fetch one persistent local TTS voice profile."""

    _ = request_user_scope
    db = _get_db()
    try:
        with db.get_session() as session:
            profile = get_tts_voice_profile(session, profile_id)
            return serialize_tts_voice_profile(profile)
    except TTSVoiceProfileError as exc:
        _raise_profile_http_error(exc)


@router.patch("/profiles/{profile_id}")
async def patch_tts_profile(
    profile_id: str,
    body: TTSVoiceProfilePatchBody,
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
):
    """Update a persistent local TTS voice profile."""

    _ = request_user_scope
    db = _get_db()
    try:
        with db.get_session() as session:
            profile = update_tts_voice_profile(
                session, profile_id, _body_dict(body, exclude_unset=True)
            )
            return serialize_tts_voice_profile(profile)
    except TTSVoiceProfileError as exc:
        _raise_profile_http_error(exc)


@router.delete("/profiles/{profile_id}")
async def delete_tts_profile(
    profile_id: str,
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
):
    """Delete a persistent local TTS voice profile."""

    _ = request_user_scope
    db = _get_db()
    try:
        with db.get_session() as session:
            delete_tts_voice_profile(session, profile_id)
        return {"ok": True}
    except TTSVoiceProfileError as exc:
        _raise_profile_http_error(exc)


@router.post("/profiles/{profile_id}/set-default")
async def set_tts_profile_default(
    profile_id: str,
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
):
    """Mark exactly one local TTS voice profile as default."""

    _ = request_user_scope
    db = _get_db()
    try:
        with db.get_session() as session:
            profile = set_default_tts_voice_profile(session, profile_id)
            return serialize_tts_voice_profile(profile)
    except TTSVoiceProfileError as exc:
        _raise_profile_http_error(exc)


@router.post("/profiles/{profile_id}/preview")
async def preview_tts_profile(
    profile_id: str,
    body: TTSVoiceProfilePreviewBody,
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
):
    """Preview a TTS voice profile through the existing local adapter."""

    _ = request_user_scope
    db = _get_db()
    try:
        with db.get_session() as session:
            profile = get_tts_voice_profile(session, profile_id)
            profile_payload = serialize_tts_voice_profile(profile)
            render_kwargs = profile_to_render_kwargs(profile)
    except TTSVoiceProfileError as exc:
        _raise_profile_http_error(exc)

    cfg = get_local_tts_config()
    fmt = body.format or profile_payload.get("output_format") or "wav"
    preview_name = f"{profile_id}-{uuid4().hex}.generated.{fmt}"
    output_path = cfg.output_dir / "previews" / preview_name
    result = render_voiceover(
        text=body.text,
        output_path=output_path,
        output_format=fmt,
        dry_run=body.dry_run,
        config=cfg,
        **render_kwargs,
    )
    if not result.render_succeeded and not body.dry_run:
        raise HTTPException(
            status_code=503,
            detail={
                "failure_reason": result.failure_reason,
                "setup_hint": result.setup_hint,
                "profile_id": profile_id,
                "plan": result.plan.to_dict(),
            },
        )

    output = result.output_path or output_path
    return {
        "profile": profile_payload,
        "preview": result.to_dict(),
        "artifact": {
            "output_path": str(output),
            "media_url": None if body.dry_run else f"/api/tts/previews/{output.name}",
            "format": fmt,
            "bytes_written": result.bytes_written,
        },
    }


@router.get("/previews/{filename}")
async def stream_tts_preview(
    filename: str,
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
):
    """Serve generated local preview audio from the configured TTS output dir."""

    _ = request_user_scope
    safe_name = Path(filename).name
    if safe_name != filename or not safe_name.endswith(
        (".generated.wav", ".generated.mp3")
    ):
        raise HTTPException(status_code=404, detail="TTS preview not found")

    preview_dir = (get_local_tts_config().output_dir / "previews").resolve()
    output_path = (preview_dir / safe_name).resolve()
    if preview_dir not in output_path.parents or not output_path.exists():
        raise HTTPException(status_code=404, detail="TTS preview not found")

    media_type = "audio/mpeg" if output_path.suffix == ".mp3" else "audio/wav"
    return FileResponse(output_path, media_type=media_type, filename=safe_name)


def _body_dict(body: BaseModel, *, exclude_unset: bool = False) -> dict[str, Any]:
    if hasattr(body, "model_dump"):
        return body.model_dump(exclude_unset=exclude_unset)
    return body.dict(exclude_unset=exclude_unset)


def _raise_profile_http_error(exc: TTSVoiceProfileError) -> None:
    status = 422
    if exc.code in {"tts_voice_profile_not_found", "tts_default_profile_missing"}:
        status = 404
    raise HTTPException(status_code=status, detail={"code": exc.code}) from exc
