"""Guardian-derived execution authority for the OpenConnector crossing.

The authority for a custodian execution is Guardian's, and this module is where
Guardian states it. Nothing here is taken from the request body, the query
string, or any model-supplied argument:

* the **account** and **subject** come from the verified account session;
* the **provider** comes from the reviewed allowlist entry for the action;
* the **task** is minted per invocation;
* the **permission profile** is read from Guardian's current state at the
  moment it is needed, not captured once and reused.

Two Guardian facts are required, and they answer two different questions.

**The credential binding** answers *which* account-owned credential may be
selected. It carries the custodian connection and the reference to the scoped
runtime token, and it is resolved for the authenticated account, so an account
can only ever select its own credential.

**The usage grant** answers *whether this actor may invoke that credential at
all*: this account, this subject, this provider, this action, in the current
invocation. It is a separate Guardian determination with its own source, and it
is what supplies connector and network permission.

Neither substitutes for the other, and this is load-bearing rather than
cosmetic. ADR-094 requires credential selection and eligibility to be separate
decisions, and requires the execution-time boundary to revalidate the binding
**and** the policy. If connector permission were derived from the binding, a
binding's existence would stand in for the invocation permission check, and a
revoked *permission* would be invisible to a revalidation that only re-reads
the credential.

The permission profile is Guardian's own contract
(:mod:`guardian.command_bus.permission_profiles`), evaluated by Guardian's own
evaluator. This module does not introduce a second authorization system; it
supplies the facts Guardian already owns.

Both facts are read live on every evaluation, so the revalidation the adapter
performs immediately before the external crossing observes a revocation — of
the credential or of the permission — that happened after either was first
resolved.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable
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


@dataclass(frozen=True)
class CustodianUsageGrant:
    """Guardian's explicit grant to invoke one custodian crossing.

    This is the *invocation permission* fact, deliberately separate from the
    credential binding. It names the account, the acting subject, the provider,
    and the action.

    Attributes:
        guardian_account_id: The account the grant was issued to.
        subject_id: The principal the grant was issued to.
        provider: The provider the grant covers.
        action_id: The action the grant covers.
        task_id: The task scope the grant covers. ``None`` means the grant
            covers the invoking task; a named task must match exactly.
        granted: Whether the grant is currently in force.
    """

    guardian_account_id: str
    subject_id: str
    provider: str
    action_id: str
    task_id: str | None = None
    granted: bool = True

    def covers(
        self,
        *,
        account_id: str,
        subject_id: str,
        provider: str,
        action_id: str,
        task_id: str,
    ) -> bool:
        """Whether this grant authorizes exactly this crossing."""

        if not self.granted:
            return False
        if str(self.guardian_account_id or "").strip() != account_id:
            return False
        if str(self.subject_id or "").strip() != subject_id:
            return False
        if str(self.provider or "").strip() != provider:
            return False
        if str(self.action_id or "").strip() != action_id:
            return False
        if self.task_id is not None and str(self.task_id).strip() != task_id:
            return False
        return True


@runtime_checkable
class CustodianUsageAuthorizer(Protocol):
    """The source of Guardian's invocation permission for a custodian crossing.

    An implementation answers one question: does Guardian currently authorize
    this account, subject, provider, action, and task to cross? It must not
    answer that question by inspecting a credential binding — the two decisions
    are separate, and the binding's existence is not evidence of permission.
    """

    async def authorize(
        self,
        *,
        account_id: str,
        subject_id: str,
        provider: str,
        action_id: str,
        task_id: str,
    ) -> CustodianUsageGrant | None: ...


class NoUsageAuthorizer:
    """The fail-closed default: nothing is authorized.

    With no authorizer configured, every custodian crossing is denied. There is
    no fallback to "the account holds a binding", and no fallback to another
    account, another provider, or a shared default.
    """

    async def authorize(
        self,
        *,
        account_id: str,
        subject_id: str,
        provider: str,
        action_id: str,
        task_id: str,
    ) -> CustodianUsageGrant | None:
        return None


def _binding_grants_credential_use(
    binding,
    *,
    account_id: str,
    provider: str,
) -> bool:
    """Whether the binding may be *selected* for this account and provider.

    This is credential eligibility only. It says nothing about whether the
    account is permitted to invoke it.
    """

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
    authorizer: CustodianUsageAuthorizer,
):
    """Return a provider that reads Guardian's current permission profile.

    The returned callable is awaitable: it re-reads both Guardian facts on every
    evaluation, so the adapter's pre-dispatch revalidation sees live Guardian
    state rather than a snapshot taken earlier in the invocation. A revocation
    of the credential or of the permission, between resolution and dispatch,
    stops the crossing.
    """

    async def current_permission_profile() -> PermissionProfile | None:
        binding = await resolver.resolve_binding(scope.account_id, provider)
        if not _binding_grants_credential_use(
            binding, account_id=scope.account_id, provider=provider
        ):
            return None

        grant = await authorizer.authorize(
            account_id=scope.account_id,
            subject_id=scope.subject_id,
            provider=provider,
            action_id=action_id,
            task_id=scope.task_id,
        )
        if grant is None or not grant.covers(
            account_id=scope.account_id,
            subject_id=scope.subject_id,
            provider=provider,
            action_id=action_id,
            task_id=scope.task_id,
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
    authorizer: CustodianUsageAuthorizer,
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
            authorizer=authorizer,
        ),
        arguments={},
        requested_connection_uuid=None,
    )


__all__ = [
    "CustodianUsageAuthorizer",
    "CustodianUsageGrant",
    "GuardianAccountScope",
    "NoUsageAuthorizer",
    "build_execution_authority",
    "build_permission_profile_provider",
]
