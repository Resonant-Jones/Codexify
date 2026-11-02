"""Guardian-derived execution authority for the OpenConnector crossing.

The authority for a custodian execution is Guardian's, and this module is where
Guardian states it. Nothing here is taken from the request body, the query
string, or any model-supplied argument:

* the **account** and **subject** come from the verified account session;
* the **provider** comes from the reviewed allowlist entry for the action;
* the **task** is minted per invocation;
* the **permission profile** is read from Guardian's current state at the
  moment it is needed, not captured once and reused.

The permission profile is Guardian's own contract
(:mod:`guardian.command_bus.permission_profiles`), evaluated by Guardian's own
evaluator. This module does not introduce a second authorization system; it
supplies the facts Guardian already owns.

Where the connector and network permissions come from, stated plainly: an
**authorized, grant-bearing Guardian binding** for the provider *is* Guardian's
grant for that account to execute through the custodian for that provider.
The binding is the account's own custodian credential, exactly as a native
provider credential is the account's own credential in the Notion and Google
Drive integrations. A missing, revoked, mismatched, or unscoped binding
therefore yields no profile at all, which the existing evaluator denies as a
missing profile — a denial, never a permission.

The provider is read live on every evaluation, so the revalidation the adapter
performs immediately before the external crossing observes a revocation that
happened after the binding was first resolved.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from guardian.command_bus.permission_profiles import PermissionProfile
from guardian.connections.openconnector.adapter import (
    COMMAND_CLASS_CONNECTOR,
    COMMAND_ID_PREFIX,
    ExecutionAuthority,
)
from guardian.connections.openconnector.bindings import BindingResolver


@dataclass(frozen=True)
class GuardianAccountScope:
    """The server-derived identity of the calling account for one invocation.

    Attributes:
        account_id: The Codexify account that owns any binding. Guardian is
            the only authority for this value.
        subject_id: The authenticated principal acting for the account.
        task_id: A per-invocation task scope, minted by Guardian.
    """

    account_id: str
    subject_id: str
    task_id: str

    @classmethod
    def for_invocation(
        cls, *, account_id: str, subject_id: str
    ) -> "GuardianAccountScope":
        """Mint a scope for one invocation."""

        return cls(
            account_id=str(account_id or "").strip(),
            subject_id=str(subject_id or "").strip(),
            task_id=f"openconnector_{uuid4().hex[:16]}",
        )


def _binding_grants_custodian_use(
    binding,
    *,
    account_id: str,
    provider: str,
) -> bool:
    """Whether the binding is Guardian's current grant for this crossing."""

    if binding is None:
        return False
    if not binding.is_authorized():
        return False
    if str(getattr(binding, "guardian_account_id", "") or "").strip() != account_id:
        return False
    if str(getattr(binding, "provider", "") or "").strip() != provider:
        return False
    if not binding.has_scoped_grant():
        return False
    connection_uuid = str(getattr(binding, "connection_uuid", "") or "").strip()
    if not connection_uuid:
        return False
    return binding.grants_connection(connection_uuid)


def build_permission_profile_provider(
    *,
    scope: GuardianAccountScope,
    provider: str,
    action_id: str,
    resolver: BindingResolver,
):
    """Return a provider that reads Guardian's current permission profile.

    The returned callable is awaitable: it re-reads the binding on every
    evaluation, so the adapter's pre-dispatch revalidation sees live Guardian
    state rather than a snapshot taken earlier in the invocation.
    """

    async def current_permission_profile() -> PermissionProfile | None:
        binding = await resolver.resolve_binding(scope.account_id, provider)
        if not _binding_grants_custodian_use(
            binding, account_id=scope.account_id, provider=provider
        ):
            return None
        return PermissionProfile(
            profile_id=f"{COMMAND_ID_PREFIX}::{provider}::{scope.account_id}",
            actor_id=scope.subject_id,
            subject_id=scope.subject_id,
            task_id=scope.task_id,
            allowed_command_classes=(COMMAND_CLASS_CONNECTOR,),
            allowed_command_ids=(f"{COMMAND_ID_PREFIX}::{action_id}",),
            connector_allowed=True,
            network_allowed=True,
        )

    return current_permission_profile


def build_execution_authority(
    *,
    scope: GuardianAccountScope,
    provider: str,
    action_id: str,
    resolver: BindingResolver,
) -> ExecutionAuthority:
    """Build the server-derived authority for one custodian execution.

    The action arguments are empty by construction: this crossing exposes no
    model-supplied action inputs, so no argument can carry account identity,
    connection identity, or credential material.
    """

    return ExecutionAuthority(
        guardian_account_id=scope.account_id,
        provider=provider,
        action_id=action_id,
        actor_id=scope.subject_id,
        subject_id=scope.subject_id,
        task_id=scope.task_id,
        permission_profile_provider=build_permission_profile_provider(
            scope=scope,
            provider=provider,
            action_id=action_id,
            resolver=resolver,
        ),
        arguments={},
        requested_connection_uuid=None,
    )


__all__ = [
    "GuardianAccountScope",
    "build_execution_authority",
    "build_permission_profile_provider",
]
