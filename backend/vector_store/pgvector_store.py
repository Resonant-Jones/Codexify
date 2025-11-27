"""Postgres/pgvector backed vector store implementation."""

from __future__ import annotations

import logging
import os
from typing import Any, Mapping, Sequence

from sqlalchemy import (
    Column,
    Index,
    MetaData,
    String,
    Table,
    create_engine,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

try:
    from pgvector.sqlalchemy import CosineDistance, Vector
except ImportError as exc:  # pragma: no cover - import guard
    raise ImportError(
        "pgvector package is required for the pgvector vector store. "
        "Install it with `pip install pgvector`."
    ) from exc

from . import DEFAULT_NAMESPACE, VectorStore

logger = logging.getLogger(__name__)


class PGVectorStore(VectorStore):
    """Vector store backed by Postgres + pgvector."""

    def __init__(
        self,
        *,
        database_url: str | None = None,
        table_name: str = "embeddings",
        schema: str | None = None,
        engine: Engine | None = None,
        eager_init: bool = True,
    ) -> None:
        self._database_url = database_url or os.getenv("DATABASE_URL")
        if not self._database_url and engine is None:
            raise ValueError(
                "DATABASE_URL is required when using the pgvector vector store."
            )

        self._engine: Engine = engine or create_engine(
            self._database_url, future=True
        )
        self._metadata = MetaData(schema=schema)
        self._table = Table(
            table_name,
            self._metadata,
            Column("id", String, primary_key=True),
            Column("vector", Vector(), nullable=False),
            Column("metadata", JSONB, nullable=False),
            Column("namespace", String, nullable=False),
            extend_existing=True,
        )
        Index(f"idx_{table_name}_namespace", self._table.c.namespace)

        if eager_init:
            self._ensure_ready()

    def upsert(
        self,
        *,
        id: str,
        embedding: Sequence[float],
        metadata: Mapping[str, Any],
    ) -> None:
        namespace = _namespace_from_metadata(metadata)
        payload = dict(metadata)

        stmt = pg_insert(self._table).values(
            id=id,
            vector=list(embedding),
            metadata=payload,
            namespace=namespace,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[self._table.c.id],
            set_={
                "vector": stmt.excluded.vector,
                "metadata": stmt.excluded.metadata,
                "namespace": stmt.excluded.namespace,
            },
        )

        with Session(self._engine) as session, session.begin():
            session.execute(stmt)

    def query(
        self,
        *,
        embedding: Sequence[float],
        top_k: int,
        namespace: str | None = None,
    ) -> list[dict[str, Any]]:
        distance_expr = CosineDistance(
            self._table.c.vector, list(embedding)
        ).label("distance")

        stmt = (
            select(
                self._table.c.id,
                self._table.c.metadata,
                self._table.c.namespace,
                distance_expr,
            )
            .order_by(distance_expr.asc())
            .limit(max(top_k, 0))
        )

        if namespace:
            stmt = stmt.where(self._table.c.namespace == namespace)

        rows = []
        with Session(self._engine) as session:
            result = session.execute(stmt)
            rows = result.fetchall()

        matches: list[dict[str, Any]] = []
        for row in rows:
            distance = float(row.distance) if row.distance is not None else 1.0
            score = 1.0 - distance
            matches.append(
                {
                    "id": row.id,
                    "score": score,
                    "metadata": row.metadata,
                    "namespace": row.namespace,
                }
            )
        return matches

    def delete(
        self,
        *,
        namespace: str | None = None,
        ids: Sequence[str] | None = None,
    ) -> int:
        stmt = self._table.delete()

        if namespace:
            stmt = stmt.where(self._table.c.namespace == namespace)

        if ids:
            stmt = stmt.where(self._table.c.id.in_(list(ids)))

        with Session(self._engine) as session, session.begin():
            result = session.execute(stmt)
            return int(result.rowcount or 0)

    def _ensure_ready(self) -> None:
        try:
            with self._engine.begin() as conn:
                try:
                    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                except SQLAlchemyError as exc:
                    logger.debug(
                        "Skipping pgvector extension creation: %s", exc
                    )
                self._metadata.create_all(conn)
        except SQLAlchemyError as exc:  # pragma: no cover - defensive
            raise RuntimeError("Failed to initialise pgvector table") from exc


def _namespace_from_metadata(metadata: Mapping[str, Any]) -> str:
    namespace = (
        metadata.get("namespace") if isinstance(metadata, Mapping) else None
    )
    if isinstance(namespace, str) and namespace.strip():
        return namespace.strip()
    return DEFAULT_NAMESPACE


__all__ = ["PGVectorStore"]
