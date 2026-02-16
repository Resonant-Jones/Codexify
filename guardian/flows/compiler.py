"""FlowSpec compiler: normalize and validate executable plans."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from guardian.flows.primitives import PrimitiveRegistry
from guardian.flows.spec import (
    CompilationWarning,
    CompiledFlow,
    CompiledStep,
    FlowSpec,
)


def _coerce_flowspec(flow_spec: FlowSpec | dict[str, Any]) -> FlowSpec:
    if isinstance(flow_spec, FlowSpec):
        return flow_spec
    return FlowSpec.model_validate(flow_spec)


def compile_flow(
    flow_spec: FlowSpec | dict[str, Any],
    registry: PrimitiveRegistry | None = None,
) -> CompiledFlow:
    """Compile a FlowSpec into a normalized, executable deterministic plan."""
    spec = _coerce_flowspec(flow_spec)
    primitive_registry = registry or PrimitiveRegistry.default()

    warnings: list[CompilationWarning] = []
    compiled_steps: list[CompiledStep] = []
    has_side_effects = False

    for step in spec.steps:
        if not primitive_registry.has(step.primitive):
            raise ValueError(
                f"Unknown primitive '{step.primitive}' in step '{step.step_id}'"
            )

        registration = primitive_registry.get(step.primitive)
        try:
            normalized_params = primitive_registry.validate_params(
                step.primitive, step.params
            )
        except ValidationError as exc:
            raise ValueError(
                f"Invalid params for primitive '{step.primitive}' in step "
                f"'{step.step_id}': {exc.errors()}"
            ) from exc

        side_effecting = registration.contract.side_effecting
        has_side_effects = has_side_effects or side_effecting
        compiled_steps.append(
            CompiledStep(
                step_id=step.step_id,
                primitive=step.primitive,
                params=normalized_params,
                side_effecting=side_effecting,
                required_scopes=step.required_scopes,
                external_domain=step.external_domain,
                requires_network=step.requires_network,
                requests_auth=step.requests_auth,
                requested_scopes=step.requested_scopes,
            )
        )

    if (
        has_side_effects
        and not spec.policy.allow_side_effects_without_confirmation
    ):
        warnings.append(
            CompilationWarning(
                code="SIDE_EFFECT_POLICY_BLOCK",
                message=(
                    "Flow contains side-effecting steps but policy does not allow "
                    "unconfirmed side effects."
                ),
            )
        )

    if spec.trigger.type != "manual" and has_side_effects:
        warnings.append(
            CompilationWarning(
                code="NON_MANUAL_SIDE_EFFECTS",
                message=(
                    "Non-manual trigger with side-effecting steps requires explicit "
                    "confirmation handling."
                ),
            )
        )

    # Compiler safety warnings are always confirmation-gated. Confidence-threshold
    # toggles are applied at NL drafting time and must not disable explicit
    # side-effect safety enforcement.
    requires_confirmation = bool(warnings)

    return CompiledFlow(
        flow_id=spec.flow_id,
        version=spec.version,
        enabled=spec.enabled,
        trigger=spec.trigger,
        scope=spec.scope,
        budget=spec.budget,
        policy=spec.policy,
        steps=compiled_steps,
        output=spec.output,
        idempotency=spec.idempotency,
        audit=spec.audit,
        warnings=warnings,
        has_side_effects=has_side_effects,
        requires_confirmation=requires_confirmation,
    )
