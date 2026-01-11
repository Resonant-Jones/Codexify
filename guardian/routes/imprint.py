"""
Imprint_Zero routes: proposal, acceptance, status, and system prompt summary.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, HTTPException, Query
from fastapi.responses import JSONResponse

from guardian.cognition.imprints import store as imprint_store
from guardian.cognition.personas import store as persona_store
from guardian.cognition.system_docs import store as system_doc_store
from guardian.cognition.system_prompt_builder import (
    build_guardian_system_prompt,
)
from guardian.cognition.user_settings import store as user_settings_store

logger = logging.getLogger(__name__)

try:
    from guardian.core.dependencies import chatlog_db
except Exception:
    chatlog_db = None

router = APIRouter(prefix="/api/imprint", tags=["Imprint"])
system_prompt_router = APIRouter(
    prefix="/api/system_prompt", tags=["SystemPrompt"]
)
system_docs_router = APIRouter(prefix="/api/system_docs", tags=["SystemDocs"])


def _resolve_user_project(
    thread_id: int | None, project_id: int | None
) -> tuple[str, int | None, dict[str, Any] | None]:
    user_id = "default"
    resolved_project = project_id
    thread: dict[str, Any] | None = None
    if thread_id and chatlog_db:
        try:
            th = chatlog_db.get_chat_thread(thread_id)
            if th:
                user_id = th.get("user_id") or user_id
                if resolved_project is None:
                    resolved_project = th.get("project_id")
                thread = th
        except Exception as e:
            logger.warning(
                "[imprint] failed to resolve thread %s: %s", thread_id, e
            )
    return user_id, resolved_project, thread


def _identity_updates_allowed(
    user_id: str, thread: dict[str, Any] | None
) -> bool:
    settings = user_settings_store.get_user_settings(user_id)
    memory_mode = settings.get("memory_mode", "deep")
    if thread:
        if thread.get("exclude_from_identity"):
            return False
        if thread.get("is_diary") and settings.get("diary_requires_unlock"):
            return False
    if memory_mode == "none":
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
):
    """
    Return active imprint/persona and system prompt meta for current user/project.
    """
    user_id, resolved_project, _thread = _resolve_user_project(
        thread_id, project_id
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

    segments_present = {}
    if system_prompt_meta.get("segments"):
        segments_present = {
            k: (v > 0) for k, v in system_prompt_meta["segments"].items()
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
            "segments": system_prompt_meta.get("segments", {}),
        },
    }


def _generate_name(user_id: str, project_id: int | None) -> str:
    """
    Lightweight, deterministic-ish fallback name generator inspired by ImprintName.ts vibe categories.
    For v1 we use a simple hash-based name to avoid porting the TS generator fully.
    """
    seed = f"{user_id}:{project_id}".encode()
    val = sum(seed) % 10000
    syllables = [
        "Ari",
        "Len",
        "Vor",
        "Ny",
        "Sol",
        "Kai",
        "Ren",
        "Lio",
        "Mira",
        "Cen",
    ]
    return (
        syllables[val % len(syllables)]
        + syllables[(val // len(syllables)) % len(syllables)]
    )


@router.post("/proposal")
def create_imprint_proposal(body: dict[str, Any] = Body(default_factory=dict)):
    """
    Create a draft Imprint_Zero proposal (imprint + persona text). Does not activate.
    """
    project_id = body.get("project_id")
    thread_id = body.get("thread_id")
    user_id, resolved_project, thread = _resolve_user_project(
        thread_id, project_id
    )

    if not _identity_updates_allowed(user_id, thread):
        raise HTTPException(
            status_code=403, detail="identity updates disabled for this context"
        )

    # In a fuller implementation, we would compute marker signals and call the TS name generator.
    name = _generate_name(user_id, resolved_project)
    preferred_name = "friend"

    persona_text = (
        f"You are {name}, the Guardian assistant for this user inside Codexify. "
        f'When the user asks for your name, always reply first with exactly "{name}". '
        "You may optionally add that you are their Guardian inside Codexify.\n\n"
        f'Address the user as "{preferred_name}" when it feels natural. '
        "Respond concisely, with clarity and kindness. Keep answers grounded; when unsure, ask a clarifying question."
    )

    imprint = imprint_store.save_imprint(
        user_id=user_id,
        project_id=resolved_project,
        status="draft",
        guardian_name=name,
        preferred_name=preferred_name,
        style="playful-dry",
        heat_score=0.7,
        metrics={"persona_draft": persona_text, "proposed_name": name},
    )

    return {
        "imprint_draft": {
            "id": imprint.id,
            "user_id": imprint.user_id,
            "project_id": imprint.project_id,
            "guardian_name": imprint.guardian_name,
            "preferred_name": imprint.preferred_name,
            "status": imprint.status,
            "heat_score": imprint.heat_score,
        },
        "persona_draft": persona_text,
        "name": name,
    }


@router.post("/accept")
def accept_imprint(body: dict[str, Any] = Body(...)):
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

    user_id, resolved_project = imprint.user_id, imprint.project_id
    _, _, thread = _resolve_user_project(
        body.get("thread_id"), resolved_project
    )
    if not _identity_updates_allowed(user_id, thread):
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

    # Best-effort: sync persona text into user settings system prompt, if supported.
    try:
        if hasattr(user_settings_store, "set_system_prompt"):
            user_settings_store.set_system_prompt(
                user_id=user_id,
                project_id=resolved_project,
                system_prompt=persona.body,
            )
    except Exception as e:
        logger.warning(
            "[imprint] failed to sync persona to user settings: %s", e
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
def reject_imprint(body: dict[str, Any] = Body(...)):
    """Reject a draft imprint; mark as superseded."""
    imprint_id = body.get("imprint_id")
    if imprint_id is None:
        raise HTTPException(status_code=400, detail="imprint_id is required")
    imprint = imprint_store.supersede_imprint(imprint_id)
    if not imprint:
        raise HTTPException(status_code=404, detail="imprint not found")
    return {"status": "rejected", "imprint_id": imprint_id}


@system_prompt_router.get("/summary")
def system_prompt_summary(
    thread_id: int | None = Query(None),
    project_id: int | None = Query(None),
):
    """Return system prompt meta for the current user/project."""
    user_id, resolved_project, _ = _resolve_user_project(thread_id, project_id)
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
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": "system prompt unavailable"},
        )

    warnings = []
    if meta.get("estimated_tokens", 0) > 1500:
        warnings.append("System prompt is large and may increase cost/latency.")
    if meta.get("docs_truncated"):
        warnings.append("System docs truncated due to token budget.")

    return {
        "estimated_tokens": meta.get("estimated_tokens"),
        "docs_count": meta.get("docs_count"),
        "segments": meta.get("segments"),
        "cap_tokens": meta.get("cap_tokens"),
        "docs_truncated": meta.get("docs_truncated"),
        "overflow": meta.get("overflow"),
        "warnings": warnings,
    }


@router.post("/persona")
def update_persona(body: dict[str, Any] = Body(...)):
    """Explicitly set persona text (source=user) for the current user/project."""
    text = body.get("body")
    thread_id = body.get("thread_id")
    project_id = body.get("project_id")
    if not text or not str(text).strip():
        raise HTTPException(status_code=400, detail="body is required")
    user_id, resolved_project, thread = _resolve_user_project(
        thread_id, project_id
    )
    if not _identity_updates_allowed(user_id, thread):
        raise HTTPException(
            status_code=403, detail="identity updates disabled for this context"
        )
    try:
        persona = persona_store.set_persona(
            user_id, resolved_project, str(text), source="user"
        )
        # Best-effort: sync explicit persona changes into user settings system prompt, if supported.
        try:
            if hasattr(user_settings_store, "set_system_prompt"):
                user_settings_store.set_system_prompt(
                    user_id=user_id,
                    project_id=resolved_project,
                    system_prompt=persona.body,
                )
        except Exception as e:
            logger.warning(
                "[imprint] failed to sync persona to user settings: %s", e
            )
        return {
            "id": persona.id,
            "body": persona.body,
            "source": persona.source,
            "is_active": persona.is_active,
            "created_at": getattr(persona, "created_at", None),
        }
    except Exception as e:
        logger.warning("[imprint] failed to update persona: %s", e)
        return JSONResponse(
            status_code=500, content={"ok": False, "error": "update failed"}
        )


@system_docs_router.get("")
def list_system_docs(
    thread_id: int | None = Query(None),
    project_id: int | None = Query(None),
):
    """List system docs for current user/project with enable state."""
    user_id, resolved_project, _ = _resolve_user_project(thread_id, project_id)
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
def toggle_system_doc(body: dict[str, Any] = Body(...)):
    """Enable/disable a system doc link for current user/project."""
    doc_id = body.get("doc_id")
    enabled = body.get("enabled")
    thread_id = body.get("thread_id")
    project_id = body.get("project_id")
    if doc_id is None or enabled is None:
        raise HTTPException(
            status_code=400, detail="doc_id and enabled are required"
        )
    user_id, resolved_project, _ = _resolve_user_project(thread_id, project_id)
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
