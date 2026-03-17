import requests

from guardian.core.config import ROUTER_SUPPORTED_LLM_PROVIDERS, Settings
from guardian.core.provider_registry import (
    PROVIDER_ORDER,
    get_provider_model_descriptors,
    provider_allows_default_during_degraded_discovery,
    provider_governance,
    provider_governance_contract,
    provider_routing_requires_discovered_inventory,
    resolve_provider_capability,
    resolve_provider_for_model,
    validate_provider_model_selection,
)


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


def test_provider_governance_contract_classifies_every_known_provider_once():
    contract = provider_governance_contract()

    assert set(contract) == set(PROVIDER_ORDER)
    assert len(contract) == len(PROVIDER_ORDER)
    assert all(
        entry["provider"] == provider for provider, entry in contract.items()
    )

    discovery_backed = {
        provider
        for provider, entry in contract.items()
        if entry["governance_classification"] == "discovery_backed"
    }
    static_authorized = {
        provider
        for provider, entry in contract.items()
        if entry["governance_classification"] == "static_authorized"
    }
    local_only = {
        provider
        for provider, entry in contract.items()
        if entry["governance_classification"] == "local_only"
    }
    disabled = {
        provider
        for provider, entry in contract.items()
        if entry["governance_classification"] == "disabled"
    }

    assert discovery_backed == {"alibaba", "minimax"}
    assert static_authorized == {"openai", "groq"}
    assert local_only == {"local"}
    assert disabled == {"anthropic", "gemini"}
    assert discovery_backed.isdisjoint(static_authorized)
    assert discovery_backed | static_authorized | local_only == set(
        ROUTER_SUPPORTED_LLM_PROVIDERS
    )


def test_provider_governance_contract_is_internally_consistent():
    contract = provider_governance_contract()

    for provider, entry in contract.items():
        assert provider_governance(provider) == entry
        assert (
            provider_routing_requires_discovered_inventory(provider)
            is entry["routing_validate_discovered_inventory"]
        )
        assert (
            provider_allows_default_during_degraded_discovery(provider)
            is entry["configured_defaults_allowed_during_degraded_discovery"]
        )

        classification = entry["governance_classification"]
        if classification == "discovery_backed":
            assert entry["live_discovery_expected"] is True
            assert entry["routing_validate_discovered_inventory"] is True
            assert (
                entry["configured_defaults_allowed_during_degraded_discovery"]
                is True
            )
            assert entry["local_only"] is False
        elif classification == "local_only":
            assert entry["live_discovery_expected"] is False
            assert entry["routing_validate_discovered_inventory"] is False
            assert (
                entry["configured_defaults_allowed_during_degraded_discovery"]
                is False
            )
            assert entry["local_only"] is True
        else:
            assert entry["live_discovery_expected"] is False
            assert entry["routing_validate_discovered_inventory"] is False
            assert (
                entry["configured_defaults_allowed_during_degraded_discovery"]
                is False
            )
            assert entry["local_only"] is False
