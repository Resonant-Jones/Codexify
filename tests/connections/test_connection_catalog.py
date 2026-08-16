"""Canonical Connections catalog contract tests.

These tests lock the static truth of the catalog: ids, categories,
implementation states, capability metadata, auth-method honesty, and the
rule that catalog visibility never implies a runtime adapter.
"""

from __future__ import annotations

from guardian.connections.catalog import (
    get_catalog,
    get_connection,
)
from guardian.protocol_tokens import (
    CONNECTION_AUTH_METHODS,
    CONNECTION_CATEGORIES,
    CONNECTION_IMPLEMENTATION_STATES,
    CONNECTION_SETUP_STATES,
)

MESSAGING_IDS = {
    "telegram",
    "discord",
    "slack",
    "google_chat",
    "whatsapp",
    "signal",
    "mattermost",
    "matrix",
    "bluebubbles_imessage",
    "home_assistant",
    "email",
    "sms_twilio",
    "dingtalk",
    "feishu_lark",
    "wecom",
    "weixin_wechat",
    "qq_bot",
    "yuanbao",
    "microsoft_teams",
    "line",
    "ntfy",
    "api_server",
    "webhooks",
}

WEB_IDS = {
    "firecrawl",
    "searxng",
    "brave",
    "ddgs",
    "tavily",
    "exa",
    "parallel",
    "xai_grok",
}

SEARCH_EXTRACT_IDS = {"firecrawl", "tavily", "exa", "parallel"}
SEARCH_ONLY_IDS = {"searxng", "brave", "ddgs", "xai_grok"}


def test_catalog_ids_are_unique() -> None:
    entries = get_catalog()
    ids = [entry.id for entry in entries]
    assert len(ids) == len(set(ids))


def test_only_canonical_categories_exist() -> None:
    for entry in get_catalog():
        assert entry.category in CONNECTION_CATEGORIES


def test_states_and_methods_are_canonical_tokens() -> None:
    for entry in get_catalog():
        assert entry.implementation_state in CONNECTION_IMPLEMENTATION_STATES
        assert entry.default_setup_state in CONNECTION_SETUP_STATES
        for method in entry.auth_methods:
            assert method in CONNECTION_AUTH_METHODS


def test_every_requested_messaging_entry_is_present() -> None:
    catalog_ids = {e.id for e in get_catalog() if e.category == "messaging"}
    assert MESSAGING_IDS <= catalog_ids


def test_slack_discord_telegram_do_not_claim_unwired_runtime_capability() -> None:
    for entry_id, adapter in (
        ("slack", "guardian.channels.adapters.slack.SlackAdapter"),
        ("discord", "guardian.channels.adapters.discord.DiscordAdapter"),
        ("telegram", "guardian.channels.adapters.telegram.TelegramAdapter"),
    ):
        entry = get_connection(entry_id)
        assert entry is not None
        assert entry.implementation_state == "partial"
        binding = entry.runtime_binding
        assert binding.subsystem == "guardian.channels"
        assert binding.adapter == adapter
        assert binding.setup_route is None
        assert entry.required_fields == ()
        assert entry.capabilities == frozenset()
        assert entry.default_setup_state == "unavailable"
        assert "no production runtime path" in entry.setup_help


def test_non_implemented_messaging_entries_are_unimplemented() -> None:
    partial = {"slack", "discord", "telegram"}
    for entry in get_catalog():
        if entry.category != "messaging":
            continue
        if entry.id in partial:
            continue
        assert entry.implementation_state == "unimplemented", entry.id
        assert entry.default_setup_state == "unavailable", entry.id
        assert entry.runtime_binding.adapter is None, entry.id


def test_web_capability_matrix_is_exact() -> None:
    for entry in get_catalog():
        if entry.category != "web":
            continue
        assert entry.id in WEB_IDS
        caps = set(entry.capabilities)
        if entry.id in SEARCH_EXTRACT_IDS:
            assert caps == {"search", "extract"}, entry.id
        else:
            assert caps == {"search"}, entry.id


def test_web_providers_are_unimplemented_and_do_not_claim_runtime_effect() -> None:
    for entry in get_catalog():
        if entry.category != "web":
            continue
        assert entry.implementation_state == "unimplemented", entry.id
        assert entry.default_setup_state == "unavailable", entry.id
        assert entry.runtime_binding.adapter is None, entry.id
        assert "does not change current search behavior" in entry.setup_help


def test_deepseek_is_api_key_only() -> None:
    entry = get_connection("deepseek")
    assert entry is not None
    assert entry.auth_methods == ("api_key",)
    assert entry.implementation_state == "implemented"
    assert entry.runtime_binding.registry_provider_id == "deepseek"
    assert entry.runtime_binding.oauth_backend_handler_exists is False


def test_no_entry_claims_an_oauth_backend_handler_exists() -> None:
    # No provider-specific OAuth exchange is implemented in this slice, so
    # no entry may advertise one; OAuth UI must stay disabled.
    for entry in get_catalog():
        assert (
            entry.runtime_binding.oauth_backend_handler_exists is False
        ), entry.id


def test_inference_registry_mapping_matches_provider_registry() -> None:
    expected = {
        "deepseek": "deepseek",
        "openai_api": "openai",
        "minimax_api": "minimax",
        "minimax_oauth": "minimax",
        "gemini_api": "gemini",
        "gemini_oauth": "gemini",
        "groq": "groq",
        "alibaba_dashscope": "alibaba",
        "anthropic_api": "anthropic",
        "anthropic_subscription": "anthropic",
    }
    for entry_id, registry_id in expected.items():
        entry = get_connection(entry_id)
        assert entry is not None
        assert entry.runtime_binding.registry_provider_id == registry_id


def test_unlisted_inference_entries_have_no_registry_binding() -> None:
    unlisted = {
        "openrouter",
        "kimi_moonshot",
        "nvidia",
        "huggingface",
        "stepfun",
        "xai_api",
        "xai_oauth",
        "qwen_oauth",
        "ollama_cloud",
        "azure",
        "aws_bedrock",
        "codex_chatgpt",
        "nous_portal",
        "github_copilot",
    }
    for entry_id in unlisted:
        entry = get_connection(entry_id)
        assert entry is not None
        assert entry.runtime_binding.registry_provider_id is None


def test_inference_entries_distinguish_adapter_from_registry() -> None:
    # Adapter code exists for gemini but the registry records it disabled;
    # the catalog must keep implementation truth separate from registry
    # authorization truth.
    gemini = get_connection("gemini_api")
    assert gemini is not None
    assert gemini.implementation_state == "partial"
    assert gemini.runtime_binding.registry_provider_id == "gemini"

    alibaba = get_connection("alibaba_dashscope")
    assert alibaba is not None
    assert alibaba.implementation_state == "implemented"

    anthropic = get_connection("anthropic_api")
    assert anthropic is not None
    assert anthropic.implementation_state == "unimplemented"


def test_every_entry_has_safe_setup_help() -> None:
    for entry in get_catalog():
        assert isinstance(entry.setup_help, str)
