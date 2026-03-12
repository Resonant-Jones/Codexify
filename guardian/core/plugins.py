"""Canonical service plugin facade for discovery and invocation."""

from __future__ import annotations

import logging
import uuid
from threading import Lock
from typing import Any, Mapping

import requests

from guardian.plugin_loader import plugin_loader as _runtime_plugin_loader
from guardian.plugins.plugin_loader import (
    load_all_manifests as _load_manifest_plugins,
)
from guardian.plugins.plugin_manifest import PluginManifest

logger = logging.getLogger(__name__)

_RUNTIME_LOADER_LOCK = Lock()
HEALTH_TIMEOUT_SECONDS = 2.0
INVOKE_TIMEOUT_SECONDS = 10.0
PROTOCOL_VERSION = "1.0"

ERROR_NOT_FOUND = "not_found"
ERROR_AMBIGUOUS = "ambiguous"
ERROR_TIMEOUT = "timeout"
ERROR_TRANSPORT_FAILURE = "transport_failure"
ERROR_INVALID_RESPONSE = "invalid_response"
ERROR_REMOTE_ERROR = "remote_error"

_INVOKE_HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
}


class PluginFacadeError(RuntimeError):
    """Stable error surface for plugin facade consumers."""

    def __init__(
        self,
        *,
        code: str,
        message: str,
        plugin_id: str | None = None,
        capability: str | None = None,
        action: str | None = None,
        details: Any | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.plugin_id = plugin_id
        self.capability = capability
        self.action = action
        self.details = details

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "plugin_id": self.plugin_id,
            "capability": self.capability,
            "action": self.action,
            "details": self.details,
        }


def get_runtime_plugin_loader():
    """Return the singleton runtime plugin loader instance."""
    return _runtime_plugin_loader


def load_runtime_plugins():
    """
    Load runtime plugins through a single guarded entrypoint.

    Loader invocation is idempotent for non-empty registries to avoid
    accidental duplicate initialization across call sites.
    """
    loader = get_runtime_plugin_loader()
    with _RUNTIME_LOADER_LOCK:
        if not getattr(loader, "plugins", {}):
            loader.load_all_plugins()
    return loader


def list_plugin_manifests() -> list[PluginManifest]:
    """Return manifests validated via the canonical discovery path."""
    return _load_manifest_plugins()


def get_plugin_manifest_by_id(plugin_id: str) -> PluginManifest | None:
    """Return a plugin manifest by id from the centralized manifest list."""
    for manifest in list_plugin_manifests():
        if manifest.id == plugin_id:
            return manifest
    return None


def find_plugins_by_capability_action(
    capability: str, action: str
) -> list[PluginManifest]:
    """Return all plugins advertising the capability/action pair."""
    wanted_capability = capability.strip()
    wanted_action = action.strip()
    if not wanted_capability or not wanted_action:
        return []

    matches: list[PluginManifest] = []
    for manifest in list_plugin_manifests():
        if manifest.supports_operation(wanted_capability, wanted_action):
            matches.append(manifest)
    return matches


def _normalize_context(
    context: Mapping[str, Any] | None,
) -> dict[str, Any]:
    context = dict(context or {})
    request_id = context.get("request_id")
    if request_id is None or str(request_id).strip() == "":
        request_id = str(uuid.uuid4())

    return {
        "request_id": str(request_id),
        "thread_id": context.get("thread_id"),
        "user_id": context.get("user_id"),
    }


def _build_invoke_envelope(
    *,
    plugin_id: str,
    capability: str,
    action: str,
    input: Any,
    context: Mapping[str, Any] | None,
) -> dict[str, Any]:
    return {
        "protocol_version": PROTOCOL_VERSION,
        "plugin_id": plugin_id,
        "capability": capability,
        "action": action,
        "input": input,
        "context": _normalize_context(context),
    }


