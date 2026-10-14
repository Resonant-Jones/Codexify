"""Configuration contract tests.

Every rule must fail closed: a misconfigured adapter must refuse to start
rather than silently degrade.
"""

from __future__ import annotations

import pytest

from guardian.mcp_memory.config import (
    DEFAULT_TIMEOUT,
    ENV_API_KEY,
    ENV_BASE_URL,
    ENV_GUARDIAN_API_KEY,
    ENV_TIMEOUT,
    ENV_USER_ID,
    MAX_TIMEOUT,
    load_config,
)
from guardian.mcp_memory.errors import ConfigurationError


def _env(**overrides: str) -> dict[str, str]:
    base = {
        ENV_BASE_URL: "http://127.0.0.1:8010",
        ENV_API_KEY: "test-key",
        "GUARDIAN_AUTH_MODE": "local",
    }
    for key, value in overrides.items():
        if value is None:
            base.pop(key, None)
        else:
            base[key] = value
    return base


def test_explicit_base_url_is_required() -> None:
    with pytest.raises(ConfigurationError) as exc:
        load_config(_env(**{ENV_BASE_URL: None}))
    assert "no default" in exc.value.message.lower()


def test_no_implicit_port_8000_default() -> None:
    """Port 8000 belongs to Whoosh'd; the adapter must never assume it."""
    with pytest.raises(ConfigurationError):
        load_config(_env(**{ENV_BASE_URL: None}))
    # And a config built without a default must not silently pick a port.
    cfg = load_config(_env())
    assert cfg.origin != "http://127.0.0.1:8000"


@pytest.mark.parametrize(
    "host",
    ["example.com", "10.0.0.5", "127.0.0.1.evil.com", "192.168.1.10", "::ffff:8.8.8.8"],
)
def test_non_loopback_hosts_are_rejected(host: str) -> None:
    with pytest.raises(ConfigurationError) as exc:
        load_config(_env(**{ENV_BASE_URL: f"http://{host}:8010"}))
    assert "loopback" in exc.value.message.lower()


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "127.0.0.2", "[::1]"])
def test_loopback_hosts_are_accepted(host: str) -> None:
    cfg = load_config(_env(**{ENV_BASE_URL: f"http://{host}:8010"}))
    assert cfg.origin.startswith("http://")


def test_missing_api_key_fails() -> None:
    with pytest.raises(ConfigurationError) as exc:
        load_config(_env(**{ENV_API_KEY: None}))
    assert ENV_API_KEY in exc.value.message


def test_api_key_falls_back_to_guardian_api_key() -> None:
    cfg = load_config(_env(**{ENV_API_KEY: None, ENV_GUARDIAN_API_KEY: "fallback-key"}))
    assert cfg.api_key == "fallback-key"


@pytest.mark.parametrize(
    "url",
    [
        "http://user:pass@127.0.0.1:8010",
        "http://127.0.0.1:8010?token=abc",
        "http://127.0.0.1:8010#frag",
        "http://127.0.0.1:8010/prefix",
    ],
)
def test_url_credential_query_fragment_and_prefix_rejected(url: str) -> None:
    with pytest.raises(ConfigurationError):
        load_config(_env(**{ENV_BASE_URL: url}))


def test_non_http_scheme_rejected() -> None:
    with pytest.raises(ConfigurationError):
        load_config(_env(**{ENV_BASE_URL: "https://127.0.0.1:8010"}))


def test_timeout_default_and_bounds() -> None:
    assert load_config(_env()).timeout == DEFAULT_TIMEOUT
    assert load_config(_env(**{ENV_TIMEOUT: "2.5"})).timeout == 2.5
    with pytest.raises(ConfigurationError):
        load_config(_env(**{ENV_TIMEOUT: "0"}))
    with pytest.raises(ConfigurationError):
        load_config(_env(**{ENV_TIMEOUT: str(MAX_TIMEOUT + 1)}))
    with pytest.raises(ConfigurationError):
        load_config(_env(**{ENV_TIMEOUT: "not-a-number"}))


def test_populated_user_id_is_rejected_not_ignored() -> None:
    """A populated identity override must fail loudly, never pass silently."""
    with pytest.raises(ConfigurationError) as exc:
        load_config(_env(**{ENV_USER_ID: "someone-else"}))
    assert ENV_USER_ID in exc.value.message


@pytest.mark.parametrize("value", ["", "   "])
def test_empty_user_id_is_accepted(value: str) -> None:
    cfg = load_config(_env(**{ENV_USER_ID: value}))
    assert cfg.api_key == "test-key"


@pytest.mark.parametrize(
    "mode", ["remote", "cloud", "hosted", "public", "prod", "production", "REMOTE"]
)
def test_remote_auth_modes_rejected(mode: str) -> None:
    with pytest.raises(ConfigurationError) as exc:
        load_config(_env(**{"GUARDIAN_AUTH_MODE": mode}))
    assert "local" in exc.value.message.lower()


def test_public_allowlist_exposure_rejected() -> None:
    with pytest.raises(ConfigurationError):
        load_config(_env(**{"GUARDIAN_EXPOSURE_MODE": "public_allowlist"}))


def test_unknown_auth_mode_defaults_to_local_for_this_process() -> None:
    """Unknown values are not treated as remote here; Guardian decides."""
    cfg = load_config(_env(**{"GUARDIAN_AUTH_MODE": "somethingelse"}))
    assert cfg.api_key == "test-key"


def test_validation_errors_use_invalid_configuration_code() -> None:
    with pytest.raises(ConfigurationError) as exc:
        load_config(_env(**{ENV_BASE_URL: None}))
    assert exc.value.code == "invalid_configuration"
