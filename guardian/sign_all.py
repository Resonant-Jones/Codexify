"""
sign_all.py
Utility script for generating Ed25519 key pairs and signing manifests for all Codexify nodes.
This aligns with the federation_manifest specification (Task 12).
"""

import base64
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

logger = logging.getLogger(__name__)

KEYS_DIR = Path(__file__).parent / "keys"
KEYS_DIR.mkdir(exist_ok=True)


def generate_keypair(node_id: str):
    """Generate and persist an Ed25519 keypair for a given node."""
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    (KEYS_DIR / f"{node_id}_private.pem").write_bytes(private_bytes)
    (KEYS_DIR / f"{node_id}_public.pem").write_bytes(public_bytes)
    logger.info(f"Generated keypair for {node_id}")
    return private_key, public_key


def load_private_key(node_id: str):
    path = KEYS_DIR / f"{node_id}_private.pem"
    if not path.exists():
        raise FileNotFoundError(f"No private key found for {node_id}")
    return serialization.load_pem_private_key(path.read_bytes(), password=None)


def load_public_key(node_id: str):
    path = KEYS_DIR / f"{node_id}_public.pem"
    if not path.exists():
        raise FileNotFoundError(f"No public key found for {node_id}")
    return serialization.load_pem_public_key(path.read_bytes())


def sign_manifest(node_id: str, manifest: dict):
    """Sign a manifest dict with the node's private key."""
    private_key = load_private_key(node_id)
    manifest_bytes = json.dumps(manifest, sort_keys=True).encode()
    signature = private_key.sign(manifest_bytes)
    manifest["signature"] = base64.b64encode(signature).decode()
    manifest["signed_at"] = datetime.now(timezone.utc).isoformat()
    logger.info(f"Manifest signed for node {node_id}")
    return manifest


def verify_manifest_signature(manifest: dict, public_key_pem: bytes):
    """Verify a signed manifest using the provided public key."""
    try:
        public_key = serialization.load_pem_public_key(public_key_pem)
        signature = base64.b64decode(manifest["signature"])
        manifest_copy = {k: v for k, v in manifest.items() if k != "signature"}
        public_key.verify(
            json.dumps(manifest_copy, sort_keys=True).encode(), signature
        )
        return True
    except (InvalidSignature, KeyError, ValueError):
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Sign or verify Codexify federation manifests."
    )
    parser.add_argument("--node-id", required=True, help="Node identifier")
    parser.add_argument(
        "--manifest", required=False, help="Path to manifest JSON"
    )
    parser.add_argument(
        "--verify", action="store_true", help="Verify a signed manifest"
    )
    args = parser.parse_args()

    if args.verify:
        if not args.manifest:
            logger.warning("Must provide --manifest for verification")
        else:
            manifest_data = json.loads(Path(args.manifest).read_text())
            pub_key = load_public_key(args.node_id)
            valid = verify_manifest_signature(
                manifest_data,
                pub_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo,
                ),
            )
            if valid:
                logger.info("Signature valid")
            else:
                logger.error("Invalid signature")
        # Sign manifest
        manifest_data = (
            json.loads(Path(args.manifest).read_text())
            if args.manifest
            else {
                "node_id": args.node_id,
                "capabilities": ["share", "collab", "autosave"],
                "relay_endpoint": "wss://relay.codexify.net/api/federation/relay",
            }
        )
        signed_manifest = sign_manifest(args.node_id, manifest_data)
        out_path = Path(f"{args.node_id}_manifest.json")
        out_path.write_text(json.dumps(signed_manifest, indent=2))
        logger.info(f"Signed manifest written to {out_path}")
