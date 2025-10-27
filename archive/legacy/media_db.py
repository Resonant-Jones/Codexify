"""
⚠️ DEPRECATED: Archived on 2025-10-27
==================================================
This module has been superseded by:
- ORM models in guardian/db/models.py
- Alembic revision 9373693cc12e_add_media_and_tts_tables.py
- Storage abstraction in guardian/core/storage.py
- REST API in guardian/routes/media.py

DO NOT import from this module in runtime code.
Preserved for historical reference only.
==================================================

guardian.core.media_db (Postgres)
=================================

Media Database Operations for Guardian (PostgreSQL backend)

This module provides database operations for managing:
- GeneratedImages (AI-generated images)
- UploadedImages (user-uploaded images)
- GeneratedDocuments (AI-generated documents)
- UploadedDocuments (user-uploaded documents)

All tables support soft deletes via deleted_at timestamp.

Notes:
- Requires psycopg (v3): `pip install psycopg[binary]`
- Uses DSN from env var `GUARDIAN_DB_URL` or `DATABASE_URL`
- Expects tables/indices created via migrations (no CREATE TABLE here)
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row


class MediaDB:
    """Handles all media-related database operations for Guardian (Postgres)."""

    def __init__(self, db_path: str | None = None):
        # `db_path` kept for API compatibility; if it looks like a DSN, allow it.
        dsn_from_arg = db_path if (db_path and db_path.startswith("postgres")) else None
        self.dsn = (
            dsn_from_arg or os.getenv("GUARDIAN_DB_URL") or os.getenv("DATABASE_URL")
        )
        if not self.dsn:
            raise RuntimeError(
                "Postgres DSN not configured. Set GUARDIAN_DB_URL or DATABASE_URL."
            )

    def _connect(self):
        """Open a new psycopg connection with dict_row row factory."""
        return psycopg.connect(self.dsn, row_factory=dict_row)

    # ==================== Generated Images ====================

    def create_generated_image(
        self,
        project_id: str,
        thread_id: str,
        user_id: str,
        src_url: str,
        prompt: str,
        model: str,
    ) -> str:
        """Create a new generated image record."""
        image_id = str(uuid4())
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO generated_images
                    (id, project_id, thread_id, user_id, src_url, prompt, model, created_at, updated_at)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s, now(), now())
                """,
                (image_id, project_id, thread_id, user_id, src_url, prompt, model),
            )
        return image_id

    def get_generated_images_by_project(
        self, project_id: str, include_deleted: bool = False
    ) -> List[Dict[str, Any]]:
        base = (
            "SELECT id, project_id, thread_id, user_id, src_url, prompt, model, created_at, updated_at "
            "FROM generated_images WHERE project_id = %s"
        )
        params: list[Any] = [project_id]
        if not include_deleted:
            base += " AND deleted_at IS NULL"
        base += " ORDER BY created_at DESC"
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(base, params)
            return list(cur.fetchall())

    def get_generated_images_by_thread(
        self, thread_id: str, include_deleted: bool = False
    ) -> List[Dict[str, Any]]:
        base = (
            "SELECT id, project_id, thread_id, user_id, src_url, prompt, model, created_at, updated_at "
            "FROM generated_images WHERE thread_id = %s"
        )
        params: list[Any] = [thread_id]
        if not include_deleted:
            base += " AND deleted_at IS NULL"
        base += " ORDER BY created_at DESC"
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(base, params)
            return list(cur.fetchall())

    def soft_delete_generated_image(self, image_id: str) -> bool:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE generated_images SET deleted_at = now(), updated_at = now() WHERE id = %s AND deleted_at IS NULL",
                (image_id,),
            )
            return cur.rowcount > 0

    # ==================== Uploaded Images ====================

    def create_uploaded_image(
        self,
        project_id: str,
        thread_id: str,
        user_id: str,
        src_url: str,
        filename: str,
        filesize: int,
        mime_type: str,
    ) -> str:
        image_id = str(uuid4())
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO uploaded_images
                    (id, project_id, thread_id, user_id, src_url, filename, filesize, mime_type, created_at, updated_at)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s, %s, now(), now())
                """,
                (
                    image_id,
                    project_id,
                    thread_id,
                    user_id,
                    src_url,
                    filename,
                    filesize,
                    mime_type,
                ),
            )
        return image_id

    def get_uploaded_images_by_project(
        self, project_id: str, include_deleted: bool = False
    ) -> List[Dict[str, Any]]:
        base = (
            "SELECT id, project_id, thread_id, user_id, src_url, filename, filesize, mime_type, created_at, updated_at "
            "FROM uploaded_images WHERE project_id = %s"
        )
        params: list[Any] = [project_id]
        if not include_deleted:
            base += " AND deleted_at IS NULL"
        base += " ORDER BY created_at DESC"
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(base, params)
            return list(cur.fetchall())

    def get_uploaded_images_by_mime_type(
        self, mime_type: str, include_deleted: bool = False
    ) -> List[Dict[str, Any]]:
        base = (
            "SELECT id, project_id, thread_id, user_id, src_url, filename, filesize, mime_type, created_at, updated_at "
            "FROM uploaded_images WHERE mime_type = %s"
        )
        params: list[Any] = [mime_type]
        if not include_deleted:
            base += " AND deleted_at IS NULL"
        base += " ORDER BY created_at DESC"
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(base, params)
            return list(cur.fetchall())

    def soft_delete_uploaded_image(self, image_id: str) -> bool:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE uploaded_images SET deleted_at = now(), updated_at = now() WHERE id = %s AND deleted_at IS NULL",
                (image_id,),
            )
            return cur.rowcount > 0

    # ==================== Generated Documents ====================

    def create_generated_document(
        self,
        project_id: str,
        thread_id: str,
        user_id: str,
        title: str,
        content: str,
        format: str,
        model: str,
    ) -> str:
        doc_id = str(uuid4())
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO generated_documents
                    (id, project_id, thread_id, user_id, title, content, format, model, created_at, updated_at)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s, %s, now(), now())
                """,
                (doc_id, project_id, thread_id, user_id, title, content, format, model),
            )
        return doc_id

    def get_generated_documents_by_project(
        self, project_id: str, include_deleted: bool = False
    ) -> List[Dict[str, Any]]:
        base = (
            "SELECT id, project_id, thread_id, user_id, title, content, format, model, created_at, updated_at "
            "FROM generated_documents WHERE project_id = %s"
        )
        params: list[Any] = [project_id]
        if not include_deleted:
            base += " AND deleted_at IS NULL"
        base += " ORDER BY created_at DESC"
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(base, params)
            return list(cur.fetchall())

    def get_generated_documents_by_format(
        self, format: str, include_deleted: bool = False
    ) -> List[Dict[str, Any]]:
        base = (
            "SELECT id, project_id, thread_id, user_id, title, content, format, model, created_at, updated_at "
            "FROM generated_documents WHERE format = %s"
        )
        params: list[Any] = [format]
        if not include_deleted:
            base += " AND deleted_at IS NULL"
        base += " ORDER BY created_at DESC"
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(base, params)
            return list(cur.fetchall())

    def soft_delete_generated_document(self, doc_id: str) -> bool:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE generated_documents SET deleted_at = now(), updated_at = now() WHERE id = %s AND deleted_at IS NULL",
                (doc_id,),
            )
            return cur.rowcount > 0

    # ==================== Uploaded Documents ====================

    def create_uploaded_document(
        self,
        project_id: str,
        thread_id: str,
        user_id: str,
        filename: str,
        filesize: int,
        mime_type: str,
        src_url: str,
        parsed_text: Optional[str] = None,
    ) -> str:
        doc_id = str(uuid4())
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO uploaded_documents
                    (id, project_id, thread_id, user_id, filename, filesize, mime_type, src_url, parsed_text, created_at, updated_at)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s, %s, %s, now(), now())
                """,
                (
                    doc_id,
                    project_id,
                    thread_id,
                    user_id,
                    filename,
                    filesize,
                    mime_type,
                    src_url,
                    parsed_text,
                ),
            )
        return doc_id

    def get_uploaded_documents_by_project(
        self, project_id: str, include_deleted: bool = False
    ) -> List[Dict[str, Any]]:
        base = (
            "SELECT id, project_id, thread_id, user_id, filename, filesize, mime_type, src_url, parsed_text, created_at, updated_at "
            "FROM uploaded_documents WHERE project_id = %s"
        )
        params: list[Any] = [project_id]
        if not include_deleted:
            base += " AND deleted_at IS NULL"
        base += " ORDER BY created_at DESC"
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(base, params)
            return list(cur.fetchall())

    def search_uploaded_documents(
        self, search_query: str, include_deleted: bool = False
    ) -> List[Dict[str, Any]]:
        """Search uploaded documents by parsed text content using Postgres FTS (english)."""
        base = (
            "SELECT id, project_id, thread_id, user_id, filename, filesize, mime_type, src_url, parsed_text, created_at, updated_at "
            "FROM uploaded_documents "
            "WHERE to_tsvector('english', COALESCE(parsed_text, '')) @@ plainto_tsquery('english', %s)"
        )
        params: list[Any] = [search_query]
        if not include_deleted:
            base += " AND deleted_at IS NULL"
        base += " ORDER BY created_at DESC"
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(base, params)
            return list(cur.fetchall())

    def soft_delete_uploaded_document(self, doc_id: str) -> bool:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE uploaded_documents SET deleted_at = now(), updated_at = now() WHERE id = %s AND deleted_at IS NULL",
                (doc_id,),
            )
            return cur.rowcount > 0

    # ==================== Utility Functions ====================

    def get_media_stats(self, project_id: str) -> Dict[str, Any]:
        """Get media statistics for a project."""
        with self._connect() as conn, conn.cursor() as cur:
            stats: Dict[str, Any] = {}

            cur.execute(
                "SELECT COUNT(*) AS count FROM generated_images WHERE project_id = %s AND deleted_at IS NULL",
                (project_id,),
            )
            stats["generated_images"] = cur.fetchone()["count"]

            cur.execute(
                "SELECT COUNT(*) AS count FROM uploaded_images WHERE project_id = %s AND deleted_at IS NULL",
                (project_id,),
            )
            stats["uploaded_images"] = cur.fetchone()["count"]

            cur.execute(
                "SELECT COUNT(*) AS count FROM generated_documents WHERE project_id = %s AND deleted_at IS NULL",
                (project_id,),
            )
            stats["generated_documents"] = cur.fetchone()["count"]

            cur.execute(
                "SELECT COUNT(*) AS count FROM uploaded_documents WHERE project_id = %s AND deleted_at IS NULL",
                (project_id,),
            )
            stats["uploaded_documents"] = cur.fetchone()["count"]

            return stats

    def cleanup_deleted_media(self, days_old: int = 30) -> int:
        """Permanently delete soft-deleted media older than `days_old` days."""
        total_deleted = 0
        interval_expr = f"{int(days_old)} days"
        with self._connect() as conn, conn.cursor() as cur:
            for table in (
                "generated_images",
                "uploaded_images",
                "generated_documents",
                "uploaded_documents",
            ):
                cur.execute(
                    f"DELETE FROM {table} WHERE deleted_at IS NOT NULL AND deleted_at < (now() - (%s)::interval)",
                    (interval_expr,),
                )
                total_deleted += cur.rowcount
        return total_deleted


# Singleton instance for the app
_media_db_instance: Optional[MediaDB] = None


def get_media_db(db_path: str = "guardian.db") -> MediaDB:
    """Get or create the singleton MediaDB instance.

    `db_path` is accepted for backward compatibility; if it is a Postgres DSN, it will be used.
    """
    global _media_db_instance
    if _media_db_instance is None:
        dsn_override = db_path if (db_path and db_path.startswith("postgres")) else None
        _media_db_instance = MediaDB(db_path=dsn_override)
    return _media_db_instance


def reset_media_db() -> None:
    """Reset the singleton MediaDB instance."""
    global _media_db_instance
    _media_db_instance = None