def _parse_response_payload(
    response: requests.Response,
    *,
    plugin_id: str,
    capability: str,
    action: str,
) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError as exc:
        raise PluginFacadeError(
            code=ERROR_INVALID_RESPONSE,
            message="Plugin response was not valid JSON",
            plugin_id=plugin_id,
            capability=capability,
            action=action,
            details={"status_code": response.status_code},
        ) from exc

    if not isinstance(payload, dict):
        raise PluginFacadeError(
            code=ERROR_INVALID_RESPONSE,
            message="Plugin response payload must be a JSON object",
            plugin_id=plugin_id,
            capability=capability,
            action=action,
            details={"status_code": response.status_code},
        )
    return payload


def _handle_transport_error(
    exc: Exception,
    *,
    plugin_id: str,
    capability: str,
    action: str,
) -> None:
    if isinstance(exc, requests.Timeout):
        raise PluginFacadeError(
            code=ERROR_TIMEOUT,
            message="Plugin invocation timed out",
            plugin_id=plugin_id,
            capability=capability,
            action=action,
        ) from exc

    raise PluginFacadeError(
        code=ERROR_TRANSPORT_FAILURE,
        message="Plugin transport failure",
        plugin_id=plugin_id,
        capability=capability,
        action=action,
        details=str(exc),
    ) from exc


