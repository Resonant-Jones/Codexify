"""Canonical tokens for extension proposal persistence."""

from __future__ import annotations

from enum import Enum


class ExtensionTargetSurface(str, Enum):
    """Bounded target surfaces for self-extending proposals."""

    COMMAND_BUS = "command_bus"
    WORKFLOW_BUILDER = "workflow_builder"
    RETRIEVAL_ROUTER = "retrieval_router"
    PERSONA_STUDIO = "persona_studio"


class ExtensionProposalScope(str, Enum):
    """Canonical scope bindings for extension proposals."""

    PROJECT = "project_scoped"
    PROFILE = "profile_scoped"
    ACCOUNT = "account_scoped"


class ExtensionProposalStatus(str, Enum):
    """Canonical proposal lifecycle statuses."""

    DRAFT = "draft"
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    ARCHIVED = "archived"


EXTENSION_TARGET_SURFACES: frozenset[str] = frozenset(
    surface.value for surface in ExtensionTargetSurface
)
EXTENSION_PROPOSAL_SCOPES: frozenset[str] = frozenset(
    scope.value for scope in ExtensionProposalScope
)
EXTENSION_PROPOSAL_STATUSES: frozenset[str] = frozenset(
    status.value for status in ExtensionProposalStatus
)


class ExtensionTokenError(ValueError):
    """Raised when a caller supplies an invalid extension token."""


def _normalize_token(
    value: str | None, *, allowed: frozenset[str], kind: str
) -> str:
    token = str(value or "").strip()
    if token not in allowed:
        raise ExtensionTokenError(f"Invalid {kind}: {value!r}")
    return token


def normalize_extension_target_surface(value: str | None) -> str:
    return _normalize_token(
        value, allowed=EXTENSION_TARGET_SURFACES, kind="target_surface"
    )


def normalize_extension_proposal_scope(value: str | None) -> str:
    return _normalize_token(
        value, allowed=EXTENSION_PROPOSAL_SCOPES, kind="proposal_scope"
    )


def normalize_extension_proposal_status(value: str | None) -> str:
    return _normalize_token(
        value, allowed=EXTENSION_PROPOSAL_STATUSES, kind="proposal_status"
    )


__all__ = [
    "ExtensionTargetSurface",
    "ExtensionProposalScope",
    "ExtensionProposalStatus",
    "ExtensionTokenError",
    "EXTENSION_TARGET_SURFACES",
    "EXTENSION_PROPOSAL_SCOPES",
    "EXTENSION_PROPOSAL_STATUSES",
    "normalize_extension_target_surface",
    "normalize_extension_proposal_scope",
    "normalize_extension_proposal_status",
]
