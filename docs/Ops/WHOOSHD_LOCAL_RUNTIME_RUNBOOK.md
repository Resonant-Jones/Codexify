# Whoosh'd Local Runtime Runbook

Purpose: install, start, and prove the host-local Whoosh'd inference node that
Codexify uses through the canonical `LLM_PROVIDER=local` provider lane.

## Current Contract

Codexify does not import Whoosh'd Python code into its backend. Codexify treats
Whoosh'd as a separate local service that exposes an OpenAI-compatible HTTP API.

```text
Codexify backend / workers (Docker)
  -> host.docker.internal:8000
  -> Whoosh'd host process
  -> stub or MLX adapter
```

For the supported local beta path:

- `LLM_PROVIDER=local`
- `CODEXIFY_LOCAL_ONLY_MODE=true`
- `ALLOW_CLOUD_PROVIDERS=false`
- `LOCAL_BASE_URL=http://host.docker.internal:8000/v1`
- `VAULTNODE_BASE_URL=http://host.docker.internal:8000`
- `VAULTNODE_HEALTH_ENDPOINTS=/v1/models,/api/tags`

Model availability is live evidence. Codexify should only consider the selected
model usable when Whoosh'd advertises it through `/v1/models` or `/api/tags`.

## Nodes And Boundaries

| Boundary | Responsibility |
|---|---|
| Whoosh'd host process | Owns model loading, readiness, inference, and local model inventory. |
| Codexify backend and chat workers | Own routing, context assembly, queueing, persistence, and provider health reporting. |
| Docker host bridge | Lets Codexify containers reach the host-side Whoosh'd process through `host.docker.internal`. |
| Model cache | Local machine storage for MLX/HuggingFace artifacts; not stored in Codexify Git. |

Trust posture:

- Treat Whoosh'd as a local trusted node on the same machine.
- Keep prompts and completions on the local host when `ALLOW_CLOUD_PROVIDERS=false`.
- Do not treat `LOCAL_API_KEY=local` as security. It is a compatibility value,
  not a meaningful auth boundary.

## Install On This Machine

Default SSD-local layout:

```bash
export WHOOSHD_ROOT="/Volumes/Dev_SSD/ResonantConstructs/Whoosh'd"
export WHOOSHD_PYTHON="$WHOOSHD_ROOT/.venv311/bin/python"
```

If the checkout is missing:

```bash
mkdir -p /Volumes/Dev_SSD/ResonantConstructs
gh repo clone Resonant-Jones/whooshd "$WHOOSHD_ROOT"
```

Create or refresh the local Python environment:

```bash
/opt/homebrew/bin/python3.11 -m venv "$WHOOSHD_ROOT/.venv311"
"$WHOOSHD_PYTHON" -m pip install -e "$WHOOSHD_ROOT[dev]"
```

For MLX-backed inference:

```bash
"$WHOOSHD_PYTHON" -m pip install -e "$WHOOSHD_ROOT[mlx]"
```

## Start Whoosh'd

Stub mode proves the API contract without a model:

```bash
cd "$WHOOSHD_ROOT"
WHOOSHD_ADAPTER=stub \
"$WHOOSHD_PYTHON" -m uvicorn whooshd.app:app --host 127.0.0.1 --port 8000
```

MLX mode serves the configured model:

```bash
cd "$WHOOSHD_ROOT"
WHOOSHD_ADAPTER=mlx \
WHOOSHD_MLX_MODEL=mlx-community/Llama-3.2-3B-Instruct-4bit \
"$WHOOSHD_PYTHON" -m uvicorn whooshd.app:app --host 0.0.0.0 --port 8000
```

Use `127.0.0.1` for host-native Codexify checks. Use `0.0.0.0` when Dockerized
Codexify services need to reach Whoosh'd through `host.docker.internal`.

## Prove The Runtime Before Starting Codexify

From the host:

```bash
curl -s http://127.0.0.1:8000/health
curl -i http://127.0.0.1:8000/ready
curl -s http://127.0.0.1:8000/v1/models
curl -s http://127.0.0.1:8000/api/tags
```

For Docker bridge proof:

```bash
curl -s http://host.docker.internal:8000/health
curl -s http://host.docker.internal:8000/v1/models
curl -s http://host.docker.internal:8000/api/tags
```

If `LOCAL_CHAT_MODEL` is set to
`mlx-community/Llama-3.2-3B-Instruct-4bit`, the inventory response must include
that exact string.

## Start Codexify Against Whoosh'd

Codexify's `.env` should contain:

```dotenv
AI_BACKEND=ollama
LLM_PROVIDER=local
CODEXIFY_LOCAL_ONLY_MODE=true
ALLOW_CLOUD_PROVIDERS=false
LOCAL_BASE_URL=http://host.docker.internal:8000/v1
LOCAL_DOCKER_FALLBACK_BASE_URL=http://host.docker.internal:8000/v1
LOCAL_PROVIDER_DISPLAY_NAME=Whoosh'd
LOCAL_PROVIDER_VENDOR=whooshd
LOCAL_CHAT_MODEL=mlx-community/Llama-3.2-3B-Instruct-4bit
LOCAL_LLM_MODEL=mlx-community/Llama-3.2-3B-Instruct-4bit
LOCAL_COMPAT_FIRST=1
LOCAL_ENABLE_OLLAMA_GENERATE_FALLBACK=0
VAULTNODE_BASE_URL=http://host.docker.internal:8000
VAULTNODE_HEALTH_ENDPOINTS=/v1/models,/api/tags
```

Then start the supported Compose path:

```bash
docker compose up -d
```

Read these together before calling the runtime usable:

```bash
curl -s http://127.0.0.1:8888/health
curl -s http://127.0.0.1:8888/health/chat
curl -s http://127.0.0.1:8888/health/llm
curl -s http://127.0.0.1:8888/api/llm/catalog
```

## Failure Modes

| Symptom | Likely layer | First check |
|---|---|---|
| `local_inference_not_running` | Whoosh'd host process or Docker host bridge | `curl http://127.0.0.1:8000/v1/models` and `curl http://host.docker.internal:8000/v1/models` |
| `model_missing` | Whoosh'd inventory does not advertise `LOCAL_CHAT_MODEL` | `curl http://127.0.0.1:8000/v1/models` |
| `/health/chat` red | Codexify queue/worker layer | Redis and chat worker logs |
| `/health/llm` red while Whoosh'd is green | Codexify provider routing/config layer | `LOCAL_BASE_URL`, `LOCAL_CHAT_MODEL`, `/api/llm/catalog` |

## Binary Hardening Path

The current official local-beta path is a managed host service plus live
inventory proof. A true bundled Whoosh'd binary would be a separate hardening
slice:

1. Add a Whoosh'd release artifact or console executable.
2. Teach the Codexify launcher to resolve and start that executable.
3. Record process lifecycle, port binding, and model-cache location in launcher
   diagnostics.
4. Preserve the current HTTP contract so backend and worker code do not need to
   know how Whoosh'd was started.

Do not vendor the Whoosh'd source tree into Codexify as a shortcut. That would
blur ownership and make upgrades harder.
