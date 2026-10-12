"""Focused route tests for the UMS-11 permanent-erasure endpoints.

Proves the two purge routes are thin adapters over ``MemoryPurgeService``:

* both delegate exactly to the purge service and to nothing else;
* the routes own no SQL, no fingerprint computation, no child enumeration,
  no CAS logic, and no confirmation-token derivation;
* typed service failures map to bounded, sanitized HTTP postures --
  401 / 404 / 409 / 422 -- that leak no SQL, no fingerprint, no plaintext
  source id, and no another-account existence;
* a same-account idempotent retry succeeds with ``already_purged`` while a
  cross-account or missing target yields the same indistinguishable 404;
* and the routes stay on the internal-only Memory Vault router, hidden from
  any public surface.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from guardian.core.dependencies import RequestUserScope, get_request_user_scope
from guardian.routes import memory_vault
from guardian.services.memory_purge import (
    MemoryPurgeAmbiguousSourceIdentity,
    MemoryPurgeConflict,
    MemoryPurgeError,
    MemoryPurgeIntegrityError,
    MemoryPurgeInvalid,
    MemoryPurgeNotAvailable,
    MemoryPurgePreview,
    MemoryPurgeResult,
)

ACCOUNT_A = "account-a"
T1 = datetime(2026, 1, 1, tzinfo=timezone.utc)
T2 = datetime(2026, 1, 2, tzinfo=timezone.utc)

MEMORY_ID = "mem-1"
RECORD_FP = "v1:" + "a" * 64
CONFIRM_TOKEN = "v1:" + "b" * 64
SOURCE_FP = "v1:" + "c" * 64
RECEIPT_ID = "11111111-2222-3333-4444-555555555555"


def _preview_url(memory_id: str = MEMORY_ID) -> str:
    return f"/api/memory-vault/items/canonical/{memory_id}/purge-preview"


def _purge_url(memory_id: str = MEMORY_ID) -> str:
    return f"/api/memory-vault/items/canonical/{memory_id}/purge"


class FakePurgeService:
    """Records delegation and returns typed UMS-11 results."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.preview_result: MemoryPurgePreview | None = None
        self.purge_result: MemoryPurgeResult | None = None
        self.error: Exception | None = None

    def preview_purge(self, *, memory_id: str) -> MemoryPurgePreview:
        self.calls.append({"method": "preview_purge", "memory_id": memory_id})
        if self.error is not None:
            raise self.error
        assert self.preview_result is not None, "fake preview not configured"
        return self.preview_result

    def purge(
        self,
        *,
        memory_id: str,
        expected_updated_at: datetime,
        confirmation_token: str,
        reason: str | None = None,
        request_ref: str | None = None,
    ) -> MemoryPurgeResult:
        self.calls.append(
            {
                "method": "purge",
                "memory_id": memory_id,
                "expected_updated_at": expected_updated_at,
                "confirmation_token": confirmation_token,
                "reason": reason,
                "request_ref": request_ref,
            }
        )
        if self.error is not None:
            raise self.error
        assert self.purge_result is not None, "fake purge result not configured"
        return self.purge_result


def _preview(**overrides: Any) -> MemoryPurgePreview:
    values: dict[str, Any] = {
        "memory_id": MEMORY_ID,
        "record_fingerprint": RECORD_FP,
        "updated_at": T1,
        "content_revision_count": 1,
        "review_revision_count": 2,
        "lifecycle_revision_count": 0,
        "provenance_count": 1,
        "persona_link_count": 0,
        "derived_state_count": 0,
        "suppression_fingerprint_available": True,
        "suppression_ambiguity": None,
        "confirmation_token": CONFIRM_TOKEN,
    }
    values.update(overrides)
    return MemoryPurgePreview(**values)


def _result(**overrides: Any) -> MemoryPurgeResult:
    values: dict[str, Any] = {
        "memory_id": MEMORY_ID,
        "changed": True,
        "already_purged": False,
        "purge_receipt_id": RECEIPT_ID,
        "purged_at": T2,
        "record_fingerprint": RECORD_FP,
        "source_atom_fingerprint": SOURCE_FP,
        "suppression": True,
        "deleted_content_revisions": 1,
        "deleted_review_revisions": 2,
        "deleted_lifecycle_revisions": 0,
        "deleted_provenance": 1,
        "deleted_persona_links": 0,
    }
    values.update(overrides)
    return MemoryPurgeResult(**values)


