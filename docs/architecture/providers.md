# Inference Providers

## MiniMax

MiniMax is available as a first-class chat provider through the backend provider
registry and `/api/llm/catalog`.

### Enable MiniMax

Set:

- `LLM_PROVIDER=minimax`
- `MINIMAX_API_KEY=<your_minimax_api_key>`
- `MINIMAX_API_BASE=<openai_compatible_base_url>`

Optional:

- `MINIMAX_MODEL=<default_model_id>`
- `MINIMAX_TIMEOUT_SECONDS=<request_timeout_seconds>`

When `LLM_PROVIDER=minimax`, backend config validation fails fast with a clear
message if `MINIMAX_API_KEY` or `MINIMAX_API_BASE` is missing.

### Routing behavior

- Provider registry loads MiniMax only when both `MINIMAX_API_KEY` and
  `MINIMAX_API_BASE` are present.
- Catalog entry is deterministic and includes one default model:
  `MINIMAX_MODEL` or `minimax-default`.
- Existing fallback order is unchanged. MiniMax is used only when selected.

### Security

- Keep MiniMax credentials server-side only.
- Do not commit `.env`/`.env.local` files with real keys.
- Do not expose provider keys to frontend clients in production.
