"""Flow runner: deterministic execution with budgets and trace capture."""

from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import datetime, timezone
from typing import Any

from guardian.flows.primitives import PrimitiveRegistry
from guardian.flows.security import (
    FlowSecurityError,
    build_preflight_contract,
    build_step_spec,
    coerce_execution_context,
    validate_preflight_contract,
    validate_step,
)
from guardian.flows.spec import CompiledFlow, FlowRun, FlowStepResult

_RUN_CACHE: dict[str, FlowRun] = {}
_REDACT_RE = re.compile(
    r"(api[_-]?key|authorization|cookie|token|secret)", re.IGNORECASE
)


def clear_run_cache() -> None:
    """Clear in-memory idempotency cache."""
    _RUN_CACHE.clear()


def _coerce_compiled_flow(
    compiled_flow: CompiledFlow | dict[str, Any]
) -> CompiledFlow:
    if isinstance(compiled_flow, CompiledFlow):
        return compiled_flow
    return CompiledFlow.model_validate(compiled_flow)


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


def _estimate_tokens(payload: Any) -> int:
    serialized = json.dumps(payload, sort_keys=True, default=str)
    return max(1, len(serialized) // 4)


def _render_template(
    template: str | None, values: dict[str, Any]
) -> str | None:
    if not template:
        return None
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", str(value))
    return rendered


def _redact_payload(
    payload: dict[str, Any], explicit_redactions: list[str]
) -> dict[str, Any]:
    redactions = {field.lower() for field in explicit_redactions}
    sanitized: dict[str, Any] = {}
    for key, value in payload.items():
        key_lower = key.lower()
        if key_lower in redactions or _REDACT_RE.search(key_lower):
            sanitized[key] = "<redacted>"
            continue
        sanitized[key] = value
    return sanitized


def _build_idempotency_key(
    compiled: CompiledFlow,
    context: dict[str, Any],
) -> str | None:
    rendered = _render_template(compiled.idempotency.key_template, context)
    if rendered:
        return rendered
    fallback = context.get("idempotency_key")
    if isinstance(fallback, str) and fallback:
        return fallback
    return None


def run_flow(
    compiled_flow: CompiledFlow | dict[str, Any],
    context: dict[str, Any] | None = None,
    registry: PrimitiveRegistry | None = None,
) -> FlowRun:
    """Execute a compiled flow deterministically and return a trace-rich FlowRun."""
    compiled = _coerce_compiled_flow(compiled_flow)
    run_context = dict(context or {})
    primitive_registry = registry or PrimitiveRegistry.default()

    run_id_seed = json.dumps(
        {"flow_id": compiled.flow_id, "context": run_context},
        sort_keys=True,
        default=str,
    )
    run_id = hashlib.sha256(run_id_seed.encode("utf-8")).hexdigest()[:16]
    idempotency_key = _build_idempotency_key(compiled, run_context)

    if idempotency_key and compiled.idempotency.mode == "return_cached":
        cached = _RUN_CACHE.get(idempotency_key)
        if cached is not None:
            return cached.model_copy(update={"status": "cached"})

    run = FlowRun(
        run_id=run_id,
        flow_id=compiled.flow_id,
        version=compiled.version,
        status="running",
        idempotency_key=idempotency_key,
    )
    run.warnings = [warning.message for warning in compiled.warnings]

    if not compiled.enabled:
        run.status = "blocked"
        run.error = "Flow is disabled"
        run.ended_at = _utcnow()
        return run

    if compiled.requires_confirmation and not run_context.get(
        "confirmed", False
    ):
        run.status = "blocked"
        run.needs_confirmation = True
        run.error = "Flow requires confirmation before side effects are allowed"
        run.warnings = [warning.message for warning in compiled.warnings]
        run.ended_at = _utcnow()
        return run

    if len(compiled.steps) > compiled.budget.max_steps:
        run.status = "failed"
        run.error = "Step budget exceeded before execution"
        run.ended_at = _utcnow()
        return run

    try:
        execution_context = coerce_execution_context(
            run_context.get("execution_context"),
            run_id=run_id,
        )
    except Exception as exc:
        run.status = "failed"
        run.error = f"invalid_execution_context: {exc}"
        run.ended_at = _utcnow()
        return run

    step_specs = [build_step_spec(step) for step in compiled.steps]
    preflight_contract = build_preflight_contract(step_specs)
    run.output = {"preflight_contract": preflight_contract}
    try:
        validate_preflight_contract(preflight_contract, execution_context)
    except FlowSecurityError as exc:
        run.status = "blocked"
        run.error = f"{exc.code}: {exc.message}"
        run.ended_at = _utcnow()
        return run

    started_monotonic = time.monotonic()
    consumed_tokens = 0
    step_outputs: dict[str, dict[str, Any]] = {}

    for step, step_spec in zip(compiled.steps, step_specs):
        elapsed = time.monotonic() - started_monotonic
        if elapsed > compiled.budget.timeout_seconds:
            run.status = "failed"
            run.error = "Execution timed out"
            break

        if len(run.step_results) >= compiled.budget.max_steps:
            run.status = "failed"
            run.error = "Step budget exhausted during execution"
            break

        step_started = _utcnow()
        sanitized_params = _redact_payload(
            step.params, compiled.audit.redact_fields
        )

        try:
            validate_step(step_spec, execution_context)
        except FlowSecurityError as exc:
            step_error = f"{exc.code}: {exc.message}"
            run.step_results.append(
                FlowStepResult(
                    step_id=step.step_id,
                    primitive=step.primitive,
                    status="blocked",
                    started_at=step_started,
                    ended_at=_utcnow(),
                    params_redacted=sanitized_params,
                    output={},
                    error=step_error,
                    token_usage=0,
                )
            )
            run.status = "blocked"
            run.error = step_error
            break

        try:
            output = primitive_registry.invoke(
                step.primitive,
                step.params,
                {
                    "flow_id": compiled.flow_id,
                    "step_outputs": step_outputs,
                    "context": run_context,
                },
            )
            consumed_tokens += _estimate_tokens(step.params) + _estimate_tokens(
                output
            )
            step_status = "ok"
            step_error: str | None = None
        except Exception as exc:  # pragma: no cover - defensive path
            output = {}
            step_status = "error"
            step_error = str(exc)

        run.step_results.append(
            FlowStepResult(
                step_id=step.step_id,
                primitive=step.primitive,
                status=step_status,
                started_at=step_started,
                ended_at=_utcnow(),
                params_redacted=sanitized_params,
                output=output,
                error=step_error,
                token_usage=_estimate_tokens(output) if output else 0,
            )
        )

        if step_status == "error":
            run.status = "failed"
            run.error = f"Step '{step.step_id}' failed: {step_error}"
            break

        step_outputs[step.step_id] = output

        if consumed_tokens > compiled.budget.max_tokens:
            run.status = "failed"
            run.error = "Token budget exhausted during execution"
            break

    if run.status == "running":
        run.status = "success"

    run.output["step_outputs"] = step_outputs
    run.ended_at = _utcnow()

    if idempotency_key and compiled.idempotency.mode in {
        "return_cached",
        "skip_if_running",
    }:
        _RUN_CACHE[idempotency_key] = run

    return run
