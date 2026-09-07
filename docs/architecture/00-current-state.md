## Purpose

This file is the canonical short-form source of truth for Codexify’s current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated

2026-09-05

## Interpretation rule

This file is authoritative for:

- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase

`main` remains in local-first Beta hardening with a gated private-preview lane. A bounded live private-preview schema upgrade reached repository Alembic head with data-preservation and immediate runtime-read checks passing; the installed scheduled reconciler subsequently passed from its coherent shared-image baseline without recreating healthy long-running containers or changing canonical database state. No Beta support boundary widened.

## What changed recently

- Qualified the private-preview migration lineage on a disposable clone, then upgraded the live database to `b2c8d0e3f5a7` with preservation, worker recovery, no-op, and authenticated read checks passing.
- Proved the installed post-upgrade scheduled reconciler completes against `b2c8d0e3f5a7` from its coherent shared migrator image, while preserving healthy long-running container identities and canonical database state.
- Proved chat-history disappearance is a data-present/API-filter mismatch caused by legacy Project ownership divergence; no canonical chat row loss or runtime database-target drift was found.
- Converged the covered Project and Media runtime authorization paths on
  `projects.user_id`, stopped new description-envelope writes, and added a
  classify-before-mutate migration for matching legacy envelopes. Focused
  helper, route, and migration-unit tests pass; conflicting envelopes fail
  closed.
- Implemented fail-closed reconciliation for legacy
  `projects.user_id == 'local'` rows under ADR-081's exact canonical-thread
  evidence rule. Always-on classification and mutation-order tests pass, but
  this harness could not execute the required disposable-PostgreSQL migration
  proof, so UMS-01 remains open.
- Revisions `c3d9e4f6a8b1` and `d4e8f1a2b6c9` have not been applied to the live
  private-preview database.
- Reconciled the UMS ownership migration lineage behind Persona Studio with
  one Alembic head, `d4e8f1a2b6c9`. Focused migration tests report 15 passed
  and 18 PostgreSQL-dependent skips; ownership regressions report 47 passed.
  See the [UMS-01R reconciliation proof](./proofs/runtime/2026-09-05-ums-project-ownership-lineage-reconciliation-proof.md).
  The checkpoint is:

  ```text
  UMS-01A: IMPLEMENTED
  UMS-01B: IMPLEMENTED
  UMS-01R: CLOSED
  UMS-01Q-R1: CLOSED
  UMS-01Q-R2: CLOSED
  UMS-01Q-R3: CLOSED
  UMS-01Q POSTGRESQL QUALIFICATION: PASSED
  UMS-01 CAMPAIGN GATE: CLOSED
  UMS-01: CLOSED
  UMS-02A STABLE PERSONA SUBJECT CONTRACT: PASSED
  UMS-02B PERSONA SUBJECT LIFECYCLE TOKENS: CLOSED
  UMS-02C PERSONA SUBJECT PERSISTENCE: PASSED
  UMS-02: CLOSED
  UMS-03A CANONICAL MEMORY ENVELOPE CONTRACT: REVERIFIED
  UMS-03A-A MEMORY-SPECIES TOKEN SPELLINGS: CLOSED
  UMS-03B MEMORY ENVELOPE PROTOCOL TOKENS: CLOSED
  UMS-03C CANONICAL MEMORY PERSISTENCE SCHEMA: CLOSED
  UMS-03C-A REVIEW/ACTIVATION ORDERING: CLOSED
  UMS-03C-B PROJECT COMPOSITE OWNERSHIP TARGET: CLOSED
  UMS-03D CANONICAL MEMORY PERSISTENCE: CLOSED
  UMS-03E MEMORY-ENTRY COMPATIBILITY PROJECTION: CLOSED
  UMS-03: OPEN
  UMS-03F: AUTHORIZED TO START
  UMS-04: NOT AUTHORIZED
  ```

