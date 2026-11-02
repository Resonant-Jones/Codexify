"""Canonical mounted-route visibility authority.

Guardian has exactly one authority for what is mounted: the application's
routes. Two consumers project that authority with different visibility
policies:

* the **public** OpenAPI document, which exposes public routes only;
* the **Command Bus** manifest, which exposes public routes plus the
  internal-only routes that are *explicitly* marked command-visible.

Both projections are computed from the same mounted routes, so a route cannot
be visible to one consumer and unknown to the other by accident, and there is
no second command registry to drift out of sync. Command visibility is a
property of the route, declared once, where the route is declared.

Internal-only routes stay internal-only in every deployment. A route mounted
under an internal-only posture is hidden from the public document and is
refused by the public-exposure middleware for **every** caller, including the
Command Bus loopback. Marking a route command-visible therefore does not make
it reachable: it only makes it *discoverable* to the Command Bus, which still
has to authenticate and authorize the call before anything executes.

Mounting alone is never sufficient for command visibility. An internal-only
route family that is mounted but not marked stays invisible to the Command Bus,
so an internal route cannot silently widen the agent-visible command surface.
"""

from __future__ import annotations

from typing import Any, Callable, Iterable

from fastapi import routing as fastapi_routing
from fastapi.openapi.utils import get_openapi

#: Attribute set on an endpoint to declare that its route is command-visible.
COMMAND_VISIBLE_ATTRIBUTE = "guardian_command_visible"

#: Keys used to cache the mounted-route schema on the application state.
_MOUNTED_SCHEMA_CACHE = "mounted_route_schema"
_MOUNTED_SCHEMA_FINGERPRINT = "mounted_route_schema_fingerprint"


def command_visible(func: Callable[..., Any] | None = None):
    """Mark a route as visible to the Command Bus manifest.

    Usable as ``@command_visible`` or ``@command_visible()``. The marker is set
    on the endpoint function, which survives router inclusion, so the declared
    intent travels with the route itself.
    """

    def _mark(target: Callable[..., Any]) -> Callable[..., Any]:
        setattr(target, COMMAND_VISIBLE_ATTRIBUTE, True)
        return target

    if func is None:
        return _mark
    return _mark(func)


def is_command_visible(obj: Any) -> bool:
    """Return whether an endpoint or route is marked command-visible."""

    return bool(getattr(obj, COMMAND_VISIBLE_ATTRIBUTE, False))


def iter_mounted_routes(app: Any):
    """Yield the effective mounted routes of an application.

    Recent FastAPI versions keep an included router as a single entry in
    ``app.routes`` and expand it on demand. This helper expands that entry so
    callers see the same route objects the OpenAPI document is built from,
    with their effective paths and endpoints.
    """

    routes = list(getattr(app, "routes", None) or [])
    iter_contexts = getattr(fastapi_routing, "iter_route_contexts", None)
    if iter_contexts is None:
        return routes
    return list(iter_contexts(routes))


def command_visible_paths(app: Any) -> frozenset[str]:
    """Return the mounted route paths that are explicitly command-visible."""

    paths: set[str] = set()
    for route in iter_mounted_routes(app):
        if not is_command_visible(getattr(route, "endpoint", None)):
            continue
        path = getattr(route, "path", None)
        if isinstance(path, str) and path:
            paths.add(path)
    return frozenset(paths)


def internal_only_paths(app: Any) -> frozenset[str]:
    """Return the mounted route paths hidden behind an internal-only posture."""

    state = getattr(app, "state", None)
    hidden = getattr(state, "supported_profile_hidden_paths", None)
    if not hidden:
        return frozenset()
    return frozenset(hidden)


def invalidate_mounted_route_schema(app: Any) -> None:
    """Drop the cached mounted-route schema after the route set changes."""

    state = getattr(app, "state", None)
    if state is None:
        return
    try:
        setattr(state, _MOUNTED_SCHEMA_CACHE, None)
        setattr(state, _MOUNTED_SCHEMA_FINGERPRINT, None)
    except Exception:  # pragma: no cover - defensive, app state is writable
        pass


def hide_paths(app: Any, paths: Iterable[str]) -> None:
    """Record mounted paths as internal-only.

    A hidden path is removed from the public OpenAPI document and is refused
    by the public-exposure middleware for every caller, including the Command
    Bus loopback.
    """

    state = getattr(app, "state", None)
    if state is None:
        return
    hidden = getattr(state, "supported_profile_hidden_paths", None)
    if hidden is None:
        hidden = set()
        state.supported_profile_hidden_paths = hidden
    for path in paths:
        if isinstance(path, str) and path:
            hidden.add(path)
    app.openapi_schema = None
    invalidate_mounted_route_schema(app)


def _route_fingerprint(app: Any) -> tuple[tuple[Any, ...], ...]:
    """Return a cheap fingerprint of the mounted route set.

    The mounted-route schema is cached, because the Command Bus builds its
    manifest on every invocation. The fingerprint makes the cache follow the
    route set instead of assuming the routes never change after the first
    build, so a route mounted later cannot be missing from the manifest.
    """

    fingerprint: list[tuple[Any, ...]] = []
    for route in iter_mounted_routes(app):
        endpoint = getattr(route, "endpoint", None)
        methods = getattr(route, "methods", None) or ()
        fingerprint.append(
            (
                getattr(route, "path", None),
                id(endpoint),
                tuple(sorted(str(method) for method in methods)),
            )
        )
    return tuple(fingerprint)


def build_mounted_route_schema(app: Any) -> dict[str, Any]:
    """Return the OpenAPI document derived from every mounted route.

    This is the canonical projection of the mounted routes. It contains
    internal-only routes, because hiding them is a *visibility policy* applied
    by the consumer, not a property of the route set itself.
    """

    state = getattr(app, "state", None)
    fingerprint = _route_fingerprint(app)
    cached = getattr(state, _MOUNTED_SCHEMA_CACHE, None) if state is not None else None
    cached_fingerprint = (
        getattr(state, _MOUNTED_SCHEMA_FINGERPRINT, None)
        if state is not None
        else None
    )
    if cached is not None and cached_fingerprint == fingerprint:
        return cached

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    if state is not None:
        try:
            setattr(state, _MOUNTED_SCHEMA_CACHE, schema)
            setattr(state, _MOUNTED_SCHEMA_FINGERPRINT, fingerprint)
        except Exception:  # pragma: no cover - defensive, app state is writable
            pass
    return schema


def build_public_route_schema(app: Any) -> dict[str, Any]:
    """Return the public OpenAPI projection of the mounted routes.

    Internal-only paths are removed. The mounted-route schema itself is never
    mutated and never handed out, so the Command Bus projection stays intact
    and the public document cannot be edited in place by one consumer and
    observed changed by another.
    """

    raw = build_mounted_route_schema(app)
    hidden = internal_only_paths(app)
    paths = raw.get("paths", {}) or {}
    visible_paths = {
        path: path_item for path, path_item in paths.items() if path not in hidden
    }
    return {**raw, "paths": visible_paths}
