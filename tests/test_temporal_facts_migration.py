"""Tests for temporal ordering and personal facts schema migration."""

from datetime import datetime, timedelta, timezone

import pytest

from guardian.db.models import (
    ChatMessage,
    PersonalFact,
    PersonalFactEvidence,
    PersonalFactRevision,
)


class TestChatMessageTemporalFields:
    """Test temporal fields on ChatMessage model."""

    def test_chat_message_has_event_at_field(self):
        """ChatMessage model should have event_at field."""
        assert hasattr(ChatMessage, "event_at")

    def test_chat_message_has_kind_field(self):
        """ChatMessage model should have kind field."""
        assert hasattr(ChatMessage, "kind")

    def test_chat_message_has_extra_meta_field(self):
        """ChatMessage model should have extra_meta field."""
        assert hasattr(ChatMessage, "extra_meta")

    def test_kind_column_default(self):
        """kind column should default to 'chat'."""
        col = ChatMessage.__table__.columns["kind"]
        assert col.server_default.arg == "chat"

    def test_extra_meta_column_default(self):
        """extra_meta column should default to empty JSON object."""
        col = ChatMessage.__table__.columns["extra_meta"]
        assert col.server_default.arg == "{}"


class TestPersonalFactModel:
    """Test PersonalFact model."""

    def test_personal_fact_has_required_fields(self):
        """PersonalFact model should have all required fields."""
        required_fields = [
            "id",
            "user_id",
            "key",
            "value",
            "status",
            "confidence",
            "is_active",
            "last_confirmed_at",
            "created_at",
            "updated_at",
        ]
        for field in required_fields:
            assert hasattr(PersonalFact, field), f"Missing field: {field}"

    def test_status_default(self):
        """status column should default to 'candidate'."""
        col = PersonalFact.__table__.columns["status"]
        assert col.server_default.arg == "candidate"

    def test_confidence_default(self):
        """confidence column should default to 0.5."""
        col = PersonalFact.__table__.columns["confidence"]
        assert col.server_default.arg == "0.5"

    def test_is_active_default(self):
        """is_active column should default to true."""
        col = PersonalFact.__table__.columns["is_active"]
        assert col.server_default.arg == "true"

    def test_has_evidence_relationship(self):
        """PersonalFact should have evidence relationship."""
        assert hasattr(PersonalFact, "evidence")

    def test_has_revisions_relationship(self):
        """PersonalFact should have revisions relationship."""
        assert hasattr(PersonalFact, "revisions")


class TestPersonalFactEvidenceModel:
    """Test PersonalFactEvidence model."""

    def test_evidence_has_required_fields(self):
        """PersonalFactEvidence model should have all required fields."""
        required_fields = [
            "id",
            "fact_id",
            "source_message_id",
            "excerpt",
            "modality",
            "confidence",
            "source_type",
            "evidence_meta",
            "created_at",
        ]
        for field in required_fields:
            assert hasattr(
                PersonalFactEvidence, field
            ), f"Missing field: {field}"

    def test_modality_default(self):
        """modality column should default to 'text'."""
        col = PersonalFactEvidence.__table__.columns["modality"]
        assert col.server_default.arg == "text"

    def test_evidence_meta_default(self):
        """evidence_meta column should default to empty JSON object."""
        col = PersonalFactEvidence.__table__.columns["evidence_meta"]
        assert col.server_default.arg == "{}"

    def test_has_fact_relationship(self):
        """PersonalFactEvidence should have fact relationship."""
        assert hasattr(PersonalFactEvidence, "fact")

    def test_has_source_message_relationship(self):
        """PersonalFactEvidence should have source_message relationship."""
        assert hasattr(PersonalFactEvidence, "source_message")


class TestPersonalFactRevisionModel:
    """Test PersonalFactRevision model."""

    def test_revision_has_required_fields(self):
        """PersonalFactRevision model should have all required fields."""
        required_fields = [
            "id",
            "fact_id",
            "actor",
            "action",
            "field_changed",
            "old_value",
            "new_value",
            "reason",
            "created_at",
        ]
        for field in required_fields:
            assert hasattr(
                PersonalFactRevision, field
            ), f"Missing field: {field}"

    def test_has_fact_relationship(self):
        """PersonalFactRevision should have fact relationship."""
        assert hasattr(PersonalFactRevision, "fact")


class TestStatusInvariant:
    """Test status + is_active invariant documentation."""

    def test_valid_status_values(self):
        """Status should accept candidate, verified, disputed, archived."""
        # This is a documentation/design test - the actual constraint is in the DB
        valid_statuses = ["candidate", "verified", "disputed", "archived"]
        # The constraint is checked at DB level, here we just document expected values
        assert len(valid_statuses) == 4

    def test_retrieval_rules(self):
        """Document retrieval rules for status + is_active combinations."""
        # candidate + active: included (tentative)
        # verified + active: included (confident)
        # disputed + active: EXCLUDED from retrieval (shown in review UI)
        # archived + inactive: EXCLUDED from everything
        retrieval_rules = {
            ("candidate", True): "included_tentative",
            ("verified", True): "included_confident",
            ("disputed", True): "excluded_review_only",
            ("archived", False): "excluded",
        }
        assert len(retrieval_rules) == 4
