from __future__ import annotations

import pytest

from guardian.core.secret_broker import EnvSecretBroker, SecretBrokerError


def test_env_secret_broker_get_secret_matches_env(monkeypatch):
    broker = EnvSecretBroker()
    monkeypatch.setenv("CODEXIFY_SECRET_OPENAI_API_KEY", "secret-value")

    assert broker.get_secret("openai api key") == "secret-value"


def test_env_secret_broker_missing_secret_raises_controlled_error(monkeypatch):
    broker = EnvSecretBroker()
    monkeypatch.delenv("CODEXIFY_SECRET_MISSING_TOKEN", raising=False)

    with pytest.raises(SecretBrokerError) as exc:
        broker.get_secret("missing token")

    assert "expected env: CODEXIFY_SECRET_MISSING_TOKEN" in str(exc.value)


def test_env_secret_broker_error_message_redacts_secret_value(monkeypatch):
    broker = EnvSecretBroker()
    secret_value = "super-secret-value"
    monkeypatch.setenv("CODEXIFY_SECRET_TEST_TOKEN", secret_value)
    monkeypatch.delenv("CODEXIFY_SECRET_OTHER_TOKEN", raising=False)

    with pytest.raises(SecretBrokerError) as exc:
        broker.get_secret("other token")

    message = str(exc.value)
    assert "super-secret-value" not in message
