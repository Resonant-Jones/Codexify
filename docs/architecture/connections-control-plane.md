# Connections Control Plane

## Purpose

The Settings **Connectors** tab is Codexify's single user-facing destination
for external connections. This document establishes the canonical
**Connections control plane**: one backend-owned, typed catalog that the
existing bay projects for discovering, inspecting, and setting up Messaging,
Web, Inference, and Knowledge integrations.

Connections is a **control plane, not a new execution owner**. The underlying
runtime systems retain their authority:

- Messaging runtime behavior remains owned by `guardian/channels/`.
- Generic sync connectors remain owned by the existing connector subsystem
  (`guardian/routes/connectors.py`, `/api/connectors`).
- Inference execution authorization remains owned by
  `guardian/core/provider_registry.py` and supported-profile policy.
- Web execution remains owned by the eventual web-tool/provider runtime.
- Knowledge-provider execution remains owned by the provider-specific
  knowledge adapter and Command Bus authority seam.
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

Exactly four canonical categories exist:

- `messaging`
- `web`
- `inference`
- `knowledge`

`knowledge` is the catalog classification for external content systems whose
primary value is access to user-authorized structured or semi-structured
knowledge. It is not a runtime owner and does not imply ingestion,
synchronization, indexing, memory writes, health, authorization, or write
access. ADR-075 defines the bounded taxonomy extension and its future
capability semantics.

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
- `capabilities` — canonical capability tokens. Web providers use distinct
  `search` and `extract` capabilities; Knowledge providers use distinct
  `content_search` and `content_read` capabilities as defined by ADR-075
- `implementation_state` — one of `implemented`, `partial`,
  `unimplemented`, `experimental`
- `setup_state` — one of `available`, `needs_setup`, `authenticating`,
  `configured`, `connected`, `degraded`, `error`, `unavailable`
- `runtime_binding` — the real owning subsystem, concrete adapter path
  (when one exists), the existing authoritative setup route (when one
  exists), the `provider_registry` provider id for inference entries, and
  whether a real backend OAuth authorization handler exists
- `required_fields`, `scopes` (when applicable), `setup_help`, and a safe
  `oauth` projection; provider-specific entries may also expose a safe
  bounded validation projection

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
- A user-scoped Notion credential record projects `needs_setup` when absent,
  `configured` when saved but unvalidated, `connected` only after an explicit
  successful validation, and `error` for bounded authorization, transport,
  or provider validation failures. The status contains no token or raw error.
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
bounded classification (`provider_error` or a provider-owned bounded code).

Google Drive / Docs adds a provider-specific server-side authorization-code
flow. Its node/operator-owned client id, client secret, and redirect URI are
read only from `GOOGLE_DRIVE_OAUTH_CLIENT_ID`,
`GOOGLE_DRIVE_OAUTH_CLIENT_SECRET`, and
`GOOGLE_DRIVE_OAUTH_REDIRECT_URI`; none is serialized through the catalog or
frontend. Its state is signed, the PKCE verifier is server-only, and returned
access/refresh credentials are encrypted at rest in `oauth_connections` under
the user-scoped provider key `google_drive` / mode `node_local`. The browser
receives only a server-generated authorization URL and never calls Google
content APIs directly.

The narrowly scoped Notion integration token is described below.

The Notion integration token is not stored in `oauth_connections`: it is an
integration token rather than an OAuth grant. Its one-per-user
`notion_connection_credentials` record is encrypted using the existing
server-side secret primitive and can only be configured or removed by its
provider-specific setup route. Neither that encrypted value nor a token
prefix, suffix, hash, authorization header, or upstream raw error is exposed
through the Connections projection or browser storage.

## Runtime-binding ownership

- Messaging entries with adapters bind to `guardian.channels`, but the
  Connections bay does not collect or persist their runtime credentials.
  These adapters currently read server-managed environment credentials; the
  generic `/api/channels/configs` JSON route is not advertised as a
  Connections setup action.
- Inference entries bind to `guardian.core.provider_registry`; the
  registry, not the catalog, decides authorization. The catalog does not
  add providers to the registry.
- Web entries bind to no runtime yet. Catalog presence of Firecrawl,
  SearXNG, Brave, DDGS, Tavily, Exa, Parallel, or xAI/Grok does **not**
  change current search behavior: the legacy research search path and the
  separate remote-recall web seam are unaffected.
