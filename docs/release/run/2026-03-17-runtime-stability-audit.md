# Codexify Runtime Stability Audit

## Purpose

Use this document as the weekly operational audit for Codexify runtime stabilization.
It is intended to measure runtime reliability on the supported path, capture concrete evidence, record recurring failure classes, and define the fixes required before the runtime can be scored higher.

## Audit Metadata

- Audit Window: `2026-03-11 to 2026-03-17`
- Environment: `local Docker Compose supported runtime`
- Branch / Commit Range: `main / 5b95a10ef..4e2c8c386`
- Owner: `Resonant Jones`
- Audit Version: `v1.0`

## Executive Summary

- Overall Stability Index: `41/60`
- Rating Band: `stabilizing`
- Summary: March 17 evidence shows a materially healthier runtime than the failed March 11 smoke. Deterministic core, retrieval, and supported-profile test slices all passed, and live backend health confirms Redis reachability, enqueue health, worker heartbeats, and an online local provider. The main blocker is now a supported-profile contract failure: the Beta-1 runbook requires core-only flags, but the live Compose runtime still boots with `CODEXIFY_BETA_CORE_ONLY=false`, cloud providers enabled, and non-core routes mounted because backend and worker services are pinned to `env_file: .env`.
- Top Regressions This Week:
  - `Supported-profile smoke is blocked by Compose env wiring drift`
  - `Beta-1 quarantine contract is broken on the live stack; /api/connectors and /api/tools/manifest both return 200`
  - `Health surfaces can read green while the supported-profile contract is still invalid`
- Primary Blockers:
  - `Backend and worker services hardcode env_file=.env, preventing profile-safe smoke overrides`
  - `Live upload -> embed -> retrieve was not re-proven on the current supported path because smoke aborts before the happy-path checks`
- Recommended Release Posture: `limited internal validation only`

## Weighted Stability Index

Score each category with an integer value from `0` up to its weight.
Do not increase a score without direct evidence from the current audit window.

| Category | Weight | Score | Notes |
| --- | ---: | ---: | --- |
| Core Loop Reliability | 15 | `11/15` | Deterministic core gate passed and live queue health is green, but March 17 did not re-prove a full supported-profile assistant turn under the runbook flags because smoke aborts on profile drift. |
| Retrieval / Context Integrity | 12 | `9/12` | Retrieval/context suites passed strongly, but live document retrieval on the supported path was not re-demonstrated after the smoke abort. |
| Queue / Worker Health | 12 | `10/12` | `/health/chat` reports Redis reachable, enqueue probe OK, and fresh worker heartbeats; worker logs show healthy startup. |
| Contract Stability | 12 | `5/12` | Test slices are green, but live runtime behavior still contradicts the Beta-1 runbook and quarantine contract. |
| Operator Confidence | 9 | `6/9` | Logs and health surfaces are useful, but diagnosing the profile failure required Compose config inspection and in-container probing. |
| **Total** | **60** | `41/60` | `Subsystems are stabilizing, but the supported-profile contract is not yet trustworthy enough for broader release claims.` |

### Rating Bands

- `0-19 = unstable`
- `20-29 = fragile`
- `30-39 = improving`
- `40-49 = stabilizing`
- `50-60 = beta-ready core`

### Suggested First Target Thresholds

- `40+ = stabilizing`
- `50+ = beta-ready core`

## Core Loop Reliability

### Goal

Confirm that the supported user-critical runtime loops complete end to end without stalls, silent drops, duplicate side effects, or manual intervention.

### Audit Questions

- Do the primary user flows start, progress, and complete on the supported path?
- Are turns, tasks, and persisted state transitions visible and internally consistent?
- Are retries idempotent, or do they create duplicate messages, tasks, or records?
- Does restart or transient failure leave the runtime in a recoverable state?

### Score

`11/15`

### Evidence

