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

`main` remains in local-first Beta hardening. Recent mainline work added audit evidence, a simplification-risk ledger, a frozen next-phase execution graph, a daily log, and a sidebar source icon; none expands the supported runtime. Fresh current-tip supported-Compose proof remains open.

## What changed recently

- Promoted authenticated identity/prompt/system-document routes and the read-only Connections catalog under ADR-072; generic connector mutation/sync remains quarantined.
- Merged Connections browser QA: 57 catalog entries exercised with `PASS WITH FINDINGS`; one P3 light-theme disabled-label contrast issue remains.
- Canonized Anthropic / Claude account-export conversation import as Beta Bounded / Conditional after the R2 proof recorded 63 threads and 784 messages through the durable worker path.
- Canonicalized Guardian Pi authorized-readiness diagnostics and regression coverage; no live provider or OAuth support was established.
- Repaired and requalified migration, psycopg3, Chroma-retirement, and supported-Compose proof seams; the current Compose closure receipt remains blocked at runtime selection/source provenance.
- Merged Settings dock material and active-selector polish; this changes presentation, not release capability.
- Captured a 2026-08-21 current-main supported-runtime audit; its preflight stopped at source identity and produced no new live health, chat, persistence, or retrieval evidence.
- Added a simplification-opportunity audit; it does not change Beta posture and keeps canonical-versus-legacy configuration duplication as a high-risk reduction target.
- Added a Claude sidebar source icon with regression coverage; this is presentation-only.
- Froze the workspace-baseline next-phase execution graph; the document explicitly changes neither implementation nor release claims.

## Current supported reality

- Local Docker Compose is the supported install path, using `v1-local-core-web-mcp` with local-only defaults: `LLM_PROVIDER=local`, `CODEXIFY_LOCAL_ONLY_MODE=true`, and `ALLOW_CLOUD_PROVIDERS=false`.
- Whoosh'd / local inference, ordinary chat, durable threads/messages/tasks, upload → embed → readback, and workspace-local retrieval are in the Beta envelope.
- `/health`, `/health/chat`, and `/api/health/llm` are the primary operator checks; route inventory is published by startup for frontend capability gating.
- Authenticated local Settings routes and the read-only `/api/connections` catalog are bounded Beta surfaces; catalog visibility does not imply setup, authorization, credentials, or health.
- OpenAI and bounded Anthropic account-export conversation import, Task Prompt Archive, and owner-scoped zero-write retry/recovery are present only within their existing contracts.
- Persona Studio core and repository intelligence are Beta Bounded / Conditional; authority remains Guardian-owned and scope-limited.
- Architecture, schema, DLG, focused test, and proof-validation tooling is present on `main`; these checks do not substitute for live-service proof.

## ADR-069 release-class interpretation

The five human-facing Beta release classes are the canonical short-horizon interpretation of accepted ADR-069 posture. The classification of each surface below matches the current accepted authority; this section does not introduce a new taxonomy and does not promote or demote any capability.

### Beta Supported

The normal supported Beta envelope. Today this includes:

- the local Docker Compose install path (`v1-local-core-web-mcp` with local-only defaults);
- the local-only provider posture (`LLM_PROVIDER=local`, `CODEXIFY_LOCAL_ONLY_MODE=true`, `ALLOW_CLOUD_PROVIDERS=false`);
- Whoosh'd / local inference on the supported local profile;
- ordinary chat, durable threads / messages / tasks, upload → embed → readback, and workspace-local retrieval;
- the canonical operator health surfaces (`/health`, `/health/chat`, `/api/health/llm`).

This envelope is not a claim of current-tip live proof or production-grade readiness.

### Beta Bounded / Conditional

Surfaces that are intentionally part of Beta but only inside an explicit authority, topology, provider, mode, or capability boundary. Today this includes:

- authenticated local Settings routes and the read-only `/api/connections` catalog, within their existing contracts; catalog visibility does not imply setup, authorization, credentials, or live health;
- Persona Studio core (profile create / edit / select / apply), where TTS / voice execution, unsupported permission authoring, unsupported retrieval-policy execution, and preview-UI equals-enforcement claims are not in this promotion;
- repository intelligence (candidate discovery, explicit repository import, account / Project `RepositoryBinding`, direct Project-bound repository search, ordinary-chat exposure only when Guardian resolves exactly one valid active binding and existing authority checks pass), governed by ADR-065;
- bounded import / continuity surfaces: OpenAI and bounded Anthropic account-export conversation import, Task Prompt Archive, and owner-scoped zero-write retry / recovery, only within their existing contracts.

### Internal

Real operational substrate or operator / developer mechanisms that may support Beta behavior but are not themselves a public / user-facing release promise. Examples include:

- direct Command Bus HTTP / control-plane surfaces;
- plugin SDK internals;
- developer-only diagnostics;
- generic internal tooling or mutation surfaces that are not separately Beta-qualified;
- local Guardian Evidence bounded-read tooling (`scripts/guardian/read_bounded_evidence.py`; see also the Guardian Evidence bounded read contract and the static proof fixture `guardian-evidence-bounded-read.local-tooling.v1.json`) is present as Internal repository-local static evidence preparation over validated, allowlisted source references; it remains bounded and non-executing and does not authorize evidence ingestion, packet generation, authority promotion, source mutation, provider execution, WorkOrder or Execution Ledger writes, CI/default release gating, or release-support expansion.

### Qualification Pending

Intended or plausible Beta surfaces whose implementation is present but whose named proof / authority / operational gate remains open. Each entry names its remaining gate.

- **Coding Loop** — remaining gate: provider / adapter execution plus terminal durable result plus durable source-thread readback on the claimed supported profile.
- **Hosted Rooms** — remaining gate: clean supported / tester startup plus owner / guest live semantic proof after the applicable migration repair.
- **DeepSeek / private-preview provider lane** — remaining gate: required credentials, authenticated provider-specific persisted runtime proof, and explicit supported-profile promotion.

None of these are promoted to Beta Supported by being listed here.

### Out of Beta

Surfaces explicitly excluded from the present Beta promise. They are intentionally Out of Beta, not qualification-pending, and are not promoted by being listed here.

- TTS / voice execution — Out of Beta.
- federation — Out of Beta.
- unrestricted autonomous / recursive agent execution — Out of Beta.
- arbitrary write-capability tool use — Out of Beta.
- generic shell / filesystem execution through ordinary Beta chat — Out of Beta.
- public Command Bus exposure — Out of Beta.
- generic cron / unattended automation — Out of Beta.
- generic connectors without separate qualification — Out of Beta.
- graph-write / Neo4j-derived-write behavior where the supported path remains flagged off or quarantined — Out of Beta.
- remote / multi-user repository execution not covered by a separately accepted authority contract and live proof — Out of Beta.

## Not yet true / do not assume

- Do not assume a fresh current-tip Compose run proves health, model inventory, chat completion, persisted output, or retrieval.
- Do not assume green unit tests, route registration, health responses, or proof receipts establish end-to-end runtime readiness.
- Do not assume Coding Loop, provider/tool turns, DeepSeek/private-preview execution, Hosted Rooms, Browser Host, or packaged desktop distribution are release-supported.
- Do not assume Anthropic import includes Projects, `memories.json`, `users.json`, binary media reconstruction, arbitrary export shapes, or Anthropic inference.
- Do not assume Connections catalog visibility provides a working adapter, configured credential, authorization, or live provider health; generic connector sync/mutation remains quarantined.
- Do not assume TTS/voice execution, federation, graph writes, generic shell/filesystem tools, recursive agents, public Command Bus, or unattended automation are in Beta.
- Do not treat audit records, simplification recommendations, or the frozen next-phase graph as implementation or release proof.
- Do not count feature branches, unmerged work, origin-only commits, or proof from another checkout as shipped reality.

## Active blockers

- Fresh supported-Compose proof at current `main` is incomplete: the latest current-main audit stopped before live startup because its source-identity preflight did not match `origin/main`; no later current-tip runtime receipt is present on `main`.
- Queue/worker/turn-lock/terminal-event behavior still lacks current-tip end-to-end proof with durable output and readback.
- Canonical and legacy configuration paths coexist, leaving startup and operator-state drift risk.
- Coding Loop and tool-enabled provider lanes lack current supported-profile proof of adapter execution, terminal completion, continuation, and durable source-thread readback.
- DeepSeek/private-preview credentials and authenticated persisted turns remain unproven; Hosted Rooms still lack clean startup plus owner/guest semantic proof.

## This week's priorities

1. Capture current-tip supported-Compose proof for health, model inventory, chat, persistence, and retrieval.
2. Validate queue completion, turn locking, migrations, configuration, and import recovery on that same supported profile.
3. Reprove Coding Loop and provider/tool-turn lanes end to end, or keep them quarantined.
4. Reconcile canonical-versus-legacy configuration paths and retain explicit operator diagnostics.
5. Fix the Connections P3 light-theme contrast defect without widening its capability claim.

## Release definition right now

- [x] The supported profile, local-only defaults, Beta envelope, and release classes are defined on `main`.
- [x] Settings/Connections boundaries, generic connector quarantine, and Out-of-Beta surfaces are explicit.
- [x] Every claimed capability is merged to `main` and classified by its evidence/support boundary.
- [ ] Current-tip live proof confirms supported Compose health, model inventory, terminal chat, persistence, and retrieval.
- [ ] Queue, worker, lock, migration, configuration, and recovery behavior is green on the supported install path.
- [ ] Qualification-pending lanes either have their named proof or remain visibly quarantined.

## How to read the rest of the KB

- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence/invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
