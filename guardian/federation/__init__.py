"""Federation module for cross-node collaboration.

Enables secure session exchange and relay channels between
Codexify nodes using signed manifests and JWT tokens.
"""

from .manifest import NodeManifest, verify_manifest, generate_keypair
from .manager import FederationManager

__all__ = [
    "NodeManifest",
    "verify_manifest",
    "generate_keypair",
    "FederationManager",
]
