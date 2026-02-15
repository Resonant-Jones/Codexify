from __future__ import annotations

from typing import Any

from guardian.channels import allowlist, registry
from guardian.channels.adapters.slack import SlackAdapter
from guardian.channels.base import AdapterContext, InboundMessage
from guardian.channels.router import handle_inbound


class _Resp:
    def __init__(self, status_code: int, payload: dict[str, Any]) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict[str, Any]:
        return self._payload


def test_router_invokes_registered_adapter_send(monkeypatch) -> None:
    allowlist.reset_state()
    registry.clear_adapters()
    allowlist.allow_sender("sender-1", "room-1")

    captured: dict[str, Any] = {}

    def _fake_post(
        url: str, headers: dict[str, str], json: dict[str, Any], timeout: int
    ):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        return _Resp(200, {"ok": True, "ts": "171.0002"})

    monkeypatch.setattr(
        "guardian.channels.adapters.slack.requests.post", _fake_post
    )
    adapter = SlackAdapter(bot_token="xoxb-test")
    registry.register_adapter(adapter)

    result = handle_inbound(
        "slack",
        InboundMessage(channel_id="room-1", sender_id="sender-1", text="hi"),
        ctx=AdapterContext(request_id="req-1"),
    )

    assert result["ok"] is True
    assert captured["json"]["channel"] == "room-1"
    assert captured["json"]["text"] == "ack: hi"
