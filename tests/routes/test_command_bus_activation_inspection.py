from __future__ import annotations

import json
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.db.models import (
    AgentExtensionInstallBinding,
    AgentExtensionInstallGateDecision,
    AgentExtensionProposal,
    AgentExtensionRegistryEntry,
    Base,
)
from guardian.extensions.bindings import ExtensionInstallBindings
from guardian.extensions.contracts import (
    CapabilityActivationConflictClassToken,
    CapabilityActivationDenyReasonToken,
    CapabilityActivationOutcomeToken,
    CapabilityExposedCommand,
    ExtensionDeclaredDependency,
    ExtensionInstallBinding,
    ExtensionProposalManifest,
    ExtensionRequestedPermission,
    ExtensionRollbackMetadata,
    ExtensionTestEvidenceMetadata,
)
from guardian.extensions.install_gate import InstallGate
from guardian.extensions.registry import CapabilityRegistry
from guardian.extensions.resolver import EffectiveCapabilityResolver
from guardian.extensions.store import ExtensionProposalStore
from guardian.extensions.tokens import (
    ExtensionInstallBindingScope,
    ExtensionProposalScope,
    ExtensionTargetSurface,
)
from guardian.routes import command_bus

COMMAND_ID = "command::activate-alpha"
OTHER_COMMAND_ID = "command::activate-beta"


@pytest.fixture()
def activation_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-key")
    monkeypatch.setenv("DEBUG", "1")

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        bind=engine,
        tables=[
            AgentExtensionProposal.__table__,
            AgentExtensionInstallGateDecision.__table__,
            AgentExtensionRegistryEntry.__table__,
            AgentExtensionInstallBinding.__table__,
        ],
    )
    Session = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, future=True
    )

    class _DB:
        def get_session(self):
            return Session()

    command_bus.configure_db(_DB())

    app = FastAPI()
    app.include_router(command_bus.router)
    client = TestClient(app)
    try:
        yield client
    finally:
        client.close()
        command_bus.configure_db(None)


def _manifest(
    *,
    target_surface: str,
    scope: str,
    project_id: int | None = None,
    profile_id: str | None = None,
    source_thread_id: int | None = 41,
    source_message_id: int | None = 42,
    exposed_command_ids: tuple[str, ...] = (COMMAND_ID,),
    requested_permissions: tuple[ExtensionRequestedPermission, ...]
    | None = None,
) -> ExtensionProposalManifest:
    return ExtensionProposalManifest(
        target_surface=target_surface,
        scope=scope,
        project_id=project_id,
        profile_id=profile_id,
        source_thread_id=source_thread_id,
        source_message_id=source_message_id,
        summary="Generate a bounded tool plugin",
        description="Draft a tool proposal without executing it.",
        requested_permissions=requested_permissions
        or (
            ExtensionRequestedPermission(
                permission="command.run",
                resource="command_bus",
                reason="bounded command execution",
            ),
        ),
        declared_dependencies=(
            ExtensionDeclaredDependency(
                name="httpx",
                version_spec=">=0.28",
                source="pypi",
            ),
        ),
        exposed_commands=tuple(
            CapabilityExposedCommand(
                command_id=command_id,
                tool_aliases=(),
            )
            for command_id in exposed_command_ids
        ),
        rollback_metadata=ExtensionRollbackMetadata(
            strategy="disable_and_revert",
            rollback_ref="ticket-123",
        ),
        test_evidence_metadata=ExtensionTestEvidenceMetadata(
            status="passing",
            summary="activation inspection route coverage",
            artifacts=(
                "tests/routes/test_command_bus_activation_inspection.py",
            ),
        ),
    )


def _approved_registry_entry(
    store: ExtensionProposalStore,
    gate: InstallGate,
    *,
    account_id: str,
    manifest: ExtensionProposalManifest,
):
    proposal = store.create_proposal(account_id=account_id, manifest=manifest)
    decision, registry_entry = gate.approve_proposal(
        account_id=account_id,
        proposal_id=proposal.proposal_id,
        reason="manual approval",
        notes={"reviewer": "alice"},
    )
    return proposal, decision, registry_entry