def invoke_plugin(
    plugin_id: str,
    capability: str,
    action: str,
    input: Any,
    context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Invoke a specific plugin for a declared capability/action pair.
    """
    manifest = get_plugin_manifest_by_id(plugin_id)
    if manifest is None:
        raise PluginFacadeError(
            code=ERROR_NOT_FOUND,
            message=f"Plugin not found: {plugin_id}",
            plugin_id=plugin_id,
            capability=capability,
            action=action,
        )
    if not manifest.supports_operation(capability, action):
        raise PluginFacadeError(
            code=ERROR_NOT_FOUND,
            message=(
                "Plugin does not advertise capability/action pair: "
                f"{plugin_id} {capability}/{action}"
            ),
            plugin_id=plugin_id,
            capability=capability,
            action=action,
        )

    envelope = _build_invoke_envelope(
        plugin_id=plugin_id,
        capability=capability,
        action=action,
        input=input,
        context=context,
    )
    url = f"{manifest.base_url}/invoke"

    try:
        response = requests.post(
            url,
            json=envelope,
            headers=_INVOKE_HEADERS,
            timeout=INVOKE_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        _handle_transport_error(
            exc,
            plugin_id=plugin_id,
            capability=capability,
            action=action,
        )

    payload = _parse_response_payload(
        response,
        plugin_id=plugin_id,
        capability=capability,
        action=action,
    )

    if response.status_code >= 400:
        raise PluginFacadeError(
            code=ERROR_REMOTE_ERROR,
            message="Plugin returned an error response",
            plugin_id=plugin_id,
            capability=capability,
            action=action,
            details={
                "status_code": response.status_code,
                "error": payload.get("error"),
            },
        )

    if payload.get("error") not in (None, ""):
        raise PluginFacadeError(
            code=ERROR_REMOTE_ERROR,
            message="Plugin returned an application error",
            plugin_id=plugin_id,
            capability=capability,
            action=action,
            details=payload.get("error"),
        )

    if "ok" in payload and not isinstance(payload["ok"], bool):
        raise PluginFacadeError(
            code=ERROR_INVALID_RESPONSE,
            message="Plugin response field 'ok' must be boolean when present",
            plugin_id=plugin_id,
            capability=capability,
            action=action,
            details={"status_code": response.status_code},
        )

    if payload.get("ok") is False and payload.get("error") in (None, ""):
        raise PluginFacadeError(
            code=ERROR_INVALID_RESPONSE,
            message=(
                "Plugin response marked failure without canonical error payload"
            ),
            plugin_id=plugin_id,
            capability=capability,
            action=action,
            details={"status_code": response.status_code},
        )

    if "output" not in payload:
        raise PluginFacadeError(
            code=ERROR_INVALID_RESPONSE,
            message="Plugin response missing required 'output' field",
            plugin_id=plugin_id,
            capability=capability,
            action=action,
            details={"status_code": response.status_code},
        )
    if not isinstance(payload["output"], dict):
        raise PluginFacadeError(
            code=ERROR_INVALID_RESPONSE,
            message="Plugin response field 'output' must be an object",
            plugin_id=plugin_id,
            capability=capability,
            action=action,
            details={"status_code": response.status_code},
        )

    return payload


def get_plugin_health(plugin_id: str) -> dict[str, Any]:
    """
    Fetch liveness metadata from GET /health for a specific plugin.

    Health does not influence installation/discovery state.
    """
    manifest = get_plugin_manifest_by_id(plugin_id)
    if manifest is None:
        raise PluginFacadeError(
            code=ERROR_NOT_FOUND,
            message=f"Plugin not found: {plugin_id}",
            plugin_id=plugin_id,
        )

    url = f"{manifest.base_url}/health"
    try:
        response = requests.get(url, timeout=HEALTH_TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        _handle_transport_error(
            exc,
            plugin_id=plugin_id,
            capability="health",
            action="health",
        )

    payload = _parse_response_payload(
        response,
        plugin_id=plugin_id,
        capability="health",
        action="health",
    )
    if response.status_code >= 400:
        raise PluginFacadeError(
            code=ERROR_REMOTE_ERROR,
            message="Plugin health endpoint returned an error response",
            plugin_id=plugin_id,
            capability="health",
            action="health",
            details={
                "status_code": response.status_code,
                "error": payload.get("error"),
            },
        )
    return payload


def probe_plugin_health(plugin_id: str) -> dict[str, Any]:
    """Alias for get_plugin_health used by newer call sites."""
    return get_plugin_health(plugin_id)


def invoke_capability(
    capability: str,
    action: str,
    input: Any,
    context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Invoke by capability/action when exactly one plugin advertises it.
    """
    matches = find_plugins_by_capability_action(capability, action)
    if not matches:
        raise PluginFacadeError(
            code=ERROR_NOT_FOUND,
            message=(
                "No plugin advertises capability/action pair: "
                f"{capability}/{action}"
            ),
            capability=capability,
            action=action,
        )
    if len(matches) > 1:
        raise PluginFacadeError(
            code=ERROR_AMBIGUOUS,
            message=(
                "Multiple plugins advertise capability/action pair: "
                f"{capability}/{action}"
            ),
            capability=capability,
            action=action,
            details=[manifest.id for manifest in matches],
        )
    return invoke_plugin(
        matches[0].id,
        capability=capability,
        action=action,
        input=input,
        context=context,
    )


def get_plugin_manifest_by_capability(
    capability: str,
) -> PluginManifest | None:
    """
    Back-compat helper: return first plugin exposing any action for capability.
    """
    wanted = capability.strip().lower()
    if not wanted:
        return None

    for manifest in list_plugin_manifests():
        capability_ids = {
            decl.id.strip().lower() for decl in manifest.capabilities
        }
        if wanted in capability_ids:
            return manifest

    return None


__all__ = [
    "ERROR_AMBIGUOUS",
    "ERROR_INVALID_RESPONSE",
    "ERROR_NOT_FOUND",
    "ERROR_REMOTE_ERROR",
    "ERROR_TIMEOUT",
    "ERROR_TRANSPORT_FAILURE",
    "PluginFacadeError",
    "find_plugins_by_capability_action",
    "get_plugin_manifest_by_capability",
    "get_plugin_manifest_by_id",
    "get_plugin_health",
    "get_runtime_plugin_loader",
    "invoke_capability",
    "invoke_plugin",
    "list_plugin_manifests",
    "load_runtime_plugins",
    "probe_plugin_health",
]
