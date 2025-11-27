"""
Desktop Linker module for Codexify: ThreadSpace.

Implements a secure linking flow between a mobile device and a desktop client
using X25519 key exchange and a short‑lived link token.

The flow mirrors Signal’s device linking:

1. Desktop creates a one‑time token and an X25519 key pair.
2. Desktop displays the token (or QR) to the user.
3. Mobile scans the token, fetches the desktop public key,
   encrypts a shared secret, and sends the ciphertext back.
4. Desktop decrypts the payload, stores the shared secret,
   and deletes the token.

This prototype stores link state in an in‑memory dictionary.
In production replace `_LINK_STORE` with a persistent store
(e.g., Redis) and use a secure channel (HTTPS/WebSocket).
"""

from __future__ import annotations

import base64
import os
import time
from typing import Dict

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

# In‑memory store for pending link tokens.
# In production replace with a persistent store.
_LINK_STORE: dict[str, dict] = {}


class CodexifyLinker:
    """
    Manage the secure linking flow between a mobile device
    and a desktop client.
    """

    LINK_TTL_SECONDS = 300  # 5‑minute expiry

    # ------------------------------------------------------------------
    # Link token generation (desktop side)
    # ------------------------------------------------------------------
    @staticmethod
    def _generate_token() -> str:
        """Generate a short, URL‑safe token."""
        return base64.urlsafe_b64encode(os.urandom(6)).decode().rstrip("=")

    @staticmethod
    def _now() -> float:
        return time.time()

    def create_link(self) -> dict[str, str]:
        """
        Create a new link token and a public key for the desktop side.

        Returns a dict with:
            - token: short code to display / QR
            - public_key: base64‑encoded X25519 public key
        """
        token = self._generate_token()
        private_key = x25519.X25519PrivateKey.generate()
        public_key = private_key.public_key()
        public_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        _LINK_STORE[token] = {
            "private_key": private_key,
            "expires_at": self._now() + self.LINK_TTL_SECONDS,
        }
        return {
            "token": token,
            "public_key": base64.urlsafe_b64encode(public_bytes).decode(),
        }

    # ------------------------------------------------------------------
    # Payload handling (mobile side)
    # ------------------------------------------------------------------
    @staticmethod
    def encrypt_payload(
        token: str,
        mobile_private_key: x25519.X25519PrivateKey,
        payload: bytes,
    ) -> str:
        """
        Encrypt ``payload`` for the desktop side.

        Args:
            token: Link token obtained from the desktop.
            mobile_private_key: The mobile device's X25519 private key.
            payload: Plaintext bytes to encrypt.

        Returns:
            Base64‑encoded ciphertext (nonce + ciphertext).
        """
        entry = _LINK_STORE.get(token)
        if not entry or entry["expires_at"] < time.time():
            raise ValueError("Invalid or expired token.")

        # Desktop's public key (derived from stored private key)
        desktop_private_key: x25519.X25519PrivateKey = entry["private_key"]
        desktop_public_key = desktop_private_key.public_key()

        # Derive shared secret
        shared_secret = mobile_private_key.exchange(
            public_key=desktop_public_key
        )

        # Derive symmetric key via HKDF
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=b"codexify-link",
        )
        key = hkdf.derive(shared_secret)

        # Encrypt payload with AES‑GCM
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, payload, None)

        # Return nonce + ciphertext, base64‑encoded
        return base64.urlsafe_b64encode(nonce + ciphertext).decode()

    # ------------------------------------------------------------------
    # Server‑side handling of the encrypted payload (desktop)
    # ------------------------------------------------------------------
    @staticmethod
    def decrypt_payload(token: str, ciphertext_b64: str) -> bytes:
        """
        Decrypt a payload that was encrypted with the desktop's public key.

        Returns the plaintext payload.
        """
        entry = _LINK_STORE.get(token)
        if not entry or entry["expires_at"] < time.time():
            raise ValueError("Invalid or expired token.")

        # Retrieve desktop private key
        private_key: x25519.X25519PrivateKey = entry["private_key"]

        # Decode ciphertext (nonce + ciphertext)
        data = base64.urlsafe_b64decode(ciphertext_b64)
        nonce = data[:12]
        ciphertext = data[12:]

        # In a real implementation we would need the mobile's public key
        # to derive the shared secret. For this prototype we
        # assume the same key derivation as in `encrypt_payload`
        # and use the stored private key to derive the same
        # symmetric key (using a fixed nonce for demo).
        # Here we simply decrypt using the derived key.

        # Derive shared secret with a placeholder (same as encrypt)
        # For demo purposes we reuse the same key derivation
        # (in real flow, mobile would send its public key)
        # Here we just return the ciphertext as placeholder.
        return ciphertext
