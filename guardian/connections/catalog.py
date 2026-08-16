"""Canonical Connections catalog and control-plane model.

This module is the single source of truth for the Settings Connections bay
inventory. It is a *control plane*, not a new execution owner:

- Messaging runtime behavior remains owned by ``guardian/channels/``.
- Generic sync connectors remain owned by the existing connector subsystem.
- Inference execution authorization remains owned by
  ``guardian/core/provider_registry.py`` and supported-profile policy.
- Web execution remains owned by the eventual web-tool/provider runtime.
- Credential persistence remains server-side.

Catalog visibility is not implementation truth, configuration presence is
not runtime authorization, and runtime authorization is not live connection
health. The model below keeps those meanings as distinct, canonically typed
fields (see ``guardian/protocol_tokens.py`` for the token definitions).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from guardian.protocol_tokens import (
    ConnectionAuthMethod,
    ConnectionCapability,
    ConnectionCategory,
    ConnectionImplementationState,
    ConnectionSetupState,
)

# --- canonical method / capability shorthands -------------------------------

_OAUTH_BROWSER = ConnectionAuthMethod.OAUTH_BROWSER.value
_OAUTH_DEVICE = ConnectionAuthMethod.OAUTH_DEVICE.value
_API_KEY = ConnectionAuthMethod.API_KEY.value
_TOKEN = ConnectionAuthMethod.TOKEN.value
_SERVICE_CREDENTIALS = ConnectionAuthMethod.SERVICE_CREDENTIALS.value
_LOCAL_ENDPOINT = ConnectionAuthMethod.LOCAL_ENDPOINT.value
_NONE = ConnectionAuthMethod.NONE.value

_SEARCH = ConnectionCapability.SEARCH.value
_EXTRACT = ConnectionCapability.EXTRACT.value
_CHAT = ConnectionCapability.CHAT_COMPLETION.value
_OUTBOUND = ConnectionCapability.OUTBOUND_MESSAGING.value

_IMPLEMENTED = ConnectionImplementationState.IMPLEMENTED.value
_PARTIAL = ConnectionImplementationState.PARTIAL.value
_UNIMPLEMENTED = ConnectionImplementationState.UNIMPLEMENTED.value

_NEEDS_SETUP = ConnectionSetupState.NEEDS_SETUP.value
_UNAVAILABLE = ConnectionSetupState.UNAVAILABLE.value

_MESSAGING_UNIMPLEMENTED_HELP = (
    "No Codexify messaging adapter exists for this platform yet. This "
    "catalog entry is discovery only and cannot change messaging behavior."
)

_WEB_UNIMPLEMENTED_HELP = (
    "No Codexify web adapter exists for this provider yet. Selecting this "
    "connection does not change current search behavior: the legacy research "
    "search path and the separate remote-recall web seam are unaffected."
)

_OAUTH_UNAVAILABLE_HELP = (
    "OAuth setup is not yet available: no backend authorization handler "
    "exists for this provider in Codexify today. This entry is catalog "
    "discovery only."
)


@dataclass(frozen=True)
class ConnectionFieldSpec:
    """A single setup field an entry's setup flow needs."""

    key: str
    label: str
    type: str = "string"  # string | password | boolean | number
    secret: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "type": self.type,
            "secret": self.secret,
        }


@dataclass(frozen=True)
class ConnectionRuntimeBinding:
    """Which real subsystem owns this entry's runtime, if any."""

    subsystem: str | None = None
    adapter: str | None = None
    setup_route: str | None = None
    registry_provider_id: str | None = None
    oauth_backend_handler_exists: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "subsystem": self.subsystem,
            "adapter": self.adapter,
            "setup_route": self.setup_route,
            "registry_provider_id": self.registry_provider_id,
            "oauth_backend_handler_exists": self.oauth_backend_handler_exists,
        }


