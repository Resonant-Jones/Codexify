"""Loopback HTTP adapter for raw command execution."""

from __future__ import annotations

import os
import re
from typing import Any
from urllib.parse import quote, urlparse

import httpx

_PATH_TOKEN_RE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")
_FORWARDED_AUTH_HEADERS = ("authorization", "x-api-key", "x-user-id", "cookie")

RECURSION_BLOCKED_PREFIXES = (
    "/api/guardian/commands/",
    "/tools/",
    "/api/tools/",
)


def resolve_loopback_base() -> str:
    """Resolve deterministic loopback base URL for command execution."""
    raw = (os.getenv("GUARDIAN_COMMAND_BUS_LOOPBACK_BASE") or "").strip()
    if not raw:
        raise RuntimeError(
            "GUARDIAN_COMMAND_BUS_LOOPBACK_BASE is required for command bus loopback execution"
        )
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise RuntimeError(
            "GUARDIAN_COMMAND_BUS_LOOPBACK_BASE must be a valid absolute http(s) URL"
        )
    return raw.rstrip("/")


def render_path(path_template: str, path_params: dict[str, Any]) -> str:
    """Render OpenAPI path template from path params."""
    params = {str(k): v for k, v in (path_params or {}).items()}

    def _replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in params:
            raise ValueError(f"missing required path param '{name}'")
        return quote(str(params[name]), safe="")

    return _PATH_TOKEN_RE.sub(_replace, path_template)


def is_recursion_blocked(path: str) -> bool:
    normalized = "/" + str(path or "").lstrip("/")
    for prefix in RECURSION_BLOCKED_PREFIXES:
        if normalized.startswith(prefix):
            return True
    return False


async def execute_loopback_request(
    *,
    method: str,
    path_template: str,
    path_params: dict[str, Any],
    query: dict[str, Any],
    headers: dict[str, Any],
    body: Any,
    inbound_headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Execute raw command over loopback HTTP."""
    path = render_path(path_template, path_params)
    if is_recursion_blocked(path):
        raise RuntimeError("recursion_guard_blocked")

    base_url = resolve_loopback_base()
    url = f"{base_url}{path}"
    outbound_headers: dict[str, str] = {}

    for key, value in (inbound_headers or {}).items():
        if key.lower() in _FORWARDED_AUTH_HEADERS:
            outbound_headers[key] = value

    for key, value in (headers or {}).items():
        outbound_headers[str(key)] = str(value)

    kwargs: dict[str, Any] = {
        "method": method.upper(),
        "url": url,
        "params": query or None,
        "headers": outbound_headers or None,
        "timeout": 30.0,
    }
    if body is not None and method.upper() not in {"GET", "HEAD"}:
        kwargs["json"] = body

    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.request(**kwargs)

    content_type = (response.headers.get("content-type") or "").lower()
    parsed_body: Any
    if "application/json" in content_type:
        try:
            parsed_body = response.json()
        except Exception:
            parsed_body = {"raw": response.text}
    else:
        parsed_body = response.text

    return {
        "status_code": int(response.status_code),
        "headers": dict(response.headers),
        "body": parsed_body,
    }
