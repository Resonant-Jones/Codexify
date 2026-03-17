"""Canonical facade for service-plugin discovery and invocation."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from threading import Lock
from typing import Any

import requests

from guardian.plugin_loader import plugin_loader as _runtime_plugin_loader
from guardian.plugins.plugin_loader import load_all_manifests
from guardian.plugins.plugin_manifest import PluginManifest

logger = logging.getLogger(__name__)

_RUNTIME_LOADER_LOCK = Lock()

HEALTH_TIMEOUT_SECONDS = 2
INVOKE_TIMEOUT_SECONDS = 10
_PROTOCOL_VERSION = "1.0"


@dataclass
class PluginFacadeError(Exception):
    """Stable facade error for plugin discovery and invocation failures."""

    code: str
    message: str

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.code}: {self.message}"


def get_runtime_plugin_loader():
    """Return the singleton legacy runtime plugin loader instance."""
    return _runtime_plugin_loader


def load_runtime_plugins():
    """Load runtime plugins once for compatibility with legacy callers."""
    loader = get_runtime_plugin_loader()
    with _RUNTIME_LOADER_LOCK:
        if not getattr(loader, "plugins", {}):
            loader.load_all_plugins()
    return loader


def list_plugin_manifests() -> list[PluginManifest]:
    """Return installed plugins from canonical validated manifest discovery."""
    return load_all_manifests()


def get_plugin_manifest_by_id(plugin_id: str) -> PluginManifest | None:
    """Return the installed manifest for a plugin id."""
    for manifest in list_plugin_manifests():
        if manifest.id == plugin_id:
            return manifest
    return None


def find_plugins_by_capability_action(
    capability: str,
    action: str,
) -> list[PluginManifest]:
    """Return manifests that advertise a callable (capability, action) pair."""
    return [
        manifest
        for manifest in list_plugin_manifests()
        if manifest.supports_operation(capability, action)
    ]


def get_plugin_manifest_by_capability(capability: str) -> PluginManifest | None:
    """Compatibility helper for legacy TTS lookup by capability id only."""
    wanted = capability.strip()
    if not wanted:
        return None

    for manifest in list_plugin_manifests():
        if any(cap.id == wanted for cap in manifest.capabilities):
            return manifest
    return None


def _invoke_url(base_url: str) -> str:
    return f"{base_url}/invoke"


def _health_url(base_url: str) -> str:
    return f"{base_url}/health"


def _build_context(context: dict[str, Any] | None) -> dict[str, Any]:
    defaults = {"request_id": "", "thread_id": None, "user_id": None}
    if context:
        defaults.update(context)
    return defaults


def _build_envelope(
    *,
    plugin_id: str,
    capability: str,
    action: str,
    input: dict[str, Any],
    context: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "protocol_version": _PROTOCOL_VERSION,
        "plugin_id": plugin_id,
        "capability": capability,
        "action": action,
        "input": input,
        "context": _build_context(context),
    }


def _normalize_response(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise PluginFacadeError(
            code="invalid_response",
            message="plugin response must be a JSON object",
        )
    if "ok" not in payload:
        raise PluginFacadeError(
            code="invalid_response",
            message="plugin response missing 'ok'",
        )
    if payload["ok"] is True:
        return payload
    if payload["ok"] is False:
        raise PluginFacadeError(
            code="remote_error",
            message=str(payload.get("error") or "plugin reported an error"),
        )
    raise PluginFacadeError(
        code="invalid_response",
        message="plugin response field 'ok' must be a boolean",
    )


def _safe_json(response: requests.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except (ValueError, json.JSONDecodeError) as exc:
        raise PluginFacadeError(
            code="invalid_response",
            message=f"plugin returned malformed JSON: {exc}",
        ) from exc
    return _normalize_response(payload)


def invoke_plugin(
    plugin_id: str,
    capability: str,
    action: str,
    input: dict[str, Any],
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Invoke a specific plugin service endpoint using the canonical envelope."""
    manifest = get_plugin_manifest_by_id(plugin_id)
    if manifest is None:
        raise PluginFacadeError(
            code="not_found",
            message=f"plugin '{plugin_id}' not found",
        )
    if not manifest.supports_operation(capability, action):
        raise PluginFacadeError(
            code="not_found",
            message=(
                f"plugin '{plugin_id}' does not support "
                f"{capability}/{action}"
            ),
        )

    envelope = _build_envelope(
        plugin_id=plugin_id,
        capability=capability,
        action=action,
        input=input,
        context=context,
    )

    try:
        response = requests.post(
            _invoke_url(manifest.base_url),
            json=envelope,
            timeout=INVOKE_TIMEOUT_SECONDS,
        )
    except requests.Timeout as exc:
        raise PluginFacadeError(
            code="timeout",
            message=f"plugin invoke timed out for '{plugin_id}'",
        ) from exc
    except requests.RequestException as exc:
        raise PluginFacadeError(
            code="transport_failure",
            message=f"plugin invoke transport failure for '{plugin_id}'",
        ) from exc

    return _safe_json(response)


def invoke_capability(
    capability: str,
    action: str,
    input: dict[str, Any],
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Invoke a capability/action pair when exactly one plugin supports it."""
    manifests = find_plugins_by_capability_action(capability, action)
    if not manifests:
        raise PluginFacadeError(
            code="not_found",
            message=f"no plugin found for {capability}/{action}",
        )
    if len(manifests) > 1:
        plugin_ids = ", ".join(sorted(manifest.id for manifest in manifests))
        raise PluginFacadeError(
            code="ambiguous",
            message=f"multiple plugins found for {capability}/{action}: {plugin_ids}",
        )
    return invoke_plugin(manifests[0].id, capability, action, input, context)


def probe_plugin_health(plugin_id: str) -> dict[str, Any]:
    """Fetch /health metadata without affecting installation state."""
    manifest = get_plugin_manifest_by_id(plugin_id)
    if manifest is None:
        raise PluginFacadeError(code="not_found", message="plugin not found")

    try:
        response = requests.get(
            _health_url(manifest.base_url), timeout=HEALTH_TIMEOUT_SECONDS
        )
        return response.json()
    except requests.Timeout as exc:
        raise PluginFacadeError(
            code="timeout", message="health check timed out"
        ) from exc
    except requests.RequestException as exc:
        raise PluginFacadeError(
            code="transport_failure", message="health check failed"
        ) from exc
    except ValueError as exc:
        raise PluginFacadeError(
            code="invalid_response", message="health response is not JSON"
        ) from exc


__all__ = [
    "PluginFacadeError",
    "find_plugins_by_capability_action",
    "get_plugin_manifest_by_capability",
    "get_runtime_plugin_loader",
    "get_plugin_manifest_by_id",
    "invoke_capability",
    "invoke_plugin",
    "list_plugin_manifests",
    "load_runtime_plugins",
    "probe_plugin_health",
]
