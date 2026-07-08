"""JSON-only backend adapter for the Guardian Codex Runner preflight bridge."""

from __future__ import annotations

import json
import subprocess
from typing import Any

from guardian.codex_runner_bridge.contracts import (
    BOUNDARY_LABEL,
    CODEX_RUNNER_ROOT,
    GuardianBridgeOperation,
    GuardianBridgeRequest,
    GuardianBridgeResponse,
    GuardianBridgeResponseMode,
    GuardianBridgeResult,
    default_authority,
    validate_bridge_request,
)

DEFAULT_TIMEOUT_SECONDS = 30
CODEXRUN_BINARY = "codexrun"
ADAPTER_VERSION = "v0-json-preflight-adapter"


class GuardianBridgeAdapterError(ValueError):
    """Raised when the adapter request cannot be supported safely."""


class GuardianBridgeCommandError(GuardianBridgeAdapterError):
    """Raised when command construction fails before invocation."""


class GuardianBridgeJsonError(GuardianBridgeAdapterError):
    """Raised when a successful command does not return valid JSON."""


class GuardianBridgeUnsupportedOperationError(GuardianBridgeAdapterError):
    """Raised when a request asks for an unsupported bridge operation."""


def build_codex_runner_command(request: GuardianBridgeRequest) -> list[str]:
    validated = validate_bridge_request(request)

    if validated.response_mode != GuardianBridgeResponseMode.JSON:
        raise GuardianBridgeUnsupportedOperationError(
            "Only JSON response_mode is supported by this adapter slice."
        )
    if validated.write_receipt:
        raise GuardianBridgeUnsupportedOperationError(
            "write_receipt is not supported by this adapter slice."
        )
    if validated.write_orchestration_log:
        raise GuardianBridgeUnsupportedOperationError(
            "write_orchestration_log is not supported by this adapter slice."
        )
    if validated.write_orchestration_receipt:
        raise GuardianBridgeUnsupportedOperationError(
            "write_orchestration_receipt is not supported by this adapter slice."
        )

    if validated.operation == GuardianBridgeOperation.VALIDATE_PLAN_PACK:
        return [
            CODEXRUN_BINARY,
            "guardian",
            "validate-plan-pack",
            "--path",
            str(validated.plan_pack_path),
            "--json",
        ]

    if validated.operation == GuardianBridgeOperation.ORCHESTRATE_DRY_RUN_PREFLIGHT:
        if validated.validation_receipt_path is None:
            raise GuardianBridgeCommandError(
                "validation_receipt_path is required for orchestrate_dry_run_preflight."
            )
        return [
            CODEXRUN_BINARY,
            "guardian",
            "orchestrate-dry-run",
            "--plan-pack",
            str(validated.plan_pack_path),
            "--require-receipt",
            str(validated.validation_receipt_path),
            "--json",
        ]

    raise GuardianBridgeUnsupportedOperationError(
        f"Unsupported operation for JSON adapter: {validated.operation.value}"
    )


def _parse_json_payload(stdout_text: str) -> Any | None:
    stripped = stdout_text.strip()
    if not stripped:
        return None
    return json.loads(stripped)


def _response_reason(
    payload: Any | None,
    *,
    fallback: str,
) -> str:
    if isinstance(payload, dict):
        reason = payload.get("reason")
        if isinstance(reason, str) and reason.strip():
            return reason.strip()
    return fallback


def run_codex_runner_json(
    request: GuardianBridgeRequest,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> GuardianBridgeResponse:
    validated = validate_bridge_request(request)
    command = build_codex_runner_command(validated)
    command_kind = validated.operation.value

    try:
        completed = subprocess.run(
            command,
            cwd=CODEX_RUNNER_ROOT,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
            shell=False,
        )
    except subprocess.TimeoutExpired as exc:
        stdout_text = exc.stdout if isinstance(exc.stdout, str) else ""
        return GuardianBridgeResponse(
            command_kind=command_kind,
            result=GuardianBridgeResult.FAIL,
            reason=f"Codex Runner preflight command timed out after {timeout_seconds} seconds.",
            stdout_text=stdout_text or None,
            json_payload=None,
            authority=default_authority(),
            boundary_label=BOUNDARY_LABEL,
            correlation_id=validated.correlation_id,
            adapter_version=ADAPTER_VERSION,
        )

    stdout_text = completed.stdout or ""
    payload: Any | None = None

    if completed.returncode == 0:
        try:
            payload = _parse_json_payload(stdout_text)
        except json.JSONDecodeError as exc:
            raise GuardianBridgeJsonError(
                "Codex Runner returned success but did not emit valid JSON."
            ) from exc
        return GuardianBridgeResponse(
            command_kind=command_kind,
            result=GuardianBridgeResult.PASS,
            reason=_response_reason(payload, fallback="Codex Runner preflight passed."),
            stdout_text=stdout_text,
            json_payload=payload,
            authority=default_authority(),
            boundary_label=BOUNDARY_LABEL,
            correlation_id=validated.correlation_id,
            adapter_version=ADAPTER_VERSION,
        )

    try:
        payload = _parse_json_payload(stdout_text)
    except json.JSONDecodeError:
        payload = None

    fallback_reason = (
        completed.stderr.strip()
        or stdout_text.strip()
        or f"Codex Runner preflight failed with exit code {completed.returncode}."
    )
    return GuardianBridgeResponse(
        command_kind=command_kind,
        result=GuardianBridgeResult.FAIL,
        reason=_response_reason(payload, fallback=fallback_reason),
        stdout_text=stdout_text,
        json_payload=payload,
        authority=default_authority(),
        boundary_label=BOUNDARY_LABEL,
        correlation_id=validated.correlation_id,
        adapter_version=ADAPTER_VERSION,
    )


__all__ = [
    "ADAPTER_VERSION",
    "CODEXRUN_BINARY",
    "DEFAULT_TIMEOUT_SECONDS",
    "GuardianBridgeAdapterError",
    "GuardianBridgeCommandError",
    "GuardianBridgeJsonError",
    "GuardianBridgeUnsupportedOperationError",
    "build_codex_runner_command",
    "run_codex_runner_json",
]
