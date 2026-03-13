
🧠 Codexify Campaign Prompt

Campaign: Inference Provider State Ledger

⸻

Objective

Design and implement a dedicated Inference Provider State table to track operational status, configuration integrity, and runtime diagnostics of all inference providers (OpenAI, Groq, local LLMs, etc.).

The system must:
	•	Eliminate implicit provider assumptions
	•	Replace environment-only configuration trust
	•	Provide structured health introspection
	•	Enable orchestration routing decisions
	•	Support future multi-provider failover
	•	Support diagnostics and telemetry correlation

⸻

Why This Exists

Currently:
	•	Provider state is inferred from env vars.
	•	Health failures occur at call-time.
	•	No persistent state record exists.
	•	UI cannot reliably display provider readiness.
	•	Orchestrator cannot reason about degraded providers.

This creates hidden instability.

We want:

Deterministic provider awareness across runtime and persistence layers.

⸻

Scope

Phase 1 — Schema + Persistence

Create a dedicated Postgres table:

inference_providers

Suggested fields:

id UUID PRIMARY KEY
name TEXT NOT NULL
provider_type TEXT NOT NULL
base_url TEXT
model_default TEXT
api_key_present BOOLEAN DEFAULT FALSE
status TEXT CHECK (status IN ('healthy','degraded','unavailable','unknown')) DEFAULT 'unknown'
last_health_check TIMESTAMP
avg_latency_ms FLOAT
error_rate FLOAT
capabilities JSONB
created_at TIMESTAMP
updated_at TIMESTAMP

Key design principles:
	•	Status is explicit.
	•	Health is measurable.
	•	Capabilities are structured (chat, embeddings, image, audio).
	•	No secrets stored (never store raw API keys).

⸻

Phase 2 — Health Probing

Implement background health checks:
	•	/health/provider/{id}
	•	Periodic scheduler (configurable interval)
	•	Timeout + retry logic
	•	Update status, last_health_check, avg_latency_ms

Failure states:
	•	401 → degraded (misconfigured)
	•	429 → degraded (rate limited)
	•	Timeout → unavailable
	•	5xx → degraded/unavailable based on threshold

⸻

Phase 3 — Orchestrator Integration

Modify inference routing logic:

Instead of:

if ENV_PROVIDER == 'openai':

Use:

SELECT * FROM inference_providers
WHERE status = 'healthy'
ORDER BY priority

Add:
	•	Failover ordering
	•	Provider preference ranking
	•	Optional cost-aware routing

⸻

Phase 4 — Telemetry Correlation

Extend inference execution logging:

Add foreign key:

provider_id

Log:
	•	latency
	•	token usage
	•	cost estimate
	•	failure reason
	•	model used

This enables:
	•	Provider performance dashboards
	•	Cost heatmaps
	•	Reliability scoring

⸻

Phase 5 — UI Exposure

Add Provider Diagnostics panel:

Show:
	•	Health state badge
	•	Latency average
	•	Last check timestamp
	•	Supported capabilities
	•	Current default model

This is NOT marketing UI.

It is operational truth UI.

⸻

Non-Goals
	•	No provider-specific business logic in DB
	•	No API key storage
	•	No secrets in logs
	•	No runtime-only in-memory state

⸻

Acceptance Criteria
	•	Providers persist across restarts
	•	Health changes update DB
	•	Orchestrator respects provider status
	•	Failover works when primary provider is degraded
	•	UI reflects real provider state
	•	Tests simulate provider failure and recovery

⸻

Deliverables
	•	Migration file
	•	Provider model ORM
	•	Health probe service
	•	Orchestrator routing update
	•	Telemetry extension
	•	Unit + integration tests
	•	Documentation update (`docs/reference/infrastructure/system_architecture.md` + `docs/reference/development/DB_POSTGRES_ONLY.md`)

⸻

Risk Considerations
	•	Do not introduce blocking health checks in request path
	•	Avoid thundering herd on provider recovery
	•	Ensure health scheduler is isolated from main loop
	•	Handle cold-start gracefully

⸻

