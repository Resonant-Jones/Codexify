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
    updated = db.update_fact(
        fact_id,
        status="verified",
        actor="user",
        reason=body.reason,
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
