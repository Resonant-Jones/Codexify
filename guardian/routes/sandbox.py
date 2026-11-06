"""
Sandbox execution operator route.

Exposes the provider-neutral sandbox contract over HTTP so that a worker
(which owns the provider credential) can execute a bounded request without
knowing which provider will run it.

The route never accepts a provider name: the provider is resolved from the
server configuration. That keeps the caller provider-agnostic and prevents a
caller from selecting a provider whose posture is wider than policy allows.

Authentication is a service capability, not operator or account authority: the
caller is a trusted worker, not an end user and not an operator. The route
uses :func:`require_service_capability`, which validates the raw service key
without resolving a principal, so it does not widen the frozen operator-route
surface.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from guardian.core.dependencies import require_service_capability
from guardian.sandbox import (
    SANDBOX_CONTRACT_VERSION,
    SandboxPolicyDenied,
    SandboxRequest,
    get_provider,
    list_providers,
)
from guardian.sandbox.contracts import (
    NETWORK_MODE_ALLOWLIST,
    NETWORK_MODE_DENY,
    ArtifactPolicy,
    NetworkPosture,
    ResourcePosture,
    SecretPosture,
    WorkspaceMaterialization,
)
from guardian.sandbox.policy import default_resource_posture

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sandbox", tags=["Sandbox"])


class SandboxExecuteRequest(BaseModel):
    """A bounded execution request as submitted by a trusted worker."""

    command: str = Field(min_length=1)
    workspace_identity: str = Field(min_length=1)
    workspace_source: str = Field(min_length=1)
    workspace_digest: Optional[str] = None
    working_directory: str = ""
    principal: str = Field(default="worker", min_length=1)
    request_id: Optional[str] = None
    attempt_id: Optional[str] = None
    idempotency_key: Optional[str] = None
    timeout_seconds: Optional[int] = Field(default=None, ge=1)
    cpu_millis: Optional[int] = Field(default=None, ge=1)
    memory_mb: Optional[int] = Field(default=None, ge=1)
    storage_bytes: Optional[int] = Field(default=None, ge=1)
    network_allowlist: list[str] = Field(default_factory=list)
    output_max_bytes: Optional[int] = Field(default=None, ge=1)
    secret_refs: list[str] = Field(default_factory=list)


class SandboxAttestedPostureModel(BaseModel):
    requested: list[str] = Field(default_factory=list)
    established: list[str] = Field(default_factory=list)
    unestablished: list[str] = Field(default_factory=list)
    conformant: bool = True


class SandboxExecuteResponse(BaseModel):
    """The projection of a sandbox result."""

    contract_version: str
    request_id: str
    attempt_id: str
    status: str
    failure_class: Optional[str] = None
    reason: Optional[str] = None
    exit_code: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    output_truncated: bool = False
    attested_posture: SandboxAttestedPostureModel
    provider: str
    region: Optional[str] = None
    sandbox_id: Optional[str] = None
    teardown_status: str = "unknown"
    teardown_warning: Optional[str] = None


class SandboxProviderModel(BaseModel):
    name: str
    supported_postures: list[str] = Field(default_factory=list)


class SandboxProvidersResponse(BaseModel):
    providers: list[SandboxProviderModel] = Field(default_factory=list)


@router.get("/providers", response_model=SandboxProvidersResponse)
def list_sandbox_providers(
    _service_capability: None = Depends(require_service_capability),
):
    """Report the registered providers and the postures each can establish."""
    providers = []
    for name in list_providers():
        try:
            provider = get_provider(name)
            postures = list(provider.supported_postures())
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("sandbox provider %s unavailable: %s", name, exc)
            continue
        providers.append(SandboxProviderModel(name=name, supported_postures=postures))
    return SandboxProvidersResponse(providers=providers)


@router.post("/execute", response_model=SandboxExecuteResponse)
def execute_sandbox(
    request: SandboxExecuteRequest,
    _service_capability: None = Depends(require_service_capability),
):
    """
    Execute one bounded request in the configured sandbox provider.

    A denial (an unsupported posture) is returned as ``denied`` with a
    ``boundary`` failure class. It is never reported as an execution failure,
    and it never falls back to a different provider.
    """
    defaults = default_resource_posture()
    resources = ResourcePosture(
        timeout_seconds=int(request.timeout_seconds or defaults.timeout_seconds),
        cpu_millis=request.cpu_millis or defaults.cpu_millis,
        memory_mb=request.memory_mb or defaults.memory_mb,
        storage_bytes=request.storage_bytes or defaults.storage_bytes,
        output_max_bytes=int(request.output_max_bytes or defaults.output_max_bytes),
    )
    network = NetworkPosture(
        mode=NETWORK_MODE_ALLOWLIST if request.network_allowlist else NETWORK_MODE_DENY,
        allowlist=tuple(request.network_allowlist),
    )

    request_id = request.request_id or f"sbr-{uuid.uuid4().hex[:12]}"
    attempt_id = request.attempt_id or f"att-{uuid.uuid4().hex[:12]}"

    sandbox_request = SandboxRequest(
        contract_version=SANDBOX_CONTRACT_VERSION,
        request_id=request_id,
        idempotency_key=request.idempotency_key or request_id,
        attempt_id=attempt_id,
        deadline_epoch=time.time() + resources.timeout_seconds,
        principal=request.principal,
        lineage={"source": "guardian.routes.sandbox"},
        workspace=WorkspaceMaterialization(
            identity=request.workspace_identity,
            source=request.workspace_source,
            digest=request.workspace_digest,
            working_directory=request.working_directory,
        ),
        command=request.command,
        resources=resources,
        network=network,
        secrets=SecretPosture(refs=tuple(request.secret_refs)),
        artifacts=ArtifactPolicy(),
    )

    try:
        provider = get_provider()
    except SandboxPolicyDenied as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    try:
        result = provider.execute(sandbox_request)
    except SandboxPolicyDenied as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("sandbox execution failed")
        raise HTTPException(status_code=500, detail=f"sandbox_execution_failed:{exc}") from exc

    attested = result.attested_posture
    return SandboxExecuteResponse(
        contract_version=result.contract_version,
        request_id=result.request_id,
        attempt_id=result.attempt_id,
        status=result.status,
        failure_class=result.failure_class,
        reason=result.reason,
        exit_code=result.exit_code,
        stdout=result.stdout.decode("utf-8", "replace"),
        stderr=result.stderr.decode("utf-8", "replace"),
        output_truncated=result.output_truncated,
        attested_posture=SandboxAttestedPostureModel(
            requested=list(attested.requested),
            established=list(attested.established),
            unestablished=list(attested.unestablished),
            conformant=attested.conformant,
        ),
        provider=result.provenance.provider,
        region=result.provenance.region,
        sandbox_id=result.provenance.sandbox_id,
        teardown_status=result.teardown_status,
        teardown_warning=result.teardown_warning,
    )


__all__ = ["router"]
