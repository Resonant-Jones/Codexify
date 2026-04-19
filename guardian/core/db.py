"""GuardianDB Postgres adapter.

The implementation in this module targets PostgreSQL via SQLAlchemy ORM
models. SQLite support has been removed; all persistence is expected to
flow through Postgres tables managed by Alembic migrations.
"""

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Any, Dict, List, Optional

from sqlalchemy import create_engine, func, inspect, or_, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from guardian.core.default_project import resolve_project_id_or_default

# Import ORM models
from guardian.db.models import (
    AuditLog,
    Base,
    ChatMessage,
    ChatThread,
    ConnectorConfig,
    ConnectorRun,
    EventOutbox,
    MemoryEntry,
    OAuthConnection,
    PersonalFact,
    PersonalFactEvidence,
    PersonalFactRevision,
    Project,
    RawDocument,
    SyncJob,
    ThreadMove,
)

logger = logging.getLogger(__name__)
EXPECTED_TABLES = set(Base.metadata.tables.keys()) | {"alembic_version"}
_SCHEMA_VERIFIED_URLS: set[str] = set()
_SCHEMA_VERIFY_LOCK = Lock()
_GUARDIAN_DB_CACHE: dict[str, "GuardianDB"] = {}
_GUARDIAN_DB_CACHE_LOCK = Lock()
_DEFAULT_USER_ID = "local"


def _default_user_id() -> str:
    return _DEFAULT_USER_ID


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


