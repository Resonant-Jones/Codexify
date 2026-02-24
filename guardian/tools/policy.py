"""Unified tool policy evaluation for command-bus and legacy shim lanes."""

from __future__ import annotations

import logging
import os
from typing import Any, Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

PolicyMode = Literal["enforce", "warn", "off"]
PolicyDecisionType = Literal["allow", "deny", "require_confirmation"]

_TRUE_VALUES = {"1", "true", "yes", "on"}


class PolicyDecision(BaseModel):
    decision: PolicyDecisionType
    reason_codes: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class PolicyOutcome(BaseModel):
    mode: PolicyMode
    decision: PolicyDecisionType
    blocked: bool
    reason_codes: list[str] = Field(default_factory=list)
    warnings: list[dict[str, Any]] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


def _truthy(raw: str | None) -> bool:
    return str(raw or "").strip().lower() in _TRUE_VALUES


def get_policy_mode(env: Mapping[str, str] | None = None) -> PolicyMode:
    source = env if env is not None else os.environ
    raw = str(source.get("CODEXIFY_POLICY_MODE") or "enforce").strip().lower()
    if raw in {"enforce", "warn", "off"}:
        return raw  # type: ignore[return-value]
    return "enforce"


def is_declared_non_docker_mode(env: Mapping[str, str] | None = None) -> bool:
    source = env if env is not None else os.environ
    return _truthy(source.get("LOCAL_DEV")) or _truthy(source.get("DEBUG"))


def has_resolvable_execution_base(env: Mapping[str, str] | None = None) -> bool:
    source = env if env is not None else os.environ
    if str(source.get("GUARDIAN_COMMAND_BUS_LOOPBACK_BASE") or "").strip():
        return True
    if is_declared_non_docker_mode(source):
        api_base = str(source.get("GUARDIAN_API_BASE") or "").strip()
        if api_base:
            return True
    return False


def evaluate_tool_policy(
    actor: dict[str, Any] | Any,
    command_or_tool: dict[str, Any] | Any,
    args: dict[str, Any] | None,
    env: Mapping[str, str] | None = None,
) -> PolicyDecision:
    """Evaluate policy once, independent of route/transport."""

    _ = actor, args
    command: dict[str, Any]
    if isinstance(command_or_tool, dict):
        command = dict(command_or_tool)
    elif hasattr(command_or_tool, "model_dump"):
        command = command_or_tool.model_dump(mode="json")
    else:
        command = {}

    method = str(command.get("method") or "GET").upper()
    effect = str(command.get("effect") or "").strip().lower()
    if not effect:
        effect = "read" if method in {"GET", "HEAD"} else "write"

    risk = str(command.get("risk") or "").strip().lower()
    approval_mode = str(command.get("approval_mode") or "").strip().lower()
    requires_confirmation = bool(command.get("requires_confirmation")) or (
        approval_mode not in {"", "none"}
    )
    path_template = str(command.get("path_template") or "").strip().lower()

    reason_codes: list[str] = []
    decision: PolicyDecisionType = "allow"

    if effect == "write":
        reason_codes.append("write_effect")
        decision = "require_confirmation"
    if risk in {"mutating", "high"}:
        if "risk_high" not in reason_codes:
            reason_codes.append("risk_high")
        if decision == "allow":
            decision = "require_confirmation"
    if "/external/" in path_template or "/webhook" in path_template:
        if "external_network" not in reason_codes:
            reason_codes.append("external_network")
        if decision == "allow":
            decision = "require_confirmation"
    if requires_confirmation and decision == "allow":
        reason_codes.append("requires_confirmation")
        decision = "require_confirmation"

    requires_transport_execution = effect == "read" and method in {"GET", "HEAD"}
    if requires_transport_execution and not has_resolvable_execution_base(env):
        reason_codes.append("loopback_base_missing")
        decision = "deny"

    metadata = {
        "method": method,
        "effect": effect,
        "risk": risk or "unknown",
        "path_template": str(command.get("path_template") or ""),
    }
    return PolicyDecision(
        decision=decision, reason_codes=reason_codes, metadata=metadata
    )


def apply_policy_mode(
    decision: PolicyDecision,
    mode: PolicyMode | None = None,
    *,
    confirmation_granted: bool = False,
) -> PolicyOutcome:
    resolved_mode = mode or get_policy_mode()
    if resolved_mode == "off":
        logger.info(
            "tool_policy mode=off decision=%s reasons=%s",
            decision.decision,
            decision.reason_codes,
        )
        return PolicyOutcome(
            mode=resolved_mode,
            decision=decision.decision,
            blocked=False,
            reason_codes=list(decision.reason_codes),
            warnings=[],
        )

    if resolved_mode == "warn":
        warnings: list[dict[str, Any]] = []
        if decision.decision != "allow":
            warnings.append(
                {
                    "decision": decision.decision,
                    "reason_codes": list(decision.reason_codes),
                }
            )
            logger.warning(
                "tool_policy mode=warn decision=%s reasons=%s",
                decision.decision,
                decision.reason_codes,
            )
        return PolicyOutcome(
            mode=resolved_mode,
            decision=decision.decision,
            blocked=False,
            reason_codes=list(decision.reason_codes),
            warnings=warnings,
        )

    blocked = decision.decision == "deny" or (
        decision.decision == "require_confirmation"
        and not confirmation_granted
    )
    if blocked:
        logger.warning(
            "tool_policy mode=enforce blocked decision=%s reasons=%s",
            decision.decision,
            decision.reason_codes,
        )
    return PolicyOutcome(
        mode=resolved_mode,
        decision=decision.decision,
        blocked=blocked,
        reason_codes=list(decision.reason_codes),
        warnings=[],
    )