- `2026-03-17`: `bash scripts/verification/validate_beta1_core_gate.sh` -> `PASS: Beta-1 deterministic core gate`
- `2026-03-17`: `pytest -ra tests/queue/test_turn_lock.py tests/test_chat_worker_turn_integrity.py tests/integration/test_rag_integration_loop.py tests/memoryos/test_retriever.py tests/routes/test_chat_routes.py tests/routes/test_media_routes.py tests/routes/test_tools_manifest_phase21_format.py tests/core/test_supported_profile_startup.py` -> `104 passed, 3 xpassed, 10 warnings in 28.45s`
- `2026-03-17`: `docker compose --env-file .env ps` -> backend, db, redis, frontend, and required workers were up; backend was healthy
- `2026-03-17`: in-container `GET /health/chat` -> `completion_service.ok=true`, `redis_reachable=true`, `enqueue_test_ok=true`, `worker_heartbeat_detected=true`

### Failure Patterns Seen

- `supported-path smoke aborted before live assistant-turn proof`
- `quarantine profile not applied at runtime`
- `live route surface broader than the runbook promises`

### Current Assessment

The core loop is much healthier than it was on March 11. Deterministic queue, turn-lock, and RAG loop coverage is green, and live Redis plus worker heartbeat checks show the runtime can accept and process chat work. What remains unresolved is supported-path truth: this audit window did not capture a fully runbook-compliant live completion flow because the Compose runtime did not honor the required Beta-1 profile flags.

### Required Fixes Before Score Can Increase

- `Make the Compose-supported runtime honor the documented Beta-1 flags without manual .env editing`
- `Capture a fresh live thread -> assistant completion proof on the supported profile after the env wiring fix`

## Retrieval / Context Integrity

### Goal

Verify that retrieval, context assembly, and context delivery remain correct, bounded, and explainable under normal and degraded runtime conditions.

### Audit Questions

- Does retrieval return relevant, expected records for supported queries?
- Is the context window assembled from the correct sources in the correct order?
- Are empty, partial, or stale retrieval results surfaced clearly instead of failing silently?
- Do source references, metadata, and context payloads match what downstream consumers expect?

### Score

`9/12`

### Evidence

- `2026-03-17`: `pytest -ra tests/memoryos/test_retriever.py tests/core/test_context_broker_depth.py tests/integration/test_chat_completion_context.py tests/federation/test_context_retrieval.py` -> `132 passed, 5 warnings in 3.91s`
- `2026-03-17`: targeted runtime slice above includes `tests/integration/test_rag_integration_loop.py` passing
- `2026-03-11`: last failed live smoke recorded empty retrieval evidence for the supported path in `docs/release/run/2026-03-11-beta-smoke.md`

### Failure Patterns Seen

- `live retrieval happy path not re-proven after smoke aborted early`
- `historical signal exists for empty RAG trace documents on the supported path`

### Current Assessment

Retrieval and context integrity look strong under deterministic test coverage, including retriever behavior, context assembly, and queue-backed integration. The missing piece is live-stack closure in this audit window: because the March 17 smoke stopped at the profile check, there is no fresh live evidence yet that document upload, embedding, and retrieval complete end to end on the supported Compose path.

### Required Fixes Before Score Can Increase

- `Re-run the supported-profile smoke past the profile gate and archive a live upload -> embed -> retrieve result`
- `Attach RAG trace or equivalent runtime artifact to the weekly audit so retrieval success is not inferred from tests alone`

## Queue / Worker Health

### Goal

Confirm that queued runtime work is accepted, processed, observed, and recovered correctly without hidden backlog growth or silent worker failure.

### Audit Questions

- Are queue-backed jobs enqueued and acknowledged reliably?
- Are workers healthy, connected, and consuming the expected job classes?
- Is backlog growth visible and bounded during normal usage?
- Do retries, dead-letter paths, and failure signals behave as intended?

### Score

`10/12`

### Evidence

- `2026-03-17`: in-container `GET /health/chat` returned:
  - `completion_service.ok=true`
  - `redis_reachable=true`
  - `enqueue_test_ok=true`
  - `worker_heartbeat_detected=true`
  - `worker_heartbeat_age_seconds ~= 2-4`
- `2026-03-17`: `docker compose --env-file .env logs --tail=120 backend worker-chat worker-document-embed`
  - `worker-chat` logged `started queue=codexify:queue:chat concurrency=2`
  - `worker-document-embed` logged `worker started queue=codexify:queue:document-embed`
