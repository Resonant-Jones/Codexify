"""Tests for Prometheus metrics endpoints."""

import pytest
from fastapi.testclient import TestClient


def test_metrics_endpoint_prometheus(test_client):
    """Test that /metrics endpoint returns Prometheus-compatible metrics."""
    res = test_client.get("/metrics")
    assert res.status_code == 200
    assert (
        "codexify_requests_total" in res.text
        or "codexify_db_backend" in res.text
    )
    # Verify Prometheus content type
    assert "text/plain" in res.headers.get("content-type", "")


def test_metrics_endpoint_unauthenticated(test_client):
    """Test that /metrics endpoint is accessible without API key."""
    # No headers, should still work
    res = test_client.get("/metrics")
    assert res.status_code == 200


def test_health_deps_json_format(test_client):
    """Test /health/deps with default JSON format."""
    res = test_client.get("/health/deps")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "db_backend" in data
    assert "api_key_masked" in data


def test_health_deps_prometheus_format(test_client):
    """Test /health/deps with format=prometheus."""
    res = test_client.get("/health/deps?format=prometheus")
    assert res.status_code == 200
    # Should return Prometheus-compatible metrics
    assert "text/plain" in res.headers.get("content-type", "")
    # Should contain metric name
    assert "codexify" in res.text.lower() or "#" in res.text


def test_health_deps_invalid_format(test_client):
    """Test /health/deps with invalid format parameter."""
    res = test_client.get("/health/deps?format=invalid")
    # Should default to JSON or handle gracefully
    assert res.status_code == 200
    # Try to parse as JSON (default behavior)
    try:
        data = res.json()
        assert "status" in data
    except Exception:
        # If it returns Prometheus format, that's also acceptable
        assert "text/plain" in res.headers.get("content-type", "")


def test_db_backend_gauge_initialization(test_client):
    """Test that DB backend gauge is initialized and exposed."""
    res = test_client.get("/metrics")
    assert res.status_code == 200
    # Check that the DB backend metric is present
    assert "codexify_db_backend" in res.text


def test_health_endpoint_basic(test_client):
    """Test basic /health endpoint still works."""
    res = test_client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"


def test_health_chat_endpoint(test_client):
    """Test /health/chat endpoint still works."""
    res = test_client.get("/health/chat")
    assert res.status_code == 200
    data = res.json()
    assert "backend" in data
    assert "status" in data
    assert "redis" in data
    assert "worker" in data
    assert "notes" in data
    assert "completion_service" in data
    completion = data["completion_service"]
    assert "redis_reachable" in completion
    assert "enqueue_test_ok" in completion
    assert "worker_heartbeat_detected" in completion
    assert "worker_heartbeat_age_seconds" in completion
    assert "worker_heartbeat_status" in completion
    assert data["status"] in {"healthy", "degraded", "unhealthy"}
    assert data["redis"] in {"ok", "unhealthy"}
    assert data["worker"]["status"] in {"fresh", "stale", "dead"}
    assert "heartbeat_age_seconds" in data["worker"]


def test_health_vector_endpoint(test_client):
    """Test /health/vector endpoint verifies vector store connectivity."""
    res = test_client.get("/health/vector")
    assert res.status_code == 200
    data = res.json()
    assert data.get("ok") is True
    assert data.get("status") == "ok"
    assert "backend" in data
    assert data.get("source") in ("shared", "local", "probe")
    assert data.get("added") == 1
    assert data.get("matches", 0) >= 1