- Froze the implementation-ready Persona-subject mapping and enforcement
  contract in [§4.5 of the Unified Memory Store Contract](./unified-memory-store-contract.md),
  including the current Persona-persistence inventory, `ref_kind` mapping,
  subject-creation rule, coalescing categories, binding-history semantics,
  cross-account enforcement mechanism, legacy/ambiguous migration policy,
  and export-shape review. Persona-subject lifecycle vocabulary is now
  canonical: `active | retired`. It is an identity-persistence token domain;
  stable Persona-subject persistence is PostgreSQL-qualified. No users can
  create, bind, retire, retrieve, or manage Persona subjects, and no release
  capability changed. UMS-02 is closed and UMS-03 is authorized to start.
  See the [UMS-02A stable Persona-subject contract proof](./proofs/runtime/2026-09-07-ums02a-stable-persona-subject-contract-proof.md)
  and the [UMS-02C stable Persona-subject persistence proof](./proofs/runtime/2026-09-07-ums02c-persona-subject-persistence-proof.md).
  Two narrow test-harness repairs were required to obtain a faithful
  PostgreSQL proof: an explicit `CAST(:profile_id AS TEXT)` in one JSONB
  fixture helper, and a test-only `_historical_guardian_db` helper that
  mirrors the existing `_PostgresGuardianDB.__new__` pattern used elsewhere
  in the test suite so the historical-revision migration test no longer
  requires current-head schema verification. No production runtime, ORM,
  or migration code was changed by these repairs; the implementation-only
  fingerprint is identical before and after the qualification run.

- Froze the canonical memory envelope and the legacy compatibility-read
  boundary as semantic doctrine in
  [§4.6–§4.15 of the Unified Memory Store Contract](./unified-memory-store-contract.md).
  UMS-03A is documentation-only: no SQL schema, no migration, no ORM
  model, no runtime reader/writer, no retrieval behavior change, and no
  export implementation change. The freeze records the current
  memory-bearing source inventory (`memory_entries`,
  `personal_facts`, `personal_fact_evidence`,
  `personal_fact_revisions`, candidates, verified facts, and the
  external `Memoryos` library state); the canonical envelope semantic
  categories (identity, ownership, scope, semantic species,
  content/payload, Persona attribution, provenance, governance,
  lifecycle, priority/decay control, compatibility); the minimum
  semantic-species taxonomy (episodic/semantic memory, verified
  personal fact, candidate/unreviewed fact); explicit independence of
  ownership, scope, and Persona attribution; explicit independence of
  stored / retrievable / ambient-eligible states; the minimum
  provenance spine; the compatibility-read matrix with explicit
  `not safely mappable` rows; eight fail-closed cases; and the
  deferred physical-design questions. ADR-081, ADR-082, and ADR-084
  remain unchanged; ADR-084 remains controlling. UMS-03 remains
  OPEN, UMS-03B is authorized to start, UMS-04 is NOT AUTHORIZED. No
  Beta/release claim widened; no canonical memory persistence
  implementation exists yet. See the
  [UMS-03A canonical memory envelope contract proof](./proofs/runtime/2026-09-07-ums03a-canonical-memory-envelope-contract-proof.md).
  The committed UMS-03A artifact at
  `12075540e29077a40a7d578eef315bc4277c0841` was independently
  reverified at `09a13039cc6309188d66782f18514cc2856733b3` by a
  second harness against the full UMS-03A acceptance surface
  (38/38 verdicts PASS, including the documentation-gap record that
  ADR-083 is not present in the canonical ADR registry). See the
  [UMS-03A reverification proof](./proofs/runtime/2026-09-07-ums03a-reverification-proof.md).
  UMS-03A was not retroactively edited; the reverification is
  additive evidence only.

- Froze the canonical serialized spellings for the three
  UMS-03A semantic species in
  [§4.8 of the Unified Memory Store Contract](./unified-memory-store-contract.md):

  ```text
  episodic_semantic_memory
  verified_personal_fact
  candidate_unreviewed_fact
  ```

  UMS-03A-A is a documentation-only architecture amendment. The
  three-species taxonomy, every species meaning, the
  review / activation / retrieval / ambient-influence posture, the
  provenance requirements, the mutation / revision semantics, and
  the legacy compatibility mapping remain unchanged. The
  slash-joined human-readable labels (`Episodic / semantic memory`,
  `Candidate / unreviewed fact`) remain a single combined label
  per affected species, not a list of protocol aliases. The
  amendment is purely a serialization-authority clarification:
  the canonical serialized token is the protocol authority;
  human-readable labels are descriptive. No new ADR was created;
  ADR-084 remains controlling. UMS-03B was previously BLOCKED
  because two slash-joined species did not provide unambiguous
  canonical token spellings; UMS-03A-A removes that block. UMS-03
  remains OPEN, UMS-03B is authorized to resume, UMS-03C remains
  NOT AUTHORIZED, UMS-04 remains NOT AUTHORIZED. No
  Beta/release claim widened; no canonical memory persistence
  implementation exists yet. See the
  [UMS-03A-A memory-species token spelling proof](./proofs/runtime/2026-09-07-ums03a-a-memory-species-token-spelling-proof.md).

