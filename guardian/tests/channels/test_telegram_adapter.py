from __future__ import annotations

from typing import Any

from guardian.channels.adapters.telegram import TelegramAdapter


class _Resp:
    def __init__(self, status_code: int, payload: dict[str, Any]) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict[str, Any]:
        return self._payload


def test_telegram_missing_config_fails() -> None:
    adapter = TelegramAdapter(bot_token="")
    result = adapter.send_message(chat_id="123", text="hello")
    assert result["success"] is False
    assert result["error"] == "missing_bot_token"


def test_telegram_success_normalized(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def _fake_post(url: str, json: dict[str, Any], timeout: int):
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        return _Resp(200, {"ok": True, "result": {"message_id": 9001}})

    monkeypatch.setattr("guardian.channels.adapters.telegram.requests.post", _fake_post)
    adapter = TelegramAdapter(bot_token="bot-token")

    result = adapter.send_message(chat_id="123", text="hello")

    assert result == {
        "success": True,
        "provider": "telegram",
        "error": None,
        "message_id": 9001,
    }
    assert "bot-token" in captured["url"]
    assert captured["json"] == {"chat_id": "123", "text": "hello"}


def test_telegram_vendor_error_normalized(monkeypatch) -> None:
    def _fake_post(url: str, json: dict[str, Any], timeout: int):
        return _Resp(200, {"ok": False, "description": "chat not found"})

    monkeypatch.setattr("guardian.channels.adapters.telegram.requests.post", _fake_post)
    adapter = TelegramAdapter(bot_token="bot-token")

    result = adapter.send_message(chat_id="123", text="hello")
    assert result["success"] is False
    assert result["error"] == "chat not found"

