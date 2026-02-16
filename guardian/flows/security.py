"""Flow execution security policy for pre-auth, scopes, and egress."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Iterable
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FlowSecurityError(ValueError):
    """Raised when a flow violates execution boundary policy."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class FlowExecutionContext(BaseModel):
    """Runtime capability envelope established before flow execution."""

    pre_authenticated: bool
    granted_scopes: list[str] = Field(default_factory=list)
    allowed_external_domains: list[str] = Field(default_factory=list)
    allow_network_egress: bool = False
    run_id: str
    issued_at: datetime
    expires_at: datetime

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_window(self) -> FlowExecutionContext:
        if self.expires_at <= self.issued_at:
            raise ValueError("expires_at must be after issued_at")
        return self


class FlowStepSpec(BaseModel):
    """Security-relevant normalized step contract."""

    step_id: str = Field(min_length=1)
    action: str = Field(min_length=1)
    required_scopes: list[str] = Field(default_factory=list)
    external_domain: str | None = None
    requires_network: bool = False
    requests_auth: bool = False
    requested_scopes: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


def _coerce_scopes(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, (str, bytes)):
        value = str(raw).strip()
        return [value] if value else []
    if isinstance(raw, Iterable):
        out: list[str] = []
        for item in raw:
            value = str(item).strip()
            if value:
                out.append(value)
        return sorted(set(out))
    return []


def normalize_domain(value: Any) -> str | None:
    raw = str(value or "").strip().lower()
    if not raw:
        return None
    candidate = raw if "://" in raw else f"https://{raw}"
    parsed = urlparse(candidate)
    host = (parsed.hostname or "").strip().lower()
    return host or None


def coerce_execution_context(
    raw_context: FlowExecutionContext | dict[str, Any] | None,
    *,
    run_id: str,
) -> FlowExecutionContext:
    now = _utcnow()
    if isinstance(raw_context, FlowExecutionContext):
        return raw_context

    payload = dict(raw_context or {})
    payload.setdefault("pre_authenticated", True)
    payload.setdefault("granted_scopes", [])
    payload.setdefault("allowed_external_domains", [])
    payload.setdefault("allow_network_egress", False)
    payload.setdefault("run_id", run_id)
    payload.setdefault("issued_at", now)
    payload.setdefault("expires_at", now + timedelta(minutes=15))
    return FlowExecutionContext.model_validate(payload)


def build_step_spec(step: Any) -> FlowStepSpec:
    params = dict(getattr(step, "params", {}) or {})
    action = str(getattr(step, "action", "") or getattr(step, "primitive", ""))
    requested_scopes = _coerce_scopes(
        getattr(step, "requested_scopes", None)
        or params.get("request_scopes")
        or params.get("additional_scopes")
        or params.get("grant_scopes")
    )
    external_domain = getattr(step, "external_domain", None) or params.get(
        "external_domain"
    )
    if not external_domain and isinstance(params.get("url"), str):
        external_domain = normalize_domain(params.get("url"))
    return FlowStepSpec(
        step_id=str(getattr(step, "step_id", "")),
        action=action,
        required_scopes=_coerce_scopes(
            getattr(step, "required_scopes", None)
            or params.get("required_scopes")
        ),
        external_domain=normalize_domain(external_domain),
        requires_network=bool(
            getattr(step, "requires_network", False)
            or params.get("requires_network")
        ),
        requests_auth=bool(
            getattr(step, "requests_auth", False)
            or action.lower() in {"request_auth", "authenticate"}
            or action.lower().startswith("oauth_")
            or action.lower().startswith("auth_")
            or action.lower().startswith("request_scope")
            or action.lower().startswith("grant_scope")
            or params.get("request_auth")
            or params.get("prompt_for_auth")
            or params.get("auth_prompt")
        ),
        requested_scopes=requested_scopes,
    )


def build_preflight_contract(step_specs: list[FlowStepSpec]) -> dict[str, Any]:
    required_scopes = sorted(
        {scope for step in step_specs for scope in step.required_scopes}
    )
    external_domains = sorted(
        {
            domain
            for step in step_specs
            for domain in [step.external_domain]
            if domain
        }
    )
    return {
        "steps_count": len(step_specs),
        "required_scopes": required_scopes,
        "external_domains": external_domains,
        "requires_network_egress": any(
            step.requires_network for step in step_specs
        ),
    }


def validate_preflight_contract(
    contract: dict[str, Any], ctx: FlowExecutionContext
) -> None:
    if not ctx.pre_authenticated:
        raise FlowSecurityError(
            "pre_auth_required",
            "Flow execution requires pre_authenticated=true.",
        )
    if ctx.expires_at <= _utcnow():
        raise FlowSecurityError(
            "execution_context_expired",
            "Execution context is expired.",
        )

    granted = set(ctx.granted_scopes)
    required = set(_coerce_scopes(contract.get("required_scopes")))
    missing = sorted(required - granted)
    if missing:
        raise FlowSecurityError(
            "missing_scopes",
            f"Flow requires scopes not granted at run start: {missing}",
        )

    requires_network = bool(contract.get("requires_network_egress"))
    if requires_network and not ctx.allow_network_egress:
        raise FlowSecurityError(
            "network_egress_blocked",
            "Flow requires network egress but allow_network_egress is false.",
        )

    allowed_domains = {
        d
        for d in (normalize_domain(v) for v in ctx.allowed_external_domains)
        if d
    }
    external_domains = {
        d
        for d in (
            normalize_domain(v) for v in contract.get("external_domains") or []
        )
        if d
    }
    not_allowed = sorted(external_domains - allowed_domains)
    if not_allowed:
        raise FlowSecurityError(
            "external_domain_not_allowed",
            f"Flow targets domains not pre-approved in execution context: {not_allowed}",
        )


def validate_step(step_spec: FlowStepSpec, ctx: FlowExecutionContext) -> None:
    if step_spec.requests_auth:
        raise FlowSecurityError(
            "mid_flow_auth_forbidden",
            f"Step '{step_spec.step_id}' attempted mid-flow auth request.",
        )
    if step_spec.requested_scopes:
        raise FlowSecurityError(
            "scope_escalation_forbidden",
            f"Step '{step_spec.step_id}' attempted to request additional scopes: {step_spec.requested_scopes}",
        )

    granted = set(ctx.granted_scopes)
    required = set(step_spec.required_scopes)
    missing = sorted(required - granted)
    if missing:
        raise FlowSecurityError(
            "missing_scopes",
            f"Step '{step_spec.step_id}' requires missing scopes: {missing}",
        )

    if not step_spec.requires_network:
        return
    if not ctx.allow_network_egress:
        raise FlowSecurityError(
            "network_egress_blocked",
            f"Step '{step_spec.step_id}' requires network egress but execution context forbids it.",
        )
    if not step_spec.external_domain:
        raise FlowSecurityError(
            "external_domain_missing",
            f"Step '{step_spec.step_id}' requires network but external_domain is missing.",
        )
    allowed_domains = {
        d
        for d in (normalize_domain(v) for v in ctx.allowed_external_domains)
        if d
    }
    if step_spec.external_domain not in allowed_domains:
        raise FlowSecurityError(
            "external_domain_not_allowed",
            f"Step '{step_spec.step_id}' targets '{step_spec.external_domain}' which is not pre-approved.",
        )


__all__ = [
    "FlowExecutionContext",
    "FlowSecurityError",
    "FlowStepSpec",
    "build_preflight_contract",
    "build_step_spec",
    "coerce_execution_context",
    "validate_preflight_contract",
    "validate_step",
]
