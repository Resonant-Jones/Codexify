"""Model override management routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator

from guardian.core.dependencies import chatlog_db, require_api_key

router = APIRouter(
    prefix="/api/llm",
    tags=["LLM Overrides"],
    dependencies=[Depends(require_api_key)],
)


class ModelOverrideUpsertRequest(BaseModel):
    display_label: str | None = None
    picker_label: str | None = None
    supports_chat: bool | None = None
    supports_vision: bool | None = None
    supports_text_input: bool | None = None
    model_kind: str | None = None
    notes: str | None = None

    @field_validator("display_label", "picker_label", "model_kind", "notes")
    @classmethod
    def _normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        clean = value.strip()
        return clean or None

    @field_validator("model_kind")
    @classmethod
    def _normalize_model_kind(cls, value: str | None) -> str | None:
        if value is None:
            return None
        clean = value.strip().lower()
        if clean in {"chat", "vision_chat", "utility"}:
            return clean
        raise ValueError("model_kind must be chat, vision_chat, or utility")


def _require_chatlog_db():
    if chatlog_db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model overrides are unavailable until the chat database is configured.",
        )
    return chatlog_db


@router.get("/model-overrides")
def list_model_overrides():
    db = _require_chatlog_db()
    return {"overrides": db.list_inference_model_overrides()}


@router.get("/model-overrides/{provider_id}/{model_id}")
def get_model_override(provider_id: str, model_id: str):
    db = _require_chatlog_db()
    override = db.get_inference_model_override(provider_id, model_id)
    if override is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model override not found",
        )
    return {"override": override}


@router.put("/model-overrides/{provider_id}/{model_id}")
def upsert_model_override(
    provider_id: str,
    model_id: str,
    payload: ModelOverrideUpsertRequest,
):
    db = _require_chatlog_db()
    data = payload.model_dump(exclude_unset=True)
    if not any(value is not None for value in data.values()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one model override field is required.",
        )
    override = db.upsert_inference_model_override(provider_id, model_id, data)
    return {"ok": True, "override": override}


@router.delete("/model-overrides/{provider_id}/{model_id}")
def delete_model_override(provider_id: str, model_id: str):
    db = _require_chatlog_db()
    deleted = db.delete_inference_model_override(provider_id, model_id)
    return {"ok": deleted, "deleted": deleted}