- Registered the two closed UMS-03A / UMS-03A-A vocabularies as
  canonical protocol tokens in
  [`guardian/protocol_tokens.py`](../../guardian/protocol_tokens.py):

  ```text
  MemorySemanticSpecies:
    episodic_semantic_memory
    verified_personal_fact
    candidate_unreviewed_fact

  MemoryPersonaLinkKind:
    captured_under
    suggested_by
    associated_with
  ```

  UMS-03B is a token-only implementation slice. It added the two
  enum classes plus the `MEMORY_SEMANTIC_SPECIES_VALUES` and
  `MEMORY_PERSONA_LINK_KIND_VALUES` aggregate frozen sets, plus
  two new contract tests in
  [`tests/contracts/test_protocol_tokens.py`](../../tests/contracts/test_protocol_tokens.py)
  (35/35 tests pass). The new tokens are scoped to the protocol
  registry and its tests; no runtime memory consumer, no
  ContextBroker, no retrieval path, no export path, no ORM model,
  and no Alembic migration consume them. The Alembic head
  remains `e5a9c2f7b4d1`. No ADR was created or modified; ADR-084
  remains controlling. UMS-03 remains OPEN, UMS-03C is authorized
  to start, UMS-04 remains NOT AUTHORIZED. No Beta/release claim
  widened; no canonical memory persistence implementation exists
  yet. The Runtime Protocol Token Contract and §4.8.2 of the
  Unified Memory Store Contract record the new registries. See
  the [UMS-03B memory envelope token proof](./proofs/runtime/2026-09-07-ums03b-memory-envelope-token-proof.md).

- Froze the canonical memory persistence schema as DDL-contract
  precision in
  [§4.16 of the Unified Memory Store Contract](./unified-memory-store-contract.md):

  ```text
  memory_records            — canonical envelope row
  memory_persona_links      — typed stable-Persona attribution
  memory_provenance         — first-class durable lineage
  ```

  The schema freezes table identity, column identity, type,
  nullability, defaults, FK authority, uniqueness, token-derived
  CHECK constraints, payload placement, Persona-link structure,
  governance representation (typed `reviewed_at` / `activated_at`
  timestamps plus independent `pinned` / `held` booleans; no
  monolithic lifecycle enum), FK delete behavior, and a
  minimum index strategy. The first migration is explicitly
  additive: the three tables are created empty, no legacy
  backfill is performed, no source row is mutated, and the
  legacy memory / personal-fact stores remain the durable
  authority. Same-account integrity between memory and Project
  scope is DB-enforced by a composite FK
  `(project_id, user_id) → projects(id, user_id)`; same-account
  integrity between memory and Persona attribution is
  DB-enforced by composite FKs plus a
  `CHECK (user_id = persona_user_id)` constraint on
  `memory_persona_links`. UMS-03C introduced no SQL table, no
  ORM model, no Alembic migration, no runtime writer / reader /
  retrieval / export behavior, and no new ADR. The Alembic head
  remains `e5a9c2f7b4d1`. No Beta/release claim widened. UMS-03
  remains OPEN, UMS-03D is authorized to start, UMS-04 remains
  NOT AUTHORIZED. See the
  [UMS-03C schema proof](./proofs/runtime/2026-09-07-ums03c-canonical-memory-persistence-schema-proof.md).

- Clarified the canonical review-before-activation ordering
  in
  [§4.16.2a of the Unified Memory Store Contract](./unified-memory-store-contract.md).
  The new CHECK predicate is

  ```text
  activated_at IS NULL
  OR (
      reviewed_at IS NOT NULL
      AND activated_at >= reviewed_at
  )
  ```

  Review and activation remain distinct governance states,
  but they may share the same recorded timestamp.
  Activation earlier than review is forbidden. The earlier
  UMS-03C prose that claimed "activation is a strictly later
  event than review" and the earlier CHECK
  `NOT (reviewed_at IS NULL AND activated_at IS NOT NULL)`
  were both retracted. UMS-03C-A is documentation-only: no
  SQL table, no ORM model, no Alembic migration, no runtime
  writer / reader / retrieval / export behavior, and no new
  ADR. The Alembic head remains `e5a9c2f7b4d1`. No
  Beta/release claim widened. UMS-03D is now authorized to
  resume; UMS-04 remains NOT AUTHORIZED. See the
  [UMS-03C-A ordering proof](./proofs/runtime/2026-09-07-ums03c-a-review-activation-ordering-proof.md).

