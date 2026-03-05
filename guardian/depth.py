"""Depth resolution contract for chat completion APIs."""

from __future__ import annotations

from typing import Literal

DepthMode = Literal["light", "deep"]
DepthDowngradeReason = Literal[
    "no_project",
    "project_identity_depth_light",
    "policy_gate_rejected",
    "capability_missing",
    "server_forced",
    "unknown",
]
ProjectDepthState = Literal["missing", "known", "malformed"]
KnownRequestDepthToken = Literal["shallow", "normal", "deep", "diagnostic"]

KNOWN_REQUEST_DEPTH_TOKENS: frozenset[str] = frozenset(
    {"shallow", "normal", "deep", "diagnostic"}
)
KNOWN_PROJECT_DEPTH_TOKENS: frozenset[str] = frozenset({"light", "deep"})


def normalize_requested_depth_raw(value: str | None) -> str:
    """Normalize raw request depth from API payload."""
    return str(value or "deep").strip().lower()


def project_requested_depth_mode(requested_depth_raw: str) -> DepthMode:
    """
    Binary projection for API contract fields.

    Requested mode is "deep" iff raw request is exactly "deep", otherwise "light".
    """
    return "deep" if requested_depth_raw == "deep" else "light"


def normalize_project_identity_depth(value: str | None) -> str:
    """Normalize project identity depth for classification."""
    return str(value or "").strip().lower()


def classify_project_identity_depth(
    project_identity_depth_raw: str | None,
) -> ProjectDepthState:
    """
    Classify project identity depth according to API contract.

    - None => missing
    - deep/light => known
    - anything else => malformed
    """
    if project_identity_depth_raw is None:
        return "missing"
    normalized = normalize_project_identity_depth(project_identity_depth_raw)
    if normalized in KNOWN_PROJECT_DEPTH_TOKENS:
        return "known"
    return "malformed"


def resolve_depth(
    requested_depth_raw: DepthMode | str,
    *,
    thread_has_project: bool,
    project_depth_state: ProjectDepthState,
    project_identity_depth_norm: str,
    policy_allows_deep: bool,
) -> tuple[DepthMode, DepthDowngradeReason | None]:
    """
    Resolve API-facing effective depth and downgrade reason.

    `unknown` is emitted only for malformed requested/project-depth inputs.
    """
    requested = str(requested_depth_raw or "").strip().lower()
    if requested not in KNOWN_REQUEST_DEPTH_TOKENS:
        return "light", "unknown"
    if requested != "deep":
        return "light", None

    if not thread_has_project:
        return "light", "no_project"
    if project_depth_state == "malformed":
        return "light", "unknown"
    if project_depth_state == "missing":
        return "light", "project_identity_depth_light"
    if project_identity_depth_norm != "deep":
        return "light", "project_identity_depth_light"
    if not policy_allows_deep:
        return "light", "policy_gate_rejected"
    return "deep", None


__all__ = [
    "DepthDowngradeReason",
    "DepthMode",
    "KNOWN_REQUEST_DEPTH_TOKENS",
    "KnownRequestDepthToken",
    "ProjectDepthState",
    "classify_project_identity_depth",
    "normalize_project_identity_depth",
    "normalize_requested_depth_raw",
    "project_requested_depth_mode",
    "resolve_depth",
]
