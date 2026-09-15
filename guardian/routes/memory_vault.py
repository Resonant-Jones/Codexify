"""Authenticated Memory Vault HTTP adapter (UMS-05B2 / UMS-05C2).

This module exposes the already-qualified Memory Vault read and
pin/unpin mutation authorities over FastAPI:

    GET   /api/memory-vault/items
    GET   /api/memory-vault/items/canonical/{memory_id}
    GET   /api/memory-vault/items/compatibility/{source_kind}/{source_id}
    PATCH /api/memory-vault/items/canonical/{memory_id}/pin

It is an adapter only. It does not:

- query canonical memory tables directly;
- call the compatibility dispatcher directly;
- derive Personal Facts posture;
- resolve Persona authority independently;
- mint route-local memory identities;
- implement CAS, receipts, or no-op logic locally;
- register itself in ``guardian.guardian_api``.

Runtime activation in the Guardian application (route registration,
supported-profile posture, feature-flag posture) is owned by UMS-05B3.
This module is qualified against a directly mounted FastAPI test app
only.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Iterator, Literal

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel, field_validator

from guardian.core.dependencies import (
    RequestUserScope,
    get_request_user_scope,
    require_api_key,
)
from guardian.core.memory_compatibility import (
    MemoryCompatibilitySourceKind,
    MemoryCompatibilitySourceRef,
)
from guardian.protocol_tokens import MemorySemanticSpecies
from guardian.services.memory_vault_mutation import (
    MemoryVaultMutationConflict,
    MemoryVaultMutationError,
    MemoryVaultMutationNotAvailable,
    MemoryVaultMutationService,
)
from guardian.services.memory_vault_read import (
    DEFAULT_LIST_LIMIT,
    LIFECYCLE_POSTURE_ACTIVE,
    LIFECYCLE_POSTURE_INACTIVE,
    MAX_LIST_LIMIT,
    REVIEW_POSTURE_APPROVED,
    REVIEW_POSTURE_DISPUTED,
    REVIEW_POSTURE_PENDING,
    MemoryVaultReadError,
    MemoryVaultReadService,
    VaultIdentity,
    VaultItem,
    VaultListFilter,
)

router = APIRouter(
    prefix="/api/memory-vault",
    tags=["Memory Vault"],
    dependencies=[Depends(require_api_key)],
)

#: Canonical review-posture vocabulary. Referenced from the B1 read
#: service so the route never redefines the token set.
ReviewPostureParam = Literal[
    REVIEW_POSTURE_PENDING,
    REVIEW_POSTURE_APPROVED,
    REVIEW_POSTURE_DISPUTED,
]

#: Canonical lifecycle-posture vocabulary. Referenced from the B1 read
#: service so the route never redefines the token set.
LifecyclePostureParam = Literal[
    LIFECYCLE_POSTURE_ACTIVE,
    LIFECYCLE_POSTURE_INACTIVE,
]

_GENERIC_UNAVAILABLE_DETAIL = "Memory item unavailable"
_PROJECTION_UNAVAILABLE_DETAIL = "Memory projection unavailable"
_STABLE_ACCOUNT_REQUIRED_DETAIL = "Stable account identity required"
_MUTATION_UNAVAILABLE_DETAIL = "Memory not available"
_STALE_WRITE_DETAIL = "Memory changed since it was read"
_MUTATION_INTEGRITY_DETAIL = "Memory mutation unavailable"


# ---------------------------------------------------------------------------
# Response models.
# ---------------------------------------------------------------------------


class MemoryCompatibilitySourceRefResponse(BaseModel):
    """Serialized compatibility source reference (typed, verbatim)."""

    source_kind: MemoryCompatibilitySourceKind
    source_id: int


class VaultIdentityResponse(BaseModel):
    """Serialized authoritative Vault identity.

    Canonical identities carry ``canonical_memory_id`` with a null
    ``compatibility_source``; compatibility identities carry the typed
    ``compatibility_source`` with a null ``canonical_memory_id``.
    """

    kind: str
    canonical_memory_id: str | None = None
    compatibility_source: MemoryCompatibilitySourceRefResponse | None = None


class VaultPersonaLinkResponse(BaseModel):
    """Serialized stable-Persona attribution link."""

    link_id: str
    persona_subject_id: str
    persona_user_id: str
    link_kind: str
    display_name_snapshot: str | None = None


class VaultProvenanceResponse(BaseModel):
    """Serialized provenance row (multiplicity preserved)."""

    provenance_id: str
    source_system: str
    source_record_id: str | None = None
    source_thread_id: int | None = None
    source_message_id: int | None = None
    source_import_job_id: str | None = None
    source_export_fingerprint: str | None = None
    source_subject_kind: str | None = None
    source_subject_id: str | None = None
    is_imported: bool = False


class VaultItemResponse(BaseModel):
    """Serialized operator-facing projection of one memory item."""

    identity: VaultIdentityResponse
    semantic_species: str
    content: str | None = None
    account_owner: str = ""
    project_id: int | None = None
    review_posture: str = REVIEW_POSTURE_PENDING
    lifecycle_posture: str = LIFECYCLE_POSTURE_INACTIVE
    pinned: bool = False
    held: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None
    persona_links: list[VaultPersonaLinkResponse] = []
    provenance: list[VaultProvenanceResponse] = []
    extensions: dict[str, Any] | None = None
    compatibility_legacy_source_family: str | None = None
    compatibility_legacy_source_record_id: str | None = None
    compatibility_semantic_species: str | None = None


class VaultListResponse(BaseModel):
    """Serialized bounded Vault list page."""

    items: list[VaultItemResponse]
    limit: int
    offset: int
    returned_count: int


class _VaultMutationRequest(BaseModel):
    """Shared request shape for canonical Vault governance mutations."""

    expected_updated_at: datetime
    reason: str | None = None
    request_ref: str | None = None

    @field_validator("expected_updated_at")
    @classmethod
    def _require_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("expected_updated_at must be timezone-aware")
        return value


class VaultPinRequest(_VaultMutationRequest):
    """Request body for canonical pin/unpin mutation."""

    pinned: bool


class VaultHoldRequest(_VaultMutationRequest):
    """Request body for canonical hold/release-hold mutation."""

    held: bool


class VaultMutationResponse(BaseModel):
    """Serialized Vault governance mutation result."""

    changed: bool
    receipt_id: str | None
    previous_updated_at: datetime
    resulting_updated_at: datetime
    item: VaultItemResponse


# ---------------------------------------------------------------------------
# Account resolution and service dependency.
# ---------------------------------------------------------------------------


def _resolve_vault_account(scope: RequestUserScope) -> str:
    """Return the stable account id that owns Vault content authority.

    The account comes exclusively from ``RequestUserScope.account_id``.
    A blank/missing account id fails authentication (401); there is no
    legacy ``user_id`` fallback and no single-user default for Vault
    content access.
    """
    account_id = (scope.account_id or "").strip()
    if not account_id:
        raise HTTPException(
            status_code=401,
            detail=_STABLE_ACCOUNT_REQUIRED_DETAIL,
        )
    return account_id


def _get_vault_db() -> Any:
    """Return the repository-standard GuardianDB using the existing env authority."""
    from guardian.core.db import load_guardian_db_from_env

    db = load_guardian_db_from_env()
    if db is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    return db


def get_memory_vault_read_service(
    scope: RequestUserScope = Depends(get_request_user_scope),
) -> Iterator[MemoryVaultReadService]:
    """Bind a ``MemoryVaultReadService`` to the authenticated account.

    This is the dependency-overridable service factory. The B1 service
    remains the read authority; the route never queries canonical
    memory tables or compatibility adapters directly.
    """
    account_id = _resolve_vault_account(scope)
    db = _get_vault_db()
    session = db.get_session()
    try:
        yield MemoryVaultReadService(
            session,
            authenticated_account_id=account_id,
        )
    finally:
        session.close()


def get_memory_vault_mutation_service(
    scope: RequestUserScope = Depends(get_request_user_scope),
) -> Iterator[MemoryVaultMutationService]:
    """Bind a ``MemoryVaultMutationService`` to the authenticated account.

    Reuses the same repository database/session authority as the read
    service; the C1 mutation service remains the mutation authority.
    """
    account_id = _resolve_vault_account(scope)
    db = _get_vault_db()
    session = db.get_session()
    try:
        yield MemoryVaultMutationService(
            session,
            authenticated_account_id=account_id,
        )
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Serialization helpers.
# ---------------------------------------------------------------------------


def _source_ref_response(
    ref: MemoryCompatibilitySourceRef | None,
) -> MemoryCompatibilitySourceRefResponse | None:
    if ref is None:
        return None
    return MemoryCompatibilitySourceRefResponse(
        source_kind=ref.source_kind,
        source_id=ref.source_id,
    )


def _identity_response(identity: VaultIdentity) -> VaultIdentityResponse:
    return VaultIdentityResponse(
        kind=identity.kind,
        canonical_memory_id=identity.canonical_memory_id,
        compatibility_source=_source_ref_response(identity.compatibility_source),
    )


def _item_response(item: VaultItem) -> VaultItemResponse:
    return VaultItemResponse(
        identity=_identity_response(item.identity),
        semantic_species=item.semantic_species,
        content=item.content,
        account_owner=item.account_owner,
        project_id=item.project_id,
        review_posture=item.review_posture,
        lifecycle_posture=item.lifecycle_posture,
        pinned=item.pinned,
        held=item.held,
        created_at=item.created_at,
        updated_at=item.updated_at,
        persona_links=[
            VaultPersonaLinkResponse(
                link_id=link.link_id,
                persona_subject_id=link.persona_subject_id,
                persona_user_id=link.persona_user_id,
                link_kind=link.link_kind,
                display_name_snapshot=link.display_name_snapshot,
            )
            for link in item.persona_links
        ],
        provenance=[
            VaultProvenanceResponse(
                provenance_id=prov.provenance_id,
                source_system=prov.source_system,
                source_record_id=prov.source_record_id,
                source_thread_id=prov.source_thread_id,
                source_message_id=prov.source_message_id,
                source_import_job_id=prov.source_import_job_id,
                source_export_fingerprint=prov.source_export_fingerprint,
                source_subject_kind=prov.source_subject_kind,
                source_subject_id=prov.source_subject_id,
                is_imported=prov.is_imported,
            )
            for prov in item.provenance
        ],
        extensions=item.extensions,
        compatibility_legacy_source_family=item.compatibility_legacy_source_family,
        compatibility_legacy_source_record_id=(
            item.compatibility_legacy_source_record_id
        ),
        compatibility_semantic_species=item.compatibility_semantic_species,
    )


# ---------------------------------------------------------------------------
# Endpoints.
# ---------------------------------------------------------------------------


@router.get("/items", response_model=VaultListResponse)
def list_vault_items(
    limit: int = Query(DEFAULT_LIST_LIMIT, ge=1, le=MAX_LIST_LIMIT),
    offset: int = Query(0, ge=0),
    semantic_species: MemorySemanticSpecies | None = Query(None),
    project_id: int | None = Query(None),
    account_scoped_only: bool = Query(False),
    persona_subject_id: str | None = Query(None),
    review_posture: ReviewPostureParam | None = Query(None),
    lifecycle_posture: LifecyclePostureParam | None = Query(None),
    source_system: str | None = Query(None),
    pinned: bool | None = Query(None),
    held: bool | None = Query(None),
    service: MemoryVaultReadService = Depends(get_memory_vault_read_service),
) -> VaultListResponse:
    """List the authenticated account's Vault items (bounded, read-only).

    The route is a pure HTTP adapter. Both semantic filtering and
    logical pagination (``offset`` + ``limit``) are delegated to the B1
    service; the route performs no list slicing and never widens the
    requested page size.
    """
    flt = VaultListFilter(
        semantic_species=(
            semantic_species.value if semantic_species is not None else None
        ),
        project_id=project_id,
        account_scoped_only=account_scoped_only,
        persona_subject_id=persona_subject_id,
        review_posture=review_posture,
        lifecycle_posture=lifecycle_posture,
        source_system=source_system,
        pinned=pinned,
        held=held,
    )

    try:
        items = service.list_items(filter=flt, limit=limit, offset=offset)
    except MemoryVaultReadError:
        raise HTTPException(
            status_code=409,
            detail=_PROJECTION_UNAVAILABLE_DETAIL,
        )

    return VaultListResponse(
        items=[_item_response(item) for item in items],
        limit=limit,
        offset=offset,
        returned_count=len(items),
    )


@router.get("/items/canonical/{memory_id}", response_model=VaultItemResponse)
def get_canonical_vault_item(
    memory_id: str,
    service: MemoryVaultReadService = Depends(get_memory_vault_read_service),
) -> VaultItemResponse:
    """Return one canonical Vault item by its authoritative memory id."""
    identity = VaultIdentity(
        kind="canonical",
        canonical_memory_id=memory_id,
    )
    try:
        item = service.get_item(identity=identity)
    except MemoryVaultReadError:
        raise HTTPException(
            status_code=409,
            detail=_PROJECTION_UNAVAILABLE_DETAIL,
        )

    if item is None:
        raise HTTPException(status_code=404, detail=_GENERIC_UNAVAILABLE_DETAIL)
    return _item_response(item)


@router.get(
    "/items/compatibility/{source_kind}/{source_id}",
    response_model=VaultItemResponse,
)
def get_compatibility_vault_item(
    source_kind: MemoryCompatibilitySourceKind,
    source_id: int,
    service: MemoryVaultReadService = Depends(get_memory_vault_read_service),
) -> VaultItemResponse:
    """Return one compatibility Vault item by its typed source reference.

    The source kind is validated against the existing
    ``MemoryCompatibilitySourceKind`` authority; an invalid kind yields
    HTTP 422 via FastAPI's path-parameter validation.
    """
    identity = VaultIdentity(
        kind="compatibility",
        compatibility_source=MemoryCompatibilitySourceRef(
            source_kind=source_kind,
            source_id=source_id,
        ),
    )
    try:
        item = service.get_item(identity=identity)
    except MemoryVaultReadError:
        raise HTTPException(
            status_code=409,
            detail=_PROJECTION_UNAVAILABLE_DETAIL,
        )

    if item is None:
        raise HTTPException(status_code=404, detail=_GENERIC_UNAVAILABLE_DETAIL)
    return _item_response(item)


@router.patch(
    "/items/canonical/{memory_id}/pin",
    response_model=VaultMutationResponse,
)
def patch_canonical_vault_item_pin(
    memory_id: str,
    body: VaultPinRequest = Body(...),
    service: MemoryVaultMutationService = Depends(get_memory_vault_mutation_service),
) -> VaultMutationResponse:
    """Set the desired canonical pin state with an explicit CAS token.

    All mutation semantics (CAS comparison, transaction, provenance
    receipt, canonical readback, no-op calculation) are delegated to the
    C1 mutation service. The route performs no SQL, no CAS comparison,
    no receipt creation, and no read-before-write.
    """
    try:
        result = service.set_pinned(
            memory_id=memory_id,
            expected_updated_at=body.expected_updated_at,
            pinned=body.pinned,
            reason=body.reason,
            request_ref=body.request_ref,
        )
    except MemoryVaultMutationNotAvailable:
        raise HTTPException(
            status_code=404,
            detail=_MUTATION_UNAVAILABLE_DETAIL,
        )
    except MemoryVaultMutationConflict:
        raise HTTPException(status_code=409, detail=_STALE_WRITE_DETAIL)
    except MemoryVaultMutationError:
        raise HTTPException(
            status_code=409,
            detail=_MUTATION_INTEGRITY_DETAIL,
        )

    return VaultMutationResponse(
        changed=result.changed,
        receipt_id=result.receipt_id,
        previous_updated_at=result.previous_updated_at,
        resulting_updated_at=result.resulting_updated_at,
        item=_item_response(result.item),
    )


@router.patch(
    "/items/canonical/{memory_id}/hold",
    response_model=VaultMutationResponse,
)
def patch_canonical_vault_item_hold(
    memory_id: str,
    body: VaultHoldRequest = Body(...),
    service: MemoryVaultMutationService = Depends(get_memory_vault_mutation_service),
) -> VaultMutationResponse:
    """Set the desired canonical hold state with an explicit CAS token.

    Holding suspends decay only; this route delegates all mutation
    semantics (CAS, transaction, receipt, canonical readback, no-op) to the
    C1/C3 mutation service. The route performs no SQL, no CAS comparison,
    no receipt creation, no no-op calculation, and no decay behavior.
    """
    try:
        result = service.set_held(
            memory_id=memory_id,
            expected_updated_at=body.expected_updated_at,
            held=body.held,
            reason=body.reason,
            request_ref=body.request_ref,
        )
    except MemoryVaultMutationNotAvailable:
        raise HTTPException(
            status_code=404,
            detail=_MUTATION_UNAVAILABLE_DETAIL,
        )
    except MemoryVaultMutationConflict:
        raise HTTPException(status_code=409, detail=_STALE_WRITE_DETAIL)
    except MemoryVaultMutationError:
        raise HTTPException(
            status_code=409,
            detail=_MUTATION_INTEGRITY_DETAIL,
        )

    return VaultMutationResponse(
        changed=result.changed,
        receipt_id=result.receipt_id,
        previous_updated_at=result.previous_updated_at,
        resulting_updated_at=result.resulting_updated_at,
        item=_item_response(result.item),
    )


__all__ = [
    "router",
    "get_memory_vault_read_service",
    "get_memory_vault_mutation_service",
    "VaultIdentityResponse",
    "VaultItemResponse",
    "VaultListResponse",
    "VaultPersonaLinkResponse",
    "VaultProvenanceResponse",
    "VaultPinRequest",
    "VaultHoldRequest",
    "VaultMutationResponse",
    "MemoryCompatibilitySourceRefResponse",
]
