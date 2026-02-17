"""Capability grant primitives for scoped, short-lived authorization."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4


class CapabilityError(RuntimeError):
    """Raised for invalid capability consumption or configuration."""


@dataclass
class CapabilityGrant:
    grant_id: str
    action: str
    resource: str
    expires_at: datetime
    max_calls: int
    calls_used: int = 0

    @classmethod
    def issue(
        cls,
        *,
        action: str,
        resource: str,
        ttl_seconds: int,
        max_calls: int,
    ) -> CapabilityGrant:
        if ttl_seconds <= 0:
            raise CapabilityError("ttl_seconds must be > 0")
        if max_calls <= 0:
            raise CapabilityError("max_calls must be > 0")
        return cls(
            grant_id=str(uuid4()),
            action=action,
            resource=resource,
            expires_at=datetime.now(timezone.utc)
            + timedelta(seconds=ttl_seconds),
            max_calls=max_calls,
            calls_used=0,
        )

    def is_expired(self, now: datetime | None = None) -> bool:
        now = now or datetime.now(timezone.utc)
        return now >= self.expires_at

    def _resource_allows(self, requested_resource: str) -> bool:
        granted = (self.resource or "").strip()
        requested = (requested_resource or "").strip()
        if not granted or not requested:
            return False
        return requested == granted or requested.startswith(granted)

    def allows(
        self,
        action: str,
        resource: str,
        now: datetime | None = None,
    ) -> bool:
        if not action or not resource:
            return False
        if self.is_expired(now):
            return False
        if self.calls_used >= self.max_calls:
            return False
        if action != self.action:
            return False
        return self._resource_allows(resource)

    def consume_call(self) -> None:
        if self.calls_used >= self.max_calls:
            raise CapabilityError("capability max_calls exceeded")
        self.calls_used += 1
