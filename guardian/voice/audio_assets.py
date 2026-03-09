"""Helpers for message-linked audio asset persistence."""

from __future__ import annotations

import hashlib
import os
from datetime import datetime
from typing import Any, Iterable
from urllib.parse import urlsplit

from sqlalchemy.exc import IntegrityError

from guardian.core.db import GuardianDB, load_guardian_db_from_env
from guardian.core.dependencies import chatlog_db
from guardian.core.media_signing import sign_media_url
from guardian.core.storage import create_storage_from_env
from guardian.db.models import MessageAudioAsset

_storage = create_storage_from_env()
_AUDIO_STATUS_VALUES = {"pending", "ready", "failed"}


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


def _normalize_audio_status(status: str | None, *, src_url: str | None) -> str:
    normalized = str(status or "").strip().lower()
    if normalized in _AUDIO_STATUS_VALUES:
        return normalized
    if str(src_url or "").strip():
        return "ready"
    return "pending"


def _serialize_error_payload(error: Any) -> dict[str, Any] | None:
    if error is None:
        return None
    if isinstance(error, dict):
        return {
            str(key): value
            for key, value in error.items()
            if value not in (None, "", [], {})
        } or None
    message = str(error).strip()
    if not message:
        return None
    return {"message": message}


def _normalized_delivery_variants(
    *,
    existing: dict[str, Any] | None = None,
    updates: dict[str, Any] | None = None,
    status: str,
    mime_type: str | None = None,
    error: Any | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if isinstance(existing, dict):
        payload.update(existing)
    if isinstance(updates, dict):
        payload.update(updates)
    payload["status"] = _normalize_audio_status(status, src_url=None)
    if mime_type:
        payload["mime_type"] = mime_type
    serialized_error = _serialize_error_payload(error)
    if serialized_error:
        payload["error"] = serialized_error
    elif payload.get("status") == "ready":
        payload.pop("error", None)
    return payload


def _asset_status(asset: MessageAudioAsset) -> str:
    variants = (
        asset.delivery_variants_json
        if isinstance(asset.delivery_variants_json, dict)
        else {}
    )
    return _normalize_audio_status(
        variants.get("status") if isinstance(variants, dict) else None,
        src_url=asset.src_url,
    )


def _asset_is_ready(asset: MessageAudioAsset) -> bool:
    return _asset_status(asset) == "ready" and bool(
        str(asset.src_url or "").strip()
    )


def _base_asset_query(
    session,
    *,
    message_id: int,
    provider: str | None = None,
    voice: str | None = None,
):
    query = session.query(MessageAudioAsset).filter_by(message_id=message_id)
    if provider is not None:
        query = query.filter_by(provider=provider)
    if voice is not None:
        query = query.filter_by(voice=voice)
    return query.order_by(
        MessageAudioAsset.created_at.desc(),
        MessageAudioAsset.id.desc(),
    )


def _latest_asset_row(
    session,
    *,
    message_id: int,
    provider: str | None = None,
    voice: str | None = None,
) -> MessageAudioAsset | None:
    return _base_asset_query(
        session,
        message_id=message_id,
        provider=provider,
        voice=voice,
    ).first()


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
            _base_asset_query(
                session,
                message_id=message_id,
                provider=provider,
                voice=voice,
            )
            .filter_by(text_hash=text_hash)
            .first()
        )
        if not row or not _asset_is_ready(row):
            return None
        return _serialize_asset(row)


def upsert_message_audio_asset_status(
    *,
    message_id: int,
    text: str,
    provider: str,
    voice: str,
    status: str,
    audio_format: str = "wav",
    delivery_variants_json: dict[str, Any] | None = None,
    error: Any | None = None,
) -> dict[str, Any]:
    normalized_status = _normalize_audio_status(status, src_url=None)
    text_hash = compute_text_hash(text)
    db = _db()
    with db.get_session() as session:
        row = _latest_asset_row(
            session,
            message_id=message_id,
            provider=provider,
            voice=voice,
        )
        if row is None:
            row = MessageAudioAsset(
                message_id=message_id,
                provider=provider,
                voice=voice,
                text_hash=text_hash,
                src_url="",
                internal_format=audio_format,
                delivery_variants_json=_normalized_delivery_variants(
                    updates=delivery_variants_json,
                    status=normalized_status,
                    mime_type=_content_type_for_format(audio_format),
                    error=error,
                ),
                duration_seconds=None,
                filesize_bytes=None,
            )
            session.add(row)
        else:
            row.text_hash = text_hash
            row.src_url = ""
            row.internal_format = audio_format or row.internal_format or "wav"
            row.delivery_variants_json = _normalized_delivery_variants(
                existing=row.delivery_variants_json,
                updates=delivery_variants_json,
                status=normalized_status,
                mime_type=_content_type_for_format(row.internal_format),
                error=error,
            )
            row.duration_seconds = None
            row.filesize_bytes = None
        session.commit()
        session.refresh(row)
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
    content_type = _content_type_for_format(audio_format)
    filename = (
        f"audio/messages/{message_id}_{text_hash[:12]}_{provider}_{voice}.{ext}"
    )
    src_url = _storage.upload_file(
        audio_bytes,
        filename,
        content_type=content_type,
    )

    db = _db()
    with db.get_session() as session:
        row = _latest_asset_row(
            session,
            message_id=message_id,
            provider=provider,
            voice=voice,
        )
        if row is None:
            row = MessageAudioAsset(
                message_id=message_id,
                provider=provider,
                voice=voice,
                text_hash=text_hash,
                src_url=src_url,
                internal_format=audio_format,
                delivery_variants_json=_normalized_delivery_variants(
                    updates=delivery_variants_json,
                    status="ready",
                    mime_type=content_type,
                ),
                duration_seconds=None,
                filesize_bytes=len(audio_bytes),
            )
            session.add(row)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                existing = (
                    _base_asset_query(
                        session,
                        message_id=message_id,
                        provider=provider,
                        voice=voice,
                    )
                    .filter_by(text_hash=text_hash)
                    .first()
                )
                if existing:
                    return _serialize_asset(existing)
                raise
        else:
            row.text_hash = text_hash
            row.src_url = src_url
            row.internal_format = audio_format
            row.delivery_variants_json = _normalized_delivery_variants(
                existing=row.delivery_variants_json,
                updates=delivery_variants_json,
                status="ready",
                mime_type=content_type,
            )
            row.duration_seconds = None
            row.filesize_bytes = len(audio_bytes)
            session.commit()

        session.refresh(row)
        return _serialize_asset(row)


