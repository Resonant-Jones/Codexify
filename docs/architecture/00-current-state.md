## Purpose

This file is the canonical short-form source of truth for Codexify's current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated

2026-08-24

## Interpretation rule

This file is authoritative for:

- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase

`main` remains in local-first Beta hardening. The latest merged NX-1 supported-Compose observation cleared dependency startup, migrations / init, model preparation, and backend-container Guardian application import; the historical MemoryStore readonly-write failure did not recur. Startup then failed during lifespan on supported local-gateway configuration coherence before healthy HTTP. PR #745 aligned `.env.example` with the existing supported profile, but no post-alignment supported-Compose rerun is recorded, so current-tip closure remains open.

## What changed recently

- Promoted authenticated identity/prompt/system-document routes and the read-only Connections catalog under ADR-072; generic connector mutation/sync remains quarantined.
- Merged Connections browser QA: 57 catalog entries exercised with `PASS WITH FINDINGS`; one P3 light-theme disabled-label contrast issue remains.
- Canonized Anthropic / Claude account-export conversation import as Beta Bounded / Conditional after the R2 proof recorded 63 threads and 784 messages through the durable worker path.
- Canonicalized Guardian Pi authorized-readiness diagnostics and regression coverage; no live provider or OAuth support was established.
- Repaired and requalified migration, psycopg3, Chroma-retirement, and supported-Compose proof seams; no resulting work widened the supported profile.
- PR #744/#745 advanced the NX-1 startup boundary. At audited SHA `7aae1807492313d4cf10eb7876c3ebde92408819`, dependency services, migrations / init, model preparation, and backend-container Guardian import succeeded; `guardian_api_import_ok` was emitted, `guardian/memory/store.db` was not created, and the historical `sqlite3.OperationalError` readonly-write failure did not recur. Lifespan then stopped on `LLMConfigError` because five local-gateway template values diverged from the active supported profile. PR #745 aligned `.env.example` with that existing profile contract and added static coverage; it did not prove a post-repair supported-Compose rerun, healthy HTTP, chat, persistence, or retrieval. No release support widened.
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
- local Guardian Evidence bounded-read tooling (`scripts/guardian/read_bounded_evidence.py`; see also the Guardian Evidence bounded read contract and the static proof fixture `guardian-evidence-bounded-read.local-tooling.v1.json`) is present as Internal repository-local static evidence preparation over validated, allowlisted source references; it remains bounded and non-executing and does not authorize evidence ingestion, packet generation, authority promotion, source mutation, provider execution, WorkOrder or Execution Ledger writes, CI/default release gating, or release-support expansion.
- local Guardian Evidence packet-generator tooling (`scripts/guardian/generate_evidence_packet.py`) is present as Internal stdout-only static packet preparation over bounded-read artifacts and remains governed by the Guardian Evidence Packet generator contract (`docs/architecture/guardian-evidence-packet-generator-contract.md`); it reads only supplied bounded-read results and does not authorize source-target reads, evidence ingestion, execution, authority promotion, source mutation, provider execution, WorkOrder or Execution Ledger writes, CI/default release gating, or release-support expansion.
- local Guardian Evidence reducer input-bundle dry-run loader tooling (`scripts/guardian/reducer_dry_run.py --json --input-bundle ...`) is present as Internal diagnostics-only tooling and remains governed by the input-bundle dry-run loader contract (`docs/architecture/guardian-evidence-reducer-input-bundle-dry-run-loader-contract.md`); it validates only the explicitly selected bundle before mapping metadata into reducer input objects, reads the bundle file but not `source_ref` targets, returns `packet=null` and `validation_result=null`, keeps all authority locks false, and does not provide evidence ingestion, packet generation, runtime reducer behavior, command-bus/Codex Runner/Pi/provider execution, source mutation, WorkOrder or Execution Ledger writes, CI/default release gating, or release-support expansion.
- the static Guardian Evidence Reducer input bundle template (`docs/architecture/templates/guardian-evidence-reducer-input-bundle-template.v1.json`) and local-tooling fixture (`docs/architecture/fixtures/guardian-evidence-reducer-input-bundle.local-tooling.v1.json`) are present as Internal authoring aids for future reducer-input shape; they are not evidence and do not authorize file reads, evidence ingestion, packet generation, runtime reducer behavior, UI support, Command Bus/Codex Runner/Pi/provider execution, source mutation, WorkOrder or Execution Ledger writes, CI/default release gating, or release-support expansion.

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

