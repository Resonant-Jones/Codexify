# Whoosh'd Local Provider

This note records the working local-provider configuration used to route Codexify execution through a Whoosh'd MLX server while keeping provider id `local`.

## Working Config

```env
LLM_PROVIDER=local
LOCAL_API_KEY=local
CODEXIFY_LOCAL_ENDPOINT_CHAIN=http://host.docker.internal:8000/v1
LOCAL_PROVIDER_DISPLAY_NAME=Whoosh'd
LOCAL_PROVIDER_VENDOR=whooshd
LOCAL_CHAT_MODEL=mlx-community/Llama-3.2-3B-Instruct-4bit
LOCAL_LLM_MODEL=mlx-community/Llama-3.2-3B-Instruct-4bit
LLM_MODEL=mlx-community/Llama-3.2-3B-Instruct-4bit
DEFAULT_LOCAL_MODEL=mlx-community/Llama-3.2-3B-Instruct-4bit
```

## Whoosh'd Runtime Command

```bash
WHOOSHD_ADAPTER=mlx \
WHOOSHD_MLX_MODEL=mlx-community/Llama-3.2-3B-Instruct-4bit \
python -m uvicorn whooshd.app:app --host 0.0.0.0 --port 8000
```

## Boundary Rule

- Do not create a new routed provider id for Whoosh'd.
- Execution remains under provider id `local`.
- Whoosh'd is display/vendor metadata plus local endpoint configuration.
- When Codexify runs in Docker and Whoosh'd runs on the macOS host, Whoosh'd must bind `0.0.0.0` and Codexify must reach it via `host.docker.internal`.

## Live Proof

- Codexify commit: `f603d0a929867b9e0b5ecad778419813bcf9eb6b`
- Whoosh'd inventory fix commit: `ad43c279714cd83facd7408febb917a0da6d0d7f`
- Live result: `task.completed` reached, assistant message `12412` persisted
- Cleanup: Whoosh'd `/runtime/requests` returned `active_count=0`
