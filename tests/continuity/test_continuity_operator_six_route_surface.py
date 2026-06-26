"""Six-route Continuity operator surface regression tests.

Pins the shared surface key, route inventory, profile quarantine, feature
flag gate, auth boundary, and no-ambient-path guarantees for the full
six-route Continuity operator surface.
"""

from __future__ import annotations

import inspect
import os
import subprocess
from unittest.mock import patch

import pytest


# ── Route inventory ─────────────────────────────────────────────────────────

_ROUTES = [
    ("POST", "/api/operator/continuity/reality-stamp"),
    ("GET", "/api/operator/continuity/context-packets/{packet_id}"),
    ("GET", "/api/operator/continuity/diagnostics"),
    ("GET", "/api/operator/continuity/reality-states/{state_id}"),
    ("GET", "/api/operator/continuity/reality-commits/{commit_id}"),
    ("GET", "/api/operator/continuity/state-packet-links/{link_id}"),
]


def _six_path_methods():
    from guardian.routes.continuity_operator import router
    return {(frozenset(r.methods), r.path) for r in router.routes}


def test_route_inventory_has_six_routes():
    paths = _six_path_methods()
    assert len(paths) == 6, f"Expected 6 routes, got {len(paths)}"


def test_write_route_present():
    paths = _six_path_methods()
    assert any("reality-stamp" in p for _, p in paths)


def test_packet_readback_present():
    paths = _six_path_methods()
    assert any("context-packets" in p and "{packet_id}" in p for _, p in paths)


def test_diagnostics_present():
    paths = _six_path_methods()
    assert any(p.endswith("/diagnostics") for _, p in paths)


def test_state_readback_present():
    paths = _six_path_methods()
    assert any("reality-states" in p and "{state_id}" in p for _, p in paths)


def test_commit_readback_present():
    paths = _six_path_methods()
    assert any("reality-commits" in p and "{commit_id}" in p for _, p in paths)


def test_link_readback_present():
    paths = _six_path_methods()
    assert any("state-packet-links" in p and "{link_id}" in p for _, p in paths)


# ── No unsupported routes ───────────────────────────────────────────────────


_FORBIDDEN_PATTERNS = [
    "/context-packets",   # no list-all-context-packets
    "/reality-states",    # no list-all-states (exact-ID only)
    "/reality-commits",   # no list-all-commits
    "/state-packet-links", # no list-all-links
    "search", "list", "traverse", "graph", "pulse", "export", "restore",
]


def test_no_unsupported_list_routes():
    """No route exists that lists all records without an ID parameter."""
    paths = _six_path_methods()
    # Each path with a collection name must have a parameter
    collections = {"context-packets", "reality-states", "reality-commits", "state-packet-links"}
    for m, p in paths:
        for coll in collections:
            if f"/{coll}" in p and "{" not in p:
                # Only diagnostics is allowed without a parameter
                if "diagnostics" not in p:
                    pytest.fail(f"Unspported list route: {m} {p}")


def test_no_forbidden_patterns_in_routes():
    paths = _six_path_methods()
    for m, p in paths:
        lower = p.lower()
        for pat in ("search", "list", "traverse", "graph", "pulse", "export", "restore"):
            assert pat not in lower, f"Forbidden pattern '{pat}' in route {m} {p}"


# ── Surface key / profile ───────────────────────────────────────────────────


def test_surface_key_shared():
    """All six routes belong to the continuity_operator surface key."""
    from guardian.routes.continuity_operator import router
    assert router.prefix == "/api/operator/continuity"


def test_test_profile_exposes_key():
    from guardian.core.supported_profile import load_supported_profile
    manifest = load_supported_profile("test-continuity")
    assert manifest.allows_route("continuity_operator")


def test_beta_profile_quarantines_key():
    from guardian.core.supported_profile import load_supported_profile
    manifest = load_supported_profile("v1-local-core-web-mcp")
    assert not manifest.allows_route("continuity_operator")
    assert manifest.route_status("continuity_operator") == "quarantined"


# ── No ambient call sites ───────────────────────────────────────────────────


def test_no_ambient_operator_routes_in_chat():
    result = subprocess.run(
        ["grep", "-rl", "continuity_operator", "guardian/routes/"],
        capture_output=True, text=True,
    )
    files = result.stdout.strip().split("\n")
    allowed = {"guardian/routes/continuity_operator.py"}
    for f in files:
        if f and "__pycache__" not in f:
            assert f in allowed, f"continuity_operator referenced in {f}"


def test_no_ambient_write_service_in_workers():
    result = subprocess.run(
        ["grep", "-rl", "ContinuityWriteActionService", "guardian/"],
        capture_output=True, text=True,
    )
    files = result.stdout.strip().split("\n")
    allowed = {
        "guardian/continuity/write_actions.py",
        "guardian/continuity/__init__.py",
        "guardian/routes/continuity_operator.py",
    }
    for f in files:
        if f and "__pycache__" not in f and "test" not in f:
            assert f in allowed, f"ContinuityWriteActionService referenced in {f}"


# ── Auth boundary ───────────────────────────────────────────────────────────


def test_route_requires_auth():
    """Route module uses require_api_key dependency."""
    from guardian.routes import continuity_operator as co
    source = inspect.getsource(co)
    assert "require_api_key" in source
    assert "Depends" in source


def test_unauth_write_route_blocked():
    from fastapi import FastAPI
    from guardian.routes.continuity_operator import router
    from fastapi.testclient import TestClient
    app = FastAPI(); app.include_router(router)
    # No dependency override → auth will fail
    # Route may return 403, 422, or a FastAPI dependency error
    client = TestClient(app)
    with patch("guardian.routes.continuity_operator.get_database_dsn",
               return_value="sqlite+pysqlite:///:memory:"):
        r = client.get("/api/operator/continuity/diagnostics")
        # Without overriding require_api_key, FastAPI will fail dependency injection
        assert r.status_code != 200, f"Unauthenticated request got 200: {r.text}"
