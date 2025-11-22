"""
Prometheus Metrics
~~~~~~~~~~~~~~~~~~

Prometheus-compatible metrics collection for Codexify backend monitoring.
Provides counters, gauges, and metric export endpoints.
"""

try:
    # Real Prometheus metrics (production / full env)
    from prometheus_client import (
        Counter,
        Gauge,
        generate_latest,
        CollectorRegistry,
        CONTENT_TYPE_LATEST,
    )
    PROMETHEUS_AVAILABLE = True
except Exception:  # ModuleNotFoundError or any import/runtime issue
    # Fallback: no-op metrics so code still imports and tests can run
    PROMETHEUS_AVAILABLE = False

    class _NoopMetric:
        def __init__(self, *args, **kwargs):
            # No-op metric placeholder used when prometheus_client
            # is not installed; all operations become inert.
            pass

        def labels(self, *args, **kwargs):
            # Preserve prometheus_client-style label API while doing nothing.
            return self

        def inc(self, *args, **kwargs):
            # Increment operation is a no-op in the shim.
            return self

        def dec(self, *args, **kwargs):
            # Decrement operation is a no-op in the shim.
            return self

        def observe(self, *args, **kwargs):
            # Histogram/summary observe call is a no-op in the shim.
            return self

        def set(self, *args, **kwargs):
            # Gauge-style set operation is a no-op in the shim.
            return self

    class _NoopRegistry:
        def __init__(self, *args, **kwargs):
            pass

        def register(self, *args, **kwargs):
            pass

    Counter = Gauge = _NoopMetric
    CollectorRegistry = _NoopRegistry

    def generate_latest(registry=None):
        # Minimal stub; real Prometheus returns bytes
        return b""

    CONTENT_TYPE_LATEST = "text/plain; charset=utf-8"
# Custom registry to avoid conflicts with default registry
registry = CollectorRegistry()

# Request counter - tracks total HTTP requests by method and endpoint
REQUEST_COUNT = Counter(
    "codexify_requests_total",
    "Total number of HTTP requests handled",
    ["method", "endpoint"],
    registry=registry,
)

# Database backend gauge - 1 for Postgres, 0 for unknown/legacy
DB_BACKEND_GAUGE = Gauge(
    "codexify_db_backend",
    "Current active database backend (1=Postgres, 0=unknown)",
    registry=registry,
)


def set_db_backend(backend: str) -> None:
    """
    Set the database backend metric value.

    Args:
        backend: Database backend name ("postgres" expected)
    """
    # Metrics are safe to call even when PROMETHEUS_AVAILABLE is False
    # because _NoopMetric implements the same surface API.
    try:
        is_postgres = backend.lower() == "postgres"
    except AttributeError:
        # Defensive: if backend is None or non-string, skip metric update.
        return

    DB_BACKEND_GAUGE.set(1 if is_postgres else 0)


# Export all prometheus-client exports for convenience
__all__ = [
    "registry",
    "REQUEST_COUNT",
    "DB_BACKEND_GAUGE",
    "set_db_backend",
    "generate_latest",
    "CONTENT_TYPE_LATEST",
]
