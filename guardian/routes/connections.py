"""Read-only Connections aggregation API for the Settings bay.

The Connections API is a projection seam, not a mutation authority:

- static catalog metadata comes from ``guardian.connections.catalog``;
- per-user setup state is derived from user-scoped channel config and
  ``oauth_connections`` rows plus provider-specific credential projections
  (safe fields only);
- runtime implementation truth is the catalog's code-proven
  ``implementation_state``;
- runtime authorization truth for inference entries is projected from
  ``guardian.core.provider_registry`` without changing it.

Existing subsystem mutation APIs (``/api/channels``, ``/api/connectors``,
inference provider configuration) remain authoritative. This router never
serializes credentials, tokens, or raw error text.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from guardian.connections.catalog import (
    ConnectionCatalogEntry,
    get_catalog,
    get_connection,
)
from guardian.connections.notion import credentials as notion_credentials
from guardian.core.dependencies import get_request_user_id, require_api_key
from guardian.db import models as db_models
from guardian.protocol_tokens import (
    ConnectionCategory,
    ConnectionSetupState,
    CONNECTION_CATEGORIES,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/connections",
    tags=["Connections"],
    dependencies=[Depends(require_api_key)],
)

_db: Any | None = None

_OAUTH_STATUS_TO_SETUP_STATE: dict[str, str] = {
    "connected": ConnectionSetupState.CONNECTED.value,
    "error": ConnectionSetupState.ERROR.value,
    "pending": ConnectionSetupState.AUTHENTICATING.value,
    "disconnected": ConnectionSetupState.CONFIGURED.value,
}

_NOTION_VALIDATION_TO_SETUP_STATE: dict[str, str] = {
    "unconfigured": ConnectionSetupState.NEEDS_SETUP.value,
    notion_credentials.VALIDATION_UNVALIDATED: ConnectionSetupState.CONFIGURED.value,
    notion_credentials.VALIDATION_VALID: ConnectionSetupState.CONNECTED.value,
    notion_credentials.VALIDATION_AUTHORIZATION_ERROR: ConnectionSetupState.ERROR.value,
    notion_credentials.VALIDATION_TRANSPORT_ERROR: ConnectionSetupState.ERROR.value,
    notion_credentials.VALIDATION_PROVIDER_ERROR: ConnectionSetupState.ERROR.value,
}


def configure_db(db: Any) -> None:
    """Inject a session-providing DB wrapper (test seam; mirrors channels)."""
    global _db
    _db = db


def _get_db() -> Any | None:
    if _db is not None:
        return _db
    try:
        from guardian.core import dependencies as core_dependencies

        return getattr(core_dependencies, "chatlog_db", None)
    except Exception:  # pragma: no cover - defensive import path
        return None


def _user_channel_configs(db: Any, user_id: str) -> set[str]:
    try:
        with db.get_session() as session:
            rows = (
                session.query(db_models.ChannelConfig)
                .filter_by(user_id=user_id)
                .all()
            )
            return {str(row.channel) for row in rows}
    except Exception as exc:  # pragma: no cover - DB degraded
        logger.warning(
            "[connections] channel config lookup failed kind=%s",
            exc.__class__.__name__,
        )
        return set()


def _sanitize_oauth_error_kind(status: str, last_error: str | None) -> str | None:
    """Bounded classification only; raw error text is never serialized."""
    if status == ConnectionSetupState.ERROR.value:
        # Only provider-owned, enumerated Google Drive codes may be exposed.
        # Existing generic OAuth rows can contain raw exception strings and
        # continue to collapse to the older generic classification.
        google_error_kinds = {
            "google_drive_authorization_failed",
            "google_drive_oauth_denied",
            "google_drive_refresh_required",
            "google_drive_oauth_transport_error",
            "google_drive_transport_error",
            "google_drive_oauth_provider_error",
            "google_drive_provider_error",
        }
        if last_error in google_error_kinds:
            return last_error
    if status == ConnectionSetupState.ERROR.value:
        return "provider_error"
    return None


def _user_oauth_rows(db: Any, user_id: str) -> dict[str, dict[str, Any]]:
    try:
        with db.get_session() as session:
            rows = (
                session.query(db_models.OAuthConnection)
                .filter_by(user_id=user_id)
                .all()
            )
    except Exception as exc:  # pragma: no cover - DB degraded
        logger.warning(
            "[connections] oauth lookup failed kind=%s", exc.__class__.__name__
        )
        return {}
    projected: dict[str, dict[str, Any]] = {}
    for row in rows:
        # Safe fields only: never access token columns.
        projected[str(row.provider)] = {
            "provider": str(row.provider),
            "mode": str(row.mode),
            "status": str(row.status),
            "scopes": list(row.scopes or []),
            "expires_at": (
                row.expires_at.isoformat() if row.expires_at else None
            ),
            "last_refresh_at": (
                row.last_refresh_at.isoformat() if row.last_refresh_at else None
            ),
            "error_kind": _sanitize_oauth_error_kind(
                str(row.status), str(row.last_error or "") or None
            ),
        }
    return projected


def _user_notion_validation(db: Any, user_id: str) -> dict[str, Any]:
    """Project only safe Notion credential state for the current user."""
    try:
        return notion_credentials.status_projection(db, user_id)
    except Exception as exc:  # pragma: no cover - DB degraded
        logger.warning(
            "[connections] notion credential lookup failed kind=%s",
            exc.__class__.__name__,
        )
        return {
            "configured": False,
            "state": "storage_unavailable",
            "last_validated_at": None,
        }


def _inference_authorization(
    entry: ConnectionCatalogEntry,
) -> dict[str, Any] | None:
    """Project provider-registry authorization truth for an inference entry."""
    if entry.category != ConnectionCategory.INFERENCE.value:
        return None
    registry_provider_id = entry.runtime_binding.registry_provider_id
    if not registry_provider_id:
        return {
            "registered": False,
            "registry_provider_id": None,
            "note": (
                "Not listed in the canonical provider registry; catalog "
                "visibility is not runtime authorization."
            ),
        }
    try:
        from guardian.core import provider_registry
        from guardian.core.config import Settings

        settings = Settings()
        governance = provider_registry.provider_governance(registry_provider_id)
        authorized = provider_registry.provider_authorized(
            registry_provider_id, settings
        )
        available, disabled_reason = provider_registry.provider_availability(
            registry_provider_id,
            settings,
            authorized=authorized,
        )
        return {
            "registered": True,
            "registry_provider_id": registry_provider_id,
            "governance_classification": governance.get(
                "governance_classification"
            ),
            "authorized": bool(authorized),
            "available": bool(available),
            "enabled": bool(authorized and available),
            "disabled_reason": (
                str(disabled_reason) if disabled_reason else None
            ),
        }
    except ValueError:
        # provider_governance raises for unlisted providers.
        return {
            "registered": False,
            "registry_provider_id": registry_provider_id,
            "note": (
                "Not listed in the canonical provider registry; catalog "
                "visibility is not runtime authorization."
            ),
        }
    except Exception as exc:  # pragma: no cover - registry evaluation failed
        logger.warning(
            "[connections] registry evaluation failed kind=%s",
            exc.__class__.__name__,
        )
        return {
            "registered": True,
            "registry_provider_id": registry_provider_id,
            "evaluation": "failed",
            "note": (
                "Provider registry evaluation is unavailable right now; "
                "no authorization claim is made."
            ),
        }


def _resolve_setup_state(
    entry: ConnectionCatalogEntry,
    *,
    channel_configs: set[str],
    oauth_rows: dict[str, dict[str, Any]],
    notion_validation: dict[str, Any] | None,
    inference_authorization: dict[str, Any] | None,
) -> str:
    """Resolve per-user setup state without ever implying live health."""
    if entry.implementation_state == "unimplemented":
        return ConnectionSetupState.UNAVAILABLE.value

    if entry.id == "notion":
        validation_state = str((notion_validation or {}).get("state") or "")
        return _NOTION_VALIDATION_TO_SETUP_STATE.get(
            validation_state, ConnectionSetupState.ERROR.value
        )

    oauth_key = entry.oauth_provider_key
    if oauth_key and oauth_key in oauth_rows:
        status = str(oauth_rows[oauth_key].get("status") or "")
        return _OAUTH_STATUS_TO_SETUP_STATE.get(
            status, entry.default_setup_state
        )

    if entry.category == ConnectionCategory.MESSAGING.value:
        if entry.id in channel_configs:
            return ConnectionSetupState.CONFIGURED.value
        return entry.default_setup_state

    if (
        entry.category == ConnectionCategory.INFERENCE.value
        and inference_authorization is not None
    ):
        if inference_authorization.get("registered"):
            authorized = inference_authorization.get("authorized")
            if authorized is None:
                return entry.default_setup_state
            if not authorized:
                return ConnectionSetupState.NEEDS_SETUP.value
            if not inference_authorization.get("available"):
                return ConnectionSetupState.ERROR.value
            return ConnectionSetupState.CONFIGURED.value
        return entry.default_setup_state

    return entry.default_setup_state


def _project_entry(
    entry: ConnectionCatalogEntry,
    *,
    channel_configs: set[str],
    oauth_rows: dict[str, dict[str, Any]],
    notion_validation: dict[str, Any] | None,
) -> dict[str, Any]:
    inference_authorization = _inference_authorization(entry)
    item = entry.as_dict()
    item["setup_state"] = _resolve_setup_state(
        entry,
        channel_configs=channel_configs,
        oauth_rows=oauth_rows,
        notion_validation=notion_validation,
        inference_authorization=inference_authorization,
    )
    oauth_key = entry.oauth_provider_key
    if oauth_key:
        item["oauth"] = {
            "supported": bool(
                entry.runtime_binding.oauth_backend_handler_exists
            ),
            "backend_handler_exists": (
                entry.runtime_binding.oauth_backend_handler_exists
            ),
            "connection": oauth_rows.get(oauth_key),
            "launchable": False,
            "node_configured": False,
        }
        if entry.runtime_binding.oauth_backend_handler_exists:
            item["oauth"]["launchable"] = _oauth_launchable(entry)
            item["oauth"]["node_configured"] = item["oauth"]["launchable"]
            if not item["oauth"]["launchable"]:
                # A node without legitimate OAuth application configuration
                # must surface unavailable, even though the backend handler
                # exists in code.
                item["setup_state"] = ConnectionSetupState.UNAVAILABLE.value
    else:
        item["oauth"] = None
    item["validation"] = notion_validation if entry.id == "notion" else None
    item["authorization"] = inference_authorization
    return item


def _oauth_launchable(entry: ConnectionCatalogEntry) -> bool:
    """Return True iff this entry's OAuth setup can actually launch on this node."""

    if not entry.runtime_binding.oauth_backend_handler_exists:
        return False
    if entry.id == "minimax_oauth":
        try:
            from guardian.connectors.minimax import node_oauth_configured

            return bool(node_oauth_configured())
        except Exception:  # pragma: no cover - defensive
            return False
    if entry.id == "google_drive":
        try:
            from guardian.connections.google_drive.oauth import node_oauth_configured

            return bool(node_oauth_configured())
        except Exception:  # pragma: no cover - defensive
            return False
    # Generic rule for future entries: a setup route must exist. The rule
    # is intentionally conservative so future entries do not become
    # accidentally clickable merely because a backend handler exists.
    return bool(entry.runtime_binding.setup_route)


