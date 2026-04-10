"""
Imprint_Zero routes: proposal, acceptance, status, and system prompt summary.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from guardian.cognition.identity_policy import (
    can_run_deep_identity_modeling,
    normalize_identity_depth,
    thread_blocks_identity_modeling,
)
from guardian.cognition.imprints import store as imprint_store
from guardian.cognition.personas import store as persona_store
from guardian.cognition.system_docs import store as system_doc_store
from guardian.cognition.system_prompt_builder import (
    build_guardian_system_prompt,
)
from guardian.core.dependencies import get_current_user, require_api_key
from guardian.services import (
    iddb_settings_service,
    imprint_proposal_service,
    imprint_scope_service,
    imprint_signal_snapshot_service,
)

logger = logging.getLogger(__name__)

try:
    from guardian.core.dependencies import chatlog_db
except Exception:
    chatlog_db = None

router = APIRouter(
    prefix="/api/imprint",
    tags=["Imprint"],
    dependencies=[Depends(require_api_key)],
)
system_prompt_router = APIRouter(
    prefix="/api/system_prompt",
    tags=["SystemPrompt"],
    dependencies=[Depends(require_api_key)],
)
system_docs_router = APIRouter(
    prefix="/api/system_docs",
    tags=["SystemDocs"],
    dependencies=[Depends(require_api_key)],
)

DEFAULT_WARN_TOKENS = 6000
DEFAULT_HARD_TOKENS = 8000


def _parse_threshold_env(value: str | None, default: int) -> int:
    try:
        parsed = int(str(value).strip()) if value is not None else default
        return parsed if parsed > 0 else default
    except (TypeError, ValueError):
        return default


def _resolve_prompt_thresholds() -> tuple[int, int]:
    warn_tokens = _parse_threshold_env(
        os.getenv("SYSTEM_PROMPT_WARN_TOKENS"),
        DEFAULT_WARN_TOKENS,
    )
    hard_tokens = _parse_threshold_env(
        os.getenv("SYSTEM_PROMPT_HARD_TOKENS"),
        DEFAULT_HARD_TOKENS,
    )
    if hard_tokens < warn_tokens:
        hard_tokens = warn_tokens
    return warn_tokens, hard_tokens


def _coerce_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _normalize_segments(raw_segments: Any) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []

    if isinstance(raw_segments, list):
        for segment in raw_segments:
            if not isinstance(segment, dict):
                continue
            name = str(segment.get("name") or "").strip()
            if not name:
                continue
            normalized.append(
                {
                    "name": name,
                    "chars": _coerce_int(segment.get("chars")) or 0,
                    "estimated_tokens": _coerce_int(
                        segment.get("estimated_tokens")
                    )
                    or 0,
                    "truncated": bool(segment.get("truncated")),
                }
            )
        return normalized

    if isinstance(raw_segments, dict):
        for key, value in raw_segments.items():
            name = str(key).strip()
            if not name:
                continue
            chars = _coerce_int(value) or 0
            normalized.append(
                {
                    "name": name,
                    "chars": chars,
                    "estimated_tokens": max(1, chars // 4) if chars > 0 else 0,
                    "truncated": False,
                }
            )
    return normalized


def _threshold_status(
    estimated_tokens_total: int | None, warn_tokens: int, hard_tokens: int
) -> str:
    if estimated_tokens_total is None:
        return "unknown"
    if estimated_tokens_total >= hard_tokens:
        return "hard"
    if estimated_tokens_total >= warn_tokens:
        return "warn"
    return "ok"


def _resolve_user_project(
    current_user: str,
    thread_id: int | None,
    project_id: int | None,
    *,
    mutation: bool = False,
) -> tuple[str, int | None, dict[str, Any] | None]:
    return imprint_scope_service.resolve_user_project_scope(
        current_user,
        thread_id,
        project_id,
        chatlog_backend=chatlog_db,
        mutation=mutation,
    )


def _resolve_project_identity_depth(project_id: int | None) -> str:
    if not project_id or not chatlog_db:
        return "light"
    getter = getattr(chatlog_db, "get_project_identity_depth", None)
    if not callable(getter):
        return "light"
    try:
        return normalize_identity_depth(getter(project_id))
    except Exception as e:
        logger.warning(
            "[imprint] failed to resolve identity_depth project=%s: %s",
            project_id,
            e,
        )
        return "light"


def _identity_updates_allowed(
    user_id: str,
    thread: dict[str, Any] | None,
    *,
    project_identity_depth: str = "light",
    requested_depth: str = "light",
) -> bool:
    settings = iddb_settings_service.get_user_settings(user_id)
    memory_mode = settings.get("memory_mode", "deep")
    if thread_blocks_identity_modeling(thread):
        return False
    if (
        thread
        and bool(thread.get("is_diary") or thread.get("diary_mode"))
        and settings.get("diary_requires_unlock")
    ):
        return False
    if memory_mode == "none":
        return False
    if normalize_identity_depth(requested_depth) == "deep" and (
        not can_run_deep_identity_modeling(project_identity_depth)
    ):
        return False
    return True


def _safe_snippet(text: str | None, length: int = 200) -> str | None:
    if not text:
        return None
    stripped = text.strip()
    if len(stripped) <= length:
        return stripped
    return stripped[: length - 3] + "..."


@router.get("/status")
def get_imprint_status(
    thread_id: int | None = Query(None),
    project_id: int | None = Query(None),
    current_user: str = Depends(get_current_user),
):
    """
    Return persisted active imprint/persona rows and resolved system prompt
    metadata for the current user/project.
    """
    user_id, resolved_project, _thread = _resolve_user_project(
        current_user,
        thread_id,
        project_id,
    )

    imprint = imprint_store.get_active_imprint(user_id, resolved_project)
    persona = persona_store.get_active_persona(user_id, resolved_project)

    system_prompt_meta: dict[str, Any] = {}
    try:
        if build_guardian_system_prompt:
            _, meta = build_guardian_system_prompt(
                user_id=user_id,
                project_id=resolved_project,
                depth="normal",
                bundle=None,
            )
            system_prompt_meta = meta
    except Exception as e:
        logger.warning("[imprint] system prompt meta failed: %s", e)

    segments_present: dict[str, bool] = {}
    segments_payload = system_prompt_meta.get("segments")
    if isinstance(segments_payload, list):
        for segment in segments_payload:
            if not isinstance(segment, dict):
                continue
            name = segment.get("name")
            if not isinstance(name, str):
                continue
            segments_present[name] = int(segment.get("chars") or 0) > 0
    elif isinstance(segments_payload, dict):
        segments_present = {
            str(k): int(v) > 0 for k, v in segments_payload.items()
        }

    return {
        "imprint": imprint
        and {
            "id": imprint.id,
            "status": imprint.status,
            "heat_score": getattr(imprint, "heat_score", None),
            "preferred_name": getattr(imprint, "preferred_name", None),
            "created_at": getattr(imprint, "created_at", None),
        },
        "persona": persona
        and {
            "id": persona.id,
            "source": persona.source,
            "snippet": _safe_snippet(persona.body),
            "created_at": persona.created_at,
        },
        "system_prompt_meta": {
            "estimated_tokens": system_prompt_meta.get("estimated_tokens"),
            "docs_count": system_prompt_meta.get("docs_count"),
            "segments_present": segments_present,
            "segments": system_prompt_meta.get("segments", []),
        },
    }


@router.post("/proposal")
def create_imprint_proposal(
    body: dict[str, Any] = Body(default_factory=dict),
    current_user: str = Depends(get_current_user),
):
    """
    Create a draft Imprint_Zero proposal (imprint + persona text). Does not activate.
    """
    project_id = body.get("project_id")
    thread_id = body.get("thread_id")
    user_id, resolved_project, thread = _resolve_user_project(
        current_user,
        thread_id,
        project_id,
        mutation=True,
    )
    requested_depth = str(
        body.get("requested_depth")
        or body.get("identity_modeling_depth")
        or "light"
    )
    project_identity_depth = _resolve_project_identity_depth(resolved_project)

    if not _identity_updates_allowed(
        user_id,
        thread,
        project_identity_depth=project_identity_depth,
        requested_depth=requested_depth,
    ):
        raise HTTPException(
            status_code=403, detail="identity updates disabled for this context"
        )

    snapshot = imprint_signal_snapshot_service.build_imprint_signal_snapshot(
        user_id=user_id,
        project_id=resolved_project,
        requested_depth=requested_depth,
        project_identity_depth=project_identity_depth,
    )
    proposal = imprint_proposal_service.build_imprint_proposal(snapshot)

    imprint = imprint_store.save_imprint(
        user_id=user_id,
        project_id=resolved_project,
        status="draft",
        guardian_name=proposal.proposal_name,
        preferred_name=proposal.preferred_name,
        style=proposal.prompt_metadata.get("style"),
        grammar_prefs=proposal.prompt_metadata.get("grammar_prefs") or {},
        heat_score=proposal.prompt_metadata.get("heat_score"),
        metrics={
            "proposal_name": proposal.proposal_name,
            "persona_draft": proposal.persona_draft,
            "prompt_metadata": proposal.prompt_metadata,
            "snapshot_version": snapshot.snapshot_version,
            "snapshot_hash": snapshot.snapshot_hash,
            "proposal_version": proposal.proposal_version,
            "generator_version": proposal.generator_version,
        },
    )

    return {
        "proposal": proposal.to_dict(),
        "imprint_draft": {
            "id": imprint.id,
            "user_id": imprint.user_id,
            "project_id": imprint.project_id,
            "guardian_name": imprint.guardian_name,
            "preferred_name": imprint.preferred_name,
            "status": imprint.status,
            "heat_score": imprint.heat_score,
        },
        "persona_draft": proposal.persona_draft,
        "name": proposal.proposal_name,
        "prompt_metadata": proposal.prompt_metadata,
    }


@router.post("/accept")
def accept_imprint(
    body: dict[str, Any] = Body(...),
    current_user: str = Depends(get_current_user),
):
    """
    Activate a draft imprint and upsert persona.
    """
    imprint_id = body.get("imprint_id")
    persona_override = body.get("persona_text_override")
    if imprint_id is None:
        raise HTTPException(status_code=400, detail="imprint_id is required")

    imprint = imprint_store.get_imprint_by_id(imprint_id)
    if not imprint:
        raise HTTPException(status_code=404, detail="imprint not found")

    if str(imprint.user_id).strip() != current_user:
        raise HTTPException(
            status_code=403,
            detail="imprint does not belong to the current user",
        )

    user_id, resolved_project, thread = _resolve_user_project(
        current_user,
        body.get("thread_id"),
        imprint.project_id,
        mutation=True,
    )
    project_identity_depth = _resolve_project_identity_depth(resolved_project)
    if not _identity_updates_allowed(
        user_id,
        thread,
        project_identity_depth=project_identity_depth,
    ):
        raise HTTPException(
            status_code=403, detail="identity updates disabled for this context"
        )

    persona_text = persona_override
    if not persona_text:
        metrics = getattr(imprint, "metrics", {}) or {}
        persona_text = metrics.get("persona_draft")
    if not persona_text:
        persona_text = (
            "You are a reliable Guardian. Answer concisely and safely."
        )

    activated = imprint_store.activate_imprint(imprint_id)
    persona = persona_store.set_persona(
        user_id=user_id,
        project_id=resolved_project,
        body=persona_text,
        source="user" if persona_override else "imprint_zero_seed",
    )

    return {
        "imprint": {
            "id": activated.id,
            "status": activated.status,
            "guardian_name": activated.guardian_name,
            "preferred_name": activated.preferred_name,
            "heat_score": activated.heat_score,
        },
        "persona": {
            "id": persona.id,
            "body": persona.body,
            "source": persona.source,
            "is_active": persona.is_active,
        },
    }


@router.post("/reject")
def reject_imprint(
    body: dict[str, Any] = Body(...),
    current_user: str = Depends(get_current_user),
):
    """Reject a draft imprint; mark as superseded."""
    imprint_id = body.get("imprint_id")
    if imprint_id is None:
        raise HTTPException(status_code=400, detail="imprint_id is required")
    imprint = imprint_scope_service.resolve_owned_imprint_for_mutation(
        current_user,
        imprint_id,
    )
    imprint = imprint_store.supersede_imprint(imprint.id)
    return {"status": "rejected", "imprint_id": imprint_id}


@system_prompt_router.get("/summary")
def system_prompt_summary(
    thread_id: int | None = Query(None),
    project_id: int | None = Query(None),
    current_user: str = Depends(get_current_user),
):
    """Return resolved system prompt metadata for the current user/project."""
    user_id, resolved_project, _ = _resolve_user_project(
        current_user,
        thread_id,
        project_id,
    )
    warn_tokens, hard_tokens = _resolve_prompt_thresholds()
    generated_at = datetime.now(timezone.utc).isoformat()
    try:
        if not build_guardian_system_prompt:
            raise RuntimeError("system prompt builder unavailable")
        _, meta = build_guardian_system_prompt(
            user_id=user_id,
            project_id=resolved_project,
            depth="normal",
            bundle=None,
        )
    except Exception as e:
        logger.warning("[system_prompt] summary failed: %s", e)
        return {
            "estimated_tokens_total": None,
            "threshold": {
                "warn_tokens": warn_tokens,
                "hard_tokens": hard_tokens,
                "status": "unknown",
            },
            "segments": [],
            "docs_count": None,
            "generated_at": generated_at,
            # Legacy compatibility payload
            "estimated_tokens": None,
            "cap_tokens": None,
            "docs_truncated": False,
            "overflow": False,
            "warnings": [],
        }

    segments = _normalize_segments(meta.get("segments"))
    estimated_tokens_total = _coerce_int(
        meta.get("estimated_tokens_total", meta.get("estimated_tokens"))
    )
    if estimated_tokens_total is None:
        estimated_tokens_total = sum(
            int(segment.get("estimated_tokens") or 0) for segment in segments
        )
    status = _threshold_status(estimated_tokens_total, warn_tokens, hard_tokens)

    warnings: list[str] = []
    if status == "warn":
        warnings.append(
            "System prompt is approaching the configured token threshold."
        )
    elif status == "hard":
        warnings.append("System prompt exceeds the configured hard threshold.")
    if bool(meta.get("docs_truncated")):
        warnings.append("System docs truncated due to token budget.")

    return {
        "estimated_tokens_total": estimated_tokens_total,
        "threshold": {
            "warn_tokens": warn_tokens,
            "hard_tokens": hard_tokens,
            "status": status,
        },
        "segments": segments,
        "docs_count": meta.get("docs_count"),
        "generated_at": generated_at,
        # Legacy compatibility payload
        "estimated_tokens": estimated_tokens_total,
        "cap_tokens": meta.get("cap_tokens"),
        "docs_truncated": bool(meta.get("docs_truncated")),
        "overflow": meta.get("overflow"),
        "warnings": warnings,
    }


@router.post("/persona")
def update_persona(
    body: dict[str, Any] = Body(...),
    current_user: str = Depends(get_current_user),
):
    """Explicitly set persona text (source=user) for the current user/project."""
    logger.info("[api/system-prompt/save] incoming body %s", body)
    text = (
        body.get("body")
        or body.get("persona_prompt")
        or body.get("system_prompt")
    )
    thread_id = body.get("thread_id")
    project_id = body.get("project_id")
    if not text or not str(text).strip():
        raise HTTPException(status_code=400, detail="body is required")
    user_id, resolved_project, thread = _resolve_user_project(
        current_user,
        thread_id,
        project_id,
        mutation=True,
    )
    project_identity_depth = _resolve_project_identity_depth(resolved_project)
    if not _identity_updates_allowed(
        user_id,
        thread,
        project_identity_depth=project_identity_depth,
    ):
        raise HTTPException(
            status_code=403, detail="identity updates disabled for this context"
        )
    try:
        logger.info(
            "[persona_prompt] updating active prompt %s",
            {"userId": user_id, "personaId": None},
        )
        persona = persona_store.set_persona(
            user_id, resolved_project, str(text), source="user"
        )
        logger.info(
            "[persona_prompt_versions] inserting version row %s",
            {"userId": user_id, "personaId": persona.id},
        )
        return {
            "id": persona.id,
            "body": persona.body,
            "source": persona.source,
            "is_active": persona.is_active,
            "created_at": getattr(persona, "created_at", None),
        }
    except Exception as e:
        logger.exception("[system-prompt persistence] DB error %s", e)
        return JSONResponse(
            status_code=500, content={"ok": False, "error": "update failed"}
        )


@system_docs_router.get("")
def list_system_docs(
    thread_id: int | None = Query(None),
    project_id: int | None = Query(None),
    current_user: str = Depends(get_current_user),
):
    """List system docs for current user/project with enable state."""
    user_id, resolved_project, _ = _resolve_user_project(
        current_user,
        thread_id,
        project_id,
    )
    docs = system_doc_store.list_docs_with_links(user_id, resolved_project)
    out = []
    for doc, enabled in docs:
        out.append(
            {
                "id": doc.id,
                "title": doc.title,
                "scope": doc.scope,
                "enabled": bool(enabled),
                "token_estimate": system_doc_store.estimate_token_cost_for_docs(
                    [doc]
                ),
            }
        )
    return {"docs": out}


@system_docs_router.post("/toggle")
def toggle_system_doc(
    body: dict[str, Any] = Body(...),
    current_user: str = Depends(get_current_user),
):
    """Enable/disable a system doc link for current user/project."""
    doc_id = body.get("doc_id")
    enabled = body.get("enabled")
    thread_id = body.get("thread_id")
    project_id = body.get("project_id")
    if doc_id is None or enabled is None:
        raise HTTPException(
            status_code=400, detail="doc_id and enabled are required"
        )
    user_id, resolved_project, _ = _resolve_user_project(
        current_user,
        thread_id,
        project_id,
        mutation=True,
    )
    try:
        system_doc_store.set_doc_link(
            user_id, resolved_project, int(doc_id), bool(enabled)
        )
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.warning("[system_docs] toggle failed: %s", e)
        return JSONResponse(
            status_code=500, content={"ok": False, "error": "toggle failed"}
        )
