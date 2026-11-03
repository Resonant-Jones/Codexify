"""Guardian-owned account-to-custodian binding contracts.

OpenConnector is a **delegated external credential custodian**: it holds
provider credential material and it executes provider actions. It holds no
Codexify account authority and it grants none. Authority for an
account-scoped execution lives in a Guardian-owned binding — the record that
names the invoking account, the custodian, the provider, the custodian-side
connection, and the scoped runtime-token reference.

See the ADR-071 and ADR-094 amendments accepted 2026-11-02 (clauses B1-B4)
and the integration plan §4.3.

This module defines the typed interface only. The durable schema and the
binding lifecycle belong to Gate C. This slice ships **no** production
registry and **no** credential database, so an adapter without a configured
authoritative resolver fails closed.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol, runtime_checkable


class BindingState(str, Enum):
    """Authorization state of one Guardian-owned binding."""

    AUTHORIZED = "authorized"
    REVOKED = "revoked"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class AccountBinding:
    """One Guardian-owned account-to-connection authorization binding.

    The custodian's own records — its credential row, its connection row, its
    discovery result — are **delegated custody**. They are not represented
    here as authority, and nothing in this record is inferred from them.

    Attributes:
        guardian_account_id: The Codexify account that owns this binding.
            Ownership is canonical in Guardian; the custodian never owns it.
        custodian_id: The external custodian instance holding the credential.
        provider: The provider identity this binding authorizes.
        connection_id: The custodian-side connection identity. For a
            credential-bearing connection this is the custodian's connection
            UUID; for a no-auth provider it is the custodian's *virtual*
            no-auth connection identity, which has no stored UUID. Either way
            it is the identity the scoped grant covers, it is never defaulted,
            and it is never empty.
        connection_alias: Optional human-facing alias, where the custodian
            exposes one. Never used for selection by this adapter.
        runtime_token_ref: Reference to the account-scoped persistent runtime
            token. This is a *reference*, not token material; material is
            fetched through the resolver and stays inside the transport.
        allowed_connections: The connection set this binding's scoped token
            is granted. An **empty** grant means the custodian would treat the
            token as unrestricted, so it is never acceptable and never means
            "everything".
        state: Current authorization state. Only ``AUTHORIZED`` permits
            execution.
    """

    guardian_account_id: str
    custodian_id: str
    provider: str
    connection_id: str
    connection_alias: str | None = None
    runtime_token_ref: str | None = None
    allowed_connections: tuple[str, ...] = ()
    state: BindingState = BindingState.AUTHORIZED

    def is_authorized(self) -> bool:
        """Whether this binding currently authorizes execution."""
        return self.state is BindingState.AUTHORIZED

    def has_scoped_grant(self) -> bool:
        """Whether the binding carries a non-empty scoped connection grant.

        An empty grant is *unrestricted* in the custodian's semantics, not
        deny-all, so it is treated as "no usable grant" and never as a
        permissive pass.
        """
        return bool(self.granted_connections())

    def granted_connections(self) -> frozenset[str]:
        """The normalized, non-empty set of connections this binding grants."""
        return frozenset(
            value.strip()
            for value in self.allowed_connections
            if str(value).strip()
        )

    def grants_connection(self, connection_id: str) -> bool:
        """Whether the scoped grant covers ``connection_id``."""
        candidate = str(connection_id or "").strip()
        if not candidate:
            return False
        return candidate in self.granted_connections()


@runtime_checkable
class BindingResolver(Protocol):
    """Guardian-side resolution of account bindings and their scoped tokens.

    Implementations are expected to be authoritative Guardian state. This
    slice ships no production implementation; the durable resolver and the
    binding lifecycle belong to Gate C.
    """

    async def resolve_binding(
        self, guardian_account_id: str, provider: str
    ) -> AccountBinding | None:
        """Resolve the binding for one account and provider.

        Returns ``None`` when no binding exists. Returning a binding whose
        ``state`` is not ``AUTHORIZED`` is a valid way to express a revoked
        or uncertain binding; the adapter refuses both.
        """
        ...

    async def resolve_runtime_token(self, binding: AccountBinding) -> str | None:
        """Resolve the account-scoped persistent runtime token for a binding.

        Returns the token material, or ``None`` when it is unavailable. The
        material is used only inside the HTTP transport and never appears in
        an argument, a result, or a log.
        """
        ...


class NoBindingResolver:
    """Fail-closed resolver used when no authoritative resolver is configured.

    An adapter wired with this resolver can never execute: there is no
    Guardian-owned binding to authorize against. This is the default so that
    an unconfigured adapter is inert rather than permissive.
    """

    async def resolve_binding(
        self, guardian_account_id: str, provider: str
    ) -> AccountBinding | None:
        return None

    async def resolve_runtime_token(self, binding: AccountBinding) -> str | None:
        return None


__all__ = [
    "AccountBinding",
    "BindingResolver",
    "BindingState",
    "NoBindingResolver",
]
