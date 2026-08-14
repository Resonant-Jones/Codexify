# Connections Control Plane

## Purpose

The Settings **Connectors** tab is Codexify's single user-facing destination
for external connections. This document establishes the canonical
**Connections control plane**: one backend-owned, typed catalog that the
existing bay projects for discovering, inspecting, and setting up Messaging,
Web, and Inference integrations.

Connections is a **control plane, not a new execution owner**. The underlying
runtime systems retain their authority:

- Messaging runtime behavior remains owned by `guardian/channels/`.
- Generic sync connectors remain owned by the existing connector subsystem
  (`guardian/routes/connectors.py`, `/api/connectors`).
- Inference execution authorization remains owned by
  `guardian/core/provider_registry.py` and supported-profile policy.
- Web execution remains owned by the eventual web-tool/provider runtime.
- Credential persistence remains server-side.

The bay aggregates those systems into one setup experience without merging
their runtime domains.

## Canonical sources

| Surface | Canonical source |
| --- | --- |
| Catalog vocabulary (categories, states, methods) | `guardian/protocol_tokens.py` (`ConnectionCategory`, `ConnectionImplementationState`, `ConnectionSetupState`, `ConnectionAuthMethod`, `ConnectionCapability`) |
| Catalog entries (static truth) | `guardian/connections/catalog.py` |
| Read API (`GET /api/connections`, `GET /api/connections/{id}`) | `guardian/routes/connections.py` |
| Frontend projection types and helpers | `frontend/src/features/connectors/connectionCatalog.ts` |
| Setup wizard | `frontend/src/features/connectors/ConnectorConfigModal.tsx` |
| Bay surface | `frontend/src/features/settings/SettingsView.tsx` (existing `connectors` tab) |

## Category model

Exactly three canonical categories exist:

- `messaging`
- `web`
- `inference`

The desktop-only `connection` Settings tab is a different surface (Codexify's
own backend/runtime connection) and is not part of this catalog. The legacy
sync connectors (GitHub) remain on their existing surface inside the same tab
and are not assigned a catalog category.

## Catalog contract

Every entry exposes:

- `id`, `display_name`, `category`, `description`
- `auth_methods` — from the canonical method vocabulary:
  `oauth_browser`, `oauth_device`, `api_key`, `token`,
  `service_credentials`, `local_endpoint`, `none`
- `capabilities` — canonical capability tokens; for web providers,
  `search` and `extract` are modeled as **distinct** capabilities
- `implementation_state` — one of `implemented`, `partial`,
  `unimplemented`, `experimental`
- `setup_state` — one of `available`, `needs_setup`, `authenticating`,
  `configured`, `connected`, `degraded`, `error`, `unavailable`
- `runtime_binding` — the real owning subsystem, concrete adapter path
  (when one exists), the existing authoritative setup route (when one
  exists), the `provider_registry` provider id for inference entries, and
  whether a real backend OAuth authorization handler exists
- `required_fields`, `scopes` (when applicable), `setup_help`, and a safe
  `oauth` projection

## The five distinctions

The model deliberately keeps five meanings apart. The UI must never collapse
them into one green/gray dot:

1. **Catalog visibility** — an entry listed in the catalog.
2. **Credential/configuration presence** — derivable per-user state
   (channel config, oauth_connections row, provider credential presence).
3. **Adapter/runtime implementation** — a real Codexify runtime adapter
   currently exists (`implementation_state`).
4. **Runtime authorization** — the provider is allowed to execute under
   `guardian/core/provider_registry.py` and supported-profile policy.
5. **Live connection health** — a runtime probe currently reports healthy.

Examples of the distinction:

- MiniMax credentials configured ≠ MiniMax allowed by the supported
  profile ≠ MiniMax runtime healthy.
- Telegram adapter exists ≠ Telegram configured for this user ≠ Telegram
  currently connected.
- A gemini adapter module exists, but the provider registry records
  Gemini as `disabled` and the router does not dispatch it: the catalog
  reports `partial` implementation plus registry truth, and never claims
  authorization.

## Implementation-state semantics

`implemented` — a concrete runtime adapter/call path exists in code and is
wired into the owning subsystem. `partial` — adapter code exists but is not
fully wired (e.g. no router dispatch, no setup surface). `unimplemented` —
no Codexify runtime adapter exists; the entry is catalog discovery only.
`experimental` — reserved for future opt-in runtime lanes.

Implementation state is **static, code-proven catalog truth**. It is not a
runtime probe and not a supported-release claim.

## Setup-state semantics

Setup state is the per-user projection merged by
`GET /api/connections`:

- `unimplemented` entries always project `unavailable` — no setup flow
  exists, and the UI must say so instead of opening a dead flow.
- A persisted `oauth_connections` row projects safe metadata
  (provider, mode, status, scopes, `expires_at`, `last_refresh_at`,
  sanitized error classification). A `connected` row projects
  `connected`; `error` projects `error`; `pending` projects
  `authenticating`; `disconnected` projects `configured`.
- A user-scoped `channel_configs` row for Slack/Discord/Telegram projects
  `configured`.
- Registered inference providers project `configured` when registry
  authorization is available, `error` when authorization exists but
  availability is blocked, and `needs_setup` when credentials are absent.
- Unlisted inference providers report `registered: false` in their
  authorization projection; catalog visibility is not authorization.

`configured` never implies `connected`. Nothing in this slice fabricates
live health.

## Credential ownership

