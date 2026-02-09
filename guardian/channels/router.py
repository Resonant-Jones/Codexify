"""Minimal channel router for inbound -> outbound handling."""

from __future__ import annotations

from typing import Any

from guardian.channels.allowlist import (
    PairingCodeError,
    is_allowed,
    redeem_pairing_code,
)
from guardian.channels.base import AdapterContext, InboundMessage, OutboundMessage
from guardian.channels.registry import get_adapter


def handle_inbound(
    adapter_id: str,
    inbound: InboundMessage,
    *,
    ctx: AdapterContext,
    pairing_code: str | None = None,
) -> dict[str, Any]:
    try:
        adapter = get_adapter(adapter_id)
    except KeyError:
        return {
            "ok": False,
            "error": "unknown_adapter",
            "adapter_id": adapter_id,
        }

    allowed = is_allowed(inbound.sender_id, inbound.channel_id)
    if not allowed and pairing_code:
        try:
            redeemed_sender, redeemed_channel = redeem_pairing_code(
                pairing_code
            )
        except PairingCodeError as exc:
            return {
                "ok": False,
                "error": "not_allowed",
                "reason": str(exc),
            }
        allowed = (
            redeemed_sender == inbound.sender_id
            and redeemed_channel == inbound.channel_id
        )

    if not allowed:
        return {
            "ok": False,
            "error": "not_allowed",
            "reason": "sender not allowlisted",
        }

    thread_id = f"{adapter_id}:{inbound.channel_id}:{inbound.sender_id}"
    outbound = OutboundMessage(
        channel_id=inbound.channel_id,
        recipient_id=inbound.sender_id,
        text=f"ack: {inbound.text}",
        thread_id=thread_id,
        raw={"source": "channel_router"},
    )
    adapter.send(outbound, ctx)

    return {
        "ok": True,
        "adapter_id": adapter_id,
        "thread_id": thread_id,
        "sent": True,
    }

