# Inference Providers

## Alibaba / DashScope

Alibaba Cloud DashScope / Model Studio is available as a first-class chat
provider through the backend provider registry and `/api/llm/catalog`.

### Enable Alibaba / DashScope

Set:

- `LLM_PROVIDER=alibaba`
- `ALIBABA_API_KEY=<your_dashscope_api_key>`
- `ALIBABA_API_BASE=https://dashscope-us.aliyuncs.com/compatible-mode/v1`
- `ALLOW_CLOUD_PROVIDERS=true`
- `CODEXIFY_LOCAL_ONLY_MODE=false`
- `CODEXIFY_EGRESS_ALLOWLIST=...` including `alibaba`

Optional:

- `ALIBABA_MODEL=<default_model_id>`
- `ALIBABA_TIMEOUT_SECONDS=<request_timeout_seconds>`

Default base URL:

- `https://dashscope-us.aliyuncs.com/compatible-mode/v1`

When `LLM_PROVIDER=alibaba`, backend config validation fails fast with a clear
message if `ALIBABA_API_KEY` is missing or `ALIBABA_API_BASE` is blank.

### Routing behavior

- Runtime chat routing uses Alibaba through its OpenAI-compatible
  `/chat/completions` endpoint.
- Explicit request selection (`provider`/`model`) takes precedence over profile
  overrides in the chat worker.
- Provider registry loads Alibaba only when `ALIBABA_API_KEY` is present and
  `ALIBABA_API_BASE` resolves to a non-empty value.
- Catalog entry is deterministic and exposes `ALIBABA_MODEL` when configured.
- Existing fallback order is unchanged. Alibaba is used only when selected.

### Security

- Keep Alibaba credentials server-side only.
- Do not commit `.env`/`.env.local` files with real keys.
- Do not expose provider keys to frontend clients in production.

## MiniMax

MiniMax is available as a first-class chat provider through the backend provider
registry and `/api/llm/catalog`.

### Enable MiniMax

Set:

- `LLM_PROVIDER=minimax`
- `MINIMAX_API_KEY=<your_minimax_api_key>`
- `MINIMAX_API_BASE=https://api.minimax.io/anthropic`
- `MINIMAX_API_FLAVOR=anthropic`
- `ALLOW_CLOUD_PROVIDERS=true`
- `CODEXIFY_LOCAL_ONLY_MODE=false`
- `CODEXIFY_EGRESS_ALLOWLIST=...` including `minimax`

Optional:

- `MINIMAX_MODEL_DISCOVERY_URL=<explicit_model_catalog_url>` when you want to
  probe a documented MiniMax inventory endpoint directly
- `MINIMAX_ANTHROPIC_VERSION=<anthropic_api_version>` (used when flavor is `anthropic`)
- `MINIMAX_MODEL=<default_model_id>` (recommended direct-chat default: `MiniMax-M2.1`)
- `MINIMAX_TIMEOUT_SECONDS=<request_timeout_seconds>`

Base URL examples:

- Anthropic flavor (`MINIMAX_API_FLAVOR=anthropic`): `https://api.minimax.io/anthropic`
- OpenAI fallback (`MINIMAX_API_FLAVOR=openai`): `https://api.minimax.io/v1`

When `LLM_PROVIDER=minimax`, backend config validation fails fast with a clear
message if `MINIMAX_API_KEY` or `MINIMAX_API_BASE` is missing. The default
runtime flavor is Anthropic-compatible, and OpenAI-compatible MiniMax is only
used when explicitly selected.

### Routing behavior

- Runtime chat routing uses the Anthropic-compatible MiniMax surface by default.
- Explicit request selection (`provider`/`model`) takes precedence over profile
  overrides in the chat worker.
- Provider registry loads MiniMax only when both `MINIMAX_API_KEY` and
  `MINIMAX_API_BASE` are present.
- Catalog entry prefers live discovery when configured, but falls back to the
  documented MiniMax chat model list instead of hiding the provider when live
  discovery is unavailable.
- Prompt caching is most effective when the static system/tool prefix stays
  stable; Anthropic-compatible requests mark the stable system blocks with
  explicit cache metadata.
- Existing fallback order is unchanged. MiniMax is used only when selected.

### Security

- Keep MiniMax credentials server-side only.
- Do not commit `.env`/`.env.local` files with real keys.
- Do not expose provider keys to frontend clients in production.
