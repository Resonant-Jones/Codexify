"""Manual install-binding helpers for approved capability registry entries."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping
from uuid import uuid4

from guardian.extensions.contracts import (
    ExtensionBindingRecord,
    ExtensionInstallBinding,
)
from guardian.extensions.registry import CapabilityRegistry
from guardian.extensions.store import ExtensionProposalStore
from guardian.extensions.tokens import ExtensionInstallBindingStatus


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _new_binding_id() -> str:
    return f"binding_{uuid4().hex[:16]}"


def _clean_mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    if not value:
        return {}
    return {str(key): item for key, item in dict(value).items()}


class ExtensionInstallBindings:
    """Backend-only scoped binding persistence facade."""

    def __init__(
        self,
        store: ExtensionProposalStore | None = None,
        registry: CapabilityRegistry | None = None,
    ) -> None:
        self.store = store or ExtensionProposalStore()
        self.registry = registry or CapabilityRegistry(self.store)

    def bind_registry_entry_to_scope(
        self,
        *,
        binding: ExtensionInstallBinding,
        binding_id: str | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> ExtensionBindingRecord:
        registry_entry = self.registry.get_registry_entry_by_id(
            account_id=binding.account_id,
            registry_id=binding.registry_entry_id,
        )
        if registry_entry is None:
            raise LookupError(
                f"registry entry not found for account_id={binding.account_id!r}"
            )
        if not registry_entry.is_registered:
            raise ValueError("bindings require a registered capability entry")

        if (
            binding.source_thread_id is not None
            and binding.source_thread_id != registry_entry.source_thread_id
        ):
            raise ValueError("source_thread_id must match the registry lineage")
        if (
            binding.source_message_id is not None
            and binding.source_message_id != registry_entry.source_message_id
        ):
            raise ValueError(
                "source_message_id must match the registry lineage"
            )

        existing = self.store.list_bindings(
            account_id=binding.account_id,
            registry_entry_id=binding.registry_entry_id,
            scope=binding.scope_token,
            project_id=binding.project_id,
            profile_id=binding.profile_id,
            account_scope_target_id=binding.account_scope_target_id,
            status=ExtensionInstallBindingStatus.ACTIVE.value,
        )
        if existing:
            raise ValueError(
                "duplicate active binding for the same account, registry entry, and scope"
            )

        now = created_at or _utc_now()
        record = ExtensionBindingRecord(
            binding_id=binding_id or _new_binding_id(),
            account_id=binding.account_id,
            registry_entry_id=registry_entry.registry_id,
            proposal_id=registry_entry.proposal_id,
            scope_token=binding.scope_token,
            project_id=binding.project_id,
            profile_id=binding.profile_id,
            account_scope_target_id=binding.account_scope_target_id,
            binding_status_token=ExtensionInstallBindingStatus.ACTIVE.value,
            bind_reason=binding.bind_reason,
            bind_notes=binding.bind_notes,
            bind_metadata={
                **_clean_mapping(binding.bind_metadata),
                "registry_entry_id": registry_entry.registry_id,
                "proposal_id": registry_entry.proposal_id,
                "scope_token": binding.scope_token,
                "source_thread_id": registry_entry.source_thread_id,
                "source_message_id": registry_entry.source_message_id,
                "registry_status_token": registry_entry.status_token,
            },
            unbind_metadata={},
            source_thread_id=registry_entry.source_thread_id,
            source_message_id=registry_entry.source_message_id,
            created_at=now,
            updated_at=updated_at or now,
        )
        return self.store.create_binding(record)

    def get_binding_by_id(
        self, *, account_id: str, binding_id: str
    ) -> ExtensionBindingRecord | None:
        return self.store.get_binding_by_id(
            account_id=account_id, binding_id=binding_id
        )

    def list_bindings(
        self,
        *,
        account_id: str,
        registry_entry_id: str | None = None,
        scope: str | None = None,
        project_id: int | None = None,
        profile_id: str | None = None,
        account_scope_target_id: str | None = None,
        status: str | None = None,
    ) -> list[ExtensionBindingRecord]:
        return self.store.list_bindings(
            account_id=account_id,
            registry_entry_id=registry_entry_id,
            scope=scope,
            project_id=project_id,
            profile_id=profile_id,
            account_scope_target_id=account_scope_target_id,
            status=status,
        )

    def unbind_existing_binding(
        self,
        *,
        account_id: str,
        binding_id: str,
        reason: str | None = None,
        notes: Mapping[str, Any] | None = None,
        unbind_metadata: Mapping[str, Any] | None = None,
    ) -> ExtensionBindingRecord:
        record = self.store.get_binding_by_id(
            account_id=account_id, binding_id=binding_id
        )
        if record is None:
            raise LookupError(
                f"binding not found for account_id={account_id!r}"
            )
        payload = dict(unbind_metadata or {})
        if reason is not None:
            payload.setdefault("reason", reason)
        if notes is not None:
            payload.setdefault("notes", _clean_mapping(notes))
        payload.setdefault("binding_id", record.binding_id)
        payload.setdefault("registry_entry_id", record.registry_entry_id)
        payload.setdefault("proposal_id", record.proposal_id)
        payload.setdefault("scope_token", record.scope_token)
        payload.setdefault("source_thread_id", record.source_thread_id)
        payload.setdefault("source_message_id", record.source_message_id)
        return self.store.unbind_binding(
            account_id=account_id,
            binding_id=binding_id,
            unbind_metadata=payload,
            unbound_at=_utc_now(),
        )

    def update_binding_status(
        self,
        *,
        account_id: str,
        binding_id: str,
        status: str,
    ) -> ExtensionBindingRecord:
        if status == ExtensionInstallBindingStatus.UNBOUND.value:
            return self.unbind_existing_binding(
                account_id=account_id,
                binding_id=binding_id,
            )
        return self.store.update_binding_status(
            account_id=account_id,
            binding_id=binding_id,
            status=status,
        )


__all__ = ["ExtensionInstallBindings"]
