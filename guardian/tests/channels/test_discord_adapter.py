from __future__ import annotations

from typing import Any

from guardian.channels.adapters.discord import DiscordAdapter


class _Resp:
    def __init__(self, status_code: int, payload: dict[str, Any] | None = None) -> None:
        self.status_code = status_code
        self._payload = payload or {}

    def json(self) -> dict[str, Any]:
        return self._payload


def test_discord_missing_config_fails() -> None:
    adapter = DiscordAdapter(webhook_url="")
    result = adapter.send_message(text="hello")
    assert result["success"] is False
    assert result["error"] == "missing_webhook_url"


def test_discord_success_normalized(monkeypatch) -> None:
    seen: dict[str, Any] = {}

    def _fake_post(url: str, json: dict[str, Any], timeout: int):
        seen["url"] = url
        seen["json"] = json
        seen["timeout"] = timeout
        return _Resp(200, {"id": "m-123"})

    monkeypatch.setattr("guardian.channels.adapters.discord.requests.post", _fake_post)
    adapter = DiscordAdapter(webhook_url="https://discord.example/webhook")

    result = adapter.send_message(text="hello")

    assert result == {
        "success": True,
        "provider": "discord",
        "error": None,
        "message_id": "m-123",
    }
    assert seen["json"]["content"] == "hello"


def test_discord_http_error_normalized(monkeypatch) -> None:
    def _fake_post(url: str, json: dict[str, Any], timeout: int):
        return _Resp(400, {"message": "bad request"})

    monkeypatch.setattr("guardian.channels.adapters.discord.requests.post", _fake_post)
    adapter = DiscordAdapter(webhook_url="https://discord.example/webhook")

    result = adapter.send_message(text="hello")
    assert result["success"] is False
    assert result["error"] == "bad request"

