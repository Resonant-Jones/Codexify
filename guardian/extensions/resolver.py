"""Read-time effective capability resolution for approved extensions."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Sequence

from guardian.extensions.contracts import (
    EffectiveCapabilityRecord,
    EffectiveCapabilitySnapshot,
    ExtensionBindingRecord,
)
from guardian.extensions.store import ExtensionProposalStore
from guardian.extensions.tokens import ExtensionInstallBindingScope


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _clean_account_id(value: str | None) -> str:
    account_id = str(value or "").strip()
    if not account_id:
        raise ValueError("account_id is required")
    return account_id


class EffectiveCapabilityResolutionError(ValueError):
    """Raised when effective capability resolution encounters ambiguity."""


class EffectiveCapabilityResolver:
    """Backend-only read-time capability resolution facade."""

    def __init__(self, store: ExtensionProposalStore | None = None) -> None:
        self.store = store or ExtensionProposalStore()

    def resolve_effective_capabilities_for_owner(
        self, *, account_id: str
    ) -> EffectiveCapabilitySnapshot:
        return self._resolve(account_id=account_id)

    def resolve_effective_capabilities_for_owner_and_project(
        self, *, account_id: str, project_id: int
    ) -> EffectiveCapabilitySnapshot:
        return self._resolve(account_id=account_id, project_id=int(project_id))

    def resolve_effective_capabilities_for_owner_and_profile(
        self, *, account_id: str, profile_id: str
    ) -> EffectiveCapabilitySnapshot:
        profile_id = str(profile_id).strip()
        if not profile_id:
            raise ValueError("profile_id is required")
        return self._resolve(account_id=account_id, profile_id=profile_id)

    def resolve_effective_capabilities_for_owner_project_profile(
        self,
        *,
        account_id: str,
        project_id: int,
        profile_id: str,
    ) -> EffectiveCapabilitySnapshot:
        profile_id = str(profile_id).strip()
        if not profile_id:
            raise ValueError("profile_id is required")
        return self._resolve(
            account_id=account_id,
            project_id=int(project_id),
            profile_id=profile_id,
        )

    def _resolve(
        self,
        *,
        account_id: str,
        project_id: int | None = None,
        profile_id: str | None = None,
    ) -> EffectiveCapabilitySnapshot:
        account_id = _clean_account_id(account_id)
        profile_id = str(profile_id).strip() if profile_id is not None else None
        if profile_id == "":
            profile_id = None

        registry_entries = self.store.list_registered_registry_entries(
            account_id=account_id
        )
        active_bindings = self.store.list_active_bindings(account_id=account_id)
        bindings_by_registry: dict[
            str, list[ExtensionBindingRecord]
        ] = defaultdict(list)
        for binding in active_bindings:
            bindings_by_registry[binding.registry_entry_id].append(binding)

        records: list[EffectiveCapabilityRecord] = []
        for registry_entry in registry_entries:
            candidate_bindings = bindings_by_registry.get(
                registry_entry.registry_id
            )
            if not candidate_bindings:
                continue
            selected = self._select_binding(
                registry_entry_id=registry_entry.registry_id,
                candidate_bindings=candidate_bindings,
                project_id=project_id,
                profile_id=profile_id,
            )
            if selected is None:
                continue
            records.append(
                EffectiveCapabilityRecord(
                    registry_entry=registry_entry,
                    binding=selected,
                    query_project_id=project_id,
                    query_profile_id=profile_id,
                )
            )

        records.sort(
            key=lambda record: (
                record.target_surface_token,
                record.registry_entry_id,
                record.binding_id,
            )
        )
        return EffectiveCapabilitySnapshot(
            account_id=account_id,
            project_id=project_id,
            profile_id=profile_id,
            records=tuple(records),
            resolved_at=_utc_now(),
        )

    def _precedence_order(
        self, *, project_id: int | None, profile_id: str | None
    ) -> tuple[str, ...]:
        order: list[str] = []
        if profile_id is not None:
            order.append(ExtensionInstallBindingScope.PROFILE.value)
        if project_id is not None:
            order.append(ExtensionInstallBindingScope.PROJECT.value)
        order.append(ExtensionInstallBindingScope.ACCOUNT.value)
        return tuple(order)

    def _matches_context(
        self,
        *,
        binding,
        project_id: int | None,
        profile_id: str | None,
    ) -> bool:
        if binding.scope_token == ExtensionInstallBindingScope.PROFILE.value:
            return profile_id is not None and binding.profile_id == profile_id
        if binding.scope_token == ExtensionInstallBindingScope.PROJECT.value:
            return project_id is not None and binding.project_id == project_id
        if binding.scope_token == ExtensionInstallBindingScope.ACCOUNT.value:
            return True
        return False

    def _select_binding(
        self,
        *,
        registry_entry_id: str,
        candidate_bindings: Sequence[ExtensionBindingRecord],
        project_id: int | None,
        profile_id: str | None,
    ) -> ExtensionBindingRecord | None:
        precedence_order = self._precedence_order(
            project_id=project_id, profile_id=profile_id
        )
        ranked: list[tuple[int, ExtensionBindingRecord]] = []
        for binding in candidate_bindings:
            if not self._matches_context(
                binding=binding,
                project_id=project_id,
                profile_id=profile_id,
            ):
                continue
            try:
                rank = precedence_order.index(binding.scope_token)
            except ValueError:
                continue
            ranked.append((rank, binding))

        if not ranked:
            return None

        ranked.sort(
            key=lambda item: (
                item[0],
                item[1].created_at or datetime.min.replace(tzinfo=timezone.utc),
                item[1].binding_id,
            )
        )
        best_rank = ranked[0][0]
        winners = [binding for rank, binding in ranked if rank == best_rank]
        if len(winners) > 1:
            raise EffectiveCapabilityResolutionError(
                "ambiguous active bindings for registry entry "
                f"{registry_entry_id!r} at precedence {precedence_order[best_rank]!r}"
            )
        return winners[0]


__all__ = [
    "EffectiveCapabilityResolver",
    "EffectiveCapabilityResolutionError",
]