def list_message_audio_assets(
    *,
    message_ids: Iterable[int],
    preferred_source: str | None = None,
) -> dict[int, dict[str, Any]]:
    normalized_ids: list[int] = []
    for message_id in message_ids:
        try:
            value = int(message_id)
        except (TypeError, ValueError):
            continue
        if value > 0:
            normalized_ids.append(value)
    if not normalized_ids:
        return {}

    db = _db()
    with db.get_session() as session:
        rows = (
            session.query(MessageAudioAsset)
            .filter(MessageAudioAsset.message_id.in_(normalized_ids))
            .order_by(
                MessageAudioAsset.message_id.asc(),
                MessageAudioAsset.created_at.desc(),
                MessageAudioAsset.id.desc(),
            )
            .all()
        )

    selected: dict[int, tuple[int, MessageAudioAsset]] = {}
    for row in rows:
        variants = (
            row.delivery_variants_json
            if isinstance(row.delivery_variants_json, dict)
            else {}
        )
        source = str(variants.get("source") or "").strip().lower()
        status = _asset_status(row)
        priority = 0
        if preferred_source and source == preferred_source.strip().lower():
            priority += 100
        if status == "ready":
            priority += 10
        elif status == "pending":
            priority += 5
        current = selected.get(int(row.message_id))
        if current is None or priority > current[0]:
            selected[int(row.message_id)] = (priority, row)

    return {
        message_id: _serialize_asset(row)
        for message_id, (_priority, row) in selected.items()
    }


def _looks_like_remote_url(url: str) -> bool:
    lowered = (url or "").strip().lower()
    return lowered.startswith("http://") or lowered.startswith("https://")


def _sign_with_storage_signer(url: str) -> tuple[str, int | None]:
    for method_name in ("sign_url", "get_signed_url", "signed_url"):
        signer = getattr(_storage, method_name, None)
        if not callable(signer):
            continue
        try:
            signed = signer(url)
        except Exception:
            continue

        if isinstance(signed, str) and signed:
            return signed, None
        if isinstance(signed, dict):
            signed_url = str(
                signed.get("url") or signed.get("src_url") or ""
            ).strip()
            if not signed_url:
                continue
            expires_at = signed.get("expires_at") or signed.get(
                "url_expires_at"
            )
            try:
                expires_at_int = (
                    int(expires_at) if expires_at is not None else None
                )
            except Exception:
                expires_at_int = None
            return signed_url, expires_at_int
    return url, None


def _sign_local_media_url(url: str) -> str:
    candidate = (url or "").strip()
    if candidate.startswith("/media/"):
        return sign_media_url(candidate)

    parsed = urlsplit(candidate)
    if parsed.scheme or parsed.netloc:
        return candidate

    normalized = candidate.lstrip("/")
    if normalized.startswith("media/"):
        return sign_media_url(f"/{normalized}")
    return sign_media_url(f"/media/{normalized}")


def _signed_asset_url(url: str | None) -> tuple[str | None, int | None]:
    if url is None:
        return None, None

    candidate = str(url).strip()
    if not candidate:
        return None, None

    if _looks_like_remote_url(candidate):
        return _sign_with_storage_signer(candidate)

    # Local /media paths or local storage keys always use Guardian media signing.
    return _sign_local_media_url(candidate), None


def _serialize_asset(asset: MessageAudioAsset) -> dict[str, Any]:
    signed_src, expires_at = _signed_asset_url(asset.src_url)
    status = _asset_status(asset)
    delivery_variants = (
        asset.delivery_variants_json
        if isinstance(asset.delivery_variants_json, dict)
        else {}
    )
    error_payload = (
        delivery_variants.get("error")
        if isinstance(delivery_variants.get("error"), dict)
        else None
    )
    return {
        "id": asset.id,
        "message_id": asset.message_id,
        "provider": asset.provider,
        "voice": asset.voice,
        "text_hash": asset.text_hash,
        "src_url": signed_src,
        "stream_url": f"/api/voice/audio/{asset.id}" if asset.id else None,
        "url_expires_at": expires_at,
        "internal_format": asset.internal_format,
        "mime_type": delivery_variants.get("mime_type")
        or _content_type_for_format(asset.internal_format),
        "status": status,
        "delivery_variants_json": delivery_variants,
        "duration_seconds": asset.duration_seconds,
        "filesize_bytes": asset.filesize_bytes,
        "error": error_payload,
        "created_at": asset.created_at.isoformat()
        if isinstance(asset.created_at, datetime)
        else str(asset.created_at),
    }
