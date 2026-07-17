"""Tests for continuity operator reality commit readback route."""

from __future__ import annotations

import ast
import inspect
import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


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


def test_commit_readback_response_shape():
    from guardian.routes.continuity_operator import RealityCommitReadbackResponse

    r = RealityCommitReadbackResponse(
        commit_id="c1", found=True, state_id="s1", schema_version="1.0",
        committed_at="2026-01-01T00:00:00Z", summary="test",
        change_reason="manual", actor={"user_id": "u"},
        metadata={}, provenance={"pids": []}, deleted=False,
        graph_used=False, runtime_event_published=False,
        project_pulse_enabled=False, export_restore_enabled=False,
        read_at="2026-01-01T00:00:00Z",
    )
    assert r.graph_used is False
    assert r.runtime_event_published is False
    assert r.project_pulse_enabled is False
    assert r.export_restore_enabled is False


def test_missing_commit_response():
    from guardian.routes.continuity_operator import RealityCommitReadbackResponse

    r = RealityCommitReadbackResponse(commit_id="x", found=False)
    assert r.found is False


# ── 3. Route behavior via TestClient ────────────────────────────────────────


def test_commit_readback_existing(mock_readback_deps):
    with patch("guardian.routes.continuity_operator.get_database_dsn",
               return_value="sqlite+pysqlite:///:memory:"), \
         patch("guardian.routes.continuity_operator.Session") as mk:
        mk.return_value.query.return_value.filter.return_value.first.return_value = \
            _make_mock_commit_row("commit-1")

        from fastapi import FastAPI
        from guardian.routes.continuity_operator import router
        app = FastAPI(); app.include_router(router)
        app.dependency_overrides["require_api_key"] = lambda: "k"
        client = TestClient(app)

        r = client.get("/api/operator/continuity/reality-commits/commit-1")
        assert r.status_code == 200
        d = r.json()
        assert d["found"] is True
        assert d["commit_id"] == "commit-1"
        assert d["graph_used"] is False
        assert d["runtime_event_published"] is False
        assert d["project_pulse_enabled"] is False
        assert d["export_restore_enabled"] is False


def test_commit_readback_missing(mock_readback_deps):
    with patch("guardian.routes.continuity_operator.get_database_dsn",
               return_value="sqlite+pysqlite:///:memory:"), \
         patch("guardian.routes.continuity_operator.Session") as mk:
        mk.return_value.query.return_value.filter.return_value.first.return_value = None

        from fastapi import FastAPI
        from guardian.routes.continuity_operator import router
        app = FastAPI(); app.include_router(router)
        app.dependency_overrides["require_api_key"] = lambda: "k"
        client = TestClient(app)

        r = client.get("/api/operator/continuity/reality-commits/nonexistent")
        assert r.status_code == 200
        assert r.json()["found"] is False


# ── Mock helpers ────────────────────────────────────────────────────────────


def _make_mock_commit_row(commit_id: str):
    from unittest.mock import MagicMock
    from datetime import datetime, timezone
    row = MagicMock()
    row.id = commit_id
    row.schema_version = "1.0"
    row.kind = "state_update"
    row.trigger = "manual"
    row.title = "Test commit"
    row.summary = "A test commit"
    row.user_id = "local"
    row.new_state_id = "state-1"
    row.previous_state_id = None
    row.scope = "project"
    row.provenance_json = {"source_packet_ids": ["a"]}
    row.created_at = datetime(2026, 6, 25, tzinfo=timezone.utc)
    row.deleted_at = None
    return row


@pytest.fixture
def mock_readback_deps():
    pass


# ── 4. Live DB integration ──────────────────────────────────────────────────


@pytest.mark.integration
def test_live_commit_readback_roundtrip():
    from fastapi import FastAPI
    from guardian.routes.continuity_operator import router
    db_url = os.getenv("GUARDIAN_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not db_url or "sqlite" in db_url.lower():
        pytest.fail(
            "Live Continuity proof requires GUARDIAN_DATABASE_URL or DATABASE_URL "
            "for a disposable PostgreSQL database."
        )
    import uuid
    test_id = uuid.uuid4().hex[:12]
    commit_id = f"commit-live-{test_id}"

    app = FastAPI(); app.include_router(router)
    app.dependency_overrides["require_api_key"] = lambda: "k"

    import guardian.routes.continuity_operator as _route
    original = _route.get_database_dsn
    _route.get_database_dsn = lambda: db_url
    try:
        # Create a commit directly via SQL
        from sqlalchemy import create_engine, text
        engine = create_engine(db_url, echo=False)
        with engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO continuity_reality_commits
                (id, schema_version, scope, kind, "trigger", title, summary, user_id,
                 source_packet_ids_json, provenance_json, created_at)
                VALUES (:id, '0.1', 'project', 'state_update', 'manual', 'Proof commit',
                        'Live test', 'local', '[]', '{}', NOW())
            """), {"id": commit_id})
            conn.commit()

        client = TestClient(app)
        r = client.get(f"/api/operator/continuity/reality-commits/{commit_id}")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["found"] is True
        assert d["commit_id"] == commit_id
        assert d["graph_used"] is False
        assert d["runtime_event_published"] is False
        assert d["project_pulse_enabled"] is False
        assert d["export_restore_enabled"] is False
    finally:
        _route.get_database_dsn = original
