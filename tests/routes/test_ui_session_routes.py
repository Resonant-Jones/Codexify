"""Tests for Redis-backed UI session cache routes."""

from __future__ import annotations

from guardian.queue.redis_queue import get_redis_client
from guardian.routes.ui_session import make_session_key


def _sample_state() -> dict:
    return {
        "userId": "user-1",
        "deviceId": "device-1",
        "tabs": [
            {
                "tabId": "tab-1",
                "threadId": "101",
                "title": "Alpha",
                "modelId": "default",
                "createdAt": "2026-02-14T00:00:00.000Z",
                "updatedAt": "2026-02-14T00:00:00.000Z",
            }
        ],
        "activeTabId": "tab-1",
        "drafts": {"tab-1": "draft"},
        "version": 1,
        "updatedAt": "2026-02-14T00:00:00.000Z",
    }


def test_ui_session_set_get_delete_round_trip(test_client):
    payload = {
        "user_id": "user-1",
        "device_id": "device-1",
        "ttl_seconds": 1200,
        "state": _sample_state(),
    }
    put_resp = test_client.put("/api/ui/session", json=payload)
    assert put_resp.status_code == 200
    assert put_resp.json()["ok"] is True

    get_resp = test_client.get(
        "/api/ui/session",
        params={"user_id": "user-1", "device_id": "device-1"},
    )
    assert get_resp.status_code == 200
    body = get_resp.json()
    assert body["ok"] is True
    assert body["state"] is not None
    assert body["state"]["activeTabId"] == "tab-1"
    assert body["state"]["tabs"][0]["modelId"] == "default"

    del_resp = test_client.delete(
        "/api/ui/session",
        params={"user_id": "user-1", "device_id": "device-1"},
    )
    assert del_resp.status_code == 200
    assert del_resp.json()["ok"] is True

    get_after_delete = test_client.get(
        "/api/ui/session",
        params={"user_id": "user-1", "device_id": "device-1"},
    )
    assert get_after_delete.status_code == 200
    assert get_after_delete.json()["state"] is None


def test_ui_session_patch_merges_existing_state(test_client):
    base = _sample_state()
    base["tabs"].append(
        {
            "tabId": "tab-2",
            "threadId": "202",
            "title": "Beta",
            "modelId": "gpt-oss",
            "createdAt": "2026-02-14T00:01:00.000Z",
            "updatedAt": "2026-02-14T00:01:00.000Z",
        }
    )
    put_resp = test_client.put(
        "/api/ui/session",
        json={
            "user_id": "user-2",
            "device_id": "device-2",
            "state": base,
        },
    )
    assert put_resp.status_code == 200

    patch_resp = test_client.patch(
        "/api/ui/session",
        json={
            "user_id": "user-2",
            "device_id": "device-2",
            "patch": {
                "activeTabId": "tab-2",
                "drafts": {"tab-2": "checkpoint"},
                "version": 2,
            },
        },
    )
    assert patch_resp.status_code == 200
    patch_body = patch_resp.json()
    assert patch_body["ok"] is True
    assert patch_body["state"]["activeTabId"] == "tab-2"
    assert patch_body["state"]["drafts"]["tab-2"] == "checkpoint"
    assert patch_body["state"]["tabs"][1]["tabId"] == "tab-2"

    get_resp = test_client.get(
        "/api/ui/session",
        params={"user_id": "user-2", "device_id": "device-2"},
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["state"]["activeTabId"] == "tab-2"


def test_ui_session_uses_versioned_namespaced_key(test_client):
    payload = {
        "user_id": "name with spaces",
        "device_id": "device:1",
        "state": _sample_state(),
    }
    put_resp = test_client.put("/api/ui/session", json=payload)
    assert put_resp.status_code == 200

    key = make_session_key("name with spaces", "device:1")
    assert key.startswith("ui:v1:")
    assert key.endswith(":session")

    redis_client = get_redis_client()
    raw = redis_client.get(key)
    assert raw is not None
