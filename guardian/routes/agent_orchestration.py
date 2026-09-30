"""Agent orchestration routes for delegated multi-agent runs."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import subprocess
from typing import Any, AsyncGenerator

from fastapi import (
    APIRouter,
    Body,
    Depends,
    Header,
    HTTPException,
    Query,
    Request,
)
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, SecretStr

from guardian.agents.coding_agent_contracts import (
    CodingExecutionBinding,
    CodingAgentResult,
    CodingAgentTaskEnvelope,
)
from guardian.agents.credential_transport import seal_lease_payload
from guardian.agents.execution_credentials import (
    CredentialAuthorityError,
    authorize_credential_selection,
    issue_api_key_lease,
    list_account_credentials,
    revoke_account_credential,
    store_api_key,
)
from guardian.agents.events import AgentEventPublisher, publisher
from guardian.agents.store import AgentStore, store
from guardian.core.dependencies import (
    get_account_user as get_current_user,
    require_account_session as require_api_key,
    require_operator_auth,
    require_service_api_key,
)
from guardian.db.models import ChatMessage, ChatThread, Project
from guardian.protocol_tokens import AcceptanceStatus
from guardian.queue import task_events

router = APIRouter(
    prefix="/api/agents",
    tags=["Agent Orchestration"],
)
chat_router = APIRouter(
    tags=["Agent Orchestration"],
    dependencies=[Depends(require_api_key)],
)

_store: AgentStore = store
_event_publisher: AgentEventPublisher = publisher

ALLOWED_RUNTIME_TARGETS = {"container", "terminal"}
DEFAULT_CODING_ADAPTER_KIND = "pi_codex_runner"
# `pi_codex_runner` is the legacy-compatible Pi broker runner name. It must
# not be interpreted as direct Codex CLI execution, and direct Codex/Claude
# adapter targets are unsupported for this module.


def configure_db(db: Any | None) -> None:
    _store.configure_db(db)
    _event_publisher.configure_db(db)


def _stable_hash(payload: dict[str, Any]) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _coerce_optional_positive_int(raw: Any) -> int | None:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _resolved_request_user(current_user: Any, requested_user: str) -> str:
    resolved = str(current_user or "").strip()
    if not resolved or resolved.startswith("Depends("):
        raise HTTPException(status_code=401, detail="account_identity_missing")
    if str(requested_user or "").strip() != resolved:
        raise HTTPException(status_code=403, detail="account_identity_mismatch")
    return resolved


class AgentPlanRequest(BaseModel):
    prompt: str = Field(min_length=1)
    thread_id: int | None = None
    proposed_steps: list[dict[str, Any]] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class AgentDeploymentRequest(BaseModel):
    flow_id: str = Field(min_length=1)
    thread_id: int | None = None
    spec: dict[str, Any] = Field(default_factory=dict)
    spec_hash: str | None = None
    trust_state: str = "supervised"

    model_config = ConfigDict(extra="forbid")


class AgentRunStartRequest(BaseModel):
    runtime_target: str = "container"
    supervised: bool = True

    model_config = ConfigDict(extra="forbid")


class CodingExecutionRequest(BaseModel):
    run_id: str = Field(min_length=1)
    coding_task_id: str = Field(min_length=1)
    campaign_id: str | None = None
    work_order_id: str | None = None
    thread_id: str = Field(min_length=1)
    source_message_id: str = Field(min_length=1)
    attempt_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    project_id: int | None = None
    adapter_kind: str = Field(default=DEFAULT_CODING_ADAPTER_KIND, min_length=1)
    instructions: str = Field(min_length=1)
    repo_root: str | None = None
    context_summary: str | None = None
    permission_policy: dict[str, Any] = Field(default_factory=dict)
    # Optional single validation command; the worker runs it once if allowed.
    validation_command: str | None = None
    max_validation_attempts: int = Field(default=1, ge=1, le=3)
    worktree_lease_id: str | None = None
    require_worktree_lease: bool = False
    commit_after_validation: bool = False
    commit_message: str | None = None
    require_human_review_before_merge: bool = True

    model_config = ConfigDict(extra="forbid")


class CodingExecutionCredentialCreateRequest(BaseModel):
    provider_id: str = Field(min_length=1, max_length=128)
    api_key: SecretStr = Field(min_length=1, max_length=8192)

    model_config = ConfigDict(extra="forbid")


class CodingExecutionCredentialLeaseRequest(BaseModel):
    run_id: str = Field(min_length=1, max_length=128)
    deployment_id: str = Field(min_length=1, max_length=128)
    coding_task_id: str = Field(min_length=1, max_length=255)
    attempt_id: str = Field(min_length=1, max_length=255)
    attempt_index: int = Field(ge=1, le=3)
    worker_public_key: str = Field(min_length=1, max_length=8192)

    model_config = ConfigDict(extra="forbid")


def build_coding_execution_task_payload(
    body: CodingExecutionRequest,
) -> dict[str, Any]:
    payload = body.model_dump(exclude_none=True)
    if "permission_policy" not in payload:
        payload["permission_policy"] = {}
    return payload


def _resolve_coding_harness(envelope: CodingAgentTaskEnvelope) -> tuple[str, str]:
    selection_mode = str(envelope.harness_selection_mode or "").strip().lower()
    if selection_mode == "auto":
        raise HTTPException(status_code=422, detail="auto_harness_selection_unsupported")
    if selection_mode == "default":
        harness_id = (os.getenv("CODEXIFY_DEFAULT_HARNESS") or "pi").strip().lower()
    elif selection_mode == "explicit":
        harness_id = (
            "pi"
            if envelope.adapter_kind in {"pi", "pi_sdk", "pi_codex_runner"}
            else ""
        )
    else:
        raise HTTPException(status_code=422, detail="harness_selection_mode_invalid")
    if harness_id != "pi":
        raise HTTPException(status_code=409, detail="selected_harness_unavailable")
    if envelope.adapter_kind not in {"pi", "pi_sdk", "pi_codex_runner"}:
        raise HTTPException(status_code=409, detail="explicit_harness_unavailable")
    return harness_id, selection_mode


def _validate_coding_lineage(
    *,
    account_id: str,
    thread_id: str,
    source_message_id: str,
    requested_project_id: str | None,
) -> str | None:
    db = getattr(_store, "db", None)
    if db is None or not hasattr(db, "get_session"):
        raise HTTPException(status_code=503, detail="coding_lineage_store_unavailable")
    try:
        thread_key = int(thread_id)
        message_key = int(source_message_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="coding_lineage_invalid") from None

    try:
        with db.get_session() as session:
            thread = session.query(ChatThread).filter_by(id=thread_key).one_or_none()
            message = (
                session.query(ChatMessage)
                .filter_by(
                    id=message_key,
                    thread_id=thread_key,
                    user_id=account_id,
                    role="user",
                )
                .one_or_none()
            )
            if thread is None or str(thread.user_id) != account_id or message is None:
                raise HTTPException(status_code=404, detail="coding_lineage_not_found")
            resolved_project_id = thread.project_id
            if requested_project_id is not None:
                try:
                    supplied_project_id = int(requested_project_id)
                except (TypeError, ValueError):
                    raise HTTPException(status_code=422, detail="coding_project_invalid") from None
                if supplied_project_id != resolved_project_id:
                    raise HTTPException(status_code=403, detail="coding_project_mismatch")
            if resolved_project_id is not None:
                project = (
                    session.query(Project)
                    .filter_by(id=resolved_project_id, user_id=account_id)
                    .one_or_none()
                )
                if project is None:
                    raise HTTPException(status_code=403, detail="coding_project_owner_mismatch")
            return str(resolved_project_id) if resolved_project_id is not None else None
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail="coding_lineage_lookup_failed") from exc


def _build_execution_binding(
    envelope: CodingAgentTaskEnvelope,
    *,
    account_id: str,
) -> dict[str, object]:
    provider_id = str(envelope.provider_id or "").strip()
    model_id = str(envelope.model_id or "").strip()
    credential_ref = str(envelope.credential_ref or "").strip()
    if not provider_id or not model_id or not credential_ref:
        raise HTTPException(status_code=422, detail="execution_binding_identity_required")
    harness_id, selection_mode = _resolve_coding_harness(envelope)
    project_id = _validate_coding_lineage(
        account_id=account_id,
        thread_id=envelope.thread_id,
        source_message_id=envelope.source_message_id,
        requested_project_id=envelope.project_id,
    )
    db = getattr(_store, "db", None)
    try:
        credential = authorize_credential_selection(
            db,
            credential_ref=credential_ref,
            account_id=account_id,
            provider_id=provider_id,
            model_id=model_id,
        )
        binding = CodingExecutionBinding.authorized(
            harness_id=harness_id,
            harness_selection_mode=selection_mode,
            provider_id=provider_id,
            model_id=model_id,
            placement="container",
            credential=credential,
            user_id=account_id,
            project_id=project_id,
            thread_id=envelope.thread_id,
            source_message_id=envelope.source_message_id,
            coding_task_id=envelope.coding_task_id,
            attempt_id=envelope.attempt_id,
            max_attempts=envelope.max_validation_attempts,
        )
    except CredentialAuthorityError as exc:
        raise HTTPException(status_code=403, detail=exc.code) from None
    except Exception as exc:
        raise HTTPException(status_code=503, detail="credential_authority_unavailable") from exc
    return binding.to_dict()


@router.post("/plans", dependencies=[Depends(require_operator_auth)])
async def create_plan(body: AgentPlanRequest) -> dict[str, Any]:
    spec = {
        "prompt": body.prompt,
        "thread_id": body.thread_id,
        "steps": body.proposed_steps,
    }
    plan_hash = _stable_hash(spec)
    return {
        "ok": True,
        "plan_id": f"plan_{plan_hash[:16]}",
        "spec_hash": plan_hash,
        "spec": spec,
    }


@router.post("/deployments", dependencies=[Depends(require_operator_auth)])
async def create_deployment(body: AgentDeploymentRequest) -> dict[str, Any]:
    spec = dict(body.spec or {})
    spec_hash = body.spec_hash or _stable_hash(spec)
    deployment = _store.create_deployment(
        flow_id=body.flow_id,
        thread_id=body.thread_id,
        spec_json=spec,
        spec_hash=spec_hash,
        trust_state=body.trust_state,
    )
    return {"ok": True, "deployment": deployment}


@router.post(
    "/deployments/{deployment_id}/runs",
    dependencies=[Depends(require_operator_auth)],
)
async def start_run(
    deployment_id: str,
    body: AgentRunStartRequest = Body(default_factory=AgentRunStartRequest),
) -> dict[str, Any]:
    runtime_target = (body.runtime_target or "container").strip()
    if runtime_target not in ALLOWED_RUNTIME_TARGETS:
        raise HTTPException(status_code=400, detail="invalid_runtime_target")

    deployment = _store.get_deployment(deployment_id)
    if deployment is None:
        raise HTTPException(status_code=404, detail="deployment_not_found")
    if not body.supervised and deployment.get("trust_state") != "unlocked":
        raise HTTPException(
            status_code=403,
            detail="unsupervised_run_requires_unlocked_deployment",
        )

    run = _store.create_run(
        deployment_id=deployment_id,
        thread_id=deployment.get("thread_id"),
        runtime_target=runtime_target,
        rollback_mode="auto",
        status="running",
    )
    _event_publisher.emit(
        run_id=run["run_id"],
        event_type="created",
        payload={
            "deployment_id": deployment_id,
            "run_id": run["run_id"],
            "runtime_target": runtime_target,
        },
    )
    _event_publisher.emit(
        run_id=run["run_id"],
        event_type="started",
        payload={
            "deployment_id": deployment_id,
            "run_id": run["run_id"],
            "runtime_target": runtime_target,
        },
    )
    return {"ok": True, "run": run}


@router.post("/coding/credentials", dependencies=[Depends(require_api_key)])
async def create_coding_execution_credential(
    body: CodingExecutionCredentialCreateRequest,
    current_user: str = Depends(get_current_user),
) -> dict[str, Any]:
    account_id = str(current_user or "").strip()
    if not account_id or account_id.startswith("Depends("):
        raise HTTPException(status_code=401, detail="account_identity_missing")
    db = getattr(_store, "db", None)
    if db is None:
        raise HTTPException(status_code=503, detail="credential_store_unavailable")
    try:
        record = store_api_key(
            db,
            owner_scope="account",
            owner_id=account_id,
            provider_id=body.provider_id,
            api_key=body.api_key.get_secret_value(),
            funding_route="user_byok",
        )
    except CredentialAuthorityError as exc:
        raise HTTPException(status_code=503, detail=exc.code) from None
    return {"ok": True, "credential": record}


@router.get("/coding/credentials", dependencies=[Depends(require_api_key)])
async def list_coding_execution_credentials(
    current_user: str = Depends(get_current_user),
) -> dict[str, Any]:
    account_id = str(current_user or "").strip()
    if not account_id or account_id.startswith("Depends("):
        raise HTTPException(status_code=401, detail="account_identity_missing")
    db = getattr(_store, "db", None)
    if db is None:
        raise HTTPException(status_code=503, detail="credential_store_unavailable")
    try:
        records = list_account_credentials(db, account_id=account_id)
    except CredentialAuthorityError as exc:
        raise HTTPException(status_code=503, detail=exc.code) from None
    return {"credentials": records}


@router.delete(
    "/coding/credentials/{credential_ref}",
    dependencies=[Depends(require_api_key)],
)
async def revoke_coding_execution_credential(
    credential_ref: str,
    current_user: str = Depends(get_current_user),
) -> dict[str, Any]:
    account_id = str(current_user or "").strip()
    if not account_id or account_id.startswith("Depends("):
        raise HTTPException(status_code=401, detail="account_identity_missing")
    db = getattr(_store, "db", None)
    if db is None:
        raise HTTPException(status_code=503, detail="credential_store_unavailable")
    if not revoke_account_credential(
        db, account_id=account_id, credential_ref=credential_ref
    ):
        raise HTTPException(status_code=404, detail="credential_reference_not_found")
    return {"ok": True, "credential_ref": credential_ref, "status": "revoked"}


@router.post("/coding/execute", dependencies=[Depends(require_api_key)])
async def execute_coding_task(
    envelope: CodingAgentTaskEnvelope,
    current_user: str | None = Depends(get_current_user),
) -> dict[str, Any]:
    """Execute a coding task via a registered coding adapter.

    Takes a CodingAgentTaskEnvelope per ADR-020 and routes to the
    requested adapter kind.

    Returns immediately with run_id. Poll /api/agents/runs/{run_id}/events for progress.
    """
    resolved_user_id = _resolved_request_user(current_user, envelope.user_id)
    execution_binding = _build_execution_binding(
        envelope,
        account_id=resolved_user_id,
    )

    # Create deployment to track this coding task and preserve the requested
    # adapter kind in Guardian-owned intake state.
    flow_id = f"coding_{envelope.coding_task_id}"
    deployment = _store.create_deployment(
        flow_id=flow_id,
        thread_id=int(envelope.thread_id) if envelope.thread_id else None,
        spec_json={
            "coding_task_id": envelope.coding_task_id,
            "campaign_id": envelope.campaign_id,
            "work_order_id": envelope.work_order_id,
            "adapter_kind": envelope.adapter_kind,
            "execution_binding": execution_binding,
            "validation_command": envelope.validation_command,
            "max_validation_attempts": envelope.max_validation_attempts,
            "worktree_lease_id": envelope.worktree_lease_id,
            "require_worktree_lease": envelope.require_worktree_lease,
            "commit_after_validation": envelope.commit_after_validation,
            "commit_message": envelope.commit_message,
            "require_human_review_before_merge": (
                envelope.require_human_review_before_merge
            ),
            "source_thread_id": int(envelope.thread_id)
            if envelope.thread_id
            else None,
            "source_message_id": _coerce_optional_positive_int(
                envelope.source_message_id
            ),
            "user_id": resolved_user_id,
            "project_id": execution_binding.get("project_id"),
            "attempt_id": envelope.attempt_id,
            "instructions": envelope.instructions,
            "repo_root": envelope.repo_root,
            "context_summary": envelope.context_summary,
            "permission_policy": {
                "allow_shell": envelope.permission_policy.allow_shell,
                "allow_network": envelope.permission_policy.allow_network,
                "allow_write": envelope.permission_policy.allow_write,
                "allowed_paths": list(envelope.permission_policy.allowed_paths),
                "max_runtime_seconds": envelope.permission_policy.max_runtime_seconds,
            },
        },
        spec_hash=_stable_hash(
            {
                "coding_task_id": envelope.coding_task_id,
                "campaign_id": envelope.campaign_id,
                "work_order_id": envelope.work_order_id,
                "attempt_id": envelope.attempt_id,
                "adapter_kind": envelope.adapter_kind,
                "execution_binding": execution_binding,
                "validation_command": envelope.validation_command,
                "max_validation_attempts": envelope.max_validation_attempts,
                "worktree_lease_id": envelope.worktree_lease_id,
                "require_worktree_lease": envelope.require_worktree_lease,
                "commit_after_validation": envelope.commit_after_validation,
                "commit_message": envelope.commit_message,
                "require_human_review_before_merge": (
                    envelope.require_human_review_before_merge
                ),
            }
        ),
        trust_state="supervised",
    )

    # Create run for tracking
    # The DB only tracks the execution surface here; the worker resolves the
    # requested registered adapter at execution time.
    run = _store.create_run(
        deployment_id=deployment["deployment_id"],
        thread_id=deployment.get("thread_id"),
        runtime_target="container",
        rollback_mode="auto",
        status="queued",
    )

    # Emit created event
    _event_publisher.emit(
        run_id=run["run_id"],
        event_type="created",
        payload={
            "coding_task_id": envelope.coding_task_id,
            "attempt_id": envelope.attempt_id,
            "deployment_id": deployment["deployment_id"],
            "thread_id": deployment.get("thread_id"),
            "source_thread_id": deployment.get("thread_id"),
            "source_message_id": _coerce_optional_positive_int(
                envelope.source_message_id
            ),
            "adapter_kind": envelope.adapter_kind,
            "execution_binding_id": execution_binding["binding_id"],
            "provider_id": execution_binding["provider_id"],
            "model_id": execution_binding["model_id"],
            "funding_route": execution_binding["funding_route"],
            "credential_owner_scope": execution_binding["credential_owner_scope"],
            "status": "queued",
        },
    )

    # Enqueue for async processing via CodingWorker
    from guardian.queue.redis_queue import enqueue_coding_execution
    from guardian.tasks.types import CodingExecutionTask

    task_payload = {
        "run_id": run["run_id"],
        "deployment_id": deployment["deployment_id"],
        "instructions": envelope.instructions,
        "cwd": envelope.repo_root,
        "timeout_seconds": envelope.permission_policy.max_runtime_seconds,
        "coding_task_id": envelope.coding_task_id,
        "campaign_id": envelope.campaign_id,
        "work_order_id": envelope.work_order_id,
        "attempt_id": envelope.attempt_id,
        "thread_id": int(envelope.thread_id) if envelope.thread_id else None,
        "source_message_id": _coerce_optional_positive_int(
            envelope.source_message_id
        ),
        "source_thread_id": int(envelope.thread_id)
        if envelope.thread_id
        else None,
        "user_id": resolved_user_id,
        "project_id": execution_binding.get("project_id"),
        "execution_binding": execution_binding,
        "validation_command": envelope.validation_command,
        "max_validation_attempts": envelope.max_validation_attempts,
        "worktree_lease_id": envelope.worktree_lease_id,
        "require_worktree_lease": envelope.require_worktree_lease,
        "commit_after_validation": envelope.commit_after_validation,
        "commit_message": envelope.commit_message,
        "require_human_review_before_merge": (
            envelope.require_human_review_before_merge
        ),
        "permission_policy": {
            "allow_shell": envelope.permission_policy.allow_shell,
            "allow_network": envelope.permission_policy.allow_network,
            "allow_write": envelope.permission_policy.allow_write,
            "allowed_paths": list(envelope.permission_policy.allowed_paths),
            "max_runtime_seconds": envelope.permission_policy.max_runtime_seconds,
        },
        "origin": "coding_execute_route",
    }
    enqueue_coding_execution(task_payload)

    return {
        "ok": True,
        "status": AcceptanceStatus.ACCEPTED.value,
        "run_id": run["run_id"],
        "deployment_id": deployment["deployment_id"],
        "coding_task_id": envelope.coding_task_id,
        "campaign_id": envelope.campaign_id,
        "work_order_id": envelope.work_order_id,
        "thread_id": deployment.get("thread_id"),
        "source_thread_id": deployment.get("thread_id"),
        "source_message_id": _coerce_optional_positive_int(
            envelope.source_message_id
        ),
        "attempt_id": envelope.attempt_id,
        "adapter_kind": envelope.adapter_kind,
        "execution_binding_id": execution_binding["binding_id"],
    }


@router.post(
    "/coding/credential-lease",
    dependencies=[Depends(require_service_api_key)],
)
async def lease_coding_execution_credential(
    body: CodingExecutionCredentialLeaseRequest,
) -> dict[str, Any]:
    """Revalidate a persisted binding and seal one attempt's API-key lease."""
    deployment = _store.get_deployment(body.deployment_id)
    if deployment is None:
        raise HTTPException(status_code=404, detail="execution_binding_not_found")
    spec = dict(deployment.get("spec_json") or {})
    raw_binding = spec.get("execution_binding")
    if not isinstance(raw_binding, dict):
        raise HTTPException(status_code=403, detail="execution_binding_missing")
    try:
        binding = CodingExecutionBinding.from_dict(raw_binding)
    except (TypeError, ValueError):
        raise HTTPException(status_code=403, detail="execution_binding_invalid") from None
    if (
        str(deployment.get("deployment_id") or "") != body.deployment_id
        or str(spec.get("coding_task_id") or "") != body.coding_task_id
        or binding.coding_task_id != body.coding_task_id
        or binding.attempt_id != body.attempt_id
        or str(spec.get("attempt_id") or "") != body.attempt_id
    ):
        raise HTTPException(status_code=403, detail="execution_binding_lineage_mismatch")
    run = _store.get_run(body.run_id, user_id=binding.user_id)
    if (
        run is None
        or str(run.get("deployment_id") or "") != body.deployment_id
        or str(run.get("status") or "").lower() not in {"queued", "running"}
    ):
        raise HTTPException(status_code=403, detail="execution_run_not_authorized")
    db = getattr(_store, "db", None)
    if db is None:
        raise HTTPException(status_code=503, detail="credential_authority_unavailable")
    try:
        secret, lease_metadata = issue_api_key_lease(
            db,
            binding=binding.to_dict(),
            account_id=binding.user_id,
            attempt_id=body.attempt_id,
            attempt_index=body.attempt_index,
        )
        sealed = seal_lease_payload(
            body.worker_public_key,
            {
                "api_key": secret,
                "lease": {**binding.to_dict(), **lease_metadata},
            },
        )
    except CredentialAuthorityError as exc:
        raise HTTPException(status_code=403, detail=exc.code) from None
    except Exception as exc:
        raise HTTPException(status_code=503, detail="credential_lease_unavailable") from exc
    return {"sealed_lease": sealed}


