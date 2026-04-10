"""Startup seeding helpers for runtime vector indexes."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from sqlalchemy import select

from guardian.cognition.system_docs import store as system_doc_store
from guardian.core.dependencies import get_vector_store
from guardian.db.models import SystemDoc

logger = logging.getLogger(__name__)

_SYSTEM_DOC_NAMESPACE = "system_docs:global"
_BUILTIN_HELP_SLUG = "builtin-help"
_BUILTIN_HELP_TITLE = "Codexify Guide"
_BUILTIN_HELP_FILENAME = "codexify-guide.md"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _builtin_help_candidate_paths() -> list[Path]:
    root = _repo_root()
    return [
        root
        / "backend"
        / "resources"
        / "builtin-help"
        / _BUILTIN_HELP_FILENAME,
        root / "docs" / "builtin-help" / _BUILTIN_HELP_FILENAME,
    ]


def _load_builtin_help_asset(path: Path | None = None) -> dict[str, Any] | None:
    candidate_paths = (
        [path] if path is not None else _builtin_help_candidate_paths()
    )
    for candidate in candidate_paths:
        if candidate is None:
            continue
        if not candidate.is_file():
            continue
        content = candidate.read_text(encoding="utf-8")
        return {
            "id": f"system-doc:{_BUILTIN_HELP_SLUG}",
            "text": content,
            "meta": {
                "namespace": _SYSTEM_DOC_NAMESPACE,
                "source": "builtin_help_asset",
                "scope": "global",
                "doc_id": _BUILTIN_HELP_SLUG,
                "slug": _BUILTIN_HELP_SLUG,
                "title": _BUILTIN_HELP_TITLE,
                "asset_path": str(candidate),
                "is_enabled": True,
            },
        }
    return None


def _load_global_system_docs(
    *,
    session_factory: Any | None = None,
) -> list[SystemDoc]:
    factory = session_factory or system_doc_store._get_session_factory()  # type: ignore[attr-defined]
    with factory() as session:
        stmt = (
            select(SystemDoc)
            .where(
                SystemDoc.scope == "global",
                SystemDoc.is_enabled.is_(True),
            )
            .order_by(SystemDoc.id.asc())
        )
        return list(session.scalars(stmt).all())


def seed_global_system_docs(
    vector_store: Any | None = None,
    *,
    session_factory: Any | None = None,
    builtin_help_path: Path | None = None,
) -> dict[str, Any]:
    """Seed enabled global system docs into the shared runtime vector store.

    The seed is intentionally idempotent at the persistence layer:
    - Chroma receives stable ids and upserts.
    - FAISS is process-local, so startup replays the canonical DB rows into
      the current in-memory index after a restart or index reset.
    """
    store = vector_store or get_vector_store()
    docs = _load_global_system_docs(session_factory=session_factory)
    existing_slugs = {
        str(getattr(doc, "slug", "") or "").strip()
        for doc in docs
        if str(getattr(doc, "slug", "") or "").strip()
    }
    builtin_help_item = None
    if _BUILTIN_HELP_SLUG not in existing_slugs:
        builtin_help_item = _load_builtin_help_asset(builtin_help_path)
        if builtin_help_item is not None:
            existing_slugs.add(_BUILTIN_HELP_SLUG)
    if not docs:
        items: list[dict[str, Any]] = []
    else:
        items = []

    for doc in docs:
        items.append(
            {
                "id": f"system-doc:{doc.id}",
                "text": doc.content,
                "meta": {
                    "namespace": _SYSTEM_DOC_NAMESPACE,
                    "source": "system_doc",
                    "scope": doc.scope,
                    "doc_id": doc.id,
                    "slug": doc.slug,
                    "title": doc.title,
                    "owner_user_id": doc.owner_user_id,
                    "project_id": doc.project_id,
                    "is_enabled": doc.is_enabled,
                },
            }
        )

    if builtin_help_item is not None:
        items.append(builtin_help_item)

    if not items:
        return {
            "seeded": 0,
            "candidate_count": 0,
            "namespace": _SYSTEM_DOC_NAMESPACE,
        }

    seeded = int(store.add_texts(items))
    logger.info(
        "[startup] seeded global system docs into vector store count=%d",
        seeded,
    )
    return {
        "seeded": seeded,
        "candidate_count": len(items),
        "namespace": _SYSTEM_DOC_NAMESPACE,
    }


__all__ = ["seed_global_system_docs"]
