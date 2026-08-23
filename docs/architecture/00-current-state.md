## Purpose

This file is the canonical short-form source of truth for Codexify's current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated

2026-08-22

## Interpretation rule

This file is authoritative for:

- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase

`main` remains in local-first Beta hardening. An NX-1 supported-runtime audit receipt is now merged, but it is not successful supported-runtime closure: it advanced through source identity, Docker / Compose readiness, migrations / init, model preparation, and core data-plane health before backend startup failed. Current-tip supported-Compose closure remains open because the receipt audited a then-current `origin/main` SHA, not today's newer `main` tip, and no HTTP/runtime proof could continue after the backend failure.

## What changed recently

- Promoted authenticated identity/prompt/system-document routes and the read-only Connections catalog under ADR-072; generic connector mutation/sync remains quarantined.
- Merged Connections browser QA: 57 catalog entries exercised with `PASS WITH FINDINGS`; one P3 light-theme disabled-label contrast issue remains.
- Canonized Anthropic / Claude account-export conversation import as Beta Bounded / Conditional after the R2 proof recorded 63 threads and 784 messages through the durable worker path.
- Canonicalized Guardian Pi authorized-readiness diagnostics and regression coverage; no live provider or OAuth support was established.
- Repaired and requalified migration, psycopg3, Chroma-retirement, and supported-Compose proof seams; no resulting work widened the supported profile.
- PR #737 (merge `8cfe9daa5c15dbed59e626206f22dfd28032ed1c`) canonicalized the NX-1 receipt. In a fresh isolated worktree pinned to then-current `origin/main` at `29b01148a774a2e8f0fcacc47f44adf9f36f1e91`, source identity, Docker / Compose, migrations / init, and model preparation cleared; Postgres, Redis, and Neo4j were healthy. Backend startup then failed at module import in `guardian.memory.query_memory` with `sqlite3.OperationalError: attempt to write a readonly database`, before HTTP binding. No health, chat, queue/worker, persistence, or retrieval support claim resulted.
- Merged Settings dock material and active-selector polish; this changes presentation, not release capability.
- Added a simplification-opportunity audit; it does not change Beta posture and keeps canonical-versus-legacy configuration duplication as a high-risk reduction target.
- Added a Claude sidebar source icon with regression coverage; this is presentation-only.
- Froze the workspace-baseline next-phase execution graph; the document explicitly changes neither implementation nor release claims.

## Current supported reality

- Local Docker Compose is the supported install path, using `v1-local-core-web-mcp` with local-only defaults: `LLM_PROVIDER=local`, `CODEXIFY_LOCAL_ONLY_MODE=true`, and `ALLOW_CLOUD_PROVIDERS=false`.
- The accepted Beta support boundary and current live qualification are distinct: a supported surface is not thereby proven by NX-1, and the NX-1 receipt is not proof of the present `main` tip.
- Architecture, schema, DLG, focused test, and proof-validation tooling is present on `main`; these checks do not substitute for live-service proof.

## Release classes

### Beta Supported

- The local-first core remains the accepted Beta support boundary: local Docker Compose, local-only provider defaults, Whoosh'd / local inference, ordinary chat, durable threads/messages/tasks, upload → embed → readback, workspace-local retrieval, identity/ownership, migrations, and operator diagnostics on the supported profile.
- `/health`, `/health/chat`, and `/api/health/llm` remain the primary operator checks in the supported contract; NX-1 did not reach them.
- This class records the accepted support doctrine, not fresh current-tip runtime closure. The NX-1 backend-startup failure does not demote the accepted local-first support boundary.

### Beta Bounded / Conditional

- Persona Studio core and repository intelligence remain Beta Bounded / Conditional, with Guardian-owned authority and their existing single-user/local scope limits.
- OpenAI and bounded Anthropic account-export conversation import, Task Prompt Archive, and owner-scoped zero-write retry/recovery remain limited to their existing contracts and proven shapes.
- Authenticated local Settings read surfaces and the read-only `/api/connections` catalog remain bounded: catalog visibility does not imply setup, authorization, credentials, adapter health, or generic connector mutation/sync.

### Internal

- Direct Command Bus HTTP/control-plane APIs, plugin SDK internals, developer-only diagnostics, unsafe operator mutation surfaces, and generic tools / API-tools mechanisms remain Internal or quarantined operational substrate, not user-facing Beta promises.

### Qualification Pending

