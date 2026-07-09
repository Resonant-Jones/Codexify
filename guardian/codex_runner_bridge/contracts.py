"""Typed contracts for the future Guardian Codex Runner preflight bridge.

This module is intentionally dependency-light and deterministic. It defines the
typed request/response vocabulary and path-validation helpers for a future
Codexify -> Codex Runner bridge without invoking commands, routes, workers, or
subprocesses.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields, replace
from enum import StrEnum
from pathlib import Path
from typing import Any

BOUNDARY_LABEL = (
    "PREFLIGHT ONLY\n"
    "NO PI LOOP INVOCATION\n"
    "NO SOURCE MUTATION\n"
    "NO CODEXIFY INGESTION"
)

CODEX_RUNNER_ROOT = Path("/Volumes/Dev_SSD/Codex-Runner")
CODEXIFY_ROOT = Path("/Volumes/Dev_SSD/Codexify-main")
ARCHIVED_CODEXIFY_CORE_ROOT = Path(
    "/Volumes/Dev_SSD/ResonantConstructs/Codexify-Core"
)
ADAPTER_VERSION = "v0-contract-only"

_CODEX_RUNNER_ROOT_RESOLVED = CODEX_RUNNER_ROOT.resolve(strict=False)
_CODEXIFY_ROOT_RESOLVED = CODEXIFY_ROOT.resolve(strict=False)
_ARCHIVED_CODEXIFY_CORE_ROOT_RESOLVED = ARCHIVED_CODEXIFY_CORE_ROOT.resolve(
    strict=False
)


class GuardianBridgePathError(ValueError):
    """Raised when a proposed bridge path violates boundary rules."""


class GuardianBridgeOperation(StrEnum):
    VALIDATE_PLAN_PACK = "guardian.validate_plan_pack"
    WRITE_VALIDATION_RECEIPT = "guardian.write_validation_receipt"
    ORCHESTRATE_DRY_RUN_PREFLIGHT = "guardian.orchestrate_dry_run_preflight"
    WRITE_ORCHESTRATION_EVIDENCE = "guardian.write_orchestration_evidence"
    LIST_EVIDENCE_FOR_PLAN_PACK = "guardian.list_evidence_for_plan_pack"


class GuardianBridgeResponseMode(StrEnum):
    TEXT = "text"
    JSON = "json"


class GuardianBridgeResult(StrEnum):
    PASS = "pass"
    FAIL = "fail"


ALLOWED_GUARDIAN_BRIDGE_OPERATIONS: tuple[GuardianBridgeOperation, ...] = tuple(
    GuardianBridgeOperation
)


def _clean_required_text(value: object, field_name: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"{field_name} must be non-empty.")
    return text


def _path_inside(child: Path, root: Path) -> bool:
    return child == root or root in child.parents


def _normalize_str_enum(
    value: object,
    enum_type: type[StrEnum],
    *,
    field_name: str,
) -> StrEnum:
    if isinstance(value, enum_type):
        return value
    try:
        return enum_type(_clean_required_text(value, field_name))
    except ValueError as exc:
        allowed = ", ".join(member.value for member in enum_type)
        raise ValueError(f"{field_name} must be one of: {allowed}.") from exc


@dataclass(frozen=True, slots=True)
class GuardianBridgeAuthority:
    guardian_operational: bool = False
    plan_execution_allowed: bool = False
    pi_loop_invocation_allowed: bool = False
    codexify_ingestion_allowed: bool = False
    durable_mutation_allowed: bool = False
    provider_execution_allowed: bool = False
    patch_application_allowed: bool = False
    dispatch_allowed: bool = False
    merge_allowed: bool = False

    def __post_init__(self) -> None:
        for authority_field in fields(self):
            if getattr(self, authority_field.name) is not False:
                raise ValueError(
                    f"{authority_field.name} must remain false for bridge authority."
                )


def default_authority() -> GuardianBridgeAuthority:
    return GuardianBridgeAuthority()


@dataclass(frozen=True, slots=True)
class GuardianBridgeRequest:
    operation: GuardianBridgeOperation | str
    plan_pack_path: Path | str
    requested_by: str
    correlation_id: str
    validation_receipt_path: Path | str | None = None
    write_receipt: bool = False
    write_orchestration_log: bool = False
    write_orchestration_receipt: bool = False
    response_mode: GuardianBridgeResponseMode | str = GuardianBridgeResponseMode.JSON


@dataclass(frozen=True, slots=True)
class GuardianBridgeEvidencePaths:
    validation_receipt_path: Path | None = None
    orchestration_log_path: Path | None = None
    orchestration_receipt_path: Path | None = None


@dataclass(frozen=True, slots=True)
class GuardianBridgeResponse:
    command_kind: str
    result: GuardianBridgeResult
    reason: str
    correlation_id: str
    stdout_text: str | None = None
    json_payload: Any | None = None
    evidence_paths: GuardianBridgeEvidencePaths = field(
        default_factory=GuardianBridgeEvidencePaths
    )
    authority: GuardianBridgeAuthority = field(default_factory=default_authority)
    boundary_label: str = BOUNDARY_LABEL
    adapter_version: str = ADAPTER_VERSION


def normalize_bridge_path(path: str | Path) -> Path:
    try:
        if isinstance(path, Path):
            candidate = path.expanduser()
        else:
            candidate = Path(_clean_required_text(path, "path")).expanduser()
        return candidate.resolve(strict=False)
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        raise GuardianBridgePathError(f"Invalid bridge path: {path!r}") from exc


def validate_codex_runner_path(path: str | Path) -> Path:
    normalized = normalize_bridge_path(path)
    if _path_inside(normalized, _CODEXIFY_ROOT_RESOLVED):
        raise GuardianBridgePathError(
            f"Path must not resolve inside Codexify root: {normalized}"
        )
    if _path_inside(normalized, _ARCHIVED_CODEXIFY_CORE_ROOT_RESOLVED):
        raise GuardianBridgePathError(
            f"Path must not resolve inside archived Codexify-Core root: {normalized}"
        )
    if not _path_inside(normalized, _CODEX_RUNNER_ROOT_RESOLVED):
        raise GuardianBridgePathError(
            f"Path must resolve inside Codex Runner root: {normalized}"
        )
    return normalized


def validate_plan_pack_path(path: str | Path) -> Path:
    return validate_codex_runner_path(path)


def validate_validation_receipt_path(path: str | Path | None) -> Path | None:
    if path is None:
        return None
    return validate_codex_runner_path(path)


def validate_operation(
    operation: str | GuardianBridgeOperation,
) -> GuardianBridgeOperation:
    if isinstance(operation, GuardianBridgeOperation):
        return operation
    text = _clean_required_text(operation, "operation")
    if any(ch.isspace() for ch in text):
        raise ValueError("operation must not contain whitespace.")
    if any(ch in text for ch in (";", "|", "&", ">", "<", "`", "$")):
        raise ValueError("operation must be a typed bridge operation, not shell input.")
    try:
        return GuardianBridgeOperation(text)
    except ValueError as exc:
        allowed = ", ".join(member.value for member in GuardianBridgeOperation)
        raise ValueError(f"operation must be one of: {allowed}.") from exc


def validate_bridge_request(
    request: GuardianBridgeRequest,
) -> GuardianBridgeRequest:
    if not isinstance(request, GuardianBridgeRequest):
        raise TypeError("request must be a GuardianBridgeRequest.")

    validated_operation = validate_operation(request.operation)
    validated_plan_pack_path = validate_plan_pack_path(request.plan_pack_path)
    validated_validation_receipt_path = validate_validation_receipt_path(
        request.validation_receipt_path
    )
    validated_response_mode = _normalize_str_enum(
        request.response_mode,
        GuardianBridgeResponseMode,
        field_name="response_mode",
    )
    validated_requested_by = _clean_required_text(request.requested_by, "requested_by")
    validated_correlation_id = _clean_required_text(
        request.correlation_id, "correlation_id"
    )

    return replace(
        request,
        operation=validated_operation,
        plan_pack_path=validated_plan_pack_path,
        validation_receipt_path=validated_validation_receipt_path,
        response_mode=validated_response_mode,
        requested_by=validated_requested_by,
        correlation_id=validated_correlation_id,
    )


__all__ = [
    "ADAPTER_VERSION",
    "ALLOWED_GUARDIAN_BRIDGE_OPERATIONS",
    "ARCHIVED_CODEXIFY_CORE_ROOT",
    "BOUNDARY_LABEL",
    "CODEXIFY_ROOT",
    "CODEX_RUNNER_ROOT",
    "GuardianBridgeAuthority",
    "GuardianBridgeEvidencePaths",
    "GuardianBridgeOperation",
    "GuardianBridgePathError",
    "GuardianBridgeRequest",
    "GuardianBridgeResponse",
    "GuardianBridgeResponseMode",
    "GuardianBridgeResult",
    "default_authority",
    "normalize_bridge_path",
    "validate_bridge_request",
    "validate_codex_runner_path",
    "validate_operation",
    "validate_plan_pack_path",
    "validate_validation_receipt_path",
]
