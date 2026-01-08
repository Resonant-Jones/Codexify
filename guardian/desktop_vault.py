"""
Desktop Vault module for Codexify: Codexify.

Provides AES‑256‑GCM encryption/decryption of the
user’s IDDB (SQLite file) and handles re‑keying,
deletion, and optional cloud sync.

The API mirrors the mobile `CodexifyVault` so that
the same contract can be used by the backend
or any desktop client.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .desktop_keyring import CodexifyDesktopKeyring


class CodexifyDesktopVault:
    """
    Manage an encrypted IDDB blob on the local filesystem.
    The vault file is a binary blob containing the
    encrypted SQLite database.
    """

    def __init__(
        self,
        keyring: CodexifyDesktopKeyring | None = None,
        vault_path: str = "iddb_vault.bin",
    ) -> None:
        self.keyring = keyring or CodexifyDesktopKeyring()
        self.vault_path = Path(vault_path)

    # ------------------------------------------------------------------
    # Encryption / Decryption
    # ------------------------------------------------------------------
    def encrypt_and_store(
        self,
        plaintext: bytes,
        passphrase: str,
        associated_data: bytes | None = None,
    ) -> None:
        """
        Encrypt ``plaintext`` with a key derived from the
        passphrase and store the ciphertext to
        ``self.vault_path``. ``associated_data`` is
        optional additional authenticated data.
        """
        key = self.keyring.derive_key(passphrase)
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)  # 96‑bit nonce for GCM
        ciphertext = aesgcm.encrypt(nonce, plaintext, associated_data)

        # Store nonce + ciphertext
        with self.vault_path.open("wb") as f:
            f.write(nonce + ciphertext)

    def decrypt(
        self, passphrase: str, associated_data: bytes | None = None
    ) -> bytes:
        """
        Decrypt the vault using ``passphrase``.
        Returns the plaintext bytes.
        """
        if not self.vault_path.is_file():
            raise FileNotFoundError("Vault file does not exist.")
        key = self.keyring.derive_key(passphrase)
        aesgcm = AESGCM(key)

        with self.vault_path.open("rb") as f:
            data = f.read()
        nonce = data[:12]
        ciphertext = data[12:]
        return aesgcm.decrypt(nonce, ciphertext, associated_data)

    # ------------------------------------------------------------------
    # Rekeying
    # ------------------------------------------------------------------
    def rekey(self, old_passphrase: str, new_passphrase: str) -> None:
        """
        Re‑encrypt the vault with a new passphrase.
        """
        plaintext = self.decrypt(old_passphrase)
        self.encrypt_and_store(plaintext, new_passphrase)

    # ------------------------------------------------------------------
    # Deletion / Wipe
    # ------------------------------------------------------------------
    def delete_vault(self) -> None:
        """Securely delete the vault file."""
        if self.vault_path.is_file():
            size = self.vault_path.stat().st_size
            with self.vault_path.open("wb") as f:
                f.write(os.urandom(size))
            self.vault_path.unlink()

    # ------------------------------------------------------------------
    # Cloud sync (placeholder)
    # ------------------------------------------------------------------
    def upload_to_cloud(self, endpoint_url: str, auth_token: str) -> None:
        """
        Upload the encrypted vault to a cloud endpoint.
        Placeholder – implement with your chosen backend
        (e.g., Firebase, Turso, S3).
        """
        with self.vault_path.open("rb") as f:
            blob = f.read()
        # Example using ``requests``:
        # import requests
        # headers = {"Authorization": f"Bearer {auth_token}"}
        # requests.post(endpoint_url, data=blob, headers=headers)

    def download_from_cloud(self, endpoint_url: str, auth_token: str) -> None:
        """
        Download the encrypted vault from a cloud endpoint.
        """
        # Example using ``requests``:
        # import requests
        # headers = {"Authorization": f"Bearer {auth_token}"}
        # response = requests.get(endpoint_url, headers=headers)
        # response.raise_for_status()
        # with self.vault_path.open("wb") as f:
        #     f.write(response.content)
