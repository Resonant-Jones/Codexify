# Live Whoosh'd Catalog Mismatch Proof - 2026-06-15

## Scope

This proof verifies Phase 36A behavior from the supported local Docker path:
Codexify must expose live Whoosh'd inventory while marking the configured
Gemma E2B default unavailable when Whoosh'd does not advertise it.

This is a proof artifact only. No product code or broad architecture docs were
changed.

## Repo And Contract Checks

- Working repo: `/Users/resonant_jones/Keep/Resonant_Constructs/projectCodexify/Codexify`
- Proof starting HEAD: `9710ba3efad6ea10c6312ccad0696ef26c4bc081`
- Phase 36A commit present in recent history:
  `d68f38561 fix(local): surface Whooshd catalog inventory mismatches`
- Required architecture docs were read before proof.
- `docs/architecture/adr/ADR Index.md` was not present in this checkout;
  `docs/architecture/adr/adr-index.md` was present and read.

Current-truth anchors checked:

- Codexify remains local-first beta hardening.
- Local Docker Compose remains the supported path.
- Whoosh'd is a supported Apple Silicon local runtime preset.
- Live Whoosh'd model availability is proven only through `/v1/models` or
  `/api/tags`.
- The Gemma E2B smoke default is a configured default, not live-model proof.
- Catalog, health, supported profile, and provider registry truth must be read
  together.

## Stack Startup Notes

The smoke override was used to preserve the Whoosh'd proof posture:

- `LLM_PROVIDER=local`
- `LOCAL_PROVIDER_VENDOR=whooshd`
- `LOCAL_CHAT_MODEL=mlx-community/gemma-4-e2b-it-4bit`
- `ALLOW_CLOUD_PROVIDERS=false`
- `CODEXIFY_EGRESS_ALLOWLIST=`
- `CODEXIFY_LOCAL_ONLY_MODE=true`

The first direct smoke start failed because `.env` currently supplies
`AI_BACKEND=local`, while the legacy `guardian.config.core.Settings` schema
accepts only `ollama`, `openai`, `gemini`, `groq`, or `anthropic` for
`AI_BACKEND`.

For the live proof only, a temporary env file outside the repo was created at
`/tmp/codexify-whooshd-proof.env` with `AI_BACKEND=ollama`. The canonical
provider rail remained `LLM_PROVIDER=local`; the temporary value only allowed
the legacy settings object to initialize.

Backend container proof environment:

```txt
AI_BACKEND=ollama
LLM_PROVIDER=local
LOCAL_PROVIDER_VENDOR=whooshd
LOCAL_CHAT_MODEL=mlx-community/gemma-4-e2b-it-4bit
ALLOW_CLOUD_PROVIDERS=false
CODEXIFY_EGRESS_ALLOWLIST=
CODEXIFY_LOCAL_ONLY_MODE=true
```

Final stack status:

```txt
codexify-backend-1      Up (healthy), port 8888
codexify-db-1           Up (healthy), port 5433
codexify-redis-1        Up (healthy)
codexify-worker-chat-1  Up
```

## Host Whoosh'd Inventory

Host probes:

```bash
curl -s http://localhost:8000/v1/models | jq
curl -s http://localhost:8000/api/tags | jq
curl -s http://localhost:8000/health/runtime | jq
```

Observed live model IDs from both `/v1/models` and `/api/tags`:

```txt
qwen2.5-0.5b-gguf
llama-3.2-3b-mlx
qwen2-vl-2b-mlx
```

Gemma E2B was not advertised by either live inventory endpoint.

`/health/runtime` reported Whoosh'd runtime status `ok`, with text MLX still
configured as `mlx-community/Llama-3.2-3B-Instruct-4bit`.

## Backend Container Reachability

Backend container probes:

```bash
docker compose -f docker-compose.yml -f docker-compose.whooshd-smoke.yml \
  exec -T backend python3 -c '...'
```

Container URLs checked:

```txt
http://host.docker.internal:8000/v1/models
http://host.docker.internal:8000/api/tags
http://host.docker.internal:8000/health/runtime
```

Result:

- `/v1/models`: reachable, advertised the three live models above.
- `/api/tags`: reachable, advertised the same three live models.
- `/health/runtime`: reachable, status `ok`.

This proves Codexify can reach Whoosh'd inventory from the supported Docker
path.

