"""Focused route tests for the authenticated Memory Vault API (UMS-05B2 / C2).

These tests mount ``guardian.routes.memory_vault.router`` on a bare
``FastAPI`` application and use dependency overrides for:

- API-key authority (``require_api_key``);
- stable request-user scope (``get_request_user_scope``);
- the Memory Vault read service factory (``get_memory_vault_read_service``);
- the Memory Vault mutation service factory
  (``get_memory_vault_mutation_service``).

Read/mutation services are faked with typed B1/C1 DTO return values. No
full Guardian application is imported or booted, and no
supported-profile manifest is touched.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from guardian.core.dependencies import RequestUserScope, get_request_user_scope
from guardian.core.memory_compatibility import (
    MemoryCompatibilitySourceKind,
    MemoryCompatibilitySourceRef,
)
from guardian.protocol_tokens import MemoryPersonaLinkKind, MemorySemanticSpecies
from guardian.routes import memory_vault
from guardian.services.memory_vault_creation import (
    MemoryVaultCreationError,
    MemoryVaultCreationIntegrityError,
    VaultCreationResult,
)
from guardian.services.memory_vault_mutation import (
    MemoryVaultMutationConflict,
    MemoryVaultMutationError,
    MemoryVaultMutationNotAvailable,
    MemoryVaultPersonaSubjectLifecycleConflict,
    MemoryVaultPersonaSubjectNotAvailable,
    MemoryVaultProjectAuthorityConflict,
    MemoryVaultProjectNotAvailable,
    VaultMutationResult,
)
from guardian.services.memory_vault_read import (
    DEFAULT_LIST_LIMIT,
    MAX_LIST_LIMIT,
    MemoryVaultReadError,
    VaultIdentity,
    VaultItem,
    VaultListFilter,
    VaultPersonaLink,
    VaultProvenance,
)

ACCOUNT_A = "account-a"
ACCOUNT_B = "account-b"

GENERIC_UNAVAILABLE_DETAIL = "Memory item unavailable"

T1 = datetime(2026, 1, 1, tzinfo=timezone.utc)
T2 = datetime(2026, 1, 2, tzinfo=timezone.utc)


def _mutation_result(
    *,
    changed: bool,
    item: VaultItem,
    receipt_id: str | None = None,
    previous_updated_at: datetime = T1,
    resulting_updated_at: datetime = T2,
) -> VaultMutationResult:
    return VaultMutationResult(
        changed=changed,
        receipt_id=receipt_id,
        previous_updated_at=previous_updated_at,
        resulting_updated_at=resulting_updated_at,
        item=item,
    )


class FakeVaultService:
    """Records calls and returns typed B1 DTOs (not a semantic model)."""

    def __init__(self) -> None:
        self.list_calls: list[dict[str, Any]] = []
        self.get_calls: list[VaultIdentity] = []
        self.list_result: list[VaultItem] = []
        self.get_result: VaultItem | None = None
        self.list_error: Exception | None = None
        self.get_error: Exception | None = None

    def list_items(
        self,
        *,
        filter: VaultListFilter | None = None,
        limit: int = DEFAULT_LIST_LIMIT,
        offset: int = 0,
    ) -> list[VaultItem]:
        self.list_calls.append({"filter": filter, "limit": limit, "offset": offset})
        if self.list_error is not None:
            raise self.list_error
        return list(self.list_result)

    def get_item(self, *, identity: VaultIdentity) -> VaultItem | None:
        self.get_calls.append(identity)
        if self.get_error is not None:
            raise self.get_error
        return self.get_result


class FakeVaultMutationService:
    """Records calls and returns typed C1 mutation results."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.result: VaultMutationResult | None = None
        self.error: Exception | None = None

    def set_pinned(
        self,
        *,
        memory_id: str,
        expected_updated_at: datetime,
        pinned: bool,
        reason: str | None = None,
        request_ref: str | None = None,
    ) -> VaultMutationResult:
        self.calls.append(
            {
                "memory_id": memory_id,
                "expected_updated_at": expected_updated_at,
                "pinned": pinned,
                "reason": reason,
                "request_ref": request_ref,
            }
        )
        if self.error is not None:
            raise self.error
        assert self.result is not None, "fake mutation result not configured"
        return self.result

    def set_held(
        self,
        *,
        memory_id: str,
        expected_updated_at: datetime,
        held: bool,
        reason: str | None = None,
        request_ref: str | None = None,
    ) -> VaultMutationResult:
        self.calls.append(
            {
                "memory_id": memory_id,
                "expected_updated_at": expected_updated_at,
                "held": held,
                "reason": reason,
                "request_ref": request_ref,
            }
        )
        if self.error is not None:
            raise self.error
        assert self.result is not None, "fake mutation result not configured"
        return self.result

    def set_project_scope(
        self,
        *,
        memory_id: str,
        expected_updated_at: datetime,
        project_id: int | None,
        reason: str | None = None,
        request_ref: str | None = None,
    ) -> VaultMutationResult:
        self.calls.append(
            {
                "memory_id": memory_id,
                "expected_updated_at": expected_updated_at,
                "project_id": project_id,
                "reason": reason,
                "request_ref": request_ref,
            }
        )
        if self.error is not None:
            raise self.error
        assert self.result is not None, "fake mutation result not configured"
        return self.result

    def set_persona_attribution(
        self,
        *,
        memory_id: str,
        expected_updated_at: datetime,
        persona_subject_id: str,
        link_kind,
        present: bool,
        reason: str | None = None,
        request_ref: str | None = None,
    ) -> VaultMutationResult:
        self.calls.append(
            {
                "memory_id": memory_id,
                "expected_updated_at": expected_updated_at,
                "persona_subject_id": persona_subject_id,
                "link_kind": link_kind,
                "present": present,
                "reason": reason,
                "request_ref": request_ref,
            }
        )
        if self.error is not None:
            raise self.error
        assert self.result is not None, "fake mutation result not configured"
        return self.result


