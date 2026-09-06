## Purpose

This file is the canonical short-form source of truth for Codexify’s current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated

2026-09-06

## Interpretation rule

This file is authoritative for:

- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase

`main` remains in local-first Beta hardening with a gated private-preview lane. The private-preview database has now reached the Persona head `d4e0f2a5b7c9` with original-column preservation and canonical no-op proof. The old application remains stopped and stack reconciliation is intentionally suspended until matching Persona deployment is qualified. No Beta support boundary widened.

## What changed recently

- [Persona Chroma empty-control qualification](./proofs/runtime/2026-09-06-persona-private-preview-chroma-empty-control-diagnosis.md) establishes `EMPTY_CONTROL_HARNESS_PERMISSION_DEFECT`: the reproduced host bind passes ordinary writes but fails stdlib SQLite with `SQLITE_READONLY_DBMOVED` (1032); container-internal and named-volume controls pass SQLite and first-call Chroma initialization. A corrected preserved-copy comparison remains pending. No canonical retirement, application restart, or recovery is proven.

- [Persona deployment attempt 2](./proofs/runtime/2026-09-06-persona-private-preview-lineage-proof-r2.md) is BLOCKED: the matching backend failed startup with `pyo3_runtime.PanicException` in Chroma initialization. The startup migrator exited 0 and the database remains at `d4e0f2a5b7c9`. The restarting backend was stopped; frontend/origin/workers never reached running state. PostgreSQL, Redis, and Neo4j remain available, the rollback checkpoint is intact, and stack reconciliation remains suspended. Live Persona route and browser proof remain pending; no release claim advances.

- [Persona private-preview live upgrade](./proofs/runtime/2026-09-06-persona-private-preview-live-migration-proof.md) proved the authorized upgrade to `d4e0f2a5b7c9` after a fresh external checkpoint. All 111 pre-existing tables / 5,595 rows retained original-column digests; the second canonical migrator run was a no-op. PostgreSQL remains running, old application services remain stopped, stack reconciliation remains unloaded, and the tunnel agent and desired-up marker remain intact. Matching Persona application deployment and authenticated browser save/readback are pending.

- [Persona private-preview clone migration rehearsal](./proofs/runtime/2026-09-06-persona-private-preview-migration-rehearsal-proof.md) proved `b2c8d0e3f5a7 → c3d9e1f4a6b8 → d4e0f2a5b7c9` compatibility using the canonical Persona-branch migrator on an isolated restored snapshot. All 111 pre-existing tables retained row counts and original-column digests. That prerequisite is closed; no release claim advances.

- Repository-level private-preview Persona Profile admission is proven: `v1-whooshd-deepseek-web` adds only `persona_profiles` to enabled routes. Three focused profile/router/auth cases prove mounting, rejection of anonymous/static-key/unapproved sessions, approved-session account scope, and explicit flag disablement; all six private-preview Compose contract cases pass with the hermetic harness. This admits the existing authenticated create/list/read/update API under ADR-082 without changing manifest, revision, binding, provider, service, or runtime implementation semantics. It is bounded tester exposure, not broader Beta support.

- Persona Studio saved state now depends on backend-confirmed canonical V1 manifests and server revisions. Full authored manifest hydration/writes, update/create failure preservation, offline draft recovery without saved authority, and edits surviving delayed acknowledgements are covered by focused store/page tests. localStorage remains draft/cache continuity only; it does not restore revision authority. This is frontend state/component proof with mocked API responses, not live runtime qualification. Persona bindings, thread pins, capability enforcement, backend semantics, and release/support boundaries are unchanged.

- Added the internal authenticated `GET /api/system_prompt/inspect` signal and migrated the Settings `SystemPromptInspector` to consume it as its sole backend read: canonical thread profile ID/revision/source observation, active Imprint metadata, independent system-document counts, legacy-free inspection-builder measurements, and per-layer failure states now remain visible through the existing read-only UI. Focused frontend tests prove one canonical request, state-preserving normalization, revisionless profiles, partial layer unavailability, and request-level retry behavior. This is not supported-profile exposure, live-browser qualification, or release support.

- Removed frontend clients and controls for the retired Persona mutation endpoint: Settings no longer edits or syncs legacy Persona prompt text, and obsolete Persona panels/hooks are deleted. Unrelated local preview fields and Imprint proposal/accept/reject remain unchanged; retained status consumers observe legacy Persona state read-only. No replacement API or local Persona authority was introduced. Legacy Persona storage/status observation and canonical Persona Studio adoption remain unfinished; the Settings Inspector migration is bounded to the canonical read-only projection and does not widen release/support claims.