@dataclass(frozen=True)
class ConnectionCatalogEntry:
    """A typed catalog entry.

    Static truth only: implementation state is code-proven at authoring
    time; per-user setup state and runtime authorization are merged by the
    connections routes at request time and are never stored here.
    """

    id: str
    display_name: str
    category: str
    description: str
    auth_methods: tuple[str, ...] = ()
    capabilities: frozenset[str] = frozenset()
    implementation_state: str = _UNIMPLEMENTED
    default_setup_state: str = _UNAVAILABLE
    runtime_binding: ConnectionRuntimeBinding = field(
        default_factory=ConnectionRuntimeBinding
    )
    required_fields: tuple[ConnectionFieldSpec, ...] = ()
    scopes: tuple[str, ...] = ()
    setup_help: str = ""
    oauth_provider_key: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "display_name": self.display_name,
            "category": self.category,
            "description": self.description,
            "auth_methods": list(self.auth_methods),
            "capabilities": sorted(self.capabilities),
            "implementation_state": self.implementation_state,
            "setup_state": self.default_setup_state,
            "runtime_binding": self.runtime_binding.as_dict(),
            "required_fields": [f.as_dict() for f in self.required_fields],
            "scopes": list(self.scopes),
            "setup_help": self.setup_help,
            "oauth_provider_key": self.oauth_provider_key,
        }


def _messaging_adapter_entry(
    entry_id: str,
    display_name: str,
    description: str,
    *,
    adapter_class: str,
) -> ConnectionCatalogEntry:
    return ConnectionCatalogEntry(
        id=entry_id,
        display_name=display_name,
        category=ConnectionCategory.MESSAGING.value,
        description=description,
        auth_methods=(_TOKEN,),
        capabilities=frozenset({_OUTBOUND}),
        implementation_state=_IMPLEMENTED,
        # These adapters currently consume server-managed environment
        # credentials. Do not turn the generic ChannelConfig JSON route into
        # a browser-facing secret persistence path.
        default_setup_state=_UNAVAILABLE,
        runtime_binding=ConnectionRuntimeBinding(
            subsystem="guardian.channels",
            adapter=adapter_class,
        ),
        setup_help=(
            "The adapter is available for server-managed runtime wiring, but "
            "the Connections bay does not collect or persist its credentials. "
            "Configure the server-owned environment credential through the "
            "channel runtime's operator path."
        ),
    )


def _messaging_unimplemented_entry(
    entry_id: str,
    display_name: str,
    description: str,
    *,
    setup_help: str | None = None,
) -> ConnectionCatalogEntry:
    return ConnectionCatalogEntry(
        id=entry_id,
        display_name=display_name,
        category=ConnectionCategory.MESSAGING.value,
        description=description,
        setup_help=setup_help or _MESSAGING_UNIMPLEMENTED_HELP,
    )


def _web_entry(
    entry_id: str,
    display_name: str,
    description: str,
    *,
    capabilities: frozenset[str],
    auth_methods: tuple[str, ...],
) -> ConnectionCatalogEntry:
    return ConnectionCatalogEntry(
        id=entry_id,
        display_name=display_name,
        category=ConnectionCategory.WEB.value,
        description=description,
        auth_methods=auth_methods,
        capabilities=capabilities,
        setup_help=_WEB_UNIMPLEMENTED_HELP,
    )


def _inference_oauth_entry(
    entry_id: str,
    display_name: str,
    description: str,
    *,
    registry_provider_id: str | None = None,
) -> ConnectionCatalogEntry:
    return ConnectionCatalogEntry(
        id=entry_id,
        display_name=display_name,
        category=ConnectionCategory.INFERENCE.value,
        description=description,
        auth_methods=(_OAUTH_BROWSER,),
        capabilities=frozenset({_CHAT}),
        runtime_binding=ConnectionRuntimeBinding(
            subsystem="guardian.core.provider_registry",
            registry_provider_id=registry_provider_id,
        ),
        scopes=("chat",),
        setup_help=_OAUTH_UNAVAILABLE_HELP,
        oauth_provider_key=entry_id,
    )