## Codexify Health And Catalog Results

Codexify routes queried from host:

```bash
BASE=http://localhost:8888
curl -s -H "X-API-Key: $GUARDIAN_API_KEY" "$BASE/health" | jq
curl -s -H "X-API-Key: $GUARDIAN_API_KEY" "$BASE/health/llm" | jq
curl -s -H "X-API-Key: $GUARDIAN_API_KEY" "$BASE/health/chat" | jq
curl -s -H "X-API-Key: $GUARDIAN_API_KEY" "$BASE/api/llm/catalog" | jq
curl -s -H "X-API-Key: $GUARDIAN_API_KEY" "$BASE/api/llm/catalog?include=all" | jq
```

### `/health`

- Overall status: `ok`
- Supported profile: `v1-local-core-web-mcp`
- Supported profile valid: `true`
- Supported profile mismatches: `[]`
- Selected provider: `local`
- Cloud-capable configuration present: `false`
- Release hold: `false`

### `/health/llm`

- Status: `down`
- Details status: `misconfigured`
- Provider: `local`
- Configured model: `mlx-community/gemma-4-e2b-it-4bit`
- Configured model available: `false`
- Availability reason: `configured_model_not_advertised_by_whooshd`
- Inventory source: `whooshd:/api/tags`
- Advertised models:
  - `qwen2.5-0.5b-gguf`
  - `llama-3.2-3b-mlx`
  - `qwen2-vl-2b-mlx`
- Provider truth:
  - `configured=true`
  - `authorized=true`
  - `discovered_inventory=true`
  - `discoverable=true`
  - `selectable=false`
  - `executable=false`
  - `cloud_capable_configuration_present=false`
  - `attempted=false`
  - `executed=false`
  - `completed=false`

### `/health/chat`

- Status: `unhealthy`
- Redis: `ok`
- Worker heartbeat: `fresh`
- Queue depth: `0`
- Provider: `local`
- Configured model available: `false`
- Availability reason: `configured_model_not_advertised_by_whooshd`
- Notes included the configured-model mismatch.

### `/api/llm/catalog`

The local provider remained visible but disabled for the selected model:

- Provider id: `local`
- Provider available: `true`
- Provider enabled: `false`
- Source vendor: `whooshd`
- Source base URL: `http://host.docker.internal:8000/v1`
- Default/configured model: `mlx-community/gemma-4-e2b-it-4bit`
- Configured model available: `false`
- Availability reason: `configured_model_not_advertised_by_whooshd`
- Inventory source: `whooshd:/api/tags`
- Disabled reason: configured Gemma E2B is not advertised by the reachable
  local runtime.

Live advertised models remained visible in catalog:

```txt
qwen2.5-0.5b-gguf
llama-3.2-3b-mlx
qwen2-vl-2b-mlx
```

Gemma E2B was not listed as a live catalog model.

### `/api/llm/catalog?include=all`

The local provider reported the same mismatch fields as `/api/llm/catalog`.
Cloud providers were present only as unavailable/non-selectable entries:

- `truth.configured=false`
- `truth.authorized=false`
- `truth.egress_allowed=false`
- `truth.cloud_capable_configuration_present=false`
- disabled by missing credentials or unavailable live inventory

No cloud provider was selected as fallback.

## Before And After Behavior

Catalog behavior before Phase 36A risk:

- A configured default could be confused with live model availability.
- Catalog truth could become misleading if the configured Whoosh'd model was
  absent from inventory.

Catalog behavior proven after Phase 36A:

- Live Whoosh'd inventory remains visible.
- Configured Gemma E2B is marked unavailable.
- `configured_model_not_advertised_by_whooshd` is emitted.
- Gemma E2B is not claimed as live.
- The local provider is not fully enabled for the selected model.

Health behavior before Phase 36A risk:

- A reachable runtime or green endpoint could be overread as selected-model
  readiness.

Health behavior proven after Phase 36A:

- `/health/llm` is `down` with details status `misconfigured`.
- `/health/chat` is `unhealthy` even though Redis, queue, and worker heartbeat
  are healthy.
- Health carries the same configured-model mismatch evidence as catalog.

## Status Table

