from __future__ import annotations

import os
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from guardian.intents import service as intent_service
from guardian.intents.contracts import (
    GuardianIntentDispatchResult,
    GuardianIntentRequest,
)
from guardian.routes import intents

_API_KEY = os.getenv("GUARDIAN_API_KEY", "test-key")


def _build_client() -> TestClient:
    app = FastAPI()
    app.include_router(intents.router)
    return TestClient(app)


def test_intent_dispatch_normalizes_and_routes_to_command_bus(
    monkeypatch,
) -> None:
    observed: dict[str, Any] = {}

    async def fake_dispatch(
        *,
        intent: GuardianIntentRequest,
        auth_subject: str,
        inbound_headers: dict[str, str],
        app: Any,
    ) -> Any:
        observed["intent"] = intent
        observed["auth_subject"] = auth_subject
        observed["inbound_headers"] = inbound_headers
        observed["app"] = app
        return GuardianIntentDispatchResult(
            intent_id=intent.intent_id,
            status="accepted",
            dispatch_target="command_bus",
            intent_kind=intent.intent_kind,
            source_surface=intent.source_surface,
            receipt_ref="run_123",
            downstream_result_json={"run_id": "run_123", "status": "queued"},
            execution_state="accepted",
            provenance_json={"intent_id": intent.intent_id},
        )

    monkeypatch.setattr(
        "guardian.intents.service.dispatch_guardian_intent",
        fake_dispatch,
    )

    client = _build_client()
    response = client.post(
        "/api/guardian/intents/dispatch",
        headers={"X-API-Key": _API_KEY},
        json={
            "actor": {"kind": "human", "id": "local"},
            "source_surface": "cli",
            "intent_kind": "command_bus.invoke",
            "target": {
                "command_id": "ping_ping_get",
                "arguments": {"path_params": {}, "query": {}, "headers": {}},
            },
            "policy": {
                "approval_required": False,
                "allow_write_execution": False,
                "metadata": {},
            },
            "scope": {"metadata": {}},
            "provenance_json": {"surface": "cli"},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "accepted"
    assert body["dispatch_target"] == "command_bus"
    assert body["receipt_ref"] == "run_123"
    assert observed["auth_subject"] == "local"
    assert observed["intent"].source_surface == "cli"
    assert observed["intent"].target.command_id == "ping_ping_get"


def test_intent_dispatch_blocks_when_approval_required_and_missing(
    monkeypatch,
) -> None:
    called = {"value": False}

    async def fake_dispatch(*_args: Any, **_kwargs: Any) -> Any:
        called["value"] = True
        raise AssertionError("dispatch should not run when blocked")

    monkeypatch.setattr(
        "guardian.intents.service.execute_invoke",
        fake_dispatch,
    )

    client = _build_client()
    response = client.post(
        "/api/guardian/intents/dispatch",
        headers={"X-API-Key": _API_KEY},
        json={
            "actor": {"kind": "human", "id": "local"},
            "source_surface": "chat",
            "intent_kind": "command_bus.invoke",
            "target": {
                "command_id": "ping_ping_get",
                "arguments": {"path_params": {}, "query": {}, "headers": {}},
            },
            "policy": {
                "approval_required": True,
                "allow_write_execution": False,
                "metadata": {},
            },
            "approval_state": "pending",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "blocked"
    assert body["rejection_reason"] == "approval_required"
    assert called["value"] is False


@pytest.mark.asyncio
async def test_intent_service_builds_command_bus_invoke_request(
    monkeypatch,
) -> None:
    observed: dict[str, Any] = {}

    async def fake_execute_invoke(
        *,
        payload: Any,
        auth_subject: str,
        inbound_headers: dict[str, str],
        store: Any,
        app: Any,
        execution_lane: str = "raw",
        allow_write_execution: bool = False,
        confirmation_granted: bool = False,
    ) -> dict[str, Any]:
        observed["payload"] = payload
        observed["auth_subject"] = auth_subject
        observed["inbound_headers"] = inbound_headers
        observed["store"] = store
        observed["app"] = app
        observed["execution_lane"] = execution_lane
        observed["allow_write_execution"] = allow_write_execution
        observed["confirmation_granted"] = confirmation_granted
        return {"run_id": "run_abc", "status": "queued"}

    monkeypatch.setattr(
        "guardian.intents.service.execute_invoke",
        fake_execute_invoke,
    )

    intent = GuardianIntentRequest(
        intent_id="intent_123",
        actor={"kind": "human", "id": "local"},
        source_surface="chat",
        target={
            "command_id": "ping_ping_get",
            "arguments": {"path_params": {}, "query": {}, "headers": {}},
            "idempotency_key": "intent-123",
        },
        policy={
            "approval_required": False,
            "allow_write_execution": False,
            "metadata": {"priority": "low"},
        },
        provenance_json={"surface": "chat"},
    )

    result = await intent_service.dispatch_guardian_intent(
        intent=intent,
        auth_subject="local",
        inbound_headers={"x-api-key": "test-key"},
        app=object(),
    )

    assert result.status == "accepted"
    assert result.receipt_ref == "run_abc"
    payload = observed["payload"]
    assert payload.command_id == "ping_ping_get"
    assert payload.idempotency_key == "intent-123"
    assert (
        payload.provenance_json["intent_envelope"]["intent_id"] == "intent_123"
    )
    assert observed["execution_lane"] == "tools"
    assert observed["allow_write_execution"] is False
    assert observed["confirmation_granted"] is False


@pytest.mark.asyncio
async def test_intent_service_builds_cron_job_create_request(
    monkeypatch,
) -> None:
    observed: dict[str, Any] = {}

    async def fake_create_cron_job(body: Any) -> dict[str, Any]:
        observed["body"] = body
        return {
            "id": 77,
            "name": body.name,
            "schedule": body.schedule,
            "job_type": body.job_type,
            "payload": body.payload,
            "is_enabled": body.is_enabled,
            "created_at": "2026-03-09T05:30:00Z",
            "updated_at": "2026-03-09T05:30:00Z",
        }

    monkeypatch.setattr(
        "guardian.routes.cron.create_cron_job",
        fake_create_cron_job,
    )

    intent = GuardianIntentRequest(
        intent_id="intent_cron_1",
        actor={"kind": "human", "id": "local"},
        source_surface="chat",
        intent_kind="cron.create",
        target={
            "name": "Daily pulse",
            "schedule": "@daily",
            "job_type": "noop",
            "payload": {"reference": "status/daily-pulse"},
            "is_enabled": True,
        },
        policy={
            "approval_required": False,
            "allow_write_execution": False,
            "metadata": {"priority": "low"},
        },
        provenance_json={"surface": "chat"},
    )

    result = await intent_service.dispatch_guardian_intent(
        intent=intent,
        auth_subject="local",
        inbound_headers={"x-api-key": "test-key"},
        app=object(),
    )

    assert result.status == "accepted"
    assert result.dispatch_target == "cron"
    assert result.receipt_ref == "cron_job_77"
    body = observed["body"]
    assert body.name == "Daily pulse"
    assert body.schedule == "@daily"
    assert body.job_type == "noop"
    assert body.payload == {"reference": "status/daily-pulse"}
