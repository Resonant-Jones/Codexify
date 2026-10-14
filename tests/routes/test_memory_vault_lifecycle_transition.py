"""Focused route tests for the UMS-05C10B-W lifecycle transition endpoint.

Proves ``PATCH /api/memory-vault/items/canonical/{memory_id}/lifecycle`` is
a thin adapter: it delegates exactly to
``MemoryVaultMutationService.transition_lifecycle`` and maps typed service
failures to sanitized HTTP postures. It performs no SQL, no parent lookup, no
row locking, no CAS comparison, no lifecycle state-machine logic, no
lifecycle-history read, no restore-target resolution, no revision numbering,
no receipt construction, and no read-before-write.
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
    MemoryVaultLifecycleIntegrityError,
    MemoryVaultLifecycleInvalid,
    MemoryVaultLifecycleUnsupported,
    MemoryVaultMutationConflict,
    MemoryVaultMutationError,
    MemoryVaultMutationNotAvailable,
    VaultLifecycleTransitionResult,
)
from guardian.services.memory_vault_read import VaultIdentity, VaultItem

ACCOUNT_A = "account-a"
T1 = datetime(2026, 1, 1, tzinfo=timezone.utc)
T2 = datetime(2026, 1, 2, tzinfo=timezone.utc)

LCR_ID = "eeeeeeee-1111-1111-1111-111111111111"
RECEIPT_ID = "ffffffff-1111-1111-1111-111111111111"
MEMORY_ID = "mem-1"


def _url(memory_id: str = MEMORY_ID) -> str:
    return f"/api/memory-vault/items/canonical/{memory_id}/lifecycle"


class FakeLifecycleMutationService:
    """Records delegation and returns typed C10B-W results."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.result: VaultLifecycleTransitionResult | None = None
        self.error: Exception | None = None

    def transition_lifecycle(
        self,
        *,
        memory_id: str,
        expected_updated_at: datetime,
        action: str,
        reason: str | None = None,
        request_ref: str | None = None,
    ) -> VaultLifecycleTransitionResult:
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


def _canonical_item(lifecycle_posture: str = "retired") -> VaultItem:
    return VaultItem(
        identity=VaultIdentity(kind="canonical", canonical_memory_id=MEMORY_ID),
        semantic_species=MemorySemanticSpecies.EPISODIC_SEMANTIC_MEMORY.value,
        content="hello",
        account_owner=ACCOUNT_A,
        project_id=None,
        review_posture="approved",
        lifecycle_posture=lifecycle_posture,
        pinned=False,
        held=False,
        created_at=None,
        updated_at=None,
        persona_links=[],
        provenance=[],
        extensions=None,
    )


def _changed_result(
    action: str, previous: str, resulting: str
) -> VaultLifecycleTransitionResult:
    return VaultLifecycleTransitionResult(
        changed=True,
        action=action,
        receipt_id=RECEIPT_ID,
        lifecycle_revision_id=LCR_ID,
        lifecycle_revision_number=1,
        previous_lifecycle_state=previous,
        resulting_lifecycle_state=resulting,
        previous_updated_at=T1,
        resulting_updated_at=T2,
        item=_canonical_item(resulting),
    )


def _noop_result(action: str, state: str) -> VaultLifecycleTransitionResult:
    return VaultLifecycleTransitionResult(
        changed=False,
        action=action,
        receipt_id=None,
        lifecycle_revision_id=None,
        lifecycle_revision_number=None,
        previous_lifecycle_state=state,
        resulting_lifecycle_state=state,
        previous_updated_at=T1,
        resulting_updated_at=T1,
        item=_canonical_item(state),
    )


def _client(fake: FakeLifecycleMutationService, account_id: str | None = ACCOUNT_A):
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
def fake() -> FakeLifecycleMutationService:
    return FakeLifecycleMutationService()


@pytest.fixture
def client(fake: FakeLifecycleMutationService) -> TestClient:
    return _client(fake)


def _body(action: str = "retire", **overrides) -> dict[str, Any]:
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