@router.post("/pi-invocation/dry-run", dependencies=[Depends(require_operator_auth)])
async def pi_invocation_dry_run(
    body: dict[str, Any],
) -> dict[str, Any]:
    """Validate a proposed Pi/Coder invocation envelope without executing.

    This is a dry-run-only route. It does NOT:
      - call Pi SDK
      - call Coder
      - execute adapters
      - enqueue workers
      - call _store or _event_publisher
      - write to the database
      - create receipts or artifacts
      - persist result-return records
      - write transcript messages
    """
    from guardian.pi.contracts import PiInvocationEnvelope
    from guardian.pi.validation import validate_invocation_envelope
    from guardian.pi.evidence import build_operator_evidence_from_dry_run_response

    envelope = PiInvocationEnvelope.from_payload(body)
    result = validate_invocation_envelope(envelope)

    response = {
        "dry_run": True,
        "accepted": result.ok,
        "state": "validated" if result.ok else "validation_failed",
        "validation_status": result.validation_outcome,
        "errors": list(result.failure_reasons),
        "warnings": [],
        "redaction_state": "clean",
        "release_support": "unsupported",
        "execution_performed": False,
        "persistence_performed": False,
        "invocation_id": envelope.invocation_id or None,
        "source_thread_id": envelope.source_thread_id or None,
        "source_message_id": envelope.source_message_id or None,
        "harness_id": envelope.harness_id or None,
        "permission_posture": _safe_permission_summary(envelope),
    }

    # Include safe operator evidence
    response["operator_evidence"] = build_operator_evidence_from_dry_run_response(
        response=response,
        safe_invocation_id=envelope.invocation_id or None,
        safe_source_thread_id=envelope.source_thread_id or None,
        safe_source_message_id=envelope.source_message_id or None,
        safe_harness_id=envelope.harness_id or None,
    ).to_payload()

    return response


