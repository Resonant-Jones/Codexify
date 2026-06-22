# Whoosh'd Local Provider — Durable Docker Smoke Contract

## Overview

Whoosh'd is a standalone local inference gateway that Codexify connects to
over HTTP.  It is **not merged into Codexify**, and Codexify never imports
Whoosh'd internals.  All communication uses the OpenAI-compatible
`/v1/chat/completions` endpoint.

This document describes the durable Docker smoke path for verifying the
Whoosh'd integration end-to-end.

## Quick Start: Docker Smoke

```bash
# Full stack
bash scripts/whooshd_docker_smoke_up.sh

# Minimal smoke stack (db redis migrator backend worker-chat)
bash scripts/whooshd_docker_smoke_up.sh minimal
```

The script:
1. Probes Whoosh'd host health at `http://host.docker.internal:8000/health`
2. Cleans stale Codexify containers
3. Tears down orphaned Compose services
4. Resolves the merged Compose config with the smoke override
5. Asserts the blessed gateway contract is present
6. Starts the stack

## Blessed Gateway Contract

The `v1-local-core-web-mcp` supported profile requires these exact values:

| Variable | Required Value |
|----------|---------------|
| `LLM_PROVIDER` | `local` |
| `LOCAL_PROVIDER_VENDOR` | `whooshd` |
| `LOCAL_BASE_URL` | `http://host.docker.internal:8000/v1` |
| `WHOOSHD_HEALTH_BASE_URL` | `http://host.docker.internal:8000` |
| `ALLOW_CLOUD_PROVIDERS` | `false` |
| `CODEXIFY_EGRESS_ALLOWLIST` | `""` (empty) |
| `CODEXIFY_LOCAL_ONLY_MODE` | `true` |

Model names are intentionally not enforced by the supported profile. The
Whoosh'd smoke override currently sets:

| Variable | Smoke Default |
|----------|---------------|
| `LOCAL_CHAT_MODEL` | `mlx-community/gemma-4-e2b-it-4bit` |
| `LOCAL_VISION_MODEL` | `qwen2-vl-2b-mlx` |
| `LOCAL_GGUF_MODEL` | `qwen2.5-0.5b-gguf` |

Those defaults are configuration, not live-model proof.

If your Whoosh'd host maintains a registry of several models, point the
launcher at it with `WHOOSHD_MODEL_REGISTRY_PATH` and use
`WHOOSHD_MLX_MODEL` to choose the default MLX model at startup. The launcher
now forwards both env vars when present so the host can expose multiple
registered models without hardcoding a single selection in Codexify.

## Live Inventory Truth

Codexify treats Whoosh'd live inventory as proven only by Whoosh'd HTTP
inventory surfaces:

```bash
curl http://localhost:8000/v1/models
curl http://localhost:8000/api/tags
```

Inside the Docker backend container, use the host bridge instead of host
localhost:

```bash
curl http://host.docker.internal:8000/v1/models
curl http://host.docker.internal:8000/api/tags
```

If `LOCAL_CHAT_MODEL` is set to Gemma E2B but Whoosh'd advertises only
models such as `llama-3.2-3b-mlx`, `qwen2-vl-2b-mlx`, and
`qwen2.5-0.5b-gguf`, Codexify must not claim Gemma execution. Catalog and
health surfaces should keep the advertised models visible while marking the
configured model unavailable with:

```txt
configured_model_not_advertised_by_whooshd
```

Interpretation: the local Whoosh'd endpoint was reachable and returned live
inventory, but the configured chat default was not in that inventory. This is
a catalog/configuration mismatch, not proof that Whoosh'd inference is broken
for every advertised model.

## Why Not Patch .env?

The default `.env` file contains development defaults that may point at
Ollama, Tailscale hosts, or include cloud provider allowlists.  Tearing
these apart for every smoke cycle is fragile.  The Compose override is
the single source of truth and survives `.env` churn.

## Manual Shell Exports Are Fragile

Do not rely on manual `export` commands to set smoke variables.  Shell
exports leak across sessions, are easy to forget, and are invisible to
other developers.  Always use the smoke wrapper script or the explicit
`-f docker-compose.whooshd-smoke.yml` flag.

## Inspecting the Resolved Config

```bash
docker compose -f docker-compose.yml -f docker-compose.whooshd-smoke.yml config \
  > /tmp/resolved.yml

# Check key values
grep -E 'LOCAL_BASE_URL|ALLOW_CLOUD|EGRESS|LLM_PROVIDER|CODEXIFY_LOCAL' /tmp/resolved.yml
```

## Cleaning Stale Containers

```bash
# Remove only Codexify containers
docker rm -f $(docker ps -aq --filter "name=codexify") 2>/dev/null || true

# Full teardown (preserves volumes)
docker compose -f docker-compose.yml -f docker-compose.whooshd-smoke.yml down --remove-orphans

# Full teardown (resets database)
docker compose -f docker-compose.yml -f docker-compose.whooshd-smoke.yml down --remove-orphans --volumes
```

## Verification Checklist

After startup, verify each lane:

### Backend Health
```bash
curl http://localhost:8888/ping
curl http://localhost:8888/health
curl http://localhost:8888/api/health/llm
```

