# C00 Proof Pack

## Campaign

- **Campaign ID**: C00
- **Title**: Truth Gate and Worktree Classification

## Proof Pass

- **Date/Time**: 2026-06-16 16:33 UTC
- **Branch**: `codex/campaignOS`
- **Latest Commit**: `99017e3` — docs: create Guardian Maturity planning scaffold
- **Local Runtime Assumption**: Backend on `http://localhost:8888` (per `docker compose ps`). Whoosh'd on `http://localhost:8000` (per `.env` `LOCAL_BASE_URL` and `docker-compose.yml` default).

## Evidence Collected

### C00-TASK-001: Worktree Classification

**Command**: `git status --short --branch --untracked-files=all`

**Result**: Clean working tree. On branch `codex/campaignOS`. No modified tracked files. 19 untracked files in `docs/Campaign/guardian-maturity/` (the planning scaffold, now committed). Branch is `codex/campaignOS`, not `main` as implied by `00-current-state.md`.

**Classification**: **Branch drift detected.** Worktree is clean but on a feature branch (`codex/campaignOS`) rather than `main`. This is a planning branch, not a release branch. For Guardian Maturity work, this is acceptable — the scaffold was committed here — but the branch identity must be recorded for downstream campaigns.

### C00-TASK-002: Health Endpoints

**Command**: `curl -sS -m 5 http://localhost:8888/health`

| Endpoint | HTTP Status | Status Field | Key Details |
|----------|-------------|--------------|-------------|
| `/health` | 200 | `ok` | Supported profile `v1-local-core-web-mcp` valid. Local provider selected. Release hold false. |
| `/health/chat` | 200 | `unhealthy` | Redis OK. Worker heartbeat fresh (3.5s). Queue depth 0. Infrastructure is healthy. Unhealthy due to model mismatch: configured model `mlx-community/gemma-4-e2b-it-4bit` not advertised by Whoosh'd. |
| `/health/llm` | 200 | `down` | Same root cause: model mismatch. `provider_truth.executable: false`. `provider_truth.selectable: false`. |

**Note**: The `/health/chat` "unhealthy" label is a model-configuration issue, not an infrastructure failure. Redis, worker heartbeat, and queue are all healthy. The backend correctly distinguishes infrastructure health from model availability.

### C00-TASK-003: Provider Catalog

**Command**: `curl -sS -m 5 'http://localhost:8888/api/llm/catalog'` and `?include=all`

| Endpoint | Result |
|----------|--------|
| `/api/llm/catalog` | Returns only local provider. 1 model advertised: `mlx-community/Llama-3.2-3B-Instruct-4bit`. Provider `enabled: false`, `selectable: false`, `executable: false`. |
| `/api/llm/catalog?include=all` | Returns all 7 providers. All cloud providers (openai, anthropic, gemini, groq, alibaba, minimax) disabled with "Missing provider credentials". Local provider shows model mismatch. |

**Catalog truth fields per provider (local)**:
- `configured`: true
- `authorized`: true
- `discovered_inventory`: true
- `discoverable`: true
- `selectable`: false
- `executable`: false
- `egress_allowed`: true
- `supported_profile_approved`: true
- `configured_model_available`: false
- `disabled_reason`: "Configured local chat model 'mlx-community/gemma-4-e2b-it-4bit' from LOCAL_CHAT_MODEL is not advertised by the reachable local runtime"

### C00-TASK-004: Whoosh'd Model Inventory

**Commands**:
- `curl -sS -m 5 http://localhost:8000/v1/models`
- `curl -sS -m 5 http://localhost:8000/api/tags`
- `curl -sS -m 5 http://localhost:8001/v1/models` (not reachable)
- `curl -sS -m 5 http://localhost:8080/v1/models` (not reachable)
- `curl -sS -m 5 http://localhost:11434/api/tags` (not reachable)

| Endpoint | Reachable | Models Returned |
|----------|-----------|-----------------|
| `localhost:8000/v1/models` | Yes | `mlx-community/Llama-3.2-3B-Instruct-4bit` (1 model) |
| `localhost:8000/api/tags` | Yes | `mlx-community/Llama-3.2-3B-Instruct-4bit` (1 model) |
| `localhost:8001/v1/models` | No | Connection refused |
| `localhost:8080/v1/models` | No | Connection refused |
| `localhost:11434/api/tags` | No | Connection refused |

**Whoosh'd status**: Running and reachable on port 8000. Serves exactly one model: `mlx-community/Llama-3.2-3B-Instruct-4bit`. The configured model `mlx-community/gemma-4-e2b-it-4bit` is not loaded.

