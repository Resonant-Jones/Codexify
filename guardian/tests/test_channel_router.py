from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from guardian.channels import allowlist, registry, router
from guardian.channels.base import (
    Adapter,
    AdapterContext,
    InboundMessage,
    OutboundMessage,
)


@dataclass
class _MockAdapter(Adapter):
    sent: list[OutboundMessage] = field(default_factory=list)

    @property
    def adapter_id(self) -> str:
        return "mock"

    def send(self, outbound: OutboundMessage, ctx: AdapterContext) -> None:
        self.sent.append(outbound)

    def parse_inbound(
        self, payload: dict[str, Any], ctx: AdapterContext
    ) -> InboundMessage:
        return InboundMessage(
            channel_id=payload["channel_id"],
            sender_id=payload["sender_id"],
            text=payload["text"],
            raw=payload,
        )


@pytest.fixture(autouse=True)
def _reset() -> None:
    allowlist.reset_state()
    registry.clear_adapters()


def _inbound() -> InboundMessage:
    return InboundMessage(
        channel_id="room-1",
        sender_id="sender-1",
        text="hello",
    )


def test_router_rejects_not_allowed_sender() -> None:
    adapter = _MockAdapter()
    registry.register_adapter(adapter)

    result = router.handle_inbound(
        "mock",
        _inbound(),
        ctx=AdapterContext(request_id="req-1"),
    )

    assert result["ok"] is False
    assert result["error"] == "not_allowed"
    assert adapter.sent == []


def test_router_allows_allowed_sender_and_sends_outbound() -> None:
    adapter = _MockAdapter()
    registry.register_adapter(adapter)
    allowlist.allow_sender("sender-1", "room-1")

    result = router.handle_inbound(
        "mock",
        _inbound(),
        ctx=AdapterContext(request_id="req-2"),
    )

    assert result["ok"] is True
    assert result["sent"] is True
    assert len(adapter.sent) == 1
    assert adapter.sent[0].recipient_id == "sender-1"
    assert adapter.sent[0].thread_id == "mock:room-1:sender-1"


def test_router_unknown_adapter_returns_deterministic_error() -> None:
    result = router.handle_inbound(
        "missing",
        _inbound(),
        ctx=AdapterContext(request_id="req-3"),
    )

    assert result == {
        "ok": False,
        "error": "unknown_adapter",
        "adapter_id": "missing",
    }

