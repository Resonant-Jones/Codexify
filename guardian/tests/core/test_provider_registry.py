from itertools import combinations

import requests

from guardian.core.config import ROUTER_SUPPORTED_LLM_PROVIDERS, Settings
from guardian.core.provider_registry import (
    DISABLED_PROVIDERS,
    DISCOVERY_BACKED_PROVIDERS,
    LOCAL_ONLY_PROVIDERS,
    PROVIDER_ORDER,
    STATIC_AUTHORIZED_PROVIDERS,
    get_provider_model_descriptors,
    provider_allows_default_during_degraded_discovery,
    provider_availability,
    provider_egress_allowed,
    provider_governance,
    provider_governance_contract,
    provider_routing_requires_discovered_inventory,
    resolve_provider_capability,
    resolve_provider_for_model,
    supported_profile_posture,
    validate_provider_model_selection,
)
from guardian.core.provider_truth import (
    build_provider_truth,
    cloud_capable_configuration_present,
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


def _supported_profile_settings(**overrides) -> Settings:
    defaults = {
        "LLM_PROVIDER": "local",
        "ALLOW_CLOUD_PROVIDERS": False,
        "CODEXIFY_LOCAL_ONLY_MODE": True,
        "CODEXIFY_EGRESS_ALLOWLIST": "",
        "LOCAL_BASE_URL": "http://host.docker.internal:11434/v1",
        "LOCAL_API_KEY": "local",
        "LOCAL_LLM_MODEL": "library2/ministral-3:8b",
        "LOCAL_CHAT_MODEL": "library2/ministral-3:8b",
        "LLM_MODEL": "library2/ministral-3:8b",
        "OPENAI_API_KEY": None,
        "OPENAI_BASE_URL": None,
        "GROQ_API_KEY": None,
        "GROQ_BASE_URL": None,
        "ANTHROPIC_API_KEY": None,
        "GEMINI_API_KEY": None,
        "GENAI_API_KEY": None,
        "GOOGLE_API_KEY": None,
        "ALIBABA_API_KEY": None,
        "ALIBABA_API_BASE": None,
        "MINIMAX_API_KEY": None,
        "MINIMAX_API_BASE": None,
    }
    defaults.update(overrides)
    return Settings(_env_file=None, **defaults)


def _supported_profile_settings_with_default_cloud_bases(
    **overrides,
) -> Settings:
    defaults = {
        "LLM_PROVIDER": "local",
        "ALLOW_CLOUD_PROVIDERS": False,
        "CODEXIFY_LOCAL_ONLY_MODE": True,
        "CODEXIFY_EGRESS_ALLOWLIST": "",
        "LOCAL_BASE_URL": "http://host.docker.internal:11434/v1",
        "LOCAL_API_KEY": "local",
        "LOCAL_LLM_MODEL": "library2/ministral-3:8b",
        "LOCAL_CHAT_MODEL": "library2/ministral-3:8b",
        "LLM_MODEL": "library2/ministral-3:8b",
        "OPENAI_API_KEY": None,
        "OPENAI_BASE_URL": None,
        "GROQ_API_KEY": None,
        "GROQ_BASE_URL": None,
        "ANTHROPIC_API_KEY": None,
        "GEMINI_API_KEY": None,
        "GENAI_API_KEY": None,
        "GOOGLE_API_KEY": None,
        "ALIBABA_API_KEY": None,
        "MINIMAX_API_KEY": None,
    }
    defaults.update(overrides)
    return Settings(_env_file=None, **defaults)


def test_every_known_provider_is_classified_exactly_once():
    known_providers = set(PROVIDER_ORDER)
    contract = provider_governance_contract()
    assert set(contract) == known_providers

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
        {"groq", "alibaba", "minimax"}
    )
    assert STATIC_AUTHORIZED_PROVIDERS == frozenset({"openai"})
    assert LOCAL_ONLY_PROVIDERS == frozenset({"local"})
    assert DISABLED_PROVIDERS == frozenset({"anthropic", "gemini"})


def test_local_only_provider_is_marked_explicitly():
    contract = provider_governance("local")
    assert contract is not None
    assert contract["governance_classification"] == "local_only"
    assert contract["local_only"] is True
    assert contract["live_discovery_expected"] is False
    assert contract["routing_validate_discovered_inventory"] is False
    assert (
        contract["configured_defaults_allowed_during_degraded_discovery"]
        is False
    )


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
    contract = provider_governance_contract()

    for provider_id, contract_entry in contract.items():
        assert contract_entry["provider"] == provider_id
        assert provider_governance(provider_id) == contract_entry

        classification = contract_entry["classification"]
        local_only = contract_entry["local_only"]

        if classification == "discovery_backed":
            assert contract_entry["live_discovery_expected"] is True
            assert (
                contract_entry["routing_requires_discovered_inventory"] is True
            )
            assert (
                contract_entry[
                    "configured_defaults_allowed_on_discovery_failure"
                ]
                is True
            )
            assert local_only is False
            continue

        if classification == "static_authorized":
            assert contract_entry["live_discovery_expected"] is False
            assert (
                contract_entry["routing_requires_discovered_inventory"] is False
            )
            assert local_only is False
            continue

        if classification == "local_only":
            assert local_only is True
            assert (
                contract_entry[
                    "configured_defaults_allowed_on_discovery_failure"
                ]
                is True
            )
            continue

        assert classification == "disabled"
        assert contract_entry["live_discovery_expected"] is False
        assert contract_entry["routing_requires_discovered_inventory"] is False
        assert (
            contract_entry["configured_defaults_allowed_on_discovery_failure"]
            is False
        )
        assert local_only is False