- Do not assume the present latest `main` SHA has passed supported-Compose closure: the latest merged NX-1 observation audited `7aae1807492313d4cf10eb7876c3ebde92408819`, and no post-PR-745 live rerun is proven.
- Do not assume backend startup is healthy, or that NX-1 reached `/health`, `/health/chat`, `/api/health/llm`, a live provider/model inventory, ordinary chat completion, queue dequeue, turn-lock concurrency, terminal task events, assistant persistence, source-thread readback, PostgreSQL assistant readback, or upload/embed/retrieval closure.
- Do not assume `.env.example` alignment, static configuration tests, or the cleared historical MemoryStore failure prove current-tip healthy HTTP, model inventory, terminal chat, persistence, retrieval, queue/worker, or turn-lock closure.
- Do not assume green unit tests, route registration, health responses, or proof receipts establish end-to-end runtime readiness.
- Do not assume Coding Loop, provider/tool turns, DeepSeek/private-preview execution, Hosted Rooms, Browser Host, or packaged desktop distribution are release-supported.
- Do not assume Anthropic import includes Projects, `memories.json`, `users.json`, binary media reconstruction, arbitrary export shapes, or Anthropic inference.
- Do not assume Connections catalog visibility provides a working adapter, configured credential, authorization, or live provider health; generic connector sync/mutation remains quarantined.
- Do not treat audit records, simplification recommendations, or the frozen next-phase graph as implementation or release proof.
- Do not count feature branches, unmerged work, origin-only commits, or proof from another checkout as shipped reality.

## Active blockers

- The historical NX-1 MemoryStore readonly-write failure is cleared evidence, not the active blocker: at audited SHA `7aae1807492313d4cf10eb7876c3ebde92408819`, backend-container Guardian import emitted `guardian_api_import_ok`, did not create `guardian/memory/store.db`, and did not emit `sqlite3.OperationalError` or `attempt to write a readonly database`.
- The active supported-runtime blocker is that fresh supported-Compose closure has not been rerun after the merged `.env.example` supported-profile alignment. The latest observation instead stopped before healthy HTTP on `LLMConfigError` from five local-gateway configuration mismatches; PR #745 repaired the template contract statically but did not prove the required live rerun.
- Queue/worker/turn-lock/terminal-event behavior still lacks current-tip end-to-end proof with durable output and readback.
- Canonical and legacy configuration paths coexist, leaving startup and operator-state drift risk.
- Coding Loop and tool-enabled provider lanes lack current supported-profile proof of adapter execution, terminal completion, continuation, and durable source-thread readback.
- DeepSeek/private-preview credentials and authenticated persisted turns remain unproven; Hosted Rooms still lack clean startup plus owner/guest semantic proof.

## This week's priorities

1. Rerun fresh current-main supported-Compose closure using the merged aligned template.
2. Prove health, model inventory, terminal chat, persistence, queue/worker/turn-lock behavior, and retrieval on that same supported profile.
3. Continue Coding Loop and provider/tool qualification only after the dependent runtime proof is available; otherwise keep those lanes quarantined.
4. Reconcile canonical-versus-legacy configuration paths, retain explicit operator diagnostics, and fix the bounded Connections P3 light-theme contrast defect without widening capability claims.

## Release definition right now

- [x] The supported profile, local-only defaults, Beta envelope, and ADR-069 release classes are defined on `main`.
- [x] Settings/Connections boundaries, generic connector quarantine, and Out-of-Beta surfaces are explicit.
- [x] The latest merged NX-1 proof clears the historical MemoryStore import-time readonly-write failure, and PR #745 aligns `.env.example` with the existing supported profile; neither establishes a post-repair live closure or changes support classifications.
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