class FakeVaultCreationService:
    """Records calls and returns typed C6 creation results."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.result: VaultCreationResult | None = None
        self.error: Exception | None = None

    def create_memory(
        self,
        *,
        content: str,
        request_ref: str | None = None,
    ):
        from guardian.services.memory_vault_creation import (
            MemoryVaultCreationError,
            MemoryVaultCreationIntegrityError,
            VaultCreationResult,
        )

        self.calls.append({"content": content, "request_ref": request_ref})
        if self.error is not None:
            raise self.error
        assert self.result is not None, "fake creation result not configured"
        return self.result


def _canonical_item(memory_id: str = "mem-1", **overrides: Any) -> VaultItem:
    kwargs: dict[str, Any] = dict(
        identity=VaultIdentity(kind="canonical", canonical_memory_id=memory_id),
        semantic_species=MemorySemanticSpecies.EPISODIC_SEMANTIC_MEMORY.value,
        content="hello",
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
    kwargs.update(overrides)
    return VaultItem(**kwargs)


def _compat_item(
    source_id: int = 42,
    *,
    source_kind: MemoryCompatibilitySourceKind = (
        MemoryCompatibilitySourceKind.MEMORY_ENTRY
    ),
    **overrides: Any,
) -> VaultItem:
    kwargs: dict[str, Any] = dict(
        identity=VaultIdentity(
            kind="compatibility",
            compatibility_source=MemoryCompatibilitySourceRef(
                source_kind=source_kind,
                source_id=source_id,
            ),
        ),
        semantic_species=MemorySemanticSpecies.EPISODIC_SEMANTIC_MEMORY.value,
        content=None,
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
        compatibility_legacy_source_family=source_kind.value,
        compatibility_legacy_source_record_id=f"{source_kind.value}:{source_id}",
        compatibility_semantic_species=(
            MemorySemanticSpecies.EPISODIC_SEMANTIC_MEMORY.value
        ),
    )
    kwargs.update(overrides)
    return VaultItem(**kwargs)


def _build_client(
    *,
    api_key_override: bool = True,
    scope: RequestUserScope | None = None,
    service_factory: Any | None = None,
    mutation_factory: Any | None = None,
    creation_factory: Any | None = None,
) -> TestClient:
    app = FastAPI()
    app.include_router(memory_vault.router)
    if api_key_override:
        app.dependency_overrides[memory_vault.require_api_key] = lambda: "test-key"
    if scope is not None:
        app.dependency_overrides[memory_vault.get_request_user_scope] = lambda: scope
    if service_factory is not None:
        app.dependency_overrides[memory_vault.get_memory_vault_read_service] = (
            service_factory
        )
    if mutation_factory is not None:
        app.dependency_overrides[memory_vault.get_memory_vault_mutation_service] = (
            mutation_factory
        )
    if creation_factory is not None:
        app.dependency_overrides[memory_vault.get_memory_vault_creation_service] = (
            creation_factory
        )
    return TestClient(app)


@pytest.fixture
def fake_service() -> FakeVaultService:
    return FakeVaultService()


@pytest.fixture
def fake_mutation_service() -> FakeVaultMutationService:
    return FakeVaultMutationService()


@pytest.fixture
def fake_creation_service() -> FakeVaultCreationService:
    return FakeVaultCreationService()


@pytest.fixture
def client(
    fake_service: FakeVaultService,
    fake_mutation_service: FakeVaultMutationService,
    fake_creation_service: FakeVaultCreationService,
) -> TestClient:
    captured: dict[str, Any] = {}

    def fake_factory(
        scope: RequestUserScope = Depends(get_request_user_scope),
    ) -> FakeVaultService:
        captured["account_id"] = scope.account_id
        captured["user_id"] = scope.user_id
        return fake_service

    def mutation_factory(
        scope: RequestUserScope = Depends(get_request_user_scope),
    ) -> FakeVaultMutationService:
        return fake_mutation_service

    def creation_factory(
        scope: RequestUserScope = Depends(get_request_user_scope),
    ) -> FakeVaultCreationService:
        captured["creation_account_id"] = scope.account_id
        return fake_creation_service

    scope = RequestUserScope(
        user_id="legacy-a",
        subject_id="subject-a",
        account_id=ACCOUNT_A,
        multi_user_enabled=True,
    )
    return _build_client(
        scope=scope,
        service_factory=fake_factory,
        mutation_factory=mutation_factory,
        creation_factory=creation_factory,
    )


# ---------------------------------------------------------------------------
# Authentication.
# ---------------------------------------------------------------------------


def test_list_requires_api_key() -> None:
    """The router requires repository-standard API-key posture."""
    fake = FakeVaultService()
    fake.list_result = [_canonical_item()]
    scope = RequestUserScope(account_id=ACCOUNT_A)
    client = _build_client(
        api_key_override=False,
        scope=scope,
        service_factory=lambda: fake,
    )
    # The repository TestClient auto-injects a valid key, so send an
    # explicit invalid key to prove the API-key dependency is enforced.
    response = client.get(
        "/api/memory-vault/items", headers={"X-API-Key": "invalid-key"}
    )
    assert response.status_code == 401


def test_list_requires_stable_account_scope() -> None:
    """A blank/missing stable account id fails authentication (401)."""
    blank = RequestUserScope(user_id="legacy-a", account_id="", multi_user_enabled=True)
    client = _build_client(api_key_override=True, scope=blank)
    response = client.get("/api/memory-vault/items")
    assert response.status_code == 401


def test_legacy_user_id_without_account_does_not_authorize() -> None:
    """A populated legacy user_id with a blank account id does NOT
    authorize memory access (no legacy fallback)."""
    legacy_only = RequestUserScope(
        user_id="legacy-user",
        account_id="",
        multi_user_enabled=True,
    )
    client = _build_client(api_key_override=True, scope=legacy_only)
    response = client.get("/api/memory-vault/items")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Caller-supplied identity rejection.
# ---------------------------------------------------------------------------


def test_caller_account_query_params_have_no_authority() -> None:
    """Caller-provided account/user query values never change the
    account bound to the service."""
    captured: dict[str, Any] = {}
    fake = FakeVaultService()
    fake.list_result = [_canonical_item()]

    def fake_factory(
        scope: RequestUserScope = Depends(get_request_user_scope),
    ) -> FakeVaultService:
        captured["account_id"] = scope.account_id
        return fake

    scope = RequestUserScope(user_id="legacy-a", account_id=ACCOUNT_A)
    client = _build_client(scope=scope, service_factory=fake_factory)

    response = client.get(
        "/api/memory-vault/items",
        params={"user_id": ACCOUNT_B, "account_id": ACCOUNT_B},
    )
    assert response.status_code == 200
    assert captured["account_id"] == ACCOUNT_A


# ---------------------------------------------------------------------------
# List delegation.
# ---------------------------------------------------------------------------


def test_list_default_limit_is_50(
    fake_service: FakeVaultService, client: TestClient
) -> None:
    fake_service.list_result = [_canonical_item("a")]
    response = client.get("/api/memory-vault/items")
    assert response.status_code == 200
    body = response.json()
    assert body["limit"] == DEFAULT_LIST_LIMIT
    assert body["offset"] == 0
    assert body["returned_count"] == 1
    assert len(fake_service.list_calls) == 1
    assert fake_service.list_calls[0]["limit"] == DEFAULT_LIST_LIMIT
    assert fake_service.list_calls[0]["offset"] == 0


def test_list_max_limit_is_100(
    fake_service: FakeVaultService, client: TestClient
) -> None:
    response = client.get("/api/memory-vault/items", params={"limit": 100})
    assert response.status_code == 200
    assert response.json()["limit"] == 100
    assert fake_service.list_calls[0]["limit"] == 100


def test_list_exact_delegation_limit_offset(
    fake_service: FakeVaultService, client: TestClient
) -> None:
    """HTTP limit and offset reach the service exactly, never widened."""
    fake_service.list_result = [_canonical_item("a")]
    response = client.get(
        "/api/memory-vault/items", params={"limit": 100, "offset": 50}
    )
    assert response.status_code == 200
    assert len(fake_service.list_calls) == 1
    assert fake_service.list_calls[0]["limit"] == 100
    assert fake_service.list_calls[0]["offset"] == 50


def test_list_does_not_slice_service_result(
    fake_service: FakeVaultService, client: TestClient
) -> None:
    """The route serializes the service's already-paginated sequence
    unchanged; it performs no second slice."""
    fake_service.list_result = [_canonical_item(f"m{i}") for i in range(5)]
    response = client.get("/api/memory-vault/items", params={"limit": 2, "offset": 3})
    assert response.status_code == 200
    body = response.json()
    ids = [it["identity"]["canonical_memory_id"] for it in body["items"]]
    assert ids == [f"m{i}" for i in range(5)]
    assert body["returned_count"] == 5
    # The service received the exact (unwidened) page request.
    assert fake_service.list_calls[0]["limit"] == 2
    assert fake_service.list_calls[0]["offset"] == 3


def test_list_maps_all_nine_filters_exactly(
    fake_service: FakeVaultService, client: TestClient
) -> None:
    response = client.get(
        "/api/memory-vault/items",
        params={
            "semantic_species": "episodic_semantic_memory",
            "project_id": 7,
            "account_scoped_only": "true",
            "persona_subject_id": "ps-1",
            "review_posture": "approved",
            "lifecycle_posture": "active",
            "source_system": "codexify",
            "pinned": "true",
            "held": "false",
        },
    )
    assert response.status_code == 200
    assert len(fake_service.list_calls) == 1
    flt = fake_service.list_calls[0]["filter"]
    assert isinstance(flt, VaultListFilter)
    assert flt.semantic_species == "episodic_semantic_memory"
    assert flt.project_id == 7
    assert flt.account_scoped_only is True
    assert flt.persona_subject_id == "ps-1"
    assert flt.review_posture == "approved"
    assert flt.lifecycle_posture == "active"
    assert flt.source_system == "codexify"
    assert flt.pinned is True
    assert flt.held is False


def test_list_receives_one_filter_object_and_does_not_filter_locally(
    fake_service: FakeVaultService, client: TestClient
) -> None:
    """The route delegates filtering to B1; it does not re-filter the
    returned items."""
    # Items that do NOT match the requested species are still returned
    # because the fake service (B1 authority) is the only filter.
    fake_service.list_result = [
        _canonical_item("a"),
        _compat_item(1),
        _canonical_item("b"),
    ]
    response = client.get(
        "/api/memory-vault/items",
        params={"semantic_species": "episodic_semantic_memory"},
    )
    assert response.status_code == 200
    assert len(fake_service.list_calls) == 1
    assert isinstance(fake_service.list_calls[0]["filter"], VaultListFilter)
    assert len(response.json()["items"]) == 3


def test_list_bounds(fake_service: FakeVaultService, client: TestClient) -> None:
    assert client.get("/api/memory-vault/items", params={"limit": 0}).status_code == 422
    assert (
        client.get("/api/memory-vault/items", params={"limit": 101}).status_code == 422
    )
    assert (
        client.get("/api/memory-vault/items", params={"offset": -1}).status_code == 422
    )


def test_invalid_canonical_filter_values_are_422(
    fake_service: FakeVaultService, client: TestClient
) -> None:
    assert (
        client.get(
            "/api/memory-vault/items", params={"semantic_species": "bogus"}
        ).status_code
        == 422
    )
    assert (
        client.get(
            "/api/memory-vault/items", params={"review_posture": "bogus"}
        ).status_code
        == 422
    )
    assert (
        client.get(
            "/api/memory-vault/items", params={"lifecycle_posture": "bogus"}
        ).status_code
        == 422
    )


# ---------------------------------------------------------------------------
# Canonical detail.
# ---------------------------------------------------------------------------


def test_canonical_detail_constructs_exact_identity(
    fake_service: FakeVaultService, client: TestClient
) -> None:
    fake_service.get_result = _canonical_item("mem-1")
    response = client.get("/api/memory-vault/items/canonical/mem-1")
    assert response.status_code == 200
    assert len(fake_service.get_calls) == 1
    identity = fake_service.get_calls[0]
    assert identity == VaultIdentity(kind="canonical", canonical_memory_id="mem-1")
    assert identity.canonical_memory_id == "mem-1"


def test_canonical_detail_serializes_full_item(
    fake_service: FakeVaultService, client: TestClient
) -> None:
    fake_service.get_result = _canonical_item("mem-1")
    response = client.get("/api/memory-vault/items/canonical/mem-1")
    assert response.status_code == 200
    body = response.json()
    assert body["identity"]["kind"] == "canonical"
    assert body["identity"]["canonical_memory_id"] == "mem-1"
    assert body["identity"]["compatibility_source"] is None
    assert body["semantic_species"] == "episodic_semantic_memory"
    assert body["content"] == "hello"
    assert body["account_owner"] == ACCOUNT_A


def test_canonical_detail_unavailable_is_generic_404(
    fake_service: FakeVaultService, client: TestClient
) -> None:
    fake_service.get_result = None
    response = client.get("/api/memory-vault/items/canonical/missing")
    assert response.status_code == 404
    assert response.json()["detail"] == GENERIC_UNAVAILABLE_DETAIL


# ---------------------------------------------------------------------------
# Compatibility detail.
# ---------------------------------------------------------------------------


def test_compatibility_detail_constructs_exact_source_ref(
    fake_service: FakeVaultService, client: TestClient
) -> None:
    fake_service.get_result = _compat_item(42)
    response = client.get("/api/memory-vault/items/compatibility/memory_entries/42")
    assert response.status_code == 200
    assert len(fake_service.get_calls) == 1
    identity = fake_service.get_calls[0]
    assert identity.kind == "compatibility"
    assert identity.compatibility_source == MemoryCompatibilitySourceRef(
        source_kind=MemoryCompatibilitySourceKind.MEMORY_ENTRY,
        source_id=42,
    )


def test_compatibility_detail_preserves_typed_identity(
    fake_service: FakeVaultService, client: TestClient
) -> None:
    fake_service.get_result = _compat_item(
        7, source_kind=MemoryCompatibilitySourceKind.PERSONAL_FACT
    )
    response = client.get("/api/memory-vault/items/compatibility/personal_facts/7")
    assert response.status_code == 200
    body = response.json()
    assert body["identity"]["kind"] == "compatibility"
    assert body["identity"]["canonical_memory_id"] is None
    assert body["identity"]["compatibility_source"] == {
        "source_kind": "personal_facts",
        "source_id": 7,
    }


def test_compatibility_detail_invalid_source_kind_is_422(
    fake_service: FakeVaultService, client: TestClient
) -> None:
    response = client.get("/api/memory-vault/items/compatibility/bogus/1")
    assert response.status_code == 422


def test_compatibility_detail_unavailable_is_generic_404(
    fake_service: FakeVaultService, client: TestClient
) -> None:
    fake_service.get_result = None
    response = client.get("/api/memory-vault/items/compatibility/memory_entries/42")
    assert response.status_code == 404
    assert response.json()["detail"] == GENERIC_UNAVAILABLE_DETAIL


def test_unavailable_posture_is_identical_for_both_identity_kinds(
    fake_service: FakeVaultService, client: TestClient
) -> None:
    fake_service.get_result = None
    canonical = client.get("/api/memory-vault/items/canonical/missing")
    compatibility = client.get(
        "/api/memory-vault/items/compatibility/memory_entries/42"
    )
    assert canonical.status_code == 404
    assert compatibility.status_code == 404
    assert canonical.json() == compatibility.json()


# ---------------------------------------------------------------------------
# Integrity failure.
# ---------------------------------------------------------------------------


def test_integrity_failure_does_not_leak_internals(
    fake_service: FakeVaultService, client: TestClient
) -> None:
    fake_service.get_error = MemoryVaultReadError(
        "deliberately sensitive internal text: account=secret persona=secret "
        "content=secret provenance=secret SQL=secret traceback=secret"
    )
    response = client.get("/api/memory-vault/items/canonical/mem-1")
    assert response.status_code == 409
    body = response.json()
    assert "deliberately sensitive" not in response.text
    assert "secret" not in response.text.lower()
    assert body == {"detail": "Memory projection unavailable"}


def test_list_integrity_failure_is_fail_closed(
    fake_service: FakeVaultService, client: TestClient
) -> None:
    fake_service.list_error = MemoryVaultReadError("internal-boom-account-a")
    response = client.get("/api/memory-vault/items")
    assert response.status_code == 409
    assert "internal-boom-account-a" not in response.text
    assert response.json() == {"detail": "Memory projection unavailable"}


# ---------------------------------------------------------------------------
# Serialization fidelity.
# ---------------------------------------------------------------------------


def test_rich_canonical_item_serialization_is_complete(
    fake_service: FakeVaultService, client: TestClient
) -> None:
    created = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    updated = datetime(2026, 2, 3, 4, 5, 6, tzinfo=timezone.utc)
    rich = VaultItem(
        identity=VaultIdentity(kind="canonical", canonical_memory_id="mem-rich"),
        semantic_species=MemorySemanticSpecies.VERIFIED_PERSONAL_FACT.value,
        content="fact payload",
        account_owner=ACCOUNT_A,
        project_id=9000,
        review_posture="disputed",
        lifecycle_posture="inactive",
        pinned=True,
        held=True,
        created_at=created,
        updated_at=updated,
        persona_links=[
            VaultPersonaLink(
                link_id="link-1",
                persona_subject_id="ps-1",
                persona_user_id=ACCOUNT_A,
                link_kind="captured_under",
                display_name_snapshot="Persona One",
            ),
            VaultPersonaLink(
                link_id="link-2",
                persona_subject_id="ps-2",
                persona_user_id=ACCOUNT_A,
                link_kind="associated_with",
                display_name_snapshot=None,
            ),
        ],
        provenance=[
            VaultProvenance(
                provenance_id="prov-1",
                source_system="codexify",
                source_record_id="opaque-ext-1",
                source_thread_id=None,
                source_message_id=None,
                source_import_job_id=None,
                source_export_fingerprint="fp-1",
                source_subject_kind="chat",
                source_subject_id="opaque-subject-1",
                is_imported=True,
            ),
            VaultProvenance(
                provenance_id="prov-2",
                source_system="openai",
                source_record_id="opaque-ext-2",
                source_export_fingerprint=None,
                is_imported=False,
            ),
        ],
        extensions={"k": "v", "nested": {"a": 1}},
    )
    fake_service.get_result = rich
    response = client.get("/api/memory-vault/items/canonical/mem-rich")
    assert response.status_code == 200
    body = response.json()

    assert body["identity"] == {
        "kind": "canonical",
        "canonical_memory_id": "mem-rich",
        "compatibility_source": None,
    }
    assert body["semantic_species"] == "verified_personal_fact"
    assert body["content"] == "fact payload"
    assert body["account_owner"] == ACCOUNT_A
    assert body["project_id"] == 9000
    assert body["review_posture"] == "disputed"
    assert body["lifecycle_posture"] == "inactive"
    assert body["pinned"] is True
    assert body["held"] is True
    assert "2026-01-02T03:04:05" in body["created_at"]
    assert "2026-02-03T04:05:06" in body["updated_at"]

    assert len(body["persona_links"]) == 2
    assert body["persona_links"][0] == {
        "link_id": "link-1",
        "persona_subject_id": "ps-1",
        "persona_user_id": ACCOUNT_A,
        "link_kind": "captured_under",
        "display_name_snapshot": "Persona One",
    }
    assert body["persona_links"][1]["link_kind"] == "associated_with"
    assert body["persona_links"][1]["display_name_snapshot"] is None

    assert len(body["provenance"]) == 2
    assert body["provenance"][0]["provenance_id"] == "prov-1"
    assert body["provenance"][0]["source_system"] == "codexify"
    assert body["provenance"][0]["source_record_id"] == "opaque-ext-1"
    assert body["provenance"][0]["source_export_fingerprint"] == "fp-1"
    assert body["provenance"][0]["source_subject_kind"] == "chat"
    assert body["provenance"][0]["source_subject_id"] == "opaque-subject-1"
    assert body["provenance"][0]["is_imported"] is True
    assert body["provenance"][1]["source_system"] == "openai"
    assert body["provenance"][1]["is_imported"] is False

    assert body["extensions"] == {"k": "v", "nested": {"a": 1}}


def test_compatibility_unavailable_fields_stay_none(
    fake_service: FakeVaultService, client: TestClient
) -> None:
    item = VaultItem(
        identity=VaultIdentity(
            kind="compatibility",
            compatibility_source=MemoryCompatibilitySourceRef(
                source_kind=MemoryCompatibilitySourceKind.PERSONAL_FACT,
                source_id=99,
            ),
        ),
        semantic_species=MemorySemanticSpecies.CANDIDATE_UNREVIEWED_FACT.value,
        content=None,
        account_owner=ACCOUNT_A,
        project_id=None,
        review_posture="pending",
        lifecycle_posture="inactive",
        pinned=False,
        held=False,
        created_at=None,
        updated_at=None,
        persona_links=[],
        provenance=[
            VaultProvenance(
                provenance_id="prov-none",
                source_system="codexify",
                source_record_id="personal_facts:99",
            )
        ],
        extensions=None,
        compatibility_legacy_source_family="personal_facts",
        compatibility_legacy_source_record_id="personal_facts:99",
        compatibility_semantic_species=(
            MemorySemanticSpecies.CANDIDATE_UNREVIEWED_FACT.value
        ),
    )
    fake_service.get_result = item
    response = client.get("/api/memory-vault/items/compatibility/personal_facts/99")
    assert response.status_code == 200
    body = response.json()
    assert body["content"] is None
    assert body["project_id"] is None
    assert body["created_at"] is None
    assert body["updated_at"] is None
    assert body["extensions"] is None
    prov = body["provenance"][0]
    assert prov["source_thread_id"] is None
    assert prov["source_message_id"] is None
    assert prov["source_import_job_id"] is None
    assert prov["source_export_fingerprint"] is None
    assert prov["source_subject_kind"] is None
    assert prov["source_subject_id"] is None
    assert prov["is_imported"] is False


# ---------------------------------------------------------------------------
# Pin/unpin mutation API.
# ---------------------------------------------------------------------------


def _pin_url(memory_id: str) -> str:
    return f"/api/memory-vault/items/canonical/{memory_id}/pin"


def test_pin_mutation_delegates_exactly(
    fake_mutation_service: FakeVaultMutationService, client: TestClient
) -> None:
    item = _canonical_item("mem-1", pinned=True, updated_at=T2)
    fake_mutation_service.result = _mutation_result(
        changed=True,
        receipt_id="receipt-1",
        item=item,
        previous_updated_at=T1,
        resulting_updated_at=T2,
    )
    response = client.patch(
        _pin_url("mem-1"),
        json={
            "pinned": True,
            "expected_updated_at": T1.isoformat(),
            "reason": "operator pin",
            "request_ref": "req-1",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["changed"] is True
    assert body["receipt_id"] == "receipt-1"
    assert "2026-01-01T00:00:00" in body["previous_updated_at"]
    assert "2026-01-02T00:00:00" in body["resulting_updated_at"]
    assert body["item"]["pinned"] is True

    assert len(fake_mutation_service.calls) == 1
    call = fake_mutation_service.calls[0]
    assert call["memory_id"] == "mem-1"
    assert call["expected_updated_at"] == T1
    assert call["pinned"] is True
    assert call["reason"] == "operator pin"
    assert call["request_ref"] == "req-1"


def test_unpin_mutation_delegates(
    fake_mutation_service: FakeVaultMutationService, client: TestClient
) -> None:
    item = _canonical_item("mem-1", pinned=False, updated_at=T2)
    fake_mutation_service.result = _mutation_result(
        changed=True,
        receipt_id="receipt-2",
        item=item,
        previous_updated_at=T1,
        resulting_updated_at=T2,
    )
    response = client.patch(
        _pin_url("mem-1"),
        json={"pinned": False, "expected_updated_at": T1.isoformat()},
    )
    assert response.status_code == 200
    assert fake_mutation_service.calls[0]["pinned"] is False
    assert response.json()["item"]["pinned"] is False


def test_noop_mutation(
    fake_mutation_service: FakeVaultMutationService, client: TestClient
) -> None:
    item = _canonical_item("mem-1", pinned=False, updated_at=T1)
    fake_mutation_service.result = _mutation_result(
        changed=False,
        receipt_id=None,
        item=item,
        previous_updated_at=T1,
        resulting_updated_at=T1,
    )
    response = client.patch(
        _pin_url("mem-1"),
        json={"pinned": False, "expected_updated_at": T1.isoformat()},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["changed"] is False
    assert body["receipt_id"] is None
    assert body["previous_updated_at"] == body["resulting_updated_at"]


def test_stale_conflict_409(
    fake_mutation_service: FakeVaultMutationService, client: TestClient
) -> None:
    fake_mutation_service.error = MemoryVaultMutationConflict("internal stale details")
    response = client.patch(
        _pin_url("mem-1"),
        json={"pinned": True, "expected_updated_at": T1.isoformat()},
    )
    assert response.status_code == 409
    assert response.json() == {"detail": "Memory changed since it was read"}
    assert "internal stale details" not in response.text


def test_missing_cross_account_404(
    fake_mutation_service: FakeVaultMutationService, client: TestClient
) -> None:
    fake_mutation_service.error = MemoryVaultMutationNotAvailable(
        "memory item is not available"
    )
    response = client.patch(
        _pin_url("mem-missing"),
        json={"pinned": True, "expected_updated_at": T1.isoformat()},
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "Memory not available"}


def test_integrity_failure_409(
    fake_mutation_service: FakeVaultMutationService, client: TestClient
) -> None:
    fake_mutation_service.error = MemoryVaultMutationError("internal boom")
    response = client.patch(
        _pin_url("mem-1"),
        json={"pinned": True, "expected_updated_at": T1.isoformat()},
    )
    assert response.status_code == 409
    assert response.json() == {"detail": "Memory mutation unavailable"}
    assert "internal boom" not in response.text


def test_malformed_naive_cas_422(
    fake_mutation_service: FakeVaultMutationService, client: TestClient
) -> None:
    # Missing expected_updated_at.
    assert client.patch(_pin_url("mem-1"), json={"pinned": True}).status_code == 422
    # Malformed timestamp.
    assert (
        client.patch(
            _pin_url("mem-1"),
            json={"pinned": True, "expected_updated_at": "not-a-date"},
        ).status_code
        == 422
    )
    # Naive timestamp (no timezone).
    assert (
        client.patch(
            _pin_url("mem-1"),
            json={
                "pinned": True,
                "expected_updated_at": "2026-01-01T00:00:00",
            },
        ).status_code
        == 422
    )
    # The mutation service is never reached.
    assert fake_mutation_service.calls == []


def test_mutation_requires_stable_account() -> None:
    blank = RequestUserScope(user_id="legacy-a", account_id="", multi_user_enabled=True)
    client = _build_client(api_key_override=True, scope=blank)
    response = client.patch(
        _pin_url("mem-1"),
        json={"pinned": True, "expected_updated_at": T1.isoformat()},
    )
    assert response.status_code == 401


def test_caller_account_override_has_no_authority(
    fake_mutation_service: FakeVaultMutationService,
) -> None:
    captured: dict[str, Any] = {}

    def mutation_factory(
        scope: RequestUserScope = Depends(get_request_user_scope),
    ) -> FakeVaultMutationService:
        captured["account_id"] = scope.account_id
        return fake_mutation_service

    scope = RequestUserScope(user_id="legacy-a", account_id=ACCOUNT_A)
    client = _build_client(scope=scope, mutation_factory=mutation_factory)
    fake_mutation_service.result = _mutation_result(
        changed=True,
        receipt_id="r",
        item=_canonical_item("mem-1", pinned=True, updated_at=T2),
        previous_updated_at=T1,
        resulting_updated_at=T2,
    )
    response = client.patch(
        _pin_url("mem-1"),
        params={"user_id": ACCOUNT_B, "account_id": ACCOUNT_B},
        json={"pinned": True, "expected_updated_at": T1.isoformat()},
    )
    assert response.status_code == 200
    assert captured["account_id"] == ACCOUNT_A


def _hold_url(memory_id: str) -> str:
    return f"/api/memory-vault/items/canonical/{memory_id}/hold"


def test_hold_mutation_delegates_exactly(
    fake_mutation_service: FakeVaultMutationService, client: TestClient
) -> None:
    item = _canonical_item("mem-1", held=True, updated_at=T2)
    fake_mutation_service.result = _mutation_result(
        changed=True,
        receipt_id="receipt-hold",
        item=item,
        previous_updated_at=T1,
        resulting_updated_at=T2,
    )
    response = client.patch(
        _hold_url("mem-1"),
        json={
            "held": True,
            "expected_updated_at": T1.isoformat(),
            "reason": "operator hold",
            "request_ref": "req-hold",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["changed"] is True
    assert body["receipt_id"] == "receipt-hold"
    assert body["item"]["held"] is True

    assert len(fake_mutation_service.calls) == 1
    call = fake_mutation_service.calls[0]
    assert call["memory_id"] == "mem-1"
    assert call["expected_updated_at"] == T1
    assert call["held"] is True
    assert call["reason"] == "operator hold"
    assert call["request_ref"] == "req-hold"


def test_release_mutation_delegates(
    fake_mutation_service: FakeVaultMutationService, client: TestClient
) -> None:
    item = _canonical_item("mem-1", held=False, updated_at=T2)
    fake_mutation_service.result = _mutation_result(
        changed=True,
        receipt_id="receipt-release",
        item=item,
        previous_updated_at=T1,
        resulting_updated_at=T2,
    )
    response = client.patch(
        _hold_url("mem-1"),
        json={"held": False, "expected_updated_at": T1.isoformat()},
    )
    assert response.status_code == 200
    assert fake_mutation_service.calls[0]["held"] is False
    assert response.json()["item"]["held"] is False


def test_hold_noop(
    fake_mutation_service: FakeVaultMutationService, client: TestClient
) -> None:
    item = _canonical_item("mem-1", held=False, updated_at=T1)
    fake_mutation_service.result = _mutation_result(
        changed=False,
        receipt_id=None,
        item=item,
        previous_updated_at=T1,
        resulting_updated_at=T1,
    )
    response = client.patch(
        _hold_url("mem-1"),
        json={"held": False, "expected_updated_at": T1.isoformat()},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["changed"] is False
    assert body["receipt_id"] is None
    assert body["previous_updated_at"] == body["resulting_updated_at"]


def test_hold_stale_conflict_409(
    fake_mutation_service: FakeVaultMutationService, client: TestClient
) -> None:
    fake_mutation_service.error = MemoryVaultMutationConflict("internal stale")
    response = client.patch(
        _hold_url("mem-1"),
        json={"held": True, "expected_updated_at": T1.isoformat()},
    )
    assert response.status_code == 409
    assert response.json() == {"detail": "Memory changed since it was read"}
    assert "internal stale" not in response.text


def test_hold_unavailable_404(
    fake_mutation_service: FakeVaultMutationService, client: TestClient
) -> None:
    fake_mutation_service.error = MemoryVaultMutationNotAvailable("unavailable")
    response = client.patch(
        _hold_url("mem-missing"),
        json={"held": True, "expected_updated_at": T1.isoformat()},
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "Memory not available"}


def test_hold_malformed_naive_cas_422(
    fake_mutation_service: FakeVaultMutationService, client: TestClient
) -> None:
    assert client.patch(_hold_url("mem-1"), json={"held": True}).status_code == 422
    assert (
        client.patch(
            _hold_url("mem-1"),
            json={"held": True, "expected_updated_at": "not-a-date"},
        ).status_code
        == 422
    )
    assert (
        client.patch(
            _hold_url("mem-1"),
            json={"held": True, "expected_updated_at": "2026-01-01T00:00:00"},
        ).status_code
        == 422
    )
    assert fake_mutation_service.calls == []


def test_hold_requires_stable_account() -> None:
    blank = RequestUserScope(user_id="legacy-a", account_id="", multi_user_enabled=True)
    client = _build_client(api_key_override=True, scope=blank)
    response = client.patch(
        _hold_url("mem-1"),
        json={"held": True, "expected_updated_at": T1.isoformat()},
    )
    assert response.status_code == 401


def test_hold_caller_account_override_has_no_authority(
    fake_mutation_service: FakeVaultMutationService,
) -> None:
    captured: dict[str, Any] = {}

    def mutation_factory(
        scope: RequestUserScope = Depends(get_request_user_scope),
    ) -> FakeVaultMutationService:
        captured["account_id"] = scope.account_id
        return fake_mutation_service

    scope = RequestUserScope(user_id="legacy-a", account_id=ACCOUNT_A)
    client = _build_client(scope=scope, mutation_factory=mutation_factory)
    fake_mutation_service.result = _mutation_result(
        changed=True,
        receipt_id="r",
        item=_canonical_item("mem-1", held=True, updated_at=T2),
        previous_updated_at=T1,
        resulting_updated_at=T2,
    )
    response = client.patch(
        _hold_url("mem-1"),
        params={"user_id": ACCOUNT_B, "account_id": ACCOUNT_B},
        json={"held": True, "expected_updated_at": T1.isoformat()},
    )
    assert response.status_code == 200
    assert captured["account_id"] == ACCOUNT_A


# ---------------------------------------------------------------------------
# Project-scope mutation API.
# ---------------------------------------------------------------------------


def _project_scope_url(memory_id: str) -> str:
    return f"/api/memory-vault/items/canonical/{memory_id}/project-scope"


@pytest.mark.parametrize("project_id", [42, 43])
def test_project_scope_set_and_move_delegate_exactly(
    fake_mutation_service: FakeVaultMutationService,
    client: TestClient,
    project_id: int,
) -> None:
    fake_mutation_service.result = _mutation_result(
        changed=True,
        receipt_id="receipt-scope",
        item=_canonical_item("mem-1", project_id=project_id, updated_at=T2),
    )
    response = client.patch(
        _project_scope_url("mem-1"),
        json={
            "project_id": project_id,
            "expected_updated_at": T1.isoformat(),
            "reason": "move scope",
            "request_ref": "req-scope",
        },
    )
    assert response.status_code == 200
    assert response.json()["item"]["project_id"] == project_id
    assert fake_mutation_service.calls == [
        {
            "memory_id": "mem-1",
            "expected_updated_at": T1,
            "project_id": project_id,
            "reason": "move scope",
            "request_ref": "req-scope",
        }
    ]


def test_project_scope_explicit_null_clears(
    fake_mutation_service: FakeVaultMutationService,
    client: TestClient,
) -> None:
    fake_mutation_service.result = _mutation_result(
        changed=True,
        receipt_id="receipt-clear",
        item=_canonical_item("mem-1", project_id=None, updated_at=T2),
    )
    response = client.patch(
        _project_scope_url("mem-1"),
        json={"project_id": None, "expected_updated_at": T1.isoformat()},
    )
    assert response.status_code == 200
    assert response.json()["item"]["project_id"] is None
    assert fake_mutation_service.calls[0]["project_id"] is None


@pytest.mark.parametrize("project_id", [0, -1, True, "42", 1.5])
def test_project_scope_missing_or_invalid_project_id_is_422(
    fake_mutation_service: FakeVaultMutationService,
    client: TestClient,
    project_id: Any,
) -> None:
    missing = client.patch(
        _project_scope_url("mem-1"),
        json={"expected_updated_at": T1.isoformat()},
    )
    invalid = client.patch(
        _project_scope_url("mem-1"),
        json={
            "project_id": project_id,
            "expected_updated_at": T1.isoformat(),
        },
    )
    assert missing.status_code == 422
    assert invalid.status_code == 422
    assert fake_mutation_service.calls == []


def test_project_scope_cas_validation_is_422(
    fake_mutation_service: FakeVaultMutationService,
    client: TestClient,
) -> None:
    for payload in (
        {"project_id": 42},
        {"project_id": 42, "expected_updated_at": "not-a-date"},
        {"project_id": 42, "expected_updated_at": "2026-01-01T00:00:00"},
    ):
        assert (
            client.patch(_project_scope_url("mem-1"), json=payload).status_code == 422
        )
    assert fake_mutation_service.calls == []


@pytest.mark.parametrize(
    ("error", "status", "body"),
    [
        (
            MemoryVaultMutationConflict("internal stale"),
            409,
            {"detail": "Memory changed since it was read"},
        ),
        (
            MemoryVaultProjectNotAvailable("foreign or missing"),
            404,
            {"detail": "Project not available"},
        ),
        (
            MemoryVaultProjectAuthorityConflict("legacy owner secret"),
            409,
            {
                "detail": {
                    "code": "project_ownership_authority_conflict",
                    "message": (
                        "Project ownership metadata conflicts with canonical "
                        "authority."
                    ),
                }
            },
        ),
        (
            MemoryVaultMutationNotAvailable("memory secret"),
            404,
            {"detail": "Memory not available"},
        ),
        (
            MemoryVaultMutationError("sql secret"),
            409,
            {"detail": "Memory mutation unavailable"},
        ),
    ],
)
def test_project_scope_error_mapping(
    fake_mutation_service: FakeVaultMutationService,
    client: TestClient,
    error: Exception,
    status: int,
    body: dict[str, Any],
) -> None:
    fake_mutation_service.error = error
    response = client.patch(
        _project_scope_url("mem-1"),
        json={"project_id": 42, "expected_updated_at": T1.isoformat()},
    )
    assert response.status_code == status
    assert response.json() == body
    assert str(error) not in response.text


def test_project_scope_requires_stable_account() -> None:
    blank = RequestUserScope(user_id="legacy-a", account_id="", multi_user_enabled=True)
    client = _build_client(api_key_override=True, scope=blank)
    response = client.patch(
        _project_scope_url("mem-1"),
        json={"project_id": None, "expected_updated_at": T1.isoformat()},
    )
    assert response.status_code == 401


def test_project_scope_caller_account_override_has_no_authority(
    fake_mutation_service: FakeVaultMutationService,
) -> None:
    captured: dict[str, Any] = {}

    def mutation_factory(
        scope: RequestUserScope = Depends(get_request_user_scope),
    ) -> FakeVaultMutationService:
        captured["account_id"] = scope.account_id
        return fake_mutation_service

    scope = RequestUserScope(user_id="legacy-a", account_id=ACCOUNT_A)
    client = _build_client(scope=scope, mutation_factory=mutation_factory)
    fake_mutation_service.result = _mutation_result(
        changed=True,
        receipt_id="r",
        item=_canonical_item("mem-1", project_id=42, updated_at=T2),
    )
    response = client.patch(
        _project_scope_url("mem-1"),
        params={"user_id": ACCOUNT_B, "account_id": ACCOUNT_B},
        json={"project_id": 42, "expected_updated_at": T1.isoformat()},
    )
    assert response.status_code == 200
    assert captured["account_id"] == ACCOUNT_A


def test_no_compatibility_mutation_route() -> None:
    app = FastAPI()
    app.include_router(memory_vault.router)
    schema = app.openapi()
    for path in schema["paths"]:
        if path.startswith("/api/memory-vault/items/compatibility"):
            assert "patch" not in schema["paths"][path]


# ---------------------------------------------------------------------------
# Read-only HTTP surface.
# ---------------------------------------------------------------------------


def test_router_method_surface() -> None:
    app = FastAPI()
    app.include_router(memory_vault.router)
    schema = app.openapi()
    for path in schema["paths"]:
        if path.startswith("/api/memory-vault"):
            methods = set(schema["paths"][path].keys())
            assert methods <= {
                "get",
                "patch",
                "post",
            }, f"{path} has unexpected methods: {methods}"
    # Explicitly assert no other write methods exist under the Vault
    # namespace beyond the admitted ``POST /api/memory-vault/items``
    # (C6 explicit creation). PUT/DELETE must never appear.
    for path, operations in schema["paths"].items():
        if path.startswith("/api/memory-vault"):
            for forbidden in ("put", "delete"):
                assert forbidden not in operations, f"{path} exposes {forbidden}"
    # Only the explicit creation PATCH route may carry POST.
    assert "post" in schema["paths"]["/api/memory-vault/items"]
    for path, operations in schema["paths"].items():
        if path.startswith("/api/memory-vault") and path != "/api/memory-vault/items":
            assert "post" not in operations, f"{path} exposes post"


# ---------------------------------------------------------------------------
# Persona-attribution mutation API.
# ---------------------------------------------------------------------------


def _persona_attribution_url(memory_id: str) -> str:
    return f"/api/memory-vault/items/canonical/{memory_id}/persona-attribution"


def test_persona_attribution_add_and_remove_delegate_exactly(
    fake_mutation_service: FakeVaultMutationService,
    client: TestClient,
) -> None:
    fake_mutation_service.result = _mutation_result(
        changed=True,
        receipt_id="receipt-persona",
        item=_canonical_item("mem-1", updated_at=T2),
    )
    response = client.patch(
        _persona_attribution_url("mem-1"),
        json={
            "persona_subject_id": "sub-A",
            "link_kind": MemoryPersonaLinkKind.ASSOCIATED_WITH.value,
            "present": True,
            "expected_updated_at": T1.isoformat(),
            "reason": "link A",
            "request_ref": "req-A",
        },
    )
    assert response.status_code == 200
    assert fake_mutation_service.calls == [
        {
            "memory_id": "mem-1",
            "expected_updated_at": T1,
            "persona_subject_id": "sub-A",
            "link_kind": MemoryPersonaLinkKind.ASSOCIATED_WITH,
            "present": True,
            "reason": "link A",
            "request_ref": "req-A",
        }
    ]

    fake_mutation_service.calls.clear()
    fake_mutation_service.result = _mutation_result(
        changed=True,
        receipt_id="receipt-remove",
        item=_canonical_item("mem-1", updated_at=T2),
    )
    response_remove = client.patch(
        _persona_attribution_url("mem-1"),
        json={
            "persona_subject_id": "sub-A",
            "link_kind": MemoryPersonaLinkKind.ASSOCIATED_WITH.value,
            "present": False,
            "expected_updated_at": T1.isoformat(),
        },
    )
    assert response_remove.status_code == 200
    assert fake_mutation_service.calls[0]["present"] is False
    assert (
        fake_mutation_service.calls[0]["link_kind"]
        == MemoryPersonaLinkKind.ASSOCIATED_WITH
    )


def test_persona_attribution_noop_returns_changed_false(
    fake_mutation_service: FakeVaultMutationService,
    client: TestClient,
) -> None:
    fake_mutation_service.result = _mutation_result(
        changed=False,
        receipt_id=None,
        item=_canonical_item("mem-1", updated_at=T1),
    )
    response = client.patch(
        _persona_attribution_url("mem-1"),
        json={
            "persona_subject_id": "sub-A",
            "link_kind": MemoryPersonaLinkKind.CAPTURED_UNDER.value,
            "present": True,
            "expected_updated_at": T1.isoformat(),
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["changed"] is False
    assert body["receipt_id"] is None


def test_persona_attribution_invalid_link_kind_is_422(
    fake_mutation_service: FakeVaultMutationService, client: TestClient
) -> None:
    response = client.patch(
        _persona_attribution_url("mem-1"),
        json={
            "persona_subject_id": "sub-A",
            "link_kind": "not_a_canonical_link_kind",
            "present": True,
            "expected_updated_at": T1.isoformat(),
        },
    )
    assert response.status_code == 422
    assert fake_mutation_service.calls == []


@pytest.mark.parametrize(
    "missing_body",
    [
        {"expected_updated_at": T1.isoformat(), "present": True},
        {
            "persona_subject_id": "sub-A",
            "present": True,
            "expected_updated_at": T1.isoformat(),
        },
        {
            "persona_subject_id": "sub-A",
            "link_kind": MemoryPersonaLinkKind.ASSOCIATED_WITH.value,
            "expected_updated_at": T1.isoformat(),
        },
        {
            "persona_subject_id": "sub-A",
            "link_kind": MemoryPersonaLinkKind.ASSOCIATED_WITH.value,
            "present": True,
        },
    ],
)
def test_persona_attribution_missing_required_field_is_422(
    fake_mutation_service: FakeVaultMutationService,
    client: TestClient,
    missing_body: dict,
) -> None:
    response = client.patch(_persona_attribution_url("mem-1"), json=missing_body)
    assert response.status_code == 422
    assert fake_mutation_service.calls == []


def test_persona_attribution_cas_validation_is_422(
    fake_mutation_service: FakeVaultMutationService, client: TestClient
) -> None:
    base = {
        "persona_subject_id": "sub-A",
        "link_kind": MemoryPersonaLinkKind.ASSOCIATED_WITH.value,
        "present": True,
    }
    for variant in (
        {**base},
        {**base, "expected_updated_at": "not-a-date"},
        {**base, "expected_updated_at": "2026-01-01T00:00:00"},
    ):
        assert (
            client.patch(_persona_attribution_url("mem-1"), json=variant).status_code
            == 422
        )
    assert fake_mutation_service.calls == []


@pytest.mark.parametrize(
    ("error", "status", "body"),
    [
        (
            MemoryVaultMutationConflict("internal stale"),
            409,
            {"detail": "Memory changed since it was read"},
        ),
        (
            MemoryVaultPersonaSubjectNotAvailable("missing"),
            404,
            {"detail": "Persona subject not available"},
        ),
        (
            MemoryVaultPersonaSubjectLifecycleConflict("retired"),
            409,
            {"detail": "Persona subject is not active for new attribution"},
        ),
        (
            MemoryVaultMutationNotAvailable("memory secret"),
            404,
            {"detail": "Memory not available"},
        ),
        (
            MemoryVaultMutationError("sql secret"),
            409,
            {"detail": "Memory mutation unavailable"},
        ),
    ],
)
def test_persona_attribution_error_mapping(
    fake_mutation_service: FakeVaultMutationService,
    client: TestClient,
    error: Exception,
    status: int,
    body: dict,
) -> None:
    fake_mutation_service.error = error
    response = client.patch(
        _persona_attribution_url("mem-1"),
        json={
            "persona_subject_id": "sub-A",
            "link_kind": MemoryPersonaLinkKind.ASSOCIATED_WITH.value,
            "present": True,
            "expected_updated_at": T1.isoformat(),
        },
    )
    assert response.status_code == status
    assert response.json() == body
    assert str(error) not in response.text


def test_persona_attribution_requires_stable_account() -> None:
    blank = RequestUserScope(user_id="legacy-a", account_id="", multi_user_enabled=True)
    client = _build_client(api_key_override=True, scope=blank)
    response = client.patch(
        _persona_attribution_url("mem-1"),
        json={
            "persona_subject_id": "sub-A",
            "link_kind": MemoryPersonaLinkKind.ASSOCIATED_WITH.value,
            "present": True,
            "expected_updated_at": T1.isoformat(),
        },
    )
    assert response.status_code == 401


def test_persona_attribution_rejects_attempted_authority_injection() -> None:
    captured: dict[str, Any] = {}

    def mutation_factory(
        scope: RequestUserScope = Depends(get_request_user_scope),
    ) -> FakeVaultMutationService:
        captured["account_id"] = scope.account_id
        fake = FakeVaultMutationService()
        fake.result = _mutation_result(
            changed=True,
            receipt_id="r",
            item=_canonical_item("mem-1", updated_at=T2),
        )
        return fake

    scope = RequestUserScope(user_id="legacy-a", account_id=ACCOUNT_A)
    client = _build_client(scope=scope, mutation_factory=mutation_factory)
    response = client.patch(
        _persona_attribution_url("mem-1"),
        params={
            "user_id": ACCOUNT_B,
            "account_id": ACCOUNT_B,
            "persona_profile_id": "pro-1",
        },
        json={
            "persona_subject_id": "sub-A",
            "link_kind": MemoryPersonaLinkKind.ASSOCIATED_WITH.value,
            "present": True,
            "expected_updated_at": T1.isoformat(),
        },
    )
    assert response.status_code == 200
    assert captured["account_id"] == ACCOUNT_A


# ---------------------------------------------------------------------------
# C6 direct user-authored creation (POST /api/memory-vault/items).
# ---------------------------------------------------------------------------


def test_create_memory_delegates_exactly(
    fake_creation_service: FakeVaultCreationService,
    client: TestClient,
) -> None:
    fake_creation_service.result = VaultCreationResult(
        receipt_id="receipt-create-1",
        item=_canonical_item(
            "new-mem-1",
            content="The red toolbox is in the garage.",
        ),
    )
    response = client.post(
        "/api/memory-vault/items",
        json={
            "content": "The red toolbox is in the garage.",
            "request_ref": "req-c6-1",
        },
    )
    assert response.status_code == 201
    assert fake_creation_service.calls == [
        {
            "content": "The red toolbox is in the garage.",
            "request_ref": "req-c6-1",
        }
    ]
    body = response.json()
    assert body["receipt_id"] == "receipt-create-1"
    assert body["item"]["identity"]["canonical_memory_id"] == "new-mem-1"


def test_create_memory_account_authority_is_constructor_bound(
    fake_creation_service: FakeVaultCreationService,
    client: TestClient,
) -> None:
    fake_creation_service.result = VaultCreationResult(
        receipt_id="r",
        item=_canonical_item("mem-x"),
    )
    response = client.post(
        "/api/memory-vault/items",
        json={
            "content": "for A only",
            "account_id": ACCOUNT_B,
            "user_id": ACCOUNT_B,
            "memory_id": "client-supplied",
            "project_id": 9999,
            "pinned": True,
            "held": True,
            "semantic_species": "verified_personal_fact",
        },
    )
    assert response.status_code == 201
    # Only the body fields content/request_ref reach the service; the
    # additional keys have zero semantic effect because the model only
    # accepts `content` and `request_ref`.
    assert fake_creation_service.calls == [
        {
            "content": "for A only",
            "request_ref": None,
        }
    ]


def test_create_memory_missing_content_is_422(
    fake_creation_service: FakeVaultCreationService,
    client: TestClient,
) -> None:
    response = client.post("/api/memory-vault/items", json={})
    assert response.status_code == 422
    assert fake_creation_service.calls == []


def test_create_memory_whitespace_only_is_422(
    fake_creation_service: FakeVaultCreationService,
    client: TestClient,
) -> None:
    fake_creation_service.error = MemoryVaultCreationError("content is required")
    response = client.post(
        "/api/memory-vault/items",
        json={"content": "   \n  "},
    )
    assert response.status_code == 422
    assert "Memory" in response.json()["detail"]


def test_create_memory_integrity_failure_is_409(
    fake_creation_service: FakeVaultCreationService,
    client: TestClient,
) -> None:
    fake_creation_service.error = MemoryVaultCreationIntegrityError("internal")
    response = client.post("/api/memory-vault/items", json={"content": "for A only"})
    assert response.status_code == 409
    # Internal exception text must not leak into the HTTP detail.
    assert "internal" not in response.text


def test_create_memory_requires_stable_account() -> None:
    blank = RequestUserScope(user_id="legacy-a", account_id="", multi_user_enabled=True)
    client = _build_client(api_key_override=True, scope=blank)
    response = client.post(
        "/api/memory-vault/items",
        json={"content": "should fail"},
    )
    assert response.status_code == 401


def test_create_memory_methods_posture() -> None:
    """Vault routes now expose GET + POST + PATCH (no PUT/DELETE)."""
    client = _build_client()
    routes = {
        (route.path, tuple(sorted(route.methods - {"HEAD"})))
        for route in memory_vault.router.routes
    }
    has_post_items = any(
        p == "/api/memory-vault/items" and "POST" in m for p, m in routes
    )
    has_get_items = any(
        p == "/api/memory-vault/items" and "GET" in m for p, m in routes
    )
    assert has_post_items
    assert has_get_items
    for path, methods in routes:
        if path.startswith("/api/memory-vault"):
            for forbidden in ("PUT", "DELETE"):
                assert forbidden not in methods, f"{path} exposes {forbidden}"


def test_create_memory_existing_mutation_routes_remain_qualified(
    fake_mutation_service: FakeVaultMutationService,
    client: TestClient,
) -> None:
    """C5 PATCH Persona-attribution route must not have regressed."""
    fake_mutation_service.result = VaultMutationResult(
        changed=True,
        receipt_id="r",
        previous_updated_at=T1,
        resulting_updated_at=T2,
        item=_canonical_item("mem-1"),
    )
    response = client.patch(
        "/api/memory-vault/items/canonical/mem-1/persona-attribution",
        json={
            "persona_subject_id": "sub-A",
            "link_kind": MemoryPersonaLinkKind.ASSOCIATED_WITH.value,
            "present": True,
            "expected_updated_at": T1.isoformat(),
        },
    )
    assert response.status_code == 200