def test_supported_profile_posture_marks_local_provider_supported(monkeypatch):
    monkeypatch.setenv("CODEXIFY_SUPPORTED_PROFILE", "v1-local-core-web-mcp")
    for env_key in (
        "OPENAI_API_KEY",
        "OPENAI_BASE_URL",
        "GROQ_API_KEY",
        "GROQ_BASE_URL",
        "ANTHROPIC_API_KEY",
        "GEMINI_API_KEY",
        "GENAI_API_KEY",
        "GOOGLE_API_KEY",
        "ALIBABA_API_KEY",
        "ALIBABA_API_BASE",
        "MINIMAX_API_KEY",
        "MINIMAX_API_BASE",
    ):
        monkeypatch.delenv(env_key, raising=False)
    settings = _supported_profile_settings()

    posture = supported_profile_posture(settings)
    local_truth = build_provider_truth(
        "local",
        settings,
        capability={
            "authorized": True,
            "enabled": True,
            "model_index": {"state": "available"},
        },
    )

    assert posture["name"] == "v1-local-core-web-mcp"
    assert posture["valid"] is True
    assert posture["selected_provider"] == "local"
    assert posture["selected_provider_supported"] is True
    assert posture["release_hold"] is False
    assert posture["cloud_capable_configuration_present"] is False
    assert local_truth["supported_profile_name"] == "v1-local-core-web-mcp"
    assert local_truth["supported_profile_valid"] is True
    assert local_truth["supported_profile_approved"] is True
    assert local_truth["discovered_inventory"] is True
    assert local_truth["executable"] is True
    assert local_truth["egress_allowed"] is True


def test_supported_profile_posture_marks_cloud_provider_unsupported(
    monkeypatch,
):
    monkeypatch.setenv("CODEXIFY_SUPPORTED_PROFILE", "v1-local-core-web-mcp")
    for env_key in (
        "OPENAI_API_KEY",
        "OPENAI_BASE_URL",
        "GROQ_API_KEY",
        "GROQ_BASE_URL",
        "ANTHROPIC_API_KEY",
        "GEMINI_API_KEY",
        "GENAI_API_KEY",
        "GOOGLE_API_KEY",
        "ALIBABA_API_KEY",
        "ALIBABA_API_BASE",
        "MINIMAX_API_KEY",
        "MINIMAX_API_BASE",
    ):
        monkeypatch.delenv(env_key, raising=False)
    settings = _supported_profile_settings(
        GROQ_API_KEY="test-groq-key",
        GROQ_BASE_URL="https://api.groq.com/openai/v1",
    )

    posture = supported_profile_posture(settings)
    available, reason = provider_availability("groq", settings)
    groq_truth = build_provider_truth(
        "groq",
        settings,
        capability={
            "authorized": True,
            "enabled": False,
            "model_index": {"state": "unavailable"},
        },
    )

    assert posture["name"] == "v1-local-core-web-mcp"
    assert posture["valid"] is True
    assert posture["cloud_capable_configuration_present"] is True
    assert posture["release_hold"] is True
    assert available is False
    assert reason == "Cloud providers disabled by config"
    assert provider_egress_allowed("groq", settings) is False
    assert groq_truth["supported_profile_approved"] is False
    assert groq_truth["executable"] is False
    assert groq_truth["egress_allowed"] is False


