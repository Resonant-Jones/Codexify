# Approved Governing Core Runtime Sweep (`v1-local-core-web-mcp`)

## Summary
- Status: approved. This replaces the prior draft and governs the `v1` core-runtime stabilization sweep.
- Release promise: single-user local WebUI on Docker Compose, boringly reliable chat + document ingestion + retrieval, with `MCP` as the only public extension contract.
- Storage truth:
  - `Postgres` is the durable system of record for threads, messages, document metadata, audit state, command metadata, and audio metadata.
  - configured file/object storage is the durable system of record for raw media and audio bytes.
  - `Redis` is volatile coordination only: queues, turn locks, cancellation, task events, and worker heartbeats.
  - vector indexes, caches, browser session state, and similar search/runtime accelerators are derived and must be rebuildable from durable truth.
- Trust boundaries: browser to backend auth boundary, backend to provider boundary, backend to data boundary, and an internal-only SDK/plugin boundary for first-party features such as `TTS`.

## Supported Profile Manifest
- Define one named, versioned supported-profile manifest: `v1-local-core-web-mcp`.
- Represent it as a repo-owned machine-readable artifact consumed by startup diagnostics, docs, and smoke gates.
- The manifest pins:
  - surface: local Docker Compose + WebUI only
  - required services: `frontend`, `backend`, `db`, `redis`, `worker-chat`, `worker-document-embed`, `migrator`
  - optional/non-blocking services: `worker-warmup`, `neo4j`, `graph-init`
  - default route posture: core routes on; federation, connectors, flows, cron, websocket RPC, image generation, and legacy tools off
  - extension posture: `MCP` public, plugin SDK internal/provisional, raw command-bus HTTP internal
  - `TTS`: off in the supported profile by default; enabled only via a separate beta overlay
- Exact `v1` provider contract in the manifest:
  - `LLM_PROVIDER=local`
  - `ALLOW_CLOUD_PROVIDERS=false`
  - `CODEXIFY_LOCAL_ONLY_MODE=true`
  - `CODEXIFY_EGRESS_ALLOWLIST=`
  - `LOCAL_BASE_URL=http://host.docker.internal:11434/v1`
  - `LOCAL_API_KEY=local`
  - `LOCAL_LLM_MODEL=library2/ministral-3:8b`
  - `LOCAL_CHAT_MODEL=library2/ministral-3:8b` as a temporary compatibility alias until config convergence is complete
- Unsupported in `v1`: direct host-IP provider targets, non-`/v1` local endpoints, cloud-provider matrices, and bundled inference.

## Criticality Matrix
| Tier | Services / Workers | Routes / Surfaces | Required behavior |
|---|---|---|---|
| Tier 0 `release-blocking core` | `frontend`, `backend`, `db`, `redis`, `worker-chat`, `worker-document-embed` | thread create/list, message create/list, `POST /api/chat/{thread_id}/complete`, document upload/list, `/health`, `/health/chat`, `/health/llm`, `/api/tasks/{task_id}/events` | any failure blocks release |
| Tier 1 `supported-supporting` | `migrator`, `worker-warmup` | `/ping`, `/metrics`, `/api/events`, latest RAG trace/debug surfaces | may degrade only if Tier 0 remains green and operator diagnostics are explicit |
| Tier 2 `internal or beta` | command-bus substrate, cron workers, websocket RPC, federation/sync, TTS workers/services | raw `/api/guardian/commands/*`, `/api/cron/*`, `/api/ws/*`, `/api/tools/*`, `/tools/*`, `/api/media/tts/*` | must not degrade Tier 0; off by default or hidden |

## Interfaces and Boundary Rules
- Public extension contract for `v1`:
  - `MCP` capability set, naming, and behavior are the external promise.
  - MCP docs should describe stable tool behavior, not raw backend execution internals.
- Internal extension/control substrate:
  - `command bus` remains the internal execution layer used by MCP adapters and first-party control surfaces.
  - command-bus HTTP wire shape, run IDs, event schemas, and store internals are not part of the `v1` public compatibility promise.
- Legacy tool routes:
  - `/api/tools/*` and `/tools/*` are aggressively quarantined.
  - In the supported profile they are unmounted by default, not merely deprecated.
  - If retained outside the supported profile, they stay explicit legacy/debug-only with no frontend links and no public docs.
- SDK/plugin boundary:
  - plugin SDK remains internal/provisional and may continue powering first-party features like `TTS`.
  - `v1` does not promise SDK stability, compatibility, or third-party developer support.

## Reliability Changes
- Boot determinism:
  - converge all boot-critical provider/config reads onto one canonical settings path
  - keep compatibility aliases only behind coherence tests
  - fail startup fast when the supported profile manifest and effective runtime disagree
  - remove supported-path bootstrap dependence on ad hoc runtime downloads
- Orphaned turn crash recovery:
  - replace plain string turn locks with structured lock payloads carrying `thread_id`, `turn_id`, `owner_task_id`, `acquired_at`, and lease metadata
  - renew the lease while a worker actively owns the turn
  - add a startup sweeper and a runtime stale-lock reconciler for `turn_lock:*`
  - on `turn_in_flight`, inspect lock age and owner state; if stale and unrecoverable, emit an audit event, clear the lock, and allow one safe retry
  - add restart tests proving no worker crash can wedge a thread until TTL expiry alone
- Provider/runtime honesty:
  - the UI and health/catalog surfaces may advertise only the exact local provider shape in the supported profile
  - if the blessed provider path is missing or offline, boot and UI must fail honestly with actionable setup guidance
  - no flexible provider matrix in `v1`
- Ingestion recoverability:
  - document parsing and metadata stay durable in Postgres/storage
  - embedding/vector state remains replayable
  - failed embeddings must have an explicit retry/replay path and visible operator state

## Release Gates
### Core Release Gates
- The `v1-local-core-web-mcp` manifest resolves cleanly at startup and matches the effective runtime.
- First-run Docker Compose boot succeeds without manual recovery.
- WebUI loads and reaches a truthful ready/degraded state.
- `/health/chat` and `/health/llm` are green for the exact blessed local provider contract.
- Thread create -> message send -> assistant completion succeeds without stuck turns.
- Document upload reaches `ready`, then participates in retrieval through the real chat path.
- Restart sanity passes:
  - durable state survives restart
  - no orphaned turn lock blocks the next completion
  - no duplicate assistant turn is created
- Quarantined routes remain off or hidden in the supported profile.

### TTS Beta Isolation Checks
- `TTS` is not part of the core release gate and is off by default in `v1-local-core-web-mcp`.
- A separate internal beta overlay may enable `TTS`, but backend boot, chat completion, retrieval, and message rendering must remain healthy if `TTS` is absent, disabled, or failing.
- `TTS` failure must produce isolated error state only; it must not fail the assistant turn, wedge a queue, or regress the core smoke path.
- `TTS` checks validate isolation, not feature completeness.

## Assumptions and Defaults
- Scope remains `core-only`.
- Supported install path remains local WebUI on Docker Compose.
- `MCP` remains the only public extension promise.
- plugin SDK remains internal/provisional.
- `TTS` remains a guarded first-party beta behind isolation rules.
- If a later release promotes SDK stability, bundled inference, or broader deployment, it must do so by introducing a new named supported-profile manifest rather than by widening this one in place.
