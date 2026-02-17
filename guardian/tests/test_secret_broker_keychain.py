from __future__ import annotations

import pytest

import guardian.core.secret_broker_keychain as keychain_broker
from guardian.core.secret_broker import SecretBrokerError
from guardian.core.secret_broker_keychain import KeychainSecretBroker


class _FakeFailBackend:
    pass


class _FakeSecureBackend:
    pass


class _FakeKeyringModule:
    def __init__(self, *, backend_name: str = "SecureKeyring") -> None:
        self._store: dict[tuple[str, str], str] = {}
        if backend_name == "FailKeyring":
            self._backend = _FakeFailBackend()
        else:
            self._backend = _FakeSecureBackend()

    def get_keyring(self):
        return self._backend

    def get_password(self, service: str, account: str):
        return self._store.get((service, account))

    def set_password(self, service: str, account: str, value: str):
        self._store[(service, account)] = value


def test_keychain_broker_reports_unavailable_when_keyring_missing(monkeypatch):
    monkeypatch.setattr(keychain_broker, "_load_keyring", lambda: None)
    broker = KeychainSecretBroker()

    assert broker.is_available() is False
    with pytest.raises(SecretBrokerError, match="install keyring"):
        broker.get_secret("token")


def test_keychain_broker_happy_path_with_fake_backend(monkeypatch):
    fake = _FakeKeyringModule()
    monkeypatch.setattr(keychain_broker, "_load_keyring", lambda: fake)
    broker = KeychainSecretBroker()

    assert broker.is_available() is True
    broker.set_secret("api_token", "secret-123")
    assert broker.get_secret("api_token") == "secret-123"


def test_keychain_broker_real_backend_smoke_or_skip():
    broker = KeychainSecretBroker()
    if not broker.is_available():
        pytest.skip("keyring backend not available")
    assert broker.is_available() is True
