"""Connections control-plane package.

The Connections catalog is the canonical inventory behind the Settings
Connectors bay. It is an aggregation/projection surface: it never owns
runtime execution, credential storage, or authorization decisions.

See ``guardian/connections/catalog.py`` for the catalog contract and
``guardian/routes/connections.py`` for the read-only API projection.
"""

from guardian.connections.catalog import (
    ConnectionCatalogEntry,
    ConnectionFieldSpec,
    ConnectionRuntimeBinding,
    connections_by_category,
    get_catalog,
    get_connection,
)

__all__ = [
    "ConnectionCatalogEntry",
    "ConnectionFieldSpec",
    "ConnectionRuntimeBinding",
    "connections_by_category",
    "get_catalog",
    "get_connection",
]
