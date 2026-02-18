# Inference Providers

## MiniMax

MiniMax is available as a first-class chat provider through the backend provider
registry and `/api/llm/catalog`.

### Enable MiniMax

Set:

- `LLM_PROVIDER=minimax`
- `MINIMAX_API_KEY=<your_minimax_api_key>`
- `MINIMAX_API_BASE=<minimax_base_url>`
- `ALLOW_CLOUD_PROVIDERS=true`
- `CODEXIFY_LOCAL_ONLY_MODE=false`
- `CODEXIFY_EGRESS_ALLOWLIST=...` including `minimax`

Optional:

- `MINIMAX_API_FLAVOR=<openai|anthropic>` (default: `openai`)
- `MINIMAX_ANTHROPIC_VERSION=<anthropic_api_version>` (used when flavor is `anthropic`)
- `MINIMAX_MODEL=<default_model_id>`
- `MINIMAX_TIMEOUT_SECONDS=<request_timeout_seconds>`

Base URL examples:

- OpenAI flavor (`MINIMAX_API_FLAVOR=openai`): `https://api.minimax.io/v1`
- Anthropic flavor (`MINIMAX_API_FLAVOR=anthropic`): `https://api.minimax.io/anthropic`

When `LLM_PROVIDER=minimax`, backend config validation fails fast with a clear
message if `MINIMAX_API_KEY` or `MINIMAX_API_BASE` is missing.

### Routing behavior

- Runtime chat routing uses MiniMax only when explicitly selected.
- `MINIMAX_API_FLAVOR=openai` calls `.../chat/completions`.
- `MINIMAX_API_FLAVOR=anthropic` calls `.../v1/messages` (Anthropic-compatible).
- Explicit request selection (`provider`/`model`) takes precedence over profile
  overrides in the chat worker.
- Provider registry loads MiniMax only when both `MINIMAX_API_KEY` and
  `MINIMAX_API_BASE` are present.
- Catalog entry is deterministic and includes one default model:
  `MINIMAX_MODEL` or `minimax-default`.
- Existing fallback order is unchanged. MiniMax is used only when selected.

### Security

- Keep MiniMax credentials server-side only.
- Do not commit `.env`/`.env.local` files with real keys.
- Do not expose provider keys to frontend clients in production.
