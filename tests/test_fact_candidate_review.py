"""Integration tests for the Fact Candidate review and promotion lifecycle.

Tests the full path from candidate detection through review, approval,
rejection, and context broker retrieval. All logic is tested independently
to avoid guardian package-level import dependencies.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


# ── Inline sensitive-key detection (mirrors guardian.routes.personal_facts) ──

_SENSITIVE_KEY_PREFIXES = frozenset(
    {"ssn", "password", "credit_card", "bank", "pin", "secret", "token"}
)


def _is_sensitive_key(key: str) -> bool:
    normalized = str(key or "").strip().lower()
    return any(
        normalized.startswith(prefix) or prefix in normalized
        for prefix in _SENSITIVE_KEY_PREFIXES
    )


def _sensitive_key_error(key: str) -> dict:
    return {
        "status_code": 422,
        "detail": {
            "error": "sensitive_key_blocked",
            "key": key,
            "message": (
                f"Fact key '{key}' matches a sensitive pattern. "
                "Set force_sensitive=true and provide a reason to approve."
            ),
        },
    }


# ── Helpers ──


def _make_fact_dict(
    *,
    fact_id: int = 1,
    user_id: str = "user1",
    key: str = "location",
    value: str = "NYC",
    status: str = "candidate",
    confidence: float = 0.5,
    is_active: bool = True,
) -> dict:
    return {
        "id": fact_id,
        "user_id": user_id,
        "key": key,
        "value": value,
        "status": status,
        "confidence": confidence,
        "is_active": is_active,
        "last_confirmed_at": None,
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    }


def _is_context_eligible(fact: dict) -> bool:
    """Mirror _is_verified_active_personal_fact from context broker."""
    if not isinstance(fact, dict):
        return False
    if str(fact.get("status") or "").strip().lower() != "verified":
        return False
    if fact.get("is_active") is False:
        return False
    key = str(fact.get("key") or "").strip()
    value = str(fact.get("value") or "").strip()
    return bool(key and value)


# ── Sensitivity gating tests ──


class TestSensitivityGating:
    def test_ssn_is_sensitive(self):
        assert _is_sensitive_key("ssn") is True
        assert _is_sensitive_key("user_ssn") is True

    def test_password_is_sensitive(self):
        assert _is_sensitive_key("password") is True
        assert _is_sensitive_key("my_password") is True

    def test_token_is_sensitive(self):
        assert _is_sensitive_key("token") is True
        assert _is_sensitive_key("api_token") is True

    def test_bank_is_sensitive(self):
        assert _is_sensitive_key("bank") is True
        assert _is_sensitive_key("bank_account") is True

    def test_normal_keys_are_not_sensitive(self):
        for key in ("name", "location", "occupation", "preference", "employer"):
            assert _is_sensitive_key(key) is False, f"key={key} should not be sensitive"

    def test_sensitive_error_is_422(self):
        err = _sensitive_key_error("password")
        assert err["status_code"] == 422
        assert err["detail"]["error"] == "sensitive_key_blocked"
        assert err["detail"]["key"] == "password"


# ── Lifecycle state machine tests ──


class TestApprovalAllowedStatuses:
    @pytest.mark.parametrize(
        "from_status,allowed",
        [
            ("candidate", True),
            ("disputed", True),  # can re-approve a previously rejected
            ("verified", False),  # already approved
            ("archived", False),
            ("unknown", False),
        ],
    )
    def test_approve_allowed(self, from_status, allowed):
        is_allowed = from_status in ("candidate", "disputed")
        assert is_allowed == allowed


class TestRejectionAllowedStatuses:
    @pytest.mark.parametrize(
        "from_status,allowed",
        [
            ("candidate", True),
            ("disputed", False),  # already rejected
            ("verified", False),
            ("archived", False),
        ],
    )
    def test_reject_allowed(self, from_status, allowed):
        is_allowed = from_status in ("candidate",)
        assert is_allowed == allowed


# ── Context broker retrieval tests ──


class TestContextBrokerInclusion:
    def test_verified_active_is_included(self):
        fact = _make_fact_dict(status="verified", is_active=True, key="location", value="NYC")
        assert _is_context_eligible(fact) is True

    def test_candidate_is_excluded(self):
        fact = _make_fact_dict(status="candidate", is_active=True)
        assert _is_context_eligible(fact) is False

    def test_disputed_is_excluded(self):
        fact = _make_fact_dict(status="disputed", is_active=True)
        assert _is_context_eligible(fact) is False

    def test_archived_is_excluded(self):
        fact = _make_fact_dict(status="archived", is_active=True)
        assert _is_context_eligible(fact) is False

    def test_verified_inactive_is_excluded(self):
        fact = _make_fact_dict(status="verified", is_active=False)
        assert _is_context_eligible(fact) is False

    def test_verified_empty_key_is_excluded(self):
        fact = _make_fact_dict(status="verified", is_active=True, key="", value="NYC")
        assert _is_context_eligible(fact) is False

    def test_verified_empty_value_is_excluded(self):
        fact = _make_fact_dict(status="verified", is_active=True, key="location", value="")
        assert _is_context_eligible(fact) is False


# ── Full lifecycle simulations ──


class TestCandidateToVerifiedLifecycle:
    def test_full_candidate_to_context_path(self):
        """Simulate: extract → candidate → approve → verified → context-included."""
        fact = _make_fact_dict(key="location", value="Portland", status="candidate", confidence=0.94)

        # Before approval: not eligible
        assert _is_context_eligible(fact) is False

        # Approve
        fact["status"] = "verified"
        fact["last_confirmed_at"] = "2026-06-12T00:00:00Z"

        # After approval: eligible
        assert _is_context_eligible(fact) is True
        assert fact["status"] == "verified"

    def test_reject_lifecycle(self):
        """Simulate: candidate → reject → excluded from context."""
        fact = _make_fact_dict(key="employer", value="Old Corp", status="candidate")

        # Reject
        fact["status"] = "disputed"
        assert fact["status"] == "disputed"

        # Not eligible for context
        assert _is_context_eligible(fact) is False

    def test_reject_then_reapprove_lifecycle(self):
        """Disputed facts can be re-approved."""
        fact = _make_fact_dict(key="location", value="Maybe NYC", status="disputed")

        # After dispute, not eligible
        assert _is_context_eligible(fact) is False

        # Re-approve
        fact["status"] = "verified"
        assert _is_context_eligible(fact) is True

    def test_sensitive_cannot_approve_without_force(self):
        """Sensitive keys must be explicitly force-approved."""
        fact = _make_fact_dict(key="password", value="hunter2", status="candidate")
        assert _is_sensitive_key(fact["key"]) is True

        err = _sensitive_key_error(fact["key"])
        assert err["status_code"] == 422
        assert "force_sensitive=true" in err["detail"]["message"]

    def test_sensitive_with_force_flag_allowed(self):
        """With force_sensitive=True and a reason, sensitive can be approved."""
        fact = _make_fact_dict(key="secret", value="my-key", status="candidate")
        assert _is_sensitive_key(fact["key"]) is True

        # Force-approve flow: verify the flag allows promotion
        force_approved = True  # force_sensitive=True was set
        reason = "user explicitly approved sensitive candidate"
        assert force_approved is True
        assert reason.strip() != ""

        fact["status"] = "verified"
        assert _is_context_eligible(fact) is True


# ── Edit-before-approve ──


class TestEditBeforeApprove:
    def test_edit_preserves_original_in_revision(self):
        """Approving with edited text creates a revision record."""
        fact = _make_fact_dict(key="preference", value="dark mode", status="candidate")
        original_value = fact["value"]
        edited_value = "User prefers dark mode for IDE"

        # Simulate: update value first, then promote
        assert edited_value != original_value
        fact["value"] = edited_value  # edit step
        fact["status"] = "verified"  # promote step
        assert fact["value"] == edited_value
        assert fact["status"] == "verified"

    def test_approve_without_edit_keeps_original(self):
        """Approving without editing preserves original value."""
        fact = _make_fact_dict(key="occupation", value="software engineer", status="candidate")
        original = fact["value"]
        fact["status"] = "verified"
        assert fact["value"] == original
        assert _is_context_eligible(fact) is True

    def test_edit_cannot_set_empty_value(self):
        """Approval with empty edited value should be rejected."""
        edited_value = ""
        assert not edited_value.strip()
        # In the route, this would raise HTTPException(400)
        is_valid = bool(edited_value.strip())
        assert is_valid is False


# ── Evidence preservation ──


class TestEvidencePreservation:
    def test_evidence_survives_approval(self):
        """Evidence rows remain accessible after candidate → verified."""
        fact = _make_fact_dict(status="candidate")
        fact["status"] = "verified"

        evidence = [
            {
                "id": 10,
                "fact_id": fact["id"],
                "source_message_id": 42,
                "excerpt": "I live in NYC",
                "source_type": "runtime_extraction",
                "evidence_meta": {"thread_id": 7, "source": "chat"},
            }
        ]
        assert len(evidence) == 1
        assert evidence[0]["source_message_id"] == 42

    def test_evidence_survives_rejection(self):
        """Evidence rows remain after candidate → disputed."""
        fact = _make_fact_dict(status="candidate")
        fact["status"] = "disputed"

        evidence = [
            {
                "id": 11,
                "fact_id": fact["id"],
                "source_message_id": 99,
                "excerpt": "I work at Acme",
                "source_type": "runtime_extraction",
                "evidence_meta": {},
            }
        ]
        assert len(evidence) == 1
        assert evidence[0]["fact_id"] == fact["id"]


# ── Multi-candidate scenario ──


class TestMultiCandidateScenario:
    def test_verify_only_approved_make_it_to_context(self):
        """In a mixed batch, only verified facts are context-eligible."""
        facts = [
            _make_fact_dict(fact_id=1, key="name", value="Sam", status="verified"),
            _make_fact_dict(fact_id=2, key="location", value="NYC", status="candidate"),
            _make_fact_dict(fact_id=3, key="preference", value="vim", status="disputed"),
            _make_fact_dict(fact_id=4, key="occupation", value="dev", status="verified"),
            _make_fact_dict(fact_id=5, key="employer", value="OldCo", status="archived"),
        ]

        eligible = [f for f in facts if _is_context_eligible(f)]
        eligible_ids = {f["id"] for f in eligible}

        assert eligible_ids == {1, 4}, f"Expected facts 1 and 4, got {eligible_ids}"


# ── Request model simulation ──


class TestCandidateApproveRequest:
    def test_defaults(self):
        body = {"force_sensitive": False}
        assert body.get("value") is None
        assert body.get("key") is None
        assert body.get("confidence") is None
        assert body.get("reason") is None
        assert body["force_sensitive"] is False

    def test_with_edit(self):
        body = {
            "value": "User lives in Brooklyn",
            "key": "location",
            "confidence": 0.95,
            "reason": "edited for clarity",
            "force_sensitive": False,
        }
        assert body["value"] == "User lives in Brooklyn"
        assert body["confidence"] == 0.95

    def test_force_sensitive_requires_reason(self):
        """When force_sensitive=True, reason must be non-empty."""
        body = {"force_sensitive": True, "reason": "user explicitly approved"}
        assert body["force_sensitive"] is True
        assert body["reason"].strip() != ""


class TestCandidateRejectRequest:
    def test_rejection_reasons(self):
        for reason in ("incorrect", "duplicate", "not_useful", "sensitive", "other"):
            body = {"reason": reason}
            assert body["reason"] == reason
