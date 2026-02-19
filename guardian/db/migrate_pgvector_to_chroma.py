"""One-shot migration helper from pgvector to Chroma."""

from __future__ import annotations

import argparse
import logging
import os
from collections import defaultdict
from typing import Any, Iterable

import chromadb
from chromadb.api import ClientAPI
from chromadb.config import Settings
from sqlalchemy import text
from sqlalchemy.engine import Engine, create_engine
from sqlalchemy.exc import SQLAlchemyError

from backend.vector_store import DEFAULT_NAMESPACE

logger = logging.getLogger(__name__)


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL"),
        help="Postgres connection string (defaults to $DATABASE_URL)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Number of embeddings fetched per batch",
    )
    parser.add_argument(
        "--chroma-directory",
        default=os.getenv("CHROMA_PERSIST_DIRECTORY"),
        help="Optional Chroma persistence directory",
    )
    parser.add_argument(
        "--collection-prefix",
        default="guardian",
        help="Prefix used for created Chroma collections",
    )
    return parser


def create_chroma_client(directory: str | None) -> ClientAPI:
    settings = Settings(anonymized_telemetry=False)
    if directory:
        return chromadb.PersistentClient(path=directory, settings=settings)
    return chromadb.Client(settings=settings)


def iter_embeddings(
    engine: Engine, batch_size: int
) -> Iterable[list[dict[str, Any]]]:
    query = text(
        "SELECT id, vector, metadata, namespace FROM embeddings ORDER BY namespace"
    )
    with engine.connect() as conn:
        result = conn.execution_options(stream_results=True).execute(query)
        while True:
            chunk = result.fetchmany(batch_size)
            if not chunk:
                break
            rows: list[dict[str, Any]] = []
            for row in chunk:
                rows.append(
                    {
                        "id": row.id,
                        "vector": list(row.vector)
                        if row.vector is not None
                        else [],
                        "metadata": dict(row.metadata or {}),
                        "namespace": (row.namespace or DEFAULT_NAMESPACE)
                        or DEFAULT_NAMESPACE,
                    }
                )
            yield rows


def migrate(args: argparse.Namespace) -> None:
    if not args.database_url:
        raise SystemExit(
            "DATABASE_URL must be provided via --database-url or environment"
        )

    engine = create_engine(args.database_url, future=True)
    client = create_chroma_client(args.chroma_directory)

    imported = 0
    errors = 0
    per_namespace: dict[str, int] = defaultdict(int)

    logger.info("Starting migration from pgvector to Chroma...")
    try:
        for batch in iter_embeddings(engine, args.batch_size):
            for record in batch:
                namespace = record["namespace"] or DEFAULT_NAMESPACE
                collection_name = f"{args.collection_prefix}_{namespace}"
                collection = client.get_or_create_collection(
                    name=collection_name
                )
                metadata = dict(record["metadata"])
                metadata.setdefault("namespace", namespace)
                try:
                    collection.upsert(
                        ids=[record["id"]],
                        embeddings=[record["vector"]],
                        metadatas=[metadata],
                    )
                    imported += 1
                    per_namespace[namespace] += 1
                except Exception as exc:  # pragma: no cover - defensive logging
                    errors += 1
                    logger.error(
                        f"Failed to import {record['id']} (namespace={namespace}): {exc}"
                    )
            if imported and imported % 250 == 0:
                logger.info(f"Imported {imported} embeddings so far...")
    except SQLAlchemyError as exc:
        raise SystemExit(
            f"Database error while exporting embeddings: {exc}"
        ) from exc

    logger.info("Migration completed.")
    logger.info(f"Total imported: {imported}")
    if errors:
        logger.warning(f"Errors: {errors} (review log output above)")
    if per_namespace:
        logger.info("By namespace:")
        for namespace, count in sorted(per_namespace.items()):
            logger.info(f"  - {namespace}: {count}")


def main() -> None:
    parser = make_parser()
    args = parser.parse_args()
    migrate(args)


if __name__ == "__main__":
    main()
