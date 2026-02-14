"""Unified ingestion identity and alias helpers for media assets."""

from __future__ import annotations

import hashlib
import mimetypes
import os
import re
import unicodedata
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import or_
from sqlalchemy.orm import Session

from guardian.db.models import MediaAlias, MediaAsset

MEDIA_STORAGE_PREFIX: dict[tuple[str, str], str] = {
    ("document", "uploaded"): "documents/",
    ("image", "uploaded"): "images/",
    ("image", "generated"): "generated_images/",
    ("audio", "generated"): "audio/",
}

VALID_MEDIA_KINDS = {"document", "image", "audio", "video", "other"}
VALID_PROVENANCE = {"uploaded", "generated", "imported", "system"}
VALID_ALIAS_TYPES = {
    "original_name",
    "prompt",
    "user_alias",
    "system_generated",
}

MEDIA_TITLE_MODE_HUMAN = "human"
MEDIA_TITLE_MODE_CANONICAL = "canonical"

_MIME_EXTENSION_MAP = {
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
    "application/pdf": "pdf",
    "text/plain": "txt",
    "text/markdown": "md",
    "application/msword": "doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "audio/wav": "wav",
}


@dataclass(frozen=True)
class IdentityComputation:
    content_hash: str
    deterministic_id: str
    normalized_slug: str
    system_name: str
    storage_prefix: str
    extension: str | None


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def get_media_title_mode() -> str:
    mode = os.getenv("MEDIA_TITLE_MODE", MEDIA_TITLE_MODE_HUMAN).strip().lower()
    if mode in (MEDIA_TITLE_MODE_HUMAN, MEDIA_TITLE_MODE_CANONICAL):
        return mode
    return MEDIA_TITLE_MODE_HUMAN