- `2026-03-17`: Beta deterministic core gate passed queue-sensitive selectors including `test_complete_turn_lock_error_returns_structured_503` and `test_health_chat_endpoint`

### Failure Patterns Seen

- `no live backlog or dead-letter evidence captured in this audit window`
- `queue health can appear green while supported-profile validation still fails`

### Current Assessment

Queue and worker health is the strongest live runtime signal in this audit. Redis is reachable, the enqueue probe succeeds, workers are alive, and startup logs show both chat and document embedding lanes coming online cleanly. The remaining deduction is for incomplete operational proof around backlog growth, dead-letter behavior, and restart/replay under the actual supported profile.

### Required Fixes Before Score Can Increase

- `Add queue depth, retry count, and dead-letter visibility to the weekly runtime evidence pack`
- `Exercise at least one supported-profile completion and one document-embed job after the profile wiring fix`

## Contract Stability

### Goal

Measure whether runtime-facing contracts remain stable across backend routes, frontend consumers, worker payloads, and persisted records.

### Audit Questions

- Are request and response shapes aligned across all supported runtime surfaces?
- Do worker payloads, event payloads, and persisted records use the same field names and meanings?
- Are versioned or deprecated fields handled explicitly instead of implicitly?
- Did this audit window expose any deterministic break caused by contract drift?

### Score

`5/12`

### Evidence

- `2026-03-17`: `pytest -ra tests/core/test_supported_profile.py tests/core/test_supported_profile_provider.py tests/core/test_supported_profile_startup.py tests/routes/test_tools_manifest_phase21_format.py tests/routes/test_tools_phase3_callable_contract.py tests/routes/test_tools_legacy_shims_phase15.py` -> `29 passed, 4 warnings in 22.14s`
- `2026-03-17`: `bash scripts/verification/smoke_beta1.sh` failed with `Backend CODEXIFY_BETA_CORE_ONLY is not enabled`
- `2026-03-17`: in-container backend env probe -> `beta=false local_only=false cloud=true egress=groq,openai,anthropic,gemini,minimax,alibaba`
- `2026-03-17`: in-container route probes:
  - `GET /api/connectors` -> `200`
  - `GET /api/tools/manifest` -> `200`
- `2026-03-17`: clean-environment `docker compose --env-file <temp-beta-env> config` still resolved `ALLOW_CLOUD_PROVIDERS=true`, `CODEXIFY_LOCAL_ONLY_MODE=false`, and `CODEXIFY_BETA_CORE_ONLY=false`
- Runbook expectation:
  - `docs/guardian/beta1_stabilization.md` requires `CODEXIFY_BETA_CORE_ONLY=true`, `CODEXIFY_LOCAL_ONLY_MODE=true`, `ALLOW_CLOUD_PROVIDERS=false`, and quarantined non-core routes
- Compose wiring:
  - `docker-compose.yml` hardcodes `env_file: .env` for backend and worker services, so a smoke-time `--env-file` override does not change the container runtime flags

### Failure Patterns Seen

- `runbook/runtime flag mismatch`
- `non-core routes mounted when runbook expects 404`
- `supported-profile smoke cannot safely switch runtime profile via alternate env file`

### Current Assessment

This is the biggest active weakness. Test coverage around supported-profile helpers and tool contracts is green, but the live runtime contract still disagrees with the runbook. The documented Beta-1 surface is supposed to be core-only and quarantined; the actual March 17 backend was full-surface, cloud-enabled, and not local-only. That is a deterministic contract break, not a speculative risk.

### Required Fixes Before Score Can Increase

- `Refactor Compose so backend and workers can consume a profile-specific env source instead of hardcoding .env`
- `Re-run smoke and verify quarantined routes return 404 under the supported profile`

## Operator Confidence

### Goal

Assess whether an operator can understand runtime state quickly enough to diagnose issues, confirm recovery, and make release decisions with evidence rather than guesswork.

### Audit Questions