def _bind_scope(
    bindings: ExtensionInstallBindings,
    registry_entry,
    *,
    account_id: str,
    scope_token: str,
    project_id: int | None = None,
    profile_id: str | None = None,
    account_scope_target_id: str | None = "account-target-1",
):
    return bindings.bind_registry_entry_to_scope(
        binding=ExtensionInstallBinding(
            account_id=account_id,
            registry_entry_id=registry_entry.registry_id,
            scope_token=scope_token,
            project_id=project_id,
            profile_id=profile_id,
            account_scope_target_id=account_scope_target_id,
        )
    )


def _bind_all_scopes(
    bindings: ExtensionInstallBindings,
    registry_entry,
    *,
    account_id: str,
    project_id: int | None = None,
    profile_id: str | None = None,
):
    bound = {}
    if project_id is not None:
        bound["project"] = _bind_scope(
            bindings,
            registry_entry,
            account_id=account_id,
            scope_token=ExtensionInstallBindingScope.PROJECT.value,
            project_id=project_id,
            account_scope_target_id=None,
        )
    if profile_id is not None:
        bound["profile"] = _bind_scope(
            bindings,
            registry_entry,
            account_id=account_id,
            scope_token=ExtensionInstallBindingScope.PROFILE.value,
            profile_id=profile_id,
            account_scope_target_id=None,
        )
    bound["account"] = _bind_scope(
        bindings,
        registry_entry,
        account_id=account_id,
        scope_token=ExtensionInstallBindingScope.ACCOUNT.value,
        account_scope_target_id=f"{account_id}-target",
    )
    return bound


def _inspection_payload(
    *,
    account_id: str,
    requested_command_id: str,
    activation_context_token: str,
    project_id: int | None = None,
    profile_id: str | None = None,
    requested_permissions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "account_id": account_id,
        "requested_command_id": requested_command_id,
        "activation_context_token": activation_context_token,
        "project_id": project_id,
        "profile_id": profile_id,
        "requested_permissions_json": json.dumps(requested_permissions or []),
        "request_metadata_json": json.dumps({"source": "route-test"}),
    }


def _inspect(
    client: TestClient,
    *,
    headers: dict[str, str],
    account_id: str,
    requested_command_id: str,
    activation_context_token: str,
    project_id: int | None = None,
    profile_id: str | None = None,
    requested_permissions: list[dict[str, Any]] | None = None,
) -> Any:
    params = {
        key: value
        for key, value in _inspection_payload(
            account_id=account_id,
            requested_command_id=requested_command_id,
            activation_context_token=activation_context_token,
            project_id=project_id,
            profile_id=profile_id,
            requested_permissions=requested_permissions,
        ).items()
        if value is not None
    }
    response = client.get(
        "/api/guardian/commands/activation/inspect",
        headers=headers,
        params=params,
    )
    return response


