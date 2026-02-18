"""Tests for the durable events outbox and SSE replay."""

import asyncio
import contextlib
import importlib
import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

from guardian.connectors import github as github_module
from guardian.core import event_bus


def _require_chatlog_db_or_skip(ga: Any) -> None:
    db = getattr(ga, "chatlog_db", None)
    if db is None:
        pytest.skip("chatlog DB is not configured for this environment")
    try:
        db.list_events_after(0, limit=1)
    except Exception as exc:
        pytest.skip(f"chatlog DB is unavailable for integration test: {exc}")


def test_stream_events_preserves_outbox_rows(monkeypatch):
    monkeypatch.setenv("ENABLE_OUTBOX", "1")
    monkeypatch.setenv("ENABLE_BLIP_MODEL", "0")
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-key")

    import guardian.guardian_api as ga

    ga = importlib.reload(ga)

    events = [
        {
            "id": 11,
            "topic": "message.created",
            "payload": {"thread_id": 1, "message_id": 11},
        }
    ]

    def fake_fetch(
        last_id: int,
        limit: int = 100,
        tenant_id: str | None = None,
    ) -> list[dict[str, Any]]:
        _ = tenant_id
        return events if last_id < 11 else []

    def old_delete_api(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError(
            "legacy delete_events_up_to API should not be used"
        )

    monkeypatch.setattr(event_bus, "fetch_events_after", fake_fetch)
    monkeypatch.setattr(event_bus, "delete_events_up_to", old_delete_api)

    class _Request:
        async def is_disconnected(self) -> bool:
            return False

    async def _collect_first_payload() -> dict[str, Any]:
        response = await ga.stream_events(
            request=_Request(),
            last_id_query=0,
            last_event_id_header="0",
            api_key="test-key",
        )
        buffer = ""
        iterator = response.body_iterator.__aiter__()
        async for chunk in iterator:
            text = (
                chunk.decode()
                if isinstance(chunk, (bytes, bytearray))
                else str(chunk)
            )
            buffer += text
            while "\n\n" in buffer:
                frame, buffer = buffer.split("\n\n", 1)
                if not frame.strip() or frame.startswith("retry:"):
                    continue
                lines = frame.splitlines()
                data_line = next(
                    (line for line in lines if line.startswith("data:")),
                    None,
                )
                if data_line is None:
                    continue
                payload_str = data_line.split(":", 1)[1].strip() or "{}"
                # Advance the iterator once so the producer can run post-yield
                # cleanup logic before we close the stream.
                with contextlib.suppress(Exception):
                    await asyncio.wait_for(iterator.__anext__(), timeout=0.05)
                await response.body_iterator.aclose()
                return json.loads(payload_str)
        await response.body_iterator.aclose()
        raise AssertionError("expected at least one SSE payload")

    received = asyncio.run(_collect_first_payload())

    assert received == {"thread_id": 1, "message_id": 11}
    event_bus.reset()


def test_delete_events_up_to_aliases_delete_events_through():
    calls: list[tuple[int, str | None]] = []

    class _Store:
        def ensure_event_outbox(self) -> None:
            return None

        def delete_events_through(
            self, last_id: int, tenant_id: str | None = None
        ) -> None:
            calls.append((last_id, tenant_id))

    event_bus.reset()
    event_bus.configure_event_store(_Store())
    event_bus.delete_events_up_to(19, tenant_id="tenant-x")
    assert calls == [(19, "tenant-x")]
    event_bus.reset()


def test_events_outbox_replay_without_destructive_cleanup(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("GUARDIAN_DATABASE_URL", "")
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("GUARDIAN_DB_PATH", str(tmp_path / "guardian.db"))
    monkeypatch.setenv("ENABLE_OUTBOX", "1")
    monkeypatch.setenv("GUARDIAN_ENABLE_CONNECTOR_SYNC", "0")
    monkeypatch.setenv("ENABLE_BLIP_MODEL", "0")
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-key")

    import guardian.guardian_api as ga

    ga = importlib.reload(ga)
    _require_chatlog_db_or_skip(ga)

    with TestClient(ga.app) as client:
        event_bus.emit_event(
            "message.created",
            {
                "thread_id": 1,
                "message_id": 1,
                "role": "user",
                "content": "hi",
            },
        )

        received = None
        with client.stream(
            "GET",
            "/api/events",
            headers={"Last-Event-ID": "0", "X-API-Key": "test-key"},
        ) as stream:
            buffer = ""
            for chunk in stream.iter_raw():
                if not chunk:
                    continue
                buffer += chunk.decode()
                while "\n\n" in buffer:
                    frame, buffer = buffer.split("\n\n", 1)
                    if not frame.strip() or frame.startswith("retry:"):
                        continue
                    lines = frame.splitlines()
                    data_line = next(
                        (line for line in lines if line.startswith("data:")),
                        None,
                    )
                    if data_line is None:
                        continue
                    payload_str = data_line.split(":", 1)[1].strip() or "{}"
                    received = json.loads(payload_str)
                    break
                if received is not None:
                    break

        assert received == {
            "thread_id": 1,
            "message_id": 1,
            "role": "user",
            "content": "hi",
            "created_at": None,
            "message": {
                "id": 1,
                "thread_id": 1,
                "role": "user",
                "content": "hi",
                "created_at": None,
            },
        }
        remaining = ga.chatlog_db.list_events_after(0, limit=10)
        assert len(remaining) == 1
        assert remaining[0]["topic"] == "message.created"

    event_bus.reset()
    monkeypatch.delenv("GUARDIAN_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("GUARDIAN_DB_PATH", raising=False)
    monkeypatch.delenv("ENABLE_OUTBOX", raising=False)
    monkeypatch.delenv("GUARDIAN_ENABLE_CONNECTOR_SYNC", raising=False)
    monkeypatch.delenv("GUARDIAN_API_KEY", raising=False)
    importlib.reload(ga)


def test_github_connector_worker_stores_runs(tmp_path, monkeypatch):
    monkeypatch.setenv("GUARDIAN_DATABASE_URL", "")
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("GUARDIAN_DB_PATH", str(tmp_path / "guardian.db"))
    monkeypatch.setenv("ENABLE_OUTBOX", "1")
    monkeypatch.setenv("ENABLE_CONNECTOR_WORKER", "0")
    monkeypatch.setenv("ENABLE_BLIP_MODEL", "0")
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")

    import guardian.guardian_api as ga

    ga = importlib.reload(ga)
    _require_chatlog_db_or_skip(ga)

    created = ga.chatlog_db.create_connector_config(
        "github-test", "github", {"owner": "octocat", "repo": "hello-world"}
    )

    sample_docs = [
        {
            "external_id": "issue:1",
            "payload": {"kind": "issue", "data": {"number": 1}},
            "fetched_at": "2023-01-01T00:00:00+00:00",
        }
    ]

    monkeypatch.setattr(
        github_module, "sync_repo", lambda owner, repo, token: sample_docs
    )

    asyncio.run(ga._run_github_sync(created))

    last_run = ga.chatlog_db.get_last_connector_run(created["id"])
    assert last_run is not None
    assert last_run["status"] == "succeeded"

    docs = ga.chatlog_db.list_raw_documents_for_config(created["id"])
    assert len(docs) == 1
    assert docs[0]["payload"]["kind"] == "issue"

    events = ga.chatlog_db.list_events_after(0, limit=10)
    statuses = [event.get("payload", {}).get("status") for event in events]
    assert "succeeded" in statuses

    event_bus.reset()
    monkeypatch.delenv("GUARDIAN_DATABASE_URL", raising=False)
    importlib.reload(ga)
