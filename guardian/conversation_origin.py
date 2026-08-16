"""Canonical conversation-origin registry.

This module is the single source of truth for the bounded set of values that
``chat_threads.origin_system`` may carry. It enforces the contract described in
``docs/architecture/account-export-restore-contract.md``:

- Every canonical conversation has exactly one immutable ``origin_system``.
- ``origin_system`` answers "Where was this conversation originally created?".
  It does NOT answer which provider/model later executes completions inside it.
- Canonical values are exactly: ``codexify``, ``openai``, ``anthropic``.
- Legacy product names (``chatgpt``, ``claude``, ``gpt``, ``open_ai``,
  ``anthropic_claude``, ``native``) are not canonical origin values and are
  recognized only at migration/import compatibility boundaries.

The module is import-only safe (no side effects) so it can be loaded from any
layer without database or runtime dependencies.
"""

from __future__ import annotations

from enum import Enum
from typing import Final


class ConversationOriginSystem(str, Enum):
    """Canonical conversation-origin values.

    The bounded registry is intentionally small. New values may only be added
    by extending this enum; free-form strings must never reach the persistence
    seam. See ``tests/db/test_chat_thread_origin_system.py`` for the contract
    test that locks these values in.
    """

    CODEXIFY = "codexify"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


# Frozen set exported for membership checks (e.g. validation in the chat route
# filter parameter). Both this frozenset and the enum must agree.
CANONICAL_ORIGIN_SYSTEMS: Final[frozenset[str]] = frozenset(
    member.value for member in ConversationOriginSystem
)

# The native Codexify default is what ``chat_threads.origin_system`` MUST take
# on rows created by the canonical native-creation seam (the chat-thread route
# in ``guardian/routes/chat.py``). It must not be derived from the currently
# selected inference provider.
DEFAULT_ORIGIN_SYSTEM: Final[str] = ConversationOriginSystem.CODEXIFY.value


# ---------------------------------------------------------------------------
# Legacy alias normalization
# ---------------------------------------------------------------------------

# Map of legacy product-name tokens (the values actually present in the
# existing ``chat_threads.metadata->>'import_source'`` JSONB column, and
# historical ChatGPT / Claude export product names) onto the canonical
# bounded registry.
_LEGACY_IMPORT_SOURCE_ALIASES: Final[dict[str, str]] = {
    "chatgpt": ConversationOriginSystem.OPENAI.value,
    "openai": ConversationOriginSystem.OPENAI.value,
    "claude": ConversationOriginSystem.ANTHROPIC.value,
    "anthropic": ConversationOriginSystem.ANTHROPIC.value,
}


def normalize_legacy_import_source(value: str | None) -> str | None:
    """Return the canonical origin for a legacy ``import_source`` token.

    This is the migration/import-compatibility seam only. New code MUST NOT
    invent origin tokens here; unknown external systems must fail closed at
    the importer boundary rather than silently being mapped onto a canonical
    value.
    """

    if value is None:
        return None
    cleaned = str(value).strip().lower()
    if not cleaned:
        return None
    return _LEGACY_IMPORT_SOURCE_ALIASES.get(cleaned)


def is_canonical_origin_system(value: str | None) -> bool:
    """Return True iff ``value`` is exactly one of the bounded registry tokens."""

    if value is None:
        return False
    return str(value).strip().lower() in CANONICAL_ORIGIN_SYSTEMS


def resolve_canonical_origin(value: str | None) -> str:
    """Validate and return the canonical origin token, raising on unknown.

    Used by the chat-route filter parameter and by the persistence validators
    so unsupported canonical values cannot be stored or filtered accidentally.
    """

    candidate = str(value or "").strip().lower()
    if candidate not in CANONICAL_ORIGIN_SYSTEMS:
        raise ValueError(
            f"Unsupported origin_system={value!r}; "
            f"canonical values are {sorted(CANONICAL_ORIGIN_SYSTEMS)}"
        )
    return candidate