Stretch Goals (Optional)
	•	Weighted routing
	•	Cost-aware selection
	•	Adaptive model downgrade on failure
	•	Provider trust scoring
	•	SLA tracking

⸻

Campaign Classification

This is a:

Infrastructure Stability Campaign

Estimated effort:
	•	Medium to High complexity
	•	Cross-layer refactor
	•	Worth doing before public release



# 🧠 Codexify Campaign

## CAMPAIGN_2026_02_17_INFERENCE_PROVIDER_STATE_LEDGER

### Summary
Codify inference provider *control-plane state* in Postgres so routing/failover and diagnostics are deterministic and observable across restarts.

This campaign introduces:
- A persistent provider config ledger (enabled/priority/default model/capabilities snapshot)
- A lightweight runtime health table (status, failure streak, cooldown, latency)
- Health probing + backoff that does **not** block request paths
- Router integration that respects provider state
- Telemetry correlation via provider_id
- (Optional) a minimal UI diagnostics view

### Providers in scope (launch set)
- `openai`
- `anthropic`
- `gemini`
- `groq`
- `local`

### Non-goals
- Storing raw API keys/secrets in DB
- Logging user prompts/content as telemetry
- Making health checks block normal chat completions

---

# ✅ Campaign Tasks (Codexify Task Prompts)

> Conventions:
> - Each task produces **one implementation commit**.
> - After the implementation commit, create a **task receipt file** at:
>   - `docs/Tasks/TASK-2026-02-17-XXX.md` (matching the task number)
>   - The receipt must include: summary, files changed, migrations (if any), endpoints added/changed, tests run + results, and the implementation commit hash.
> - Commit the receipt as a **docs-only commit** immediately after the implementation commit (so the repo returns to a clean tree).
> - Keep DB changes minimal and reversible.
> - Prefer additive migrations.

---

## TASK 001 — Add Provider State Schema (Config + Runtime)

### Objective
Create Postgres tables to represent provider configuration and runtime health state.

### Requirements
Create tables:

1) `inference_providers`
- `provider_id` (TEXT, PK) — stable ids: `openai|anthropic|gemini|groq|local`
- `display_name` (TEXT)
- `provider_type` (TEXT) — same as provider_id for now, reserved for future `custom`
- `enabled` (BOOLEAN)
- `priority` (INT) — lower is higher priority
- `default_model_id` (TEXT, nullable)
- `capabilities` (JSONB) — snapshot/declared provider-level caps (tools/vision/streaming/etc.)
- `metadata` (JSONB) — optional (base_url, notes, etc.)
- `created_at`, `updated_at`

2) `inference_provider_runtime`
- `provider_id` (TEXT, PK, FK → inference_providers.provider_id)
- `health_status` (TEXT) — `unknown|healthy|degraded|unavailable`
- `consecutive_failures` (INT)
- `last_success_at` (TIMESTAMP, nullable)
- `last_failure_at` (TIMESTAMP, nullable)
- `cooldown_until` (TIMESTAMP, nullable)
- `avg_latency_ms` (FLOAT, nullable)
- `error_rate` (FLOAT, nullable)
- `updated_at`

### Acceptance Criteria
- Alembic migration added and applies cleanly.
- Tables exist with correct constraints and indexes (index `enabled`, `priority`, `health_status`).
- No secrets stored.

### Implementation Notes
- If you already have a telemetry/events table, do **not** reuse it for control-plane state.

---

### Task Receipt Template
Create `docs/Tasks/TASK-2026-02-17-001.md` containing:
- **Task:** TASK-2026-02-17-001 — Add Provider State Schema (Config + Runtime)
- **Implementation Commit:** <hash>
- **Summary:** <2–6 bullets>
- **Files Changed:** <list>
- **DB/Migrations:** <details or none>
- **API/Endpoints:** <details or none>
- **Behavior Changes:** <details>
- **Tests:** <command(s) + pass/fail>
- **Notes/Risks:** <optional>

## TASK 002 — Seed/Sync Provider Rows from `/api/llm/catalog`