- Are failures observable through logs, metrics, health checks, or explicit UI state?
- Can an operator distinguish between degraded, blocked, and healthy runtime behavior?
- Are the current runbooks and recovery steps sufficient for the recurring failures seen this week?
- Can the team explain why the system failed without speculative debugging?

### Score

`6/9`

### Evidence

- `2026-03-17`: smoke failed loudly and immediately on a clear profile mismatch instead of silently hanging
- `2026-03-17`: `/health/chat` and `/api/health/llm` provide actionable subsystem detail
- `2026-03-17`: backend and worker logs clearly show startup, queue binding, and provider health checks
- `2026-03-17`: diagnosis still required:
  - `docker compose config`
  - in-container env inspection
  - in-container HTTP probes because host-side localhost access was unreliable in this Codex environment

### Failure Patterns Seen

- `misleading healthy status`
- `operator needed ad hoc Compose and container inspection to diagnose the true blocker`
- `supported-profile runbook cannot be validated from smoke output alone`

### Current Assessment

Operator confidence is better than it was in the March 11 smoke because the system now emits strong health and queue signals and the smoke failure is explicit. Confidence is still capped because health endpoints alone do not reveal that the runtime is violating the supported-profile contract, and the operator must understand Docker Compose env resolution details to explain the failure accurately.

### Required Fixes Before Score Can Increase

- `Add a startup or smoke preflight that prints the effective supported-profile flags before route checks begin`
- `Document and automate in-container evidence capture when host networking is unreliable in the audit environment`

## Known Bugs by Class

### Structural Bugs

| Bug / Symptom | Surface | Severity | Evidence | Status |
| --- | --- | --- | --- | --- |
| `Compose backend and worker services pin env_file=.env, so smoke-time env overrides do not change the runtime profile` | `docker-compose` | `high` | `docker-compose.yml` backend/worker services plus March 17 overlay smoke still reading `beta=false` | `open` |
| `Active operator env inverts the Beta-1 runbook flags` | `runtime bootstrap` | `medium` | `.env` shows `ALLOW_CLOUD_PROVIDERS=true`, `CODEXIFY_LOCAL_ONLY_MODE=false`, `CODEXIFY_BETA_CORE_ONLY=false` while the runbook requires the opposite | `open` |

### Contract Bugs

| Bug / Symptom | Surface | Severity | Evidence | Status |
| --- | --- | --- | --- | --- |
| `GET /api/connectors returns 200 on the live stack when Beta-1 runbook expects quarantine` | `backend routes` | `high` | March 17 in-container probe returned `200` with `[]` | `open` |
| `GET /api/tools/manifest returns 200 on the live stack when Beta-1 runbook expects quarantine` | `tools/control surface` | `high` | March 17 in-container probe returned `200` with a manifest envelope | `open` |
| `Three chat-route tests still xpass, masking that current behavior has already changed` | `test contract` | `low` | March 17 targeted runtime suite -> `104 passed, 3 xpassed`; March 12 XPASS audit already classifies these markers as stale | `in progress` |

### Edge-Case Runtime Bugs

| Bug / Symptom | Surface | Severity | Evidence | Status |
| --- | --- | --- | --- | --- |
| `Host-side localhost probing is unreliable in this audit environment even when the backend is healthy in-container` | `operator environment` | `low` | March 17 host curl to `localhost:8888` failed while in-container health probes succeeded | `watching` |
| `Document-embed worker starts with an embeddings fallback warning under the local-first path` | `document-embed worker` | `low` | March 17 worker log: requested OpenAI embeddings path fell back to local embeddings | `watching` |

### UX / Observability Bugs

| Bug / Symptom | Surface | Severity | Evidence | Status |
| --- | --- | --- | --- | --- |
| `Health endpoints can be green while the supported-profile contract is still broken` | `health/readiness` | `medium` | March 17 `/health/chat` and `/api/health/llm` were green while non-core routes still returned 200 | `open` |
| `Smoke failure does not explain the underlying env_file wiring bug; operator must inspect Compose internals` | `runbook / diagnostics` | `medium` | March 17 smoke output named the missing flag but not why alternate env injection failed | `open` |

