"""Channels config, allowlist, pairing, and message-audit routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field

from guardian.core.dependencies import require_api_key
from guardian.db import models as db_models

router = APIRouter(
    prefix="/api/channels",
    tags=["Channels"],
    dependencies=[Depends(require_api_key)],
)

_db: Any | None = None
_PAIRING_STATES = {"pending", "approved", "revoked"}


class ChannelConfigUpsertRequest(BaseModel):
    channel: str = Field(min_length=1, max_length=64)
    config_json: dict[str, Any] = Field(default_factory=dict)


class AllowlistEntryRequest(BaseModel):
    external_id: str = Field(min_length=1, max_length=255)
    label: str | None = Field(default=None, max_length=255)


class PairingEntryRequest(BaseModel):
    external_id: str = Field(min_length=1, max_length=255)
    status: str = Field(default="pending", min_length=1, max_length=16)


class PairingUpdateRequest(BaseModel):
    status: str = Field(min_length=1, max_length=16)


def configure_db(db: Any) -> None:
    global _db
    _db = db


def _get_db() -> Any:
    if _db is None:
        raise RuntimeError("Database not configured for channels router")
    return _db


def _current_user(
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> str:
    return (x_user_id or "default").strip() or "default"


def _normalize_channel(value: str) -> str:
    channel = (value or "").strip().lower()
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="channel is required",
        )
    return channel


def _validate_pairing_status(value: str) -> str:
    status_value = (value or "").strip().lower()
    if status_value not in _PAIRING_STATES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="status must be one of: pending, approved, revoked",
        )
    return status_value


def _serialize_config(row: db_models.ChannelConfig) -> dict[str, Any]:
    return {
        "id": row.id,
        "user_id": row.user_id,
        "channel": row.channel,
        "config_json": row.config_json or {},
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def _serialize_allowlist(row: db_models.ChannelAllowlist) -> dict[str, Any]:
    return {
        "id": row.id,
        "user_id": row.user_id,
        "channel": row.channel,
        "external_id": row.external_id,
        "label": row.label,
        "created_at": row.created_at,
    }


def _serialize_pairing(row: db_models.ChannelPairing) -> dict[str, Any]:
    return {
        "id": row.id,
        "user_id": row.user_id,
        "channel": row.channel,
        "external_id": row.external_id,
        "status": row.status,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def _serialize_message(row: db_models.ChannelMessage) -> dict[str, Any]:
    return {
        "id": row.id,
        "user_id": row.user_id,
        "channel": row.channel,
        "direction": row.direction,
        "external_id": row.external_id,
        "thread_id": row.thread_id,
        "content": row.content,
        "meta_json": row.meta_json,
        "created_at": row.created_at,
    }


@router.get("/configs")
async def list_configs(
    user_id: str = Depends(_current_user),
) -> dict[str, Any]:
    db = _get_db()
    with db.get_session() as session:
        rows = (
            session.query(db_models.ChannelConfig)
            .filter_by(user_id=user_id)
            .order_by(db_models.ChannelConfig.channel.asc())
            .all()
        )
        return {"items": [_serialize_config(row) for row in rows]}


@router.post("/configs", status_code=status.HTTP_201_CREATED)
async def upsert_config(
    body: ChannelConfigUpsertRequest,
    user_id: str = Depends(_current_user),
) -> dict[str, Any]:
    channel = _normalize_channel(body.channel)
    db = _get_db()
    with db.get_session() as session:
        row = (
            session.query(db_models.ChannelConfig)
            .filter_by(user_id=user_id, channel=channel)
            .first()
        )
        if row is None:
            row = db_models.ChannelConfig(
                user_id=user_id,
                channel=channel,
                config_json=body.config_json or {},
            )
            session.add(row)
        else:
            row.config_json = body.config_json or {}
        session.commit()
        session.refresh(row)
        return _serialize_config(row)


@router.delete("/configs/{channel}")
async def delete_config(
    channel: str,
    user_id: str = Depends(_current_user),
) -> dict[str, Any]:
    db = _get_db()
    with db.get_session() as session:
        row = (
            session.query(db_models.ChannelConfig)
            .filter_by(user_id=user_id, channel=_normalize_channel(channel))
            .first()
        )
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="config not found",
            )
        session.delete(row)
        session.commit()
        return {"ok": True, "channel": row.channel}


@router.get("/allowlist/{channel}")
async def list_allowlist(
    channel: str,
    user_id: str = Depends(_current_user),
) -> dict[str, Any]:
    db = _get_db()
    with db.get_session() as session:
        rows = (
            session.query(db_models.ChannelAllowlist)
            .filter_by(user_id=user_id, channel=_normalize_channel(channel))
            .order_by(db_models.ChannelAllowlist.created_at.desc())
            .all()
        )
        return {"items": [_serialize_allowlist(row) for row in rows]}


@router.post("/allowlist/{channel}", status_code=status.HTTP_201_CREATED)
async def add_allowlist_entry(
    channel: str,
    body: AllowlistEntryRequest,
    user_id: str = Depends(_current_user),
) -> dict[str, Any]:
    normalized_channel = _normalize_channel(channel)
    external_id = body.external_id.strip()
    db = _get_db()
    with db.get_session() as session:
        row = (
            session.query(db_models.ChannelAllowlist)
            .filter_by(
                user_id=user_id,
                channel=normalized_channel,
                external_id=external_id,
            )
            .first()
        )
        if row is None:
            row = db_models.ChannelAllowlist(
                user_id=user_id,
                channel=normalized_channel,
                external_id=external_id,
                label=body.label,
            )
            session.add(row)
        else:
            row.label = body.label
        session.commit()
        session.refresh(row)
        return _serialize_allowlist(row)


@router.delete("/allowlist/{channel}/{external_id}")
async def delete_allowlist_entry(
    channel: str,
    external_id: str,
    user_id: str = Depends(_current_user),
) -> dict[str, Any]:
    db = _get_db()
    with db.get_session() as session:
        row = (
            session.query(db_models.ChannelAllowlist)
            .filter_by(
                user_id=user_id,
                channel=_normalize_channel(channel),
                external_id=external_id,
            )
            .first()
        )
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="allowlist entry not found",
            )
        session.delete(row)
        session.commit()
        return {"ok": True, "external_id": external_id}


@router.get("/pairings/{channel}")
async def list_pairings(
    channel: str,
    user_id: str = Depends(_current_user),
) -> dict[str, Any]:
    db = _get_db()
    with db.get_session() as session:
        rows = (
            session.query(db_models.ChannelPairing)
            .filter_by(user_id=user_id, channel=_normalize_channel(channel))
            .order_by(db_models.ChannelPairing.updated_at.desc())
            .all()
        )
        return {"items": [_serialize_pairing(row) for row in rows]}


@router.post("/pairings/{channel}", status_code=status.HTTP_201_CREATED)
async def create_pairing(
    channel: str,
    body: PairingEntryRequest,
    user_id: str = Depends(_current_user),
) -> dict[str, Any]:
    normalized_channel = _normalize_channel(channel)
    external_id = body.external_id.strip()
    status_value = _validate_pairing_status(body.status)

    db = _get_db()
    with db.get_session() as session:
        row = (
            session.query(db_models.ChannelPairing)
            .filter_by(
                user_id=user_id,
                channel=normalized_channel,
                external_id=external_id,
            )
            .first()
        )
        if row is None:
            row = db_models.ChannelPairing(
                user_id=user_id,
                channel=normalized_channel,
                external_id=external_id,
                status=status_value,
            )
            session.add(row)
        else:
            row.status = status_value
        session.commit()
        session.refresh(row)
        return _serialize_pairing(row)


@router.patch("/pairings/{channel}/{external_id}")
async def update_pairing(
    channel: str,
    external_id: str,
    body: PairingUpdateRequest,
    user_id: str = Depends(_current_user),
) -> dict[str, Any]:
    db = _get_db()
    with db.get_session() as session:
        row = (
            session.query(db_models.ChannelPairing)
            .filter_by(
                user_id=user_id,
                channel=_normalize_channel(channel),
                external_id=external_id,
            )
            .first()
        )
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="pairing not found",
            )
        row.status = _validate_pairing_status(body.status)
        session.commit()
        session.refresh(row)
        return _serialize_pairing(row)


@router.get("/messages/{channel}")
async def list_messages(
    channel: str,
    limit: int = Query(default=50, ge=1, le=200),
    user_id: str = Depends(_current_user),
) -> dict[str, Any]:
    db = _get_db()
    with db.get_session() as session:
        rows = (
            session.query(db_models.ChannelMessage)
            .filter_by(user_id=user_id, channel=_normalize_channel(channel))
            .order_by(db_models.ChannelMessage.created_at.desc())
            .limit(limit)
            .all()
        )
        return {
            "items": [_serialize_message(row) for row in rows],
            "count": len(rows),
        }