- The implemented Notion Knowledge entry binds to
  `guardian.connections.notion`. Its adapter owns only Notion REST API
  translation; `/api/connect/notion/*` owns configuration, validation,
  status, and disconnect, while GET-only `/api/knowledge/notion/search` and
  `/api/knowledge/notion/read/{object_id}` are the bounded operations that
  Command Bus registers as read commands. The catalog remains a projection:
  it does not own execution, credentials, authorization, or health.
- The implemented Google Drive / Docs Knowledge entry binds to
  `guardian.connections.google_drive`. Its server-owned OAuth setup routes
  live under `/api/connect/google-drive/*`; GET-only
  `/api/knowledge/google-drive/search` and
  `/api/knowledge/google-drive/read/{object_id}` are the bounded Command Bus
  read operations. Drive is used only for native Google Docs discovery and
  metadata; the adapter translates one selected native Google Doc through the
  Docs read API. It does not read Sheets, Slides, PDFs, ordinary files, Gmail,
  Calendar, Contacts, or Chat, and it has no Google mutation path.
- Legacy sync connectors (GitHub) remain on the existing connector
  subsystem surface; their behavior is unchanged.

## Messaging/channel relationship

The three implemented messaging entries reflect real code:

| Entry | Adapter | Runtime credential |
| --- | --- | --- |
| Slack | `guardian.channels.adapters.slack.SlackAdapter` | server-managed env bot token; no Connections setup action |
| Discord | `guardian.channels.adapters.discord.DiscordAdapter` | server-managed env webhook URL; no Connections setup action |
| Telegram | `guardian.channels.adapters.telegram.TelegramAdapter` | server-managed env bot token; no Connections setup action |

Per-user channel configuration, allowlists, pairing, and message audit
remain owned by `guardian/routes/channels.py`; they are not entered through
this Connections setup action. All other requested
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

## Knowledge provider capability relationship

Knowledge is distinct from Web retrieval. `content_search` means bounded
discovery of objects visible through an authenticated or explicitly scoped
provider connection; `content_read` means bounded normalized reading of one
selected accessible object. Both return external evidence, not automatic
ingestion, synchronization, embedding, document persistence, memory writes,
or identity inference. Any later persistence path must retain source
provenance.

Notion is the first canonical, read-only Knowledge Connection. It implements
only `content_search` and `content_read` for Notion pages shared with the
configured integration, with bounded page/block pagination and normalized
source provenance. It does not write Notion, ingest or synchronize content,
create documents, embeddings, memory, graph records, or a global database
binding.

`google_drive` is the second canonical Knowledge Connection, displayed as
Google Drive / Docs. Its `content_search` operation filters Drive discovery to
the native Google Docs MIME type and returns bounded normalized metadata,
opaque continuation state, and external provenance. Its `content_read`
operation verifies that selected object type before using the Docs API,
normalizes the default document tab's paragraphs, headings, list items, and
straightforward tables into a bounded text result, and reports truncation. It
requests exactly `drive.metadata.readonly` for discovery and
`documents.readonly` for document reads: both are read-only, but Google
currently classifies the former as restricted and the latter as sensitive.
OAuth application verification/security assessment and live account/shared
Drive qualification remain operator work, not a release claim. Google Chat
and Gemini remain Messaging and Inference identities; Sheets, Slides, Gmail,
Calendar, Contacts, and Chat remain separate future decisions.

Both implementations and focused tests prove local adapter seams only; live
provider-account qualification remains separate and is not a release claim.

## OAuth posture

The method vocabulary can represent `oauth_browser`, `oauth_device`,
`api_key`, `token`, `service_credentials`, `local_endpoint`, and `none`.
The frontend may only enable an OAuth action when
`oauth.backend_handler_exists` is true **and** the node's launchability gate
(`oauth.launchable`) is true. The launchability gate is intentionally
narrower than "a backend handler exists in code": for a future OAuth entry
to become clickable, it must additionally expose a real
`runtime_binding.setup_route`, and (where the protocol requires it) the node
must supply legitimate application-owned configuration. A node without a
complete Google Drive OAuth client id, client secret, redirect URI, and state
signing secret therefore keeps `google_drive` visibly unavailable, even
though its backend handler is mounted.