- Coding Loop — remaining gate: supported-profile adapter/provider execution with a terminal result, durable persistence, and source-thread readback.
- Hosted Rooms — remaining gate: clean supported/tester startup and owner/guest live semantic proof.
- DeepSeek / private-preview provider lane — remaining gate: required credentials, authenticated provider-specific persisted-turn proof, and explicit supported-profile promotion.
- Browser side-panel / Browser Host release surface and desktop packaging — remaining gate: their respective host, authentication, and release proof on current `main`.

### Out of Beta

- TTS / voice — Out of Beta.
- federation — Out of Beta.
- Unrestricted autonomous / recursive execution, arbitrary write-capability tools, ordinary-Beta generic shell/filesystem authority, public Command Bus, generic cron/unattended automation, generic connector mutation/sync, graph writes, and unsupported remote/multi-user repository execution — Out of Beta.

## Not yet true / do not assume

- Do not assume the present latest `main` SHA has passed supported-Compose closure; NX-1 audited `29b01148a774a2e8f0fcacc47f44adf9f36f1e91`, and `main` has advanced since that receipt.
- Do not assume backend startup is healthy, or that NX-1 reached `/health`, `/health/chat`, `/api/health/llm`, a live provider/model inventory, ordinary chat completion, queue dequeue, turn-lock concurrency, terminal task events, assistant persistence, source-thread readback, PostgreSQL assistant readback, or upload/embed/retrieval closure.
- Do not assume green unit tests, route registration, health responses, or proof receipts establish end-to-end runtime readiness.
- Do not assume Coding Loop, provider/tool turns, DeepSeek/private-preview execution, Hosted Rooms, Browser Host, or packaged desktop distribution are release-supported.
- Do not assume Anthropic import includes Projects, `memories.json`, `users.json`, binary media reconstruction, arbitrary export shapes, or Anthropic inference.
- Do not assume Connections catalog visibility provides a working adapter, configured credential, authorization, or live provider health; generic connector sync/mutation remains quarantined.
- Do not treat audit records, simplification recommendations, or the frozen next-phase graph as implementation or release proof.
- Do not count feature branches, unmerged work, origin-only commits, or proof from another checkout as shipped reality.

## Active blockers

- The first material NX-1 runtime blocker is backend runtime-readiness → import-time SQLite write attempt → `guardian.memory.query_memory` → `sqlite3.OperationalError: attempt to write a readonly database` → backend exits before binding its HTTP port. This was observed at audited SHA `29b01148a774a2e8f0fcacc47f44adf9f36f1e91`.
- Current-tip supported-Compose closure remains incomplete: a successful repair still requires a fresh rerun from current `origin/main`, because NX-1 is not proof of today's newest `main` tip.
- Queue/worker/turn-lock/terminal-event behavior still lacks current-tip end-to-end proof with durable output and readback.
- Canonical and legacy configuration paths coexist, leaving startup and operator-state drift risk.
- Coding Loop and tool-enabled provider lanes lack current supported-profile proof of adapter execution, terminal completion, continuation, and durable source-thread readback.
- DeepSeek/private-preview credentials and authenticated persisted turns remain unproven; Hosted Rooms still lack clean startup plus owner/guest semantic proof.

## This week's priorities

1. Repair or correctly fence the MemoryStore / `guardian.memory.query_memory` import-time SQLite write that blocks backend startup.
2. Rerun supported-Compose closure from current `origin/main`.
3. Prove health, model inventory, terminal chat, persistence, queue/worker/turn-lock behavior, and retrieval on that same supported profile.
4. Continue Coding Loop and provider/tool qualification only after the dependent runtime proof is available; otherwise keep those lanes quarantined.
5. Reconcile canonical-versus-legacy configuration paths, retain explicit operator diagnostics, and fix the bounded Connections P3 light-theme contrast defect without widening capability claims.

## Release definition right now

- [x] The supported profile, local-only defaults, Beta envelope, and ADR-069 release classes are defined on `main`.
- [x] Settings/Connections boundaries, generic connector quarantine, and Out-of-Beta surfaces are explicit.
- [x] PR #737 merged the bounded NX-1 receipt; the receipt records a first material backend-startup blocker without changing support classifications.
- [ ] Current-tip supported-Compose closure confirms healthy backend startup, health, model inventory, terminal chat, persistence, and retrieval.
- [ ] Queue, worker, lock, migration, configuration, and recovery behavior is green on the supported install path.
- [ ] Qualification-pending lanes have their named proof receipts; until then, they remain visibly quarantined.

## How to read the rest of the KB

- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence/invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
