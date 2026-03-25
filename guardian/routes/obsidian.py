"""
Obsidian control-plane routes for local indexing.

Surface:
- GET /api/obsidian/config   -> read stored config
- PUT /api/obsidian/config   -> validate + persist config
- POST /api/obsidian/preview -> dry-run scan (no vectors)
- POST /api/obsidian/index   -> run indexing + update metadata
"""

from __future__ import annotations

import logging
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from guardian.core.dependencies import chatlog_db, require_api_key
from guardian.obsidian.indexer import (
    _normalize_tags,
    _resolve_allowed_paths,
    _resolve_vault_root,
    _scan_obsidian_vault,
    index_obsidian_vault,
)

logger = logging.getLogger(__name__)

CONNECTOR_NAME = "obsidian_local"
CONNECTOR_TYPE = "obsidian"
SAMPLE_LIMIT = 20


class ConfigPayload(BaseModel):
    vault_root: str
    allowed_paths: list[str] | None = None
    allowed_tags: list[str] | None = None


class PreviewPayload(BaseModel):
    allowed_paths: list[str] | None = None
    allowed_tags: list[str] | None = None


router = APIRouter(
    prefix="/api/obsidian",
    tags=["Obsidian"],
    dependencies=[Depends(require_api_key)],
)


def _load_settings() -> dict[str, Any] | None:
    cfg = chatlog_db.get_connector_config(CONNECTOR_NAME)
    if not cfg:
        return None
    settings = cfg.get("settings") or {}
    if not isinstance(settings, dict):
        settings = {}
    return settings


def _store_config(config: dict[str, Any]) -> dict[str, Any]:
    existing = chatlog_db.get_connector_config(CONNECTOR_NAME)
    if existing:
        stored = chatlog_db.update_connector_config(
            CONNECTOR_NAME, config=config
        )
    else:
        stored = chatlog_db.create_connector_config(
            CONNECTOR_NAME, CONNECTOR_TYPE, config
        )
    return stored.get("settings") or config


def _normalize_allowed_paths_for_storage(
    root: Path, allowed_paths: Sequence[str | Path] | None
) -> list[str]:
    resolved = _resolve_allowed_paths(root, allowed_paths)
    normalized: list[str] = []
    for path in resolved:
        try:
            rel = path.relative_to(root).as_posix()
        except ValueError:
            rel = str(path)
        if rel in ("", "."):
            continue
        normalized.append(rel)
    # Deduplicate while preserving order
    seen = set()
    ordered = []
    for p in normalized:
        if p in seen:
            continue
        seen.add(p)
        ordered.append(p)
    return ordered


def _normalize_config_payload(
    payload: ConfigPayload, *, existing: dict[str, Any] | None
) -> dict[str, Any]:
    root = _resolve_vault_root(payload.vault_root)
    normalized_allowed_paths = _normalize_allowed_paths_for_storage(
        root, payload.allowed_paths
    )
    allowed_tags = _normalize_tags(payload.allowed_tags)

    base = {
        "vault_root": str(root),
        "allowed_paths": normalized_allowed_paths,
        "allowed_tags": allowed_tags,
    }
    if existing:
        for key in ("last_indexed_at", "last_indexed_count"):
            if key in existing:
                base[key] = existing.get(key)
    # Reset last error on update
    base["last_index_error"] = None
    return base


def _runtime_config(settings: dict[str, Any]) -> dict[str, Any]:
    if not settings or "vault_root" not in settings:
        raise HTTPException(
            status_code=400, detail={"error": "obsidian_config_missing"}
        )
    vault_root = settings.get("vault_root")
    allowed_paths = settings.get("allowed_paths")
    if allowed_paths == []:
        allowed_paths = None
    allowed_tags = _normalize_tags(settings.get("allowed_tags"))
    return {
        "vault_root": vault_root,
        "allowed_paths": allowed_paths,
        "allowed_tags": allowed_tags,
    }


@router.get("/config")
def get_config() -> dict[str, Any]:
    settings = _load_settings()
    if settings is None:
        raise HTTPException(
            status_code=404, detail={"error": "obsidian_config_missing"}
        )
    return {
        "name": CONNECTOR_NAME,
        "type": CONNECTOR_TYPE,
        "config": settings,
    }


@router.put("/config")
def put_config(payload: ConfigPayload) -> dict[str, Any]:
    existing = _load_settings()
    try:
        normalized = _normalize_config_payload(payload, existing=existing)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"error": str(exc)})

    stored = _store_config(normalized)
    return {
        "name": CONNECTOR_NAME,
        "type": CONNECTOR_TYPE,
        "config": stored,
    }


@router.post("/preview")
def preview(payload: PreviewPayload) -> dict[str, Any]:
    settings = _load_settings()
    if settings is None:
        raise HTTPException(
            status_code=400, detail={"error": "obsidian_config_missing"}
        )

    runtime = _runtime_config(settings)
    allowed_paths = (
        payload.allowed_paths
        if payload.allowed_paths is not None
        else runtime.get("allowed_paths")
    )
    allowed_tags = (
        payload.allowed_tags
        if payload.allowed_tags is not None
        else runtime.get("allowed_tags")
    )
    if allowed_paths == []:
        raise HTTPException(
            status_code=400, detail={"error": "allowed_paths_empty"}
        )
    try:
        matched_paths, scanned, failures = _scan_obsidian_vault(
            runtime["vault_root"],
            allowed_paths=allowed_paths,
            allowed_tags=allowed_tags,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"error": str(exc)})

    sample = matched_paths[:SAMPLE_LIMIT]
    return {
        "note_count": len(matched_paths),
        "sample_paths": sample,
        "scanned": scanned,
        "failures": failures,
    }


def _update_index_metadata(
    settings: dict[str, Any],
    *,
    indexed_at: str | None,
    indexed_count: int | None,
    error: str | None,
) -> dict[str, Any]:
    updated = deepcopy(settings)
    updated["last_indexed_at"] = indexed_at
    updated["last_indexed_count"] = indexed_count
    updated["last_index_error"] = error
    return updated


@router.post("/index")
def index() -> dict[str, Any]:
    settings = _load_settings()
    if settings is None:
        raise HTTPException(
            status_code=400, detail={"error": "obsidian_config_missing"}
        )

    runtime = _runtime_config(settings)
    try:
        summary = index_obsidian_vault(
            runtime["vault_root"],
            allowed_paths=runtime.get("allowed_paths"),
            allowed_tags=runtime.get("allowed_tags"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"error": str(exc)})
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.exception("[obsidian] indexing failed: %s", exc)
        errored = _update_index_metadata(
            settings,
            indexed_at=settings.get("last_indexed_at"),
            indexed_count=settings.get("last_indexed_count"),
            error=str(exc),
        )
        _store_config(errored)
        raise HTTPException(
            status_code=500,
            detail={"error": "obsidian_index_failed", "message": str(exc)},
        )

    updated = _update_index_metadata(
        settings,
        indexed_at=summary.get("indexed_at"),
        indexed_count=summary.get("indexed"),
        error=None,
    )
    _store_config(updated)

    return {
        "indexed": summary.get("indexed", 0),
        "scanned": summary.get("scanned", 0),
        "deleted": summary.get("deleted", 0),
        "failures": summary.get("failures", []),
        "indexed_at": summary.get("indexed_at"),
    }
