# guardian/identity.py

import base64
import hashlib
import json
import os
from datetime import datetime
from typing import Dict

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

IDENTITY_DIR = "/app/guardian/identity"
IDENTITY_FILE = os.path.join(IDENTITY_DIR, "user.json")


def _generate_identity() -> Dict:
    """
    Generate a self-certifying Codexify identity.
    The user_id is derived from the public key hash.
    """
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )

    user_id = hashlib.sha256(public_bytes).hexdigest()

    return {
        "user_id": f"user_{user_id}",
        "created_at": datetime.utcnow().isoformat() + "Z",
        "key_version": 1,
        "public_key": base64.b64encode(public_bytes).decode("utf-8"),
        "private_key": base64.b64encode(private_bytes).decode("utf-8"),
        "devices": [],
    }


def get_or_create_user() -> Dict:
    """
    Returns the canonical Codexify user identity.
    Creates it on first run.
    """
    if os.path.exists(IDENTITY_FILE):
        with open(IDENTITY_FILE) as f:
            return json.load(f)

    os.makedirs(IDENTITY_DIR, exist_ok=True)

    identity = _generate_identity()

    with open(IDENTITY_FILE, "w") as f:
        json.dump(identity, f, indent=2)

    return identity


def get_user_id() -> str:
    """
    Convenience accessor for the canonical user_id.
    """
    return get_or_create_user()["user_id"]
