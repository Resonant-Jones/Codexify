"""Route tests for the presence heartbeat endpoint (Slice 3)."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# We test the heartbeat route contract without a full app stack.
# The route schema enforcement (extra=forbid) and response shape are testable
# through the Pydantic contracts directly.
# ---------------------------------------------------------------------------

from guardian.account_observability.contracts import (
    HeartbeatRequest,
    HeartbeatResponse,
)
from guardian.account_observability.tokens import (
    PRESENCE_ACTIVE_WINDOW_SECONDS,
    PRESENCE_IDLE_EXPIRY_SECONDS,
)


class TestHeartbeatRequestSchema:
    """HeartbeatRequest must reject unknown fields."""

    def test_empty_body_is_accepted(self):
        req = HeartbeatRequest()
        assert req is not None

    def test_unknown_fields_are_rejected(self):
        with pytest.raises(ValueError):
            HeartbeatRequest(account_id="user-1")

        with pytest.raises(ValueError):
            HeartbeatRequest(guest_id="guest-1")

        with pytest.raises(ValueError):
            HeartbeatRequest(route="/dashboard")

        with pytest.raises(ValueError):
            HeartbeatRequest(page_path="/home")

        with pytest.raises(ValueError):
            HeartbeatRequest(message_id="msg-123")

        with pytest.raises(ValueError):
            HeartbeatRequest(thread_id="thread-1")

        with pytest.raises(ValueError):
            HeartbeatRequest(project_id="proj-1")

        with pytest.raises(ValueError):
            HeartbeatRequest(referrer="https://example.com")

        with pytest.raises(ValueError):
            HeartbeatRequest(user_agent="Mozilla/5.0")

        with pytest.raises(ValueError):
            HeartbeatRequest(location="US")

        with pytest.raises(ValueError):
            HeartbeatRequest(device_fingerprint="abc123")

        with pytest.raises(ValueError):
            HeartbeatRequest(client_timestamp="2026-01-01T00:00:00Z")

    def test_prohibited_analytics_dimensions_are_rejected(self):
        """Ensure the schema blocks known analytics/telemetry field names."""
        prohibited = [
            "ip_address",
            "raw_ip",
            "hashed_ip",
            "user_agent",
            "fingerprint",
            "page_path",
            "route_name",
            "message_id",
            "thread_id",
            "project_id",
            "referrer",
            "latitude",
            "longitude",
            "city",
            "postal_code",
            "device_id",
        ]
        for field in prohibited:
            with pytest.raises(ValueError):
                HeartbeatRequest(**{field: "test"})


class TestHeartbeatResponseShape:
    """HeartbeatResponse must be minimal and well-typed."""

    def test_response_is_minimal(self):
        from datetime import datetime, timezone

        resp = HeartbeatResponse(
            active=True,
            active_window_seconds=PRESENCE_ACTIVE_WINDOW_SECONDS,
            idle_expiry_seconds=PRESENCE_IDLE_EXPIRY_SECONDS,
            server_time=datetime.now(timezone.utc),
        )
        data = resp.model_dump()
        assert set(data.keys()) == {
            "active",
            "active_window_seconds",
            "idle_expiry_seconds",
            "server_time",
        }
        # No persistence IDs, no subject IDs leaked
        for key in data:
            assert "session_id" not in key
            assert "user_id" not in key
            assert "guest_id" not in key
            assert "presence_id" not in key

    def test_canonical_timing_values_are_exposed(self):
        from datetime import datetime, timezone

        resp = HeartbeatResponse(
            active=True,
            active_window_seconds=PRESENCE_ACTIVE_WINDOW_SECONDS,
            idle_expiry_seconds=PRESENCE_IDLE_EXPIRY_SECONDS,
            server_time=datetime.now(timezone.utc),
        )
        assert resp.active_window_seconds == 300
        assert resp.idle_expiry_seconds == 1800


class TestHeartbeatRouteContract:
    """Verify that the route module compiles and has the expected endpoints."""

    def test_router_exists(self):
        from guardian.routes.account_observability import router
        assert router is not None

    def test_heartbeat_endpoint_is_registered(self):
        from guardian.routes.account_observability import router
        paths = [route.path for route in router.routes]
        heartbeat_paths = [p for p in paths if "heartbeat" in p]
        assert len(heartbeat_paths) >= 1

    def test_heartbeat_endpoint_uses_post(self):
        from guardian.routes.account_observability import router
        for route in router.routes:
            if "heartbeat" in route.path:
                assert "POST" in route.methods
                break
        else:
            pytest.fail("No heartbeat route found")


class TestCleanupRouteContract:
    """Verify that the cleanup route exists and has the expected shape."""

    def test_cleanup_endpoint_is_registered(self):
        from guardian.routes.account_observability import router
        paths = [route.path for route in router.routes]
        cleanup_paths = [p for p in paths if "cleanup" in p]
        assert len(cleanup_paths) >= 1

    def test_cleanup_endpoint_uses_post(self):
        from guardian.routes.account_observability import router
        for route in router.routes:
            if "cleanup" in route.path:
                assert "POST" in route.methods
                break
        else:
            pytest.fail("No cleanup route found")


class TestCleanupReceiptSchema:
    def test_receipt_has_required_fields(self):
        from guardian.account_observability.contracts import RetentionCleanupReceipt
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        receipt = RetentionCleanupReceipt(
            execution_timestamp=now,
            cutoff_presence_30d=now,
            cutoff_idle_30m=now,
            expired_session_count=0,
            deleted_presence_count=0,
            dry_run=True,
        )
        data = receipt.model_dump()
        assert "execution_timestamp" in data
        assert "cutoff_presence_30d" in data
        assert "cutoff_idle_30m" in data
        assert "expired_session_count" in data
        assert "deleted_presence_count" in data
        assert "dry_run" in data
        assert "deferred_guest_reason" in data
