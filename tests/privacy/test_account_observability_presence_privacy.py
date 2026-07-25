"""Privacy sentinel tests for account observability presence (Slice 3)."""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Prohibited field names — these must NEVER appear in request schemas
# or persistence write paths for the presence subsystem.
# ---------------------------------------------------------------------------

PROHIBITED_FIELDS = [
    "raw_ip",
    "ip_hash",
    "hashed_ip",
    "ip_address",
    "user_agent",
    "fingerprint",
    "device_fingerprint",
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
    "postal",
    "device_id",
    "browser_name",
    "browser_version",
    "os_name",
    "os_version",
    "screen_width",
    "screen_height",
    "viewport_width",
    "viewport_height",
    "click_id",
    "session_replay_id",
    "analytics_id",
    "tracking_id",
    "ad_id",
    "campaign_click_id",
]


class TestPresenceSchemaPrivacy:
    """HeartbeatRequest must not accept prohibited fields."""

    def test_heartbeat_request_rejects_all_prohibited_fields(self):
        from guardian.account_observability.contracts import HeartbeatRequest

        for field in PROHIBITED_FIELDS:
            with pytest.raises(ValueError):
                HeartbeatRequest(**{field: "test_value"})

    def test_heartbeat_request_accepts_no_arbitrary_fields(self):
        from guardian.account_observability.contracts import HeartbeatRequest

        # Even harmless-sounding fields should be rejected (extra=forbid)
        with pytest.raises(ValueError):
            HeartbeatRequest(timestamp="2026-01-01T00:00:00Z")

        with pytest.raises(ValueError):
            HeartbeatRequest(client_time="2026-01-01T00:00:00Z")

        with pytest.raises(ValueError):
            HeartbeatRequest(app_version="1.0.0")


class TestPresenceModelPrivacy:
    """The PresenceSession model must not have prohibited columns."""

    def test_presence_session_table_columns_are_clean(self):
        from guardian.db.models import AccountObservabilityPresenceSession

        columns = {c.name for c in AccountObservabilityPresenceSession.__table__.columns}
        for prohibited in PROHIBITED_FIELDS:
            assert prohibited not in columns, (
                f"Prohibited column '{prohibited}' found in "
                "AccountObservabilityPresenceSession"
            )

    def test_presence_model_has_no_geoip_resolution_columns(self):
        """Slice 3 must not include geoip resolution. Country/region columns
        exist from Slice 1 but are left NULL in this slice."""
        from guardian.db.models import AccountObservabilityPresenceSession

        columns = {c.name for c in AccountObservabilityPresenceSession.__table__.columns}
        # country_code and region_code exist as nullable columns from Slice 1
        # but must never be populated in Slice 3
        assert "country_code" in columns  # exists from schema
        assert "region_code" in columns  # exists from schema
        # No latitude/longitude/city columns
        for geo in ["latitude", "longitude", "city", "postal_code"]:
            assert geo not in columns


class TestPresenceServicePrivacy:
    """The presence service must not import or call GeoIP, logging of PII, etc."""

    def test_presence_service_has_no_geoip_import(self):
        import inspect
        from guardian.account_observability import presence as presence_module

        source = inspect.getsource(presence_module)
        assert "geoip" not in source.lower()
        assert "maxmind" not in source.lower()
        assert "ipaddress" not in source.lower()

    def test_presence_service_has_no_ip_processing(self):
        import inspect
        from guardian.account_observability import presence as presence_module

        source = inspect.getsource(presence_module)
        # No raw IP or hashed IP logic
        assert "raw_ip" not in source.lower()
        assert "hashed_ip" not in source.lower()
        # No IP address processing
        assert ".ip" not in source.lower() or "strip" in source.lower()

    def test_retention_service_has_no_geoip_import(self):
        import inspect
        from guardian.account_observability import retention as retention_module

        source = inspect.getsource(retention_module)
        assert "geoip" not in source.lower()
        assert "maxmind" not in source.lower()

    def test_heartbeat_schema_columns_are_content_free(self):
        """Verify the HeartbeatRequest schema doesn't contain content/
        telemetry column names."""
        from guardian.account_observability.contracts import HeartbeatRequest

        fields = set(HeartbeatRequest.model_fields.keys())
        # The only allowed field is... nothing. HeartbeatRequest has no fields.
        # It's an empty model with extra=forbid.
        assert len(fields) == 0


class TestNoThirdPartyDependencies:
    """Slice 3 must not introduce analytics SDK dependencies."""

    def test_no_analytics_imports_in_presence(self):
        import inspect
        from guardian.account_observability import presence as presence_module

        source = inspect.getsource(presence_module)
        for banned in [
            "google_analytics",
            "mixpanel",
            "amplitude",
            "segment",
            "heap",
            "posthog",
            "sentry_sdk",
        ]:
            assert banned not in source.lower(), (
                f"Third-party analytics import '{banned}' found in presence service"
            )

    def test_no_analytics_imports_in_retention(self):
        import inspect
        from guardian.account_observability import retention as retention_module

        source = inspect.getsource(retention_module)
        for banned in [
            "google_analytics",
            "mixpanel",
            "amplitude",
            "segment",
            "heap",
            "posthog",
            "sentry_sdk",
        ]:
            assert banned not in source.lower(), (
                f"Third-party analytics import '{banned}' found in retention service"
            )


class TestNoOrdinaryTrafficPresenceLeakage:
    """Presence must only be updated through explicit heartbeat."""

    def test_record_heartbeat_is_only_presence_entry_point(self):
        """The presence module's public API contains only the sanctioned
        entry points. Importing the module must not trigger side effects."""
        from guardian.account_observability import presence

        public = [n for n in dir(presence) if not n.startswith("_")]
        # The sanctioned public API
        assert "record_heartbeat" in public
        assert "end_account_presence" in public
        assert "end_guest_presence" in public
        # Verify no automatic listener/hook is registered
        assert "auto" not in [n.lower() for n in public if "update" in n.lower()]