### C00-TASK-005: Gate Decision Synthesis

Synthesized below.

## Results

| Proof Category | Status | Notes |
|----------------|--------|-------|
| Docs proof | **pass** | `00-current-state.md` is internally consistent but its "Gemma E2B smoke default" claim does not match the live Whoosh'd inventory (only Llama 3.2 3B is loaded). This is a model-configuration drift, not a docs inconsistency. |
| Backend seam proof | **pass** | All health and catalog endpoints are reachable and return structured, detailed JSON responses. The backend correctly reports the model mismatch across all surfaces. |
| Frontend UI proof | N/A | Not applicable for C00 (read-only backend audit). |
| Live supported-path proof | **pass — with gap** | Whoosh'd is reachable and returns model inventory. The infrastructure (Redis, workers, Postgres, Whoosh'd) is healthy. The gap: configured model is not loaded. |
| Operator usability proof | N/A | Not applicable for C00 (truth baseline, not operator-facing). |

## Key Findings

### Contradictions

1. **Branch drift**: `00-current-state.md` describes the supported path on `main`. Current worktree is on `codex/campaignOS`. This is a planning branch, not a release branch. No modified files, but branch identity must be tracked.

2. **Model mismatch**: `.env` configures `LOCAL_CHAT_MODEL=mlx-community/gemma-4-e2b-it-4bit`. Whoosh'd only serves `mlx-community/Llama-3.2-3B-Instruct-4bit`. The backend correctly reports this as `configured_model_not_advertised_by_whooshd`.

3. **`00-current-state.md` smoke default claim**: The doc says "Whoosh'd smoke configs now default to the Gemma E2B local model alias." The live runtime has only Llama 3.2 3B loaded. This is not a contradiction in the doc — it's a live-configuration drift. The doc correctly warns "Do not assume the Gemma E2B smoke default is itself live-model proof."

### Gaps

1. **Chat completion not proven on this branch**: With the model mismatch, chat completion using the configured model would fail. The infrastructure is healthy but the model is not available. This gap must be resolved before C01/C02 can verify chat runtime states end-to-end.

2. **Branch is not `main`**: The supported path is documented on `main`. Work on `codex/campaignOS` must be merged or rebased before release-adjacent proof claims can reference `main`.

### Agreements (Surfaces Consistent)

All five surfaces (`/health`, `/health/chat`, `/health/llm`, `/api/llm/catalog`, Whoosh'd `/v1/models`) agree:
- Whoosh'd is reachable on port 8000
- Exactly one model is loaded: `mlx-community/Llama-3.2-3B-Instruct-4bit`
- The configured model `mlx-community/gemma-4-e2b-it-4bit` is not available
- The supported profile (`v1-local-core-web-mcp`) is valid
- All cloud providers are disabled
- Release hold is false

## Known Gaps

1. **Model mismatch**: `LOCAL_CHAT_MODEL=mlx-community/gemma-4-e2b-it-4bit` but Whoosh'd only has `mlx-community/Llama-3.2-3B-Instruct-4bit`. Resolution: either load the Gemma E2B model in Whoosh'd, update `LOCAL_CHAT_MODEL` to match the available model, or accept that chat completion on this branch will use the available model via runtime fallback. This gap blocks C01/C02 end-to-end chat proof.

2. **Branch drift**: Work is on `codex/campaignOS`, not `main`. This is acceptable for planning work but must be noted when downstream campaigns make release-adjacent claims. Resolution: merge to `main` when campaigns approach release-boundary verification.

## Gate Decision

- **Decision**: `next-proof-needed`
- **Reason**: All proof surfaces are reachable and return structured data that agree with each other. The infrastructure (Whoosh'd, Redis, workers, Postgres) is healthy. However, the configured chat model is not loaded in Whoosh'd, preventing end-to-end chat completion proof. This is a specific, documented gap that must be resolved before downstream campaigns (C01, C02) can verify chat runtime states. The gate is not `hold` because the runtime truth does not contradict the release posture (local-only is preserved, supported profile is valid). The gate is not `go` because surfaces cannot yet prove a working chat completion path.

## Follow-Up Required

- [ ] Resolve model mismatch: load `gemma-4-e2b-it-4bit` in Whoosh'd, or update `LOCAL_CHAT_MODEL` to `mlx-community/Llama-3.2-3B-Instruct-4bit`
- [ ] Re-run C00 proof pass after model resolution
- [ ] Confirm chat completion works end-to-end before C01/C02 proof collection
- [ ] Track branch identity in C01/C02 proof packs
- [ ] Validate against `00-current-state.md` on `main` before making release-adjacent claims
