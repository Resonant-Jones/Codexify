"""Helpers for message-linked audio asset persistence."""

from __future__ import annotations

import hashlib
import os
from datetime import datetime
from typing import Any

from sqlalchemy.exc import IntegrityError

from guardian.core.db import GuardianDB, load_guardian_db_from_env
from guardian.core.dependencies import chatlog_db
from guardian.core.storage import create_storage_from_env
from guardian.db.models import MessageAudioAsset

_storage = create_storage_from_env()


def _database_url() -> str:
    return os.getenv(
        "DATABASE_URL", "postgresql://guardian:guardian@db:5432/guardian"
    )


def _db() -> GuardianDB:
    shared = chatlog_db or load_guardian_db_from_env()
    if shared is not None:
        return shared
    return GuardianDB(_database_url())


def compute_text_hash(text: str) -> str:
    normalized = (text or "").strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _content_type_for_format(fmt: str) -> str:
    key = (fmt or "wav").strip().lower()
    if key in {"mp3", "mpeg"}:
        return "audio/mpeg"
    if key in {"opus", "ogg"}:
        return "audio/ogg"
    return "audio/wav"


def _extension_for_format(fmt: str) -> str:
    key = (fmt or "wav").strip().lower()
    if key == "mpeg":
        return "mp3"
    return key


def find_cached_asset(
    *,
    message_id: int,
    provider: str,
    voice: str,
    text_hash: str,
) -> dict[str, Any] | None:
    db = _db()
    with db.get_session() as session:
        row = (
            session.query(MessageAudioAsset)
            .filter_by(
                message_id=message_id,
                provider=provider,
                voice=voice,
                text_hash=text_hash,
            )
            .first()
        )
        if not row:
            return None
        return _serialize_asset(row)


def save_message_audio_asset(
    *,
    message_id: int,
    text: str,
    provider: str,
    voice: str,
    audio_bytes: bytes,
    audio_format: str,
    delivery_variants_json: dict[str, Any] | None = None,
) -> dict[str, Any]:
    text_hash = compute_text_hash(text)
    ext = _extension_for_format(audio_format)
    filename = (
        f"audio/messages/{message_id}_{text_hash[:12]}_{provider}_{voice}.{ext}"
    )
    src_url = _storage.upload_file(
        audio_bytes,
        filename,
        content_type=_content_type_for_format(audio_format),
    )

    db = _db()
    with db.get_session() as session:
        row = MessageAudioAsset(
            message_id=message_id,
            provider=provider,
            voice=voice,
            text_hash=text_hash,
            src_url=src_url,
            internal_format=audio_format,
            delivery_variants_json=delivery_variants_json or {},
            duration_seconds=None,
            filesize_bytes=len(audio_bytes),
        )
        session.add(row)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            existing = (
                session.query(MessageAudioAsset)
                .filter_by(
                    message_id=message_id,
                    provider=provider,
                    voice=voice,
                    text_hash=text_hash,
                )
                .first()
            )
            if existing:
                return _serialize_asset(existing)
            raise

        session.refresh(row)
        return _serialize_asset(row)


def _maybe_sign_url(url: str | None) -> str | None:
    if not url:
        return url

    for method_name in ("sign_url", "get_signed_url", "signed_url"):
        signer = getattr(_storage, method_name, None)
        if not callable(signer):
            continue
        try:
            signed = signer(url)
        except Exception:
            continue
        if isinstance(signed, str) and signed:
            return signed

    return url


def _serialize_asset(asset: MessageAudioAsset) -> dict[str, Any]:
    return {
        "id": asset.id,
        "message_id": asset.message_id,
        "provider": asset.provider,
        "voice": asset.voice,
        "text_hash": asset.text_hash,
        "src_url": _maybe_sign_url(asset.src_url),
        "internal_format": asset.internal_format,
        "delivery_variants_json": asset.delivery_variants_json or {},
        "duration_seconds": asset.duration_seconds,
        "filesize_bytes": asset.filesize_bytes,
        "created_at": asset.created_at.isoformat()
        if isinstance(asset.created_at, datetime)
        else str(asset.created_at),
    }