def _safe_permission_summary(envelope: Any) -> str | None:
    """Return a safe permission summary without raw payloads."""
    try:
        requested = envelope.requested_permissions
        if not requested:
            return None
        return ", ".join(
            p.permission
            for p in requested
            if hasattr(p, "permission") and p.permission
        ) or None
    except Exception:
        return None


@router.post("/runs/{run_id}/cancel", dependencies=[Depends(require_api_key)])
async def cancel_run(
    run_id: str,
    current_user: str | None = Depends(get_current_user),
) -> dict[str, Any]:
    request_user = _resolved_request_user(current_user, "") or None
    run = _store.get_run(run_id, user_id=request_user)
    if run is None:
        raise HTTPException(status_code=404, detail="run_not_found")
    _store.update_run_status(run_id=run_id, status="canceled")
    _event_publisher.emit(
        run_id=run_id,
        event_type="canceled",
        payload={"run_id": run_id},
    )
    return {"ok": True, "run_id": run_id, "status": "canceled"}


@router.get("/runs/{run_id}/coding", dependencies=[Depends(require_api_key)])
async def get_coding_run(
    run_id: str,
    current_user: str | None = Depends(get_current_user),
) -> dict[str, Any]:
    request_user = _resolved_request_user(current_user, "") or None
    run = _store.get_coding_run_snapshot(run_id, user_id=request_user)
    if run is None:
        raise HTTPException(status_code=404, detail="run_not_found")
    return {"ok": True, "run": run}


