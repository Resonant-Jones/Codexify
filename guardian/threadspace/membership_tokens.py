"""Bounded canonical token domains for ThreadSpace node membership."""

from __future__ import annotations

from enum import Enum
from typing import Final


class NodeStatus(str, Enum):
    """Lifecycle values for a durable ThreadSpace Node record."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"


class NodeMembershipRole(str, Enum):
    """Positive authority roles for one ThreadSpace Node."""

    NODE_OWNER = "node_owner"
    NODE_OPERATOR = "node_operator"
    NODE_ADMIN = "node_admin"
    MEMBER = "member"
    GUEST = "guest"


class MembershipLifecycleState(str, Enum):
    """Lifecycle values for a ThreadSpace membership grant."""

    INVITED = "invited"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REVOKED = "revoked"
    EXPIRED = "expired"


class InvitationState(str, Enum):
    """Lifecycle values for a ThreadSpace membership invitation."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    REVOKED = "revoked"
    EXPIRED = "expired"


NODE_STATUSES: Final[frozenset[str]] = frozenset(
    status.value for status in NodeStatus
)
NODE_MEMBERSHIP_ROLES: Final[frozenset[str]] = frozenset(
    role.value for role in NodeMembershipRole
)
MEMBERSHIP_LIFECYCLE_STATES: Final[frozenset[str]] = frozenset(
    state.value for state in MembershipLifecycleState
)
INVITATION_STATES: Final[frozenset[str]] = frozenset(
    state.value for state in InvitationState
)

# Descriptive aliases keep the three contract domains easy to discover without
# introducing a general-purpose cross-subsystem token registry.
THREADSPACE_NODE_STATUSES: Final[frozenset[str]] = NODE_STATUSES
THREADSPACE_NODE_MEMBERSHIP_ROLES: Final[frozenset[str]] = NODE_MEMBERSHIP_ROLES
THREADSPACE_MEMBERSHIP_LIFECYCLE_STATES: Final[frozenset[str]] = (
    MEMBERSHIP_LIFECYCLE_STATES
)
THREADSPACE_INVITATION_STATES: Final[frozenset[str]] = INVITATION_STATES


def _validate_token(value: str | Enum, allowed: frozenset[str], domain: str) -> str:
    normalized = value.value if isinstance(value, Enum) else value
    if not isinstance(normalized, str) or normalized not in allowed:
        raise ValueError(f"invalid {domain}: {value!r}")
    return normalized


def validate_node_status(value: str | NodeStatus) -> str:
    return _validate_token(value, NODE_STATUSES, "ThreadSpace node status")


def validate_node_membership_role(value: str | NodeMembershipRole) -> str:
    return _validate_token(
        value, NODE_MEMBERSHIP_ROLES, "ThreadSpace node membership role"
    )


def validate_membership_lifecycle_state(
    value: str | MembershipLifecycleState,
) -> str:
    return _validate_token(
        value,
        MEMBERSHIP_LIFECYCLE_STATES,
        "ThreadSpace membership lifecycle state",
    )


def validate_invitation_state(value: str | InvitationState) -> str:
    return _validate_token(value, INVITATION_STATES, "ThreadSpace invitation state")


__all__ = [
    "InvitationState",
    "MembershipLifecycleState",
    "NodeMembershipRole",
    "NodeStatus",
    "INVITATION_STATES",
    "MEMBERSHIP_LIFECYCLE_STATES",
    "NODE_MEMBERSHIP_ROLES",
    "NODE_STATUSES",
    "THREADSPACE_INVITATION_STATES",
    "THREADSPACE_MEMBERSHIP_LIFECYCLE_STATES",
    "THREADSPACE_NODE_MEMBERSHIP_ROLES",
    "THREADSPACE_NODE_STATUSES",
    "validate_invitation_state",
    "validate_membership_lifecycle_state",
    "validate_node_membership_role",
    "validate_node_status",
]
