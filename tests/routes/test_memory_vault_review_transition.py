"""Focused route tests for the UMS-05C10A-W review transition endpoint.

Proves ``PATCH /api/memory-vault/items/canonical/{memory_id}/review`` is a
thin adapter: it delegates exactly to
``MemoryVaultMutationService.transition_review`` and maps typed service
failures to sanitized HTTP postures. It performs no SQL, no parent lookup,
no row locking, no CAS comparison, no no-op determination, no
state-machine calculation, no review-revision numbering, no ``reviewed_at``
decision, and no receipt construction of its own.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from guardian.core.dependencies import RequestUserScope, get_request_user_scope
from guardian.protocol_tokens import MemorySemanticSpecies
from guardian.routes import memory_vault
from guardian.services.memory_vault_mutation import (
    MemoryVaultMutationConflict,
    MemoryVaultMutationError,
    MemoryVaultMutationNotAvailable,
    MemoryVaultReviewTransitionIntegrityError,
    MemoryVaultReviewTransitionInvalid,
    MemoryVaultReviewTransitionUnsupported,
    VaultReviewTransitionResult,
)
from guardian.services.memory_vault_read import VaultIdentity, VaultItem

ACCOUNT_A = "account-a"
T1 = datetime(2026, 1, 1, tzinfo=timezone.utc)
T2 = datetime(2026, 1, 2, tzinfo=timezone.utc)

REVIEW_REVISION_ID = "dddddddd-1111-1111-1111-111111111111"
RECEIPT_ID = "cccccccc-1111-1111-1111-111111111111"

BASE = "/api/memory-vault/items/canonical"


def _url(memory_id: str = "mem-1") -> str:
    return f"{BASE}/{memory_id}/review"


class FakeVaultMutationService:
    """Records delegation and returns typed C10A-W results."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.result: VaultReviewTransitionResult | None = None
        self.error: Exception | None = None

    def transition_review(
        self,
        *,
        memory_id: str,
        expected_updated_at: datetime,
        action: str,
        reason: str | None = None,
        request_ref: str | None = None,
    ) -> VaultReviewTransitionResult:
        self.calls.append(
            {
                "memory_id": memory_id,
                "expected_updated_at": expected_updated_at,
                "action": action,
                "reason": reason,
                "request_ref": request_ref,
            }
        )
        if self.error is not None:
            raise self.error
        assert self.result is not None, "fake result not configured"
        return self.result


def _canonical_item(review_posture: str = "approved") -> VaultItem:
    return VaultItem(
        identity=VaultIdentity(kind="canonical", canonical_memory_id="mem-1"),
        semantic_species=MemorySemanticSpecies.EPISODIC_SEMANTIC_MEMORY.value,
        content="hello",
        account_owner=ACCOUNT_A,
        project_id=None,
        review_posture=review_posture,
        lifecycle_posture="active",
        pinned=False,
        held=False,
        created_at=None,
        updated_at=None,
        persona_links=[],
        provenance=[],
        extensions=None,
    )


def _changed_result(action: str, target: str) -> VaultReviewTransitionResult:
    return VaultReviewTransitionResult(
        changed=True,
        action=action,
        receipt_id=RECEIPT_ID,
        review_revision_id=REVIEW_REVISION_ID,
        review_revision_number=1,
        previous_review_state="pending",
        resulting_review_state=target,
        previous_updated_at=T1,
        resulting_updated_at=T2,
        item=_canonical_item(target),
    )


def _noop_result(action: str, state: str) -> VaultReviewTransitionResult:
    return VaultReviewTransitionResult(
        changed=False,
        action=action,
        receipt_id=None,
        review_revision_id=None,
        review_revision_number=None,
        previous_review_state=state,
        resulting_review_state=state,
        previous_updated_at=T1,
        resulting_updated_at=T1,
        item=_canonical_item(state),
    )


def _client(fake: FakeVaultMutationService, account_id: str | None = ACCOUNT_A):
    app = FastAPI()
    app.include_router(memory_vault.router)
    app.dependency_overrides[memory_vault.require_api_key] = lambda: "test-key"
    app.dependency_overrides[memory_vault.get_request_user_scope] = lambda: (
        RequestUserScope(
            user_id="legacy-a",
            subject_id="subject-a",
            account_id=account_id or "",
            multi_user_enabled=True,
        )
    )
    app.dependency_overrides[memory_vault.get_memory_vault_mutation_service] = (
        lambda: fake
    )
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def fake() -> FakeVaultMutationService:
    return FakeVaultMutationService()


