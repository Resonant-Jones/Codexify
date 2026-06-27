"""Federation module for cross-node collaboration.

Enables secure session exchange and relay channels between
Codexify nodes using signed manifests and JWT tokens.
"""

from importlib import import_module
from typing import TYPE_CHECKING

from .manifest import NodeManifest, generate_keypair, verify_manifest

__all__ = [
    "NodeManifest",
    "verify_manifest",
    "generate_keypair",
    "FederationManager",
]

if TYPE_CHECKING:
    from .manager import FederationManager as FederationManager


def __getattr__(name: str):
    if name == "FederationManager":
        manager = import_module("guardian.federation.manager")
        return manager.FederationManager
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
