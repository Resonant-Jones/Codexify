# C00 Decision Log

## Decision Index

| ID | Date | Decision | Status |
|----|------|----------|--------|
| C00-D001 | 2026-06-16 | `next-proof-needed` — model mismatch blocks chat completion proof | superseded |
| C00-D002 | 2026-06-16 | `go` — model mismatch resolved, all surfaces agree | active |

---

### Decision: C00-D001

- **Decision ID**: C00-D001
- **Date**: 2026-06-16
- **Decision**: Gate decision is `next-proof-needed`. All proof surfaces are reachable and internally consistent, but the configured chat model (`mlx-community/gemma-4-e2b-it-4bit`) is not loaded in Whoosh'd, preventing end-to-end chat completion proof that C01 and C02 depend on.
- **Reason**:
  - All five proof surfaces return structured data and agree with each other.
  - Whoosh'd is reachable on port 8000 and serves exactly one model: `mlx-community/Llama-3.2-3B-Instruct-4bit`.
  - The configured model `mlx-community/gemma-4-e2b-it-4bit` is not in the Whoosh'd inventory.
  - The backend correctly reports this as `configured_model_not_advertised_by_whooshd` across `/health/chat`, `/health/llm`, and `/api/llm/catalog`.
  - Infrastructure (Redis, workers, Postgres, Whoosh'd) is healthy. The gap is a model configuration mismatch, not an infrastructure failure.
  - The supported profile (`v1-local-core-web-mcp`) is valid and release hold is false.
  - The release posture (local-only) is preserved and not contradicted.
- **Evidence**:
  - `git status` — clean worktree on `codex/campaignOS`
  - `/health` — `ok`, supported profile valid
  - `/health/chat` — `unhealthy` due to model mismatch; Redis, worker, queue all healthy
  - `/health/llm` — `down` due to model mismatch; provider truth confirms `executable: false`
  - `/api/llm/catalog` — 1 model advertised: `Llama-3.2-3B-Instruct-4bit`
  - `/api/llm/catalog?include=all` — all cloud providers disabled
  - Whoosh'd `/v1/models` — 1 model: `Llama-3.2-3B-Instruct-4bit`
  - Whoosh'd `/api/tags` — same inventory, confirms Whoosh'd as inventory source
  - Ports 8001, 8080, 11434 not reachable — expected, only Whoosh'd on 8000
- **Consequence**:
  - C00 cannot advance to `go` until the model mismatch is resolved.
  - C01 and C02 depend on C00 for chat runtime proof. They can begin health/catalog inspection but cannot verify chat completion end-to-end until the model is available.
  - C11 (API Route Audit) is not blocked — it audits route registration, not model availability.
  - The gap is documented and actionable: either load `gemma-4-e2b-it-4bit` in Whoosh'd, or update `LOCAL_CHAT_MODEL` to `mlx-community/Llama-3.2-3B-Instruct-4bit`.
- **Revisit Trigger**:
  - Model configuration changes (`.env` `LOCAL_CHAT_MODEL` updated or Whoosh'd model loaded).
  - Re-run C00 proof pass after model resolution.
  - If C01 or C02 proof collection begins and chat completion is needed, escalate to this decision.

---

### Decision: C00-D002

- **Decision ID**: C00-D002
- **Date**: 2026-06-16
- **Decision**: Gate decision is `go`. The configured model mismatch from C00-D001 is resolved. All required proof surfaces agree: health ok, chat health healthy with fresh worker, model inventory consistent, local-only posture preserved, Whoosh'd model confirmed generating.
- **Reason**:
  - Commit `85931f327` aligned the git-tracked `local_runtime_presets.py` and operator-local `.env` with `mlx-community/Llama-3.2-3B-Instruct-4bit`.
  - After `docker compose up -d` (restart alone insufficient — Docker Compose restart preserves original environment), all services healthy.
  - `/health` — `ok`, profile valid, release hold false, cloud disabled.
  - `/health/chat` — `healthy`, worker fresh (4.6s heartbeat), `configured_model_available=true`, `selectable=true`, `executable=true`.
  - `/health/llm` — `ok`.
  - `/api/llm/catalog` — local provider enabled, selectable, executable with Llama 3.2.
  - `/api/llm/catalog?include=all` — all 6 cloud providers disabled, local-only preserved.
  - Whoosh'd `/v1/models` and `/api/tags` — 1 model: `mlx-community/Llama-3.2-3B-Instruct-4bit`.
  - Direct Whoosh'd `/v1/chat/completions` confirmed model generates.
  - No contradictions across any surface.
- **Evidence**:
  - `git status` — clean worktree on `codex/campaignOS`
  - `docker compose ps` — 11 services running, all healthy
  - All 9 proof endpoints verified (see proof-pack.md re-proof section)
  - Model mismatch resolved: configured = live = `mlx-community/Llama-3.2-3B-Instruct-4bit`
- **Consequence**:
  - C00 advances to `go`. The truth gate is established.
  - C01 (Command Center verdict) is unblocked — its surfaces already agree.
  - C02 (Chat Runtime State) can proceed. It must own end-to-end authenticated Codexify backend chat completion proof.
  - C08 (Whoosh'd Runtime Setup) can reference confirmed model inventory.
  - Branch drift (`codex/campaignOS` vs `main`) remains a note for release-adjacent claims.
- **Revisit Trigger**:
  - Whoosh'd model inventory changes (model unloaded or replaced).
  - Backend config drift re-introduces model mismatch.
  - C02 chat completion proof fails despite C00 gate being `go`.
  - Merge to `main` — re-verify C00 on `main` before release claims.