def test_retire_success_is_delegated_and_serialized(fake, client):
    fake.result = _changed_result("retire", "active", "retired")
    response = client.patch(_url(), json=_body("retire"))

    assert response.status_code == 200
    body = response.json()
    assert body["changed"] is True
    assert body["action"] == "retire"
    assert body["receipt_id"] == RECEIPT_ID
    assert body["lifecycle_revision_id"] == LCR_ID
    assert body["lifecycle_revision_number"] == 1
    assert body["previous_lifecycle_state"] == "active"
    assert body["resulting_lifecycle_state"] == "retired"
    assert body["item"]["lifecycle_posture"] == "retired"

    assert len(fake.calls) == 1
    call = fake.calls[0]
    assert call["memory_id"] == MEMORY_ID
    assert call["action"] == "retire"
    assert call["expected_updated_at"] == T1


@pytest.mark.parametrize(
    ("previous", "resulting"),
    [("retired", "active"), ("retired", "dormant")],
)
def test_restore_success_is_serialized_for_both_postures(
    fake, client, previous, resulting
):
    fake.result = _changed_result("restore", previous, resulting)
    body = client.patch(_url(), json=_body("restore")).json()
    assert body["changed"] is True
    assert body["resulting_lifecycle_state"] == resulting


def test_retire_noop_is_serialized_with_null_identities(fake, client):
    fake.result = _noop_result("retire", "retired")
    body = client.patch(_url(), json=_body("retire")).json()
    assert body["changed"] is False
    assert body["receipt_id"] is None
    assert body["lifecycle_revision_id"] is None
    assert body["lifecycle_revision_number"] is None
    assert body["previous_lifecycle_state"] == body["resulting_lifecycle_state"]
    assert body["previous_updated_at"] == body["resulting_updated_at"]


@pytest.mark.parametrize("state", ["active", "dormant"])
def test_restore_noop_is_serialized(fake, client, state):
    fake.result = _noop_result("restore", state)
    body = client.patch(_url(), json=_body("restore")).json()
    assert body["changed"] is False
    assert (
        body["previous_lifecycle_state"] == body["resulting_lifecycle_state"] == state
    )


def test_optional_reason_and_request_ref_are_forwarded(fake, client):
    fake.result = _changed_result("retire", "active", "retired")
    client.patch(_url(), json=_body("retire", reason="done", request_ref="req-7"))
    call = fake.calls[0]
    assert call["reason"] == "done"
    assert call["request_ref"] == "req-7"


# ---------------------------------------------------------------------------
# Admission: no raw lifecycle target.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("target", ["active", "dormant", "retired", "set_active"])
def test_raw_lifecycle_target_is_rejected_by_service_and_mapped_422(
    fake, client, target
):
    """The route admits only an action; the service rejects a raw target.

    The service-side refusal of these exact strings is proven in the service
    suite. Here the route must faithfully map that typed refusal to 422.
    """
    fake.error = MemoryVaultLifecycleInvalid(
        "lifecycle action must be retire or restore"
    )
    response = client.patch(_url(), json=_body(target))
    assert response.status_code == 422
    assert len(fake.calls) == 1
    # The route forwarded the caller's string unchanged: it did not
    # translate a raw target into an admitted action.
    assert fake.calls[0]["action"] == target


def test_route_rejects_a_lifecycle_state_field(fake, client):
    fake.result = _changed_result("retire", "active", "retired")
    response = client.patch(_url(), json=_body("retire", lifecycle_state="dormant"))
    assert response.status_code == 422
    assert fake.calls == []


@pytest.mark.parametrize(
    "authority_field",
    [
        "user_id",
        "account_id",
        "actor_account_id",
        "lifecycle_revision_id",
        "lifecycle_revision_number",
        "old_lifecycle_state",
        "review_state",
        "held",
        "pinned",
        "project_id",
        "persona_subject_id",
    ],
)
def test_route_rejects_authority_fields(fake, client, authority_field):
    fake.result = _changed_result("retire", "active", "retired")
    response = client.patch(_url(), json=_body("retire", **{authority_field: "x"}))
    assert response.status_code == 422
    assert fake.calls == []


def test_unknown_action_returns_422(fake, client):
    fake.error = MemoryVaultLifecycleInvalid("nope")
    response = client.patch(_url(), json=_body("activate"))
    assert response.status_code == 422
    assert "retire" in response.json()["detail"]