def _app(
    service: FakePurgeService | None = None,
    *,
    account: str = ACCOUNT_A,
    require_api_key: bool = True,
) -> tuple[FastAPI, FakePurgeService]:
    fake = service or FakePurgeService()
    app = FastAPI()
    if not require_api_key:
        app.dependency_overrides[memory_vault.require_api_key] = lambda: True
    app.dependency_overrides[get_request_user_scope] = lambda: RequestUserScope(
        account_id=account,
        user_id=account,
    )
    app.dependency_overrides[memory_vault.get_memory_purge_service] = lambda: fake
    app.include_router(memory_vault.router)
    return app, fake


def _client(**kwargs: Any) -> tuple[TestClient, FakePurgeService]:
    app, fake = _app(**kwargs)
    return TestClient(app, raise_server_exceptions=False), fake


# ---------------------------------------------------------------------------
# Delegation.
# ---------------------------------------------------------------------------


def test_preview_delegates_to_purge_service() -> None:
    client, fake = _client()
    fake.preview_result = _preview()

    response = client.get(_preview_url())

    assert response.status_code == 200
    body = response.json()
    assert body["memory_id"] == MEMORY_ID
    assert body["record_fingerprint"] == RECORD_FP
    assert body["content_revision_count"] == 1
    assert body["review_revision_count"] == 2
    assert body["lifecycle_revision_count"] == 0
    assert body["provenance_count"] == 1
    assert body["persona_link_count"] == 0
    assert body["derived_state_count"] == 0
    # Parent + every destroyed child row.
    assert body["total_affected_rows"] == 5
    assert body["suppression_fingerprint_available"] is True
    assert body["confirmation_token"] == CONFIRM_TOKEN
    assert fake.calls == [{"method": "preview_purge", "memory_id": MEMORY_ID}]


