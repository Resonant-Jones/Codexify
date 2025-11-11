"""
Prometheus Metrics
~~~~~~~~~~~~~~~~~~

Prometheus-compatible metrics collection for Codexify backend monitoring.
Provides counters, gauges, and metric export endpoints.
"""

from prometheus_client import Counter, Gauge, generate_latest, CollectorRegistry, CONTENT_TYPE_LATEST

# Custom registry to avoid conflicts with default registry
registry = CollectorRegistry()

# Request counter - tracks total HTTP requests by method and endpoint
REQUEST_COUNT = Counter(
    "codexify_requests_total",
    "Total number of HTTP requests handled",
    ["method", "endpoint"],
    registry=registry,
)

# Database backend gauge - 1 for Postgres, 0 for SQLite
DB_BACKEND_GAUGE = Gauge(
    "codexify_db_backend",
    "Current active database backend (1=Postgres, 0=SQLite)",
    registry=registry,
)


def set_db_backend(backend: str) -> None:
    """
    Set the database backend metric value.

    Args:
        backend: Database backend name ("postgres" or "sqlite")
    """
    if backend.lower() == "postgres":
        DB_BACKEND_GAUGE.set(1)
    else:
        DB_BACKEND_GAUGE.set(0)


# Export all prometheus-client exports for convenience
__all__ = [
    "registry",
    "REQUEST_COUNT",
    "DB_BACKEND_GAUGE",
    "set_db_backend",
    "generate_latest",
    "CONTENT_TYPE_LATEST",
]
