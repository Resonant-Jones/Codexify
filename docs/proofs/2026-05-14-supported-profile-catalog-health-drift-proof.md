# Supported-Profile / Catalog / Health Drift Proof

- Artifact date: 2026-05-14
- Branch: `main`
- HEAD at proof start: `fa994587195b8363ff2c00fbf5392b996fd09fcc`
- Runtime path: local Docker Compose on the supported beta stack
- Proof window: 2026-05-14 19:30 EDT to 2026-05-14 19:31 EDT
- Result: `FAIL`

## Purpose

Verify whether the remaining generic supported-profile / catalog / health drift hold can be retired on the current `main` tip.

The answer from live evidence is no: the local-only health and catalog surfaces are honest, but the supported-profile surface is not mutually aligned in the live backend runtime. The hold therefore remains active.

## Repo State

- Branch: `main`
- HEAD: `fa994587195b8363ff2c00fbf5392b996fd09fcc`
- Worktree: clean at proof start
- No unrelated in-flight changes were staged

## Exact Commands Run

### Repo state

- `git branch --show-current`
- `git rev-parse HEAD`
- `git status --short`
- `git log --oneline -5`

### Supported local Compose stack

- `docker compose up -d db redis neo4j`
- `docker compose run --rm migrator`
- `docker compose up -d backend frontend worker-chat worker-coding worker-document-embed worker-chat-embed worker-warmup`
- `docker compose ps`

### Supported-profile config inspection

- `sed -n '1,220p' config/supported_profiles/v1-local-core-web-mcp.yaml`

### Live health / catalog surfaces

- `BASE=http://localhost:8888`
- `KEY="$(bash scripts/dev/dev-key.sh)"`
- `curl -fsS -H "X-API-Key: $KEY" "$BASE/health"`
- `curl -fsS -H "X-API-Key: $KEY" "$BASE/health/chat"`
- `curl -fsS -H "X-API-Key: $KEY" "$BASE/api/health/llm"`
- `curl -fsS -H "X-API-Key: $KEY" "$BASE/api/llm/catalog"`
- `curl -fsS -H "X-API-Key: $KEY" "$BASE/api/llm/catalog?include=all"`

### Backend runtime inspection

- `docker compose exec -T backend sh -lc 'printf "CODEXIFY_SUPPORTED_PROFILE=%s\n" "${CODEXIFY_SUPPORTED_PROFILE:-}"; printf "CODEXIFY_SUPPORTED_PROFILE_DIR=%s\n" "${CODEXIFY_SUPPORTED_PROFILE_DIR:-}"; printf "LLM_PROVIDER=%s\n" "${LLM_PROVIDER:-}"; printf "ALLOW_CLOUD_PROVIDERS=%s\n" "${ALLOW_CLOUD_PROVIDERS:-}"; printf "CODEXIFY_LOCAL_ONLY_MODE=%s\n" "${CODEXIFY_LOCAL_ONLY_MODE:-}"'`
- `docker compose exec -T backend sh -lc 'python - <<\"PY\" ... PY'` to print `get_settings()`, `get_active_supported_profile()`, `supported_profile_posture(get_settings())`, and `provider_truth.cloud_capable_configuration_present(get_settings())`

### Validation

- `./.venv/bin/python scripts/validate_docs.py`
- `git diff --check`

## Supported-Profile Config Summary

`config/supported_profiles/v1-local-core-web-mcp.yaml` is a local-only beta manifest:

- `LLM_PROVIDER: local`
- `ALLOW_CLOUD_PROVIDERS: false`
- `CODEXIFY_LOCAL_ONLY_MODE: true`
- route posture enables supported public/runtime surfaces and quarantines internal-only or unsupported surfaces
- `command_bus` is internal-only
- cloud-provider beta support is not declared
- graph-write release expansion is not declared

This manifest is consistent with the local-first supported contract.

## Live Health Evidence

### `/health`

- `status: ok`
- `release_hold: false`
- `details.release_hold: false`
- No conflicting cloud-provider beta claim surfaced

### `/health/chat`

- `status: healthy`
- `redis: ok`
- `worker.status: fresh`
- `queue.depth: 0`
- `queue.status: progressing`
- `completion_service.ok: true`

### `/api/health/llm`

- `status: ok`
- `release_hold: false`
- `details.provider: local`
- `details.model: library2/ministral-3:8b`
- `details.supported_profile.name: null`
- `details.supported_profile.valid: null`
- `details.supported_profile.release_hold: null`
- `details.provider_truth.supported_profile_name: null`
- `details.provider_truth.supported_profile_approved: null`
- `details.provider_truth.cloud_capable_configuration_present: false`