def test_purge_delegates_to_purge_service() -> None:
    client, fake = _client()
    fake.purge_result = _result()

    response = client.post(
        _purge_url(),
        json={
            "expected_updated_at": T1.isoformat(),
            "confirmation_token": CONFIRM_TOKEN,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["changed"] is True
    assert body["already_purged"] is False
    assert body["purge_receipt_id"] == RECEIPT_ID
    assert body["purged_at"].startswith("2026-01-02")
    assert body["record_fingerprint"] == RECORD_FP
    assert body["source_atom_fingerprint"] == SOURCE_FP
    assert body["suppression"] is True
    assert body["deleted_content_revisions"] == 1
    assert body["deleted_review_revisions"] == 2
    assert body["deleted_provenance"] == 1
    assert fake.calls == [
        {
            "method": "purge",
            "memory_id": MEMORY_ID,
            "expected_updated_at": T1,
            "confirmation_token": CONFIRM_TOKEN,
            "reason": None,
            "request_ref": None,
        }
    ]


def test_route_owns_no_destructive_authority() -> None:
    """The adapter computes nothing and owns no SQL or fan-out."""
    import inspect

    source = inspect.getsource(memory_vault)
    for body in (
        inspect.getsource(memory_vault.post_canonical_vault_item_purge),
        inspect.getsource(memory_vault.get_canonical_vault_item_purge_preview),
    ):
        # No direct database access, no fingerprinting, no enumeration.
        for forbidden in (
            "session",
            "execute(",
            "select(",
            "delete(",
            "purged_record_fingerprint(",
            "source_atom_fingerprint(",
            "sha256",
            "MemoryRecord",
            "MemoryProvenance",
            "MemoryPurgeTombstone",
        ):
            assert forbidden not in body, f"route owns {forbidden!r}"
    # The module imports the tombstone relation nowhere in its route bodies.
    assert "MemoryPurgeTombstone" not in source


# ---------------------------------------------------------------------------
# HTTP posture.
# ---------------------------------------------------------------------------


def test_missing_and_cross_account_share_one_404() -> None:
    for account in (ACCOUNT_A, "other-account"):
        client, _ = _client(account=account)
        client.app.dependency_overrides[memory_vault.get_memory_purge_service] = (
            lambda: _raising(MemoryPurgeNotAvailable("memory item is not available"))
        )
        response = client.get(_preview_url())
        assert response.status_code == 404
        assert response.json()["detail"] == "Memory not available"


def _raising(exc: Exception):
    fake = FakePurgeService()
    fake.error = exc
    return fake


def test_purge_missing_and_cross_account_share_one_404() -> None:
    client, _ = _client()
    fake = _raising(MemoryPurgeNotAvailable("memory item is not available"))
    client.app.dependency_overrides[memory_vault.get_memory_purge_service] = (
        lambda: fake
    )
    response = client.post(
        _purge_url(),
        json={
            "expected_updated_at": T1.isoformat(),
            "confirmation_token": CONFIRM_TOKEN,
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Memory not available"


def test_stale_cas_is_bounded_409() -> None:
    client, _ = _client()
    fake = _raising(
        MemoryPurgeConflict("memory item changed; expected_updated_at is stale")
    )
    client.app.dependency_overrides[memory_vault.get_memory_purge_service] = (
        lambda: fake
    )
    response = client.post(
        _purge_url(),
        json={
            "expected_updated_at": T1.isoformat(),
            "confirmation_token": CONFIRM_TOKEN,
        },
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Memory changed since it was read"


def test_stale_confirmation_is_bounded_409() -> None:
    client, _ = _client()
    fake = _raising(MemoryPurgeConflict("purge confirmation is stale or invalid"))
    client.app.dependency_overrides[memory_vault.get_memory_purge_service] = (
        lambda: fake
    )
    response = client.post(
        _purge_url(),
        json={
            "expected_updated_at": T1.isoformat(),
            "confirmation_token": "v1:" + "0" * 64,
        },
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Memory purge confirmation is stale or invalid"


def test_ambiguous_source_identity_is_distinct_bounded_409() -> None:
    client, _ = _client()
    fake = _raising(
        MemoryPurgeAmbiguousSourceIdentity(
            "import-origin record has no single safe source-atom identity"
        )
    )
    client.app.dependency_overrides[memory_vault.get_memory_purge_service] = (
        lambda: fake
    )
    response = client.post(
        _purge_url(),
        json={
            "expected_updated_at": T1.isoformat(),
            "confirmation_token": CONFIRM_TOKEN,
        },
    )
    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail == "Memory purge cannot guarantee re-import suppression"
    # The caller learns the destructive claim is unsatisfiable without being
    # told which source identity was ambiguous.
    assert "atom" not in detail.lower() or "re-import" in detail.lower()


def test_integrity_failure_is_sanitized_409() -> None:
    client, _ = _client()
    fake = _raising(MemoryPurgeIntegrityError("canonical memory was not destroyed"))
    client.app.dependency_overrides[memory_vault.get_memory_purge_service] = (
        lambda: fake
    )
    response = client.post(
        _purge_url(),
        json={
            "expected_updated_at": T1.isoformat(),
            "confirmation_token": CONFIRM_TOKEN,
        },
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Memory purge unavailable"


def test_malformed_body_is_422() -> None:
    client, fake = _client()
    # Missing confirmation_token.
    response = client.post(_purge_url(), json={"expected_updated_at": T1.isoformat()})
    assert response.status_code == 422
    assert fake.calls == []


def test_missing_confirmation_token_is_422() -> None:
    client, fake = _client()
    response = client.post(
        _purge_url(),
        json={"expected_updated_at": T1.isoformat(), "confirmation_token": ""},
    )
    assert response.status_code == 422
    assert fake.calls == []


def test_blank_account_is_401() -> None:
    # Only the identity scope is overridden here. The authenticated-account
    # resolution lives inside the purge-service dependency, so stubbing that
    # dependency would delete the very code path under test.
    app = FastAPI()
    app.dependency_overrides[memory_vault.require_api_key] = lambda: True
    app.dependency_overrides[get_request_user_scope] = lambda: RequestUserScope(
        account_id="   ",
        user_id="   ",
    )
    app.include_router(memory_vault.router)
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get(_preview_url())
    assert response.status_code == 401
    assert response.json()["detail"] == "Stable account identity required"


def test_idempotent_retry_succeeds_with_already_purged() -> None:
    client, fake = _client()
    fake.purge_result = _result(
        changed=False, already_purged=True, deleted_content_revisions=0
    )
    response = client.post(
        _purge_url(),
        json={
            "expected_updated_at": T1.isoformat(),
            "confirmation_token": CONFIRM_TOKEN,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["already_purged"] is True
    assert body["changed"] is False
    # Same receipt identity is returned, not a new one.
    assert body["purge_receipt_id"] == RECEIPT_ID


def test_internal_details_are_not_leaked() -> None:
    client, _ = _client()
    fake = _raising(
        MemoryPurgeIntegrityError(
            "duplicate key value violates unique constraint "
            '"uq_memory_purge_tombstones_account_source_atom"'
        )
    )
    client.app.dependency_overrides[memory_vault.get_memory_purge_service] = (
        lambda: fake
    )
    response = client.post(
        _purge_url(),
        json={
            "expected_updated_at": T1.isoformat(),
            "confirmation_token": CONFIRM_TOKEN,
        },
    )
    rendered = response.text
    for forbidden in (
        "uq_memory_purge_tombstones",
        "SELECT",
        "INSERT",
        SOURCE_FP,
        "source_atom_fingerprint",
    ):
        assert forbidden not in rendered


def test_caller_cannot_supply_authority_fields() -> None:
    """A caller cannot forge account, fingerprint, receipt, or cascade control."""
    client, fake = _client()
    fake.purge_result = _result()
    response = client.post(
        _purge_url(),
        json={
            "expected_updated_at": T1.isoformat(),
            "confirmation_token": CONFIRM_TOKEN,
            # Every one of these must be ignored or rejected outright.
            "user_id": "someone-else",
            "account_id": "someone-else",
            "source_atom_fingerprint": SOURCE_FP,
            "purge_receipt_id": "forged-receipt",
            "force": True,
        },
    )
    assert response.status_code in (200, 422)
    if response.status_code == 200:
        # Nothing the caller asserted was forwarded to the service.
        assert set(fake.calls[0]) == {
            "method",
            "memory_id",
            "expected_updated_at",
            "confirmation_token",
            "reason",
            "request_ref",
        }


# ---------------------------------------------------------------------------
# Surface posture.
# ---------------------------------------------------------------------------


def test_routes_are_declared_with_the_expected_methods() -> None:
    app = FastAPI()
    app.include_router(memory_vault.router)
    schema = app.openapi()
    preview = "/api/memory-vault/items/canonical/{memory_id}/purge-preview"
    purge = "/api/memory-vault/items/canonical/{memory_id}/purge"
    assert set(schema["paths"][preview]) == {"get"}
    assert set(schema["paths"][purge]) == {"post"}


def test_purge_is_the_only_destructive_post() -> None:
    """The only two POSTs are creation and purge; only purge is destructive."""
    app = FastAPI()
    app.include_router(memory_vault.router)
    schema = app.openapi()
    posts = {
        path
        for path, methods in schema["paths"].items()
        if path.startswith("/api/memory-vault") and "post" in methods
    }
    # Creation (C6) and permanent erasure (UMS-11) are the only POSTs.
    assert posts == {
        "/api/memory-vault/items",
        "/api/memory-vault/items/canonical/{memory_id}/purge",
    }, posts
    # Purge is the only POST that targets an existing canonical record and
    # destroys it, so the destructive surface is unambiguous.
    destructive = {path for path in posts if "{memory_id}" in path}
    assert destructive == {
        "/api/memory-vault/items/canonical/{memory_id}/purge"
    }, destructive


def test_routes_remain_internal_only() -> None:
    """The purge surface never widens the public Beta surface.

    ``guardian.guardian_api`` is inspected as source rather than imported:
    importing it pulls in the chat/voice/storage stack, which is unrelated to
    this assertion and requires environment the route layer does not own.
    """
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[2] / "guardian" / "guardian_api.py"
    ).read_text()

    # The Vault router is flag-gated and is not a core public surface. Purge
    # inherits exactly that posture; it adds no registration of its own.
    assert "CODEXIFY_ENABLE_MEMORY_VAULT_ROUTES" in source
    vault_block = source.split('label="memory_vault"', 1)[1][:400]
    assert "core_surface=False" in vault_block
    assert "purge" not in source.lower()

    # The router itself is mounted only under the internal Memory Vault prefix.
    assert memory_vault.router.prefix == "/api/memory-vault"
