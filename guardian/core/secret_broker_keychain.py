"""Optional keychain-backed secret broker."""

from __future__ import annotations

from typing import Any

from guardian.core.secret_broker import SecretBrokerError


def _load_keyring() -> Any | None:
    try:
        import keyring  # type: ignore
    except Exception:
        return None
    return keyring


class KeychainSecretBroker:
    """OS keychain-backed secret broker using keyring."""

    def __init__(self, *, service_name: str = "codexify") -> None:
        self.service_name = service_name

    def _require_keyring(self) -> Any:
        keyring = _load_keyring()
        if keyring is None:
            raise SecretBrokerError(
                "keychain secret store unavailable: install keyring"
            )
        return keyring

    def is_available(self) -> bool:
        keyring = _load_keyring()
        if keyring is None:
            return False
        try:
            backend = keyring.get_keyring()
        except Exception:
            return False

        if backend is None:
            return False

        backend_name = backend.__class__.__name__.lower()
        return "fail" not in backend_name and "null" not in backend_name

    def get_secret(self, secret_id: str) -> str:
        keyring = self._require_keyring()
        name = (secret_id or "").strip()
        if not name:
            raise SecretBrokerError("secret_id must be a non-empty identifier")

        value = keyring.get_password(self.service_name, name)
        if value is None or str(value).strip() == "":
            raise SecretBrokerError(
                f"secret '{name}' not found in keychain service '{self.service_name}'"
            )
        return str(value)

    def set_secret(self, secret_id: str, value: str) -> None:
        keyring = self._require_keyring()
        name = (secret_id or "").strip()
        if not name:
            raise SecretBrokerError("secret_id must be a non-empty identifier")
        keyring.set_password(self.service_name, name, value)