def _project_all(user_id: str) -> list[dict[str, Any]]:
    db = _get_db()
    channel_configs: set[str] = set()
    oauth_rows: dict[str, dict[str, Any]] = {}
    notion_validation: dict[str, Any] | None = None
    if db is not None:
        channel_configs = _user_channel_configs(db, user_id)
        oauth_rows = _user_oauth_rows(db, user_id)
        notion_validation = _user_notion_validation(db, user_id)
    return [
        _project_entry(
            entry,
            channel_configs=channel_configs,
            oauth_rows=oauth_rows,
            notion_validation=notion_validation,
        )
        for entry in get_catalog()
    ]


@router.get("")
def list_connections(user_id: str = Depends(get_request_user_id)) -> dict:
    """List the canonical Connections catalog with per-user state merged."""
    return {
        "categories": sorted(CONNECTION_CATEGORIES),
        "items": _project_all(user_id),
    }


@router.get("/{connection_id}")
def get_connection_details(
    connection_id: str,
    user_id: str = Depends(get_request_user_id),
) -> dict:
    """Return one catalog entry with per-user state merged."""
    entry = get_connection(connection_id)
    if entry is None:
        raise HTTPException(
            status_code=404, detail={"error": "Connection not found"}
        )
    db = _get_db()
    channel_configs: set[str] = set()
    oauth_rows: dict[str, dict[str, Any]] = {}
    notion_validation: dict[str, Any] | None = None
    if db is not None:
        channel_configs = _user_channel_configs(db, user_id)
        oauth_rows = _user_oauth_rows(db, user_id)
        notion_validation = _user_notion_validation(db, user_id)
    return _project_entry(
        entry,
        channel_configs=channel_configs,
        oauth_rows=oauth_rows,
        notion_validation=notion_validation,
    )