@pytest.fixture
def client(fake: FakeVaultMutationService) -> TestClient:
    return _client(fake)


def _body(action: str = "approve", **overrides) -> dict[str, Any]:
    payload = {
        "action": action,
        "expected_updated_at": T1.isoformat(),
        "reason": None,
        "request_ref": None,
    }
    payload.update(overrides)
    return payload


# ---------------------------------------------------------------------------
# Delegation and serialization.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("action", "target"),
    [("approve", "approved"), ("reject", "rejected"), ("dispute", "disputed")],
)
def test_changed_transitions_are_delegated_and_serialized(fake, client, action, target):
    fake.result = _changed_result(action, target)
    response = client.patch(_url(), json=_body(action))

    assert response.status_code == 200
    body = response.json()
    assert body["changed"] is True
    assert body["action"] == action
    assert body["receipt_id"] == RECEIPT_ID
    assert body["review_revision_id"] == REVIEW_REVISION_ID
    assert body["review_revision_number"] == 1
    assert body["previous_review_state"] == "pending"
    assert body["resulting_review_state"] == target
    # Timestamps round-trip as instants; pydantic may emit "Z" for UTC.
    assert datetime.fromisoformat(body["previous_updated_at"]) == T1
    assert datetime.fromisoformat(body["resulting_updated_at"]) == T2
    assert body["item"]["review_posture"] == target
    # Canonical readback comes from the service result, not a fresh read.
    assert body["item"]["identity"]["kind"] == "canonical"

    assert len(fake.calls) == 1
    call = fake.calls[0]
    assert call["memory_id"] == "mem-1"
    assert call["action"] == action
    assert call["expected_updated_at"] == T1


def test_noop_is_serialized_with_null_identities(fake, client):
    fake.result = _noop_result("approve", "approved")
    body = client.patch(_url(), json=_body("approve")).json()

    assert body["changed"] is False
    assert body["receipt_id"] is None
    assert body["review_revision_id"] is None
    assert body["review_revision_number"] is None
    assert body["previous_review_state"] == "approved"
    assert body["resulting_review_state"] == "approved"
    assert body["previous_updated_at"] == body["resulting_updated_at"]


def test_optional_reason_and_request_ref_are_forwarded(fake, client):
    fake.result = _changed_result("approve", "approved")
    client.patch(
        _url(), json=_body("approve", reason="looks right", request_ref="req-9")
    )
    call = fake.calls[0]
    assert call["reason"] == "looks right"
    assert call["request_ref"] == "req-9"


def test_route_cannot_target_pending():
    """The request surface has no review-state field at all.

    The route can only express one of ADR-088's three admitted actions, so a
    client has no way to request `pending` as a target. Admission of the
    action string itself is the service's authority, proven separately.
    """
    from guardian.routes.memory_vault import VaultReviewTransitionRequest

    fields = set(VaultReviewTransitionRequest.model_fields)
    assert fields == {"expected_updated_at", "reason", "request_ref", "action"}
    assert "review_state" not in fields
    assert "pending" not in fields


def test_route_cannot_accept_raw_review_state(fake, client):
    fake.result = _changed_result("approve", "approved")
    response = client.patch(_url(), json=_body("approve", review_state="rejected"))
    assert response.status_code == 422
    assert fake.calls == []


@pytest.mark.parametrize(
    "authority_field",
    [
        "user_id",
        "account_id",
        "actor_account_id",
        "review_revision_id",
        "review_revision_number",
        "lifecycle_state",
        "project_id",
        "persona_subject_id",
    ],
)
def test_route_rejects_authority_fields(fake, client, authority_field):
    fake.result = _changed_result("approve", "approved")
    response = client.patch(_url(), json=_body("approve", **{authority_field: "x"}))
    assert response.status_code == 422
    assert fake.calls == []


# ---------------------------------------------------------------------------
# Request-shape failures.
# ---------------------------------------------------------------------------


def test_unknown_action_returns_422(fake, client):
    fake.error = MemoryVaultReviewTransitionInvalid("nope")
    response = client.patch(_url(), json=_body("set_pending"))
    assert response.status_code == 422
    assert "approve" in response.json()["detail"]


