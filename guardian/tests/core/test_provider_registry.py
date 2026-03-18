from itertools import combinations

import requests

from guardian.core.config import Settings
from guardian.core.provider_registry import (
    DISABLED_PROVIDERS,
    DISCOVERY_BACKED_PROVIDERS,
    LOCAL_ONLY_PROVIDERS,
    PROVIDER_GOVERNANCE,
    PROVIDER_LABELS,
    PROVIDER_ORDER,
    STATIC_AUTHORIZED_PROVIDERS,
    get_provider_governance,
    get_provider_model_descriptors,
    provider_availability,
    resolve_provider_capability,
    resolve_provider_for_model,
    validate_provider_model_selection,
)


def _settings(**overrides) -> Settings:
    defaults = {
        "ALLOW_CLOUD_PROVIDERS": True,
        "CODEXIFY_LOCAL_ONLY_MODE": False,
        "CODEXIFY_EGRESS_ALLOWLIST": (
            "openai,groq,alibaba,minimax,anthropic,gemini"
        ),
        "LOCAL_BASE_URL": "http://127.0.0.1:11434/v1",
    }
    defaults.update(overrides)
    return Settings(_env_file=None, **defaults)


def test_every_known_provider_is_classified_exactly_once():
    known_providers = set(PROVIDER_ORDER)
    assert set(PROVIDER_GOVERNANCE) == known_providers

    categories = (
        DISCOVERY_BACKED_PROVIDERS,
        STATIC_AUTHORIZED_PROVIDERS,
        LOCAL_ONLY_PROVIDERS,
        DISABLED_PROVIDERS,
    )

    for left, right in combinations(categories, 2):
        assert left.isdisjoint(right)

    classified = frozenset().union(*categories)
    assert classified == known_providers


def test_provider_governance_audit_matches_current_contract():
    assert DISCOVERY_BACKED_PROVIDERS == frozenset(
        {"openai", "groq", "alibaba", "minimax"}
    )
    assert STATIC_AUTHORIZED_PROVIDERS == frozenset()
    assert LOCAL_ONLY_PROVIDERS == frozenset({"local"})
    assert DISABLED_PROVIDERS == frozenset({"anthropic", "gemini"})


def test_local_only_provider_is_marked_explicitly():
    contract = get_provider_governance("local")
    assert contract is not None
    assert contract["classification"] == "local_only"
    assert contract["local_only"] is True
    assert contract["live_discovery_expected"] is True
    assert contract["routing_requires_discovered_inventory"] is True
    assert contract["configured_defaults_allowed_on_discovery_failure"] is True


def test_static_authorized_providers_are_distinct_from_discovery_backed():
    assert STATIC_AUTHORIZED_PROVIDERS.isdisjoint(DISCOVERY_BACKED_PROVIDERS)


def test_disabled_providers_preserve_current_unauthorized_behavior():
    settings = _settings()

    unavailable, reason = provider_availability("anthropic", settings)
    assert unavailable is False
    assert reason == "Missing provider credentials"

    unavailable, reason = provider_availability("gemini", settings)
    assert unavailable is False
    assert reason == "Missing provider credentials"


def test_disabled_providers_remain_unsupported_when_forced_authorized():
    settings = _settings()

    unavailable, reason = provider_availability(
        "anthropic", settings, authorized=True
    )
    assert unavailable is False
    assert reason == "Unsupported provider"

    unavailable, reason = provider_availability(
        "gemini", settings, authorized=True
    )
    assert unavailable is False
    assert reason == "Unsupported provider"


def test_provider_governance_contract_is_internally_consistent():
    for provider_id, contract in PROVIDER_GOVERNANCE.items():
        assert contract["provider"] == provider_id
        assert contract["display_name"] == PROVIDER_LABELS[provider_id]
        assert get_provider_governance(provider_id) == contract

        classification = contract["classification"]
        local_only = contract["local_only"]

        if classification == "discovery_backed":
            assert contract["live_discovery_expected"] is True
            assert contract["routing_requires_discovered_inventory"] is True
            assert (
                contract["configured_defaults_allowed_on_discovery_failure"]
                is True
            )
            assert local_only is False
            continue

        if classification == "static_authorized":
            assert contract["live_discovery_expected"] is False
            assert contract["routing_requires_discovered_inventory"] is False
            assert local_only is False
            continue

        if classification == "local_only":
            assert local_only is True
            assert (
                contract["configured_defaults_allowed_on_discovery_failure"]
                is True
            )
            continue

        assert classification == "disabled"
        assert contract["live_discovery_expected"] is False
        assert contract["routing_requires_discovered_inventory"] is False
        assert (
            contract["configured_defaults_allowed_on_discovery_failure"]
            is False
        )
        assert local_only is False


class _MockResponse:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def json(self) -> dict:
        return self._payload


