from __future__ import annotations

from typing import Any

from guardian.channels.adapters.slack import SlackAdapter


class _Resp:
    def __init__(self, status_code: int, payload: dict[str, Any]) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict[str, Any]:
        return self._payload


def test_slack_missing_config_fails() -> None:
    adapter = SlackAdapter(bot_token="", default_channel="C1")
    result = adapter.send_message(channel_id="C1", text="hello")
    assert result["success"] is False
    assert result["error"] == "missing_bot_token"


def test_slack_success_normalized(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def _fake_post(url: str, headers: dict[str, str], json: dict[str, Any], timeout: int):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        return _Resp(200, {"ok": True, "ts": "171.0001"})

    monkeypatch.setattr("guardian.channels.adapters.slack.requests.post", _fake_post)
    adapter = SlackAdapter(bot_token="xoxb-test")

    result = adapter.send_message(channel_id="C1", text="hello")

    assert result == {
        "success": True,
        "provider": "slack",
        "error": None,
        "message_id": "171.0001",
    }
    assert captured["json"]["channel"] == "C1"
    assert captured["json"]["text"] == "hello"


def test_slack_vendor_error_normalized(monkeypatch) -> None:
    def _fake_post(url: str, headers: dict[str, str], json: dict[str, Any], timeout: int):
        return _Resp(200, {"ok": False, "error": "invalid_auth"})

    monkeypatch.setattr("guardian.channels.adapters.slack.requests.post", _fake_post)
    adapter = SlackAdapter(bot_token="xoxb-test")
    result = adapter.send_message(channel_id="C1", text="hello")
    assert result["success"] is False
    assert result["error"] == "invalid_auth"

