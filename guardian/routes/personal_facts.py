"""Personal facts routes."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

try:
    from guardian.core.dependencies import (
        chatlog_db,
        get_request_user_id,
        init_database,
        require_api_key,
    )
except Exception:  # pragma: no cover - fallback for import issues
    chatlog_db = None  # type: ignore[assignment]

    def init_database():  # type: ignore[unused-argument]
        return None

    def require_api_key(api_key: str = "") -> str:  # type: ignore[unused-argument]
        return api_key

    def get_request_user_id() -> str:  # type: ignore[unused-argument]
        return "local"


# ── Sensitive key gating ──
# Keys matching these patterns require an explicit force flag to approve.
_SENSITIVE_KEY_PREFIXES = frozenset(
    {
        "ssn",
        "password",
        "credit_card",
        "bank",
        "pin",
        "secret",
        "token",
    }
)


def _is_sensitive_key(key: str) -> bool:
    normalized = str(key or "").strip().lower()
    return any(
        normalized.startswith(prefix) or prefix in normalized
        for prefix in _SENSITIVE_KEY_PREFIXES
    )


def _sensitive_key_error(key: str) -> HTTPException:
    return HTTPException(
        status_code=422,
        detail={
            "error": "sensitive_key_blocked",
            "key": key,
            "message": (
                f"Fact key '{key}' matches a sensitive pattern. "
                "Set force_sensitive=true and provide a reason to approve."
            ),
        },
    )


# ── Guardrail approval gating ──
# These reason labels must block direct approval per
# docs/architecture/personal-facts-guardrails-contract.md.
_BLOCKING_REASONS: frozenset[str] = frozenset(
    {
        "source_role_assistant",
        "source_role_system_like",
        "source_role_ambiguous",
        "quoted_or_hypothetical",
        "missing_evidence",
    }
)


def _is_guardrail_approval_blocked(
    fact: dict[str, Any],
) -> tuple[bool, str | None]:
    """Check whether a candidate fact is blocked from direct approval.

    Returns (blocked: bool, reason: str | None).
    Treats missing or malformed guardrail_metadata conservatively —
    if metadata cannot be trusted, approval is blocked.
    """
    meta = fact.get("guardrail_metadata")
    if meta is None:
        return False, None

    if not isinstance(meta, dict):
        # Malformed metadata — fail closed.
        return True, "guardrail_metadata_malformed"

    # Direct promotion_blocked flag
    if meta.get("promotion_blocked") is True:
        return True, "promotion_blocked"

    # Check for blocking source/authorship reasons
    reasons: list[str] = []
    raw_reasons = meta.get("reasons")
    if isinstance(raw_reasons, list):
        reasons = [str(r) for r in raw_reasons]

    for reason in reasons:
        if reason in _BLOCKING_REASONS:
            return True, reason

    return False, None


def _guardrail_blocked_error(
    fact_id: int, block_reason: str
) -> HTTPException:
    return HTTPException(
        status_code=422,
        detail={
            "error": "personal_fact_promotion_blocked",
            "fact_id": fact_id,
            "block_reason": block_reason,
            "message": (
                "This candidate is blocked from direct approval. "
                "It must be reviewed, edited, or explicitly overridden "
                f"before promotion. Block reason: {block_reason}."
            ),
        },
    )


def _is_guardrail_override_allowed(
    fact: dict[str, Any],
    edited_key: str | None,
    edited_value: str | None,
    original_key: str,
    original_value: str,
    override_guardrail: bool,
    override_note: str | None,
) -> tuple[bool, str | None]:
    """Check whether a guardrail-blocked candidate may be overridden.

    Returns (allowed: bool, failure_reason: str | None).
    """
    is_blocked, _ = _is_guardrail_approval_blocked(fact)
    if not is_blocked:
        # Not blocked — normal approval applies.
        return True, None

    if not override_guardrail:
        return False, "override_guardrail_not_set"

    # Must have explicit override intent with edit or confirmation.
    key_changed = bool(edited_key and edited_key != original_key)
    value_changed = bool(edited_value and edited_value != original_value)
    note_provided = bool(override_note and override_note.strip())

    if not (key_changed or value_changed or note_provided):
        return False, "override_requires_edit_or_note"

    # Malformed metadata cannot be overridden.
    meta = fact.get("guardrail_metadata")
    if meta is not None and not isinstance(meta, dict):
        return False, "guardrail_metadata_malformed"

    return True, None


def _guardrail_override_blocked_error(
    fact_id: int, detail_code: str, detail_message: str
) -> HTTPException:
    return HTTPException(
        status_code=422,
        detail={
            "error": detail_code,
            "fact_id": fact_id,
            "message": detail_message,
        },
    )


def _get_chatlog_db():
    global chatlog_db
    if chatlog_db is None:
        db = init_database()
        if db is None:
            raise RuntimeError("chatlog_db is not initialized")
        chatlog_db = db
    return chatlog_db


def get_current_user(
    current_user: str = Depends(get_request_user_id),
) -> str:
    return current_user


router = APIRouter(prefix="/personal-facts", tags=["Personal Facts"])


class FactCreate(BaseModel):
    key: str
    value: str
    status: str = "candidate"
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class FactUpdate(BaseModel):
    value: str | None = None
    status: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    reason: str | None = None


class FactAction(BaseModel):
    reason: str | None = None


class CandidateApproveRequest(BaseModel):
    """Request body for promoting a fact candidate to verified."""

    value: str | None = Field(
        default=None,
        description="Optional edited fact text. If provided, replaces the original candidate value before promotion.",
    )
    key: str | None = Field(
        default=None,
        description="Optional normalized key override.",
    )
    confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Optional confidence override for the promoted fact.",
    )
    reason: str | None = Field(
        default=None,
        description="Optional approval reason (recorded in revision).",
    )
    force_sensitive: bool = Field(
        default=False,
        description="Set to true to approve a fact whose key matches a sensitive pattern. Requires reason.",
    )
    override_guardrail: bool = Field(
        default=False,
        description="Set to true to explicitly override guardrail blocking after correcting the fact. Requires edited key/value and override_note.",
    )
    override_note: str | None = Field(
        default=None,
        description="Required when override_guardrail=true. Describes why the guardrail block is being overridden.",
    )


class CandidateRejectRequest(BaseModel):
    """Request body for rejecting a fact candidate."""

    reason: str | None = Field(
        default=None,
        description="Rejection reason: incorrect, duplicate, not_useful, sensitive, or other.",
    )


class EvidenceCreate(BaseModel):
    source_message_id: int | None = None
    excerpt: str | None = None
    modality: str = "text"
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    source_type: str = "runtime_extraction"
    evidence_meta: dict | None = None


@router.get("", dependencies=[Depends(require_api_key)])
def list_personal_facts(
    status: str | None = None,
    active_only: bool = True,
    limit: int = 100,
    current_user: str = Depends(get_current_user),
) -> dict[str, Any]:
    db = _get_chatlog_db()
    items = db.list_facts(
        current_user,
        status=status,
        active_only=active_only,
        limit=limit,
    )
    return {"ok": True, "facts": items}


@router.post("", dependencies=[Depends(require_api_key)])
def create_personal_fact(
    body: FactCreate = Body(...),
    current_user: str = Depends(get_current_user),
) -> dict[str, Any]:
    key = body.key.strip()
    value = body.value.strip()
    if not key or not value:
        raise HTTPException(status_code=400, detail="key and value required")
    db = _get_chatlog_db()
    fact_id = db.create_fact(
        current_user,
        key,
        value,
        status=body.status,
        confidence=body.confidence,
    )
    return {"ok": True, "id": fact_id}


@router.get("/{fact_id}", dependencies=[Depends(require_api_key)])
def get_personal_fact(
    fact_id: int,
    current_user: str = Depends(get_current_user),
) -> dict[str, Any]:
    db = _get_chatlog_db()
    fact = db.get_fact(fact_id)
    if not fact or fact.get("user_id") != current_user:
        raise HTTPException(status_code=404, detail="fact not found")
    evidence = db.list_fact_evidence(fact_id)
    return {"ok": True, "fact": fact, "evidence": evidence}


@router.patch("/{fact_id}", dependencies=[Depends(require_api_key)])
def update_personal_fact(
    fact_id: int,
    body: FactUpdate = Body(...),
    current_user: str = Depends(get_current_user),
) -> dict[str, Any]:
    db = _get_chatlog_db()
    fact = db.get_fact(fact_id)
    if not fact or fact.get("user_id") != current_user:
        raise HTTPException(status_code=404, detail="fact not found")
    updated = db.update_fact(
        fact_id,
        value=body.value,
        status=body.status,
        confidence=body.confidence,
        actor="user",
        reason=body.reason,
    )
    return {"ok": True, "fact": updated}


@router.post("/{fact_id}/confirm", dependencies=[Depends(require_api_key)])
def confirm_personal_fact(
    fact_id: int,
    body: FactAction = Body(default=FactAction()),
    current_user: str = Depends(get_current_user),
) -> dict[str, Any]:
    db = _get_chatlog_db()
    fact = db.get_fact(fact_id)
    if not fact or fact.get("user_id") != current_user:
        raise HTTPException(status_code=404, detail="fact not found")
    # Sensitivity gate: block silent promotion of sensitive keys
    key = str(fact.get("key") or "").strip().lower()
    if _is_sensitive_key(key):
        raise _sensitive_key_error(key)
    updated = db.update_fact(
        fact_id,
        status="verified",
        actor="user",
        reason=body.reason,
    )
    logger.info(
        "Personal fact confirmed fact_id=%s key=%s user=%s",
        fact_id,
        key,
        current_user,
    )
    return {"ok": True, "fact": updated}


@router.post("/{fact_id}/dispute", dependencies=[Depends(require_api_key)])
def dispute_personal_fact(
    fact_id: int,
    body: FactAction = Body(default=FactAction()),
    current_user: str = Depends(get_current_user),
) -> dict[str, Any]:
    db = _get_chatlog_db()
    fact = db.get_fact(fact_id)
    if not fact or fact.get("user_id") != current_user:
        raise HTTPException(status_code=404, detail="fact not found")
    updated = db.update_fact(
        fact_id,
        status="disputed",
        actor="user",
        reason=body.reason,
    )
    logger.info(
        "Personal fact disputed fact_id=%s key=%s user=%s",
        fact_id,
        str(fact.get("key") or ""),
        current_user,
    )
    return {"ok": True, "fact": updated}


# ── Candidate review & promotion (production endpoints) ──


@router.post(
    "/candidates/{fact_id}/approve",
    dependencies=[Depends(require_api_key)],
)
def approve_candidate(
    fact_id: int,
    body: CandidateApproveRequest = Body(default=CandidateApproveRequest()),
    current_user: str = Depends(get_current_user),
) -> dict[str, Any]:
    """Approve a fact candidate and promote it to verified status.

    Supports edit-before-approve: if body.value is provided, the fact text
    is updated before promotion. The original value is preserved in the
    revision audit trail.

    Sensitivity gating: candidates whose key matches a sensitive pattern
    (password, ssn, token, etc.) are blocked unless force_sensitive=True
    and a reason is provided.
    """
    db = _get_chatlog_db()
    fact = db.get_fact(fact_id)
    if not fact or fact.get("user_id") != current_user:
        raise HTTPException(status_code=404, detail="fact not found")

    # Verify this is a candidate (or equivalent pending state)
    current_status = str(fact.get("status") or "").strip().lower()
    if current_status not in ("candidate", "disputed"):
        raise HTTPException(
            status_code=409,
            detail={
                "error": "not_candidate",
                "current_status": current_status,
                "message": f"Fact is already {current_status}. Only candidate or disputed facts can be approved.",
            },
        )

    key = str(fact.get("key") or "").strip()
    effective_key = (body.key or key).strip()

    # Sensitivity gate
    if _is_sensitive_key(effective_key):
        if not body.force_sensitive:
            raise _sensitive_key_error(effective_key)
        if not (body.reason and body.reason.strip()):
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "sensitive_reason_required",
                    "message": "A reason is required when force_sensitive=true.",
                },
            )
        logger.warning(
            "Sensitive candidate approved with force flag fact_id=%s key=%s user=%s reason=%s",
            fact_id,
            effective_key,
            current_user,
            body.reason,
        )

    # Guardrail gate: block direct approval of promotion-blocked candidates
    # unless an explicit override is provided.
    key = str(fact.get("key") or "").strip()
    effective_key = (body.key or key).strip()
    edited_value = (body.value or "").strip()
    original_value = str(fact.get("value") or "")

    override_allowed, override_reason = _is_guardrail_override_allowed(
        fact=fact,
        edited_key=body.key,
        edited_value=body.value,
        original_key=key,
        original_value=original_value,
        override_guardrail=body.override_guardrail,
        override_note=body.override_note,
    )

    if not override_allowed:
        if override_reason == "override_guardrail_not_set":
            # Not attempting override — use the standard blocked error.
            is_blocked, block_reason = _is_guardrail_approval_blocked(fact)
            if is_blocked:
                raise HTTPException(
                    status_code=422,
                    detail={
                        "error": "personal_fact_override_required",
                        "fact_id": fact_id,
                        "block_reason": block_reason or "unknown",
                        "message": (
                            "This candidate is guardrail-blocked and cannot be directly approved. "
                            "Set override_guardrail=true with an edited value and override_note to override."
                        ),
                    },
                )
            # Not blocked after all — fall through to normal approval.
        else:
            raise _guardrail_override_blocked_error(
                fact_id,
                "personal_fact_override_invalid",
                f"Override rejected: {override_reason}.",
            )

    # Edit-before-approve: update value if provided
    effective_value = edited_value if edited_value else original_value

    if not effective_value:
        raise HTTPException(
            status_code=400, detail="Fact value cannot be empty"
        )

    # If editing, update the value first (creates revision)
    if edited_value and edited_value != original_value:
        db.update_fact(
            fact_id,
            value=effective_value,
            actor="user",
            reason=(
                f"edited before approval: {body.reason}"
                if body.reason
                else "edited before approval"
            ),
        )

    # If key changed, update key
    if effective_key and effective_key != key:
        db.update_fact(
            fact_id,
            value=effective_value,
            actor="user",
            reason=(
                f"key changed to '{effective_key}' before approval"
            ),
        )

    # Promote to verified
    confidence = body.confidence
    if confidence is None:
        confidence = max(float(fact.get("confidence") or 0.5), 0.5)

    updated = db.update_fact(
        fact_id,
        status="verified",
        confidence=confidence,
        actor="user",
        reason=body.reason or "candidate approved",
    )

    logger.info(
        "Candidate approved fact_id=%s key=%s user=%s edited=%s",
        fact_id,
        effective_key,
        current_user,
        bool(edited_value),
    )
    return {"ok": True, "fact": updated}


@router.post(
    "/candidates/{fact_id}/reject",
    dependencies=[Depends(require_api_key)],
)
def reject_candidate(
    fact_id: int,
    body: CandidateRejectRequest = Body(default=CandidateRejectRequest()),
    current_user: str = Depends(get_current_user),
) -> dict[str, Any]:
    """Reject a fact candidate.

    Sets the fact status to 'disputed' (semantically: user rejects the
    candidate as incorrect, not useful, duplicate, sensitive, or other).
    Evidence rows are preserved. A revision record captures the reason.
    """
    db = _get_chatlog_db()
    fact = db.get_fact(fact_id)
    if not fact or fact.get("user_id") != current_user:
        raise HTTPException(status_code=404, detail="fact not found")

    current_status = str(fact.get("status") or "").strip().lower()
    if current_status not in ("candidate",):
        raise HTTPException(
            status_code=409,
            detail={
                "error": "not_candidate",
                "current_status": current_status,
                "message": f"Fact is already {current_status}. Only candidate facts can be rejected.",
            },
        )

    reason = (body.reason or "candidate rejected").strip()
    updated = db.update_fact(
        fact_id,
        status="disputed",
        actor="user",
        reason=reason,
    )

    logger.info(
        "Candidate rejected fact_id=%s key=%s user=%s reason=%s",
        fact_id,
        str(fact.get("key") or ""),
        current_user,
        reason,
    )
    return {"ok": True, "fact": updated}


@router.get("/{fact_id}/evidence", dependencies=[Depends(require_api_key)])
def list_fact_evidence(
    fact_id: int,
    current_user: str = Depends(get_current_user),
) -> dict[str, Any]:
    db = _get_chatlog_db()
    fact = db.get_fact(fact_id)
    if not fact or fact.get("user_id") != current_user:
        raise HTTPException(status_code=404, detail="fact not found")
    evidence = db.list_fact_evidence(fact_id)
    return {"ok": True, "evidence": evidence}


@router.post("/{fact_id}/evidence", dependencies=[Depends(require_api_key)])
def add_fact_evidence(
    fact_id: int,
    body: EvidenceCreate = Body(...),
    current_user: str = Depends(get_current_user),
) -> dict[str, Any]:
    db = _get_chatlog_db()
    fact = db.get_fact(fact_id)
    if not fact or fact.get("user_id") != current_user:
        raise HTTPException(status_code=404, detail="fact not found")
    evidence_id = db.add_fact_evidence(
        fact_id,
        body.source_message_id,
        body.excerpt,
        modality=body.modality,
        confidence=body.confidence,
        source_type=body.source_type,
        evidence_meta=body.evidence_meta,
    )
    return {"ok": True, "id": evidence_id}


@router.get("/{fact_id}/revisions", dependencies=[Depends(require_api_key)])
def list_fact_revisions(
    fact_id: int,
    current_user: str = Depends(get_current_user),
) -> dict[str, Any]:
    db = _get_chatlog_db()
    fact = db.get_fact(fact_id)
    if not fact or fact.get("user_id") != current_user:
        raise HTTPException(status_code=404, detail="fact not found")
    revisions = db.get_fact_revisions(fact_id)
    return {"ok": True, "revisions": revisions}


# ── Developer-facing candidate inspection routes ──


@router.get("/candidates", dependencies=[Depends(require_api_key)])
def list_fact_candidates(
    status: str | None = "candidate",
    thread_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
    current_user: str = Depends(get_current_user),
) -> dict[str, Any]:
    """List fact candidates for the current user.

    Supports filtering by status (default: candidate) and thread_id.
    Evidence rows are included inline when available.

    Query params:
        status: filter by fact status (candidate, verified, disputed, archived)
        thread_id: only show facts with evidence linked to this thread
        limit: max results (default 50, max 200)
        offset: pagination offset
    """
    db = _get_chatlog_db()
    limit = max(1, min(limit, 200))

    facts = db.list_facts(
        current_user,
        status=status,
        active_only=True,
        limit=200,
    )

    if thread_id is not None:
        # Filter to facts with evidence linking to the given thread.
        filtered: list[dict[str, Any]] = []
        for fact in facts:
            try:
                evidence = db.list_fact_evidence(fact["id"])
            except Exception:
                evidence = []
            for ev in evidence or []:
                meta = ev.get("evidence_meta") if isinstance(ev, dict) else {}
                if not isinstance(meta, dict):
                    meta = {}
                ev_thread = meta.get("thread_id")
                if ev_thread is not None and int(ev_thread) == thread_id:
                    fact["_evidence"] = ev
                    filtered.append(fact)
                    break
        facts = filtered

    total = len(facts)
    page = facts[offset : offset + limit]
    return {"ok": True, "facts": page, "total": total, "limit": limit, "offset": offset}


@router.get("/candidates/debug/recent", dependencies=[Depends(require_api_key)])
def debug_recent_candidates(
    limit: int = 10,
    current_user: str = Depends(get_current_user),
) -> dict[str, Any]:
    """Quick debug endpoint: most recent candidate facts with evidence."""
    db = _get_chatlog_db()
    limit = max(1, min(limit, 20))
    facts = db.list_facts(
        current_user,
        status="candidate",
        active_only=True,
        limit=limit,
    )
    result: list[dict[str, Any]] = []
    for fact in facts:
        try:
            evidence = db.list_fact_evidence(fact["id"])
        except Exception:
            evidence = []
        fact["_evidence"] = evidence
        result.append(fact)
    return {"ok": True, "facts": result, "count": len(result)}
