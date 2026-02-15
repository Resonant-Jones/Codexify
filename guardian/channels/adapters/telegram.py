"""Telegram channel adapter (outbound-focused)."""

from __future__ import annotations

import os
from typing import Any

import requests

from guardian.channels.base import (
    Adapter,
    AdapterContext,
    InboundMessage,
    OutboundMessage,
)


class TelegramAdapter(Adapter):
    def __init__(self, *, bot_token: str | None = None) -> None:
        self._bot_token = (
            bot_token or os.getenv("GUARDIAN_TELEGRAM_BOT_TOKEN", "")
        ).strip()

    @property
    def adapter_id(self) -> str:
        return "telegram"

    def parse_inbound(
        self, payload: dict[str, Any], ctx: AdapterContext
    ) -> InboundMessage:
        message = (
            payload.get("message")
            if isinstance(payload.get("message"), dict)
            else {}
        )
        chat = (
            message.get("chat") if isinstance(message.get("chat"), dict) else {}
        )
        sender = (
            message.get("from") if isinstance(message.get("from"), dict) else {}
        )
        return InboundMessage(
            channel_id=str(chat.get("id") or payload.get("channel_id") or ""),
            sender_id=str(sender.get("id") or payload.get("sender_id") or ""),
            text=str(message.get("text") or payload.get("text") or ""),
            raw=payload,
        )

    def send(self, outbound: OutboundMessage, ctx: AdapterContext) -> None:
        result = self.send_message(
            chat_id=outbound.channel_id, text=outbound.text
        )
        if not result["success"]:
            raise ValueError(f"telegram send failed: {result['error']}")

    def send_message(self, *, chat_id: str | None, text: str) -> dict[str, Any]:
        if not self._bot_token:
            return {
                "success": False,
                "provider": "telegram",
                "error": "missing_bot_token",
                "message_id": None,
            }
        resolved_chat_id = (chat_id or "").strip()
        if not resolved_chat_id:
            return {
                "success": False,
                "provider": "telegram",
                "error": "missing_chat_id",
                "message_id": None,
            }

        url = f"https://api.telegram.org/bot{self._bot_token}/sendMessage"
        try:
            response = requests.post(
                url,
                json={"chat_id": resolved_chat_id, "text": text},
                timeout=10,
            )
        except requests.RequestException as exc:
            return {
                "success": False,
                "provider": "telegram",
                "error": f"request_failed:{exc.__class__.__name__}",
                "message_id": None,
            }

        body: dict[str, Any]
        try:
            body = response.json()
        except ValueError:
            body = {}

        if response.status_code != 200 or not body.get("ok", False):
            return {
                "success": False,
                "provider": "telegram",
                "error": str(
                    body.get("description") or f"http_{response.status_code}"
                ),
                "message_id": None,
            }

        result = (
            body.get("result") if isinstance(body.get("result"), dict) else {}
        )
        return {
            "success": True,
            "provider": "telegram",
            "error": None,
            "message_id": result.get("message_id"),
        }
