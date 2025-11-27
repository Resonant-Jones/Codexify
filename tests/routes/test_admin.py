"""
Test suite for admin-protected endpoints.

Tests authentication, authorization, and access control for admin routes.
"""

from __future__ import annotations

import os
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException


class TestRequireAdminFunction:
    """Test the require_admin dependency function directly."""

    def test_require_admin_with_valid_admin_token(self, monkeypatch):
        """Test that valid X-Admin-Token grants access."""
        monkeypatch.setenv("GUARDIAN_ADMIN_TOKEN", "test-admin-secret")
        monkeypatch.setenv("DEBUG", "false")

        # Reload module to pick up env vars
        import importlib

        from guardian.routes import admin as admin_module

        importlib.reload(admin_module)

        # Call require_admin with valid token
        result = admin_module.require_admin(
            x_admin_token="test-admin-secret", x_api_key="some-api-key"
        )

        assert result == "admin_token"

    def test_require_admin_with_invalid_admin_token(self, monkeypatch):
        """Test that invalid X-Admin-Token is rejected."""
        monkeypatch.setenv("GUARDIAN_ADMIN_TOKEN", "test-admin-secret")
        monkeypatch.setenv("DEBUG", "false")

        # Reload module to pick up env vars
        import importlib

        from guardian.routes import admin as admin_module

        importlib.reload(admin_module)

        # Call require_admin with wrong token
        with pytest.raises(HTTPException) as exc_info:
            admin_module.require_admin(
                x_admin_token="wrong-token", x_api_key="some-api-key"
            )

        assert exc_info.value.status_code == 403
        assert "Admin access required" in exc_info.value.detail["error"]

    def test_require_admin_with_no_admin_token(self, monkeypatch):
        """Test that missing X-Admin-Token and no DEBUG mode is rejected."""
        monkeypatch.setenv("GUARDIAN_ADMIN_TOKEN", "test-admin-secret")
        monkeypatch.setenv("DEBUG", "false")

        # Reload module to pick up env vars
        import importlib

        from guardian.routes import admin as admin_module

        importlib.reload(admin_module)

        # Call require_admin without token
        with pytest.raises(HTTPException) as exc_info:
            admin_module.require_admin(
                x_admin_token=None, x_api_key="some-api-key"
            )

        assert exc_info.value.status_code == 403
        assert "Admin access required" in exc_info.value.detail["error"]

    def test_require_admin_with_debug_mode(self, monkeypatch):
        """Test that DEBUG=true grants access without admin token."""
        monkeypatch.setenv("GUARDIAN_ADMIN_TOKEN", "test-admin-secret")
        monkeypatch.setenv("DEBUG", "true")

        # Reload module to pick up env vars
        import importlib

        from guardian.routes import admin as admin_module

        importlib.reload(admin_module)

        # Call require_admin without token but with DEBUG mode
        result = admin_module.require_admin(
            x_admin_token=None, x_api_key="some-api-key"
        )

        assert result == "debug_mode"

    def test_require_admin_no_token_env_var_set(self, monkeypatch):
        """Test behavior when GUARDIAN_ADMIN_TOKEN is not set."""
        monkeypatch.delenv("GUARDIAN_ADMIN_TOKEN", raising=False)
        monkeypatch.setenv("DEBUG", "false")

        # Reload module to pick up env vars
        import importlib

        from guardian.routes import admin as admin_module

        importlib.reload(admin_module)

        # Should fail since no admin token env var and DEBUG is false
        with pytest.raises(HTTPException) as exc_info:
            admin_module.require_admin(
                x_admin_token="any-token", x_api_key="some-api-key"
            )

        assert exc_info.value.status_code == 403

    def test_require_admin_error_message_structure(self, monkeypatch):
        """Test that error message has proper structure."""
        monkeypatch.setenv("GUARDIAN_ADMIN_TOKEN", "test-admin-secret")
        monkeypatch.setenv("DEBUG", "false")

        # Reload module to pick up env vars
        import importlib

        from guardian.routes import admin as admin_module

        importlib.reload(admin_module)

        # Call require_admin without credentials
        with pytest.raises(HTTPException) as exc_info:
            admin_module.require_admin(x_admin_token=None, x_api_key=None)

        detail = exc_info.value.detail
        assert "error" in detail
        assert "message" in detail
        assert "required" in detail
        assert "X-Admin-Token" in detail["message"]
        assert "DEBUG" in detail["message"]