def test_supported_profile_posture_ignores_bundled_cloud_base_defaults(
    monkeypatch,
):
    monkeypatch.setenv("CODEXIFY_SUPPORTED_PROFILE", "v1-local-core-web-mcp")
    for env_key in (
        "OPENAI_API_KEY",
        "OPENAI_BASE_URL",
        "GROQ_API_KEY",
        "GROQ_BASE_URL",
        "ANTHROPIC_API_KEY",
        "GEMINI_API_KEY",
        "GENAI_API_KEY",
        "GOOGLE_API_KEY",
        "ALIBABA_API_KEY",
        "MINIMAX_API_KEY",
    ):
        monkeypatch.delenv(env_key, raising=False)

    settings = _supported_profile_settings_with_default_cloud_bases()

    posture = supported_profile_posture(settings)
    local_truth = build_provider_truth(
        "local",
        settings,
        capability={
            "authorized": True,
            "enabled": True,
            "model_index": {"state": "available"},
        },
    )

    assert settings.ALIBABA_API_BASE or settings.MINIMAX_API_BASE
    assert posture["cloud_capable_configuration_present"] is False
    assert posture["release_hold"] is False
    assert cloud_capable_configuration_present(settings) is False
    assert local_truth["cloud_capable_configuration_present"] is False
    assert local_truth["supported_profile_approved"] is True


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
    assert [model["id"] for model in capability["models"]] == [
        "qwen-max",
        "text-embedding-v3",
    ]
    assert capability["models"][0]["supports_chat"] is True
    assert capability["models"][0]["supports_vision"] is False
    assert capability["models"][0]["supports_text_input"] is True
    assert capability["models"][0]["model_kind"] == "chat"
    assert capability["models"][0]["_capability"] == "confirmed"
    assert capability["models"][1]["supports_chat"] is False
    assert capability["models"][1]["supports_vision"] is False
    assert capability["models"][1]["supports_text_input"] is True
    assert capability["models"][1]["model_kind"] == "utility"
    assert capability["models"][1]["_capability"] == "unsupported"
    assert capability["model_index"]["state"] == "available"
    assert capability["model_index"]["model_count"] == 1
    assert capability["model_index"]["utility_model_count"] == 1
    assert capability["model_index"]["total_model_count"] == 2


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
    assert capability["models"]
    assert capability["models"][0]["id"] == "minimax-chat"
    assert capability["default_model"] == "minimax-chat"
    assert capability["model_index"]["state"] == "degraded"
    assert capability["model_index"]["source"] == "fallback"
    assert capability["model_index"]["failure_kind"] == "provider_timeout"
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
        {
            "id": "minimax-chat",
            "displayName": "minimax-chat",
            "supports_chat": True,
            "supports_vision": False,
            "supports_text_input": True,
            "model_kind": "chat",
            "_capability": "confirmed",
            "capabilities": {
                "chat": True,
                "vision": False,
                "text_input": True,
            },
        },
        {
            "id": "abab7.5-chat",
            "displayName": "abab7.5-chat",
            "supports_chat": True,
            "supports_vision": False,
            "supports_text_input": True,
            "model_kind": "chat",
            "_capability": "confirmed",
            "capabilities": {
                "chat": True,
                "vision": False,
                "text_input": True,
            },
        },
    ]
    assert (
        resolve_provider_for_model("minimax-chat", settings=settings)
        == "minimax"
    )
    assert resolve_provider_for_model("not-real", settings=settings) is None


def test_validate_provider_model_selection_rejects_non_chat_models(monkeypatch):
    monkeypatch.setattr(
        "guardian.core.provider_registry.requests.get",
        lambda *args, **kwargs: _MockResponse(
            {
                "data": [
                    {"id": "qwen-max", "capabilities": {"tools": True}},
                    {"id": "text-embedding-v3", "task": "embedding"},
                ]
            }
        ),
    )

    settings = _provider_settings()

    valid, reason = validate_provider_model_selection(
        provider_id="alibaba",
        model_id="text-embedding-v3",
        settings=settings,
    )
    assert valid is False
    assert "not available" in str(reason)
    assert (
        resolve_provider_for_model("text-embedding-v3", settings=settings)
        is None
    )


def test_discovery_falls_back_when_classifier_excludes_all_models(
    monkeypatch, caplog
):
    monkeypatch.setattr(
        "guardian.core.provider_registry.requests.get",
        lambda *args, **kwargs: _MockResponse(
            {
                "data": [
                    {"id": "qwen-max", "supports_chat": False},
                    {"id": "qwen-plus", "supportsChat": False},
                ]
            }
        ),
    )

    settings = _provider_settings(ALIBABA_MODEL=None)

    with caplog.at_level("WARNING"):
        capability = resolve_provider_capability("alibaba", settings)

    assert capability["available"] is True
    assert capability["enabled"] is True
    assert [model["id"] for model in capability["models"]] == [
        "qwen-max",
        "qwen-plus",
    ]
    assert all(model["supports_chat"] is True for model in capability["models"])
    assert all(
        model["_capability"] == "inferred" for model in capability["models"]
    )
    assert capability["model_index"]["state"] == "degraded"
    assert "falling back to all discovered models" in str(
        capability["model_index"]["reason"]
    )
    assert "falling back to all discovered models" in caplog.text

    valid, reason = validate_provider_model_selection(
        provider_id="alibaba",
        model_id="qwen-max",
        settings=settings,
    )
    assert valid is True
    assert reason is None


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

    categories = (
        DISCOVERY_BACKED_PROVIDERS,
        STATIC_AUTHORIZED_PROVIDERS,
        LOCAL_ONLY_PROVIDERS,
        DISABLED_PROVIDERS,
    )
    for left, right in combinations(categories, 2):
        assert left.isdisjoint(right)

    assert (
        discovery_backed
        == DISCOVERY_BACKED_PROVIDERS
        == {"groq", "alibaba", "minimax"}
    )
    assert static_authorized == STATIC_AUTHORIZED_PROVIDERS == {"openai"}
    assert local_only == LOCAL_ONLY_PROVIDERS == {"local"}
    assert disabled == DISABLED_PROVIDERS == {"anthropic", "gemini"}
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