def normalize_alias(value: str | None) -> str:
    if not value:
        return ""
    ascii_value = (
        unicodedata.normalize("NFKD", value)
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    lowered = ascii_value.lower()
    cleaned = re.sub(r"[^a-z0-9]+", " ", lowered)
    return re.sub(r"\s+", " ", cleaned).strip()


def normalize_slug(
    value: str | None, *, fallback: str, max_length: int = 80
) -> str:
    alias = normalize_alias(value)
    if not alias:
        alias = normalize_alias(fallback)
    if not alias:
        alias = "asset"
    slug = alias.replace(" ", "-")
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    if not slug:
        slug = "asset"
    return slug[:max_length].rstrip("-") or "asset"


def source_label_from_filename(filename: str | None, *, fallback: str) -> str:
    if not filename:
        return fallback
    stem = Path(filename).stem.strip()
    return stem or fallback


def compute_content_hash(file_data: bytes) -> str:
    return hashlib.sha256(file_data).hexdigest()


def infer_extension(
    *,
    original_filename: str | None,
    mime_type: str | None,
) -> str | None:
    if original_filename:
        suffix = Path(original_filename).suffix.strip().lower()
        if suffix.startswith(".") and len(suffix) > 1:
            return suffix[1:]
    if mime_type:
        if mime_type in _MIME_EXTENSION_MAP:
            return _MIME_EXTENSION_MAP[mime_type]
        guessed = mimetypes.guess_extension(mime_type)
        if guessed and guessed.startswith(".") and len(guessed) > 1:
            return guessed[1:]
    return None


def get_storage_prefix(media_kind: str, provenance: str) -> str:
    key = (media_kind, provenance)
    if key in MEDIA_STORAGE_PREFIX:
        return MEDIA_STORAGE_PREFIX[key]
    return "other/"


def build_deterministic_id(content_hash: str, first_seen_at: datetime) -> str:
    date_part = first_seen_at.strftime("%Y%m%d")
    return f"{date_part}-{content_hash[:8]}"


def build_system_name(
    deterministic_id: str,
    normalized_slug: str,
    extension: str | None,
) -> str:
    filename = f"{deterministic_id}--{normalized_slug}"
    if extension:
        return f"{filename}.{extension}"
    return filename


def compute_identity(
    *,
    file_data: bytes,
    media_kind: str,
    provenance: str,
    human_label: str,
    original_filename: str | None,
    mime_type: str | None,
    first_seen_at: datetime,
    content_hash: str | None = None,
) -> IdentityComputation:
    content_hash = content_hash or compute_content_hash(file_data)
    normalized_slug = normalize_slug(
        human_label,
        fallback="generated-image"
        if media_kind == "image" and provenance == "generated"
        else "asset",
    )
    extension = infer_extension(
        original_filename=original_filename,
        mime_type=mime_type,
    )
    deterministic_id = build_deterministic_id(content_hash, first_seen_at)
    system_name = build_system_name(
        deterministic_id, normalized_slug, extension
    )
    storage_prefix = get_storage_prefix(media_kind, provenance)
    return IdentityComputation(
        content_hash=content_hash,
        deterministic_id=deterministic_id,
        normalized_slug=normalized_slug,
        system_name=system_name,
        storage_prefix=storage_prefix,
        extension=extension,
    )


def find_existing_asset(
    session: Session,
    *,
    project_id: int,
    media_kind: str,
    provenance: str,
    content_hash: str,
) -> MediaAsset | None:
    return (
        session.query(MediaAsset)
        .filter(
            MediaAsset.project_id == project_id,
            MediaAsset.media_kind == media_kind,
            MediaAsset.provenance == provenance,
            MediaAsset.content_hash == content_hash,
            MediaAsset.deleted_at.is_(None),
        )
        .order_by(MediaAsset.ingested_at.asc())
        .first()
    )


def find_first_seen_timestamp(
    session: Session,
    *,
    project_id: int,
    media_kind: str,
    provenance: str,
    content_hash: str,
    fallback: datetime | None = None,
) -> datetime:
    fallback = fallback or utcnow()
    first_seen = (
        session.query(MediaAsset.ingested_at)
        .filter(
            MediaAsset.project_id == project_id,
            MediaAsset.media_kind == media_kind,
            MediaAsset.provenance == provenance,
            MediaAsset.content_hash == content_hash,
        )
        .order_by(MediaAsset.ingested_at.asc())
        .first()
    )
    if first_seen and first_seen[0]:
        return first_seen[0]
    return fallback


def ensure_asset_alias(
    session: Session,
    *,
    asset_id: str,
    alias: str | None,
    alias_type: str,
) -> None:
    if alias_type not in VALID_ALIAS_TYPES:
        raise ValueError(f"Unsupported alias_type: {alias_type}")
    alias_value = (alias or "").strip()
    if not alias_value:
        return
    alias_normalized = normalize_alias(alias_value)
    if not alias_normalized:
        return
    exists = (
        session.query(MediaAlias.id)
        .filter(
            MediaAlias.asset_id == asset_id,
            MediaAlias.alias_normalized == alias_normalized,
            MediaAlias.alias_type == alias_type,
        )
        .first()
    )
    if exists:
        return
    session.add(
        MediaAlias(
            id=str(uuid.uuid4()),
            asset_id=asset_id,
            alias=alias_value,
            alias_normalized=alias_normalized,
            alias_type=alias_type,
        )
    )


def _base_asset_query(
    session: Session,
    *,
    project_id: int,
    media_kind: str | None = None,
    provenance: str | None = None,
    source_tag: str | None = None,
):
    query = session.query(MediaAsset).filter(
        MediaAsset.project_id == project_id,
        MediaAsset.deleted_at.is_(None),
    )
    if media_kind:
        query = query.filter(MediaAsset.media_kind == media_kind)
    if provenance:
        query = query.filter(MediaAsset.provenance == provenance)
    if source_tag:
        query = query.filter(MediaAsset.source_tag == source_tag)
    return query


def resolve_asset(
    session: Session,
    *,
    project_id: int,
    query: str,
    media_kind: str | None = None,
    provenance: str | None = None,
    source_tag: str | None = None,
) -> MediaAsset | None:
    normalized_query = normalize_alias(query)
    if not normalized_query:
        return None

    base_query = _base_asset_query(
        session,
        project_id=project_id,
        media_kind=media_kind,
        provenance=provenance,
        source_tag=source_tag,
    )

    exact_alias = (
        base_query.join(MediaAlias, MediaAlias.asset_id == MediaAsset.id)
        .filter(MediaAlias.alias_normalized == normalized_query)
        .order_by(MediaAsset.ingested_at.asc())
        .first()
    )
    if exact_alias:
        return exact_alias

    partial_alias = (
        base_query.join(MediaAlias, MediaAlias.asset_id == MediaAsset.id)
        .filter(MediaAlias.alias_normalized.ilike(f"%{normalized_query}%"))
        .order_by(MediaAsset.ingested_at.desc())
        .first()
    )
    if partial_alias:
        return partial_alias

    return (
        base_query.filter(
            or_(
                MediaAsset.normalized_slug.ilike(f"%{normalized_query}%"),
                MediaAsset.system_name.ilike(f"%{normalized_query}%"),
            )
        )
        .order_by(MediaAsset.ingested_at.desc())
        .first()
    )


def display_title_for_asset(
    session: Session,
    *,
    asset: MediaAsset,
    title_mode: str | None = None,
) -> str:
    mode = title_mode or get_media_title_mode()
    if mode == MEDIA_TITLE_MODE_CANONICAL:
        return asset.system_name

    preferred_alias_types: tuple[str, ...]
    if asset.media_kind == "image" and asset.provenance == "generated":
        preferred_alias_types = (
            "prompt",
            "user_alias",
            "original_name",
            "system_generated",
        )
    else:
        preferred_alias_types = (
            "original_name",
            "user_alias",
            "prompt",
            "system_generated",
        )

    for alias_type in preferred_alias_types:
        alias = (
            session.query(MediaAlias.alias)
            .filter(
                MediaAlias.asset_id == asset.id,
                MediaAlias.alias_type == alias_type,
            )
            .order_by(MediaAlias.created_at.asc())
            .first()
        )
        if alias and alias[0]:
            return alias[0]

    if asset.media_kind == "image" and asset.provenance == "generated":
        return "Generated image"
    return asset.normalized_slug.replace("-", " ").strip() or asset.system_name