def test_activation_inspection_allows_account_context_and_returns_dispatch_envelope(
    activation_client: TestClient,
) -> None:
    store = command_bus._activation_resolver.store
    gate = InstallGate(store, CapabilityRegistry(store))
    bindings = ExtensionInstallBindings(store, CapabilityRegistry(store))
    resolver = EffectiveCapabilityResolver(store)
    proposal, _decision, registry_entry = _approved_registry_entry(
        store,
        gate,
        account_id="acct-1",
        manifest=_manifest(
            target_surface=ExtensionTargetSurface.COMMAND_BUS.value,
            scope=ExtensionProposalScope.ACCOUNT.value,
        ),
    )
    account_binding = _bind_scope(
        bindings,
        registry_entry,
        account_id="acct-1",
        scope_token=ExtensionInstallBindingScope.ACCOUNT.value,
        account_scope_target_id="account-target-1",
    )
    command_bus.configure_db(store.db)
    assert resolver.store is store

    response = _inspect(
        activation_client,
        headers={"X-API-Key": "test-key", "X-User-Id": "acct-1"},
        account_id="acct-1",
        requested_command_id=COMMAND_ID,
        activation_context_token="owner_only",
    )

    assert response.status_code == 200
    payload = response.json()
    assert (
        payload["outcome_token"]
        == CapabilityActivationOutcomeToken.ALLOWED.value
    )
    assert payload["request_json"]["account_id"] == "acct-1"
    assert payload["request_json"]["requested_command_id"] == COMMAND_ID
    assert payload["dispatch_envelope_json"]["owner_account_id"] == "acct-1"
    assert (
        payload["dispatch_envelope_json"]["requested_command_id"] == COMMAND_ID
    )
    assert payload["dispatch_envelope_json"]["command_id"] == COMMAND_ID
    assert (
        payload["dispatch_envelope_json"]["proposal_id"] == proposal.proposal_id
    )
    assert (
        payload["dispatch_envelope_json"]["registry_entry_id"]
        == registry_entry.registry_id
    )
    assert (
        payload["dispatch_envelope_json"]["binding_id"]
        == account_binding.binding_id
    )


def test_activation_inspection_prefers_profile_over_project_and_project_over_account(
    activation_client: TestClient,
) -> None:
    store = command_bus._activation_resolver.store
    gate = InstallGate(store, CapabilityRegistry(store))
    bindings = ExtensionInstallBindings(store, CapabilityRegistry(store))
    _proposal, _decision, registry_entry = _approved_registry_entry(
        store,
        gate,
        account_id="acct-1",
        manifest=_manifest(
            target_surface=ExtensionTargetSurface.COMMAND_BUS.value,
            scope=ExtensionProposalScope.PROJECT.value,
            project_id=17,
            profile_id="profile-alpha",
        ),
    )
    scoped = _bind_all_scopes(
        bindings,
        registry_entry,
        account_id="acct-1",
        project_id=17,
        profile_id="profile-alpha",
    )
    command_bus.configure_db(store.db)

    owner_only = _inspect(
        activation_client,
        headers={"X-API-Key": "test-key", "X-User-Id": "acct-1"},
        account_id="acct-1",
        requested_command_id=COMMAND_ID,
        activation_context_token="owner_only",
    )
    owner_project = _inspect(
        activation_client,
        headers={"X-API-Key": "test-key", "X-User-Id": "acct-1"},
        account_id="acct-1",
        requested_command_id=COMMAND_ID,
        activation_context_token="owner_project",
        project_id=17,
    )
    owner_profile = _inspect(
        activation_client,
        headers={"X-API-Key": "test-key", "X-User-Id": "acct-1"},
        account_id="acct-1",
        requested_command_id=COMMAND_ID,
        activation_context_token="owner_profile",
        profile_id="profile-alpha",
    )
    owner_project_profile = _inspect(
        activation_client,
        headers={"X-API-Key": "test-key", "X-User-Id": "acct-1"},
        account_id="acct-1",
        requested_command_id=COMMAND_ID,
        activation_context_token="owner_project_profile",
        project_id=17,
        profile_id="profile-alpha",
    )

    assert owner_only.status_code == 200
    assert (
        owner_only.json()["dispatch_envelope_json"]["binding_id"]
        == scoped["account"].binding_id
    )
    assert owner_project.status_code == 200
    assert (
        owner_project.json()["dispatch_envelope_json"]["binding_id"]
        == scoped["project"].binding_id
    )
    assert owner_profile.status_code == 200
    assert (
        owner_profile.json()["dispatch_envelope_json"]["binding_id"]
        == scoped["profile"].binding_id
    )
    assert owner_project_profile.status_code == 200
    assert (
        owner_project_profile.json()["dispatch_envelope_json"]["binding_id"]
        == scoped["profile"].binding_id
    )