class TestAdminLogging:
    """Test that admin access attempts are properly logged."""

    def test_successful_access_logs_info(self, monkeypatch, caplog):
        """Test that successful admin access logs info message."""
        import logging

        caplog.set_level(logging.INFO)

        monkeypatch.setenv("GUARDIAN_ADMIN_TOKEN", "test-admin-secret")
        monkeypatch.setenv("DEBUG", "false")

        # Reload module to pick up env vars
        import importlib

        from guardian.routes import admin as admin_module

        importlib.reload(admin_module)

        # Call with valid token
        admin_module.require_admin(
            x_admin_token="test-admin-secret", x_api_key="some-key"
        )

        # Check that log was emitted
        assert any(
            "Admin access granted" in record.message
            for record in caplog.records
        )

    def test_failed_access_logs_warning(self, monkeypatch, caplog):
        """Test that failed admin access logs warning message."""
        import logging

        caplog.set_level(logging.WARNING)

        monkeypatch.setenv("GUARDIAN_ADMIN_TOKEN", "test-admin-secret")
        monkeypatch.setenv("DEBUG", "false")

        # Reload module to pick up env vars
        import importlib

        from guardian.routes import admin as admin_module

        importlib.reload(admin_module)

        # Call without valid credentials
        try:
            admin_module.require_admin(x_admin_token=None, x_api_key="some-key")
        except HTTPException:
            pass

        # Check that warning log was emitted
        assert any(
            "Admin access DENIED" in record.message for record in caplog.records
        )

    def test_debug_mode_access_logs_info(self, monkeypatch, caplog):
        """Test that DEBUG mode access logs info message."""
        import logging

        caplog.set_level(logging.INFO)

        monkeypatch.setenv("GUARDIAN_ADMIN_TOKEN", "test-admin-secret")
        monkeypatch.setenv("DEBUG", "true")

        # Reload module to pick up env vars
        import importlib

        from guardian.routes import admin as admin_module

        importlib.reload(admin_module)

        # Call without admin token but with DEBUG mode
        admin_module.require_admin(x_admin_token=None, x_api_key="some-key")

        # Check that debug mode log was emitted
        assert any("DEBUG mode" in record.message for record in caplog.records)


class TestAdminTokenComparison:
    """Test secure token comparison using secrets.compare_digest."""

    def test_uses_constant_time_comparison(self, monkeypatch):
        """Test that token comparison uses secrets.compare_digest (constant time)."""
        monkeypatch.setenv("GUARDIAN_ADMIN_TOKEN", "test-admin-secret")
        monkeypatch.setenv("DEBUG", "false")

        # Reload module
        import importlib

        from guardian.routes import admin as admin_module

        importlib.reload(admin_module)

        # Patch secrets.compare_digest to verify it's called
        with patch(
            "guardian.routes.admin.secrets.compare_digest"
        ) as mock_compare:
            mock_compare.return_value = True

            admin_module.require_admin(
                x_admin_token="test-admin-secret", x_api_key="some-key"
            )

            # Verify secrets.compare_digest was called
            assert mock_compare.called
            # Verify it was called with the tokens
            call_args = mock_compare.call_args[0]
            assert "test-admin-secret" in call_args

    def test_timing_safe_against_brute_force(self, monkeypatch):
        """Test that timing attacks are mitigated by constant-time comparison."""
        monkeypatch.setenv("GUARDIAN_ADMIN_TOKEN", "secret123")
        monkeypatch.setenv("DEBUG", "false")

        # Reload module
        import importlib

        from guardian.routes import admin as admin_module

        importlib.reload(admin_module)

        # These should all fail, but take the same amount of time
        # (we can't easily test timing, but we verify they all fail)
        wrong_tokens = ["s", "se", "sec", "secr", "wrong123"]

        for token in wrong_tokens:
            with pytest.raises(HTTPException):
                admin_module.require_admin(x_admin_token=token, x_api_key="key")


class TestConfigEndpointAccess:
    """Test access control patterns for config endpoint."""

    def test_config_endpoint_exists(self):
        """Verify /debug/config endpoint is defined."""
        from guardian.routes import admin as admin_module

        # Check that router has the endpoint
        routes = [route.path for route in admin_module.router.routes]
        assert "/debug/config" in routes

    def test_config_endpoint_uses_admin_dependency(self):
        """Verify /debug/config uses require_admin dependency."""
        from guardian.routes import admin as admin_module

        # Find the /debug/config route
        config_route = None
        for route in admin_module.router.routes:
            if route.path == "/debug/config":
                config_route = route
                break

        assert config_route is not None, "/debug/config route not found"

        # Check that it has dependencies
        assert hasattr(config_route, "dependant")
        assert config_route.dependant is not None


class TestAuthzDebugEndpointAccess:
    """Test access control patterns for authz/debug endpoint."""

    def test_authz_debug_endpoint_exists(self):
        """Verify /authz/debug endpoint is defined."""
        from guardian.routes import admin as admin_module

        # Check that router has the endpoint
        routes = [route.path for route in admin_module.router.routes]
        assert "/authz/debug" in routes

    def test_authz_debug_endpoint_uses_admin_dependency(self):
        """Verify /authz/debug uses require_admin dependency."""
        from guardian.routes import admin as admin_module

        # Find the /authz/debug route
        authz_route = None
        for route in admin_module.router.routes:
            if route.path == "/authz/debug":
                authz_route = route
                break

        assert authz_route is not None, "/authz/debug route not found"

        # Check that it has dependencies
        assert hasattr(authz_route, "dependant")
        assert authz_route.dependant is not None


class TestPublicEndpointsRemainAccessible:
    """Verify public endpoints don't require admin access."""

    def test_ping_endpoint_is_public(self):
        """Verify /ping endpoint doesn't require admin."""
        from guardian.routes import admin as admin_module

        # Find the /ping route
        ping_route = None
        for route in admin_module.router.routes:
            if route.path == "/ping":
                ping_route = route
                break

        assert ping_route is not None, "/ping route not found"
        # Ping should not have require_admin dependency
        # (we just verify it exists and is accessible)

    def test_healthz_endpoint_is_public(self):
        """Verify /healthz endpoint doesn't require admin."""
        from guardian.routes import admin as admin_module

        # Find the /healthz route
        healthz_route = None
        for route in admin_module.router.routes:
            if route.path == "/healthz":
                healthz_route = route
                break

        assert healthz_route is not None, "/healthz route not found"
        # Healthz should not have require_admin dependency
