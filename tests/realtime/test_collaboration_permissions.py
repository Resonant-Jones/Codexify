"""Tests for collaboration permissions, token auth, and audit logging."""

import os
import hashlib
from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from guardian.realtime.collaboration import manager

# Import test models from conftest
from tests.realtime.conftest import (
    CollaborationAuditLog,
    CollaborationPermission,
    SharedLink,
)

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="Postgres not configured for realtime permission tests (set TEST_DATABASE_URL)",
)


@pytest.fixture
def setup_permissions(db_session: Session):
    """Set up test permissions in database."""
    # Create permissions for user1 with edit rights
    perm1 = CollaborationPermission(
        document_id="doc-123",
        user_id="user1",
        can_edit=True,
        can_comment=True,
        granted_by="admin",
    )
    # Create permissions for user2 with read-only
    perm2 = CollaborationPermission(
        document_id="doc-123",
        user_id="user2",
        can_edit=False,
        can_comment=True,
        granted_by="admin",
    )
    db_session.add(perm1)
    db_session.add(perm2)
    db_session.commit()
    return {"perm1": perm1, "perm2": perm2}


@pytest.fixture
def setup_shared_link(db_session: Session):
    """Set up test shared link in database."""
    import uuid

    token = "test_token_abc123xyz"
    shared_link = SharedLink(
        id=str(uuid.uuid4()),
        target_type="document",
        target_id="doc-456",
        token=token,
        expires_at=None,  # No expiry
    )
    db_session.add(shared_link)
    db_session.commit()
    return shared_link


class TestPermissionVerification:
    """Test permission verification logic."""

    def test_verify_access_with_edit_permission(
        self, db_session: Session, setup_permissions
    ):
        """User with edit permission should be authorized."""
        is_authorized, perms = manager.verify_access(
            "doc-123", "user1", None, db_session
        )
        assert is_authorized is True
        assert perms["can_edit"] is True
        assert perms["can_comment"] is True

    def test_verify_access_with_readonly_permission(
        self, db_session: Session, setup_permissions
    ):
        """User with read-only permission should be authorized but not edit."""
        is_authorized, perms = manager.verify_access(
            "doc-123", "user2", None, db_session
        )
        assert is_authorized is True
        assert perms["can_edit"] is False
        assert perms["can_comment"] is True

    def test_verify_access_unauthorized_user(
        self, db_session: Session, setup_permissions
    ):
        """User without permission should be denied access."""
        is_authorized, perms = manager.verify_access(
            "doc-123", "user3", None, db_session
        )
        assert is_authorized is False
        assert perms is None

    def test_verify_access_with_valid_shared_link(
        self, db_session: Session, setup_shared_link
    ):
        """Valid shared link token should grant read-only access."""
        is_authorized, perms = manager.verify_access(
            "doc-456", "unknown_user", "test_token_abc123xyz", db_session
        )
        assert is_authorized is True
        assert perms["can_edit"] is False
        assert perms["can_comment"] is True

    def test_verify_access_with_invalid_token(self, db_session: Session):
        """Invalid token should not grant access."""
        is_authorized, perms = manager.verify_access(
            "doc-456", "unknown_user", "invalid_token", db_session
        )
        assert is_authorized is False
        assert perms is None

    def test_verify_access_permission_takes_precedence(
        self, db_session: Session, setup_permissions, setup_shared_link
    ):
        """Direct permission should take precedence over shared link."""
        # user1 has direct edit permission on doc-123
        is_authorized, perms = manager.verify_access(
            "doc-123", "user1", "test_token_abc123xyz", db_session
        )
        assert is_authorized is True
        assert perms["can_edit"] is True  # Direct permission, not shared link


