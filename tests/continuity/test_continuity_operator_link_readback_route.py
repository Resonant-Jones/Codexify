"""Tests for continuity operator state-packet link readback route."""

from __future__ import annotations

import ast
import inspect
import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


def _pg_available():
    db_url = os.getenv("GUARDIAN_DATABASE_URL") or os.getenv("DATABASE_URL")
    return bool(db_url) and "sqlite" not in db_url.lower()


def test_route_imports_no_runtime_modules():
    from guardian.routes import continuity_operator as co
    source = inspect.getsource(co)
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                for f in ["guardian.workers","guardian.queue","guardian.context","guardian.vector","guardian.core.ai_router","neo4j","redis"]:
                    assert alias.name != f and not alias.name.startswith(f+".")
        elif isinstance(node, ast.ImportFrom) and node.module:
            for f in ["guardian.workers","guardian.queue","guardian.context","guardian.vector","guardian.core.ai_router","neo4j","redis"]:
                assert node.module != f and not node.module.startswith(f+".")


def test_link_readback_response_shape():
    from guardian.routes.continuity_operator import StatePacketLinkReadbackResponse
    r = StatePacketLinkReadbackResponse(
        link_id="l1", found=True, state_id="s1", packet_id="p1",
        link_kind="contributed", created_at="2026-01-01T00:00:00Z",
        metadata={}, deleted=False,
        graph_used=False, runtime_event_published=False,
        project_pulse_enabled=False, export_restore_enabled=False,
        read_at="2026-01-01T00:00:00Z",
    )
    assert r.graph_used is False
    assert r.runtime_event_published is False
    assert r.project_pulse_enabled is False
    assert r.export_restore_enabled is False


def test_missing_link_response():
    from guardian.routes.continuity_operator import StatePacketLinkReadbackResponse
    r = StatePacketLinkReadbackResponse(link_id="x", found=False)
    assert r.found is False


def test_link_readback_existing():
    with patch("guardian.routes.continuity_operator.get_database_dsn",
               return_value="sqlite+pysqlite:///:memory:"), \
         patch("guardian.routes.continuity_operator.Session") as mk:
        from unittest.mock import MagicMock
        from datetime import datetime, timezone
        row = MagicMock()
        row.id = "link-1"; row.state_id = "s1"; row.packet_id = "p1"
        row.relationship = "contributed"
        row.created_at = datetime(2026,6,25,tzinfo=timezone.utc)
        mk.return_value.query.return_value.filter.return_value.first.return_value = row

        from fastapi import FastAPI
        from guardian.routes.continuity_operator import router
        app = FastAPI(); app.include_router(router)
        app.dependency_overrides["require_api_key"] = lambda: "k"
        client = TestClient(app)

        r = client.get("/api/operator/continuity/state-packet-links/link-1")
        assert r.status_code == 200
        d = r.json()
        assert d["found"] is True
        assert d["link_id"] == "link-1"
        assert d["state_id"] == "s1"
        assert d["packet_id"] == "p1"
        assert d["link_kind"] == "contributed"
        assert d["graph_used"] is False
        assert d["runtime_event_published"] is False
        assert d["project_pulse_enabled"] is False
        assert d["export_restore_enabled"] is False


def test_link_readback_missing():
    with patch("guardian.routes.continuity_operator.get_database_dsn",
               return_value="sqlite+pysqlite:///:memory:"), \
         patch("guardian.routes.continuity_operator.Session") as mk:
        mk.return_value.query.return_value.filter.return_value.first.return_value = None
        from fastapi import FastAPI
        from guardian.routes.continuity_operator import router
        app = FastAPI(); app.include_router(router)
        app.dependency_overrides["require_api_key"] = lambda: "k"
        client = TestClient(app)
        r = client.get("/api/operator/continuity/state-packet-links/nonexistent")
        assert r.status_code == 200
        assert r.json()["found"] is False


@pytest.mark.integration
@pytest.mark.skipif(not _pg_available(), reason="Postgres not available")
def test_live_link_readback_roundtrip():
    from fastapi import FastAPI
    from guardian.routes.continuity_operator import router
    db_url = os.getenv("GUARDIAN_DATABASE_URL") or os.getenv("DATABASE_URL")
    import uuid
    test_id = uuid.uuid4().hex[:12]
    link_id = f"link-live-{test_id}"

    app = FastAPI(); app.include_router(router)
    app.dependency_overrides["require_api_key"] = lambda: "k"

    import guardian.routes.continuity_operator as _route
    original = _route.get_database_dsn
    _route.get_database_dsn = lambda: db_url
    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(db_url, echo=False)
        with engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO continuity_state_packet_links
                (id, state_id, packet_id, relationship, created_at)
                VALUES (:id, 'state-x', 'pkt-x', 'contributed', NOW())
            """), {"id": link_id})
            conn.commit()

        client = TestClient(app)
        r = client.get(f"/api/operator/continuity/state-packet-links/{link_id}")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["found"] is True
        assert d["link_id"] == link_id
        assert d["state_id"] == "state-x"
        assert d["packet_id"] == "pkt-x"
        assert d["graph_used"] is False
        assert d["runtime_event_published"] is False
    finally:
        _route.get_database_dsn = original
