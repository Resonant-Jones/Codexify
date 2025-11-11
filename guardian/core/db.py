"""GuardianDB: Thin adapter layer for Postgres persistence.

POSTGRES-ONLY: This module no longer creates tables or performs raw DDL.
All schema management is handled by Alembic migrations.

This adapter provides:
- SQLAlchemy session management
- High-level query utilities for common operations
- Backwards-compatible interface for existing API code

Schema is defined in guardian/db/models.py and managed via Alembic.
"""

import json
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import create_engine, text, func, inspect
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool

# Import ORM models
from guardian.db.models import (
    Base,
    Project,
    EventOutbox,
    MemoryEntry,
    ChatThread,
    ChatMessage,
    ConnectorConfig,
    ConnectorRun,
    RawDocument,
    SyncJob,
    AuditLog,
)


logger = logging.getLogger(__name__)
EXPECTED_TABLES = set(Base.metadata.tables.keys()) | {"alembic_version"}


def verify_schema_consistency(engine) -> None:
    """Validate that runtime schema matches Alembic-managed metadata."""
    insp = inspect(engine)
    logger.info("Verifying schema consistency...")
    existing_tables = set(insp.get_table_names())

    missing = sorted(EXPECTED_TABLES - existing_tables)
    if missing:
        raise RuntimeError(
            f"Expected database tables missing: {missing}. Apply latest Alembic migrations."
        )

    unexpected = sorted(existing_tables - EXPECTED_TABLES)
    if unexpected:
        logger.warning("Untracked schema objects detected: %s", unexpected)


