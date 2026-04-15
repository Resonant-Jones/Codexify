"""Canonical capability-grant tokens for control-plane contracts."""

from __future__ import annotations

from enum import Enum


class CapabilityGrantScope(str, Enum):
    """Bounded grant scopes supported by the foundation schema."""

    ACCOUNT = "account"


class CapabilityGrantKind(str, Enum):
    """Bounded grant kinds supported by the foundation schema."""

    PERMANENT = "permanent"
    TIME_BOXED = "time_boxed"
    PROMO = "promo"
    TRIAL = "trial"


class CapabilityGrantStatus(str, Enum):
    """Bounded grant statuses supported by the foundation schema."""

    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    SUSPENDED = "suspended"


class CapabilityFamily(str, Enum):
    """Canonical capability families used by tier definitions."""

    CORE = "core"
    CHAT = "chat"
    DOCUMENT = "document"
    MEDIA = "media"
    PROJECT = "project"
    PERSONA_PROFILE = "persona_profile"
    PLUGIN = "plugin"
    RELEASE_FAMILY = "release_family"
    QUOTA = "quota"


CAPABILITY_GRANT_SCOPES: frozenset[str] = frozenset(
    scope.value for scope in CapabilityGrantScope
)
CAPABILITY_GRANT_KINDS: frozenset[str] = frozenset(
    kind.value for kind in CapabilityGrantKind
)
CAPABILITY_GRANT_STATUSES: frozenset[str] = frozenset(
    status.value for status in CapabilityGrantStatus
)
CAPABILITY_FAMILIES: frozenset[str] = frozenset(
    family.value for family in CapabilityFamily
)

CANONICAL_CAPABILITY_IDENTIFIERS: frozenset[str] = CAPABILITY_FAMILIES


__all__ = [
    "CapabilityGrantScope",
    "CapabilityGrantKind",
    "CapabilityGrantStatus",
    "CapabilityFamily",
    "CAPABILITY_GRANT_SCOPES",
    "CAPABILITY_GRANT_KINDS",
    "CAPABILITY_GRANT_STATUSES",
    "CAPABILITY_FAMILIES",
    "CANONICAL_CAPABILITY_IDENTIFIERS",
]
