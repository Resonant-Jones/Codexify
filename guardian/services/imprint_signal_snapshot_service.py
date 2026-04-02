"""
Canonical snapshot builder for imprint proposal generation.
"""

from __future__ import annotations

from typing import Any

from guardian.cognition.identity_policy import normalize_identity_depth
from guardian.contracts.imprint_snapshot import ImprintSignalSnapshot
from guardian.services import iddb_settings_service, imprint_fold_service

SNAPSHOT_VERSION = 1
SNAPSHOT_BUILDER_VERSION = "imprint-snapshot-v1"


def _scope_bundle(state: dict[str, Any] | None) -> dict[str, Any] | None:
    if not state:
        return None
    return {
        "scope_key": state.get("scope_key"),
        "scope_kind": state.get("scope_kind"),
        "user_id": state.get("user_id"),
        "project_id": state.get("project_id"),
        "fold_version": state.get("fold_version"),
        "state_hash": state.get("state_hash"),
        "source_observation_count": state.get("source_observation_count"),
        "source_observation_max_id": state.get("source_observation_max_id"),
        "state_payload": state.get("state_payload") or {},
    }


def build_imprint_signal_snapshot(
    *,
    user_id: str,
    project_id: int | None,
    requested_depth: str = "light",
    project_identity_depth: str = "light",
    refresh: bool = True,
) -> ImprintSignalSnapshot:
    resolved_requested_depth = normalize_identity_depth(requested_depth)
    resolved_project_identity_depth = normalize_identity_depth(
        project_identity_depth
    )
    settings = iddb_settings_service.get_user_settings(user_id)
    normalized_settings = {
        "memory_mode": str(settings.get("memory_mode") or "deep")
        .strip()
        .lower(),
        "diary_requires_unlock": bool(
            settings.get("diary_requires_unlock", False)
        ),
        "allow_sensitive_modeling": bool(
            settings.get("allow_sensitive_modeling", False)
        ),
        "requested_depth": resolved_requested_depth,
        "project_identity_depth": resolved_project_identity_depth,
    }

    if refresh:
        user_global_state = imprint_fold_service.refresh_user_global_state(
            user_id,
            project_identity_depth=resolved_project_identity_depth,
        )
        project_state = (
            imprint_fold_service.refresh_project_state(
                user_id,
                project_id,
                project_identity_depth=resolved_project_identity_depth,
            )
            if project_id is not None
            else None
        )
    else:
        user_global_state = imprint_fold_service.get_scope_state(
            user_id,
            None,
            imprint_fold_service.SCOPE_USER_GLOBAL,
        )
        project_state = (
            imprint_fold_service.get_scope_state(
                user_id,
                project_id,
                imprint_fold_service.SCOPE_PROJECT_SCOPED,
            )
            if project_id is not None
            else None
        )
        if user_global_state is None:
            user_global_state = imprint_fold_service.refresh_user_global_state(
                user_id,
                project_identity_depth=resolved_project_identity_depth,
            )
        if project_id is not None and project_state is None:
            project_state = imprint_fold_service.refresh_project_state(
                user_id,
                project_id,
                project_identity_depth=resolved_project_identity_depth,
            )

    folded_state = {
        "user_global": _scope_bundle(user_global_state),
        "project_scoped": _scope_bundle(project_state),
    }
    effective_state = imprint_fold_service.merge_fold_states(
        user_global_state,
        project_state,
    )

    scope_kind = (
        imprint_fold_service.SCOPE_PROJECT_SCOPED
        if project_id is not None
        else imprint_fold_service.SCOPE_USER_GLOBAL
    )
    return ImprintSignalSnapshot(
        snapshot_version=SNAPSHOT_VERSION,
        builder_version=SNAPSHOT_BUILDER_VERSION,
        user_id=user_id,
        project_id=project_id,
        scope_kind=scope_kind,
        requested_depth=resolved_requested_depth,
        project_identity_depth=resolved_project_identity_depth,
        settings=normalized_settings,
        folded_state=folded_state,
        effective_state=effective_state,
    )


__all__ = [
    "SNAPSHOT_BUILDER_VERSION",
    "SNAPSHOT_VERSION",
    "build_imprint_signal_snapshot",
]
