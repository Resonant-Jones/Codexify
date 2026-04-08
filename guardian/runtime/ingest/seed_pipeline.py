"""Startup seeding helpers for runtime vector indexes."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select

from guardian.cognition.system_docs import store as system_doc_store
from guardian.core.dependencies import get_vector_store
from guardian.db.models import SystemDoc

logger = logging.getLogger(__name__)

_SYSTEM_DOC_NAMESPACE = "system_docs:global"


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
) -> dict[str, Any]:
    """Seed enabled global system docs into the shared runtime vector store.

    The seed is intentionally idempotent at the persistence layer:
    - Chroma receives stable ids and upserts.
    - FAISS is process-local, so startup replays the canonical DB rows into
      the current in-memory index after a restart or index reset.
    """
    store = vector_store or get_vector_store()
    docs = _load_global_system_docs(session_factory=session_factory)
    if not docs:
        return {
            "seeded": 0,
            "candidate_count": 0,
            "namespace": _SYSTEM_DOC_NAMESPACE,
        }

    items: list[dict[str, Any]] = []
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