### Backend runtime inspection

- `CODEXIFY_SUPPORTED_PROFILE` is unset in the backend container
- `guardian.core.supported_profile.get_active_supported_profile()` returned `None`
- `supported_profile_posture(get_settings())` returned:
  - `name: None`
  - `selected_provider: local`
  - `selected_provider_supported: None`
  - `cloud_capable_configuration_present: true`
  - `release_hold: None`
- `provider_truth.cloud_capable_configuration_present(get_settings())` returned `false`

The posture helper and the health truth helper are not using the same cloud-capability predicate:

- supported-profile posture treats the bundled non-empty `ALIBABA_API_BASE` default as cloud-capable
- provider truth only counts explicit cloud configuration as cloud-capable

That semantic mismatch is part of the active drift.

## Catalog Evidence

### `/api/llm/catalog`

- `provider_count: 1`
- only provider listed: `local`
- local provider was `authorized: true`, `available: true`, `enabled: true`
- no cloud provider was promoted as beta-supported

### `/api/llm/catalog?include=all`

- `provider_count: 7`
- cloud providers shown only as diagnostic inventory
- `openai`, `anthropic`, `gemini`, `groq`, `alibaba`, and `minimax` were all `authorized: false`, `available: false`, `enabled: false`
- local remained `authorized: true`, `available: true`, `enabled: true`

The catalog is honest about the local-only supported posture.

## Drift Comparison

| Surface | Observation | Alignment |
|---|---|---|
| Supported-profile manifest file | Local-only beta contract, `LLM_PROVIDER=local`, `ALLOW_CLOUD_PROVIDERS=false`, `CODEXIFY_LOCAL_ONLY_MODE=true` | Aligns with local-only promise |
| Live `/health` | `release_hold=false`, no cloud beta claim, queue/worker healthy | Aligns with local-only promise |
| Live `/health/chat` | Healthy queue/worker posture, no backlog | Aligns with local-only promise |
| Live `/api/health/llm` | `provider=local`, but supported-profile fields are null in the live backend and posture semantics diverge | Not fully aligned |
| Live `/api/llm/catalog` | Local provider only | Aligns with local-only promise |
| Live `/api/llm/catalog?include=all` | Cloud providers visible only as unauthorized/unavailable diagnostic inventory | Aligns with operator diagnosis, not beta support |

### Drift verdict

The generic hold must remain active because the live backend is not surfacing a fully aligned supported-profile state:

- `CODEXIFY_SUPPORTED_PROFILE` is unset in the backend runtime
- the live `/api/health/llm` supported-profile object is posture-only and contains null manifest fields
- supported-profile posture and health/provider-truth disagree on whether the runtime is cloud-capable

That is meaningful drift, even though the live catalog and health surfaces are otherwise honest about the local-only posture.

## No-Authority-Widening Evidence

No unsupported authority was widened during this proof:

- No Command Center dispatch endpoint was called
- No lease allocation from UI occurred
- No terminal execution from UI occurred
- No plugin runtime was activated
- No merge automation occurred
- No graph-write release claim was widened
- No cloud-provider beta support was claimed

## Validation Results

- Targeted health/provider tests were run earlier in this proof cycle and passed:
  - `guardian/tests/routes/test_health_supported_profile.py`
  - `guardian/tests/core/test_provider_registry.py`
  - `guardian/tests/core/test_llm_catalog.py`
  - `guardian/tests/test_health_endpoints.py`
- Documentation validation passed:
  - `./.venv/bin/python scripts/validate_docs.py`
- Diff hygiene passed:
  - `git diff --check`

## Final Result

`FAIL`

The current `main` tip does **not** justify retiring the generic supported-profile / catalog / health drift hold.

The hold remains active because the live backend runtime is not surfacing an aligned supported-profile state, even though the supported-profile file itself is local-only and the catalog/health surfaces are honest about the local-first posture.

## Explicit Non-Claims

- This proof does not claim cloud-provider beta support.
- This proof does not claim packaged desktop replaces the supported local Compose path.
- This proof does not claim command bus / delegation / federation / graph-write release expansion.
- This proof does not claim UI dispatch.
- This proof does not claim lease allocation from UI.
- This proof does not claim terminal execution from UI.
- This proof does not claim plugin runtime.
- This proof does not claim merge automation.
- This proof does not claim live MiniMax/Codex successful execution from Command Center.
- This proof does not retire the supported-profile/catalog/health drift hold.
