"""Focused route tests for the authenticated Memory Vault read API (UMS-05B2).

These tests mount ``guardian.routes.memory_vault.router`` on a bare
``FastAPI`` application and use dependency overrides for:

- API-key authority (``require_api_key``);
- stable request-user scope (``get_request_user_scope``);
- the Memory Vault service factory (``get_memory_vault_read_service``).

The service is faked with typed B1 DTO return values. No full Guardian
application is imported or booted, and no supported-profile manifest is
touched.
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
from guardian.protocol_tokens import MemorySemanticSpecies
from guardian.routes import memory_vault
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
    ) -> list[VaultItem]:
        self.list_calls.append({"filter": filter, "limit": limit})
        if self.list_error is not None:
            raise self.list_error
        return list(self.list_result)

    def get_item(self, *, identity: VaultIdentity) -> VaultItem | None:
        self.get_calls.append(identity)
        if self.get_error is not None:
            raise self.get_error
        return self.get_result


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
    return TestClient(app)


@pytest.fixture
def fake_service() -> FakeVaultService:
    return FakeVaultService()


@pytest.fixture
def client(fake_service: FakeVaultService) -> TestClient:
    captured: dict[str, Any] = {}

    def fake_factory(
        scope: RequestUserScope = Depends(get_request_user_scope),
    ) -> FakeVaultService:
        captured["account_id"] = scope.account_id
        captured["user_id"] = scope.user_id
        return fake_service

    scope = RequestUserScope(
        user_id="legacy-a",
        subject_id="subject-a",
        account_id=ACCOUNT_A,
        multi_user_enabled=True,
    )
    return _build_client(scope=scope, service_factory=fake_factory)


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


def test_list_max_limit_is_100(
    fake_service: FakeVaultService, client: TestClient
) -> None:
    response = client.get("/api/memory-vault/items", params={"limit": 100})
    assert response.status_code == 200
    assert response.json()["limit"] == 100
    assert fake_service.list_calls[0]["limit"] == 100


def test_list_offset_mapping(
    fake_service: FakeVaultService, client: TestClient
) -> None:
    fake_service.list_result = [_canonical_item(f"m{i}") for i in range(10)]
    response = client.get("/api/memory-vault/items", params={"offset": 4})
    assert response.status_code == 200
    body = response.json()
    assert body["offset"] == 4
    # The adapter requests a window wide enough to honor the offset.
    assert fake_service.list_calls[0]["limit"] == DEFAULT_LIST_LIMIT + 4
    ids = [it["identity"]["canonical_memory_id"] for it in body["items"]]
    assert ids == [f"m{i}" for i in range(4, 10)]
    assert body["returned_count"] == 6


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
# Read-only HTTP surface.
# ---------------------------------------------------------------------------


def test_router_is_get_only() -> None:
    app = FastAPI()
    app.include_router(memory_vault.router)
    schema = app.openapi()
    for path in schema["paths"]:
        if path.startswith("/api/memory-vault"):
            methods = set(schema["paths"][path].keys())
            assert methods == {"get"}, f"{path} has non-GET methods: {methods}"
    # Explicitly assert no write methods exist under the Vault namespace.
    for path, operations in schema["paths"].items():
        if path.startswith("/api/memory-vault"):
            for forbidden in ("post", "put", "patch", "delete"):
                assert forbidden not in operations, f"{path} exposes {forbidden}"
