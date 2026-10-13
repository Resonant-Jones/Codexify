"""Focused route tests for the UMS-05C9-W content-correction endpoint.

Proves ``PATCH /api/memory-vault/items/canonical/{memory_id}/content`` is
a thin adapter: it delegates exactly to
``MemoryVaultMutationService.correct_content`` and maps typed service
failures to sanitized HTTP postures. It performs no SQL, no revision-number
calculation, no CAS comparison, no row locking, and no receipt
construction of its own.
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
    MemoryVaultContentCorrectionIntegrityError,
    MemoryVaultContentCorrectionInvalid,
    MemoryVaultContentCorrectionUnsupported,
    MemoryVaultMutationConflict,
    MemoryVaultMutationError,
    MemoryVaultMutationNotAvailable,
    VaultContentCorrectionResult,
)
from guardian.services.memory_vault_read import VaultIdentity, VaultItem

ACCOUNT_A = "account-a"
ACCOUNT_B = "account-b"
T1 = datetime(2026, 1, 1, tzinfo=timezone.utc)
T2 = datetime(2026, 1, 2, tzinfo=timezone.utc)

REV_ID = "bbbbbbbb-1111-1111-1111-111111111111"
RECEIPT_ID = "cccccccc-1111-1111-1111-111111111111"


class FakeVaultMutationService:
    """Records delegation and returns typed C9-W results."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.result: VaultContentCorrectionResult | None = None
        self.error: Exception | None = None

    def correct_content(
        self,
        *,
        memory_id: str,
        expected_updated_at: datetime,
        content: str,
        reason: str | None = None,
        request_ref: str | None = None,
    ) -> VaultContentCorrectionResult:
        self.calls.append(
            {
                "memory_id": memory_id,
                "expected_updated_at": expected_updated_at,
                "content": content,
                "reason": reason,
                "request_ref": request_ref,
            }
        )
        if self.error is not None:
            raise self.error
        assert self.result is not None, "fake result not configured"
        return self.result


def _canonical_item(memory_id: str = "mem-1", content: str = "hello") -> VaultItem:
    return VaultItem(
        identity=VaultIdentity(kind="canonical", canonical_memory_id=memory_id),
        semantic_species=MemorySemanticSpecies.EPISODIC_SEMANTIC_MEMORY.value,
        content=content,
        account_owner=ACCOUNT_A,
        project_id=None,
        review_posture="approved",
        lifecycle_posture="active",
        pinned=False,
        held=False,
        created_at=None,
        updated_at=None,
        persona_links=[],
        provenance=[],
        extensions=None,
    )


def _changed_result(content: str = "corrected text") -> VaultContentCorrectionResult:
    return VaultContentCorrectionResult(
        changed=True,
        receipt_id=RECEIPT_ID,
        revision_id=REV_ID,
        revision_number=1,
        previous_updated_at=T1,
        resulting_updated_at=T2,
        item=_canonical_item("mem-1", content),
    )


def _noop_result() -> VaultContentCorrectionResult:
    return VaultContentCorrectionResult(
        changed=False,
        receipt_id=None,
        revision_id=None,
        revision_number=None,
        previous_updated_at=T1,
        resulting_updated_at=T1,
        item=_canonical_item("mem-1", "hello"),
    )


@pytest.fixture
def fake_mutation() -> FakeVaultMutationService:
    return FakeVaultMutationService()


@pytest.fixture
def client(fake_mutation: FakeVaultMutationService) -> TestClient:
    app = FastAPI()
    app.include_router(memory_vault.router)
    app.dependency_overrides[memory_vault.require_api_key] = lambda: "test-key"
    app.dependency_overrides[memory_vault.get_request_user_scope] = lambda: (
        RequestUserScope(
            user_id="legacy-a",
            subject_id="subject-a",
            account_id=ACCOUNT_A,
            multi_user_enabled=True,
        )
    )
    app.dependency_overrides[memory_vault.get_memory_vault_mutation_service] = (
        lambda: fake_mutation
    )
    return TestClient(app)


def _url(memory_id: str = "mem-1") -> str:
    return f"/api/memory-vault/items/canonical/{memory_id}/content"


# 1-2: exact delegation + serialization.
def test_create_route_delegates_exactly_and_serializes(
    fake_mutation: FakeVaultMutationService, client: TestClient
) -> None:
    fake_mutation.result = _changed_result()
    response = client.patch(
        _url(),
        json={
            "content": "corrected text",
            "expected_updated_at": T1.isoformat(),
            "reason": "clarify",
            "request_ref": "req-1",
        },
    )
    assert response.status_code == 200
    assert fake_mutation.calls == [
        {
            "memory_id": "mem-1",
            "expected_updated_at": T1,
            "content": "corrected text",
            "reason": "clarify",
            "request_ref": "req-1",
        }
    ]
    body = response.json()
    assert body["changed"] is True
    assert body["receipt_id"] == RECEIPT_ID
    assert body["revision_id"] == REV_ID
    assert body["revision_number"] == 1
    assert datetime.fromisoformat(body["previous_updated_at"]) == T1
    assert datetime.fromisoformat(body["resulting_updated_at"]) == T2
    assert body["item"]["content"] == "corrected text"


# 3: revision identity serialization is carried through.
def test_create_route_serializes_revision_identity(
    fake_mutation: FakeVaultMutationService, client: TestClient
) -> None:
    fake_mutation.result = _changed_result()
    body = client.patch(
        _url(), json={"content": "x", "expected_updated_at": T1.isoformat()}
    ).json()
    assert body["revision_id"] == REV_ID
    assert body["revision_number"] == 1


