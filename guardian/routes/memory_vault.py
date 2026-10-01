"""Authenticated Memory Vault HTTP adapter (UMS-05B2 / UMS-05C2-C6).

This module exposes the already-qualified Memory Vault read,
pin/unpin, hold/release-hold, Project-scope, Persona-attribution, and
direct user-authored creation authorities over FastAPI:

    GET   /api/memory-vault/items
    POST  /api/memory-vault/items
    GET   /api/memory-vault/items/canonical/{memory_id}
    GET   /api/memory-vault/items/compatibility/{source_kind}/{source_id}
    PATCH /api/memory-vault/items/canonical/{memory_id}/pin
    PATCH /api/memory-vault/items/canonical/{memory_id}/hold
    PATCH /api/memory-vault/items/canonical/{memory_id}/project-scope
    PATCH /api/memory-vault/items/canonical/{memory_id}/persona-attribution
    GET   /api/memory-vault/items/canonical/{memory_id}/purge-preview
    POST  /api/memory-vault/items/canonical/{memory_id}/purge

It is an adapter only. It does not:

- query canonical memory tables directly;
- call the compatibility dispatcher directly;
- derive Personal Facts posture;
- resolve Persona authority independently;
- mint route-local memory identities;
- implement CAS, receipts, or no-op logic locally;
- compute purge fingerprints or confirmation tokens;
- enumerate or execute purge deletion fan-out;
- own purge suppression policy;
- register itself in ``guardian.guardian_api``.

The two purge routes (UMS-11) are destructive and are the only ``POST`` that
deletes canonical memory. They are internal-only, exactly like the rest of
this router, and widen no public Beta surface.

Runtime activation in the Guardian application (route registration,
supported-profile posture, feature-flag posture) is owned by UMS-05B3.
This module is qualified against a directly mounted FastAPI test app
only.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Iterator, Literal

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator

from guardian.core.dependencies import (
    RequestUserScope,
    get_request_user_scope,
    require_api_key,
)
from guardian.core.memory_compatibility import (
    MemoryCompatibilitySourceKind,
    MemoryCompatibilitySourceRef,
)
from guardian.protocol_tokens import MemoryPersonaLinkKind, MemorySemanticSpecies
from guardian.services.memory_purge import (
    MemoryPurgeAmbiguousSourceIdentity,
    MemoryPurgeConflict,
    MemoryPurgeError,
    MemoryPurgeInvalid,
    MemoryPurgeNotAvailable,
    MemoryPurgeService,
)
from guardian.services.memory_vault_creation import (
    MemoryVaultCreationError,
    MemoryVaultCreationIntegrityError,
    MemoryVaultCreationService,
)
from guardian.services.memory_vault_mutation import (
    MemoryVaultContentCorrectionIntegrityError,
    MemoryVaultContentCorrectionInvalid,
    MemoryVaultContentCorrectionUnsupported,
    MemoryVaultLifecycleIntegrityError,
    MemoryVaultLifecycleInvalid,
    MemoryVaultLifecycleUnsupported,
    MemoryVaultMutationConflict,
    MemoryVaultMutationError,
    MemoryVaultMutationNotAvailable,
    MemoryVaultMutationService,
    MemoryVaultPersonaSubjectLifecycleConflict,
    MemoryVaultPersonaSubjectNotAvailable,
    MemoryVaultProjectAuthorityConflict,
    MemoryVaultProjectNotAvailable,
    MemoryVaultReviewTransitionIntegrityError,
    MemoryVaultReviewTransitionInvalid,
    MemoryVaultReviewTransitionUnsupported,
)
from guardian.services.memory_vault_read import (
    DEFAULT_LIST_LIMIT,
    LIFECYCLE_POSTURE_ACTIVE,
    LIFECYCLE_POSTURE_DORMANT,
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
    LIFECYCLE_POSTURE_DORMANT,
    LIFECYCLE_POSTURE_INACTIVE,
]

_GENERIC_UNAVAILABLE_DETAIL = "Memory item unavailable"
_PROJECTION_UNAVAILABLE_DETAIL = "Memory projection unavailable"
_STABLE_ACCOUNT_REQUIRED_DETAIL = "Stable account identity required"
_MUTATION_UNAVAILABLE_DETAIL = "Memory not available"
_STALE_WRITE_DETAIL = "Memory changed since it was read"
_MUTATION_INTEGRITY_DETAIL = "Memory mutation unavailable"
# UMS-11. Bounded, sanitized purge reasons. None discloses SQL, a stored
# fingerprint, a plaintext source entity id, a derived-state identifier, or
# another account's tombstone.
_PURGE_UNAVAILABLE_DETAIL = "Memory not available"
_PURGE_STALE_WRITE_DETAIL = "Memory changed since it was read"
_PURGE_CONFIRMATION_STALE_DETAIL = "Memory purge confirmation is stale or invalid"
_PURGE_SOURCE_IDENTITY_AMBIGUOUS_DETAIL = (
    "Memory purge cannot guarantee re-import suppression"
)
_PURGE_INTEGRITY_DETAIL = "Memory purge unavailable"
_PURGE_INVALID_DETAIL = "Memory purge request invalid"
_PROJECT_UNAVAILABLE_DETAIL = "Project not available"
_PROJECT_AUTHORITY_CONFLICT_DETAIL = {
    "code": MemoryVaultProjectAuthorityConflict.code,
    "message": "Project ownership metadata conflicts with canonical authority.",
}
_PERSONA_SUBJECT_UNAVAILABLE_DETAIL = "Persona subject not available"
_PERSONA_SUBJECT_LIFECYCLE_DETAIL = "Persona subject is not active for new attribution"


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
    lifecycle_posture: str = LIFECYCLE_POSTURE_DORMANT
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


class VaultContentCorrectionRequest(_VaultMutationRequest):
    """Request body for direct user-authored content correction.

    Only the explicitly human-authored ``content`` text and the shared
    governance mutation fields are accepted. Caller account, Project,
    Persona, semantic species, review/lifecycle state, revision identity,
    and revision numbering are never request authority.
    """

    content: Annotated[str, Field(strict=True, min_length=1)]


class VaultPinRequest(_VaultMutationRequest):
    """Request body for canonical pin/unpin mutation."""

    pinned: bool


class VaultHoldRequest(_VaultMutationRequest):
    """Request body for canonical hold/release-hold mutation."""

    held: bool


class VaultProjectScopeRequest(_VaultMutationRequest):
    """Request body for explicit canonical Project-scope mutation."""

    project_id: Annotated[int, Field(strict=True, gt=0)] | None


class VaultPersonaAttributionRequest(_VaultMutationRequest):
    """Request body for explicit canonical Persona-attribution mutation.

    Targets one exact ``(memory_id, persona_subject_id, link_kind)`` triple.
    PersonaProfile identity, display names, prompts, and review posture are
    never accepted as mutation authority.
    """

    persona_subject_id: Annotated[str, Field(strict=True, min_length=1)]
    link_kind: MemoryPersonaLinkKind
    present: bool


class VaultCreateMemoryRequest(BaseModel):
    """Request body for direct user-authored Vault creation (UMS-05C6).

    Only the explicitly human-authored ``content`` text and an optional
    opaque ``request_ref`` are accepted. Project, Persona, semantic
    species, pin/hold, review/activation, ambient eligibility, and
    memory ID are never caller-chosen here; the creation service
    owns those dimensions.
    """

    content: Annotated[str, Field(strict=True, min_length=1)]
    request_ref: str | None = Field(default=None, max_length=128)


class VaultMutationResponse(BaseModel):
    """Serialized Vault governance mutation result."""

    changed: bool
    receipt_id: str | None
    previous_updated_at: datetime
    resulting_updated_at: datetime
    item: VaultItemResponse


class VaultCreationResponse(BaseModel):
    """Serialized Vault direct creation result (UMS-05C6)."""

    receipt_id: str
    item: VaultItemResponse


class VaultContentCorrectionResponse(BaseModel):
    """Serialized direct content-correction result (UMS-05C9-W).

    ``revision_id`` / ``revision_number`` and ``receipt_id`` are all
    ``None`` for an exact no-op. Full old authored text is never exposed
    separately from the canonical current item.
    """

    changed: bool
    receipt_id: str | None
    revision_id: str | None
    revision_number: int | None
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


def get_memory_vault_creation_service(
    scope: RequestUserScope = Depends(get_request_user_scope),
) -> Iterator[MemoryVaultCreationService]:
    """Bind a ``MemoryVaultCreationService`` to the authenticated account.

    Reuses the same repository database/session authority as the read and
    mutation services; the C6 creation service owns user-authored record
    authoring, separate from governance mutation.
    """
    account_id = _resolve_vault_account(scope)
    db = _get_vault_db()
    session = db.get_session()
    try:
        yield MemoryVaultCreationService(
            session,
            authenticated_account_id=account_id,
        )
    finally:
        session.close()


def get_memory_purge_service(
    scope: RequestUserScope = Depends(get_request_user_scope),
) -> Iterator[MemoryPurgeService]:
    """Bind a ``MemoryPurgeService`` to the authenticated account.

    Reuses the same repository database/session authority as the read,
    mutation, and creation services. The purge service owns the destructive
    transaction; this adapter never commits, rolls back, or queries.
    """
    account_id = _resolve_vault_account(scope)
    db = _get_vault_db()
    session = db.get_session()
    try:
        yield MemoryPurgeService(
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


@router.patch(
    "/items/canonical/{memory_id}/project-scope",
    response_model=VaultMutationResponse,
)
def patch_canonical_vault_item_project_scope(
    memory_id: str,
    body: VaultProjectScopeRequest = Body(...),
    service: MemoryVaultMutationService = Depends(get_memory_vault_mutation_service),
) -> VaultMutationResponse:
    """Set or explicitly clear canonical Project scope through the C4 service."""
    try:
        result = service.set_project_scope(
            memory_id=memory_id,
            expected_updated_at=body.expected_updated_at,
            project_id=body.project_id,
            reason=body.reason,
            request_ref=body.request_ref,
        )
    except MemoryVaultMutationNotAvailable:
        raise HTTPException(status_code=404, detail=_MUTATION_UNAVAILABLE_DETAIL)
    except MemoryVaultProjectNotAvailable:
        raise HTTPException(status_code=404, detail=_PROJECT_UNAVAILABLE_DETAIL)
    except MemoryVaultProjectAuthorityConflict:
        raise HTTPException(
            status_code=409,
            detail=_PROJECT_AUTHORITY_CONFLICT_DETAIL,
        )
    except MemoryVaultMutationConflict:
        raise HTTPException(status_code=409, detail=_STALE_WRITE_DETAIL)
    except MemoryVaultMutationError:
        raise HTTPException(status_code=409, detail=_MUTATION_INTEGRITY_DETAIL)

    return VaultMutationResponse(
        changed=result.changed,
        receipt_id=result.receipt_id,
        previous_updated_at=result.previous_updated_at,
        resulting_updated_at=result.resulting_updated_at,
        item=_item_response(result.item),
    )


@router.patch(
    "/items/canonical/{memory_id}/persona-attribution",
    response_model=VaultMutationResponse,
)
def patch_canonical_vault_item_persona_attribution(
    memory_id: str,
    body: VaultPersonaAttributionRequest = Body(...),
    service: MemoryVaultMutationService = Depends(get_memory_vault_mutation_service),
) -> VaultMutationResponse:
    """Add or remove one exact typed stable-Persona attribution link."""
    try:
        result = service.set_persona_attribution(
            memory_id=memory_id,
            expected_updated_at=body.expected_updated_at,
            persona_subject_id=body.persona_subject_id,
            link_kind=body.link_kind,
            present=body.present,
            reason=body.reason,
            request_ref=body.request_ref,
        )
    except MemoryVaultMutationNotAvailable:
        raise HTTPException(status_code=404, detail=_MUTATION_UNAVAILABLE_DETAIL)
    except MemoryVaultPersonaSubjectNotAvailable:
        raise HTTPException(status_code=404, detail=_PERSONA_SUBJECT_UNAVAILABLE_DETAIL)
    except MemoryVaultPersonaSubjectLifecycleConflict:
        raise HTTPException(status_code=409, detail=_PERSONA_SUBJECT_LIFECYCLE_DETAIL)
    except MemoryVaultMutationConflict:
        raise HTTPException(status_code=409, detail=_STALE_WRITE_DETAIL)
    except MemoryVaultMutationError:
        raise HTTPException(status_code=409, detail=_MUTATION_INTEGRITY_DETAIL)

    return VaultMutationResponse(
        changed=result.changed,
        receipt_id=result.receipt_id,
        previous_updated_at=result.previous_updated_at,
        resulting_updated_at=result.resulting_updated_at,
        item=_item_response(result.item),
    )


_CREATION_UNAVAILABLE_DETAIL = "Memory creation unavailable"


@router.post(
    "/items",
    response_model=VaultCreationResponse,
    status_code=201,
)
def create_vault_item(
    body: VaultCreateMemoryRequest = Body(...),
    service: MemoryVaultCreationService = Depends(get_memory_vault_creation_service),
) -> VaultCreationResponse:
    """Direct authenticated user-authored Vault memory creation.

    Accepts only ``content`` (and optional ``request_ref``). All other
    canonical dimensions — account owner, semantic species, project
    scope, Persona links, pin/hold, review/activation, and memory ID —
    are owned by the C6 creation service. Returns 201 with the
    canonical ``VaultItem`` readback.
    """
    try:
        result = service.create_memory(
            content=body.content,
            request_ref=body.request_ref,
        )
    except MemoryVaultCreationIntegrityError:
        raise HTTPException(status_code=409, detail=_CREATION_UNAVAILABLE_DETAIL)
    except MemoryVaultCreationError:
        raise HTTPException(status_code=422, detail=_CREATION_UNAVAILABLE_DETAIL)

    return VaultCreationResponse(
        receipt_id=result.receipt_id,
        item=_item_response(result.item),
    )


_CONTENT_CORRECTION_UNAVAILABLE_DETAIL = "Memory content correction unavailable"
_CONTENT_CORRECTION_INVALID_DETAIL = "Content must be a non-empty string"
_REVIEW_TRANSITION_UNAVAILABLE_DETAIL = "Memory review transition unavailable"
_REVIEW_TRANSITION_INVALID_DETAIL = "Action must be one of: approve, reject, dispute"
_LIFECYCLE_UNAVAILABLE_DETAIL = "Memory lifecycle transition unavailable"
_LIFECYCLE_INVALID_DETAIL = "Action must be one of: retire, restore"


class VaultReviewTransitionRequest(_VaultMutationRequest):
    """ADR-088 direct review action.

    Only the admitted action is accepted. A raw ``review_state`` is never
    taken from the caller, so ``pending`` cannot be requested.

    ``extra="forbid"`` is deliberate: caller-supplied authority fields
    (account, actor, revision identity/number, lifecycle, Project, Persona)
    are rejected outright rather than silently ignored.
    """

    model_config = ConfigDict(extra="forbid")

    action: str


class VaultLifecycleTransitionRequest(_VaultMutationRequest):
    """ADR-089 direct lifecycle action.

    Only the admitted action is accepted. A raw lifecycle target is never
    taken from the caller, so ``active`` / ``dormant`` / ``retired`` cannot
    be requested directly.
    """

    model_config = ConfigDict(extra="forbid")

    action: str


class VaultLifecycleTransitionResponse(BaseModel):
    """Serialized direct lifecycle transition result (UMS-05C10B-W).

    All three identity fields are ``None`` for an ADR-089 same-state no-op.
    No internal history-validation diagnostic is exposed.
    """

    changed: bool
    action: str
    receipt_id: str | None
    lifecycle_revision_id: str | None
    lifecycle_revision_number: int | None
    previous_lifecycle_state: str
    resulting_lifecycle_state: str
    previous_updated_at: datetime
    resulting_updated_at: datetime
    item: VaultItemResponse


class VaultPurgeRequest(_VaultMutationRequest):
    """Exact-target permanent-erasure request.

    Accepts only what an authenticated account principal can legitimately
    assert about its own destructive intent. It deliberately does **not**
    accept a user/account id, a raw tombstone field, a caller-supplied source
    fingerprint, a caller-supplied purge receipt id, a lifecycle target, a
    review target, or any cascade control. Those would all let a caller
    either forge suppression authority or widen the destructive blast radius.
    """

    confirmation_token: str = Field(
        min_length=1,
        description=(
            "Opaque token returned by the purge-preview route, bound to the "
            "exact current destructive target."
        ),
    )


class VaultPurgePreviewResponse(BaseModel):
    """Serialized exact-target destructive preview.

    Counts and identity only. Never memory content, never another account's
    state, never raw queue payloads, never vector bodies, never secrets.
    """

    memory_id: str
    record_fingerprint: str
    updated_at: datetime
    content_revision_count: int
    review_revision_count: int
    lifecycle_revision_count: int
    provenance_count: int
    persona_link_count: int
    derived_state_count: int
    total_affected_rows: int
    suppression_fingerprint_available: bool
    suppression_ambiguity: str | None
    confirmation_token: str


class VaultPurgeResponse(BaseModel):
    """Serialized permanent-erasure result.

    An idempotent retry reports ``changed=False`` / ``already_purged=True``
    with the original ``purge_receipt_id`` and ``purged_at``; it creates no
    second tombstone and no second receipt identity.
    """

    memory_id: str
    changed: bool
    already_purged: bool
    purge_receipt_id: str
    purged_at: datetime
    record_fingerprint: str
    source_atom_fingerprint: str | None
    suppression: bool
    deleted_content_revisions: int
    deleted_review_revisions: int
    deleted_lifecycle_revisions: int
    deleted_provenance: int
    deleted_persona_links: int


class VaultReviewTransitionResponse(BaseModel):
    """Serialized direct review-transition result (UMS-05C10A-W).

    ``receipt_id`` / ``review_revision_id`` / ``review_revision_number`` are
    all ``None`` for an ADR-088 same-state no-op. No separate copy of memory
    content is exposed for review-history purposes.
    """

    changed: bool
    action: str
    receipt_id: str | None
    review_revision_id: str | None
    review_revision_number: int | None
    previous_review_state: str
    resulting_review_state: str
    previous_updated_at: datetime
    resulting_updated_at: datetime
    item: VaultItemResponse


@router.patch(
    "/items/canonical/{memory_id}/content",
    response_model=VaultContentCorrectionResponse,
)
def patch_canonical_vault_item_content(
    memory_id: str,
    body: VaultContentCorrectionRequest = Body(...),
    service: MemoryVaultMutationService = Depends(get_memory_vault_mutation_service),
) -> VaultContentCorrectionResponse:
    """Direct authenticated correction of ordinary-memory content.

    Thin adapter only: it performs no SQL, no revision-number
    calculation, no CAS comparison, no row locking, no old/new text
    comparison, and no receipt construction. Account authority comes
    exclusively from ``RequestUserScope.account_id`` through the
    existing mutation-service dependency.
    """
    try:
        result = service.correct_content(
            memory_id=memory_id,
            expected_updated_at=body.expected_updated_at,
            content=body.content,
            reason=body.reason,
            request_ref=body.request_ref,
        )
    except MemoryVaultMutationNotAvailable:
        # Missing and cross-account share one indistinguishable posture.
        raise HTTPException(status_code=404, detail=_MUTATION_UNAVAILABLE_DETAIL)
    except MemoryVaultContentCorrectionInvalid:
        # Ordinary request validation, not an integrity failure.
        raise HTTPException(status_code=422, detail=_CONTENT_CORRECTION_INVALID_DETAIL)
    except MemoryVaultMutationConflict:
        raise HTTPException(status_code=409, detail=_STALE_WRITE_DETAIL)
    except (
        MemoryVaultContentCorrectionUnsupported,
        MemoryVaultContentCorrectionIntegrityError,
        MemoryVaultMutationError,
    ):
        # Sanitized: no species, SQL, constraint, chain, or content detail.
        raise HTTPException(
            status_code=409, detail=_CONTENT_CORRECTION_UNAVAILABLE_DETAIL
        )

    return VaultContentCorrectionResponse(
        changed=result.changed,
        receipt_id=result.receipt_id,
        revision_id=result.revision_id,
        revision_number=result.revision_number,
        previous_updated_at=result.previous_updated_at,
        resulting_updated_at=result.resulting_updated_at,
        item=_item_response(result.item),
    )


@router.patch(
    "/items/canonical/{memory_id}/review",
    response_model=VaultReviewTransitionResponse,
)
def patch_canonical_vault_item_review(
    memory_id: str,
    body: VaultReviewTransitionRequest = Body(...),
    service: MemoryVaultMutationService = Depends(get_memory_vault_mutation_service),
) -> VaultReviewTransitionResponse:
    """Direct authenticated review transition for ordinary memory.

    Thin adapter only: it performs no SQL, no parent lookup, no row
    locking, no CAS comparison, no no-op determination, no state-machine
    calculation, no review-revision numbering, no ``reviewed_at`` decision,
    no receipt construction, and no read-before-write. Account authority
    comes exclusively from ``RequestUserScope.account_id`` through the
    existing mutation-service dependency.
    """
    try:
        result = service.transition_review(
            memory_id=memory_id,
            expected_updated_at=body.expected_updated_at,
            action=body.action,
            reason=body.reason,
            request_ref=body.request_ref,
        )
    except MemoryVaultMutationNotAvailable:
        # Missing and cross-account share one indistinguishable posture.
        raise HTTPException(status_code=404, detail=_MUTATION_UNAVAILABLE_DETAIL)
    except MemoryVaultReviewTransitionInvalid:
        raise HTTPException(status_code=422, detail=_REVIEW_TRANSITION_INVALID_DETAIL)
    except MemoryVaultMutationConflict:
        raise HTTPException(status_code=409, detail=_STALE_WRITE_DETAIL)
    except (
        MemoryVaultReviewTransitionUnsupported,
        MemoryVaultReviewTransitionIntegrityError,
        MemoryVaultMutationError,
    ):
        # Sanitized: no species, SQL, constraint, chain, or content detail.
        raise HTTPException(
            status_code=409, detail=_REVIEW_TRANSITION_UNAVAILABLE_DETAIL
        )

    return VaultReviewTransitionResponse(
        changed=result.changed,
        action=result.action,
        receipt_id=result.receipt_id,
        review_revision_id=result.review_revision_id,
        review_revision_number=result.review_revision_number,
        previous_review_state=result.previous_review_state,
        resulting_review_state=result.resulting_review_state,
        previous_updated_at=result.previous_updated_at,
        resulting_updated_at=result.resulting_updated_at,
        item=_item_response(result.item),
    )


@router.patch(
    "/items/canonical/{memory_id}/lifecycle",
    response_model=VaultLifecycleTransitionResponse,
)
def patch_canonical_vault_item_lifecycle(
    memory_id: str,
    body: VaultLifecycleTransitionRequest = Body(...),
    service: MemoryVaultMutationService = Depends(get_memory_vault_mutation_service),
) -> VaultLifecycleTransitionResponse:
    """Direct authenticated retire / restore for ordinary memory.

    Thin adapter only: it performs no SQL, no parent lookup, no row locking,
    no CAS comparison, no no-op determination, no lifecycle state-machine
    logic, no lifecycle-history read, no restore-target resolution, no
    revision numbering, no receipt construction, and no read-before-write.
    Account authority comes exclusively from ``RequestUserScope.account_id``
    through the existing mutation-service dependency.
    """
    try:
        result = service.transition_lifecycle(
            memory_id=memory_id,
            expected_updated_at=body.expected_updated_at,
            action=body.action,
            reason=body.reason,
            request_ref=body.request_ref,
        )
    except MemoryVaultMutationNotAvailable:
        # Missing and cross-account share one indistinguishable posture.
        raise HTTPException(status_code=404, detail=_MUTATION_UNAVAILABLE_DETAIL)
    except MemoryVaultLifecycleInvalid:
        raise HTTPException(status_code=422, detail=_LIFECYCLE_INVALID_DETAIL)
    except MemoryVaultMutationConflict:
        raise HTTPException(status_code=409, detail=_STALE_WRITE_DETAIL)
    except (
        MemoryVaultLifecycleUnsupported,
        MemoryVaultLifecycleIntegrityError,
        MemoryVaultMutationError,
    ):
        # Includes restore where the pre-retirement posture cannot be proven.
        # Sanitized: no SQL, constraint, chain, or account detail.
        raise HTTPException(status_code=409, detail=_LIFECYCLE_UNAVAILABLE_DETAIL)

    return VaultLifecycleTransitionResponse(
        changed=result.changed,
        action=result.action,
        receipt_id=result.receipt_id,
        lifecycle_revision_id=result.lifecycle_revision_id,
        lifecycle_revision_number=result.lifecycle_revision_number,
        previous_lifecycle_state=result.previous_lifecycle_state,
        resulting_lifecycle_state=result.resulting_lifecycle_state,
        previous_updated_at=result.previous_updated_at,
        resulting_updated_at=result.resulting_updated_at,
        item=_item_response(result.item),
    )


@router.get(
    "/items/canonical/{memory_id}/purge-preview",
    response_model=VaultPurgePreviewResponse,
)
def get_canonical_vault_item_purge_preview(
    memory_id: str,
    service: MemoryPurgeService = Depends(get_memory_purge_service),
) -> VaultPurgePreviewResponse:
    """Describe exactly what permanent purge of this item would destroy.

    Read-only and account-scoped. Thin adapter only: it performs no SQL, no
    fingerprint computation, no child enumeration, no CAS comparison, and no
    confirmation-token construction. Account authority comes exclusively from
    ``RequestUserScope.account_id``.

    A missing and a cross-account target share one indistinguishable 404
    posture, so preview never discloses another account's existence.
    """
    try:
        preview = service.preview_purge(memory_id=memory_id)
    except MemoryPurgeNotAvailable:
        raise HTTPException(status_code=404, detail=_PURGE_UNAVAILABLE_DETAIL)
    except MemoryPurgeInvalid:
        raise HTTPException(status_code=422, detail=_PURGE_INVALID_DETAIL)
    except MemoryPurgeError:
        raise HTTPException(status_code=409, detail=_PURGE_INTEGRITY_DETAIL)

    return VaultPurgePreviewResponse(
        memory_id=preview.memory_id,
        record_fingerprint=preview.record_fingerprint,
        updated_at=preview.updated_at,
        content_revision_count=preview.content_revision_count,
        review_revision_count=preview.review_revision_count,
        lifecycle_revision_count=preview.lifecycle_revision_count,
        provenance_count=preview.provenance_count,
        persona_link_count=preview.persona_link_count,
        derived_state_count=preview.derived_state_count,
        total_affected_rows=preview.total_affected_rows,
        suppression_fingerprint_available=(preview.suppression_fingerprint_available),
        suppression_ambiguity=preview.suppression_ambiguity,
        confirmation_token=preview.confirmation_token,
    )


@router.post(
    "/items/canonical/{memory_id}/purge",
    response_model=VaultPurgeResponse,
)
def post_canonical_vault_item_purge(
    memory_id: str,
    body: VaultPurgeRequest = Body(...),
    service: MemoryPurgeService = Depends(get_memory_purge_service),
) -> VaultPurgeResponse:
    """Permanently erase one canonical ordinary memory.

    Thin adapter only: it performs no SQL, no row locking, no CAS
    comparison, no confirmation-token recomputation, no fingerprint
    derivation, no deletion fan-out, no tombstone construction, and no
    suppression policy. All purge authority belongs to the purge service.

    Requires a fresh CAS token *and* a confirmation token minted against the
    current destructive target. Both are validated before any deletion.

    HTTP posture:

    * 401 -- missing or blank authenticated account;
    * 404 -- missing or cross-account target, except that a same-account
      retry of an already-completed purge succeeds with
      ``already_purged=True``;
    * 409 -- stale CAS, stale or wrong confirmation, ambiguous import-origin
      source identity, or fan-out integrity failure;
    * 422 -- malformed request body.
    """
    try:
        result = service.purge(
            memory_id=memory_id,
            expected_updated_at=body.expected_updated_at,
            confirmation_token=body.confirmation_token,
            reason=body.reason,
            request_ref=body.request_ref,
        )
    except MemoryPurgeNotAvailable:
        raise HTTPException(status_code=404, detail=_PURGE_UNAVAILABLE_DETAIL)
    except MemoryPurgeAmbiguousSourceIdentity:
        # Fail closed rather than erase a record whose source atom could not
        # be suppressed afterwards. Distinct from a generic conflict so the
        # caller learns the destructive claim is not satisfiable.
        raise HTTPException(
            status_code=409, detail=_PURGE_SOURCE_IDENTITY_AMBIGUOUS_DETAIL
        )
    except MemoryPurgeConflict as exc:
        detail = (
            _PURGE_CONFIRMATION_STALE_DETAIL
            if "confirmation" in str(exc).lower()
            else _PURGE_STALE_WRITE_DETAIL
        )
        raise HTTPException(status_code=409, detail=detail)
    except MemoryPurgeInvalid:
        raise HTTPException(status_code=422, detail=_PURGE_INVALID_DETAIL)
    except MemoryPurgeError:
        # Sanitized: no SQL, constraint, fingerprint, or content detail.
        raise HTTPException(status_code=409, detail=_PURGE_INTEGRITY_DETAIL)

    return VaultPurgeResponse(
        memory_id=result.memory_id,
        changed=result.changed,
        already_purged=result.already_purged,
        purge_receipt_id=result.purge_receipt_id,
        purged_at=result.purged_at,
        record_fingerprint=result.record_fingerprint,
        source_atom_fingerprint=result.source_atom_fingerprint,
        suppression=result.suppression,
        deleted_content_revisions=result.deleted_content_revisions,
        deleted_review_revisions=result.deleted_review_revisions,
        deleted_lifecycle_revisions=result.deleted_lifecycle_revisions,
        deleted_provenance=result.deleted_provenance,
        deleted_persona_links=result.deleted_persona_links,
    )


__all__ = [
    "router",
    "get_memory_vault_read_service",
    "get_memory_vault_mutation_service",
    "get_memory_vault_creation_service",
    "get_memory_purge_service",
    "VaultIdentityResponse",
    "VaultItemResponse",
    "VaultListResponse",
    "VaultPersonaLinkResponse",
    "VaultProvenanceResponse",
    "VaultPinRequest",
    "VaultHoldRequest",
    "VaultProjectScopeRequest",
    "VaultPersonaAttributionRequest",
    "VaultCreateMemoryRequest",
    "VaultContentCorrectionRequest",
    "VaultContentCorrectionResponse",
    "VaultLifecycleTransitionRequest",
    "VaultLifecycleTransitionResponse",
    "VaultReviewTransitionRequest",
    "VaultReviewTransitionResponse",
    "VaultPurgeRequest",
    "VaultPurgePreviewResponse",
    "VaultPurgeResponse",
    "VaultMutationResponse",
    "VaultCreationResponse",
    "MemoryCompatibilitySourceRefResponse",
]