### Objective
Ensure the DB ledger is populated for the standard providers and stays coherent with the existing catalog.

### Requirements
- On startup (or via an idempotent admin function), ensure rows exist in `inference_providers` and `inference_provider_runtime` for each known provider id.
- Default values:
  - `enabled`: true for providers that are authorized/available under current config; false otherwise.
  - `priority`: set sensible defaults (e.g., `groq` high priority for interactive; but keep it simple: a static default ordering).
  - `health_status`: `unknown` initially.
- Do **not** block startup if a provider is misconfigured; reflect it in runtime state.

### Acceptance Criteria
- Fresh DB boot results in the 5 provider rows existing.
- Re-running sync does not duplicate rows.
- Tests validate sync idempotency.

---

### Task Receipt Template
Create `docs/Tasks/TASK-2026-02-17-002.md` containing:
- **Task:** TASK-2026-02-17-002 — Seed/Sync Provider Rows from `/api/llm/catalog`
- **Implementation Commit:** <hash>
- **Summary:** <2–6 bullets>
- **Files Changed:** <list>
- **DB/Migrations:** <details or none>
- **API/Endpoints:** <details or none>
- **Behavior Changes:** <details>
- **Tests:** <command(s) + pass/fail>
- **Notes/Risks:** <optional>

## TASK 003 — Provider Health Probing Service + Endpoint

### Objective
Introduce health checks that update `inference_provider_runtime` without impacting request latency.

### Requirements
- Add an internal endpoint (auth-protected or internal-only):
  - `GET /api/providers/health` (all) and/or `GET /api/providers/health/{provider_id}`
- Implement a probe runner that:
  - Executes a cheap provider call (or model list call) with strict timeout
  - Classifies outcomes:
    - `401/403` → `degraded` (misconfigured auth)
    - `429` → `degraded` (rate limited)
    - timeout → `unavailable`
    - 5xx → `degraded` or `unavailable` based on failure streak
    - success → `healthy` and resets failure streak
  - Updates: `health_status`, `consecutive_failures`, timestamps, and a rolling `avg_latency_ms`
- Add cooldown/backoff:
  - If `consecutive_failures` exceeds threshold, set `cooldown_until` (e.g., exponential with cap)
  - Router must not select providers in cooldown

### Acceptance Criteria
- Probes can be triggered manually via endpoint.
- Probes update DB state.
- Unit tests for classification logic and cooldown behavior.

---

### Task Receipt Template
Create `docs/Tasks/TASK-2026-02-17-003.md` containing:
- **Task:** TASK-2026-02-17-003 — Provider Health Probing Service + Endpoint
- **Implementation Commit:** <hash>
- **Summary:** <2–6 bullets>
- **Files Changed:** <list>
- **DB/Migrations:** <details or none>
- **API/Endpoints:** <details or none>
- **Behavior Changes:** <details>
- **Tests:** <command(s) + pass/fail>
- **Notes/Risks:** <optional>

## TASK 004 — Router Integration: Respect Provider Runtime State

### Objective
Make routing decisions consult provider state tables.

### Requirements
- Update routing selection logic to:
  1) Filter to `enabled = true`
  2) Filter to `health_status != unavailable`
  3) Exclude `cooldown_until > now()`
  4) Apply priority ordering
  5) Choose default model per provider if no model selected
- Preserve existing behavior:
  - If user selected a specific model, resolve provider from model and attempt it first.
  - If selected model is unavailable, fallback to first healthy enabled provider/model.
- Log a structured “fallback_reason” when fallback occurs:
  - `model_unavailable`, `provider_unhealthy`, `provider_cooldown`, `rate_limited`, `auth_error`, `timeout`, `unknown`

### Acceptance Criteria
- Router never selects providers in cooldown.
- Router falls back deterministically.
- Tests cover provider unhealthy + cooldown + disabled scenarios.

---

