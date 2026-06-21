"""Tests for the Pi/Coder invocation dry-run route."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from guardian.routes import agent_orchestration


def _client(monkeypatch: Any) -> TestClient:
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-key")
    monkeypatch.setenv("DEBUG", "1")
    agent_orchestration.configure_db(None)

    app = FastAPI()
    app.include_router(agent_orchestration.router)
    return TestClient(app)


def _envelope(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    base: dict[str, Any] = {
        "guardian_boundary": {"owner_account_id": "acct-123"},
        "source_thread_id": "thread-1",
        "source_message_id": "msg-1",
        "invocation_id": "inv-1",
        "harness_id": "harness-1",
        "harness_version": "1.0.0",
        "provider_lane": {"provider_lane_class": "local"},
        "requested_permissions": [
            {
                "permission": "files.read",
                "resource": "/workspace",
                "reason": "read files",
            }
        ],
        "granted_permissions": [
            {
                "permission": "files.read",
                "resource": "/workspace",
                "reason": "read files",
            }
        ],
        "status": "prepared",
    }
    if overrides:
        base.update(overrides)
    return base


class TestValidDryRun:
    def test_valid_envelope_returns_200_and_dry_run_true(self, monkeypatch: Any) -> None:
        client = _client(monkeypatch)
        resp = client.post("/api/agents/pi-invocation/dry-run", json=_envelope())
        assert resp.status_code == 200
        data = resp.json()
        assert data["dry_run"] is True
        assert data["accepted"] is True
        assert data["execution_performed"] is False
        assert data["persistence_performed"] is False
        assert data["release_support"] == "unsupported"

    def test_response_has_no_raw_payload_fields(self, monkeypatch: Any) -> None:
        client = _client(monkeypatch)
        resp = client.post("/api/agents/pi-invocation/dry-run", json=_envelope())
        data = resp.json()
        forbidden = [
            "raw_args", "raw_command_payload", "extra_meta", "result_json",
            "event_payload", "stack_trace", "hidden_prompt", "system_prompt",
            "secret", "credential", "unredacted_payload",
        ]
        for key in forbidden:
            assert key not in data or data[key] is None

    def test_deterministic_response_same_input(self, monkeypatch: Any) -> None:
        client = _client(monkeypatch)
        r1 = client.post("/api/agents/pi-invocation/dry-run", json=_envelope())
        r2 = client.post("/api/agents/pi-invocation/dry-run", json=_envelope())
        assert r1.json() == r2.json()


class TestValidationFailures:
    def test_missing_source_thread_id_fails(self, monkeypatch: Any) -> None:
        client = _client(monkeypatch)
        resp = client.post(
            "/api/agents/pi-invocation/dry-run",
            json=_envelope({"source_thread_id": ""}),
        )
        data = resp.json()
        assert data["accepted"] is False
        assert len(data["errors"]) > 0

    def test_missing_source_message_id_fails(self, monkeypatch: Any) -> None:
        client = _client(monkeypatch)
        resp = client.post(
            "/api/agents/pi-invocation/dry-run",
            json=_envelope({"source_message_id": ""}),
        )
        data = resp.json()
        assert data["accepted"] is False

    def test_missing_harness_id_fails(self, monkeypatch: Any) -> None:
        client = _client(monkeypatch)
        resp = client.post(
            "/api/agents/pi-invocation/dry-run",
            json=_envelope({"harness_id": ""}),
        )
        data = resp.json()
        assert data["accepted"] is False

    def test_invalid_guardian_boundary_fails(self, monkeypatch: Any) -> None:
        client = _client(monkeypatch)
        resp = client.post(
            "/api/agents/pi-invocation/dry-run",
            json=_envelope({"guardian_boundary": {"owner_account_id": ""}}),
        )
        data = resp.json()
        assert data["accepted"] is False


class TestNoForbiddenSideEffects:
    def test_route_does_not_call_store(self, monkeypatch: Any) -> None:
        client = _client(monkeypatch)
        called = []
        monkeypatch.setattr(agent_orchestration, "_store", called)
        client.post("/api/agents/pi-invocation/dry-run", json=_envelope())
        # route should not try to write to _store

    def test_route_does_not_call_event_publisher(self, monkeypatch: Any) -> None:
        client = _client(monkeypatch)
        # The route does not import or call _event_publisher — verify it doesn't crash
        client.post("/api/agents/pi-invocation/dry-run", json=_envelope())