# 4: no-op serialization.
def test_create_route_serializes_noop(
    fake_mutation: FakeVaultMutationService, client: TestClient
) -> None:
    fake_mutation.result = _noop_result()
    body = client.patch(
        _url(), json={"content": "hello", "expected_updated_at": T1.isoformat()}
    ).json()
    assert body["changed"] is False
    assert body["receipt_id"] is None
    assert body["revision_id"] is None
    assert body["revision_number"] is None


# 5: 401 blank account.
def test_create_route_requires_stable_account() -> None:
    app = FastAPI()
    app.include_router(memory_vault.router)
    app.dependency_overrides[memory_vault.require_api_key] = lambda: "test-key"
    app.dependency_overrides[memory_vault.get_request_user_scope] = lambda: (
        RequestUserScope(user_id="legacy-a", account_id="", multi_user_enabled=True)
    )
    client = TestClient(app)
    response = client.patch(
        _url(), json={"content": "x", "expected_updated_at": T1.isoformat()}
    )
    assert response.status_code == 401


# 6-10: 422 validation.
@pytest.mark.parametrize(
    "body",
    [
        {"expected_updated_at": T1.isoformat()},  # missing content
        {"content": "", "expected_updated_at": T1.isoformat()},
        {"content": "x"},  # missing CAS
        {"content": "x", "expected_updated_at": "not-a-date"},
        {"content": "x", "expected_updated_at": "2026-01-01T00:00:00"},  # naive
    ],
)
def test_create_route_validation_returns_422(
    fake_mutation: FakeVaultMutationService,
    client: TestClient,
    body: dict[str, Any],
) -> None:
    response = client.patch(_url(), json=body)
    assert response.status_code == 422


# 11-13: 404 for missing and cross-account share one body.
def test_create_route_missing_and_cross_account_share_404(
    fake_mutation: FakeVaultMutationService, client: TestClient
) -> None:
    fake_mutation.error = MemoryVaultMutationNotAvailable("memory not found")
    missing = client.patch(
        _url("missing-mem"),
        json={"content": "x", "expected_updated_at": T1.isoformat()},
    )
    cross = client.patch(
        _url("cross-mem"), json={"content": "x", "expected_updated_at": T1.isoformat()}
    )
    assert missing.status_code == 404
    assert cross.status_code == 404
    assert missing.json() == cross.json()
    assert missing.json()["detail"] == "Memory not available"


# 14: 409 stale CAS.
def test_create_route_stale_cas_is_409(
    fake_mutation: FakeVaultMutationService, client: TestClient
) -> None:
    fake_mutation.error = MemoryVaultMutationConflict("stale internal detail")
    response = client.patch(
        _url(), json={"content": "x", "expected_updated_at": T1.isoformat()}
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Memory changed since it was read"
    assert "stale internal detail" not in response.text


# 15-16: 409 unsupported / integrity.
def test_create_route_unsupported_species_is_sanitized_409(
    fake_mutation: FakeVaultMutationService, client: TestClient
) -> None:
    fake_mutation.error = MemoryVaultContentCorrectionUnsupported(
        "verified_personal_fact species internal detail"
    )
    response = client.patch(
        _url(), json={"content": "x", "expected_updated_at": T1.isoformat()}
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Memory content correction unavailable"
    assert "personal_fact" not in response.text.lower()
    assert "verified_personal_fact" not in response.text


def test_create_route_integrity_failure_is_sanitized_409(
    fake_mutation: FakeVaultMutationService, client: TestClient
) -> None:
    fake_mutation.error = MemoryVaultContentCorrectionIntegrityError(
        "revision tail chain constraint internal detail"
    )
    response = client.patch(
        _url(), json={"content": "x", "expected_updated_at": T1.isoformat()}
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Memory content correction unavailable"
    assert "revision" not in response.text.lower()
    assert "constraint" not in response.text.lower()


def test_create_route_generic_mutation_error_is_409(
    fake_mutation: FakeVaultMutationService, client: TestClient
) -> None:
    fake_mutation.error = MemoryVaultMutationError("traceback leak detail")
    response = client.patch(
        _url(), json={"content": "x", "expected_updated_at": T1.isoformat()}
    )
    assert response.status_code == 409
    assert "traceback leak detail" not in response.text


# 17-18: route delegates, no local authority; caller fields do not bind.
def test_create_route_ignores_caller_authority_fields(
    fake_mutation: FakeVaultMutationService, client: TestClient
) -> None:
    fake_mutation.result = _changed_result()
    response = client.patch(
        _url(),
        params={"user_id": ACCOUNT_B, "account_id": ACCOUNT_B},
        json={
            "content": "x",
            "expected_updated_at": T1.isoformat(),
            "revision_id": "forged",
            "revision_number": 99,
            "project_id": 1,
            "semantic_species": "verified_personal_fact",
            "pinned": True,
            "held": True,
        },
    )
    assert response.status_code == 200
    call = fake_mutation.calls[0]
    assert set(call) == {
        "memory_id",
        "expected_updated_at",
        "content",
        "reason",
        "request_ref",
    }
    assert call["content"] == "x"


def test_create_route_whitespace_only_is_sanitized_422(
    fake_mutation: FakeVaultMutationService, client: TestClient
) -> None:
    """Whitespace-only text passes shape validation and is rejected by the
    service, which the route maps to a sanitized 422."""
    fake_mutation.error = MemoryVaultContentCorrectionInvalid("content is required")
    response = client.patch(
        _url(), json={"content": "   ", "expected_updated_at": T1.isoformat()}
    )
    assert response.status_code == 422
    assert "content is required" not in response.text