### Task Receipt Template
Create `docs/Tasks/TASK-2026-02-17-004.md` containing:
- **Task:** TASK-2026-02-17-004 — Router Integration: Respect Provider Runtime State
- **Implementation Commit:** <hash>
- **Summary:** <2–6 bullets>
- **Files Changed:** <list>
- **DB/Migrations:** <details or none>
- **API/Endpoints:** <details or none>
- **Behavior Changes:** <details>
- **Tests:** <command(s) + pass/fail>
- **Notes/Risks:** <optional>

## TASK 005 — Telemetry Correlation: Attach `provider_id` to Inference Logs

### Objective
Allow cost/latency/error analysis by provider without storing content.

### Requirements
- Extend existing inference request logging (or create minimal table if none exists) to include:
  - `provider_id`, `model_id`
  - `latency_ms`
  - `input_tokens`, `output_tokens`
  - `estimated_cost_usd` (nullable if unknown)
  - `success`, `error_type`
  - `fallback_used` + `fallback_reason`
- Do **not** log prompts/completions by default.

### Acceptance Criteria
- Each completion records provider/model and outcome.
- Health probe metrics remain separate from request logs.
- Tests validate provider_id is present.

---

### Task Receipt Template
Create `docs/Tasks/TASK-2026-02-17-005.md` containing:
- **Task:** TASK-2026-02-17-005 — Telemetry Correlation: Attach `provider_id` to Inference Logs
- **Implementation Commit:** <hash>
- **Summary:** <2–6 bullets>
- **Files Changed:** <list>
- **DB/Migrations:** <details or none>
- **API/Endpoints:** <details or none>
- **Behavior Changes:** <details>
- **Tests:** <command(s) + pass/fail>
- **Notes/Risks:** <optional>

## TASK 006 — Minimal Provider Diagnostics UI (Optional for Launch)

### Objective
Expose operational truth to the user/admin without cluttering the main UX.

### Requirements
- Add a “Provider Diagnostics” view/panel (behind an advanced toggle).
- Display per provider:
  - enabled
  - health_status
  - last_success_at / last_failure_at
  - avg_latency_ms
  - cooldown_until (if set)
  - default model
- No secrets displayed.

### Acceptance Criteria
- UI renders from API-backed provider state.
- No impact to main chat UX.

---

### Task Receipt Template
Create `docs/Tasks/TASK-2026-02-17-006.md` containing:
- **Task:** TASK-2026-02-17-006 — Minimal Provider Diagnostics UI (Optional for Launch)
- **Implementation Commit:** <hash>
- **Summary:** <2–6 bullets>
- **Files Changed:** <list>
- **DB/Migrations:** <details or none>
- **API/Endpoints:** <details or none>
- **Behavior Changes:** <details>
- **Tests:** <command(s) + pass/fail>
- **Notes/Risks:** <optional>

## TASK 007 — Documentation + Hardening + Regression Tests

### Objective
Lock the behavior down so it stays correct as providers evolve.

### Requirements
- Add/extend docs:
  - `docs/reference/infrastructure/system_architecture.md` (control-plane vs data-plane)
  - `docs/DB_POSTGRES_ONLY.md` (new tables + migration notes)
  - `docs/SECURITY.md` or equivalent (no content telemetry by default)
- Add regression tests:
  - Provider sync idempotency
  - Health classification matrix
  - Router respects cooldown + disabled
  - Fallback_reason correctness

### Acceptance Criteria
- CI green.
- Clear operational story: “why provider X was skipped” is visible in logs.

---

### Task Receipt Template
Create `docs/Tasks/TASK-2026-02-17-007.md` containing:
- **Task:** TASK-2026-02-17-007 — Documentation + Hardening + Regression Tests
- **Implementation Commit:** <hash>
- **Summary:** <2–6 bullets>
- **Files Changed:** <list>
- **DB/Migrations:** <details or none>
- **API/Endpoints:** <details or none>
- **Behavior Changes:** <details>
- **Tests:** <command(s) + pass/fail>
- **Notes/Risks:** <optional>

# Rollout Notes
- Start with Phase 1–4 for real reliability gains.
- UI diagnostics can ship after launch if necessary.
- Treat this as the foundation for future “Custom Provider” support.
