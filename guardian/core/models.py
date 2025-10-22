# guardian/core/models.py
"""Alembic-facing registry of SQLAlchemy metadata."""

from datetime import datetime
from importlib import import_module
import logging
from typing import Any, Dict, Iterable

from sqlalchemy import DateTime, JSON, MetaData, String, func, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    metadata = MetaData()


# Unified MetaData that Alembic will inspect for autogeneration.
metadata = Base.metadata


class EventOutbox(Base):
    __tablename__ = "events_outbox"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic: Mapped[str] = mapped_column(String, nullable=False)
    payload: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    tenant_id: Mapped[str] = mapped_column(
        String, nullable=False, default="default"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


def _load_modules(modules: Iterable[str]) -> None:
    for dotted in modules:
        try:
            import_module(dotted)
        except ModuleNotFoundError as exc:
            logger.debug("Skipping optional Postgres model module %s: %s", dotted, exc)


_load_modules(
    (
        "guardian.core.pg_models.chat_threads",
        "guardian.core.pg_models.chat_messages",
        "guardian.core.pg_models.memory",
        "guardian.core.pg_models.projects",
        "guardian.core.pg_models.sync_jobs",
    )
)


__all__ = ["metadata", "EventOutbox"]
