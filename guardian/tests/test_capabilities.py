from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from guardian.core.capabilities import CapabilityError, CapabilityGrant


def test_capability_grant_deny_by_default_on_action_or_resource_mismatch():
    grant = CapabilityGrant.issue(
        action="vector:read",
        resource="ns:user:local",
        ttl_seconds=60,
        max_calls=2,
    )

    assert grant.allows("vector:write", "ns:user:local") is False
    assert grant.allows("vector:read", "ns:other") is False


def test_capability_grant_expiry_blocks_access():
    grant = CapabilityGrant(
        grant_id="g-1",
        action="vector:read",
        resource="ns:user:local",
        expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
        max_calls=1,
        calls_used=0,
    )

    assert grant.is_expired() is True
    assert grant.allows("vector:read", "ns:user:local") is False


def test_capability_grant_max_calls_enforced():
    grant = CapabilityGrant.issue(
        action="vector:read",
        resource="ns:user:local",
        ttl_seconds=60,
        max_calls=1,
    )

    assert grant.allows("vector:read", "ns:user:local") is True
    grant.consume_call()
    assert grant.allows("vector:read", "ns:user:local") is False

    with pytest.raises(CapabilityError, match="max_calls exceeded"):
        grant.consume_call()


def test_capability_grant_resource_prefix_matching():
    grant = CapabilityGrant.issue(
        action="vector:read",
        resource="ns:user:local",
        ttl_seconds=60,
        max_calls=2,
    )

    assert grant.allows("vector:read", "ns:user:local:thread:1") is True
