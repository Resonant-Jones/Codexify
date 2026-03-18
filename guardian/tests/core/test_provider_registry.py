from itertools import combinations

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
    provider_availability,
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