def test_activation_inspection_denies_when_no_matching_exposure_exists(
    activation_client: TestClient,
) -> None:
    store = command_bus._activation_resolver.store
    gate = InstallGate(store, CapabilityRegistry(store))
    bindings = ExtensionInstallBindings(store, CapabilityRegistry(store))
    _proposal, _decision, registry_entry = _approved_registry_entry(
        store,
        gate,
        account_id="acct-1",
        manifest=_manifest(
            target_surface=ExtensionTargetSurface.COMMAND_BUS.value,
            scope=ExtensionProposalScope.ACCOUNT.value,
            exposed_command_ids=(OTHER_COMMAND_ID,),
        ),
    )
    _bind_scope(
        bindings,
        registry_entry,
        account_id="acct-1",
        scope_token=ExtensionInstallBindingScope.ACCOUNT.value,
        account_scope_target_id="account-target-1",
    )
    command_bus.configure_db(store.db)

    response = _inspect(
        activation_client,
        headers={"X-API-Key": "test-key", "X-User-Id": "acct-1"},
        account_id="acct-1",
        requested_command_id=COMMAND_ID,
        activation_context_token="owner_only",
    )

    assert response.status_code == 200
    payload = response.json()
    assert (
        payload["outcome_token"]
        == CapabilityActivationOutcomeToken.DENIED.value
    )
    assert payload["denial_reason_token"] == (
        CapabilityActivationDenyReasonToken.NO_MATCHING_EXPOSURE.value
    )
    assert "dispatch_envelope_json" not in payload


def test_activation_inspection_denies_when_requested_permissions_are_insufficient(
    activation_client: TestClient,
) -> None:
    store = command_bus._activation_resolver.store
    gate = InstallGate(store, CapabilityRegistry(store))
    bindings = ExtensionInstallBindings(store, CapabilityRegistry(store))
    _proposal, _decision, registry_entry = _approved_registry_entry(
        store,
        gate,
        account_id="acct-1",
        manifest=_manifest(
            target_surface=ExtensionTargetSurface.COMMAND_BUS.value,
            scope=ExtensionProposalScope.ACCOUNT.value,
            requested_permissions=(
                ExtensionRequestedPermission(
                    permission="command.run",
                    resource="command_bus",
                    reason="bounded command execution",
                ),
            ),
        ),
    )
    _bind_scope(
        bindings,
        registry_entry,
        account_id="acct-1",
        scope_token=ExtensionInstallBindingScope.ACCOUNT.value,
        account_scope_target_id="account-target-1",
    )
    command_bus.configure_db(store.db)

    response = _inspect(
        activation_client,
        headers={"X-API-Key": "test-key", "X-User-Id": "acct-1"},
        account_id="acct-1",
        requested_command_id=COMMAND_ID,
        activation_context_token="owner_only",
        requested_permissions=[
            {
                "permission": "command.admin",
                "resource": "command_bus",
                "reason": "requires elevated permission",
            }
        ],
    )

    assert response.status_code == 200
    payload = response.json()
    assert (
        payload["outcome_token"]
        == CapabilityActivationOutcomeToken.DENIED.value
    )
    assert payload["denial_reason_token"] == (
        CapabilityActivationDenyReasonToken.INSUFFICIENT_PERMISSIONS.value
    )
    assert "dispatch_envelope_json" not in payload


