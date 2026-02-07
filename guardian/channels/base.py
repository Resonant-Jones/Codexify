"""Shared channel adapter types and interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class AdapterContext:
    request_id: str
    user_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class InboundMessage:
    channel_id: str
    sender_id: str
    text: str
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class OutboundMessage:
    channel_id: str
    recipient_id: str
    text: str
    thread_id: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


class Adapter(ABC):
    """Adapter interface implemented by channel integrations."""

    @property
    @abstractmethod
    def adapter_id(self) -> str:
        """Stable adapter identifier used by the registry."""

    @abstractmethod
    def send(self, outbound: OutboundMessage, ctx: AdapterContext) -> None:
        """Send outbound data to the backing channel provider."""

    @abstractmethod
    def parse_inbound(
        self, payload: dict[str, Any], ctx: AdapterContext
    ) -> InboundMessage:
        """Convert provider payloads into the canonical inbound model."""