| Area | Status | Evidence |
| --- | --- | --- |
| Repo boundary | Codexify / correct repo | `git rev-parse --show-toplevel` returned `/Users/resonant_jones/Keep/Resonant_Constructs/projectCodexify/Codexify`. |
| Whoosh'd inventory fetch | pass | Host and backend container reached `/v1/models` and `/api/tags`. |
| Configured model availability | pass | Gemma E2B reported `configured_model_available=false`. |
| Live inventory still visible | pass | Catalog listed `qwen2.5-0.5b-gguf`, `llama-3.2-3b-mlx`, and `qwen2-vl-2b-mlx`. |
| Gemma live claim avoided | pass | Gemma E2B was configured but absent from live catalog models. |
| Health mismatch surfaced | pass | `/health/llm` returned `status=down`, details `status=misconfigured`, and the mismatch reason. |
| Catalog mismatch surfaced | pass | `/api/llm/catalog` emitted `configured_model_not_advertised_by_whooshd`. |
| Supported profile alignment | pass | `/health` reported `v1-local-core-web-mcp`, `valid=true`, and no mismatches. |
| No cloud fallback | verified | `LLM_PROVIDER=local`, `ALLOW_CLOUD_PROVIDERS=false`, empty egress allowlist, `cloud_capable_configuration_present=false`, and no cloud provider selected. |
| Tests | pass | 42 Phase 36A tests passed; 9 related Whoosh'd tests passed; docs validation passed. |
| Docs | updated | Added this proof artifact only. |
| Commit | pending | Proof artifact to be committed after validation. |

## Invariants Preserved

- Whoosh'd internals were not imported into Codexify.
- Whoosh'd was not merged or Dockerized inside Codexify.
- Ollama fallback was not removed.
- Local-only posture remained strict for the proof stack.
- Missing Gemma E2B did not trigger cloud fallback.
- Live Whoosh'd models were not hidden because the configured default was
  missing.
- Provider health did not report selected-model readiness.
- Supported-profile validation remained aligned.
- No frontend UI was changed.
- No secrets, prompt bodies, image payloads, or base64 data were logged in this
  proof artifact.

## Validation

Artifact checks:

```bash
test -f docs/local-provider-whooshd-live-mismatch-proof-2026-06-15.md
grep -q configured_model_not_advertised_by_whooshd docs/local-provider-whooshd-live-mismatch-proof-2026-06-15.md
grep -q Gemma docs/local-provider-whooshd-live-mismatch-proof-2026-06-15.md
grep -q "No cloud fallback" docs/local-provider-whooshd-live-mismatch-proof-2026-06-15.md
```

Result: pass.

Targeted Phase 36A tests:

```bash
.venv/bin/python -m pytest -v \
  tests/core/test_provider_catalog_whooshd_inventory.py \
  tests/routes/test_llm_catalog_whooshd_inventory.py \
  tests/core/test_supported_profile_provider.py \
  tests/core/test_local_runtime_presets.py \
  tests/test_whooshd_smoke_env_contract.py
```

Result: `42 passed, 1 warning in 0.95s`.

Related Whoosh'd tests:

```bash
.venv/bin/python -m pytest -v \
  tests/test_whooshd_vision_model_source.py \
  tests/config/test_whooshd_model_profiles.py
```

Result: `9 passed, 1 warning in 0.07s`.

Diff hygiene:

```bash
git diff --check -- docs/local-provider-whooshd-live-mismatch-proof-2026-06-15.md
```

Result: pass.

Docs validation:

```bash
python3 scripts/validate_docs.py
```

Result: `Docs validation passed: required architecture docs, README links, and
source headings verified.`

## Known Limitations

- `scripts/whooshd_docker_smoke_up.sh` is stale for Phase 36A/36B because it
  still asserts `LOCAL_CHAT_MODEL=llama-3.2-3b-mlx`. The direct compose smoke
  override correctly configures Gemma E2B, but the wrapper exits before live
  proof.
- The legacy `AI_BACKEND` startup schema still rejects `local`. This proof used
  a temporary env-file override with `AI_BACKEND=ollama` so the running backend
  could initialize while preserving `LLM_PROVIDER=local`.
- This proof verifies inventory/catalog/health truth. It does not prove Gemma
  E2B execution, because Whoosh'd did not advertise Gemma E2B.

## Recommended Next Phase

Update the smoke wrapper and legacy startup compatibility so the supported
Whoosh'd smoke path can start directly with the Gemma E2B default without a
temporary `AI_BACKEND` workaround.
