"""FlowSpec compiler: normalize and validate executable plans."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from guardian.flows.primitives import PrimitiveRegistry
from guardian.flows.spec import (
    CompiledFlow,
    CompiledStep,
    CompilationWarning,
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
            )
        )

    if has_side_effects and not spec.policy.allow_side_effects_without_confirmation:
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

    requires_confirmation = bool(warnings) and spec.policy.require_confirmation_below_threshold

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