Credentials remain server-owned and user-scoped. The Connections API never
serializes access tokens, refresh tokens, API keys, OAuth client secrets, or
raw authorization codes. The only OAuth material projected to the frontend
is the safe metadata listed above, and raw `last_error` text is reduced to a
bounded classification (`provider_error`).

No OAuth exchange endpoints, no Hermes credentials, no OAuth client ids, and
no third-party private credentials were introduced by this slice.

## Runtime-binding ownership

- Messaging entries with adapters bind to `guardian.channels` and the
  existing channel configuration surface (`/api/channels/configs`).
- Inference entries bind to `guardian.core.provider_registry`; the
  registry, not the catalog, decides authorization. The catalog does not
  add providers to the registry.
- Web entries bind to no runtime yet. Catalog presence of Firecrawl,
  SearXNG, Brave, DDGS, Tavily, Exa, Parallel, or xAI/Grok does **not**
  change current search behavior: the legacy research search path and the
  separate remote-recall web seam are unaffected.
- Legacy sync connectors (GitHub) remain on the existing connector
  subsystem surface; their behavior is unchanged.

## Messaging/channel relationship

The three implemented messaging entries reflect real code:

| Entry | Adapter | Runtime credential |
| --- | --- | --- |
| Slack | `guardian.channels.adapters.slack.SlackAdapter` | server env bot token |
| Discord | `guardian.channels.adapters.discord.DiscordAdapter` | server env webhook URL |
| Telegram | `guardian.channels.adapters.telegram.TelegramAdapter` | server env bot token |

Per-user channel configuration, allowlists, pairing, and message audit
remain owned by `guardian/routes/channels.py`. All other requested
messaging platforms (Google Chat, WhatsApp, Signal, Mattermost, Matrix,
BlueBubbles/iMessage, Home Assistant, Email, SMS/Twilio, DingTalk,
Feishu/Lark, WeCom, Weixin/WeChat, QQ Bot, Yuanbao, Microsoft Teams, LINE,
ntfy, API Server, Webhooks) are catalog discovery entries with no adapter:
they are `unimplemented` and cannot change messaging behavior. Email is
additionally governed for future implementation by ADR-047.

## Inference / provider-registry relationship

Inference entries project the registry's current truth without replacing
it. Entries map to `provider_registry` ids where one exists
(`openai`, `anthropic`, `gemini`, `groq`, `deepseek`, `alibaba`,
`minimax`, `local`). Authorization (`authorized`, `available`, `enabled`,
governance classification, disabled reason) is computed at request time
from the registry's own primitives (`provider_governance`,
`provider_authorized`, `provider_availability`) — never reimplemented in
the catalog. Providers absent from the registry report
`registered: false`.

DeepSeek is modeled as API-key authentication (`api_key`), matching the
registry's `DEEPSEEK_API_KEY` authorization path.

## Web provider capability relationship

Search and Extract are distinct capabilities. The catalog matrix:

| Provider | search | extract |
| --- | --- | --- |
| Firecrawl | yes | yes |
| Tavily | yes | yes |
| Exa | yes | yes |
| Parallel | yes | yes |
| SearXNG | yes | no |
| Brave Search | yes | no |
| DDGS / DuckDuckGo | yes | no |
| xAI / Grok | yes | no |

Every web entry is `unimplemented` in this slice. This task creates the
control-plane vocabulary for later web-provider adapter tasks; it does not
make any provider executable and does not modify
`guardian/core/research/Modules/agent/search.py`.

## OAuth posture

The method vocabulary can represent `oauth_browser`, `oauth_device`,
`api_key`, `token`, `service_credentials`, `local_endpoint`, and `none`.
No backend OAuth authorization handler exists for any entry today, so
every entry reports `oauth.backend_handler_exists = false`. The frontend
may only enable an OAuth action when that flag is true. All
provider-specific OAuth work (MiniMax, Codex/ChatGPT, Qwen, Gemini, xAI,
Nous Portal, GitHub Copilot, Anthropic subscription) is deferred to later
atomic tasks.

## API surface

`GET /api/connections` — the full catalog with per-user state merged.

`GET /api/connections/{connection_id}` — one entry with the same merge;
404 for unknown ids.

The API is read-only. Existing subsystem mutation APIs remain the
authoritative mutation surfaces: `/api/channels/*` for channels,
`/api/connectors/*` for legacy sync connectors, and server configuration
plus provider-registry policy for inference. The Connections API creates
no duplicate mutation routes.

The router is registered in `guardian_api.py` under the existing
`connectors` supported-profile label and the existing
`CODEXIFY_ENABLE_CONNECTOR_ROUTES` flag, so the bay and its data source
stay gated together. Without a configured database, the API degrades to
the static catalog (no user state) rather than failing.

## Setup/configuration versus authorization versus health

- Configuration (credential/field presence) does not imply authorization.
- Authorization (registry + supported-profile allowance) does not imply
  runtime health.
- Catalog visibility does not imply implementation.
- Nothing in this slice claims a live, healthy provider connection.

## Explicit current non-claims

This slice does not:

- implement any provider-specific OAuth exchange;
- implement missing messaging adapters;
- implement web-search/extract adapters;
- replace or extend `guardian/core/provider_registry.py`;
- add a database migration or edit migration history;
- change retrieval-router, chat-loop, Flow, or Browser Host behavior;
- widen any supported-release or cloud-provider claim;
- create a new Settings section, AppShell view, or duplicate
  configuration surface.

`docs/architecture/00-current-state.md` remains release truth and was not
updated to claim any new provider, messaging, OAuth, or web support.