- Froze the canonical Project composite ownership target in
  [§4.16.2b of the Unified Memory Store Contract](./unified-memory-store-contract.md):

  ```text
  CONSTRAINT uq_projects_id_user_id
  UNIQUE (id, user_id)
  ```

  The amendment was required because PostgreSQL correctly
  rejected the UMS-03D migration's composite foreign key
  `(project_id, user_id) → projects (id, user_id)` with
  `psycopg.errors.InvalidForeignKey: there is no unique
  constraint matching given keys for referenced table
  "projects"`. The `projects` table's primary key covers
  `id` alone; the only existing unique index is a partial
  `(user_id, system_role) WHERE system_role IS NOT NULL`
  that cannot serve as a composite FK target. The new
  constraint is mathematically non-destructive: because
  `projects.id` is already a primary key, no existing row
  can violate `UNIQUE (id, user_id)`. The amendment
  explicitly authorizes the UMS-03D migration to add the
  constraint in the same additive revision that creates the
  three canonical memory tables, rather than introducing a
  separate prerequisite Alembic revision. UMS-03C-B is
  documentation-only: no SQL was added, no ORM model was
  changed, no Alembic migration was added, no runtime
  writer / reader / retrieval / export behavior was changed,
  and no new ADR was created. The uncommitted UMS-03D WIP
  (models + migration + tests) is preserved by this
  amendment. ADR-081 and ADR-084 remain unchanged; ADR-084
  remains controlling. The Alembic head remains
  `e5a9c2f7b4d1`. No Beta/release claim widened. UMS-03D
  is now authorized to resume; UMS-04 remains NOT
  AUTHORIZED. See the
  [UMS-03C-B project target proof](./proofs/runtime/2026-09-07-ums03c-b-project-composite-ownership-target-proof.md).

- Implemented and PostgreSQL-qualified the canonical UMS
  memory persistence substrate in
  [`guardian/db/models.py`](../../guardian/db/models.py)
  and
  [`guardian/db/migrations/versions/f6b0d3e8c5a2_add_canonical_memory_persistence.py`](../../guardian/db/migrations/versions/f6b0d3e8c5a2_add_canonical_memory_persistence.py),
  with
  [`tests/migration/test_canonical_memory_persistence_migration.py`](../../tests/migration/test_canonical_memory_persistence_migration.py).
  The implementation adds `uq_projects_id_user_id UNIQUE (id,
  user_id)` to the existing `projects` table (UMS-03C-B
  prerequisite) before creating the three canonical memory
  tables. PostgreSQL 17 qualification proved: fresh replay
  reaches `f6b0d3e8c5a2`; repeat upgrade is a no-op;
  focused migration suite passes 17/17 with zero skips;
  generic ORM/Alembic parity passes 1/1 with zero skips;
  adjacent token and Persona-subject regressions pass
  46/46; same-account Project scope is accepted;
  cross-account Project scope is rejected at the composite
  FK; the frozen review/activation six boundary cases all
  behave correctly; provenance is one-to-many and source
  identity lives in typed opaque columns; downgrade
  preserves legacy memory and Project rows byte-for-byte.
  The Alembic head is now `f6b0d3e8c5a2`. Canonical
  tables are not yet runtime read/write authority; legacy
  memory sources remain authoritative. No Beta/release
  claim widened. UMS-03D is now closed; UMS-03E is
  authorized to start; UMS-04 remains NOT AUTHORIZED. See
  the
  [UMS-03D persistence proof](./proofs/runtime/2026-09-07-ums03d-canonical-memory-persistence-proof.md).

- **UMS-03E (memory-entry compatibility projection, just
  closed)**: added the first read-only compatibility
  reader in
  [`guardian/core/memory_compatibility.py`](../../guardian/core/memory_compatibility.py),
  with
  [`tests/core/test_memory_compatibility.py`](../../tests/core/test_memory_compatibility.py).
  The reader projects authoritative legacy
  `memory_entries` rows into the canonical envelope
  shape frozen in UMS-03A §4.13. It does not write
  `memory_records`, `memory_persona_links`, or
  `memory_provenance`; it does not assign a canonical
  durable `memory_id`; it does not invent Project scope;
  it does not invent Persona attribution; it does not
  mutate the legacy source row. The envelope species is
  exactly `episodic_semantic_memory` (canonical
  `MemorySemanticSpecies` token). Provenance is
  preserved as `source_system='codexify'`,
  `source_record_id='memory_entries:<id>'` exactly as
  the §4.13 mapping prescribes. Account authorization
  is enforced by a single SQLAlchemy filter on
  `(id == memory_entry_id AND user_id ==
  authenticated_account_id)`; not-found and not-owned
  are concealed identically per existing repository
  posture. The projection type is intentionally not
  registered in `Base.metadata`; it is a semantic read
  object, not an ORM mirror. Focused tests pass 15/15
  with zero skips; adjacent token and Persona-subject
  regressions pass 46/46. The Alembic head remains
  `f6b0d3e8c5a2`; no migration was added; no
  retrieval / ambient-influence consumer was wired;
  no ContextBroker, MemoryOS, router, worker,
  account-export, personal-fact, candidate-fact, or
  frontend file was changed. Legacy `memory_entries`
  rows remain durable authority; the canonical memory
  tables remain non-authoritative at runtime. No
  Beta/release claim widened. UMS-03E is now closed;
  UMS-03F is authorized to start for the next
  authoritative legacy source family
  (`personal_facts` with `status='verified'` and
  `is_active=true`); UMS-04 remains NOT AUTHORIZED.
  See the
  [UMS-03E compatibility proof](./proofs/runtime/2026-09-07-ums03e-memory-entry-compatibility-proof.md).