def _inference_api_entry(
    entry_id: str,
    display_name: str,
    description: str,
    *,
    implementation_state: str = _IMPLEMENTED,
    registry_provider_id: str | None = None,
    auth_methods: tuple[str, ...] = (_API_KEY,),
    setup_help: str = (
        "Inference provider configuration is server-owned. Credential "
        "presence and provider-registry authorization are reported here; "
        "neither proves a live provider connection."
    ),
) -> ConnectionCatalogEntry:
    return ConnectionCatalogEntry(
        id=entry_id,
        display_name=display_name,
        category=ConnectionCategory.INFERENCE.value,
        description=description,
        auth_methods=auth_methods,
        capabilities=frozenset({_CHAT}),
        implementation_state=implementation_state,
        default_setup_state=(
            _NEEDS_SETUP
            if implementation_state != _UNIMPLEMENTED
            else _UNAVAILABLE
        ),
        runtime_binding=ConnectionRuntimeBinding(
            subsystem="guardian.core.provider_registry",
            registry_provider_id=registry_provider_id,
        ),
        required_fields=(ConnectionFieldSpec("api_key", "API key", "password", True),),
        setup_help=setup_help,
    )


def _build_catalog() -> tuple[ConnectionCatalogEntry, ...]:
    entries: list[ConnectionCatalogEntry] = []

    # =========================== Messaging =================================
    entries.append(
        _messaging_adapter_entry(
            "slack",
            "Slack",
            "Outbound Slack channel delivery through the existing channel "
            "adapter, with per-user configuration, allowlist, and pairing "
            "surfaces.",
            adapter_class="guardian.channels.adapters.slack.SlackAdapter",
        )
    )
    entries.append(
        _messaging_adapter_entry(
            "discord",
            "Discord",
            "Outbound Discord channel delivery through the existing channel "
            "adapter (webhook-based), with per-user configuration, "
            "allowlist, and pairing surfaces.",
            adapter_class="guardian.channels.adapters.discord.DiscordAdapter",
        )
    )
    entries.append(
        _messaging_adapter_entry(
            "telegram",
            "Telegram",
            "Outbound Telegram channel delivery through the existing "
            "channel adapter, with per-user configuration, allowlist, and "
            "pairing surfaces.",
            adapter_class="guardian.channels.adapters.telegram.TelegramAdapter",
        )
    )
    entries.extend(
        [
            _messaging_unimplemented_entry(
                "google_chat",
                "Google Chat",
                "Google Chat messaging. No Codexify adapter exists yet.",
            ),
            _messaging_unimplemented_entry(
                "whatsapp",
                "WhatsApp",
                "WhatsApp messaging. No Codexify adapter exists yet.",
            ),
            _messaging_unimplemented_entry(
                "signal",
                "Signal",
                "Signal messaging. No Codexify adapter exists yet.",
            ),
            _messaging_unimplemented_entry(
                "mattermost",
                "Mattermost",
                "Mattermost messaging. No Codexify adapter exists yet.",
            ),
            _messaging_unimplemented_entry(
                "matrix",
                "Matrix",
                "Matrix messaging. No Codexify adapter exists yet.",
            ),
            _messaging_unimplemented_entry(
                "bluebubbles_imessage",
                "BlueBubbles / iMessage",
                "BlueBubbles-backed iMessage. No Codexify adapter exists yet.",
            ),
            _messaging_unimplemented_entry(
                "home_assistant",
                "Home Assistant",
                "Home Assistant notifications. No Codexify adapter exists "
                "yet.",
            ),
            _messaging_unimplemented_entry(
                "email",
                "Email",
                "Email messaging. Governed for future implementation by "
                "ADR-047; no Codexify email runtime exists yet.",
                setup_help=(
                    "No Codexify email runtime exists yet. Email adapter and "
                    "routing boundaries are governed by ADR-047 and remain "
                    "future work."
                ),
            ),
            _messaging_unimplemented_entry(
                "sms_twilio",
                "SMS / Twilio",
                "SMS delivery through Twilio. No Codexify adapter exists yet.",
            ),
            _messaging_unimplemented_entry(
                "dingtalk",
                "DingTalk",
                "DingTalk messaging. No Codexify adapter exists yet.",
            ),
            _messaging_unimplemented_entry(
                "feishu_lark",
                "Feishu / Lark",
                "Feishu / Lark messaging. No Codexify adapter exists yet.",
            ),
            _messaging_unimplemented_entry(
                "wecom",
                "WeCom",
                "WeCom messaging. No Codexify adapter exists yet.",
            ),
            _messaging_unimplemented_entry(
                "weixin_wechat",
                "Weixin / WeChat",
                "Weixin / WeChat messaging. No Codexify adapter exists yet.",
            ),
            _messaging_unimplemented_entry(
                "qq_bot",
                "QQ Bot",
                "QQ Bot messaging. No Codexify adapter exists yet.",
            ),
            _messaging_unimplemented_entry(
                "yuanbao",
                "Yuanbao",
                "Tencent Yuanbao. No Codexify adapter exists yet.",
            ),
            _messaging_unimplemented_entry(
                "microsoft_teams",
                "Microsoft Teams",
                "Microsoft Teams messaging. No Codexify adapter exists yet.",
            ),
            _messaging_unimplemented_entry(
                "line",
                "LINE",
                "LINE messaging. No Codexify adapter exists yet.",
            ),
            _messaging_unimplemented_entry(
                "ntfy",
                "ntfy",
                "ntfy push notifications. No Codexify adapter exists yet.",
            ),
            _messaging_unimplemented_entry(
                "api_server",
                "API Server",
                "Codexify's own API server surface. No dedicated messaging "
                "adapter exists yet.",
            ),
            _messaging_unimplemented_entry(
                "webhooks",
                "Webhooks",
                "Generic inbound webhooks. No Codexify webhook intake "
                "surface exists yet.",
            ),
        ]
    )

    # ============================== Web ====================================
    entries.extend(
        [
            _web_entry(
                "firecrawl",
                "Firecrawl",
                "Web search and page extraction through Firecrawl. Catalog "
                "discovery only; no Codexify adapter exists yet.",
                capabilities=frozenset({_SEARCH, _EXTRACT}),
                auth_methods=(_API_KEY,),
            ),
            _web_entry(
                "searxng",
                "SearXNG",
                "Self-hosted meta-search through SearXNG. Catalog discovery "
                "only; no Codexify adapter exists yet.",
                capabilities=frozenset({_SEARCH}),
                auth_methods=(_LOCAL_ENDPOINT,),
            ),
            _web_entry(
                "brave",
                "Brave Search",
                "Web search through Brave Search API. Catalog discovery "
                "only; no Codexify adapter exists yet.",
                capabilities=frozenset({_SEARCH}),
                auth_methods=(_API_KEY,),
            ),
            _web_entry(
                "ddgs",
                "DDGS / DuckDuckGo",
                "Web search through DuckDuckGo. Catalog discovery only; no "
                "Codexify adapter exists yet.",
                capabilities=frozenset({_SEARCH}),
                auth_methods=(_NONE,),
            ),
            _web_entry(
                "tavily",
                "Tavily",
                "Web search and page extraction through Tavily. Catalog "
                "discovery only; no Codexify adapter exists yet.",
                capabilities=frozenset({_SEARCH, _EXTRACT}),
                auth_methods=(_API_KEY,),
            ),
            _web_entry(
                "exa",
                "Exa",
                "Web search and page extraction through Exa. Catalog "
                "discovery only; no Codexify adapter exists yet.",
                capabilities=frozenset({_SEARCH, _EXTRACT}),
                auth_methods=(_API_KEY,),
            ),
            _web_entry(
                "parallel",
                "Parallel",
                "Web search and page extraction through Parallel. Catalog "
                "discovery only; no Codexify adapter exists yet.",
                capabilities=frozenset({_SEARCH, _EXTRACT}),
                auth_methods=(_API_KEY,),
            ),
            _web_entry(
                "xai_grok",
                "xAI / Grok",
                "Web search through xAI / Grok. Catalog discovery only; no "
                "Codexify adapter exists yet.",
                capabilities=frozenset({_SEARCH}),
                auth_methods=(_API_KEY,),
            ),
        ]
    )

    # ============================ Inference ================================
    entries.extend(
        [
            _inference_oauth_entry(
                "codex_chatgpt",
                "OpenAI Codex / ChatGPT",
                "ChatGPT/Codex subscription-style OAuth access. No backend "
                "OAuth handler exists yet.",
            ),
            _inference_oauth_entry(
                "minimax_oauth",
                "MiniMax OAuth",
                "MiniMax OAuth-style access. No backend OAuth handler "
                "exists yet; the MiniMax API-key lane is registry-governed "
                "separately.",
                registry_provider_id="minimax",
            ),
            _inference_oauth_entry(
                "qwen_oauth",
                "Qwen OAuth",
                "Qwen OAuth-style access. No backend OAuth handler exists "
                "yet.",
            ),
            _inference_oauth_entry(
                "gemini_oauth",
                "Google Gemini OAuth",
                "Google Gemini OAuth-style access. No backend OAuth handler "
                "exists yet.",
                registry_provider_id="gemini",
            ),
            _inference_oauth_entry(
                "xai_oauth",
                "xAI / Grok OAuth",
                "xAI / Grok OAuth-style access. No backend OAuth handler "
                "exists yet.",
            ),
            _inference_oauth_entry(
                "nous_portal",
                "Nous Portal",
                "Nous Portal account access. No backend handler exists yet.",
            ),
            _inference_oauth_entry(
                "github_copilot",
                "GitHub Copilot",
                "GitHub Copilot subscription-style access. No backend "
                "OAuth handler exists yet.",
            ),
            _inference_oauth_entry(
                "anthropic_subscription",
                "Anthropic / Claude subscription",
                "Anthropic subscription-style access where legitimately "
                "supported. No backend OAuth handler exists yet.",
                registry_provider_id="anthropic",
            ),
        ]
    )
    entries.extend(
        [
            _inference_api_entry(
                "deepseek",
                "DeepSeek",
                "DeepSeek chat through the existing adapter, authorized by "
                "the canonical provider registry.",
                registry_provider_id="deepseek",
            ),
            _inference_api_entry(
                "openai_api",
                "OpenAI API",
                "OpenAI chat through the existing adapter, authorized by "
                "the canonical provider registry.",
                registry_provider_id="openai",
            ),
            _inference_api_entry(
                "openrouter",
                "OpenRouter",
                "OpenRouter API access. No Codexify adapter exists yet.",
                implementation_state=_UNIMPLEMENTED,
            ),
            _inference_api_entry(
                "minimax_api",
                "MiniMax API",
                "MiniMax chat through the existing adapter, authorized by "
                "the canonical provider registry.",
                registry_provider_id="minimax",
            ),
            _inference_api_entry(
                "anthropic_api",
                "Anthropic API",
                "Anthropic API access. No Codexify adapter exists yet; the "
                "provider registry currently records Anthropic as disabled.",
                implementation_state=_UNIMPLEMENTED,
                registry_provider_id="anthropic",
            ),
            _inference_api_entry(
                "gemini_api",
                "Google Gemini API",
                "Gemini adapter code exists but is not wired into the "
                "canonical router, and the provider registry currently "
                "records Gemini as disabled.",
                implementation_state=_PARTIAL,
                registry_provider_id="gemini",
            ),
            _inference_api_entry(
                "groq",
                "Groq",
                "Groq chat through the existing adapter, authorized by the "
                "canonical provider registry.",
                registry_provider_id="groq",
            ),
            _inference_api_entry(
                "alibaba_dashscope",
                "Alibaba / DashScope",
                "DashScope chat through the existing router path, "
                "authorized by the canonical provider registry.",
                registry_provider_id="alibaba",
            ),
            _inference_api_entry(
                "kimi_moonshot",
                "Kimi / Moonshot",
                "Kimi / Moonshot API access. No Codexify adapter exists yet.",
                implementation_state=_UNIMPLEMENTED,
            ),
            _inference_api_entry(
                "nvidia",
                "NVIDIA",
                "NVIDIA hosted-model API access. No Codexify adapter exists "
                "yet.",
                implementation_state=_UNIMPLEMENTED,
            ),
            _inference_api_entry(
                "huggingface",
                "Hugging Face",
                "Hugging Face hosted-model access. No Codexify adapter "
                "exists yet.",
                implementation_state=_UNIMPLEMENTED,
                auth_methods=(_TOKEN,),
            ),
            _inference_api_entry(
                "stepfun",
                "StepFun",
                "StepFun API access. No Codexify adapter exists yet.",
                implementation_state=_UNIMPLEMENTED,
            ),
            _inference_api_entry(
                "xai_api",
                "xAI API",
                "xAI API access. No Codexify adapter exists yet.",
                implementation_state=_UNIMPLEMENTED,
            ),
            _inference_api_entry(
                "ollama_cloud",
                "Ollama Cloud",
                "Hosted Ollama Cloud access. No Codexify adapter exists "
                "yet; local Ollama serving is a separate local-runtime lane.",
                implementation_state=_UNIMPLEMENTED,
            ),
            _inference_api_entry(
                "azure",
                "Azure",
                "Azure OpenAI-compatible access. No Codexify adapter exists "
                "yet.",
                implementation_state=_UNIMPLEMENTED,
                auth_methods=(_API_KEY, _SERVICE_CREDENTIALS),
            ),
            _inference_api_entry(
                "aws_bedrock",
                "AWS Bedrock",
                "AWS Bedrock access. No Codexify adapter exists yet.",
                implementation_state=_UNIMPLEMENTED,
                auth_methods=(_SERVICE_CREDENTIALS,),
            ),
            _inference_api_entry(
                "lm_studio",
                "LM Studio",
                "LM Studio local serving. No dedicated adapter exists; the "
                "generic OpenAI-compatible endpoint path may apply.",
                implementation_state=_UNIMPLEMENTED,
                auth_methods=(_LOCAL_ENDPOINT,),
            ),
            _inference_api_entry(
                "custom_openai_compatible",
                "Custom OpenAI-compatible endpoint",
                "A user-supplied OpenAI-compatible endpoint through the "
                "existing OpenAI adapter path (OPENAI_BASE_URL). No "
                "dedicated setup surface exists yet.",
                implementation_state=_PARTIAL,
                auth_methods=(_LOCAL_ENDPOINT, _API_KEY),
                setup_help=(
                    "The existing OpenAI adapter path accepts a custom base "
                    "URL via server configuration. There is no dedicated "
                    "setup surface yet; configuration remains "
                    "server-owned."
                ),
            ),
        ]
    )

    return tuple(entries)


_CATALOG: tuple[ConnectionCatalogEntry, ...] = _build_catalog()
_CATALOG_BY_ID: dict[str, ConnectionCatalogEntry] = {
    entry.id: entry for entry in _CATALOG
}


def get_catalog() -> tuple[ConnectionCatalogEntry, ...]:
    """Return the full canonical catalog (static truth)."""
    return _CATALOG


def get_connection(connection_id: str) -> ConnectionCatalogEntry | None:
    """Look up a single catalog entry by id."""
    return _CATALOG_BY_ID.get(connection_id)


def connections_by_category(category: str) -> tuple[ConnectionCatalogEntry, ...]:
    """Return catalog entries for one canonical category."""
    return tuple(e for e in _CATALOG if e.category == category)


__all__ = [
    "ConnectionCatalogEntry",
    "ConnectionFieldSpec",
    "ConnectionRuntimeBinding",
    "connections_by_category",
    "get_catalog",
    "get_connection",
]
