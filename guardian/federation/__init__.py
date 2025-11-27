"""Federation module for cross-node collaboration.

Enables secure session exchange and relay channels between
Codexify nodes using signed manifests and JWT tokens.
"""

from .manager import FederationManager
from .manifest import NodeManifest, generate_keypair, verify_manifest

__all__ = [
    "NodeManifest",
    "verify_manifest",
    "generate_keypair",
    "FederationManager",
]