- Merged phone sidebar/navigation and composer overflow work with focused frontend coverage; this is UI change evidence, not supported-path browser proof.
- Added a metering/billing foundation design sketch; it is explicitly unimplemented and does not affect release scope.

## Current supported reality

- The named supported install path is local Docker Compose using `v1-local-core-web-mcp` with `LLM_PROVIDER=local`, `CODEXIFY_LOCAL_ONLY_MODE=true`, and `ALLOW_CLOUD_PROVIDERS=false`.
- The intended Beta Supported boundary remains local inference, ordinary chat, durable threads/messages/tasks, upload → embed → readback, workspace-local retrieval, identity/ownership, migrations, and operator diagnostics; this is support doctrine, not current-tip qualification.
- Mainline contains focused project lifecycle, conversation-origin, document-artifact preview, Guardian Chat, account-import, and mobile-shell repairs with targeted coverage; supported-path and authenticated browser proof remain separate gates.
- Valid account-import multipart batches are accepted and durably staged on the server path; the Safari/WebKit envelope failure remains unrepaired.
- Private-preview live migration preservation/readback, Guardian secret rotation, Cloudflare ingress, and private-profile People/Share behavior have bounded evidence; these do not admit guests or widen Beta.
- Pi 0.82.1 wrapper/API, source-vendor, identity, framing, and telemetry changes remain internal, non-inference, or OAuth-readiness qualification.

## Not yet true / do not assume

- Do not assume current-tip Compose health, model inventory, terminal chat, durable assistant readback, retrieval, queue/worker execution, locks, terminal events, or recovery closure.
- Do not treat the private-preview migration and scheduled-recovery proof as a canary or provider/persistence closure: the database and reconciler are coherent at `b2c8d0e3f5a7`, while the remaining preview gates stay open.
- Do not treat focused Project-ownership route/migration-unit proof as live
  private-preview migration application, disposable-PostgreSQL migration-chain
  proof, UMS-01 closure, or supported browser proof.
- Do not treat CE-L1 OAuth readiness, Pi telemetry, wrapper tests, or source-vendor closure as live provider/model execution, coding-loop completion, persisted-result readback, or Beta proof.
- Do not treat private-preview configuration, bounded recovery/ingress receipts, or a live health/read result as an admitted canary; tester isolation, provider, persistence, and observability gates remain open.
- Do not treat Modal or E2B partial conformance as a qualified hosted sandbox, provider-enforced storage/read-only boundary, supported runtime path, or release support.
- Do not infer shipped reality from mutable `latest`, another checkout, local-only artifacts, planning language, or docs alone; realtime delivery, attachments, federation, and cross-node People messaging remain deferred.

## Active blockers

- Fresh supported-Compose closure is missing at the current `main` tip, including health, chat, persistence/readback, retrieval, queue/worker, locks, and terminal events.
- Private-preview provider-specific execution, persistence, observability, tester isolation, and approved non-admin canary gates remain open; the bounded scheduled-recovery gate is now proven.
- Fresh-state Chroma startup/retrieval qualification remains unresolved; Chroma is derived state and no repair or historical restore is proven.
- CE-L1 still lacks live provider/model execution, terminal durable result, and source-thread readback.
- The friends-and-family canary is blocked on approved non-admin testers plus reruns of Access, isolation, provider, persistence, and bounded-observability gates; DeepSeek rotation/requalification remains open.
- Project-ownership disposable-PostgreSQL migration proof, Safari multipart-envelope repair, Watchdog policy/model, immutable image-retention, hosted-sandbox, and recent supported-path browser gates remain unclosed.

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