Expected: `provider: "local"`, `models_available: true` (if Whoosh'd is running).

If the configured chat model is not advertised by Whoosh'd, expect
`models_available: false` for the selected model plus advertised-model evidence
in `model_resolution`. That degraded health does not hide the live inventory
from `/api/llm/catalog`.

### Text Smoke
```bash
curl -X POST http://localhost:8888/api/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <key>" \
  -d '{"prompt": "Reply with exactly: Whooshd text smoke ok."}'
```

Verify: `provider=local`, the final model is the configured chat model only
when Whoosh'd advertises it, and no cloud fallback occurs. If Gemma E2B is the
configured default but absent from `/v1/models` and `/api/tags`, this smoke is
blocked by inventory mismatch rather than counted as Gemma live proof.

### Vision Smoke (synchronous)
Use the `tests/fixtures/vision/color_shapes.png` fixture with a multimodal
request:

```bash
curl -X POST http://localhost:8888/api/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <key>" \
  -d '{"messages":[{"role":"user","content":[
    {"type":"text","text":"What shapes and colors?"},
    {"type":"image_url","image_url":{"url":"data:image/png;base64,..."}}
  ]}],"max_tokens":80}'
```

Verify: `model=qwen2-vl-2b-mlx`, `source=local_vision_env`,
Whoosh'd routes to `mlx_vlm`, response identifies shapes/colors correctly.

### GGUF Smoke
```bash
# Start llama-server on the host (port 9090, or any free port)
llama-server \
  -m models/gguf/qwen2.5-0.5b-instruct-q4_k_m.gguf \
  --host 127.0.0.1 --port 9090 -ngl 99
```

Verify the model appears in Whoosh'd registry and that Whoosh'd has
an active `llama_cpp` runtime configured to point at the llama-server.

**Current blocker:** Whoosh'd has `qwen2.5-0.5b-gguf` in its model
inventory but no `llama_cpp` runtime is registered.  Direct llama-server
inference works; Codexify routing correctly preserves the model name;
Whoosh'd-side runtime configuration is needed.

### Async Worker Smoke
Submit a queued chat completion task.  Verify the worker dequeues,
processes via Whoosh'd, and persists the assistant response.

### Async Multimodal Worker Smoke
**Current limitation:** The queued async chat path stores messages as
plain text.  Multimodal content (with `type: image_url` in the messages
array) is only supported through the synchronous `/api/chat` endpoint.
The async worker sees plain-text messages and does not detect image
attachments.  This is a structural limitation of the message persistence
format.

### No Cloud Fallback
In local-only mode, any attempt to route to a cloud provider must fail.
Verify logs show no `groq`, `openai`, `anthropic`, `gemini`, `minimax`,
or `alibaba` provider activity.

### No Base64 Logging
Verify that raw base64 image payloads from multimodal requests do not
appear in application logs.

## Architecture

```
┌─────────────┐     HTTP /v1/chat/completions     ┌──────────────┐
│  Codexify    │ ──────────────────────────────────▶│   Whoosh'd    │
│  (Docker)    │◀────────────────────────────────── │  (host)       │
└─────────────┘                                     └──────────────┘
                                                     │
                                                     ├─ mlx_chat (MLX)
                                                     ├─ mlx_vlm  (Vision)
                                                     └─ llama_cpp (GGUF)
```

Codexify → Whoosh'd: `POST http://host.docker.internal:8000/v1/chat/completions`

Whoosh'd model aliases are resolved from Codexify's `config/whooshd/model-profiles/`
directory — these map short names (`llama-3.2-3b-mlx`) to runtime model IDs
and backend routing hints.

## Tests

```bash
pytest tests/test_whooshd_smoke_env_contract.py -v
```

Covers: supported profile existence, contract validation, Compose override
structure, contract rejection scenarios, model propagation, Whoosh'd
standalone boundary, and smoke wrapper script integrity.

## Whoosh'd Remains Standalone

- Whoosh'd is launched and managed **outside** this Docker Compose stack.
- Codexify communicates with Whoosh'd exclusively over HTTP.
- The `docker-compose.whooshd-smoke.yml` override does **not** add a
  Whoosh'd container.
- Codexify never imports Whoosh'd server internals.

## Live Verification Results (Phase 30–31)

All lanes verified 2026-06-14 against host Whoosh'd + Docker Codexify.

| Lane | Status | Notes |
|------|--------|-------|
| Text smoke (sync) | ✅ pass | `llama-3.2-3b-mlx`, "Whooshd text smoke ok." |
| Vision smoke (sync) | ✅ pass | `qwen2-vl-2b-mlx`, source=`local_vision_env` |
| Async worker text smoke | ✅ pass | Task lifecycle QUEUED→COMPLETED, SSE events verified |
| Streaming events | ✅ pass | 5 lifecycle states published via Redis streams |
| Async multimodal | ⬜ blocked | Worker sees plain-text messages; structural limitation |
| GGUF smoke | ⬜ blocked | llama-server runs but Whoosh'd has no llama_cpp runtime |
| No cloud fallback | ✅ pass | 0 cloud provider activity in logs |
| Base64 logging safety | ✅ pass | 0 `data:image` or long base64 blobs in logs |
| Supported profile validation | ✅ pass | `mismatches: []`, `valid: true` |
| Whoosh'd standalone | ✅ preserved | No Whoosh'd import or container in Codexify |
