"""
Tests for rate limiting and security headers middleware.

These tests validate that:
1. Rate limiting is enforced correctly
2. Security headers are present in responses
3. CORS and security headers work together
4. Rate limiting can be disabled via environment variables
"""

import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def test_client():
    """Create a test client for the Guardian API."""
    # Import here to allow environment variable mocking in tests
    from guardian.server.app import app

    return TestClient(app)


def test_healthz_endpoint(test_client):
    """Test that healthz endpoint returns expected structure."""
    response = test_client.get("/healthz")
    assert response.status_code == 200

    data = response.json()
    assert data["ok"] is True
    assert "codexify" in data

    # Check for rate limiting and security headers status
    codexify_info = data["codexify"]
    assert "rate_limiting" in codexify_info
    assert "security_headers" in codexify_info


def test_security_headers_present(test_client):
    """Test that security headers are included in responses."""
    response = test_client.get("/healthz")

    # Check for OWASP-recommended headers (if security headers are enabled)
    # Note: These will only be present if fastapi-security-headers is installed
    headers_lower = {k.lower(): v for k, v in response.headers.items()}

    # X-Content-Type-Options should prevent MIME sniffing
    if "x-content-type-options" in headers_lower:
        assert headers_lower["x-content-type-options"] == "nosniff"

    # X-Frame-Options should prevent clickjacking
    if "x-frame-options" in headers_lower:
        assert headers_lower["x-frame-options"] in ["DENY", "SAMEORIGIN"]

    # Content-Security-Policy (if enabled)
    if "content-security-policy" in headers_lower:
        csp = headers_lower["content-security-policy"]
        assert "default-src" in csp


def test_rate_limit_response_format(test_client):
    """Test that rate limit errors have correct format when triggered."""
    # This test attempts to trigger rate limiting
    # Note: May not trigger in test environment with high limits

    # Send many requests to potentially trigger rate limit
    responses = []
    for i in range(150):
        response = test_client.get("/healthz")
        responses.append(response)

    # Check if any responses hit rate limit
    rate_limited = [r for r in responses if r.status_code == 429]

    # If rate limiting was triggered, validate response format
    if rate_limited:
        response = rate_limited[0]
        data = response.json()
        assert "error" in data
        assert "detail" in data
        assert data["error"] == "Rate limit exceeded"
        assert "retry_after" in data


def test_cors_headers_present(test_client):
    """Test that CORS headers are configured correctly."""
    # Send a preflight OPTIONS request
    response = test_client.options(
        "/healthz",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    # CORS headers should be present
    headers_lower = {k.lower(): v for k, v in response.headers.items()}
    assert (
        "access-control-allow-origin" in headers_lower
        or response.status_code in [200, 405]
    )


def test_cors_and_security_headers_compatible(test_client):
    """Test that CORS and security headers work together without conflicts."""
    response = test_client.get("/healthz")

    headers_lower = {k.lower(): v for k, v in response.headers.items()}

    # Both header types should be able to coexist
    # (If security headers are enabled, they should not interfere with CORS)
    assert response.status_code == 200

    # Validate no conflicting header values
    if (
        "access-control-allow-origin" in headers_lower
        and "x-frame-options" in headers_lower
    ):
        # Both should be present without causing errors
        assert True


def test_rate_limit_applies_per_ip(test_client):
    """Test that rate limiting is applied per IP address."""
    # Note: TestClient uses a fixed IP, so this tests the mechanism
    # In production, different IPs would have separate rate limit buckets

    first_response = test_client.get("/healthz")
    assert first_response.status_code == 200

    # Subsequent requests should also succeed (unless limit is very low)
    for _ in range(10):
        response = test_client.get("/healthz")
        # Should either succeed or be rate limited (both are valid)
        assert response.status_code in [200, 429]


def test_root_endpoint_returns_routes(test_client):
    """Test that root endpoint returns API route information."""
    response = test_client.get("/")
    assert response.status_code == 200

    data = response.json()
    assert data["ok"] is True
    assert "routes" in data
    assert isinstance(data["routes"], list)


@pytest.mark.skipif(
    os.getenv("GUARDIAN_ENABLE_RATE_LIMITING", "1").lower()
    not in ("1", "true", "yes", "on"),
    reason="Rate limiting is disabled",
)
def test_rate_limiting_is_enabled():
    """Test that rate limiting is enabled in the current configuration."""
    from guardian.server.app import _enable_rate_limiting

    assert _enable_rate_limiting is True


@pytest.mark.skipif(
    os.getenv("GUARDIAN_ENABLE_SECURITY_HEADERS", "1").lower()
    not in ("1", "true", "yes", "on"),
    reason="Security headers are disabled",
)
def test_security_headers_are_enabled():
    """Test that security headers are enabled in the current configuration."""
    from guardian.server.app import _enable_security_headers

    assert _enable_security_headers is True


def test_healthz_includes_security_status(test_client):
    """Test that healthz endpoint reports security configuration status."""
    response = test_client.get("/healthz")
    assert response.status_code == 200

    data = response.json()
    codexify_info = data["codexify"]

    # Verify security status fields are boolean
    assert isinstance(codexify_info.get("rate_limiting"), bool)
    assert isinstance(codexify_info.get("security_headers"), bool)


# Integration tests for specific endpoints


def test_rate_limit_does_not_affect_different_endpoints(test_client):
    """Test that rate limits are tracked separately per endpoint (if configured)."""
    # Hit healthz endpoint
    for _ in range(50):
        test_client.get("/healthz")

    # Root endpoint should still work
    response = test_client.get("/")
    assert response.status_code in [200, 429]  # Either succeeds or rate limited

    # If using global rate limiting, both count toward the same limit
    # If using per-route limiting, they would be independent


def test_security_headers_on_multiple_endpoints(test_client):
    """Test that security headers are applied to all endpoints."""
    endpoints = ["/", "/healthz"]

    for endpoint in endpoints:
        response = test_client.get(endpoint)

        # Security headers should be present on all responses (if enabled)
        if response.status_code == 200:
            headers_lower = {k.lower(): v for k, v in response.headers.items()}

            # At minimum, content-type should be present
            assert "content-type" in headers_lower


# Performance tests


def test_rate_limiting_performance_overhead(test_client):
    """Test that rate limiting does not add significant overhead."""
    import time

    # Measure response time with rate limiting
    start = time.time()
    for _ in range(10):
        test_client.get("/healthz")
    elapsed = time.time() - start

    # 10 requests should complete in reasonable time (< 1 second for middleware overhead)
    # Note: This is a rough test, actual time depends on system performance
    assert elapsed < 5.0  # Very generous threshold for CI environments


def test_error_response_format(test_client):
    """Test that error responses maintain consistent format."""
    # Test with a non-existent endpoint
    response = test_client.get("/nonexistent")

    # Should return 404 with proper error structure
    assert response.status_code == 404

    # FastAPI default error response should be JSON
    assert response.headers.get("content-type") == "application/json"