class _PostgresGuardianDB:
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
        if not db_url or not db_url.startswith("postgresql"):
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

        with _SCHEMA_VERIFY_LOCK:
            should_verify = db_url not in _SCHEMA_VERIFIED_URLS

        if should_verify:
            verify_schema_consistency(self.engine)
            with _SCHEMA_VERIFY_LOCK:
                _SCHEMA_VERIFIED_URLS.add(db_url)

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

            new_project = Project(
                user_id=_default_user_id(),
                name=name,
                description=description,
            )
            session.add(new_project)
            session.commit()
            return new_project.id

    def create_project(
        self, name: str, description: str = "", user_id: str | None = None
    ) -> int:
        """Create a new project."""
        with self.get_session() as session:
            resolved_user_id = (
                str(user_id or _default_user_id()).strip() or _default_user_id()
            )
            project = Project(
                user_id=resolved_user_id,
                name=name,
                description=description,
            )
            session.add(project)
            session.commit()
            return project.id

    def ensure_default_project(self) -> int:
        """Ensure and return the canonical default project id."""
        from guardian.core.default_project import canonicalize_default_project

        project_id = canonicalize_default_project(self, logger=logger)
        if project_id is None:
            raise RuntimeError("Unable to resolve default project")
        return project_id

    def get_project_identity_depth(self, project_id: Optional[int]) -> str:
        if not project_id:
            return "light"
        with self.get_session() as session:
            project = session.query(Project).filter_by(id=project_id).first()
            if not project:
                return "light"
            depth = str(getattr(project, "identity_depth", "light")).lower()
            return "deep" if depth == "deep" else "light"

    def list_projects(self) -> List[Dict[str, Any]]:
        """List all projects."""
        with self.get_session() as session:
            projects = session.query(Project).all()
            return [
                {
                    "id": p.id,
                    "user_id": p.user_id,
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
        """Move all threads from project to the canonical default project."""
        default_project_id = self.ensure_default_project()
        if int(project_id) == int(default_project_id):
            return
        with self.get_session() as session:
            session.query(ChatThread).filter_by(project_id=project_id).update(
                {"project_id": default_project_id}
            )
            session.commit()

    # =================================================================
    # Chat Threads
    # =================================================================

    def _thread_to_dict(self, thread: ChatThread) -> Dict[str, Any]:
        """Serialize a chat thread with its durable config surface."""
        return {
            "id": thread.id,
            "user_id": thread.user_id,
            "title": thread.title,
            "summary": thread.summary,
            "project_id": thread.project_id,
            "project_name": thread.project.name if thread.project else None,
            "last_interaction_at": (
                thread.last_interaction_at.isoformat()
                if thread.last_interaction_at
                else None
            ),
            "parent_id": thread.parent_id,
            "active_profile_id": thread.active_profile_id,
            "thread_config": thread.thread_config,
            "is_diary": bool(thread.is_diary),
            "diary_mode": bool(thread.diary_mode),
            "exclude_from_identity": bool(thread.exclude_from_identity),
            "modeling_excluded": bool(thread.modeling_excluded),
            "archived_at": (
                thread.archived_at.isoformat() if thread.archived_at else None
            ),
            "created_at": (
                thread.created_at.isoformat() if thread.created_at else None
            ),
            "updated_at": (
                thread.updated_at.isoformat() if thread.updated_at else None
            ),
        }

    def create_chat_thread(
        self,
        user_id: str,
        title: str = "New Chat",
        summary: str = "",
        project_id: Optional[int] = None,
        parent_id: Optional[int] = None,
        active_profile_id: Optional[str] = None,
        diary_mode: bool = False,
        modeling_excluded: bool = False,
    ) -> Dict[str, Any]:
        """Create a new chat thread."""
        resolved_project_id = resolve_project_id_or_default(
            self, project_id, logger=logger
        )
        with self.get_session() as session:
            thread = ChatThread(
                user_id=user_id,
                title=title,
                summary=summary,
                project_id=resolved_project_id,
                parent_id=parent_id,
                active_profile_id=active_profile_id,
                is_diary=diary_mode,
                diary_mode=diary_mode,
                exclude_from_identity=modeling_excluded,
                modeling_excluded=modeling_excluded,
            )
            session.add(thread)
            session.commit()

            return self._thread_to_dict(thread)

    def ensure_chat_thread(
        self,
        thread_id: int,
        user_id: str,
        title: str = "New Chat",
        summary: str = "",
        project_id: Optional[int] = None,
        is_diary: bool = False,
        exclude_from_identity: bool = False,
        diary_mode: Optional[bool] = None,
        modeling_excluded: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Ensure thread exists, create if missing."""
        diary_flag = is_diary if diary_mode is None else diary_mode
        modeling_flag = (
            exclude_from_identity
            if modeling_excluded is None
            else modeling_excluded
        )
        resolved_project_id = resolve_project_id_or_default(
            self, project_id, logger=logger
        )
        with self.get_session() as session:
            thread = session.query(ChatThread).filter_by(id=thread_id).first()
            if thread:
                return self._thread_to_dict(thread)
            thread = ChatThread(
                id=thread_id,
                user_id=user_id,
                title=title,
                summary=summary,
                project_id=resolved_project_id,
                is_diary=diary_flag,
                diary_mode=diary_flag,
                exclude_from_identity=modeling_flag,
                modeling_excluded=modeling_flag,
            )
            session.add(thread)
            session.commit()
            return self._thread_to_dict(thread)

    def list_chat_threads(self) -> List[Dict[str, Any]]:
        """List all chat threads."""
        with self.get_session() as session:
            threads = (
                session.query(ChatThread)
                .filter(ChatThread.archived_at.is_(None))
                .order_by(
                    func.coalesce(
                        ChatThread.last_interaction_at,
                        ChatThread.updated_at,
                        ChatThread.created_at,
                    ).desc(),
                    ChatThread.id.desc(),
                )
                .all()
            )

            return [self._thread_to_dict(t) for t in threads]

    def get_chat_thread(self, thread_id: int) -> Optional[Dict[str, Any]]:
        """Get a single thread by ID."""
        with self.get_session() as session:
            thread = session.query(ChatThread).filter_by(id=thread_id).first()
            if not thread:
                return None

            return self._thread_to_dict(thread)

    def get_recent_thread(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get most recent thread for user."""
        with self.get_session() as session:
            thread = (
                session.query(ChatThread)
                .filter_by(user_id=user_id)
                .order_by(
                    func.coalesce(
                        ChatThread.last_interaction_at,
                        ChatThread.updated_at,
                        ChatThread.created_at,
                    ).desc(),
                    ChatThread.id.desc(),
                )
                .first()
            )

            if not thread:
                return None

            return self.get_chat_thread(thread.id)

    def update_thread(
        self,
        thread_id: int,
        title: Optional[str] = None,
        summary: Optional[str] = None,
        project_id: Optional[int] = None,
        project_id_set: bool = False,
        active_profile_id: Optional[str] = None,
        active_profile_id_set: bool = False,
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
            if project_id_set:
                thread.project_id = resolve_project_id_or_default(
                    self, project_id, logger=logger
                )
            if active_profile_id_set:
                thread.active_profile_id = active_profile_id

            session.commit()
            return self.get_chat_thread(thread_id)

    def set_thread_active_profile_id(
        self, thread_id: int, profile_id: Optional[str]
    ) -> bool:
        with self.get_session() as session:
            thread = session.query(ChatThread).filter_by(id=thread_id).first()
            if not thread:
                return False
            thread.active_profile_id = profile_id
            session.commit()
            return True

    def update_thread_metadata(
        self, thread_id: int, metadata: Dict[str, Any]
    ) -> bool:
        # SQL path keeps this working even if ORM model doesn't map `metadata`.
        payload = metadata or {}
        with self.get_session() as session:
            result = session.execute(
                text(
                    """
                    UPDATE chat_threads
                    SET metadata = CAST(:metadata AS JSONB), updated_at = now()
                    WHERE id = :thread_id
                    """
                ),
                {
                    "metadata": json.dumps(payload),
                    "thread_id": thread_id,
                },
            )
            session.commit()
            return bool(result.rowcount)

    def set_thread_profile_overrides(
        self, thread_id: int, overrides: Dict[str, Any]
    ) -> bool:
        with self.get_session() as session:
            row = session.execute(
                text("SELECT metadata FROM chat_threads WHERE id = :thread_id"),
                {"thread_id": thread_id},
            ).fetchone()
            if row is None:
                return False
            metadata = row[0] or {}
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except Exception:
                    metadata = {}
            if not isinstance(metadata, dict):
                metadata = {}
            metadata["profile_overrides"] = dict(overrides or {})
            result = session.execute(
                text(
                    """
                    UPDATE chat_threads
                    SET metadata = CAST(:metadata AS JSONB), updated_at = now()
                    WHERE id = :thread_id
                    """
                ),
                {
                    "metadata": json.dumps(metadata),
                    "thread_id": thread_id,
                },
            )
            session.commit()
            return bool(result.rowcount)

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
            threads = (
                session.query(ChatThread).filter_by(parent_id=parent_id).all()
            )
            return [self._thread_to_dict(t) for t in threads]

    def get_thread_summary(self, thread_id: int) -> Optional[str]:
        """Get thread summary."""
        with self.get_session() as session:
            thread = session.query(ChatThread).filter_by(id=thread_id).first()
            return thread.summary if thread else None

    # =================================================================
    # Chat Messages
    # =================================================================

    def create_message(
        self,
        thread_id: int,
        role: str,
        content: str,
        *,
        kind: str = "chat",
        event_at: Optional[datetime] = None,
        extra_meta: Optional[dict] = None,
        user_id: str | None = None,
    ) -> int:
        """Create a new message in a thread."""
        now = datetime.now(timezone.utc)
        with self.get_session() as session:
            thread = session.query(ChatThread).filter_by(id=thread_id).first()
            resolved_user_id = (
                str(
                    user_id
                    or getattr(thread, "user_id", "")
                    or _default_user_id()
                ).strip()
                or _default_user_id()
            )
            message = ChatMessage(
                thread_id=thread_id,
                user_id=resolved_user_id,
                role=role,
                content=content,
                kind=kind,
                event_at=event_at or datetime.now(timezone.utc),
                extra_meta=extra_meta or {},
            )
            session.add(message)
            if thread is not None:
                thread.updated_at = now
                thread.last_interaction_at = now
            session.commit()
            return message.id

    def record_thread_move(
        self,
        thread_id: int,
        *,
        from_project_id: int | None,
        to_project_id: int,
        user_id: str,
    ) -> dict[str, Any]:
        """Insert an explicit thread move audit row."""
        with self.get_session() as session:
            move = ThreadMove(
                thread_id=thread_id,
                from_project_id=from_project_id,
                to_project_id=to_project_id,
                user_id=user_id,
            )
            session.add(move)
            session.commit()
            return {
                "id": move.id,
                "thread_id": move.thread_id,
                "from_project_id": move.from_project_id,
                "to_project_id": move.to_project_id,
                "user_id": move.user_id,
                "timestamp": (
                    move.timestamp.isoformat() if move.timestamp else None
                ),
            }

    def list_messages(
        self,
        thread_id: int,
        limit: int = 50,
        offset: int = 0,
        exclude_kinds: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """List messages in a thread."""
        with self.get_session() as session:
            query = session.query(ChatMessage).filter_by(thread_id=thread_id)
            if exclude_kinds:
                query = query.filter(
                    or_(
                        ChatMessage.kind.is_(None),
                        ChatMessage.kind.notin_(exclude_kinds),
                    )
                )
            messages = (
                query.order_by(ChatMessage.event_at.asc(), ChatMessage.id.asc())
                .limit(limit)
                .offset(offset)
                .all()
            )

            return [
                {
                    "id": m.id,
                    "thread_id": m.thread_id,
                    "role": m.role,
                    "content": m.content,
                    "event_at": m.event_at.isoformat() if m.event_at else None,
                    "kind": m.kind,
                    "extra_meta": m.extra_meta,
                    "created_at": m.created_at.isoformat()
                    if m.created_at
                    else None,
                }
                for m in messages
            ]

    def list_messages_by_date_range(
        self,
        thread_id: int,
        start_date: str,
        end_date: Optional[str] = None,
        limit: int = 200,
    ) -> List[Dict[str, Any]]:
        """List messages in a thread ordered by event timestamp."""
        from guardian.utils.datetime import parse_ts

        with self.get_session() as session:
            query = session.query(ChatMessage).filter_by(thread_id=thread_id)
            start_dt = parse_ts(start_date)
            query = query.filter(ChatMessage.event_at >= start_dt)
            if end_date:
                end_dt = parse_ts(end_date)
                query = query.filter(ChatMessage.event_at <= end_dt)
            messages = (
                query.order_by(ChatMessage.event_at.asc(), ChatMessage.id.asc())
                .limit(limit)
                .all()
            )

            return [
                {
                    "id": m.id,
                    "thread_id": m.thread_id,
                    "role": m.role,
                    "content": m.content,
                    "event_at": m.event_at.isoformat() if m.event_at else None,
                    "kind": m.kind,
                    "extra_meta": m.extra_meta,
                    "created_at": m.created_at.isoformat()
                    if m.created_at
                    else None,
                }
                for m in messages
            ]

    def count_messages(self, thread_id: int) -> int:
        """Count messages in a thread."""
        with self.get_session() as session:
            return (
                session.query(ChatMessage)
                .filter_by(thread_id=thread_id)
                .count()
            )

    def count_all_messages(self) -> int:
        """Count all messages across all threads."""
        with self.get_session() as session:
            return session.query(ChatMessage).count()

    def delete_message(self, thread_id: int, message_id: int) -> None:
        """Delete a message."""
        with self.get_session() as session:
            message = (
                session.query(ChatMessage)
                .filter_by(id=message_id, thread_id=thread_id)
                .first()
            )
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
            entries = (
                query.order_by(MemoryEntry.updated_at.desc())
                .limit(limit)
                .offset(offset)
                .all()
            )

            return [
                {
                    "id": e.id,
                    "user_id": e.user_id,
                    "silo": e.silo,
                    "content": e.content,
                    "tags": e.tags,
                    "pinned": e.pinned,
                    "created_at": e.created_at.isoformat()
                    if e.created_at
                    else None,
                    "updated_at": e.updated_at.isoformat()
                    if e.updated_at
                    else None,
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
                "created_at": (
                    entry.created_at.isoformat() if entry.created_at else None
                ),
                "updated_at": (
                    entry.updated_at.isoformat() if entry.updated_at else None
                ),
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
            count = (
                session.query(MemoryEntry)
                .filter(
                    MemoryEntry.silo == "midterm",
                    MemoryEntry.updated_at < cutoff,
                )
                .delete()
            )
            session.commit()
            return count

    # =================================================================
    # Personal Facts
    # =================================================================

    def _fact_to_dict(self, fact: PersonalFact) -> Dict[str, Any]:
        return {
            "id": fact.id,
            "user_id": fact.user_id,
            "key": fact.key,
            "value": fact.value,
            "status": fact.status,
            "confidence": fact.confidence,
            "is_active": fact.is_active,
            "last_confirmed_at": (
                fact.last_confirmed_at.isoformat()
                if fact.last_confirmed_at
                else None
            ),
            "created_at": fact.created_at.isoformat()
            if fact.created_at
            else None,
            "updated_at": fact.updated_at.isoformat()
            if fact.updated_at
            else None,
        }

    def _evidence_to_dict(
        self, evidence: PersonalFactEvidence
    ) -> Dict[str, Any]:
        return {
            "id": evidence.id,
            "fact_id": evidence.fact_id,
            "source_message_id": evidence.source_message_id,
            "excerpt": evidence.excerpt,
            "modality": evidence.modality,
            "confidence": evidence.confidence,
            "source_type": evidence.source_type,
            "evidence_meta": evidence.evidence_meta,
            "created_at": (
                evidence.created_at.isoformat() if evidence.created_at else None
            ),
        }

    def _revision_to_dict(
        self, revision: PersonalFactRevision
    ) -> Dict[str, Any]:
        return {
            "id": revision.id,
            "fact_id": revision.fact_id,
            "actor": revision.actor,
            "action": revision.action,
            "field_changed": revision.field_changed,
            "old_value": revision.old_value,
            "new_value": revision.new_value,
            "reason": revision.reason,
            "created_at": (
                revision.created_at.isoformat() if revision.created_at else None
            ),
        }

    def list_facts(
        self,
        user_id: str,
        status: Optional[str] = None,
        active_only: bool = True,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """List personal facts for a user."""
        with self.get_session() as session:
            query = session.query(PersonalFact).filter_by(user_id=user_id)
            if status:
                query = query.filter_by(status=status)
            if active_only:
                query = query.filter_by(is_active=True)
            facts = (
                query.order_by(PersonalFact.updated_at.desc())
                .limit(limit)
                .all()
            )
            return [self._fact_to_dict(fact) for fact in facts]

    def create_fact(
        self,
        user_id: str,
        key: str,
        value: str,
        status: str = "candidate",
        confidence: float = 0.5,
    ) -> int:
        """Create a personal fact."""
        with self.get_session() as session:
            fact = PersonalFact(
                user_id=user_id,
                key=key,
                value=value,
                status=status,
                confidence=confidence,
                is_active=True,
            )
            session.add(fact)
            session.commit()
            return fact.id

    def get_fact(self, fact_id: int) -> Optional[Dict[str, Any]]:
        """Fetch a fact by id."""
        with self.get_session() as session:
            fact = session.query(PersonalFact).filter_by(id=fact_id).first()
            if not fact:
                return None
            return self._fact_to_dict(fact)

    def _add_fact_revision(
        self,
        session: Session,
        *,
        fact_id: int,
        actor: str,
        action: str,
        field_changed: Optional[str] = None,
        old_value: Optional[str] = None,
        new_value: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> None:
        revision = PersonalFactRevision(
            fact_id=fact_id,
            actor=actor,
            action=action,
            field_changed=field_changed,
            old_value=old_value,
            new_value=new_value,
            reason=reason,
        )
        session.add(revision)

    def update_fact(
        self,
        fact_id: int,
        *,
        value: Optional[str] = None,
        status: Optional[str] = None,
        confidence: Optional[float] = None,
        actor: str = "system",
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update a personal fact and record revisions."""
        with self.get_session() as session:
            fact = session.query(PersonalFact).filter_by(id=fact_id).first()
            if not fact:
                raise ValueError(f"Fact {fact_id} not found")

            if value is not None and value != fact.value:
                self._add_fact_revision(
                    session,
                    fact_id=fact.id,
                    actor=actor,
                    action="value_updated",
                    field_changed="value",
                    old_value=fact.value,
                    new_value=value,
                    reason=reason,
                )
                fact.value = value

            if status is not None and status != fact.status:
                self._add_fact_revision(
                    session,
                    fact_id=fact.id,
                    actor=actor,
                    action="status_updated",
                    field_changed="status",
                    old_value=fact.status,
                    new_value=status,
                    reason=reason,
                )
                fact.status = status
                if status == "verified":
                    fact.last_confirmed_at = datetime.now(timezone.utc)

            if confidence is not None and confidence != fact.confidence:
                self._add_fact_revision(
                    session,
                    fact_id=fact.id,
                    actor=actor,
                    action="confidence_updated",
                    field_changed="confidence",
                    old_value=str(fact.confidence),
                    new_value=str(confidence),
                    reason=reason,
                )
                fact.confidence = confidence

            fact.updated_at = datetime.now(timezone.utc)
            session.add(fact)
            session.commit()
            return self._fact_to_dict(fact)

    def deactivate_fact(
        self,
        fact_id: int,
        *,
        actor: str = "system",
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Archive a fact and mark it inactive."""
        with self.get_session() as session:
            fact = session.query(PersonalFact).filter_by(id=fact_id).first()
            if not fact:
                raise ValueError(f"Fact {fact_id} not found")

            self._add_fact_revision(
                session,
                fact_id=fact.id,
                actor=actor,
                action="deactivated",
                field_changed="is_active",
                old_value=str(fact.is_active),
                new_value="False",
                reason=reason,
            )
            fact.is_active = False
            fact.status = "archived"
            fact.updated_at = datetime.now(timezone.utc)
            session.add(fact)
            session.commit()
            return self._fact_to_dict(fact)

    def list_fact_evidence(self, fact_id: int) -> List[Dict[str, Any]]:
        """List evidence rows for a fact."""
        with self.get_session() as session:
            evidence = (
                session.query(PersonalFactEvidence)
                .filter_by(fact_id=fact_id)
                .order_by(PersonalFactEvidence.created_at.asc())
                .all()
            )
            return [self._evidence_to_dict(row) for row in evidence]

    def add_fact_evidence(
        self,
        fact_id: int,
        source_message_id: Optional[int],
        excerpt: Optional[str],
        *,
        modality: str = "text",
        confidence: float = 0.5,
        source_type: str = "runtime_extraction",
        evidence_meta: Optional[dict] = None,
    ) -> int:
        """Add evidence to a fact."""
        with self.get_session() as session:
            evidence = PersonalFactEvidence(
                fact_id=fact_id,
                source_message_id=source_message_id,
                excerpt=excerpt,
                modality=modality,
                confidence=confidence,
                source_type=source_type,
                evidence_meta=evidence_meta or {},
            )
            session.add(evidence)
            session.commit()
            return evidence.id

    def get_fact_revisions(self, fact_id: int) -> List[Dict[str, Any]]:
        """Fetch revision history for a fact."""
        with self.get_session() as session:
            revisions = (
                session.query(PersonalFactRevision)
                .filter_by(fact_id=fact_id)
                .order_by(PersonalFactRevision.created_at.desc())
                .all()
            )
            return [self._revision_to_dict(row) for row in revisions]

    # =================================================================
    # Connectors
    # =================================================================

    def list_connector_configs(
        self, type_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
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
                    "created_at": c.created_at.isoformat()
                    if c.created_at
                    else None,
                    "updated_at": c.updated_at.isoformat()
                    if c.updated_at
                    else None,
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
                "created_at": (
                    config.created_at.isoformat() if config.created_at else None
                ),
                "updated_at": (
                    config.updated_at.isoformat() if config.updated_at else None
                ),
            }

    def create_connector_config(
        self, name: str, type_: str, settings: Dict[str, Any]
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
                "created_at": (
                    config.created_at.isoformat() if config.created_at else None
                ),
                "updated_at": (
                    config.updated_at.isoformat() if config.updated_at else None
                ),
            }

    def update_connector_config(
        self, name: str, config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update connector config settings."""
        with self.get_session() as session:
            connector = (
                session.query(ConnectorConfig).filter_by(name=name).first()
            )
            if not connector:
                raise ValueError(f"Connector {name} not found")

            connector.config = config
            session.commit()

            return {
                "id": connector.id,
                "name": connector.name,
                "type": connector.type,
                "settings": connector.config,
                "created_at": (
                    connector.created_at.isoformat()
                    if connector.created_at
                    else None
                ),
                "updated_at": (
                    connector.updated_at.isoformat()
                    if connector.updated_at
                    else None
                ),
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
                "started_at": run.started_at.isoformat()
                if run.started_at
                else None,
                "finished_at": run.finished_at.isoformat()
                if run.finished_at
                else None,
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
                "started_at": run.started_at.isoformat()
                if run.started_at
                else None,
                "finished_at": run.finished_at.isoformat()
                if run.finished_at
                else None,
                "error": run.error,
                "document_count": run.document_count,
            }

    def get_last_connector_run(
        self, config_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get last run for a connector."""
        with self.get_session() as session:
            run = (
                session.query(ConnectorRun)
                .filter_by(config_id=config_id)
                .order_by(ConnectorRun.started_at.desc())
                .first()
            )

            if not run:
                return None

            return {
                "id": run.id,
                "config_id": run.config_id,
                "status": run.status,
                "started_at": run.started_at.isoformat()
                if run.started_at
                else None,
                "finished_at": run.finished_at.isoformat()
                if run.finished_at
                else None,
                "error": run.error,
                "document_count": run.document_count,
            }

    def upsert_raw_documents(
        self, config_id: int, documents: List[Dict[str, Any]]
    ) -> None:
        """Upsert raw documents from a connector."""
        with self.get_session() as session:
            for doc in documents:
                external_id = doc.get("external_id", doc.get("id"))

                # Check if exists
                existing = (
                    session.query(RawDocument)
                    .filter_by(
                        config_id=config_id, external_id=str(external_id)
                    )
                    .first()
                )

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

    def _oauth_connection_to_dict(self, row: OAuthConnection) -> Dict[str, Any]:
        return {
            "id": row.id,
            "user_id": row.user_id,
            "provider": row.provider,
            "mode": row.mode,
            "scopes": list(row.scopes or []),
            "status": row.status,
            "encrypted_refresh_token": row.encrypted_refresh_token,
            "encrypted_access_token": row.encrypted_access_token,
            "relay_grant_id": row.relay_grant_id,
            "expires_at": row.expires_at,
            "last_refresh_at": row.last_refresh_at,
            "last_error": row.last_error,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    def upsert_oauth_connection(
        self,
        *,
        user_id: str,
        provider: str,
        mode: str,
        scopes: List[str] | None,
        status: str,
        encrypted_refresh_token: str | None = None,
        encrypted_access_token: str | None = None,
        relay_grant_id: str | None = None,
        expires_at: datetime | None = None,
        last_refresh_at: datetime | None = None,
        last_error: str | None = None,
    ) -> Dict[str, Any]:
        """Create/update OAuth connection state."""
        with self.get_session() as session:
            row = (
                session.query(OAuthConnection)
                .filter_by(user_id=user_id, provider=provider, mode=mode)
                .first()
            )
            if not row:
                row = OAuthConnection(
                    user_id=user_id,
                    provider=provider,
                    mode=mode,
                )
                session.add(row)

            row.scopes = list(scopes or [])
            row.status = status
            row.encrypted_refresh_token = encrypted_refresh_token
            row.encrypted_access_token = encrypted_access_token
            row.relay_grant_id = relay_grant_id
            row.expires_at = expires_at
            if last_refresh_at is not None:
                row.last_refresh_at = last_refresh_at
            row.last_error = last_error
            session.commit()
            session.refresh(row)
            return self._oauth_connection_to_dict(row)

    def get_oauth_connection(
        self,
        *,
        user_id: str,
        provider: str,
        mode: str | None = None,
    ) -> Optional[Dict[str, Any]]:
        """Return the most recent OAuth connection row for a user/provider."""
        with self.get_session() as session:
            query = session.query(OAuthConnection).filter_by(
                user_id=user_id,
                provider=provider,
            )
            if mode:
                query = query.filter_by(mode=mode)
            row = query.order_by(OAuthConnection.updated_at.desc()).first()
            if not row:
                return None
            return self._oauth_connection_to_dict(row)

    def disconnect_oauth_connection(
        self,
        *,
        user_id: str,
        provider: str,
        mode: str | None = None,
    ) -> int:
        """Mark OAuth connections disconnected and clear persisted tokens."""
        with self.get_session() as session:
            query = session.query(OAuthConnection).filter_by(
                user_id=user_id,
                provider=provider,
            )
            if mode:
                query = query.filter_by(mode=mode)
            rows = query.all()
            now = datetime.now(timezone.utc)
            for row in rows:
                row.status = "disconnected"
                row.encrypted_refresh_token = None
                row.encrypted_access_token = None
                row.relay_grant_id = None
                row.expires_at = None
                row.last_error = None
                row.last_refresh_at = now
            session.commit()
            return len(rows)

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
                text(
                    """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_schema = 'public'
                        AND table_name = :table_name
                    )
                """
                ),
                {"table_name": table_name},
            )
            return result.scalar()

    def list_threads(
        self, user_id: Optional[str] = None, project_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List threads with optional filters (legacy API compat)."""
        with self.get_session() as session:
            query = session.query(ChatThread)

            if user_id:
                query = query.filter_by(user_id=user_id)
            if project_id:
                query = query.filter_by(project_id=int(project_id))

            threads = query.all()
            return [self._thread_to_dict(t) for t in threads]

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
        proj_id = resolve_project_id_or_default(self, project_id, logger=logger)
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
        self, query: str, limit: int, user_id: Optional[str] = None
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


class GuardianDB:
    """Postgres-only façade over ``_PostgresGuardianDB``."""

    def __init__(self, db_url: Optional[str] = None, **_: Any) -> None:
        if not db_url:
            raise RuntimeError(
                "GuardianDB now requires a Postgres DATABASE_URL"
            )
        if "://" not in str(db_url):
            raise RuntimeError(
                "SQLite backend has been removed; provide a Postgres DATABASE_URL"
            )
        self._impl = _PostgresGuardianDB(db_url=db_url)
        self.backend = "postgres"

    def __getattr__(self, name: str) -> Any:
        """
        Delegate attribute access to the underlying implementation instance.

        This keeps the public surface area aligned with the original
        GuardianDB APIs without having to re-declare each method.
        """
        return getattr(self._impl, name)


def load_guardian_db_from_env() -> Optional[GuardianDB]:
    db_url = os.getenv("GUARDIAN_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not db_url:
        return None
    with _GUARDIAN_DB_CACHE_LOCK:
        cached = _GUARDIAN_DB_CACHE.get(db_url)
        if cached is not None:
            return cached
        instance = GuardianDB(db_url)
        _GUARDIAN_DB_CACHE[db_url] = instance
        return instance
