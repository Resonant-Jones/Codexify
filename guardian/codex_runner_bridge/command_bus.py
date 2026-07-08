"""Internal command-bus exposure for the Guardian Codex Runner preflight bridge."""

from __future__ import annotations

from typing import Any, Mapping

from guardian.command_bus.contracts import CommandSpec, InvokeArguments
from guardian.codex_runner_bridge.adapter import run_codex_runner_json
from guardian.codex_runner_bridge.contracts import (
    GuardianBridgeOperation,
    GuardianBridgeRequest,
    GuardianBridgeResponse,
    GuardianBridgeResponseMode,
)

INTERNAL_VALIDATE_PLAN_PACK_COMMAND_ID = (
    "internal::guardian.codex_runner.validate_plan_pack"
)
INTERNAL_ORCHESTRATE_DRY_RUN_PREFLIGHT_COMMAND_ID = (
    "internal::guardian.codex_runner.orchestrate_dry_run_preflight"
)

_INTERNAL_COMMAND_ID_TO_OPERATION: dict[str, GuardianBridgeOperation] = {
    INTERNAL_VALIDATE_PLAN_PACK_COMMAND_ID: GuardianBridgeOperation.VALIDATE_PLAN_PACK,
    INTERNAL_ORCHESTRATE_DRY_RUN_PREFLIGHT_COMMAND_ID: (
        GuardianBridgeOperation.ORCHESTRATE_DRY_RUN_PREFLIGHT
    ),
}


def build_guardian_bridge_command_specs() -> list[CommandSpec]:
    """Return the internal command-bus manifest entries for the bridge."""

    return [
        _build_command_spec(command_id=INTERNAL_VALIDATE_PLAN_PACK_COMMAND_ID),
        _build_command_spec(
            command_id=INTERNAL_ORCHESTRATE_DRY_RUN_PREFLIGHT_COMMAND_ID
        ),
    ]


def is_guardian_bridge_command(command_id: str) -> bool:
    return command_id in _INTERNAL_COMMAND_ID_TO_OPERATION


def execute_guardian_bridge_command(
    *,
    command_id: str,
    arguments: InvokeArguments,
) -> dict[str, Any]:
    operation = _operation_for_command_id(command_id)
    body = _body_arguments(arguments)

    plan_pack_path = _required_text(body.get("plan_pack_path"), "plan_pack_path")
    validation_receipt_path = _validation_receipt_path(command_id, body)
    requested_by = _optional_text(body.get("requested_by")) or "command_bus"
    correlation_id = (
        _optional_text(body.get("correlation_id"))
        or f"command_bus::{command_id}"
    )

    request = GuardianBridgeRequest(
        operation=operation,
        plan_pack_path=plan_pack_path,
        validation_receipt_path=validation_receipt_path,
        write_receipt=False,
        write_orchestration_log=False,
        write_orchestration_receipt=False,
        response_mode=GuardianBridgeResponseMode.JSON,
        requested_by=requested_by,
        correlation_id=correlation_id,
    )
    response = run_codex_runner_json(request)
    return _serialize_response(response)


def _build_command_spec(*, command_id: str) -> CommandSpec:
    return CommandSpec(
        command_id=command_id,
        aliases=[],
        layer="internal",
        method="INTERNAL",
        path_template="",
        operation_id=None,
        risk="read_only",
        effect="read",
        idempotency="safe",
        approval_mode="none",
        input_schema=_internal_command_input_schema(),
    )


def _operation_for_command_id(command_id: str) -> GuardianBridgeOperation:
    operation = _INTERNAL_COMMAND_ID_TO_OPERATION.get(command_id)
    if operation is None:
        raise ValueError(f"Unsupported bridge command: {command_id}")
    return operation


def _body_arguments(arguments: InvokeArguments) -> dict[str, Any]:
    body = arguments.body
    if body is None:
        return {}
    if isinstance(body, dict):
        return dict(body)
    if isinstance(body, Mapping):
        return dict(body)
    raise ValueError("bridge command arguments.body must be an object.")


def _required_text(value: object, field_name: str) -> str:
    text = _optional_text(value)
    if text is None:
        raise ValueError(f"{field_name} is required.")
    return text


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _validation_receipt_path(
    command_id: str, body: Mapping[str, Any]
) -> str | None:
    raw_value = body.get("validation_receipt_path")
    if command_id == INTERNAL_ORCHESTRATE_DRY_RUN_PREFLIGHT_COMMAND_ID:
        return _required_text(raw_value, "validation_receipt_path")
    return _optional_text(raw_value)


def _serialize_response(response: GuardianBridgeResponse) -> dict[str, Any]:
    return {
        "command_kind": response.command_kind,
        "result": response.result.value,
        "reason": response.reason,
        "correlation_id": response.correlation_id,
        "stdout_text": response.stdout_text,
        "json_payload": response.json_payload,
        "evidence_paths": {
            "validation_receipt_path": _path_to_str(
                response.evidence_paths.validation_receipt_path
            ),
            "orchestration_log_path": _path_to_str(
                response.evidence_paths.orchestration_log_path
            ),
            "orchestration_receipt_path": _path_to_str(
                response.evidence_paths.orchestration_receipt_path
            ),
        },
        "authority": {
            "guardian_operational": response.authority.guardian_operational,
            "plan_execution_allowed": response.authority.plan_execution_allowed,
            "pi_loop_invocation_allowed": (
                response.authority.pi_loop_invocation_allowed
            ),
            "codexify_ingestion_allowed": (
                response.authority.codexify_ingestion_allowed
            ),
            "durable_mutation_allowed": response.authority.durable_mutation_allowed,
            "provider_execution_allowed": (
                response.authority.provider_execution_allowed
            ),
            "patch_application_allowed": response.authority.patch_application_allowed,
            "dispatch_allowed": response.authority.dispatch_allowed,
            "merge_allowed": response.authority.merge_allowed,
        },
        "boundary_label": response.boundary_label,
        "adapter_version": response.adapter_version,
    }


def _path_to_str(path: Any) -> str | None:
    if path is None:
        return None
    return str(path)


def _internal_command_input_schema() -> dict[str, Any]:
    return {
        "path_params": _empty_object_schema(),
        "query": _empty_object_schema(),
        "headers": _empty_object_schema(),
        "body": _internal_command_body_schema(),
    }


def _empty_object_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {},
        "required": [],
    }


def _internal_command_body_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "plan_pack_path": {"type": "string"},
            "validation_receipt_path": {"type": "string"},
            "requested_by": {"type": "string"},
            "correlation_id": {"type": "string"},
        },
        "required": ["plan_pack_path", "requested_by", "correlation_id"],
    }


__all__ = [
    "INTERNAL_ORCHESTRATE_DRY_RUN_PREFLIGHT_COMMAND_ID",
    "INTERNAL_VALIDATE_PLAN_PACK_COMMAND_ID",
    "build_guardian_bridge_command_specs",
    "execute_guardian_bridge_command",
    "is_guardian_bridge_command",
]
