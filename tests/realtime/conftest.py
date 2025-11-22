"""Shared test fixtures for collaboration realtime tests."""

import os
import pytest
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, DateTime, Boolean, JSON, ForeignKey, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

# Set environment variables early to avoid issues
os.environ.setdefault("STORAGE_BASE_PATH", "/tmp/test_media")
os.environ.setdefault("ENABLE_BLIP_MODEL", "false")
os.environ.setdefault("GUARDIAN_ENABLE_MONDREAM", "0")
os.environ.setdefault("ENABLE_CONNECTOR_WORKER", "0")


# Create minimal test-only models for SQLite compatibility
Base = declarative_base()


class CollaborationPermission(Base):
    __tablename__ = "collaboration_permissions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String(36), nullable=False)
    user_id = Column(String(255), nullable=False)
    can_edit = Column(Boolean, server_default="false", nullable=False)
    can_comment = Column(Boolean, server_default="true", nullable=False)
    granted_by = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class SharedLink(Base):
    __tablename__ = "shared_links"
    id = Column(String(36), primary_key=True)
    target_type = Column(String(32), nullable=False)
    target_id = Column(String(36), nullable=False)
    token = Column(String(64), unique=True, nullable=False)
    expires_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class CollaborationAuditLog(Base):
    __tablename__ = "collaboration_audit_log"
    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String(36), nullable=False)
    user_id = Column(String(255))
    action = Column(String(64), nullable=False)
    payload = Column(JSON)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


@pytest.fixture(scope="function")
def db_engine():
    """Create a Postgres-backed database for testing."""
    db_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not db_url:
        pytest.skip("TEST_DATABASE_URL or DATABASE_URL must be set for realtime DB tests")
    engine = create_engine(db_url, future=True)

    # Create only the test tables
    Base.metadata.create_all(engine)

    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Create a session for test operations."""
    SessionLocal = sessionmaker(bind=db_engine)
    session = SessionLocal()
    yield session
    session.close()
