"""Tests for developer/operator continuity write route."""

from __future__ import annotations

import ast
import inspect
import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


# ── 1. Import and registration safety ───────────────────────────────────────


def test_route_imports_no_runtime_modules():
    """Route module must not import provider, graph, worker, queue, or browser modules."""
    from guardian.routes import continuity_operator as co

    source = inspect.getsource(co)
    tree = ast.parse(source)

    forbidden = [
        "guardian.workers",
        "guardian.queue",
        "guardian.context",
        "guardian.vector",
        "guardian.core.ai_router",
        "neo4j",
        "redis",
        "requests",
        "httpx",
        "guardian.core.chat_completion_service",
        "guardian.cognition.system_prompt_builder",
    ]

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                for f in forbidden:
                    assert alias.name != f and not alias.name.startswith(
                        f + "."
                    ), f"route imports {alias.name!r}"
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                for f in forbidden:
                    assert node.module != f and not node.module.startswith(
                        f + "."
                    ), f"route imports-from {node.module!r}"


def test_route_imports_no_runtime_strings():
    from guardian.routes import continuity_operator as co

    source = inspect.getsource(co)
    # Skip docstrings when checking for forbidden strings
    lines = [
        ln for ln in source.splitlines()
        if not ln.strip().startswith(('"""', "'''", "#"))
    ]
    filtered = "\n".join(lines)
    forbidden = [
        "guardian.workers",
        "guardian.queue",
        "guardian.context",
        "guardian.vector",
        "guardian.core.ai_router",
        "neo4j",
        "redis",
    ]
    for word in forbidden:
        assert word not in filtered, f"route code contains '{word}'"


# ── 2. Request/response shape (via TestClient) ──────────────────────────────


def _valid_payload(**overrides) -> dict:
    defaults = {
        "action_id": "test-action-1",
        "actor_id": "test-actor",
        "packet_id": "test-pkt",
        "created_at": "2026-06-25T00:00:00Z",
        "summary": "Test stamp",
        "payload": {"test": True},
        "project_id": "test-proj",
    }
    defaults.update(overrides)
    return defaults


def test_stamp_success_response_shape():
    from guardian.continuity.write_actions import ContinuityWriteReceipt

    mock_receipt = ContinuityWriteReceipt(
        action_id="test-action-1",
        action_kind="create_reality_stamp",
        success=True,
        created_packet_ids=("rec-1",),
        provenance_refs=("test-pkt",),
        created_at="2026-06-25T00:00:00Z",
    )

    with patch(
        "guardian.routes.continuity_operator.get_database_dsn",
        return_value="sqlite+pysqlite:///:memory:",
    ), patch(
        "guardian.continuity.write_actions.ContinuityWriteActionService.create_reality_stamp",
        return_value=mock_receipt,
    ):
        from fastapi import FastAPI

        from guardian.routes.continuity_operator import router

        app = FastAPI()
        app.include_router(router)

        def override_api_key():
            return "test-key"

        app.dependency_overrides["require_api_key"] = override_api_key

        client = TestClient(app)
        response = client.post(
            "/api/operator/continuity/reality-stamp",
            json=_valid_payload(),
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["success"] is True
        assert data["action_kind"] == "create_reality_stamp"
        assert len(data["created_packet_ids"]) == 1
        assert data["graph_used"] is False
        assert data["runtime_event_published"] is False


def test_stamp_validation_failure():
    from guardian.continuity.write_actions import ContinuityWriteReceipt

    mock_receipt = ContinuityWriteReceipt(
        action_id="test-action-1",
        action_kind="create_reality_stamp",
        success=False,
        validation_errors=("bad summary",),
    )

    with patch(
        "guardian.routes.continuity_operator.get_database_dsn",
        return_value="sqlite+pysqlite:///:memory:",
    ), patch(
        "guardian.continuity.write_actions.ContinuityWriteActionService.create_reality_stamp",
        return_value=mock_receipt,
    ):
        from fastapi import FastAPI

        from guardian.routes.continuity_operator import router

        app = FastAPI()
        app.include_router(router)

        def override_api_key():
            return "test-key"

        app.dependency_overrides["require_api_key"] = override_api_key

        client = TestClient(app)
        response = client.post(
            "/api/operator/continuity/reality-stamp",
            json=_valid_payload(summary=""),
        )
        assert response.status_code == 400


def test_stamp_persistence_failure():
    from guardian.continuity.write_actions import ContinuityWriteReceipt

    mock_receipt = ContinuityWriteReceipt(
        action_id="test-action-1",
        action_kind="create_reality_stamp",
        success=False,
        persistence_errors=("db error",),
    )

    with patch(
        "guardian.routes.continuity_operator.get_database_dsn",
        return_value="sqlite+pysqlite:///:memory:",
    ), patch(
        "guardian.continuity.write_actions.ContinuityWriteActionService.create_reality_stamp",
        return_value=mock_receipt,
    ):
        from fastapi import FastAPI

        from guardian.routes.continuity_operator import router

        app = FastAPI()
        app.include_router(router)

        def override_api_key():
            return "test-key"

        app.dependency_overrides["require_api_key"] = override_api_key

        client = TestClient(app)
        response = client.post(
            "/api/operator/continuity/reality-stamp",
            json=_valid_payload(),
        )
        assert response.status_code == 500


# ── 3. Forbidden invocation paths ───────────────────────────────────────────


def test_route_does_not_import_chat_worker_or_graph():
    """Route module must not import chat runtime, workers, graph, or providers."""
    from guardian.routes import continuity_operator as co

    source = inspect.getsource(co)
    lines = [
        ln for ln in source.splitlines()
        if not ln.strip().startswith(('"""', "'''", "#"))
    ]
    filtered = "\n".join(lines)
    forbidden_modules = [
        "guardian.routes.chat",
        "guardian.workers",
        "guardian.queue",
        "guardian.context",
        "guardian.vector",
        "guardian.core.ai_router",
    ]
    for mod in forbidden_modules:
        assert mod not in filtered, f"route code contains forbidden module '{mod}'"


# ── 4. Live DB integration ──────────────────────────────────────────────────


def _pg_available():
    db_url = os.getenv("GUARDIAN_DATABASE_URL") or os.getenv("DATABASE_URL")
    return bool(db_url) and "sqlite" not in db_url.lower()


@pytest.mark.integration
@pytest.mark.skipif(not _pg_available(), reason="Postgres not available")
def test_live_stamp_route():
    """Full end-to-end test with live Postgres and real route."""
    from fastapi import FastAPI

    from guardian.routes.continuity_operator import router

    db_url = os.getenv("GUARDIAN_DATABASE_URL") or os.getenv("DATABASE_URL")

    app = FastAPI()
    app.include_router(router)

    def override_api_key():
        return "test-key"

    app.dependency_overrides["require_api_key"] = override_api_key

    # Patch get_database_dsn() at the import level within the route module
    import guardian.routes.continuity_operator as _route
    import uuid

    original = _route.get_database_dsn
    _route.get_database_dsn = lambda: db_url
    test_id = uuid.uuid4().hex[:12]
    try:
        client = TestClient(app)
        response = client.post(
            "/api/operator/continuity/reality-stamp",
            json=_valid_payload(
                action_id=f"live-route-{test_id}",
                packet_id=f"live-pkt-{test_id}",
                summary="Live route test",
            ),
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["success"] is True
        assert data["graph_used"] is False
        assert data["runtime_event_published"] is False
    finally:
        _route.get_database_dsn = original
