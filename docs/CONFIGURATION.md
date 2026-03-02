# Configuration Reference

This document focuses on security-relevant runtime configuration.

Canonical sources:
- Runtime settings model: `guardian/core/config.py`
- Auth/identity behavior: `guardian/core/dependencies.py`
- Egress policy engine: `guardian/core/egress.py`
- Federation policy verification: `guardian/core/auth.py`, `guardian/routes/federation.py`

## Identity and Auth Boundary

| Variable | Default | Purpose |
|---|---|---|
| `CODEXIFY_SINGLE_USER_ID` | `local` (implicit) | Canonical server-side single-user identity. |
| `GUARDIAN_AUTH_MODE` | `local` | `local` allows static API key auth; `remote` requires session/JWT. |
| `GUARDIAN_API_KEY` | unset | API key used in local auth mode and compatibility fallback contexts. |
| `GUARDIAN_API_KEYS` | unset | Optional comma-separated additional API keys. |
| `GUARDIAN_SESSION_SECRET` | unset | Preferred signing secret for session/JWT validation in remote mode. |
| `GUARDIAN_JWT_SECRET` | unset | Optional JWT secret fallback in remote mode. |
| `DEBUG` | `false` (runtime default) | Enables debug behaviors; can permit `X-User-Id` override in local workflows. |
| `LOCAL_DEV` | `false` | Alternate local-dev toggle for `X-User-Id` override. |

Notes:
- `X-User-Id` is ignored unless `DEBUG=true` or `LOCAL_DEV=true`.
- In `GUARDIAN_AUTH_MODE=remote`, static API-key auth for protected routes is rejected.

## Egress and Provider Controls

| Variable | Default | Purpose |
|---|---|---|
| `CODEXIFY_LOCAL_ONLY_MODE` | `true` | Master fail-closed egress gate. |
| `CODEXIFY_EGRESS_ALLOWLIST` | empty | Comma-separated allowed outbound targets when local-only mode is disabled. |
| `ALLOW_CLOUD_PROVIDERS` | `false` | Additional gate for cloud LLM targets (`openai`, `groq`, `minimax`). |
| `LLM_PROVIDER` | `local` | Active chat provider (`local`, `openai`, `groq`, `minimax`). Must be a single provider id. |
| `OPENAI_API_KEY` | unset | Required for OpenAI usage when enabled. |
| `GROQ_API_KEY` | unset | Required for Groq usage when enabled. |
| `MINIMAX_API_KEY` | unset | Required for MiniMax usage when enabled. |
| `MINIMAX_API_BASE` | unset | Required OpenAI-compatible base URL for MiniMax (for example `https://api.minimax.chat/v1`). |
| `ELEVENLABS_API_KEY` | unset | Required for ElevenLabs TTS when enabled. |

Allowlist target names currently enforced in code:
- `openai`, `groq`, `minimax`, `elevenlabs`, `federation`, `webhook`

### Enabling a cloud LLM safely

Example (OpenAI/Groq/MiniMax enabled):

```env
ALLOW_CLOUD_PROVIDERS=true
CODEXIFY_LOCAL_ONLY_MODE=false
CODEXIFY_EGRESS_ALLOWLIST=openai,groq,minimax
LLM_PROVIDER=openai
OPENAI_API_KEY=...
# GROQ_API_KEY=...
# MINIMAX_API_KEY=...
# MINIMAX_API_BASE=https://api.minimax.chat/v1
```

Without this full set, egress remains blocked by policy.

## Federation Controls

| Variable | Default | Purpose |
|---|---|---|
| `GUARDIAN_FEDERATION_ENABLED` | `false` | Master gate for federation endpoints. |
| `GUARDIAN_FEDERATION_REQUIRE_SIGNED_POLICY` | `true` | Require signed trust policy for federation requests. |
| `GUARDIAN_FEDERATION_TRUST_POLICY_JSON` | unset | JSON trust policy document. |
| `GUARDIAN_FEDERATION_TRUST_POLICY_SIGNATURE` | unset | Base64url HMAC signature for trust policy JSON. |
| `GUARDIAN_FEDERATION_POLICY_SIGNING_KEY` | unset | Key used to verify trust policy signatures. |

Notes:
- Federation request paths also require egress allowlist permission (`federation`).
- Federation should remain disabled unless trust policy and peer controls are configured.

## Beta-1 Quarantine Controls

| Variable | Default | Purpose |
|---|---|---|
| `CODEXIFY_BETA_CORE_ONLY` | `false` | Hard-quarantine mode. When `true`, only Beta-1 core routers are mounted (chat, migration, media upload/list, projects/threads, health/admin). |
| `CODEXIFY_ENABLE_CONNECTOR_ROUTES` | `true` | Enable/disable connector routes when not in core-only mode. |
| `CODEXIFY_ENABLE_FEDERATION_ROUTES` | `true` | Enable/disable federation routes when not in core-only mode. |
| `CODEXIFY_ENABLE_FLOW_ROUTES` | `true` | Enable/disable flow routes when not in core-only mode. |
| `CODEXIFY_ENABLE_TOOL_ROUTES` | `true` | Enable/disable `/tools` and `/api/tools` routes when not in core-only mode. |
| `CODEXIFY_ENABLE_COMMAND_BUS_ROUTES` | `true` | Enable/disable `/api/guardian/commands/*` routes when not in core-only mode. |
| `CODEXIFY_ENABLE_CRON_ROUTES` | `true` | Enable/disable `/api/cron/*` routes when not in core-only mode. |
| `CODEXIFY_ENABLE_WEBSOCKET_ROUTES` | `true` | Enable/disable websocket route surface when not in core-only mode. |
| `CODEXIFY_ENABLE_MEDIA_GENERATION_ROUTES` | `true` | Enable/disable `/api/media/generate/image`. |
| `CODEXIFY_ENABLE_MEDIA_TTS_ROUTES` | `true` | Enable/disable `/api/media/tts/*`. |

Notes:
- `CODEXIFY_BETA_CORE_ONLY=true` takes precedence and quarantines non-core routers regardless of per-route toggles.
- Quarantined routes are not mounted (or return `404` for media subfeatures that share the media router).

## Plugin Loader Surface

Plugin loading is centralized through `guardian/core/plugins.py`.

Behavior:
- Runtime loader access via `get_runtime_plugin_loader()`.
- Guarded runtime initialization via `load_runtime_plugins()`.
- Manifest discovery via `list_plugin_manifests()` with dedupe and entrypoint scheme checks.

## Startup Coherence Checks

`guardian/guardian_api.py` performs a startup coherence assertion via:
- `guardian/core/config.py:assert_config_coherence`

Current overlapping security-relevant fields checked:
- `GUARDIAN_API_KEY`
- `GUARDIAN_API_KEYS`
- `GUARDIAN_DATABASE_URL`
- `OPENAI_API_KEY`
- `GROQ_API_KEY`

If config systems disagree on these values, startup fails fast.
