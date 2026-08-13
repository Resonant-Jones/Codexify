## Purpose

This file is Codexify's canonical short-form source of truth for current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated

2026-08-12

## Interpretation rule

This file is authoritative for:

- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase

`main` is in local-first beta hardening at `c4787236e`. No additional product or release-scope commits landed on local `main` after the 2026-08-11 audit. The current release interpretation remains the local Docker Compose path and local-only provider posture. Recent tool-turn, provider, Whoosh'd, and DLG/ADR work is merged code, evidence, or contract/test surface; it does not widen the release promise without matching supported-path runtime proof.

## What changed recently

- Added the bounded read-only `op::health_health_get` chat capability and advertised-subset authority gate; general tool use remains outside the release promise.
- No additional product or release-scope commits landed on local `main` after the 2026-08-11 audit; release posture and blockers remain unchanged.
- Added DeepSeek native transport translation/continuation coverage and a cross-provider semantic convergence proof; both remain non-live provider evidence.
- Added Whoosh'd capability projection, structured transport, qualification/attestation seams, and exact-target identity reconciliation; the receipt covers one target/schema identity only.
- Canonicalized ADR-060 through ADR-063 and reverified DLG/knowledge-graph freshness after history corrections; these are control-plane/documentation changes.
- Added a Doctrine of Legible Responsibility and related tool-loop contract updates; they clarify boundaries without proving runtime readiness.
- Repaired the historical `d6f7a8b9c0d1` ThreadSpace migration lineage and the `b2c3d4e5f6a7` account-observability migration-content drift: `b2c3d4e5f6a7` was restored to its original applied body and a forward normalization migration (`9d4c2a7e1b6f`) converges clean, already-canonical, and backup-derived tester schemas onto one canonical ADR-049 shape at a single Alembic head. The preserved tester source remains unmodified and still requires a separate live upgrade/startup task; the canonical migrator psycopg driver compatibility remains a separate blocker until independently landed/proven; Hosted Room runtime proof remains pending; no release promise was widened.

## Current supported reality

- Local Docker Compose is the supported install path.
- The supported beta posture is local-only: `CODEXIFY_LOCAL_ONLY_MODE=true`, `ALLOW_CLOUD_PROVIDERS=false`, and `LLM_PROVIDER=local`.
- `whooshd-mlx` is the supported Apple Silicon local runtime preset; other local presets require explicit configuration.
- Chat completion, upload -> embed -> readback, and workspace-local retrieval are the supported beta paths represented on `main`; current-tip release qualification remains open.
- `GET /health`, `GET /health/chat`, and `GET /api/health/llm` are the primary operator checks.
- OpenAI export import, Task Prompt Archive, and owner-scoped retry of failed zero-write import jobs are present on `main`.
- Linked email aliases are resolved as a fallback to the existing user identity; the username path remains first.
- Bounded chat tool decisions pass through one advertised-subset authority gate. When `task.tools` is unset, ordinary chat may automatically expose exactly the read-only, zero-argument `op::health_health_get` (`GET /health`) capability to DeepSeek or to the exact Whoosh'd target when its current capability projection is eligible; explicit tool selections remain untouched, command visibility does not bypass execution authority, and this deterministic implementation does not widen release support.
- A committed live strict-structured qualification receipt exists for the exact `gemma-4-12b-it-qat-4bit` Whoosh'd target, but this is not general model or release support.
- Coding Loop route registration, focused tests, worker readiness/guard evidence, and profile enablement are present; they do not prove a successful adapter turn or durable terminal result.
- Architecture-contract, schema, DLG, and proof-validation tooling is present on `main`; it is not live-service proof.

## Not yet true / do not assume

- Do not assume cloud-provider beta support, a packaged desktop runtime, or a current local model without live endpoint and inventory proof.
- Do not assume the tester dual-provider lane is release-supported; it still needs authenticated, provider-specific persisted turns.
- Do not assume DeepSeek tool-turn tests or the Whoosh'd Gemma qualification establish supported-provider execution, general tool capability, or release support.
- Do not assume ADR/DLG canonicalization, freshness re-verification, or architecture contracts establish runtime support or release readiness.
- Do not assume a green health check, route acceptance, unit test, proof receipt, or docs contract proves end-to-end runtime readiness.
- Do not assume the linked-email migration alone proves upgrade success or authenticated end-to-end behavior on every existing database.
- Do not assume DLG/PAO documents or fixed ARPs provide corpus migration, arbitrary retrieval/RAG, database projection, assertion resolution, or agent authority.
- Do not assume Campaign Engine schemas provide scheduling, delegation, overnight execution, auto-merge, or auto-push.
- Do not assume the tool-unification plan provides implementation approval, terminal execution, or Coding Loop completion.
- Do not assume Browser Host, Chrome extension, Hosted Room, email, federation, graph writes, Continuity/Project Pulse, or P2P video are shipped beta behavior.
- Do not assume tool-boundary tests or the Coding Loop proof packet establish provider execution, terminal persistence, or durable source-thread readback.
- Do not count local branches, unmerged work, draft plans, origin-only commits, or proof from another checkout as shipped reality.

## Active blockers

- Fresh live Compose proof is still needed at `c4787236e`, including health, model inventory, terminal completion, persisted output, and retrieval.
- Queue-coupled chat still needs current-tip evidence for Redis, worker, turn-lock, and terminal-event behavior.
- Canonical and legacy configuration paths coexist, creating startup and operator-state drift risk.
- The bounded Coding Loop lane lacks current-tip proof of backend route acceptance, provider adapter execution, terminal result persistence, and durable source-thread readback; the prior proof stopped at backend exit code 3.
- Provider/tool-turn integration lacks current supported-profile proof for capability exposure, adapter execution, continuation, and durable completion; the exact Whoosh'd receipt does not close that gate.
- The private-preview lane lacks its required DeepSeek credential and authenticated session-token prerequisite.

## This week's priorities

1. Capture fresh supported-Compose proof at `c4787236e`: health, model inventory, chat, persistence, and retrieval.
2. Verify queue completion, turn locking, migration behavior, and import recovery under the supported profile.
3. Reconcile or clearly fence canonical-versus-legacy configuration paths.
4. Re-prove provider/tool-turn and the enabled Coding Loop lanes end to end, or quarantine them until their required proof exists.
5. Keep DLG/PAO, Campaign Engine, Browser Host, Hosted Room, and provider-preview work outside release claims until their required proof exists.

## Release definition right now

- [x] The supported profile and local-only flags define the beta posture.
- [x] Whoosh'd local runtime and core chat/upload/retrieval paths are represented on `main`.
- [x] Relevant architecture and schema validation is defined on `main`.
- [ ] Fresh live Compose evidence confirms terminal completion and persisted output at the audited tip.
- [ ] Queue, configuration, migration, and recovery behavior are green for the supported install path.
- [ ] Enabled Coding Loop routes have backend, authenticated adapter, terminal, and durable readback proof, or are quarantined.
- [ ] Any tool-enabled path has exact-target capability, authority, provider, continuation, terminal, and persistence proof on the supported profile.
- [ ] Any claimed preview or alternate surface has provider- or surface-specific runtime proof.
- [ ] Every release claim is merged to `main` and backed by evidence at the claimed proof level.

## How to read the rest of the KB

- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence and invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