def test_activation_inspection_conflicts_on_overlapping_same_command_exposure(
    activation_client: TestClient,
) -> None:
    store = command_bus._activation_resolver.store
    gate = InstallGate(store, CapabilityRegistry(store))
    bindings = ExtensionInstallBindings(store, CapabilityRegistry(store))
    first_registry = _approved_registry_entry(
        store,
        gate,
        account_id="acct-1",
        manifest=_manifest(
            target_surface=ExtensionTargetSurface.COMMAND_BUS.value,
            scope=ExtensionProposalScope.ACCOUNT.value,
            exposed_command_ids=(COMMAND_ID,),
        ),
    )[2]
    second_registry = _approved_registry_entry(
        store,
        gate,
        account_id="acct-1",
        manifest=_manifest(
            target_surface=ExtensionTargetSurface.PERSONA_STUDIO.value,
            scope=ExtensionProposalScope.ACCOUNT.value,
            exposed_command_ids=(COMMAND_ID,),
        ),
    )[2]
    _bind_scope(
        bindings,
        first_registry,
        account_id="acct-1",
        scope_token=ExtensionInstallBindingScope.ACCOUNT.value,
        account_scope_target_id="account-target-1",
    )
    _bind_scope(
        bindings,
        second_registry,
        account_id="acct-1",
        scope_token=ExtensionInstallBindingScope.ACCOUNT.value,
        account_scope_target_id="account-target-2",
    )
    command_bus.configure_db(store.db)

    response = _inspect(
        activation_client,
        headers={"X-API-Key": "test-key", "X-User-Id": "acct-1"},
        account_id="acct-1",
        requested_command_id=COMMAND_ID,
        activation_context_token="owner_only",
    )

    assert response.status_code == 200
    payload = response.json()
    assert (
        payload["outcome_token"]
        == CapabilityActivationOutcomeToken.CONFLICT.value
    )
    assert payload["conflict_class_token"] == (
        CapabilityActivationConflictClassToken.SAME_COMMAND_EXPOSURE.value
    )
    assert "dispatch_envelope_json" not in payload
    assert len(payload["candidate_matches_json"]) == 2


def test_activation_inspection_rejects_owner_mismatch(
    activation_client: TestClient,
) -> None:
    store = command_bus._activation_resolver.store
    gate = InstallGate(store, CapabilityRegistry(store))
    bindings = ExtensionInstallBindings(store, CapabilityRegistry(store))
    _proposal, _decision, registry_entry = _approved_registry_entry(
        store,
        gate,
        account_id="acct-2",
        manifest=_manifest(
            target_surface=ExtensionTargetSurface.COMMAND_BUS.value,
            scope=ExtensionProposalScope.ACCOUNT.value,
        ),
    )
    _bind_scope(
        bindings,
        registry_entry,
        account_id="acct-2",
        scope_token=ExtensionInstallBindingScope.ACCOUNT.value,
        account_scope_target_id="account-target-2",
    )
    command_bus.configure_db(store.db)

    response = _inspect(
        activation_client,
        headers={"X-API-Key": "test-key", "X-User-Id": "acct-1"},
        account_id="acct-2",
        requested_command_id=COMMAND_ID,
        activation_context_token="owner_only",
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "forbidden"}


def test_activation_inspection_does_not_execute_command_bus(
    activation_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = command_bus._activation_resolver.store
    gate = InstallGate(store, CapabilityRegistry(store))
    bindings = ExtensionInstallBindings(store, CapabilityRegistry(store))
    _proposal, _decision, registry_entry = _approved_registry_entry(
        store,
        gate,
        account_id="acct-1",
        manifest=_manifest(
            target_surface=ExtensionTargetSurface.COMMAND_BUS.value,
            scope=ExtensionProposalScope.ACCOUNT.value,
        ),
    )
    _bind_scope(
        bindings,
        registry_entry,
        account_id="acct-1",
        scope_token=ExtensionInstallBindingScope.ACCOUNT.value,
        account_scope_target_id="account-target-1",
    )
    command_bus.configure_db(store.db)

    calls: list[dict[str, Any]] = []

    async def _execute_invoke(*args: Any, **kwargs: Any) -> dict[str, Any]:
        calls.append({"args": args, "kwargs": kwargs})
        raise AssertionError("command bus should not execute during inspection")

    monkeypatch.setattr(command_bus, "execute_invoke", _execute_invoke)

    response = _inspect(
        activation_client,
        headers={"X-API-Key": "test-key", "X-User-Id": "acct-1"},
        account_id="acct-1",
        requested_command_id=COMMAND_ID,
        activation_context_token="owner_only",
    )

    assert response.status_code == 200
    assert calls == []