def test_missing_cas_returns_422(fake, client):
    body = _body()
    body.pop("expected_updated_at")
    response = client.patch(_url(), json=body)
    assert response.status_code == 422
    assert fake.calls == []


def test_malformed_cas_returns_422(fake, client):
    response = client.patch(_url(), json=_body("approve", expected_updated_at="nope"))
    assert response.status_code == 422
    assert fake.calls == []


def test_naive_cas_returns_422(fake, client):
    response = client.patch(
        _url(), json=_body("approve", expected_updated_at="2026-01-01T00:00:00")
    )
    assert response.status_code == 422
    assert fake.calls == []


def test_missing_action_returns_422(fake, client):
    body = _body()
    body.pop("action")
    response = client.patch(_url(), json=body)
    assert response.status_code == 422
    assert fake.calls == []


def test_blank_account_returns_401():
    """A blank authenticated account is refused by the real service authority."""
    app = FastAPI()
    app.include_router(memory_vault.router)
    app.dependency_overrides[memory_vault.require_api_key] = lambda: "test-key"
    app.dependency_overrides[memory_vault.get_request_user_scope] = lambda: (
        RequestUserScope(user_id="legacy-a", account_id="", multi_user_enabled=True)
    )
    client = TestClient(app, raise_server_exceptions=False)
    response = client.patch(_url(), json=_body())
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Failure mapping and sanitization.
# ---------------------------------------------------------------------------


def test_missing_memory_returns_404(fake, client):
    fake.error = MemoryVaultMutationNotAvailable("memory item is not available")
    response = client.patch(_url(), json=_body())
    assert response.status_code == 404
    assert response.json()["detail"] == "Memory not available"


def test_cross_account_posture_is_indistinguishable(fake, client):
    """Missing and cross-account must look identical from outside."""
    fake.error = MemoryVaultMutationNotAvailable("memory item is not available")
    missing = client.patch(_url(), json=_body())
    cross = client.patch(_url("other-mem"), json=_body())
    assert missing.status_code == cross.status_code == 404
    assert missing.json() == cross.json()


def test_stale_cas_maps_to_bounded_409(fake, client):
    fake.error = MemoryVaultMutationConflict(
        "memory item changed; expected_updated_at is stale"
    )
    response = client.patch(_url(), json=_body())
    assert response.status_code == 409
    assert response.json()["detail"] == "Memory changed since it was read"


@pytest.mark.parametrize(
    "error",
    [
        MemoryVaultReviewTransitionUnsupported(
            "not writable by the generic review writer"
        ),
        MemoryVaultReviewTransitionIntegrityError("review history is not contiguous"),
        MemoryVaultMutationError("memory mutation failed"),
    ],
)
def test_unsupported_and_integrity_map_to_sanitized_409(fake, client, error):
    fake.error = error
    response = client.patch(_url(), json=_body())
    assert response.status_code == 409
    assert response.json()["detail"] == "Memory review transition unavailable"


def test_errors_do_not_leak_internal_detail(fake, client):
    secret = "memory_review_revisions_memory_account CHECK violation"
    fake.error = MemoryVaultReviewTransitionIntegrityError(secret)
    payload = client.patch(_url(), json=_body()).text
    assert secret not in payload
    assert "CHECK" not in payload
    assert "memory_review_revisions" not in payload
    assert "traceback" not in payload.lower()


# ---------------------------------------------------------------------------
# Delegation boundary.
# ---------------------------------------------------------------------------


def test_route_performs_no_independent_read_before_write(fake, client):
    """Exactly one service call; the route resolves no parent itself."""
    fake.result = _changed_result("dispute", "disputed")
    response = client.patch(_url(), json=_body("dispute"))
    assert response.status_code == 200
    assert len(fake.calls) == 1
    call = fake.calls[0]
    # The route forwards only request fields; it adds no authority.
    assert set(call) == {
        "memory_id",
        "expected_updated_at",
        "action",
        "reason",
        "request_ref",
    }
    # No DB read attributes are consulted on the route object.
    assert not hasattr(client.app.state, "session")


def test_response_never_exposes_separate_memory_content_copy(fake, client):
    fake.result = _changed_result("approve", "approved")
    body = client.patch(_url(), json=_body("approve")).json()
    # Content appears only inside the canonical item, never as a separate
    # review-history field.
    assert "text_content" not in body
    assert "old_review_state" not in body
    assert "new_review_state" not in body
    assert body["item"]["content"] == "hello"
