"""Tests for continuity operator reality state readback route."""

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


# ── 1. Import and source safety ─────────────────────────────────────────────


def test_route_imports_no_runtime_modules():
    from guardian.routes import continuity_operator as co

    source = inspect.getsource(co)
    tree = ast.parse(source)
    forbidden = [
        "guardian.workers", "guardian.queue", "guardian.context",
        "guardian.vector", "guardian.core.ai_router", "neo4j", "redis",
        "requests", "httpx",
    ]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                for f in forbidden:
                    assert alias.name != f and not alias.name.startswith(f + ".")
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                for f in forbidden:
                    assert node.module != f and not node.module.startswith(f + ".")


# ── 2. Response model shape ─────────────────────────────────────────────────


def test_state_readback_response_shape():
    from guardian.routes.continuity_operator import RealityStateReadbackResponse

    r = RealityStateReadbackResponse(
        state_id="s1", found=True, schema_version="1.0", scope="project",
        compiled_at="2026-01-01T00:00:00Z", summary="test",
        state={"k": "v"}, metadata={}, provenance={"pids": []},
        source_packet_count=3, deleted=False,
        graph_used=False, runtime_event_published=False,
        project_pulse_enabled=False, export_restore_enabled=False,
        read_at="2026-01-01T00:00:00Z",
    )
    assert r.graph_used is False
    assert r.runtime_event_published is False
    assert r.project_pulse_enabled is False
    assert r.export_restore_enabled is False


def test_missing_state_response():
    from guardian.routes.continuity_operator import RealityStateReadbackResponse

    r = RealityStateReadbackResponse(state_id="x", found=False)
    assert r.found is False
    assert r.graph_used is False


# ── 3. Route behavior via TestClient ────────────────────────────────────────


def test_state_readback_existing(mock_readback_deps):
    with patch("guardian.routes.continuity_operator.get_database_dsn",
               return_value="sqlite+pysqlite:///:memory:"), \
         patch("guardian.routes.continuity_operator.Session") as mk:
        mk.return_value.query.return_value.filter.return_value.first.return_value = \
            _make_mock_state_row("state-1")

        from fastapi import FastAPI
        from guardian.routes.continuity_operator import router
        app = FastAPI(); app.include_router(router)
        app.dependency_overrides["require_api_key"] = lambda: "k"
        client = TestClient(app)

        r = client.get("/api/operator/continuity/reality-states/state-1")
        assert r.status_code == 200
        d = r.json()
        assert d["found"] is True
        assert d["state_id"] == "state-1"
        assert d["graph_used"] is False
        assert d["runtime_event_published"] is False
        assert d["project_pulse_enabled"] is False
        assert d["export_restore_enabled"] is False


def test_state_readback_missing(mock_readback_deps):
    with patch("guardian.routes.continuity_operator.get_database_dsn",
               return_value="sqlite+pysqlite:///:memory:"), \
         patch("guardian.routes.continuity_operator.Session") as mk:
        mk.return_value.query.return_value.filter.return_value.first.return_value = None

        from fastapi import FastAPI
        from guardian.routes.continuity_operator import router
        app = FastAPI(); app.include_router(router)
        app.dependency_overrides["require_api_key"] = lambda: "k"
        client = TestClient(app)

        r = client.get("/api/operator/continuity/reality-states/nonexistent")
        assert r.status_code == 200
        assert r.json()["found"] is False


# ── Mock helpers ────────────────────────────────────────────────────────────


def _make_mock_state_row(state_id: str):
    from unittest.mock import MagicMock
    from datetime import datetime, timezone
    row = MagicMock()
    row.id = state_id
    row.schema_version = "1.0"
    row.scope = "project"
    row.compiled_at = datetime(2026, 6, 25, tzinfo=timezone.utc)
    row.active_branch = "test-branch"
    row.state_json = {"compiled": True}
    row.provenance_json = {"source_packet_ids": ["a", "b", "c"]}
    row.source_packet_ids_json = ["a", "b", "c"]
    row.deleted_at = None
    return row


@pytest.fixture
def mock_readback_deps():
    pass


# ── 4. Live DB integration ──────────────────────────────────────────────────


@pytest.mark.skipif(not _pg_available(), reason="Postgres not available")
def test_live_state_readback_roundtrip():
    from fastapi import FastAPI
    from guardian.routes.continuity_operator import router
    db_url = os.getenv("GUARDIAN_DATABASE_URL") or os.getenv("DATABASE_URL")
    import uuid
    test_id = uuid.uuid4().hex[:12]

    app = FastAPI(); app.include_router(router)
    app.dependency_overrides["require_api_key"] = lambda: "k"

    import guardian.routes.continuity_operator as _route
    original = _route.get_database_dsn
    _route.get_database_dsn = lambda: db_url
    try:
        client = TestClient(app)

        # Write a stamp first, then compile+save a state
        pkt_id = f"state-rb-pkt-{test_id}"
        client.post("/api/operator/continuity/reality-stamp", json={
            "action_id": f"rb-{test_id}", "actor_id": "t", "packet_id": pkt_id,
            "created_at": "2026-06-25T00:00:00Z", "summary": "State RB test",
            "payload": {}, "project_id": "p",
        })

        # Compile state from the explicit packet
        from guardian.continuity.contracts import ContextPacket
        from guardian.continuity.compiler import compile_reality_state
        from guardian.continuity.persistence import ContinuityPersistenceAdapter
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session
        engine = create_engine(db_url, echo=False)
        session = Session(engine)
        adapter = ContinuityPersistenceAdapter(session)
        try:
            pkt = ContextPacket(packet_id=pkt_id, schema_version="1.0", kind="thread",
                scope=__import__("guardian.continuity.contracts", fromlist=["ContinuityScope"]).ContinuityScope(project_id="p"),
                source=__import__("guardian.continuity.contracts", fromlist=["ContinuitySource"]).ContinuitySource(system="test"),
                created_at="2026-06-25T00:00:00Z", summary="x")
            result = compile_reality_state([pkt], scope="project")
            adapter.save_reality_state(result.state)
            state_id = result.state.state_id

            # Now read back via the route
            r = client.get(f"/api/operator/continuity/reality-states/{state_id}")
            assert r.status_code == 200, r.text
            d = r.json()
            assert d["found"] is True
            assert d["graph_used"] is False
            assert d["runtime_event_published"] is False
            assert d["project_pulse_enabled"] is False
            assert d["export_restore_enabled"] is False
        finally:
            session.rollback()
            session.close()
    finally:
        _route.get_database_dsn = original
