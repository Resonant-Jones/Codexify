"""Bounded canonical token domains for social identity and direct messaging.

These tokens are protocol contract-bearing values for the node-addressed
profile identity and direct private-messaging boundary governed by
``docs/architecture/adr/079-node-addressed-profile-identity-and-direct-messaging-boundary.md``
and ``docs/architecture/direct-messaging-contract.md``.

Scope
-----

* ``USERNAME_STATES``      — lifecycle of a deliberate social username.
* ``DM_CONVERSATION_KINDS`` — direct-message conversation kinds.
* ``DM_CONTENT_TYPES``      — canonical message content types.
* ``DM_PROTOCOL_VERSION``   — transport-neutral envelope protocol version.

Explicitly not here
-------------------

* ``user_id`` / authentication identity — private account ownership state.
* presentation preferences (accent color, timezone) — see
  ``guardian.user_profile_tokens``.
* ThreadSpace node lifecycle states — see
  ``guardian.threadspace.membership_tokens``.
* Guardian chat, queue, event, error, or execution state — see
  ``guardian.protocol_tokens``.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Final

# ── Username constants ────────────────────────────────────────────────────

USERNAME_MIN_LENGTH: Final[int] = 3
USERNAME_MAX_LENGTH: Final[int] = 32

# Conservative V1 grammar: lowercase ASCII letters, digits, underscore, and
# hyphen; must start and end with a letter or digit.  The normalized value is
# always stored lowercase, so the stored username *is* the case-insensitive
# canonical form.  No Unicode normalization is attempted in V1.
_USERNAME_GRAMMAR: Final[str] = (
    f"^[a-z0-9][a-z0-9_-]{{{USERNAME_MIN_LENGTH - 2},{USERNAME_MAX_LENGTH - 2}}}[a-z0-9]$"
)
USERNAME_PATTERN: Final[re.Pattern[str]] = re.compile(_USERNAME_GRAMMAR)

# Names reserved for system surfaces and future mention aliases.  A human
# social username must never shadow them.
RESERVED_USERNAMES: Final[frozenset[str]] = frozenset(
    [
        "admin",
        "all",
        "anonymous",
        "codexify",
        "everyone",
        "guardian",
        "help",
        "here",
        "me",
        "mod",
        "moderator",
        "noreply",
        "root",
        "support",
        "system",
        "unknown",
        "you",
    ]
)


class UsernameState(str, Enum):
    """Lifecycle values for a deliberate social username selection."""

    UNSET = "unset"
    ACTIVE = "active"


class DirectMessageConversationKind(str, Enum):
    """Canonical kinds for direct-message conversations."""

    DIRECT = "direct"


class DirectMessageContentType(str, Enum):
    """Canonical content types for direct messages."""

    TEXT_PLAIN = "text/plain"


USERNAME_STATES: Final[frozenset[str]] = frozenset(
    state.value for state in UsernameState
)
DM_CONVERSATION_KINDS: Final[frozenset[str]] = frozenset(
    kind.value for kind in DirectMessageConversationKind
)
DM_CONTENT_TYPES: Final[frozenset[str]] = frozenset(
    content_type.value for content_type in DirectMessageContentType
)

# Transport-neutral envelope protocol version.
DM_PROTOCOL_VERSION: Final[str] = "1.0"

# Descriptive aliases keep the contract domains discoverable without
# introducing a general-purpose cross-subsystem token registry.
DIRECT_MESSAGE_CONVERSATION_KINDS: Final[frozenset[str]] = DM_CONVERSATION_KINDS
DIRECT_MESSAGE_CONTENT_TYPES: Final[frozenset[str]] = DM_CONTENT_TYPES


def _validate_token(value: str | Enum, allowed: frozenset[str], domain: str) -> str:
    normalized = value.value if isinstance(value, Enum) else value
    if not isinstance(normalized, str) or normalized not in allowed:
        raise ValueError(f"invalid {domain}: {value!r}")
    return normalized


def validate_username_state(value: str | UsernameState) -> str:
    return _validate_token(value, USERNAME_STATES, "username state")


def validate_dm_conversation_kind(
    value: str | DirectMessageConversationKind,
) -> str:
    return _validate_token(
        value, DM_CONVERSATION_KINDS, "direct-message conversation kind"
    )


def validate_dm_content_type(value: str | DirectMessageContentType) -> str:
    return _validate_token(value, DM_CONTENT_TYPES, "direct-message content type")


def normalize_username(raw: str) -> str:
    """Return the canonical lowercase social username for *raw*.

    Raises ``ValueError`` with a machine-readable first token when the
    value cannot be a deliberate social username.  The username is a
    discovery alias only — it is never durable authorization authority.
    """
    if not isinstance(raw, str):
        raise ValueError("username_required: username must be a string")
    candidate = raw.strip().lower()
    if not candidate:
        raise ValueError("username_required: username must not be empty")
    if len(candidate) < USERNAME_MIN_LENGTH or len(candidate) > USERNAME_MAX_LENGTH:
        raise ValueError(
            f"username_length: username must be {USERNAME_MIN_LENGTH}-"
            f"{USERNAME_MAX_LENGTH} characters"
        )
    if not USERNAME_PATTERN.fullmatch(candidate):
        raise ValueError(
            "username_grammar: username must contain only lowercase letters, "
            "digits, underscores, and hyphens, and must start and end with "
            "a letter or digit"
        )
    if candidate in RESERVED_USERNAMES:
        raise ValueError("username_reserved: username is reserved for system use")
    return candidate


__all__ = [
    "DIRECT_MESSAGE_CONTENT_TYPES",
    "DIRECT_MESSAGE_CONVERSATION_KINDS",
    "DM_CONVERSATION_KINDS",
    "DM_CONTENT_TYPES",
    "DM_PROTOCOL_VERSION",
    "DirectMessageContentType",
    "DirectMessageConversationKind",
    "RESERVED_USERNAMES",
    "USERNAME_MAX_LENGTH",
    "USERNAME_MIN_LENGTH",
    "USERNAME_PATTERN",
    "USERNAME_STATES",
    "UsernameState",
    "normalize_username",
    "validate_dm_content_type",
    "validate_dm_conversation_kind",
    "validate_username_state",
]