- Retired `POST /api/imprint/persona` and its backend mutation implementation, with no replacement or compatibility write shim. The Imprint router has no Persona mutation handler. Focused backend tests prove the retired path returns 404 without changing existing legacy Persona fields or creating rows; `/api/imprint/accept` remains Imprint-only and `/api/imprint/status` retains read-only legacy observation. Frontend callers and obsolete editing controls are now removed. Legacy storage/resolution, canonical Persona semantics, Guardian identity, and prompt assembly are unchanged; no release/support claim widens.

- Closed Imprint acceptance-to-Persona coupling: `/api/imprint/accept` activates only the owned Imprint, rejects Persona override input with HTTP 400, and returns only Imprint state. Settings Imprint Review reflects this contract. Focused tests prove activation, unchanged legacy Persona fields, no new Persona row, and preserved scope protections; canonical Persona revisions, bindings, selections, snapshots, Guardian identity, and prompt order remain unchanged. Legacy Persona storage/status observation and canonical Persona Studio adoption remain unresolved; this is bounded test/code evidence, not a release-support claim.

- Qualified the private-preview migration lineage on a disposable clone, then upgraded the live database to `b2c8d0e3f5a7` with preservation, worker recovery, no-op, and authenticated read checks passing.
- Proved the installed post-upgrade scheduled reconciler completes against `b2c8d0e3f5a7` from its coherent shared migrator image, while preserving healthy long-running container identities and canonical database state.
- Proved chat-history disappearance is a data-present/API-filter mismatch caused by legacy Project ownership divergence; no canonical chat row loss or runtime database-target drift was found.
- Accepted ADR-081 naming `projects.user_id` as Project ownership authority; runtime normalization and legacy reconciliation remain unfinished.
- Accepted ADR-058 separating canonical Persona Profile authored authority from Imprint relational/presentation ownership; legacy Persona observation/status and canonical Persona Studio adoption remain unfinished. The Settings Inspector now observes the canonical read-only projection without changing those ownership boundaries, and no Beta/support claim changed.
- Merged phone sidebar/navigation and composer overflow work with focused frontend coverage; this is UI change evidence, not supported-path browser proof.
- Added a metering/billing foundation design sketch; it is explicitly unimplemented and does not affect release scope.
- Pinned private-preview chat worker concurrency to one to match the installed single-slot MLX-VLM runtime; Compose validation and focused contract coverage pass, but live provider qualification remains open.

## Current supported reality

- The named supported install path is local Docker Compose using `v1-local-core-web-mcp` with `LLM_PROVIDER=local`, `CODEXIFY_LOCAL_ONLY_MODE=true`, and `ALLOW_CLOUD_PROVIDERS=false`.
- The intended Beta Supported boundary remains local inference, ordinary chat, durable threads/messages/tasks, upload → embed → readback, workspace-local retrieval, identity/ownership, migrations, and operator diagnostics; this is support doctrine, not current-tip qualification.
- Mainline contains focused project lifecycle, conversation-origin, document-artifact preview, Guardian Chat, account-import, and mobile-shell repairs with targeted coverage; supported-path and authenticated browser proof remain separate gates.
- Valid account-import multipart batches are accepted and durably staged on the server path; the Safari/WebKit envelope failure remains unrepaired.
- Private-preview live migration preservation/readback, Guardian secret rotation, Cloudflare ingress, and private-profile People/Share behavior have bounded evidence; these do not admit guests or widen Beta.
- Private-preview Compose now routes additional accepted local turns through the durable Redis chat queue behind one provider execution slot; this is a bounded admission configuration, not provider execution proof.
- Pi 0.82.1 wrapper/API, source-vendor, identity, framing, and telemetry changes remain internal, non-inference, or OAuth-readiness qualification.

## Not yet true / do not assume

- Persona Profile deployed lineage is not yet proven, and authenticated Persona Studio browser save/backend readback is not yet proven. Repository/profile admission and focused tests do not establish that the running private-preview deployment contains this Persona branch/profile. Qualify the deployed lineage and `/api/persona-profiles` route before resuming live browser authority proof.

