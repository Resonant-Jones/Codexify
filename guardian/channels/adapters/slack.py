"""Slack channel adapter (outbound-focused)."""

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


class SlackAdapter(Adapter):
    def __init__(
        self,
        *,
        bot_token: str | None = None,
        default_channel: str | None = None,
        base_url: str = "https://slack.com/api",
    ) -> None:
        self._bot_token = (
            bot_token or os.getenv("GUARDIAN_SLACK_BOT_TOKEN", "")
        ).strip()
        self._default_channel = (default_channel or "").strip()
        self._base_url = base_url.rstrip("/")

    @property
    def adapter_id(self) -> str:
        return "slack"

    def parse_inbound(
        self, payload: dict[str, Any], ctx: AdapterContext
    ) -> InboundMessage:
        return InboundMessage(
            channel_id=str(
                payload.get("channel") or payload.get("channel_id") or ""
            ),
            sender_id=str(
                payload.get("user") or payload.get("sender_id") or ""
            ),
            text=str(payload.get("text") or ""),
            raw=payload,
        )

    def send(self, outbound: OutboundMessage, ctx: AdapterContext) -> None:
        result = self.send_message(
            channel_id=outbound.channel_id,
            text=outbound.text,
            thread_ts=outbound.thread_id,
        )
        if not result["success"]:
            raise ValueError(f"slack send failed: {result['error']}")

    def send_message(
        self,
        *,
        channel_id: str | None,
        text: str,
        thread_ts: str | None = None,
    ) -> dict[str, Any]:
        if not self._bot_token:
            return {
                "success": False,
                "provider": "slack",
                "error": "missing_bot_token",
                "message_id": None,
            }
        resolved_channel = (channel_id or self._default_channel or "").strip()
        if not resolved_channel:
            return {
                "success": False,
                "provider": "slack",
                "error": "missing_channel_id",
                "message_id": None,
            }
        payload: dict[str, Any] = {"channel": resolved_channel, "text": text}
        if thread_ts:
            payload["thread_ts"] = thread_ts
        try:
            response = requests.post(
                f"{self._base_url}/chat.postMessage",
                headers={
                    "Authorization": f"Bearer {self._bot_token}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=10,
            )
        except requests.RequestException as exc:
            return {
                "success": False,
                "provider": "slack",
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
                "provider": "slack",
                "error": str(
                    body.get("error") or f"http_{response.status_code}"
                ),
                "message_id": None,
            }

        return {
            "success": True,
            "provider": "slack",
            "error": None,
            "message_id": body.get("ts"),
        }