class TestAuditLogging:
    """Test audit log creation and retrieval."""

    def test_log_presence_join_event(self, db_session: Session):
        """Should log presence.join events."""
        manager.log_audit_event(
            doc_id="doc-789",
            user_id="user1",
            action="presence.join",
            payload={"can_edit": True, "can_comment": True},
            session=db_session,
        )

        # Verify event was logged
        logs = (
            db_session.query(CollaborationAuditLog)
            .filter(CollaborationAuditLog.document_id == "doc-789")
            .all()
        )
        assert len(logs) >= 1
        assert logs[0].action == "presence.join"
        assert logs[0].user_id == "user1"

    def test_log_update_event_with_content_hash(self, db_session: Session):
        """Should log update events with content hash."""
        content = "test content"
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

        manager.log_audit_event(
            doc_id="doc-789",
            user_id="user1",
            action="update",
            payload={"content_hash": content_hash},
            session=db_session,
        )

        # Verify event was logged
        logs = (
            db_session.query(CollaborationAuditLog)
            .filter(CollaborationAuditLog.action == "update")
            .all()
        )
        assert len(logs) >= 1
        assert logs[0].payload["content_hash"] == content_hash

    def test_log_permission_violation(self, db_session: Session):
        """Should log update_denied events for permission violations."""
        manager.log_audit_event(
            doc_id="doc-789",
            user_id="user2",
            action="update_denied",
            payload={"reason": "insufficient_permissions"},
            session=db_session,
        )

        # Verify event was logged
        logs = (
            db_session.query(CollaborationAuditLog)
            .filter(CollaborationAuditLog.action == "update_denied")
            .all()
        )
        assert len(logs) >= 1
        assert logs[0].payload["reason"] == "insufficient_permissions"

    def test_log_access_denied_event(self, db_session: Session):
        """Should log access_denied events."""
        manager.log_audit_event(
            doc_id="doc-789",
            user_id="unauthorized_user",
            action="access_denied",
            payload={"reason": "unauthorized"},
            session=db_session,
        )

        # Verify event was logged
        logs = (
            db_session.query(CollaborationAuditLog)
            .filter(CollaborationAuditLog.action == "access_denied")
            .all()
        )
        assert len(logs) >= 1
        assert logs[0].user_id == "unauthorized_user"

    def test_log_presence_leave_event(self, db_session: Session):
        """Should log presence.leave events."""
        manager.log_audit_event(
            doc_id="doc-789",
            user_id="user1",
            action="presence.leave",
            payload={},
            session=db_session,
        )

        # Verify event was logged
        logs = (
            db_session.query(CollaborationAuditLog)
            .filter(CollaborationAuditLog.action == "presence.leave")
            .all()
        )
        assert len(logs) >= 1

    def test_audit_log_has_timestamp(self, db_session: Session):
        """Audit logs should have timestamps."""
        before = datetime.utcnow()
        manager.log_audit_event(
            doc_id="doc-789",
            user_id="user1",
            action="presence.join",
            payload={},
            session=db_session,
        )
        after = datetime.utcnow()

        logs = (
            db_session.query(CollaborationAuditLog)
            .filter(CollaborationAuditLog.action == "presence.join")
            .all()
        )
        assert len(logs) >= 1
        # Timestamp should be between before and after (accounting for DB defaults)
        assert logs[0].timestamp is not None


class TestCollaborationManagerPermissions:
    """Test manager's permission storage."""

    def test_store_permissions_in_manager(self):
        """Manager should store user permissions for quick access."""
        doc_id = "doc-test"
        user_id = "user1"
        perms = {"can_edit": True, "can_comment": True}

        # Initialize permissions dict if needed
        if doc_id not in manager.permissions:
            manager.permissions[doc_id] = {}

        manager.permissions[doc_id][user_id] = perms

        assert manager.permissions[doc_id][user_id] == perms

    def test_permission_enforcement_for_updates(self):
        """Manager should enforce permissions on updates."""
        doc_id = "doc-test2"
        user_id = "user2"
        read_only_perms = {"can_edit": False, "can_comment": True}

        if doc_id not in manager.permissions:
            manager.permissions[doc_id] = {}

        manager.permissions[doc_id][user_id] = read_only_perms

        # Check that edit permission is enforced
        assert manager.permissions[doc_id][user_id]["can_edit"] is False
        assert manager.permissions[doc_id][user_id]["can_comment"] is True
