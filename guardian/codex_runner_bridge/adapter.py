"""JSON-only backend adapter for the Guardian Codex Runner preflight bridge."""

from __future__ import annotations

import json
import os
import subprocess
from typing import Any, Mapping

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


class GuardianBridgeInvocationModeError(GuardianBridgeAdapterError):
    """Raised when the configured invocation mode is unsupported or invalid."""


class GuardianBridgeInvocationConfigError(GuardianBridgeAdapterError):
    """Raised when invocation config contains invalid tokens (e.g. whitespace)."""


# ---------------------------------------------------------------------------
# Invocation-mode resolver
# ---------------------------------------------------------------------------

ALLOWED_INVOCATION_MODES: tuple[str, ...] = ("binary", "module")
DEFAULT_INVOCATION_MODE: str = "binary"

CODEXRUN_INVOCATION_MODE_ENV = "CODEXRUN_INVOCATION_MODE"
CODEXRUN_BINARY_ENV = "CODEXRUN_BINARY"
CODEXRUN_PYTHON_BINARY_ENV = "CODEXRUN_PYTHON_BINARY"
CODEXRUN_MODULE_ENV = "CODEXRUN_MODULE"

def _clean_single_token(value: str, env_name: str) -> str:
    token = value.strip()
    if not token:
        raise GuardianBridgeInvocationConfigError(
            f"{env_name} must be non-empty."
        )
    if any(ch.isspace() for ch in token):
        raise GuardianBridgeInvocationConfigError(
            f"{env_name} must not contain whitespace."
        )
    return token


def resolve_codexrun_command_prefix(
    env: Mapping[str, str] | None = None,
) -> list[str]:
    """Return the command prefix argv list for the requested invocation mode.

    Environment keys read (via *env* or ``os.environ``):

    * ``CODEXRUN_INVOCATION_MODE`` – ``"binary"`` (default) or ``"module"``
    * ``CODEXRUN_BINARY`` – executable token for binary mode (default ``"codexrun"``)
    * ``CODEXRUN_PYTHON_BINARY`` – Python executable for module mode (default ``"python"``)
    * ``CODEXRUN_MODULE`` – module name for module mode (default ``"codex_runner"``)
    """
    resolved_env = os.environ if env is None else dict(env)

    mode_raw = resolved_env.get(
        CODEXRUN_INVOCATION_MODE_ENV, DEFAULT_INVOCATION_MODE
    )
    mode = mode_raw.strip().lower()
    if mode not in ALLOWED_INVOCATION_MODES:
        raise GuardianBridgeInvocationModeError(
            f"{CODEXRUN_INVOCATION_MODE_ENV} must be one of: "
            f"{', '.join(ALLOWED_INVOCATION_MODES)}. Got: {mode_raw!r}"
        )

    if mode == "binary":
        binary = resolved_env.get(CODEXRUN_BINARY_ENV, CODEXRUN_BINARY)
        return [_clean_single_token(binary, CODEXRUN_BINARY_ENV)]

    # module mode
    py_binary = resolved_env.get(CODEXRUN_PYTHON_BINARY_ENV, "python")
    module_name = resolved_env.get(CODEXRUN_MODULE_ENV, "codex_runner")
    return [
        _clean_single_token(py_binary, CODEXRUN_PYTHON_BINARY_ENV),
        "-m",
        _clean_single_token(module_name, CODEXRUN_MODULE_ENV),
    ]


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

    prefix = resolve_codexrun_command_prefix()

    if validated.operation == GuardianBridgeOperation.VALIDATE_PLAN_PACK:
        return [
            *prefix,
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
            *prefix,
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
    "ALLOWED_INVOCATION_MODES",
    "CODEXRUN_BINARY",
    "CODEXRUN_BINARY_ENV",
    "CODEXRUN_INVOCATION_MODE_ENV",
    "CODEXRUN_MODULE_ENV",
    "CODEXRUN_PYTHON_BINARY_ENV",
    "DEFAULT_INVOCATION_MODE",
    "DEFAULT_TIMEOUT_SECONDS",
    "GuardianBridgeAdapterError",
    "GuardianBridgeCommandError",
    "GuardianBridgeInvocationConfigError",
    "GuardianBridgeInvocationModeError",
    "GuardianBridgeJsonError",
    "GuardianBridgeUnsupportedOperationError",
    "build_codex_runner_command",
    "resolve_codexrun_command_prefix",
    "run_codex_runner_json",
]
