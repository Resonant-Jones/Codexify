from __future__ import annotations

import json
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from guardian.routes import command_bus


def _build_client(monkeypatch) -> TestClient:
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-key")
    monkeypatch.setenv("DEBUG", "1")
    command_bus.configure_db(None)

    app = FastAPI()

    @app.post("/write", operation_id="write_item")
    def write(payload: dict[str, Any]) -> dict[str, Any]:
        return {"ok": True, "payload": payload}

    app.include_router(command_bus.router)
    return TestClient(app)


def _invoke_blocked_run(client: TestClient) -> str:
    manifest = client.get(
        "/api/guardian/commands/manifest",
        headers={"X-API-Key": "test-key", "X-User-Id": "operator"},
    ).json()
    command_id = None
    for command in manifest["commands"]:
        if command["method"] == "POST" and command["path_template"] == "/write":
            command_id = command["command_id"]
            break
    assert command_id is not None

    response = client.post(
        "/api/guardian/commands/invoke",
        headers={"X-API-Key": "test-key", "X-User-Id": "operator"},
        json={
            "invoke_version": "1.0",
            "command_id": command_id,
            "actor": {"kind": "human", "id": "operator"},
            "arguments": {"body": {"x": 1}},
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "blocked"
    return payload["run_id"]


class _FakeRequest:
    def __init__(self, disconnect_after: int = 2) -> None:
        self._checks = 0
        self._disconnect_after = disconnect_after

    async def is_disconnected(self) -> bool:
        self._checks += 1
        return self._checks > self._disconnect_after


async def _collect_events(
    run_id: str,
    after_seq: int,
    expected_count: int,
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    response = await command_bus.stream_run_events(
        run_id=run_id,
        request=_FakeRequest(disconnect_after=2),
        after_seq=after_seq,
    )
    buffer = ""
    async for chunk in response.body_iterator:
        text = (
            chunk.decode()
            if isinstance(chunk, (bytes, bytearray))
            else str(chunk)
        )
        buffer += text
        while "\n\n" in buffer:
            frame, buffer = buffer.split("\n\n", 1)
            if (
                not frame.strip()
                or frame.startswith("retry:")
                or frame.startswith(": ping")
            ):
                continue
            lines = frame.splitlines()
            id_line = next(
                (line for line in lines if line.startswith("id:")), None
            )
            event_line = next(
                (line for line in lines if line.startswith("event:")), None
            )
            data_line = next(
                (line for line in lines if line.startswith("data:")), None
            )
            if not (id_line and event_line and data_line):
                continue
            payload = json.loads(data_line.split(":", 1)[1].strip() or "{}")
            events.append(
                {
                    "id": int(id_line.split(":", 1)[1].strip()),
                    "event": event_line.split(":", 1)[1].strip(),
                    "data": payload,
                }
            )
            if len(events) >= expected_count:
                return events
    return events


@pytest.mark.asyncio
async def test_events_stream_order_and_resume(monkeypatch) -> None:
    client = _build_client(monkeypatch)
    run_id = _invoke_blocked_run(client)

    all_events = await _collect_events(
        run_id=run_id, after_seq=0, expected_count=2
    )
    assert [event["id"] for event in all_events] == [1, 2]
    assert [event["event"] for event in all_events] == [
        "run.created",
        "run.blocked",
    ]

    resumed_events = await _collect_events(
        run_id=run_id, after_seq=1, expected_count=1
    )
    assert [event["id"] for event in resumed_events] == [2]
    assert [event["event"] for event in resumed_events] == ["run.blocked"]