MiniMax OAuth is the first provider-specific OAuth setup slice. Its
provider-specific mutation routes (`/api/connect/minimax/start`,
`/api/connect/minimax/poll`, `/api/connect/minimax/disconnect`,
`/api/connect/minimax/status`) live on a dedicated
`minimax_oauth` route family, distinct from the read-only `connections`
surface and the quarantined legacy `connectors` surface. The
`v1-local-core-web-mcp` supported profile mounts these routes as
`internal_only` (hidden from public OpenAPI) while leaving `connections =
enabled` and `connectors = quarantined`. Authentication/setup is implemented;
OAuth-to-inference credential binding is deliberately deferred to a
separate task that must independently preserve provider-registry
authority and prove an authenticated persisted MiniMax turn.

Credentials are encrypted at rest through `guardian.connectors.oauth_crypto`
and persisted under provider key `minimax_oauth`, mode `node_local`. The
PKCE verifier, access tokens, refresh tokens, and any browser-visible
flow metadata are kept server-side; the frontend polls only the backend
poll route and never the upstream provider directly.

Google Drive / Docs is a separate OAuth browser-flow identity, not a generic
Google catalog entry. `/api/connect/google-drive/start` records only a pending
user-scoped grant before returning a server-generated authorization URL;
`/callback` verifies state and PKCE, exchanges the code server-side, performs
a minimal read-only Drive validation, and exposes only safe state through the
catalog. Access-token refresh is server-side, and disconnect clears the local
`google_drive` encrypted grant without a provider write. A successful
canonical connection clears the quarantined historical generic `google` OAuth
row so two active local OAuth authorities do not represent the same Google
content domain.

All other provider-specific OAuth work (Codex/ChatGPT, Qwen, Gemini,
xAI, Nous Portal, GitHub Copilot, Anthropic subscription) remains
deferred. Their `oauth.backend_handler_exists` flag stays false.

## API surface

`GET /api/connections` — the full catalog with per-user state merged.

`GET /api/connections/{connection_id}` — one entry with the same merge;
404 for unknown ids.

The API is read-only. Existing subsystem mutation APIs remain the
authoritative mutation surfaces: `/api/channels/*` for channels,
`/api/connectors/*` for legacy sync connectors, and server configuration
plus provider-registry policy for inference. The Connections API creates
no duplicate mutation routes.

Notion credential mutation is deliberately outside this router on the
provider-specific, internal-only `/api/connect/notion/*` setup seam. The
generic legacy `/api/connectors` route family remains quarantined and is not
used by either Knowledge runtime. Google Drive / Docs OAuth setup likewise
stays outside this router on `/api/connect/google-drive/*`; only its bounded
GET read operations appear in the enabled Knowledge/Command Bus surface. The
historical `guardian/connectors/gsuite.py` implementation is a non-authoritative
reference artifact and is not imported by the canonical Google Drive runtime.

`guardian_api.py` registers the read-only Connections router under the
distinct `connections` supported-profile route identity and the
`CODEXIFY_ENABLE_CONNECTIONS_ROUTES` flag. The legacy sync connector router
remains under the separate `connectors` identity and
`CODEXIFY_ENABLE_CONNECTOR_ROUTES` flag. The supported local Web profile
enables the former while quarantining the latter, so exposing
`/api/connections` does not expose `/api/connectors` or its mutation/sync
authority. Without a configured database, the API degrades to the static
catalog (no user state) rather than failing.

## Setup/configuration versus authorization versus health

- Configuration (credential/field presence) does not imply authorization.
- Authorization (registry + supported-profile allowance) does not imply
  runtime health.
- Catalog visibility does not imply implementation.
- Nothing in this slice claims a live, healthy provider connection.

## Explicit current non-claims

This slice does not:

- implement any other provider-specific OAuth exchange;
- bind MiniMax OAuth credentials to the inference runtime (separate task);
- implement missing messaging adapters;
- implement web-search/extract adapters;
- replace or extend `guardian/core/provider_registry.py`;
- add a database migration or edit migration history;
- change retrieval-router, chat-loop, Flow, or Browser Host behavior;
- widen any supported-release or cloud-provider claim;
- create a new Settings section, AppShell view, or duplicate
  configuration surface.

`docs/architecture/00-current-state.md` remains release truth. MiniMax OAuth
setup code exists under Connections but is intentionally not promoted to
Beta-Supported; OAuth-to-inference credential binding remains Out of Beta.