class GuardianDB:
    """
    Postgres adapter for Guardian persistence.

    Provides a service layer over SQLAlchemy ORM models.
    No DDL creation - schema is managed by Alembic.
    """

    def __init__(self, db_url: str) -> None:
        """
        Initialize Postgres connection.

        Args:
            db_url: PostgreSQL connection string (postgresql://...)

        Raises:
            RuntimeError: If not a Postgres URL
        """
        if not db_url or not db_url.startswith('postgresql'):
            raise RuntimeError(
                f"GuardianDB is Postgres-only. Got: {db_url[:30]}..."
            )

        self.db_url = db_url
        self.engine = create_engine(
            db_url,
            poolclass=NullPool,  # Simple pool for now
            echo=False,
        )
        self.SessionLocal = sessionmaker(
            bind=self.engine,
            autocommit=False,
            autoflush=False,
        )

        verify_schema_consistency(self.engine)

        # Legacy flags (no-ops now, kept for compatibility)
        self._events_outbox_ready = True
        self._connector_tables_ready = True

    def get_session(self) -> Session:
        """Return a new SQLAlchemy session."""
        return self.SessionLocal()

    # =================================================================
    # Projects
    # =================================================================

    def ensure_project(self, name: str, description: str = "") -> int:
        """Create project if it doesn't exist, return ID."""
        with self.get_session() as session:
            project = session.query(Project).filter_by(name=name).first()
            if project:
                return project.id

            new_project = Project(name=name, description=description)
            session.add(new_project)
            session.commit()
            return new_project.id

    def create_project(self, name: str, description: str = "") -> int:
        """Create a new project."""
        with self.get_session() as session:
            project = Project(name=name, description=description)
            session.add(project)
            session.commit()
            return project.id

    def list_projects(self) -> List[Dict[str, Any]]:
        """List all projects."""
        with self.get_session() as session:
            projects = session.query(Project).all()
            return [
                {
                    "id": p.id,
                    "name": p.name,
                    "description": p.description,
                    "icon": p.icon,
                    "created_at": p.created_at,
                    "updated_at": p.updated_at,
                }
                for p in projects
            ]

    def update_project(
        self,
        project_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> None:
        """Update project fields."""
        with self.get_session() as session:
            project = session.query(Project).filter_by(id=project_id).first()
            if not project:
                raise ValueError(f"Project {project_id} not found")

            if name is not None:
                project.name = name
            if description is not None:
                project.description = description

            session.commit()

    def delete_project(self, project_id: int) -> bool:
        """Delete a project."""
        with self.get_session() as session:
            project = session.query(Project).filter_by(id=project_id).first()
            if not project:
                return False
            session.delete(project)
            session.commit()
            return True

    def eject_threads_from_project(self, project_id: int) -> None:
        """Move all threads from project to default (Loose Threads)."""
        with self.get_session() as session:
            session.query(ChatThread).filter_by(project_id=project_id).update(
                {"project_id": 1}  # Default "Loose Threads" project
            )
            session.commit()

    # =================================================================
    # Chat Threads
    # =================================================================

    def create_chat_thread(
        self,
        user_id: str,
        title: str = "New Chat",
        summary: str = "",
        project_id: Optional[int] = None,
        parent_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Create a new chat thread."""
        with self.get_session() as session:
            thread = ChatThread(
                user_id=user_id,
                title=title,
                summary=summary,
                project_id=project_id,
                parent_id=parent_id,
            )
            session.add(thread)
            session.commit()

            return {
                "id": thread.id,
                "user_id": thread.user_id,
                "title": thread.title,
                "summary": thread.summary,
                "project_id": thread.project_id,
                "parent_id": thread.parent_id,
                "archived_at": thread.archived_at.isoformat() if thread.archived_at else None,
                "created_at": thread.created_at.isoformat() if thread.created_at else None,
                "updated_at": thread.updated_at.isoformat() if thread.updated_at else None,
            }

    def ensure_chat_thread(
        self,
        thread_id: int,
        user_id: str,
        title: str = "New Chat",
        summary: str = "",
        project_id: Optional[int] = None,
    ) -> None:
        """Ensure thread exists, create if missing."""
        with self.get_session() as session:
            thread = session.query(ChatThread).filter_by(id=thread_id).first()
            if not thread:
                thread = ChatThread(
                    id=thread_id,
                    user_id=user_id,
                    title=title,
                    summary=summary,
                    project_id=project_id,
                )
                session.add(thread)
                session.commit()

    def list_chat_threads(self) -> List[Dict[str, Any]]:
        """List all chat threads."""
        with self.get_session() as session:
            threads = session.query(ChatThread).filter(
                ChatThread.archived_at.is_(None)
            ).order_by(ChatThread.updated_at.desc()).all()

            return [
                {
                    "id": t.id,
                    "user_id": t.user_id,
                    "title": t.title,
                    "summary": t.summary,
                    "project_id": t.project_id,
                    "parent_id": t.parent_id,
                    "archived_at": t.archived_at.isoformat() if t.archived_at else None,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                    "updated_at": t.updated_at.isoformat() if t.updated_at else None,
                }
                for t in threads
            ]

    def get_chat_thread(self, thread_id: int) -> Optional[Dict[str, Any]]:
        """Get a single thread by ID."""
        with self.get_session() as session:
            thread = session.query(ChatThread).filter_by(id=thread_id).first()
            if not thread:
                return None

            return {
                "id": thread.id,
                "user_id": thread.user_id,
                "title": thread.title,
                "summary": thread.summary,
                "project_id": thread.project_id,
                "parent_id": thread.parent_id,
                "archived_at": thread.archived_at.isoformat() if thread.archived_at else None,
                "created_at": thread.created_at.isoformat() if thread.created_at else None,
                "updated_at": thread.updated_at.isoformat() if thread.updated_at else None,
            }

    def get_recent_thread(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get most recent thread for user."""
        with self.get_session() as session:
            thread = session.query(ChatThread).filter_by(user_id=user_id).order_by(
                ChatThread.created_at.desc()
            ).first()

            if not thread:
                return None

            return self.get_chat_thread(thread.id)

    def update_thread(
        self,
        thread_id: int,
        title: Optional[str] = None,
        summary: Optional[str] = None,
        project_id: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """Update thread fields."""
        with self.get_session() as session:
            thread = session.query(ChatThread).filter_by(id=thread_id).first()
            if not thread:
                return None

            if title is not None:
                thread.title = title
            if summary is not None:
                thread.summary = summary
            if project_id is not None:
                thread.project_id = project_id

            session.commit()
            return self.get_chat_thread(thread_id)

    def archive_thread(self, thread_id: int) -> Optional[Dict[str, Any]]:
        """Archive a thread."""
        with self.get_session() as session:
            thread = session.query(ChatThread).filter_by(id=thread_id).first()
            if not thread:
                return None

            thread.archived_at = datetime.now(timezone.utc)
            session.commit()
            return self.get_chat_thread(thread_id)

    def unarchive_thread(self, thread_id: int) -> Optional[Dict[str, Any]]:
        """Unarchive a thread."""
        with self.get_session() as session:
            thread = session.query(ChatThread).filter_by(id=thread_id).first()
            if not thread:
                return None

            thread.archived_at = None
            session.commit()
            return self.get_chat_thread(thread_id)

    def delete_thread(self, thread_id: int, force: bool = False) -> bool:
        """Delete a thread (must be archived unless force=True)."""
        with self.get_session() as session:
            thread = session.query(ChatThread).filter_by(id=thread_id).first()
            if not thread:
                return False

            if not force and thread.archived_at is None:
                return False

            session.delete(thread)
            session.commit()
            return True

    def count_chat_threads(self) -> int:
        """Count total threads."""
        with self.get_session() as session:
            return session.query(ChatThread).count()

    def get_child_threads(self, parent_id: int) -> List[Dict[str, Any]]:
        """Get child threads of a parent."""
        with self.get_session() as session:
            threads = session.query(ChatThread).filter_by(parent_id=parent_id).all()
            return [
                {
                    "id": t.id,
                    "user_id": t.user_id,
                    "title": t.title,
                    "summary": t.summary,
                    "project_id": t.project_id,
                    "parent_id": t.parent_id,
                    "archived_at": t.archived_at.isoformat() if t.archived_at else None,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                    "updated_at": t.updated_at.isoformat() if t.updated_at else None,
                }
                for t in threads
            ]

    def get_thread_summary(self, thread_id: int) -> Optional[str]:
        """Get thread summary."""
        with self.get_session() as session:
            thread = session.query(ChatThread).filter_by(id=thread_id).first()
            return thread.summary if thread else None

    # =================================================================
    # Chat Messages
    # =================================================================

    def create_message(self, thread_id: int, role: str, content: str) -> int:
        """Create a new message in a thread."""
        with self.get_session() as session:
            message = ChatMessage(
                thread_id=thread_id,
                role=role,
                content=content,
            )
            session.add(message)
            session.commit()
            return message.id

    def list_messages(
        self,
        thread_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List messages in a thread."""
        with self.get_session() as session:
            messages = session.query(ChatMessage).filter_by(
                thread_id=thread_id
            ).order_by(
                ChatMessage.created_at.asc()
            ).limit(limit).offset(offset).all()

            return [
                {
                    "id": m.id,
                    "thread_id": m.thread_id,
                    "role": m.role,
                    "content": m.content,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in messages
            ]

    def count_messages(self, thread_id: int) -> int:
        """Count messages in a thread."""
        with self.get_session() as session:
            return session.query(ChatMessage).filter_by(thread_id=thread_id).count()

    def count_all_messages(self) -> int:
        """Count all messages across all threads."""
        with self.get_session() as session:
            return session.query(ChatMessage).count()

    def delete_message(self, thread_id: int, message_id: int) -> None:
        """Delete a message."""
        with self.get_session() as session:
            message = session.query(ChatMessage).filter_by(
                id=message_id,
                thread_id=thread_id
            ).first()
            if message:
                session.delete(message)
                session.commit()

    # =================================================================
    # Memory Entries
    # =================================================================

    def add_memory(
        self,
        user_id: str,
        silo: str,
        content: str,
        tags: str = "",
        pinned: bool = False,
    ) -> int:
        """Add a memory entry."""
        with self.get_session() as session:
            entry = MemoryEntry(
                user_id=user_id,
                silo=silo,
                content=content,
                tags=tags,
                pinned=pinned,
            )
            session.add(entry)
            session.commit()
            return entry.id

    def list_memories(
        self,
        silo: str,
        limit: int = 50,
        offset: int = 0,
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List memory entries in a silo, optionally filtered by user_id.

        Args:
            silo: Memory silo to query
            limit: Maximum number of entries to return
            offset: Number of entries to skip
            user_id: Optional user ID to filter by

        Returns:
            List of memory entries
        """
        with self.get_session() as session:
            query = session.query(MemoryEntry).filter_by(silo=silo)
            if user_id:
                query = query.filter_by(user_id=user_id)
            entries = query.order_by(
                MemoryEntry.updated_at.desc()
            ).limit(limit).offset(offset).all()

            return [
                {
                    "id": e.id,
                    "user_id": e.user_id,
                    "silo": e.silo,
                    "content": e.content,
                    "tags": e.tags,
                    "pinned": e.pinned,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                    "updated_at": e.updated_at.isoformat() if e.updated_at else None,
                }
                for e in entries
            ]

    def count_memories(self, silo: str, user_id: Optional[str] = None) -> int:
        """
        Count memory entries in a silo, optionally filtered by user_id.

        Args:
            silo: Memory silo to query
            user_id: Optional user ID to filter by

        Returns:
            Count of memory entries
        """
        with self.get_session() as session:
            query = session.query(MemoryEntry).filter_by(silo=silo)
            if user_id:
                query = query.filter_by(user_id=user_id)
            return query.count()

    def get_memory(self, entry_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a single memory entry by ID.

        Args:
            entry_id: Memory entry ID

        Returns:
            Memory entry dictionary or None if not found
        """
        with self.get_session() as session:
            entry = session.query(MemoryEntry).filter_by(id=entry_id).first()
            if not entry:
                return None
            return {
                "id": entry.id,
                "user_id": entry.user_id,
                "silo": entry.silo,
                "content": entry.content,
                "tags": entry.tags,
                "pinned": entry.pinned,
                "created_at": entry.created_at.isoformat() if entry.created_at else None,
                "updated_at": entry.updated_at.isoformat() if entry.updated_at else None,
            }

    def update_memory(
        self,
        entry_id: int,
        content: Optional[str] = None,
        tags: Optional[str] = None,
        pinned: Optional[bool] = None,
    ) -> None:
        """Update memory entry fields."""
        with self.get_session() as session:
            entry = session.query(MemoryEntry).filter_by(id=entry_id).first()
            if not entry:
                return

            if content is not None:
                entry.content = content
            if tags is not None:
                entry.tags = tags
            if pinned is not None:
                entry.pinned = pinned

            session.commit()

    def delete_memory(self, entry_id: int) -> None:
        """Delete a memory entry."""
        with self.get_session() as session:
            entry = session.query(MemoryEntry).filter_by(id=entry_id).first()
            if entry:
                session.delete(entry)
                session.commit()

    def prune_midterm(self, cutoff: str) -> int:
        """Prune old midterm memories."""
        with self.get_session() as session:
            count = session.query(MemoryEntry).filter(
                MemoryEntry.silo == "midterm",
                MemoryEntry.updated_at < cutoff
            ).delete()
            session.commit()
            return count

    # =================================================================
    # Connectors
    # =================================================================

    def list_connector_configs(self, type_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """List connector configurations."""
        with self.get_session() as session:
            query = session.query(ConnectorConfig)
            if type_filter:
                query = query.filter_by(type=type_filter)

            configs = query.all()
            return [
                {
                    "id": c.id,
                    "name": c.name,
                    "type": c.type,
                    "settings": c.config,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                    "updated_at": c.updated_at.isoformat() if c.updated_at else None,
                }
                for c in configs
            ]

    def list_connector_configs_with_last_run(self) -> List[Dict[str, Any]]:
        """List connector configs with last run info."""
        configs = self.list_connector_configs()
        for cfg in configs:
            cfg["last_run"] = self.get_last_connector_run(cfg["id"])
        return configs

    def get_connector_config(self, name: str) -> Optional[Dict[str, Any]]:
        """Get connector config by name."""
        with self.get_session() as session:
            config = session.query(ConnectorConfig).filter_by(name=name).first()
            if not config:
                return None

            return {
                "id": config.id,
                "name": config.name,
                "type": config.type,
                "settings": config.config,
                "created_at": config.created_at.isoformat() if config.created_at else None,
                "updated_at": config.updated_at.isoformat() if config.updated_at else None,
            }

    def create_connector_config(
        self,
        name: str,
        type_: str,
        settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new connector config."""
        with self.get_session() as session:
            config = ConnectorConfig(
                name=name,
                type=type_,
                config=settings,
            )
            session.add(config)
            session.commit()

            return {
                "id": config.id,
                "name": config.name,
                "type": config.type,
                "settings": config.config,
                "created_at": config.created_at.isoformat() if config.created_at else None,
                "updated_at": config.updated_at.isoformat() if config.updated_at else None,
            }

    def update_connector_config(
        self,
        name: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update connector config settings."""
        with self.get_session() as session:
            connector = session.query(ConnectorConfig).filter_by(name=name).first()
            if not connector:
                raise ValueError(f"Connector {name} not found")

            connector.config = config
            session.commit()

            return {
                "id": connector.id,
                "name": connector.name,
                "type": connector.type,
                "settings": connector.config,
                "created_at": connector.created_at.isoformat() if connector.created_at else None,
                "updated_at": connector.updated_at.isoformat() if connector.updated_at else None,
            }

    def create_connector_run(
        self,
        config_id: int,
        status: str,
        started_at: str,
    ) -> Dict[str, Any]:
        """Create a connector run record."""
        with self.get_session() as session:
            run = ConnectorRun(
                config_id=config_id,
                status=status,
                started_at=started_at,
            )
            session.add(run)
            session.commit()

            return {
                "id": run.id,
                "config_id": run.config_id,
                "status": run.status,
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "finished_at": run.finished_at.isoformat() if run.finished_at else None,
                "error": run.error,
                "document_count": run.document_count,
            }

    def complete_connector_run(
        self,
        run_id: int,
        status: str,
        finished_at: str,
        error: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Complete a connector run."""
        with self.get_session() as session:
            run = session.query(ConnectorRun).filter_by(id=run_id).first()
            if not run:
                raise ValueError(f"Run {run_id} not found")

            run.status = status
            run.finished_at = finished_at
            run.error = error
            session.commit()

            return {
                "id": run.id,
                "config_id": run.config_id,
                "status": run.status,
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "finished_at": run.finished_at.isoformat() if run.finished_at else None,
                "error": run.error,
                "document_count": run.document_count,
            }

    def get_last_connector_run(self, config_id: int) -> Optional[Dict[str, Any]]:
        """Get last run for a connector."""
        with self.get_session() as session:
            run = session.query(ConnectorRun).filter_by(
                config_id=config_id
            ).order_by(ConnectorRun.started_at.desc()).first()

            if not run:
                return None

            return {
                "id": run.id,
                "config_id": run.config_id,
                "status": run.status,
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "finished_at": run.finished_at.isoformat() if run.finished_at else None,
                "error": run.error,
                "document_count": run.document_count,
            }

    def upsert_raw_documents(
        self,
        config_id: int,
        documents: List[Dict[str, Any]]
    ) -> None:
        """Upsert raw documents from a connector."""
        with self.get_session() as session:
            for doc in documents:
                external_id = doc.get("external_id", doc.get("id"))

                # Check if exists
                existing = session.query(RawDocument).filter_by(
                    config_id=config_id,
                    external_id=str(external_id)
                ).first()

                if existing:
                    existing.payload = doc
                else:
                    new_doc = RawDocument(
                        config_id=config_id,
                        external_id=str(external_id),
                        payload=doc,
                    )
                    session.add(new_doc)

            session.commit()

    # =================================================================
    # Sync Jobs
    # =================================================================

    def ensure_sync_job_support(self) -> None:
        """No-op: Tables created by Alembic."""
        pass

    # =================================================================
    # Audit Log
    # =================================================================

    def write_audit_log(
        self,
        event: str,
        entity: str,
        entity_id: str,
        user_id: str,
    ) -> None:
        """Write an audit log entry."""
        try:
            with self.get_session() as session:
                log_entry = AuditLog(
                    event=event,
                    entity=entity,
                    entity_id=entity_id,
                    user_id=user_id,
                )
                session.add(log_entry)
                session.commit()
        except Exception:
            # Don't crash app if audit logging fails
            pass

    # =================================================================
    # Utility / Compatibility
    # =================================================================

    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists."""
        with self.get_session() as session:
            result = session.execute(
                text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_schema = 'public'
                        AND table_name = :table_name
                    )
                """),
                {"table_name": table_name}
            )
            return result.scalar()

    def list_threads(
        self,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List threads with optional filters (legacy API compat)."""
        with self.get_session() as session:
            query = session.query(ChatThread)

            if user_id:
                query = query.filter_by(user_id=user_id)
            if project_id:
                query = query.filter_by(project_id=int(project_id))

            threads = query.all()
            return [
                {
                    "id": t.id,
                    "user_id": t.user_id,
                    "title": t.title,
                    "summary": t.summary,
                    "project_id": t.project_id,
                    "parent_id": t.parent_id,
                    "archived_at": t.archived_at.isoformat() if t.archived_at else None,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                    "updated_at": t.updated_at.isoformat() if t.updated_at else None,
                }
                for t in threads
            ]

    def get_thread(self, thread_id: int) -> Optional[tuple]:
        """Get thread as tuple (legacy API compat)."""
        thread_dict = self.get_chat_thread(thread_id)
        if not thread_dict:
            return None

        return (
            thread_dict["id"],
            thread_dict["parent_id"],
            None,  # session_id (deprecated)
            thread_dict["summary"],
            thread_dict["created_at"],
            thread_dict["user_id"],
            thread_dict["project_id"],
        )

    def create_thread(
        self,
        parent_thread_id: Optional[int] = None,
        session_id: Optional[str] = None,
        summary: str = "",
        user_id: str = "default",
        project_id: Optional[str] = None,
    ) -> int:
        """Create thread (legacy API compat)."""
        proj_id = int(project_id) if project_id else None
        thread = self.create_chat_thread(
            user_id=user_id,
            title="New Chat",
            summary=summary,
            project_id=proj_id,
            parent_id=parent_thread_id,
        )
        return thread["id"]

    # Stubs for methods that may be called but are no longer needed
    def search_memory(
        self,
        query: str,
        limit: int,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """TODO: Implement full-text search over memory entries."""
        return []

    def search_github_memory(
        self,
        query: str,
        repo: Optional[str] = None,
        limit: int = 20,
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """TODO: Implement GitHub memory search."""
        return []

    def insert_memory_event(
        self,
        content: str,
        tag: Optional[str],
        agent: str,
        type_: str,
        parent_id: Optional[int],
        user_id: Optional[str] = None,
    ) -> None:
        """TODO: Implement memory event logging."""
        pass

    def history_entries(
        self,
        limit: int,
        tag: Optional[str] = None,
        agent: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """TODO: Implement history query."""
        return []
