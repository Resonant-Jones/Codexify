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

Two execution modes exist, and a reviewed action declares exactly one of them.

**Explicit selection** is the default and the safe one. The crossing names the
custodian-side connection in the upstream selector header, and the action spends
a provider credential held by the custodian. The selector is never omitted for
such an action.

**No-auth selection** is declared per reviewed action, for a provider whose
endpoint needs no credential. The custodian's connection for such a provider is
*virtual*: it holds no credential material, it has no stored UUID, and upstream
refuses an explicit selector aimed at it. The crossing therefore omits the
selector for these actions and nothing else.

This is **not** a generic "connection optional" fallback. The mode is a property
of the reviewed allowlist entry, it can only be changed by a reviewed code
change, and no request, argument, binding, or runtime flag can select it. An
action that does not declare the no-auth mode keeps explicit selection, even if
it happens to spend no credential.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Mapping


class ConnectionSelection(str, Enum):
    """How the crossing names the custodian-side connection for an action.

    Attributes:
        EXPLICIT: The custodian-side connection is named in the upstream
            selector header. This is the default for every action, and it is
            the only mode a credential-bearing action may use.
        NO_AUTH: The custodian-side connection is the custodian's *virtual*
            no-auth connection for the provider. It holds no credential, so
            there is nothing to select, and upstream refuses an explicit
            selector aimed at it. The crossing omits the selector.
    """

    EXPLICIT = "explicit"
    NO_AUTH = "no_auth"


@dataclass(frozen=True)
class ApprovedAction:
    """One reviewed, read-only action.

    Attributes:
        action_id: The custodian action identifier.
        provider: The provider identity the action belongs to.
        description: Human-facing description of the action.
        connection_selection: How this action's custodian-side connection is
            named. Defaults to explicit selection, so an action that does not
            declare the no-auth mode never omits the selector.
        credential_bearing: Whether the action spends a provider credential.
            A no-auth action is **not** evidence of grant isolation.
    """

    action_id: str
    provider: str
    description: str
    connection_selection: ConnectionSelection = ConnectionSelection.EXPLICIT
    credential_bearing: bool = False


_APPROVED_ACTIONS: Mapping[str, ApprovedAction] = MappingProxyType(
    {
        "hackernews.get_top_stories": ApprovedAction(
            action_id="hackernews.get_top_stories",
            provider="hackernews",
            description="Hacker News top stories (no-auth provider action).",
            connection_selection=ConnectionSelection.NO_AUTH,
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
    "ConnectionSelection",
    "approved_actions_for_provider",
    "get_approved_action",
    "is_approved_action",
    "resolve_allowlist",
]