- Do not assume current-tip Compose health, model inventory, terminal chat, durable assistant readback, retrieval, queue/worker execution, locks, terminal events, or recovery closure.
- Do not treat historical scheduled-recovery proof at `b2c8d0e3f5a7` or the live Persona migration as canary/provider closure. The database is now at `d4e0f2a5b7c9`; old application services are stopped and stack reconciliation is suspended pending matching deployment. Remaining preview gates stay open.
- Do not treat one-slot private-preview worker serialization or its contract test as proof that the live MLX-VLM provider executes, persists, or recovers chat successfully.
- Do not treat ADR-081 acceptance, chat-history classification, or focused UI tests as runtime Project-ownership convergence or supported browser proof.
- Do not treat ADR-058 acceptance as legacy Persona removal, frontend consumer removal, Settings or Persona Studio convergence, inspector consolidation, Default Guardian Profile semantics, or a Beta/support expansion.
- Do not treat CE-L1 OAuth readiness, Pi telemetry, wrapper tests, or source-vendor closure as live provider/model execution, coding-loop completion, persisted-result readback, or Beta proof.
- Do not treat private-preview configuration, bounded recovery/ingress receipts, or a live health/read result as an admitted canary; tester isolation, provider, persistence, and observability gates remain open.
- Do not treat Modal or E2B partial conformance as a qualified hosted sandbox, provider-enforced storage/read-only boundary, supported runtime path, or release support.
- Do not infer shipped reality from mutable `latest`, another checkout, local-only artifacts, planning language, or docs alone; realtime delivery, attachments, federation, and cross-node People messaging remain deferred.

## Active blockers

- Fresh supported-Compose closure is missing at the current `main` tip, including health, chat, persistence/readback, retrieval, queue/worker, locks, and terminal events.
- Private-preview provider-specific execution, persistence, observability, tester isolation, and approved non-admin canary gates remain open; one-slot worker serialization and scheduled recovery are bounded prerequisites, not closure.
- Fresh-state Chroma startup/retrieval qualification remains unresolved; Chroma is derived state and no repair or historical restore is proven.
- CE-L1 still lacks live provider/model execution, terminal durable result, and source-thread readback.
- The friends-and-family canary is blocked on approved non-admin testers plus reruns of Access, isolation, provider, persistence, and bounded-observability gates; DeepSeek rotation/requalification remains open.
- Project-ownership runtime/data convergence, Safari multipart-envelope repair, Watchdog policy/model, immutable image-retention, hosted-sandbox, and recent supported-path browser gates remain unclosed.

## This week’s priorities

1. Rerun current-main supported-Compose closure with the canonical local profile.
2. Prove health, terminal chat, persistence/readback, retrieval, queue/worker, locks, and terminal events on that profile; requalify Chroma.
3. Requalify CE-L1 live execution/readback and rotate/requalify the private-preview DeepSeek credential before tester execution.
4. Close Project-ownership convergence, Safari upload-envelope regression, and the browser, Watchdog, retention, and hosted-sandbox gates.

## Release definition right now

- [x] Supported local Compose path, local-only defaults, and Beta boundary are defined on `main`.
- [x] Internal, bounded/conditional, qualification-pending, and Out-of-Beta surfaces remain separate from Beta Supported claims.
- [x] Private-preview migration preservation/readback and ingress proofs are bounded without guest admission or release widening.
- [ ] Current-tip Compose proves healthy startup, model inventory, terminal chat, persistence/readback, and retrieval.
- [ ] Queue, worker, lock, migration, configuration, recovery, browser, and account-import claimed-path evidence gates are green.
- [ ] Every claimed preview/provider lane has current-main proof for live execution, durable readback, isolation, and scheduled recovery where applicable.

## How to read the rest of the KB

- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence/invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.

## Release classes

The five release classes below are accepted architecture per ADR-069. They are
human-facing release interpretations over the existing Product Architecture
Assertion dimensions and the `00-current-state.md` short-form authority, not
new schema enums. Evidence maturity and support posture remain orthogonal
under ADR-069. Support doctrine does not prove every current-tip gate is
green; the "Not yet true / do not assume" and "Active blockers" sections above
remain authoritative for the present live-state truth.

### Beta Supported

The current Beta Supported envelope is the local-first supported install
path and its core surfaces, already present in this document and accepted
by ADR-069:

- Local Docker Compose runtime, with the local-only default provider posture
  (`CODEXIFY_LOCAL_ONLY_MODE=true`, `ALLOW_CLOUD_PROVIDERS=false`,
  `LLM_PROVIDER=local`).
