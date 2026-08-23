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
    CONNECTION_CAPABILITIES,
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
        for capability in entry.capabilities:
            assert capability in CONNECTION_CAPABILITIES


def test_implemented_read_only_knowledge_entries_preserve_provider_boundaries() -> None:
    knowledge_entries = [
        entry for entry in get_catalog() if entry.category == "knowledge"
    ]
    assert [entry.id for entry in knowledge_entries] == ["notion", "google_drive"]
    notion = get_connection("notion")
    assert notion is not None
    assert notion.capabilities == {"content_search", "content_read"}
    assert notion.auth_methods == ("token",)
    assert notion.implementation_state == "implemented"
    assert notion.runtime_binding.subsystem == "guardian.connections.notion"
    assert notion.runtime_binding.setup_route == "/api/connect/notion/configure"
    assert notion.required_fields[0].secret is True
    assert "sync" not in notion.capabilities
    assert "write" not in notion.capabilities
    google_drive = get_connection("google_drive")
    assert google_drive is not None
    assert google_drive.capabilities == {"content_search", "content_read"}
    assert google_drive.auth_methods == ("oauth_browser",)
    assert google_drive.implementation_state == "implemented"
    assert google_drive.runtime_binding.subsystem == "guardian.connections.google_drive"
    assert google_drive.runtime_binding.setup_route == "/api/connect/google-drive/start"


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


def test_minimax_oauth_is_partial_with_real_backend_handler() -> None:
    """MiniMax OAuth is the first provider-specific OAuth setup entry.

    Authentication/setup code path exists; OAuth-to-inference credential
    binding remains deliberately deferred. The MiniMax API-key lane is
    registry-governed separately.
    """

    entry = get_connection("minimax_oauth")
    assert entry is not None
    assert entry.id == "minimax_oauth"
    # MiniMax OAuth is distinct from MiniMax API-key.
    assert entry.auth_methods == ("oauth_browser",)
    assert entry.implementation_state == "partial"
    assert entry.runtime_binding.setup_route == "/api/connect/minimax/start"
    assert entry.runtime_binding.oauth_backend_handler_exists is True
    assert entry.runtime_binding.registry_provider_id == "minimax"
    # MiniMax API-key entry remains unchanged.
    api_entry = get_connection("minimax_api")
    assert api_entry is not None
    assert api_entry.implementation_state == "implemented"
    assert api_entry.auth_methods == ("api_key",)
    assert api_entry.runtime_binding.oauth_backend_handler_exists is False
    assert api_entry.runtime_binding.registry_provider_id == "minimax"
    # Unrelated OAuth entries remain unimplemented.
    for entry_id in (
        "codex_chatgpt",
        "qwen_oauth",
        "gemini_oauth",
        "xai_oauth",
        "nous_portal",
        "github_copilot",
        "anthropic_subscription",
    ):
        other = get_connection(entry_id)
        assert other is not None
        assert other.runtime_binding.oauth_backend_handler_exists is False, entry_id


def test_oauth_setup_route_uses_dedicated_provider_label() -> None:
    """The MiniMax OAuth setup route is independent from the read-only
    Connections surface and from the quarantined legacy connectors surface.
    """

    entry = get_connection("minimax_oauth")
    assert entry is not None
    setup_route = entry.runtime_binding.setup_route
    assert setup_route is not None
    # Not on the read-only Connections surface.
    assert not setup_route.startswith("/api/connections")
    # Not on the quarantined legacy connector surface.
    assert not setup_route.startswith("/api/connectors")


def test_google_drive_is_one_implemented_knowledge_identity() -> None:
    entry = get_connection("google_drive")
    assert entry is not None
    assert entry.display_name == "Google Drive / Docs"
    assert entry.category == "knowledge"
    assert entry.capabilities == {"content_search", "content_read"}
    assert entry.auth_methods == ("oauth_browser",)
    assert entry.implementation_state == "implemented"
    assert entry.oauth_provider_key == "google_drive"
    assert entry.runtime_binding.setup_route == "/api/connect/google-drive/start"
    assert entry.runtime_binding.oauth_backend_handler_exists is True
    assert get_connection("google") is None


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
