"""Memory Key Vault
=================

Encrypts narrative summaries at rest with per-user keys. Keys can
be rotated and old ciphertext will be re-encrypted using the new
key. Data is kept in-memory to avoid persistent storage.

Usage example::

    from guardian.modules.memory_key_vault import MemoryKeyVault
    from cryptography.fernet import Fernet

    vault = MemoryKeyVault()
    key = Fernet.generate_key()
    vault.set_user_key("alice", key)
    vault.store_summary("alice", "Short summary")
    text = vault.get_summary("alice")
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from cryptography.fernet import Fernet
from pydantic import BaseModel, Field, validator


class VaultEntry(BaseModel):
    """Encrypted summary blob."""

    user_id: str = Field(..., description="User identifier")
    ciphertext: bytes = Field(..., description="Encrypted data")

    @validator("ciphertext")
    def ensure_bytes(cls, value: bytes) -> bytes:  # noqa: D401
        """Ensure ciphertext is bytes."""
        if not isinstance(value, (bytes, bytearray)):
            raise TypeError("ciphertext must be bytes")
        return bytes(value)


class MemoryKeyVault:
    """Simple in-memory vault for encrypted summaries."""

    def __init__(self) -> None:
        self._keys: Dict[str, Fernet] = {}
        self._store: Dict[str, VaultEntry] = {}

    def set_user_key(self, user_id: str, key: bytes) -> None:
        """Register/replace a user's encryption key."""
        self._keys[user_id] = Fernet(key)

    def store_summary(self, user_id: str, summary: str) -> None:
        """Encrypt and store a narrative summary."""
        if user_id not in self._keys:
            raise KeyError("missing key for user")
        f = self._keys[user_id]
        self._store[user_id] = VaultEntry(
            user_id=user_id, ciphertext=f.encrypt(summary.encode())
        )

    def get_summary(self, user_id: str) -> str:
        """Decrypt and return a stored summary."""
        if user_id not in self._keys or user_id not in self._store:
            raise KeyError("missing summary or key")
        f = self._keys[user_id]
        entry = self._store[user_id]
        return f.decrypt(entry.ciphertext).decode()

    def rotate_key(self, user_id: str, new_key: bytes) -> None:
        """Rotate encryption key while preserving stored data."""
        if user_id not in self._keys:
            raise KeyError("missing key for user")
        f_old = self._keys[user_id]
        entry = self._store.get(user_id)
        plaintext = f_old.decrypt(entry.ciphertext) if entry else b""
        f_new = Fernet(new_key)
        self._keys[user_id] = f_new
        if entry:
            self._store[user_id] = VaultEntry(
                user_id=user_id, ciphertext=f_new.encrypt(plaintext)
            )