# ---------------------------------------------------------------------------
# Request-shape failures.
# ---------------------------------------------------------------------------


def test_missing_cas_returns_422(fake, client):
    body = _body()
    body.pop("expected_updated_at")
    response = client.patch(_url(), json=body)
    assert response.status_code == 422
    assert fake.calls == []


def test_malformed_cas_returns_422(fake, client):
    response = client.patch(_url(), json=_body("retire", expected_updated_at="nope"))
    assert response.status_code == 422
    assert fake.calls == []


def test_naive_cas_returns_422(fake, client):
    response = client.patch(
        _url(), json=_body("retire", expected_updated_at="2026-01-01T00:00:00")
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
    response = client.patch(_url(), json=_body("retire"))
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Failure mapping and sanitization.
# ---------------------------------------------------------------------------


def test_missing_memory_returns_404(fake, client):
    fake.error = MemoryVaultMutationNotAvailable("memory item is not available")
    response = client.patch(_url(), json=_body("retire"))
    assert response.status_code == 404
    assert response.json()["detail"] == "Memory not available"


def test_cross_account_posture_is_indistinguishable(fake, client):
    fake.error = MemoryVaultMutationNotAvailable("memory item is not available")
    missing = client.patch(_url(), json=_body("retire"))
    cross = client.patch(_url("other-mem"), json=_body("retire"))
    assert missing.status_code == cross.status_code == 404
    assert missing.json() == cross.json()


def test_stale_cas_maps_to_bounded_409(fake, client):
    fake.error = MemoryVaultMutationConflict(
        "memory item changed; expected_updated_at is stale"
    )
    response = client.patch(_url(), json=_body("retire"))
    assert response.status_code == 409
    assert response.json()["detail"] == "Memory changed since it was read"


def test_zero_history_retired_restore_maps_to_bounded_409(fake, client):
    fake.error = MemoryVaultLifecycleIntegrityError(
        "restore requires canonical pre-retirement lifecycle history"
    )
    response = client.patch(_url(), json=_body("restore"))
    assert response.status_code == 409
    assert response.json()["detail"] == "Memory lifecycle transition unavailable"


@pytest.mark.parametrize(
    "error",
    [
        MemoryVaultLifecycleUnsupported("not writable by the generic writer"),
        MemoryVaultLifecycleIntegrityError("lifecycle history chain is broken"),
        MemoryVaultMutationError("memory mutation failed"),
    ],
)
def test_unsupported_and_integrity_map_to_bounded_409(fake, client, error):
    fake.error = error
    response = client.patch(_url(), json=_body("retire"))
    assert response.status_code == 409
    assert response.json()["detail"] == "Memory lifecycle transition unavailable"


def test_internal_error_detail_is_sanitized(fake, client):
    secret = "memory_lifecycle_revisions_memory_account CHECK violation"
    fake.error = MemoryVaultLifecycleIntegrityError(secret)
    payload = client.patch(_url(), json=_body("restore")).text
    assert secret not in payload
    assert "CHECK" not in payload
    assert "memory_lifecycle_revisions" not in payload
    assert "traceback" not in payload.lower()


# ---------------------------------------------------------------------------
# Route delegation boundary.
# ---------------------------------------------------------------------------


def test_route_performs_no_independent_read_before_write(fake, client):
    """Exactly one service call, carrying only request fields."""
    fake.result = _changed_result("restore", "retired", "dormant")
    response = client.patch(_url(), json=_body("restore"))
    assert response.status_code == 200
    assert len(fake.calls) == 1
    call = fake.calls[0]
    # The route adds no authority and resolves nothing itself.
    assert set(call) == {
        "memory_id",
        "expected_updated_at",
        "action",
        "reason",
        "request_ref",
    }
    assert set(fake.__dict__) & {"restored_target"} == set()


def test_route_does_not_resolve_restore_target_or_revision_number(fake, client):
    """The restore target comes from the service result, not the route."""
    fake.result = _changed_result("restore", "retired", "dormant")
    body = client.patch(_url(), json=_body("restore")).json()
    # Route simply serializes what the service decided.
    assert body["resulting_lifecycle_state"] == "dormant"
    assert body["lifecycle_revision_number"] == 1
    assert fake.calls[0]["action"] == "restore"