## Regression Watchlist

Track regressions that are either recurring, recently fixed, or likely to return under load, restart, or configuration drift.

| Regression Risk | Why It Matters | Detection Signal | Last Seen | Owner | Status |
| --- | --- | --- | --- | --- | --- |
| `Supported-profile env drift` | `Blocks truthful smoke validation and leaves unsupported routes mounted` | `smoke_beta1.sh` fails the `CODEXIFY_BETA_CORE_ONLY` check or `/api/connectors` returns `200` | `2026-03-17` | `Resonant Jones` | `reopened` |
| `Queue health and provider/runtime truth diverge` | `Operators may think chat is healthy when the actual completion path is degraded` | `GET /health/chat` green while `GET /api/health/llm` is red or stale | `2026-03-11` | `Resonant Jones` | `watching` |
| `Retrieval happy path regresses silently after upload succeeds` | `Upload and embed can look successful while chat retrieval remains empty` | `RAG trace shows empty documents after a ready embedding` | `2026-03-11` | `Resonant Jones` | `watching` |
| `Stale XPASS markers hide real contract movement` | `Test suite signal is weakened and can mask future route drift` | `pytest -rX tests/routes/test_chat_routes.py` reports the same 3 XPASS cases | `2026-03-17` | `Resonant Jones` | `watching` |

## Next Hardening Tasks

| Priority | Task | Why Now | Blocking Signal | Owner | Target Window | Status |
| --- | --- | --- | --- | --- | --- | --- |
| `P0` | `Make Compose backend and worker services consume a profile-selectable env source instead of hardcoded .env` | `This is the direct blocker preventing a truthful supported-profile smoke` | `March 17 smoke fails before route checks` | `Resonant Jones` | `2026-03-18 to 2026-03-24` | `planned` |
| `P0` | `Add a startup/smoke preflight that prints effective profile flags and fails before boot if the supported profile is not active` | `Shortens diagnosis time and prevents false confidence from green health checks` | `Operator needed Compose config + in-container probes` | `Resonant Jones` | `2026-03-18 to 2026-03-24` | `planned` |
| `P1` | `Re-run a full Compose evidence pack for thread create -> assistant turn -> upload -> embed -> retrieve after the env fix` | `The current audit still lacks fresh live retrieval closure on the supported path` | `No March 17 live happy-path proof beyond subsystem health` | `Resonant Jones` | `2026-03-18 to 2026-03-24` | `planned` |
| `P2` | `Normalize or narrow the 3 stale chat-route xfail markers` | `Improves contract-signal quality without changing runtime behavior` | `104 passed, 3 xpassed in the targeted runtime suite` | `Resonant Jones` | `2026-03-18 to 2026-03-31` | `planned` |

## Release Readiness Read

- Current Read: `internal only`
- Release-Critical Blockers:
  - `Supported-profile Compose wiring does not honor the Beta-1 core-only contract`
  - `Live supported-path upload -> retrieval closure was not re-proven in the current audit window`
- Evidence Supporting This Read:
  - `Deterministic March 17 evidence is strong: Beta gate passed, 104 targeted runtime tests passed, 132 retrieval/context tests passed, 29 contract/support-profile tests passed`
  - `Live March 17 smoke still failed on profile mismatch, and in-container probes confirmed non-core routes remain mounted`
- Conditions Required Before Promotion:
  - `Fix the Compose env wiring and rerun smoke with quarantined routes returning 404`
  - `Capture a passing live Compose artifact for assistant completion plus document upload -> embed -> retrieval in the same audit window`

Use this section to state the release decision for the current audit window.
Do not mark the runtime as ready if the weighted score, recurring blocker class, or direct evidence disagree.

## Suggested Weekly Cadence

1. Gather incident notes, failed test runs, operator observations, and open runtime bugs from the current week.
2. Re-run the supported runtime path on the current branch or release candidate.
3. Fill the weighted index with evidence from the current audit window only.
4. Update bug classes and regression watchlist with anything newly observed or newly resolved.
5. Record the release readiness read and assign the next hardening tasks before the week closes.
