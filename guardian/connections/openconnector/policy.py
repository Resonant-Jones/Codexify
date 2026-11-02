"""Server-controlled, reviewed read-only action allowlist.

This module is the **only** source of executable action authority for the
OpenConnector adapter. The allowlist is a reviewed, server-side artifact.

It is never derived from:

* the upstream custodian catalog,
* a model response,
* a user request,
* provider naming conventions.

An entry exists here because a human reviewed the action and confirmed it
does not mutate provider state. Adding an entry is an explicit, reviewed code
change — never a runtime configuration and never a discovery result.

Scope of this slice: exactly one reviewed action. It is a **no-auth provider
action**, so it is not evidence that the custodian's connection grants isolate
tenants; grant isolation is proven separately, with credential-bearing
synthetic connections, in the adapter tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True)
class ApprovedAction:
    """One reviewed, read-only action.

    Attributes:
        action_id: The custodian action identifier.
        provider: The provider identity the action belongs to.
        description: Human-facing description of the action.
        requires_connection: Whether execution must name an explicit
            account-owned connection. Every action does.
        credential_bearing: Whether the action spends a provider credential.
            A no-auth action is **not** evidence of grant isolation.
    """

    action_id: str
    provider: str
    description: str
    requires_connection: bool = True
    credential_bearing: bool = False


_APPROVED_ACTIONS: Mapping[str, ApprovedAction] = MappingProxyType(
    {
        "hackernews.get_top_stories": ApprovedAction(
            action_id="hackernews.get_top_stories",
            provider="hackernews",
            description="Hacker News top stories (no-auth provider action).",
            requires_connection=True,
            credential_bearing=False,
        ),
    }
)

#: The production allowlist. Read-only, reviewed, and deliberately small.
APPROVED_ACTIONS: Mapping[str, ApprovedAction] = _APPROVED_ACTIONS

#: The production allowlist as a flat identifier set.
REVIEWED_READ_ONLY_ACTIONS: frozenset[str] = frozenset(_APPROVED_ACTIONS)


def resolve_allowlist(
    allowlist: Mapping[str, ApprovedAction] | None,
) -> Mapping[str, ApprovedAction]:
    """Return the effective allowlist.

    ``None`` means the production allowlist. A supplied mapping is used
    verbatim; injecting one is a **test-harness** affordance for
    credential-bearing synthetic actions and must never widen the production
    allowlist.
    """
    return _APPROVED_ACTIONS if allowlist is None else allowlist


def is_approved_action(
    action_id: str,
    allowlist: Mapping[str, ApprovedAction] | None = None,
) -> bool:
    """Whether an action id is present in the effective allowlist."""
    candidate = str(action_id or "").strip()
    if not candidate:
        return False
    return candidate in resolve_allowlist(allowlist)


def get_approved_action(
    action_id: str,
    allowlist: Mapping[str, ApprovedAction] | None = None,
) -> ApprovedAction | None:
    """Return the approved action metadata, or ``None``."""
    candidate = str(action_id or "").strip()
    if not candidate:
        return None
    return resolve_allowlist(allowlist).get(candidate)


def approved_actions_for_provider(
    provider: str,
    allowlist: Mapping[str, ApprovedAction] | None = None,
) -> tuple[ApprovedAction, ...]:
    """Return the approved actions for one provider, in stable order."""
    wanted = str(provider or "").strip()
    if not wanted:
        return ()
    return tuple(
        action
        for _, action in sorted(resolve_allowlist(allowlist).items())
        if action.provider == wanted
    )


__all__ = [
    "APPROVED_ACTIONS",
    "REVIEWED_READ_ONLY_ACTIONS",
    "ApprovedAction",
    "approved_actions_for_provider",
    "get_approved_action",
    "is_approved_action",
    "resolve_allowlist",
]