@router.get("/runs/{run_id}", dependencies=[Depends(require_api_key)])
async def get_run(
    run_id: str,
    current_user: str | None = Depends(get_current_user),
) -> dict[str, Any]:
    request_user = _resolved_request_user(current_user, "") or None
    run = _store.get_run(run_id, user_id=request_user)
    if run is None:
        raise HTTPException(status_code=404, detail="run_not_found")
    return {"ok": True, "run": run}


@router.get("/runs/{run_id}/events", dependencies=[Depends(require_api_key)])
async def stream_run_events(
    request: Request,
    run_id: str,
    last_id_query: str = Query("0-0", alias="last_id"),
    last_event_id_header: str | None = Header(None, alias="Last-Event-ID"),
) -> StreamingResponse:
    async def event_stream() -> AsyncGenerator[str, None]:
        last_id = str(last_event_id_header or last_id_query or "0-0")
        if "-" not in last_id:
            last_id = "0-0"
        yield "retry: 3000\n\n"

        heartbeat_elapsed = 0.0
        heartbeat_interval = 15.0
        block_ms = 15000

        while True:
            if await request.is_disconnected():
                break
            try:
                events = await asyncio.to_thread(
                    task_events.read_events,
                    run_id,
                    last_id,
                    block_ms=block_ms,
                    count=100,
                )
            except Exception:
                await asyncio.sleep(1)
                continue

            if events:
                for event_id, event in events:
                    data_str = json.dumps(event.get("data") or {}, default=str)
                    yield f"id: {event_id}\n"
                    yield f"event: {event.get('type') or 'task.event'}\n"
                    yield f"data: {data_str}\n\n"
                    last_id = event_id
                heartbeat_elapsed = 0.0
            else:
                heartbeat_elapsed += block_ms / 1000.0
                if heartbeat_elapsed >= heartbeat_interval:
                    yield ": ping\n\n"
                    heartbeat_elapsed = 0.0

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get(
    "/chat/{thread_id}/agent-runs", dependencies=[Depends(require_api_key)]
)
async def list_thread_runs(thread_id: int) -> dict[str, Any]:
    runs = _store.list_runs_for_thread(thread_id)
    return {"ok": True, "thread_id": thread_id, "runs": runs}


@chat_router.get("/api/chat/{thread_id}/agent-runs")
async def list_thread_runs_via_chat(thread_id: int) -> dict[str, Any]:
    runs = _store.list_runs_for_thread(thread_id)
    return {"ok": True, "thread_id": thread_id, "runs": runs}


@chat_router.get("/api/chat/{thread_id}/coding-runs")
async def list_coding_runs_via_chat(
    thread_id: int,
    current_user: str | None = Depends(get_current_user),
) -> dict[str, Any]:
    request_user = _resolved_request_user(current_user, "") or None
    runs = _store.list_coding_runs_for_thread(thread_id, user_id=request_user)
    return {"ok": True, "thread_id": thread_id, "runs": runs}