- Local inference (Whoosh'd) and the supported local profile.
- Core startup / migration lifecycle.
- Queue-backed chat completion lifecycle.
- Durable thread / message / task persistence.
- Supported health and runtime diagnostics.
- Ordinary chat, threads, durable conversation history, projects, and
  project / thread / workspace navigation.
- Documents and media ingestion on currently implemented supported formats.
- Embedding and workspace-scoped retrieval.
- Codexify-native identity / authentication boundaries and account-scoped
  ownership behavior.
- Operator-visible health and configuration truth required to run the
  self-hosted node.

This is support doctrine, not current-tip qualification. The "Not yet true
/ do not assume" section above continues to bound what is provably green
on the current `main` tip. Implementation presence in a code path does not
promote a capability to Beta Supported; only the architecture-accepted
support envelope under ADR-069 does.

### Beta Bounded / Conditional

Surfaces intentionally inside the Beta envelope but only under an explicit
authority, topology, provider, mode, or capability boundary. The
classification below is the current accepted one; no new bounded surface
is added by this section.

- Persona Studio: profile creation / editing, persistence, selection, and
  application of supported persona / profile configuration to ordinary chat.
  TTS / voice execution, unsupported permission authoring, unsupported
  retrieval-policy execution, and "preview UI equals enforcement" claims
  are excluded from this promotion.
- Import / continuity entry surfaces: OpenAI / ChatGPT export import, Task
  Prompt Archive, owner-scoped retry / recovery behavior already
  implemented, and account export / restore to the exact extent supported
  by the existing contract and implementation. Not every historical
  corpus, provider export format, or migration shape is claimed.
- Repository intelligence on the supported local single-user path:
  repository candidate discovery, explicit repository import,
  account / Project `RepositoryBinding`, direct Project-bound repository
  search, and ordinary-chat repository search exposure only when
  Guardian resolves exactly one valid active binding and existing
  authority checks pass. Remote / multi-user / Hosted-Room repository
  authority remains outside this bounded Beta claim.
- Bounded Guardian tool execution: read-only health capability, and
  bounded Project repository search where current eligibility /
  authority checks pass. Advertised-subset authority, Guardian-owned
  execution authority, exact capability eligibility, bounded command
  count, and provider capability checks are preserved. Arbitrary tools,
  arbitrary write operations, and generic shell / filesystem execution
  are not promoted.
- MCP / extensibility: the public MCP extension posture may be described as
  part of Beta only as a bounded extension interface. A general plugin
  marketplace, plugin SDK internals as public Beta API, and arbitrary
  plugin execution bypassing Guardian policy are not claimed.
- Desktop / Tauri client (if current `main` still contains the functioning
  local desktop / Tauri presentation layer): Beta Bounded / Conditional
  when used as a client of the same supported local Guardian node. Not a
  packaged production desktop distribution, not auto-update support, not
  an independent desktop persistence / runtime authority, not a separate
  release topology not currently proven.

### Internal

The following remain explicitly internal, not user-facing release promises:

- direct Command Bus HTTP / control-plane API
- plugin SDK internals
- generic tools / API tools surfaces currently marked internal or
  quarantined
- developer-only diagnostics
- unsafe operator mutation surfaces
- implementation / control-plane mechanisms that support Beta behavior
  without being user-facing promises
- Pi 0.82.1 wrapper/API, source-vendor, identity, framing, and telemetry
  surfaces (per the "Current supported reality" / "Not yet true" sections
  above; non-inference / OAuth-readiness qualification; not a
  user-facing release promise at the current `main` tip).
- CE-L1 wiring (lives in code paths and is required to close active
  blockers, but remains internal / qualification pending — see below).
- Campaign / coding-worker substrate (operational substrate that supports
  Beta behavior; not a user-facing release promise).

Implementation presence of Pi, CE-L1, or coding-worker wiring does not
promote those surfaces to Beta Supported merely because their code paths
exist.

### Qualification Pending

Intended or plausible Beta surface with implementation present, but a
specifically named proof / authority / operational gate remains open.
Each entry below names its explicit `remaining gate` rather than only
saying "not supported," per the ADR-069 Qualification-Pending Doctrine.

- **Coding Loop** — `remaining gate` requires: live provider/model
  execution, terminal durable result, and source-thread readback on the
  claimed supported profile. CE-L1 wiring remains internal / qualification
  pending; no `LIVE_EXECUTOR_PROVEN_CANONICAL` is emitted by this section.
- **Hosted Rooms** — `remaining gate` requires: clean supported / tester
  startup and owner / guest live semantic proof after migration repair.
- **DeepSeek / private-preview provider lane** — `remaining gate` requires
  required credentials, authenticated provider-specific persisted runtime
  proof, and explicit supported-profile promotion.
- **Browser side-panel / Browser Host release surface** — `remaining gate`
  follows whichever current host / auth / release proof remains open on the
  current `main` tip after the present private-preview gates.
- **Any desktop packaging behavior not covered by the bounded local-client
  claim** in the Beta Bounded / Conditional section above.

### Out of Beta

The following are explicitly excluded from the present Beta promise under
ADR-069 and are not classified as qualification-pending; they are
intentionally out of scope:

- TTS / voice — Out of Beta
- federation — Out of Beta
- unrestricted autonomous / recursive agent execution
- arbitrary write-capability tool use
- generic shell / filesystem execution through ordinary Beta chat
- public Command Bus exposure
- generic cron / unattended automation
- generic connectors without separate qualification
- graph-write / Neo4j-derived-write behavior where the supported path
  remains flagged off or quarantined
- remote / multi-user repository execution not covered by a separately
  accepted authority contract and live proof
