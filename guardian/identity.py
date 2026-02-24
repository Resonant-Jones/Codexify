# guardian/identity.py

import base64
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

# Identity storage location
# - Allow explicit override via env for unusual deployments.
# - Otherwise, default to repository data/identity (gitignored).
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_IDENTITY_DIR = str(_PROJECT_ROOT / "data" / "identity")
_LEGACY_IDENTITY_FILE = (
    Path(__file__).resolve().parent / "identity" / "user.json"
)
IDENTITY_DIR = os.getenv("CODEXIFY_IDENTITY_DIR", _DEFAULT_IDENTITY_DIR)
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
        "created_at": datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
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

    # One-time migration from the legacy tracked location.
    if (
        "CODEXIFY_IDENTITY_DIR" not in os.environ
        and _LEGACY_IDENTITY_FILE.exists()
    ):
        with _LEGACY_IDENTITY_FILE.open() as f:
            identity = json.load(f)
        os.makedirs(IDENTITY_DIR, exist_ok=True)
        with open(IDENTITY_FILE, "w") as f:
            json.dump(identity, f, indent=2)
        return identity

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
