# Cloud Model Unlock

This is optional.

Do not commit or share API keys.

Cloud routing may send prompt or content data to the selected provider.

Provider billing and rate limits may apply.

Use your own key unless Resonant Jones explicitly gave you a temporary testing key.

Your tester-editable config file is:

- `~/Codexify/.env`

## Before You Change Anything

Start from the local reset values if you want the safest baseline:

```dotenv
ALLOW_CLOUD_PROVIDERS=false
CODEXIFY_LOCAL_ONLY_MODE=true
LLM_PROVIDER=local
```

## OpenAI-Style Example

Use placeholder values only:

```dotenv
ALLOW_CLOUD_PROVIDERS=true
CODEXIFY_LOCAL_ONLY_MODE=false
LLM_PROVIDER=openai
OPENAI_API_KEY=replace_with_your_key
OPENAI_MODEL=replace_with_supported_model
```

If your tester notes include an OpenAI base URL, add it too:

```dotenv
OPENAI_BASE_URL=replace_with_supported_base_url
```

## Anthropic-Style Example

The current packaged beta contract does not ship a dedicated `ANTHROPIC_MODEL` variable.

If your invite says to use an Anthropic-style cloud path, use the repo-supported Anthropic-compatible settings for that build.

For the current repo contract, that means the MiniMax Anthropic-compatible surface:

```dotenv
ALLOW_CLOUD_PROVIDERS=true
CODEXIFY_LOCAL_ONLY_MODE=false
LLM_PROVIDER=minimax
MINIMAX_API_KEY=replace_with_your_key
MINIMAX_API_BASE=https://api.minimax.io/anthropic
MINIMAX_API_FLAVOR=anthropic
MINIMAX_MODEL=replace_with_supported_model
```

If your tester build explicitly uses a direct Anthropic provider, follow the invite notes from Resonant Jones and keep the key placeholder-only.

## Local Reset Example

If you want to go back to the default local-only posture:

```dotenv
ALLOW_CLOUD_PROVIDERS=false
CODEXIFY_LOCAL_ONLY_MODE=true
LLM_PROVIDER=local
```

## Safety Notes

- Keep API keys in `~/Codexify/.env`
- Do not put real keys in the DMG
- Do not paste your key into screenshots or public messages
- If you are not sure which path you are using, ask before sending sensitive content