def _provider_settings(**overrides) -> Settings:
    base = {
        "ALLOW_CLOUD_PROVIDERS": True,
        "CODEXIFY_LOCAL_ONLY_MODE": False,
        "CODEXIFY_EGRESS_ALLOWLIST": "alibaba,minimax",
        "ALIBABA_API_KEY": "alibaba-key",
        "ALIBABA_API_BASE": "https://dashscope-us.aliyuncs.com/compatible-mode/v1",
        "MINIMAX_API_KEY": "minimax-key",
        "MINIMAX_API_BASE": "https://api.minimax.local/v1",
        "MINIMAX_API_FLAVOR": "openai",
    }
    base.update(overrides)
    return Settings(**base)


def test_resolve_provider_capability_discovers_alibaba_models_live(
    monkeypatch,
):
    def fake_get(url, headers, timeout):
        assert (
            url == "https://dashscope-us.aliyuncs.com/compatible-mode/v1/models"
        )
        assert headers["Authorization"] == "Bearer alibaba-key"
        assert timeout == 3.0
        return _MockResponse(
            {
                "data": [
                    {
                        "id": "qwen-max",
                        "contextWindow": 32768,
                        "capabilities": {"tools": True},
                    },
                    {
                        "id": "text-embedding-v3",
                        "task": "embedding",
                    },
                ]
            }
        )

    monkeypatch.setattr(
        "guardian.core.provider_registry.requests.get", fake_get
    )

    settings = _provider_settings()
    capability = resolve_provider_capability("alibaba", settings)

    assert capability["authorized"] is True
    assert capability["available"] is True
    assert capability["enabled"] is True
    assert capability["models"] == [
        {
            "id": "qwen-max",
            "displayName": "qwen-max",
            "contextWindow": 32768,
            "capabilities": {"tools": True},
        }
    ]
    assert capability["model_index"]["state"] == "available"
    assert capability["model_index"]["model_count"] == 1


def test_minimax_discovery_failure_degrades_without_fabricating_models(
    monkeypatch,
):
    def fake_get(url, headers, timeout):
        assert url == "https://api.minimax.local/v1/models"
        assert headers["Authorization"] == "Bearer minimax-key"
        assert timeout == 3.0
        raise requests.exceptions.Timeout("timed out")

    monkeypatch.setattr(
        "guardian.core.provider_registry.requests.get", fake_get
    )

    settings = _provider_settings(
        ALIBABA_API_KEY=None,
        ALIBABA_API_BASE=None,
        MINIMAX_MODEL="minimax-chat",
    )
    capability = resolve_provider_capability("minimax", settings)

    assert capability["authorized"] is True
    assert capability["available"] is True
    assert capability["enabled"] is True
    assert capability["models"] == []
    assert capability["default_model"] == "minimax-chat"
    assert capability["model_index"]["state"] == "degraded"
    assert "timed out" in capability["model_index"]["reason"].lower()

    valid, reason = validate_provider_model_selection(
        provider_id="minimax",
        model_id="minimax-chat",
        settings=settings,
    )
    assert valid is True
    assert reason is None

    valid, reason = validate_provider_model_selection(
        provider_id="minimax",
        model_id="not-real",
        settings=settings,
    )
    assert valid is False
    assert "not-real" in str(reason)


def test_dynamic_provider_without_default_becomes_unavailable_when_discovery_fails(
    monkeypatch,
):
    monkeypatch.setattr(
        "guardian.core.provider_registry.requests.get",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            requests.exceptions.ConnectionError("boom")
        ),
    )

    settings = _provider_settings(ALIBABA_MODEL=None)
    capability = resolve_provider_capability("alibaba", settings)

    assert capability["available"] is False
    assert capability["enabled"] is False
    assert capability["models"] == []
    assert capability["model_index"]["state"] == "degraded"
    assert "request failed" in capability["disabled_reason"].lower()


def test_resolve_provider_for_model_only_matches_discovered_dynamic_models(
    monkeypatch,
):
    monkeypatch.setattr(
        "guardian.core.provider_registry.requests.get",
        lambda *args, **kwargs: _MockResponse(
            {"data": [{"id": "minimax-chat"}, {"id": "abab7.5-chat"}]}
        ),
    )

    settings = _provider_settings(
        ALIBABA_API_KEY=None,
        ALIBABA_API_BASE=None,
        MINIMAX_MODEL="minimax-chat",
    )

    assert get_provider_model_descriptors("minimax", settings) == [
        {"id": "minimax-chat", "displayName": "minimax-chat"},
        {"id": "abab7.5-chat", "displayName": "abab7.5-chat"},
    ]
    assert (
        resolve_provider_for_model("minimax-chat", settings=settings)
        == "minimax"
    )
    assert resolve_provider_for_model("not-real", settings=settings) is None
