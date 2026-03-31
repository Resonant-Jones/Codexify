from __future__ import annotations

import pytest


@pytest.mark.parametrize(
    ("raw_source_mode", "expected_source_mode"),
    [
        ("personal_knowledge", "personal_knowledge"),
        ("invalid", "project"),
        (None, "project"),
    ],
)
def test_chat_complete_normalizes_source_mode_and_encodes_origin(
    test_client, mock_db, monkeypatch, raw_source_mode, expected_source_mode
):
    mock_db.get_chat_thread.return_value = {
        "id": 1,
        "user_id": "test_user",
        "project_id": 7,
        "archived_at": None,
    }
    mock_db.list_messages.return_value = [{"role": "user", "content": "Hello"}]

    captured: dict[str, object] = {}
    monkeypatch.setattr(
        "guardian.routes.chat.acquire_turn_lock", lambda *a, **k: True
    )
    monkeypatch.setattr(
        "guardian.routes.chat.enqueue",
        lambda task, queue_name: captured.update(
            {"task": task, "queue_name": queue_name}
        ),
    )

    payload = {"depth_mode": "normal"}
    if raw_source_mode is not None:
        payload["source_mode"] = raw_source_mode

    response = test_client.post("/chat/1/complete", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["source_mode"] == expected_source_mode
    task = captured["task"]
    assert getattr(task, "origin").startswith("api:chat.complete|turn_id=")
    assert f"|source_mode={expected_source_mode}" in getattr(task, "origin")
    assert captured["queue_name"] == "codexify:queue:chat"
