"""
guardian.desktop_keyring

Provides a secure, OS‑level key storage abstraction for desktop
implementations of the Codexify system.

The implementation uses the `keyring` library to store a
device‑specific secret in the OS‑level credential store
(Keychain on macOS, Secret Service on Linux,
Credential Vault on Windows).

The key is stored as a base64‑encoded string.  The
`CodexifyDesktopKeyring` class also supports optional
re‑keying from a user‑provided passphrase (e.g. when
the desktop is accessed without a paired mobile
device) and optional biometric/OS password gating
via the underlying OS mechanisms.
"""

import base64
import os
from typing import Optional

import keyring
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Constants for the keyring service
_SERVICE_NAME = "CodexifyDesktopKeyring"
# The username is a constant because we only store a single
# device‑specific secret per user.
_USERNAME = "device_key"


class CodexifyDesktopKeyring:
    """
    Secure storage for a device‑specific secret key.

    The key is stored in the OS‑level credential store
    using the `keyring` library.  The stored value
    is a base64‑encoded 32‑byte key (AES‑256 key).

    The class provides:
    * `store_key` – store a raw 32‑byte key.
    * `retrieve_key` – retrieve the stored key.
    * `delete_key` – remove the stored key.
    * `rekey_from_passphrase` – derive a new key from a
      user‑provided passphrase (e.g. for recovery).
    """

    def __init__(self):
        # The key is lazily loaded; we keep a cached copy
        # to avoid repeated keyring lookups.
        self._cached_key: Optional[bytes] = None

    # -----------------------------------------------------------------
    # Helper methods
    # -----------------------------------------------------------------
    @staticmethod
    def _b64_encode(data: bytes) -> str:
        return base64.b64encode(data).decode("utf-8")

    @staticmethod
    def _b64_decode(data: str) -> bytes:
        return base64.b64decode(data.encode("utf-8"))

    # -----------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------
    def store_key(self, key: bytes) -> None:
        """
        Store a 32‑byte key in the OS keyring.

        Args:
            key: 32‑byte raw key (AES‑256 key material).
        """
        if not isinstance(key, (bytes, bytearray)):
            raise TypeError("Key must be bytes")
        if len(key) != 32:
            raise ValueError("Key must be 32 bytes for AES‑256")
        encoded = self._b64_encode(key)
        keyring.set_password(_SERVICE_NAME, _USERNAME, encoded)
        self._cached_key = key

    def retrieve_key(self) -> bytes:
        """
        Retrieve the stored key.  Raises a
        `keyring.errors.PasswordDeleteError` if the key
        does not exist.
        """
        if self._cached_key is not None:
            return self._cached_key
        encoded = keyring.get_password(_SERVICE_NAME, _USERNAME)
        if encoded is None:
            raise RuntimeError("No device key stored in keyring")
        key = self._b64_decode(encoded)
        if len(key) != 32:
            raise RuntimeError("Stored key is malformed")
        self._cached_key = key
        return key

    def delete_key(self) -> None:
        """
        Delete the stored key from the OS keyring.
        """
        keyring.delete_password(_SERVICE_NAME, _USERNAME)
        self._cached_key = None

    # -----------------------------------------------------------------
    # Rekeying from a passphrase
    # -----------------------------------------------------------------
    @staticmethod
    def _derive_key_from_passphrase(
        passphrase: str,
        salt: bytes,
        iterations: int = 200_000,
    ) -> bytes:
        """
        Derive a 32‑byte key from a passphrase using PBKDF2‑HMAC‑SHA256.

        Args:
            passphrase: User‑provided passphrase.
            salt: 16‑byte random salt.
            iterations: Number of PBKDF2 iterations.

        Returns:
            32‑byte derived key.
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=iterations,
            backend=default_backend(),
        )
        return kdf.derive(passphrase.encode("utf-8"))

    def rekey_from_passphrase(self, passphrase: str) -> bytes:
        """
        Generate a new device key from a passphrase and
        store it in the keyring.  The method returns
        the newly generated key.

        The method also stores the salt used for
        derivation in a local file
        `~/.codexify_desktop_key_salt` so that the
        same passphrase can be used for recovery.
        """
        # Generate a random 16‑byte salt
        salt = os.urandom(16)
        new_key = self._derive_key_from_passphrase(passphrase, salt)
        self.store_key(new_key)

        # Persist the salt (not secret) for later recovery
        salt_path = os.path.expanduser("~/.codexify_desktop_key_salt")
        with open(salt_path, "wb") as f:
            f.write(salt)

        return new_key

    def load_salt_for_recovery(self) -> Optional[bytes]:
        """
        Load the stored salt for passphrase recovery.
        Returns None if the salt file does not exist.
        """
        salt_path = os.path.expanduser("~/.codexify_desktop_key_salt")
        if not os.path.exists(salt_path):
            return None
        with open(salt_path, "rb") as f:
            return f.read()
