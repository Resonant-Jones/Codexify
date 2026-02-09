"""Discord channel adapter (outbound-focused)."""

from __future__ import annotations

import os
from typing import Any

import requests

from guardian.channels.base import Adapter, AdapterContext, InboundMessage, OutboundMessage


class DiscordAdapter(Adapter):
    def __init__(self, *, webhook_url: str | None = None) -> None:
        self._webhook_url = (
            webhook_url or os.getenv("GUARDIAN_DISCORD_WEBHOOK_URL", "")
        ).strip()

    @property
    def adapter_id(self) -> str:
        return "discord"

    def parse_inbound(
        self, payload: dict[str, Any], ctx: AdapterContext
    ) -> InboundMessage:
        author = payload.get("author") if isinstance(payload.get("author"), dict) else {}
        return InboundMessage(
            channel_id=str(payload.get("channel_id") or ""),
            sender_id=str(author.get("id") or payload.get("sender_id") or ""),
            text=str(payload.get("content") or payload.get("text") or ""),
            raw=payload,
        )

    def send(self, outbound: OutboundMessage, ctx: AdapterContext) -> None:
        result = self.send_message(text=outbound.text)
        if not result["success"]:
            raise ValueError(f"discord send failed: {result['error']}")

    def send_message(self, *, text: str) -> dict[str, Any]:
        if not self._webhook_url:
            return {
                "success": False,
                "provider": "discord",
                "error": "missing_webhook_url",
                "message_id": None,
            }
        try:
            response = requests.post(
                self._webhook_url,
                json={"content": text},
                timeout=10,
            )
        except requests.RequestException as exc:
            return {
                "success": False,
                "provider": "discord",
                "error": f"request_failed:{exc.__class__.__name__}",
                "message_id": None,
            }

        body: dict[str, Any]
        try:
            body = response.json()
        except ValueError:
            body = {}

        if response.status_code not in (200, 204):
            return {
                "success": False,
                "provider": "discord",
                "error": str(body.get("message") or f"http_{response.status_code}"),
                "message_id": None,
            }
        return {
            "success": True,
            "provider": "discord",
            "error": None,
            "message_id": body.get("id"),
        }

