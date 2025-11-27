"""Manifest model and signing/verification for federation nodes.

Nodes exchange signed manifests to establish trust and verify
capabilities before creating relay channels.
"""

import base64
import os
from typing import Optional

from pydantic import BaseModel, Field

try:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ed25519
except ImportError:
    raise ImportError("cryptography library required for federation signing")


class NodeManifest(BaseModel):
    """Manifest for a Codexify node in the federation.

    Contains node identity, capabilities, and relay endpoint.
    Can be signed to establish trust between peers.
    """

    node_id: str = Field(..., description="Unique identifier for this node")
    public_key: str = Field(
        ..., description="Base64-encoded Ed25519 public key"
    )
    capabilities: list[str] = Field(
        default_factory=lambda: ["share", "collab", "autosave"],
        description="List of capabilities this node supports",
    )
    relay_endpoint: str = Field(
        ..., description="WebSocket endpoint for relay connections"
    )
    signature: Optional[str] = Field(
        default=None,
        description="Base64-encoded Ed25519 signature of the manifest",
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "node_id": "node-alpha-001",
                "public_key": "base64encodedkey==",
                "capabilities": ["share", "collab", "autosave"],
                "relay_endpoint": "wss://codexify.example.com/api/federation/relay",
                "signature": "base64encodedsignature==",
            }
        }


def generate_keypair() -> tuple[str, str]:
    """Generate Ed25519 keypair for manifest signing.

    Returns:
        Tuple of (private_key_b64, public_key_b64) as base64-encoded strings
    """
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    private_b64 = base64.b64encode(
        private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )
    ).decode("utf-8")

    public_b64 = base64.b64encode(
        public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
    ).decode("utf-8")

    return private_b64, public_b64


def sign_manifest(manifest: NodeManifest, private_key_b64: str) -> str:
    """Sign a manifest with the node's private key.

    Args:
        manifest: The manifest to sign (signature field should be None)
        private_key_b64: Base64-encoded private key

    Returns:
        Base64-encoded signature
    """
    # Clear signature field before signing
    manifest_copy = manifest.copy()
    manifest_copy.signature = None

    # Create deterministic JSON representation
    manifest_json = manifest_copy.model_dump_json(
        exclude_none=True, by_alias=False
    )

    # Decode private key and sign
    private_key_bytes = base64.b64decode(private_key_b64)
    private_key = ed25519.Ed25519PrivateKey.from_private_bytes(
        private_key_bytes
    )
    signature = private_key.sign(manifest_json.encode("utf-8"))

    return base64.b64encode(signature).decode("utf-8")


def verify_manifest(
    manifest: NodeManifest, expected_signature: Optional[str] = None
) -> bool:
    """Verify a manifest's signature using its public key.

    Args:
        manifest: The manifest to verify
        expected_signature: Expected signature (if None, uses manifest.signature)

    Returns:
        True if signature is valid, False otherwise
    """
    signature_b64 = expected_signature or manifest.signature
    if not signature_b64:
        return False

    try:
        # Clear signature field before verifying
        manifest_copy = manifest.copy()
        manifest_copy.signature = None

        # Create deterministic JSON representation
        manifest_json = manifest_copy.model_dump_json(
            exclude_none=True, by_alias=False
        )

        # Decode public key and signature
        public_key_bytes = base64.b64decode(manifest.public_key)
        public_key = ed25519.Ed25519PublicKey.from_public_bytes(
            public_key_bytes
        )
        signature_bytes = base64.b64decode(signature_b64)

        # Verify signature
        public_key.verify(signature_bytes, manifest_json.encode("utf-8"))
        return True
    except (InvalidSignature, ValueError, base64.binascii.Error):
        return False


def load_node_keypair_from_env(
    private_key_env: str = "FEDERATION_PRIVATE_KEY",
    public_key_env: str = "FEDERATION_PUBLIC_KEY",
) -> tuple[Optional[str], Optional[str]]:
    """Load node keypair from environment variables.

    If keys don't exist in environment, generates and returns None
    (caller should store in env or config).

    Args:
        private_key_env: Environment variable name for private key
        public_key_env: Environment variable name for public key

    Returns:
        Tuple of (private_key_b64, public_key_b64) or (None, None) if not found
    """
    private_key = os.getenv(private_key_env)
    public_key = os.getenv(public_key_env)

    if private_key and public_key:
        return private_key, public_key

    return None, None
