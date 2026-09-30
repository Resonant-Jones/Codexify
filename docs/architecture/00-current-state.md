## Purpose

This file is the canonical short-form source of truth for Codexify’s current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated

2026-09-14

## Interpretation rule

This file is authoritative for:

- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase

`main` remains in local-first Beta hardening with a gated private-preview lane. A bounded `b2c8d0e3f5a7` live schema upgrade and scheduled reconciliation proved preservation, immediate reads, and coherent shared-image recovery without recreating healthy long-running containers or changing canonical database state. The private-preview database subsequently reached the Persona head `d4e0f2a5b7c9` with original-column preservation and canonical no-op proof, but the matching application deployment is blocked by Chroma initialization and remains stopped pending live named-volume adoption/recovery and deployment qualification. Recent mainline work also added bounded deadline/lock implementation (ADR-087), closed UMS-04 canonical memory export/restore, and improved bounded Persona Profile, sharing, and worker-diagnosis seams. No new release-ready runtime path or wider Beta support boundary was established; Private Preview application runtime recovery remains unproven.

## What changed recently

- ADR-087 implementation landed on `main` for acceptance-time deadline snapshots and deadline-aware turn-lock renewal; provider/worker/tool/PostgreSQL enforcement, finite drain, and runtime proof remain open.
- Persona/turn-lock recovery fixture alignment and DLG verification-ancestry checks landed; these are test/provenance maintenance and do not widen release support.
- The Atlas architecture-map prototype landed on `main`; it remains a prototype surface, not a supported release path.

- [ADR-067 private-preview Chroma topology](./adr/067-operator-approved-derived-chroma-retirement.md) is implemented and contract-test proven in the private-preview Compose overlay: one explicit Docker-managed local named volume, `codexify_private_preview_chroma`, external to Compose lifecycle and shared at `/app/.chroma` by the six accepted consumers with `nocopy`. The diagnosed host bind is absent from their rendered private-preview topology. Live volume creation/adoption, retirement/fresh initialization, retrieval/reindex proof, matching Persona deployment, authenticated route/browser save/readback, and reconciliation restoration remain pending. Historical preservation remains separate. This is repository/static proof only and changes no Beta/release claim.

- [Persona SQLite host-storage diagnosis](./proofs/runtime/2026-09-07-persona-private-preview-sqlite-host-storage-diagnosis.md) classifies `DOCKER_HOST_BIND_SQLITE_IDENTITY_DEFECT`: the exact runtime fails the first SQLite insert with `SQLITE_READONLY_DBMOVED` across the worktree bind, an outside-worktree bind on the same APFS mount, and a separate APFS mount. Prior named-volume/internal controls succeed. The storage topology is now implemented and statically proven, but ADR-067 recovery remains blocked pending its separately authorized ordered live proof; no retirement, runtime recovery, or Persona qualification is claimed.

- [Persona Chroma named-volume comparison](./proofs/runtime/2026-09-07-persona-private-preview-chroma-named-volume-comparison.md) proves `PERSISTED_CHROMA_STORE_COMPATIBILITY_BOUNDARY`: both disposable named volumes passed SQLite qualification; the exact failed image initialized empty Chroma but reproduced the historical Rust panic on the byte-identical preserved copy. Canonical and preservation bytes remain unchanged. ADR-067 recovery requires separate authorization; backend remains stopped and deployment/browser proof remains pending.

- [Persona Chroma empty-control qualification](./proofs/runtime/2026-09-06-persona-private-preview-chroma-empty-control-diagnosis.md) establishes `EMPTY_CONTROL_HARNESS_PERMISSION_DEFECT`: the reproduced host bind passes ordinary writes but fails stdlib SQLite with `SQLITE_READONLY_DBMOVED` (1032); container-internal and named-volume controls pass SQLite and first-call Chroma initialization. A corrected preserved-copy comparison remains pending. No canonical retirement, application restart, or recovery is proven.

- [Persona deployment attempt 2](./proofs/runtime/2026-09-06-persona-private-preview-lineage-proof-r2.md) is BLOCKED: the matching backend failed startup with `pyo3_runtime.PanicException` in Chroma initialization. The startup migrator exited 0 and the database remains at `d4e0f2a5b7c9`. The restarting backend was stopped; frontend/origin/workers never reached running state. PostgreSQL, Redis, and Neo4j remain available, the rollback checkpoint is intact, and stack reconciliation remains suspended. Live Persona route and browser proof remain pending; no release claim advances.

- [Persona private-preview live upgrade](./proofs/runtime/2026-09-06-persona-private-preview-live-migration-proof.md) proved the authorized upgrade to `d4e0f2a5b7c9` after a fresh external checkpoint. All 111 pre-existing tables / 5,595 rows retained original-column digests; the second canonical migrator run was a no-op. PostgreSQL remains running, old application services remain stopped, stack reconciliation remains unloaded, and the tunnel agent and desired-up marker remain intact. Matching Persona application deployment and authenticated browser save/readback are pending.

- [Persona private-preview clone migration rehearsal](./proofs/runtime/2026-09-06-persona-private-preview-migration-rehearsal-proof.md) proved `b2c8d0e3f5a7 → c3d9e1f4a6b8 → d4e0f2a5b7c9` compatibility using the canonical Persona-branch migrator on an isolated restored snapshot. All 111 pre-existing tables retained row counts and original-column digests. That prerequisite is closed; no release claim advances.

- Repository-level private-preview Persona Profile admission is proven: `v1-whooshd-deepseek-web` adds only `persona_profiles` to enabled routes. Three focused profile/router/auth cases prove mounting, rejection of anonymous/static-key/unapproved sessions, approved-session account scope, and explicit flag disablement; all seven private-preview Compose contract cases pass with the hermetic harness. This admits the existing authenticated create/list/read/update API under ADR-082 without changing manifest, revision, binding, provider, service, or runtime implementation semantics. It is bounded tester exposure, not broader Beta support.

- Persona Studio saved state now depends on backend-confirmed canonical V1 manifests and server revisions. Full authored manifest hydration/writes, update/create failure preservation, offline draft recovery without saved authority, and edits surviving delayed acknowledgements are covered by focused store/page tests. localStorage remains draft/cache continuity only; it does not restore revision authority. This is frontend state/component proof with mocked API responses, not live runtime qualification. Persona bindings, thread pins, capability enforcement, backend semantics, and release/support boundaries are unchanged.

- Added the internal authenticated `GET /api/system_prompt/inspect` signal and migrated the Settings `SystemPromptInspector` to consume it as its sole backend read: canonical thread profile ID/revision/source observation, active Imprint metadata, independent system-document counts, legacy-free inspection-builder measurements, and per-layer failure states now remain visible through the existing read-only UI. Focused frontend tests prove one canonical request, state-preserving normalization, revisionless profiles, partial layer unavailability, and request-level retry behavior. This is not supported-profile exposure, live-browser qualification, or release support.

- Removed frontend clients and controls for the retired Persona mutation endpoint: Settings no longer edits or syncs legacy Persona prompt text, and obsolete Persona panels/hooks are deleted. Unrelated local preview fields and Imprint proposal/accept/reject remain unchanged; retained status consumers observe legacy Persona state read-only. No replacement API or local Persona authority was introduced. Legacy Persona storage/status observation and canonical Persona Studio adoption remain unfinished; the Settings Inspector migration is bounded to the canonical read-only projection and does not widen release/support claims.

- Retired `POST /api/imprint/persona` and its backend mutation implementation, with no replacement or compatibility write shim. The Imprint router has no Persona mutation handler. Focused backend tests prove the retired path returns 404 without changing existing legacy Persona fields or creating rows; `/api/imprint/accept` remains Imprint-only and `/api/imprint/status` retains read-only legacy observation. Frontend callers and obsolete editing controls are now removed. Legacy storage/resolution, canonical Persona semantics, Guardian identity, and prompt assembly are unchanged; no release/support claim widens.

- Closed Imprint acceptance-to-Persona coupling: `/api/imprint/accept` activates only the owned Imprint, rejects Persona override input with HTTP 400, and returns only Imprint state. Settings Imprint Review reflects this contract. Focused tests prove activation, unchanged legacy Persona fields, no new Persona row, and preserved scope protections; canonical Persona revisions, bindings, selections, snapshots, Guardian identity, and prompt order remain unchanged. Legacy Persona storage/status observation and canonical Persona Studio adoption remain unresolved; this is bounded test/code evidence, not a release-support claim.

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
  evidence rule. Always-on classification and mutation-order tests passed; the
  initial harness could not execute the required disposable-PostgreSQL migration
  proof, so UMS-01 remained open at that checkpoint. The later
  [UMS-01Q PostgreSQL qualification](./proofs/runtime/2026-09-06-project-ownership-postgresql-qualification-proof.md)
  closed that proof gap with zero skips.
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
  UMS-03F VERIFIED PERSONAL-FACT COMPATIBILITY: CLOSED
  UMS-03G CANDIDATE PERSONAL-FACT COMPATIBILITY: CLOSED
  UMS-03H-R RECONCILED-MAIN REBASELINE: CLOSED
  UMS-03H LEGACY MEMORY COMPATIBILITY COVERAGE: CLOSED
  UMS-03I UNIFIED COMPATIBILITY READ SURFACE: CLOSED

  UMS-03 CANONICAL MEMORY STORAGE + COMPATIBILITY READS: CLOSED

  UMS-04 EXPORT / RESTORE BEFORE INGESTION: CLOSED
  UMS-04A CANONICAL MEMORY EXPORT / RESTORE CONTRACT: CLOSED
  UMS-04B-PG DISPOSABLE POSTGRESQL TEST AUTHORITY: CLOSED
  UMS-04B CANONICAL MEMORY EXPORT SERIALIZATION: CLOSED
  UMS-04C CANONICAL MEMORY RESTORE RECONSTRUCTION: CLOSED
  UMS-04D FULL EXPORT → CLEAN RESTORE → SECOND-RESTORE QUALIFICATION:
    CLOSED

  UMS-05 MEMORY VAULT: OPEN
  UMS-05A MEMORY VAULT OPERATOR CONTRACT: CLOSED
  UMS-05B VAULT BACKEND READ PROJECTION: CLOSED
  UMS-05C VAULT DIRECT HUMAN MUTATION SERVICE: OPEN
  UMS-05C1 PIN/UNPIN MUTATION SPINE: CLOSED
  UMS-05C2 VAULT PIN MUTATION API: CLOSED
  UMS-05C3 VAULT HOLD/RELEASE-HOLD MUTATION: CLOSED
  UMS-05C4 PROJECT-SCOPE MUTATION: CLOSED
  UMS-05C5 PERSONA ATTRIBUTION MUTATION: CLOSED
  UMS-05C6 DIRECT USER-AUTHORED VAULT CREATION: CLOSED
  UMS-05C7 REMAINING MUTATION AUTHORITY REVALIDATION: CLOSED
  UMS-05C8 ORDINARY MEMORY REVIEW AND LIFECYCLE STATE PERSISTENCE: CLOSED
  UMS-05C8-Q GOVERNANCE-STATE MIGRATION QUALIFICATION: CLOSED
  UMS-05C9 ORDINARY MEMORY CONTENT REVISION PERSISTENCE + UMS-04 PORTABILITY: CLOSED
  UMS-05C9-W ORDINARY MEMORY CONTENT CORRECTION WRITER: CLOSED
  UMS-05C10A-R REVIEW-TRANSITION HISTORY REVALIDATION: CLOSED
  UMS-05C10A-P REVIEW-TRANSITION REVISION PERSISTENCE
                   + UMS-04 PORTABILITY: CLOSED
  UMS-05C10A-C REVIEW-TRANSITION CONTRACT RESOLUTION: CLOSED
  UMS-05C10A-W ORDINARY MEMORY REVIEW TRANSITION WRITER: CLOSED
  UMS-05C10A: CLOSED
  UMS-05C10B-R ORDINARY MEMORY LIFECYCLE MUTATION
                   AUTHORITY / HISTORY REVALIDATION: CLOSED
  UMS-05C10B-P ORDINARY MEMORY LIFECYCLE-TRANSITION REVISION PERSISTENCE
                   + UMS-04 PORTABILITY: CLOSED
  UMS-05C10B-C ORDINARY MEMORY LIFECYCLE TRANSITION
                   CONTRACT RESOLUTION: CLOSED
  UMS-05C10B-W ORDINARY MEMORY RETIRE / RESTORE WRITER: CLOSED
  UMS-05C10B: CLOSED
  UMS-05C10: CLOSED
  UMS-05C11+: NOT AUTHORIZED
  NEXT ACTION: CAMPAIGN REVALIDATION REQUIRED
  UMS-05D+: NOT AUTHORIZED

  UMS-06+: NOT AUTHORIZED
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
  (38/38 verdicts PASS, including the then-current documentation-gap
  finding that no ADR-083 document existed; the registry now carries
  the unissued/retired slot's non-authoritative tombstone). See the
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

- **UMS-03F (verified personal-fact compatibility projection,
  just closed)**: added the second read-only compatibility
  reader in
  [`guardian/core/memory_compatibility.py`](../../guardian/core/memory_compatibility.py),
  with
  [`tests/core/test_memory_compatibility.py`](../../tests/core/test_memory_compatibility.py).
  The reader enforces the frozen §4.13 eligibility predicate
  `status='verified' AND is_active=true` in the query itself.
  Candidate / disputed / archived / inactive rows return
  `None` identically to not-found / not-owned. The reader
  reuses the same `MemoryCompatibilityProjection`
  dataclass and populates the verified-fact shape
  (`fact_key`, `fact_value`, `confidence`,
  `last_confirmed_at`, `guardrail_metadata`, full
  `evidence` rows, full `revisions`). The primary (latest)
  evidence's `source_type` / `source_message_id` /
  `evidence_meta` / `modality` / `excerpt` are carried on
  the projection's provenance. Evidence rows whose
  `source_type` is outside the closed vocabulary or whose
  `evidence_meta` is self-referential on the parent fact
  id fail closed. The reader performs no canonical write,
  no personal-fact / evidence / revision mutation, and no
  retrieval integration. Legacy `personal_facts` rows
  remain durable authority; the canonical memory tables
  remain non-authoritative at runtime. Focused
  compatibility tests pass 34/34 (15 UMS-03E + 19
  UMS-03F) with zero skips; adjacent token and
  Persona-subject regressions pass 46/46. The Alembic head
  remains `f6b0d3e8c5a2`; no migration was added; no
  ContextBroker, MemoryOS, router, worker,
  account-export, candidate-fact, or frontend file was
  changed. The candidate / unreviewed fact compatibility
  is not covered by this slice and remains deferred. No
  Beta/release claim widened. UMS-03F is now closed;
  UMS-03G is authorized to start for the next unmapped
  legacy memory-bearing family; UMS-04 remains NOT
  AUTHORIZED. See the
  [UMS-03F verified-fact compatibility proof](./proofs/runtime/2026-09-07-ums03f-verified-personal-fact-compatibility-proof.md).

- **UMS-03G (candidate personal-fact compatibility
  projection, just closed)**: added the third read-only
  compatibility reader in
  [`guardian/core/memory_compatibility.py`](../../guardian/core/memory_compatibility.py),
  with
  [`tests/core/test_memory_compatibility.py`](../../tests/core/test_memory_compatibility.py).
  The reader enforces the frozen §4.13 line 901 /
  §4.10 line 725 eligibility predicate
  `status IN ('candidate', 'disputed', 'archived') OR
  is_active = FALSE` in the query itself. This is the
  natural complement of the UMS-03F verified + active
  predicate; together the two readers cover every
  `personal_facts` row exactly. The reader reuses the
  same `MemoryCompatibilityProjection` dataclass and
  populates the same fact shape and evidence / revision
  lineage as the verified reader, but with
  `semantic_species = candidate_unreviewed_fact` and
  `ambient_eligible = False`. Crucially, an active
  candidate remains pending / unapproved: Personal Fact
  `is_active` is preserved on the source row as the
  lifecycle authority, but it does not upgrade the
  candidate's review posture. Personal Facts remains the
  durable lifecycle authority; the canonical memory tables
  remain non-authoritative. The implementation was
  authorized from the post-disposition governance base
  `a6b6a5e1b4dbe280a60ea39eb540de80000dda78`; both
  intervening commits (`ba318cbb8` ADR-083 allocation
  reconciliation and `a6b6a5e1b` ADR-083 disposition)
  are governance-only and preserve ADR-084 as the
  controlling UMS memory ADR. Focused compatibility tests
  pass 52/52 (15 UMS-03E + 19 UMS-03F + 18 UMS-03G) with
  zero skips; adjacent token and Persona-subject
  regressions pass 46/46. The Alembic head remains
  `f6b0d3e8c5a2`; no migration was added; no
  ContextBroker, MemoryOS, router, worker,
  account-export, or frontend file was changed. No
  Beta/release claim widened. UMS-03G is now closed;
  UMS-03H is authorized to start for the next remaining
  compatibility prerequisite identified from the frozen
  UMS-03A inventory; UMS-04 remains NOT AUTHORIZED. See
  the
  [UMS-03G candidate-fact compatibility proof](./proofs/runtime/2026-09-08-ums03g-candidate-personal-fact-compatibility-proof.md).

- **UMS-03H-R (reconciled-main rebaseline, closed)**
  and **UMS-03H (legacy memory compatibility coverage,
  just closed)**: the local operator intentionally
  reconciled local `main` with `origin/main` after
  UMS-03G, producing 18 intervening commits. UMS-03H-R
  revalidated the UMS campaign against the reconciled
  baseline and proved the post-UMS mainline work is
  orthogonal to UMS authority. The rebaseline verdict
  is `REBASELINED_WITH_ORTHOGONAL_MAINLINE_CHANGES`.
  UMS-03H then proved legacy memory compatibility
  coverage closure against the frozen UMS-03A
  inventory and current reconciled repository truth.
  The final coverage matrix is:

  ```text
  memory_entries                        COVERED
  personal_facts (verified+active)       COVERED
  personal_facts (candidate/disputed/
    archived/inactive)                  COVERED
  personal_fact_evidence                SUBORDINATE_LINEAGE_COVERED
  personal_fact_revisions               SUBORDINATE_LINEAGE_COVERED
  Memoryos library state                EXPLICITLY_EXCLUDED_BY_CONTRACT
  ```

  ```text
  COVERED                          = 3
  SUBORDINATE_LINEAGE_COVERED      = 2
  EXPLICITLY_EXCLUDED_BY_CONTRACT  = 1
  UNMAPPED_BLOCKER                  = 0
  ```

  All three canonical semantic species
  (`episodic_semantic_memory`, `verified_personal_fact`,
  `candidate_unreviewed_fact`) have at least one valid
  legacy compatibility path. The closure verdict is
  `LEGACY_MEMORY_COMPATIBILITY_INVENTORY_CLOSED`. The
  52-test compatibility baseline passes 52/52 with zero
  skips on the reconciled `main`; the 46-test adjacent
  regression set passes 46/46; the Alembic head remains
  `f6b0d3e8c5a2`. No production code, tests, ORM models,
  migrations, retrieval wiring, retention implementation,
  or export/restore behavior was changed by UMS-03H-R
  or UMS-03H. Legacy UMS sources remain durable
  authority; canonical UMS tables remain non-authoritative;
  compatibility projections remain read-only; no live
  compatibility-projection integration exists. No
  Beta/release claim widened. UMS-03I is now authorized
  to introduce one bounded unified compatibility read
  surface that composes the three proven projections;
  UMS-03I is NOT yet authorized to redirect live
  ContextBroker / MemoryOS / completion retrieval;
  UMS-04 remains NOT AUTHORIZED. See the
  [UMS-03H-R rebaseline proof](./proofs/runtime/2026-09-08-ums03h-r-main-reconciliation-rebaseline-proof.md)
  and the
  [UMS-03H compatibility coverage proof](./proofs/runtime/2026-09-08-ums03h-legacy-memory-compatibility-coverage-proof.md).

- **UMS-03I (unified memory compatibility read surface,
  just closed)**: added one explicit unified compatibility
  read surface that composes the three proven
  UMS-03E/F/G adapters without changing their authority
  semantics. The public reader is
  `read_memory_compatibility_projection(session, *,
  authenticated_account_id, source:
  MemoryCompatibilitySourceRef)` in
  [`guardian/core/memory_compatibility.py`](../../guardian/core/memory_compatibility.py).
  The dispatcher uses the source kind explicitly; it does
  not infer kind from identifier shape and does not search
  across legacy tables. The Personal Fact adapter selection
  is derived from the source row's persisted `status` and
  `is_active` columns using the same predicates the
  UMS-03F/G adapters use, so the caller cannot select
  "verified" vs "candidate". The unified output is
  structurally equal to the corresponding direct adapter
  output for every admitted Personal Fact state and for
  every memory entry. The unified surface accepts only
  `memory_entry` and `personal_fact` source kinds;
  evidence, revisions, Memoryos library state, chat
  messages, documents, and canonical-memory source kinds
  are NOT supported and fail closed. The underlying
  per-source adapters remain independently callable. The
  Campaign sequencing principle is preserved: canonical
  storage → compatibility reads → export/restore → only
  then broader ingestion/activation surfaces. Focused
  compatibility tests pass 70/70 (52 UMS-03E/F/G + 18
  UMS-03I) with zero skips; adjacent token and Persona-subject
  regressions pass 46/46. The Alembic head remains
  `f6b0d3e8c5a2`; no migration was added; no ContextBroker,
  MemoryOS, router, worker, account-export, or frontend file
  was changed. No canonical `memory_id` was fabricated. The
  complete UMS-03 closure verdict is
  `UMS03_CANONICAL_STORAGE_AND_COMPATIBILITY_READS_CLOSED`.
  UMS-04 export / restore before ingestion is now
  authorized to start; UMS-05+ remain NOT AUTHORIZED. No
  Beta/release claim widened. See the
  [UMS-03I unified compatibility surface proof](./proofs/runtime/2026-09-08-ums03i-unified-memory-compatibility-read-surface-proof.md).

- **UMS-04A (canonical memory export / restore
  contract, just closed)**: extended the
  [Account Export + Restore Contract](./account-export-restore-contract.md)
  with one normative section covering canonical UMS
  export and restore. The contract freezes: canonical
  UMS export families (`memory_records`,
  `memory_persona_links`, `memory_provenance`); exact
  field coverage per family; stable `memory_id` round-trip
  identity; account-owner remapping through the existing
  account restore owner map (no independent UMS account
  map); Project reference remapping through the existing
  Project identity map (no silent widening to `NULL`);
  stable Persona-subject reconstruction (no PersonaProfile
  substitution, no display-name matching); provenance
  reference behavior (reuse existing thread / message ID
  maps; opaque external IDs remain opaque); restore
  dependency order; legacy + canonical coexistence
  prohibition; compatibility-projection exclusion from
  durable export; semantic and lifecycle preservation (no
  restore-time inference of review, activation, or
  lifecycle state); extension non-authority policy;
  manifest accounting; restore idempotency; conflict and
  fail-closed cases; UMS-04 implementation slicing
  (UMS-04B export serialization, UMS-04C restore
  reconstruction, UMS-04D round-trip qualification); and
  the future round-trip qualification contract. UMS-04A is
  architecture only — no export or restore implementation
  is written in this slice. No production code, tests,
  ORM models, migrations, export/restore implementation,
  retrieval behavior, or runtime authority was changed by
  UMS-04A. The Alembic head remains `f6b0d3e8c5a2`. No
  Beta/release claim widened. UMS-04B canonical memory
  export serialization is now authorized to start;
  UMS-04C and UMS-04D remain NOT AUTHORIZED; UMS-05+
  remain NOT AUTHORIZED. See the
  [UMS-04A canonical memory export / restore contract proof](./proofs/runtime/2026-09-08-ums04a-canonical-memory-export-restore-contract-proof.md).

- **UMS-04B (canonical memory export serialization, just closed)**:
  internal/non-public `account-export.v4` canonical-memory export
  serialization is implemented in `guardian/services/account_export.py`
  and `guardian/core/pgdb.py`, normalized through the repository's
  commit-authoritative pre-commit formatter chain (`psf/black@26.5.1`
  then `pycqa/isort@5.12.0`, with `--profile=black --line-length=88`),
  and requalified against the dedicated PostgreSQL 17 cluster through
  its local Unix socket under trust authentication as
  `codexify_test_runner / postgres` (LOGIN, NOSUPERUSER, CREATEDB).
  The focused UMS-04B module passed `21 passed, 0 skipped, 0 failed`;
  the isolated account-isolation seam passed `1 passed, 0 skipped,
  0 failed`. The default/ordinary account export remains
  `account-export.v3`; no public HTTP v4 selector exists; production
  v4 restore is not implemented; unsupported v4 restore remains
  fail-closed. The v4 stage adds exactly these five
  canonical/supporting families: `persona_subjects`,
  `persona_subject_bindings`, `memory_records`,
  `memory_persona_links`, `memory_provenance`. Deterministic
  serialization, manifest entity counts and integrity coverage,
  pre-ZIP ownership and referential closure validation, and account-
  filtered PostgreSQL reads remain bounded to that internal
  posture. The account-export regression gate passed
  `31 passed, 2 skipped, 0 failed`; the account-restore regression
  gate passed `11 passed, 0 failed`. `py_compile` PASS; Alembic
  reports exactly one head `f6b0d3e8c5a2`; the actual pre-commit
  Black and isort hooks PASS without mutation. The unrelated Pi
  fixture and the unrelated `guardian/watchdog/contracts.py` mypy
  baseline defect remain untouched. UMS-04 remains OPEN; UMS-04C is
  now AUTHORIZED TO START; UMS-04D and UMS-05+ remain NOT
  AUTHORIZED. No broader Beta/release qualification follows from
  UMS-04B; the full export → restore round-trip qualification
  remains incomplete. See the
  [UMS-04B canonical memory export serialization proof](./proofs/runtime/2026-09-12-ums04b-canonical-memory-export-serialization-proof.md).

- **UMS-04C (canonical memory restore reconstruction, just closed)**:
  internal/non-public production `account-export.v4` account-restore
  dispatch is implemented in `guardian/services/account_restore.py`
  and reuses the already-qualified UMS-04C-A preflight and UMS-04C-B
  transactional persistence executor. The production restore flow
  (`AccountRestoreService.restore_from_zip`) consumes the v4
  canonical payload (`persona_subjects`,
  `persona_subject_bindings`, `memory_records`,
  `memory_persona_links`, `memory_provenance`), builds identity
  maps from the regular restore's preserved primary keys, invokes
  `UnifiedMemoryRestorePreflight.plan()` and
  `CanonicalMemoryRestoreExecutor.execute(conn)` inside the same
  production `self.db._connect()` transaction that owns the
  ordinary restore, and either commits the whole restore or rolls
  it back atomically on canonical preflight, conflict, or
  persistence failure. Real PostgreSQL 17.6 qualification
  (`codexify_test_runner / postgres` via dedicated Unix socket
  `/tmp/.s.PGSQL.55432`) proved: clean v4 restore populates all
  five canonical families; identical second v4 restore is
  idempotent (no duplicate canonical rows); semantic canonical
  conflict fails closed with the entire transaction rolled back;
  late canonical persistence failure rolls back the entire
  transaction. The focused UMS restore suite passed
  `48 passed, 0 skipped, 0 failed`; the account-restore route
  regression passed `11 passed, 0 failed`. The account-export
  v4 payload-order authority was extended by exactly one line in
  `guardian/services/account_export.py` (reusing the pre-existing
  `STAGED_MANIFEST_SCHEMA_VERSION` token) — no parallel v4
  authority was introduced, no export serialization semantics
  changed; this is recorded as a procedural execution-boundary
  deviation in the UMS-04C proof receipt. `py_compile` PASS;
  Alembic remains exactly one head `f6b0d3e8c5a2`; no migration
  or ORM change. v3 behavior is preserved (`account-export.v3`
  remains the production default and the supported-schema
  authority is unchanged for it). The unrelated Pi fixture and the
  unrelated `guardian/watchdog/contracts.py` mypy baseline defect
  remain untouched. UMS-04C is now CLOSED; UMS-04D — Full Export →
  Clean Restore → Second-Restore Qualification — is now
  AUTHORIZED; UMS-04 remains OPEN; UMS-05+ remain NOT AUTHORIZED.
  The full export → restore round-trip qualification remains
  incomplete and belongs to UMS-04D. No broader Beta/release
  qualification follows from UMS-04C; no public release or
  general-availability claim widened. See the
  [UMS-04C production v4 account restore proof](./proofs/runtime/2026-09-13-ums04c-production-v4-account-restore-proof.md).

- **UMS-04D (full export → clean restore → second-restore qualification,
  just closed)**:
  production canonical v4 export and restore are now qualified together
  across two physically distinct disposable PostgreSQL databases on the
  dedicated PostgreSQL 17.6 / `/tmp/.s.PGSQL.55432` authority. The
  qualification proves:
  clean-target restore populates all five canonical families from the
  production source archive; an identical second restore of the original
  archive is idempotent; the target's first and second v4 re-export
  canonical payload semantics are equal to the source canonical
  semantics for all five canonical families; stable IDs, account
  ownership, Project scope, stable Persona attribution, Persona binding
  semantics, review/activation/lifecycle, pin/hold, all three Persona
  link kinds, provenance multiplicity (local thread + local message +
  opaque external), and non-empty extension surfaces are preserved.
  Two bounded runtime repairs were authorized by the user mid-task and
  recorded transparently in the proof receipt:
  (1) bind `fetch_account_export_*_for_user` and
  `iter_account_export_payloads_for_user` as instance methods on `PgDB`
  and update `routes/api_exports.py` to pass a `PgDB` instance;
  (2) carry canonical `user_id` through the production `projects` and
  `chat_messages` export SELECTs and restore write columns, with
  per-row `target_user_id` validation that fails closed on ownership
  mismatch before any DB write. `account_export.py` and
  `account_restore.py` remained byte-identical throughout UMS-04D;
  `pgdb.py` mutated under explicit user authorization only. The
  focused UMS-04D qualification (`1 passed, 0 failed, 0 skipped`); the
  UMS-04C regression surface (`48 passed` in
  `test_account_restore_unified_memory.py` + `11 passed` in
  `test_account_restore.py`); the canonical v4 export regression
  (`20 passed` in `test_account_export_unified_memory.py`; one
  pre-existing `test_v4_restore_remains_unsupported` failure is
  orthogonal to UMS-04D and predates the UMS-04C production v4 restore
  becoming supported); the new R2 owner-fidelity regression (`6
  passed` in `test_pgdb_account_export_owner_columns.py`). `py_compile`
  PASS; Alembic remains exactly one head `f6b0d3e8c5a2`; no migration
  or ORM change; v3 behavior preserved. The unrelated Pi fixture and
  the unrelated `guardian/watchdog/contracts.py` mypy baseline defect
  remain untouched. UMS-04 is now CLOSED; UMS-05 Memory Vault is now
  AUTHORIZED; UMS-06+ remain NOT AUTHORIZED. Same-account identity
  restore was exercised; different-account-ID remapping is not claimed.
  No broader Beta/release qualification follows from UMS-04D; no
  public release or general-availability claim widened. See the
  [UMS-04D canonical memory export restore round-trip proof](./proofs/runtime/2026-09-13-ums04d-canonical-memory-export-restore-roundtrip-proof.md).

- **UMS-05A (Memory Vault operator contract, just closed)**:
  the human operator surface over the canonical Unified Memory Store
  is frozen as architecture-only doctrine at
  [./memory-vault-contract.md](./memory-vault-contract.md). The
  contract freezes: the logical item model (every Vault field
  resolves to a named canonical authority); the list / detail
  contract with canonical-only filters and sort; the direct human
  Vault action boundary (create / approve / reject / dispute /
  correct / scope change / Persona link / pin / hold / retire /
  restore), each with a named authority owner and a durable receipt;
  Personal Facts authority remains the sole owner of Personal Facts
  review / activation transitions; the server-side mutation rule
  (`Vault UI → Guardian service → authority validation → canonical
  subtype service → transaction → receipt → readback`, never direct
  UI persistence writes); the read model (canonical + admitted
  compatibility projections, never compatibility→canonical promotion);
  fail-closed cases (wrong account, Project owner mismatch,
  unresolved Persona, missing canonical parent, unsupported subtype,
  invalid lifecycle transition, stale version, Personal Facts
  authority mismatch, deferred UMS-06+ capability); the audit /
  receipt shape; and the capability matrix that names every
  UMS-05 admitted action and every UMS-06+ deferred action. The
  contract explicitly distinguishes the Memory Vault from the
  unrelated `guardian/modules/memory_key_vault.py` / `MemoryKeyVault`
  in-memory summary encryption helper and imposes no rename, removal,
  or wiring of that helper. UMS-05A is docs-only; no Vault runtime,
  API, service, route, repository, migration, or frontend component
  is implemented by this task. UMS-05B (Vault backend read
  projection — account-scoped list, detail, filters, provenance /
  Persona readback; no writes) is now AUTHORIZED; UMS-05C/05D/05E
  remain NOT AUTHORIZED; UMS-06+ remain NOT AUTHORIZED. No broader
  Beta/release qualification follows from UMS-05A; no public
  release or general-availability claim widened. See the
  [Memory Vault operator contract](./memory-vault-contract.md).

- **UMS-05B (Memory Vault backend read surface, just closed)**: the
  qualified read chain — canonical + compatibility persistence →
  `MemoryVaultReadService` (account-scoped list/detail, service-owned
  offset pagination) → authenticated GET-only Memory Vault router — is
  now registered in `guardian_api` through `_include_router` under the
  new route-control label `memory_vault` (feature flag
  `CODEXIFY_ENABLE_MEMORY_VAULT_ROUTES`, `default_enabled=True`,
  `core_surface=False`). `memory_vault` is `internal_only` on
  `v1-local-core-web-mcp`, `v1-friends-family-web`, and
  `v1-whooshd-deepseek-web`; all other supported profiles remain
  quarantined by omission. The three Vault paths are mounted at runtime
  but hidden from public OpenAPI; the feature flag can disable them on
  an admitted profile and cannot override quarantine on an unadmitted
  profile. No Memory Vault frontend exists, no Memory Vault mutation
  exists, no public route promotion occurred, and UMS-06+ remain NOT
  AUTHORIZED. UMS-05B is CLOSED; UMS-05C (Vault direct human mutation
  service) is now AUTHORIZED; UMS-05D+ remain NOT AUTHORIZED. See the
  [UMS-05B read-surface activation proof](./proofs/runtime/2026-09-14-ums05b-memory-vault-read-surface-proof.md).

- **UMS-05C1 (Vault pin/unpin mutation spine, just closed)**: the
  first internal Vault mutation service,
  `guardian/services/memory_vault_mutation.py`, proves account-owned
  canonical pin/unpin through an explicit `memory_records.updated_at`
  compare-and-swap token and one append-only `memory_provenance`
  receipt per changed mutation. `updated_at` is the proven CAS token for
  this seam; the receipt is audit/lineage only and never becomes pin
  authority (`memory_records.pinned` remains the sole pin authority).
  No migration, no revision column, and no mutation-receipt table were
  introduced; existing v4 export/restore portability remains intact. The
  service is not yet exposed by an HTTP mutation route, no frontend
  mutation exists, pinning remains priority-only (no retrieval widening
  or ambient-eligibility mutation), and UMS-06+ remain NOT AUTHORIZED.
  UMS-05C is now OPEN; UMS-05C1 is CLOSED; UMS-05C2 (Vault pin mutation
  API) alone is AUTHORIZED; UMS-05C3+ and UMS-05D+ remain NOT
  AUTHORIZED. See the [UMS-05C1 pin mutation proof](./proofs/runtime/2026-09-14-ums05c1-vault-pin-mutation-proof.md).

- **UMS-05C2 (Vault pin mutation API, just closed)**: the qualified C1
  pin/unpin mutation service is now exposed through one internal-only
  `PATCH /api/memory-vault/items/canonical/{memory_id}/pin` endpoint on
  the existing `memory_vault` router. Stable account authority remains
  `RequestUserScope.account_id`; the request requires a fresh timezone-aware
  `expected_updated_at`; stale writes return an explicit conflict; missing
  and cross-account memory remain opaque; and the C1 service remains the
  mutation authority (no route-level SQL, CAS, receipt, or no-op logic).
  No new persistence or migration was introduced; Memory Vault remains
  internal-only and hidden from public OpenAPI; no frontend mutation
  controls exist. UMS-05C2 is CLOSED; UMS-05C3 (Vault hold/release-hold
  mutation) alone is AUTHORIZED; UMS-05C4+ and UMS-05D+ remain NOT
  AUTHORIZED. See the [UMS-05C2 pin mutation API proof](./proofs/runtime/2026-09-15-ums05c2-vault-pin-mutation-api-proof.md).

- **UMS-05C3 (Vault hold/release-hold mutation, just closed)**: the
  qualified mutation spine now supports canonical
  `PATCH /api/memory-vault/items/canonical/{memory_id}/hold`. `held`
  remains canonical hold authority; holding suspends decay only and has
  no heat/decay/ranking/retrieval side effect. Hold and pin share the
  same record-level `memory_records.updated_at` CAS; cross-action
  stale-write protection is proven (a hold invalidates a stale pin
  intent and vice versa). Changed hold/release actions append one
  existing non-authority Vault provenance receipt (`hold` /
  `release_hold`). Memory Vault remains internal-only; no frontend
  control and no Project/Persona/content/review/create mutation exist.
  UMS-05C3 is CLOSED; UMS-05C4 (Project-scope mutation) alone is
  AUTHORIZED; UMS-05C5+ and UMS-05D+ remain NOT AUTHORIZED. See the
  [UMS-05C3 hold mutation proof](./proofs/runtime/2026-09-15-ums05c3-vault-hold-mutation-proof.md).

- **UMS-05C4 (Vault Project-scope mutation, just closed)**: the
  qualified mutation spine now supports canonical
  `PATCH /api/memory-vault/items/canonical/{memory_id}/project-scope`,
  exposing `MemoryVaultMutationService.set_project_scope`. Project scope
  authority remains `memory_records.project_id`; canonical target Project
  ownership is proven solely from `projects.user_id`; legacy description
  ownership envelopes remain non-authoritative. Missing and foreign-account
  target Projects share a single unavailable posture (404
  `Project not available`); canonically account-owned Projects whose
  legacy envelope conflicts with `projects.user_id` fail closed (409 with
  the existing `project_ownership_authority_conflict` code). Project-scope
  mutation shares the same record-level `memory_records.updated_at` CAS
  with pin and hold; cross-action stale-write protection is proven in
  both directions. Changed mutations append one existing non-authority
  Vault provenance receipt using the frozen `set_project_scope` /
  `clear_project_scope` action labels; receipt payloads carry only
  authoritative Project ID transitions and never memory content, Project
  description, or legacy owner metadata. `project_id=None` is an
  explicit account-scope transition; missing `project_id` in the request
  body is rejected with 422 and is not interpreted as a clear. No
  Project row is mutated, repaired, archived, or restored; no retrieval,
  recall, ambient eligibility, pin, hold, Persona attribution, review, or
  activation side effect is created. Memory Vault remains internal-only
  and hidden from public OpenAPI; no frontend control exists. UMS-05C4
  is CLOSED; UMS-05C5 (Persona attribution mutation) alone is
  AUTHORIZED; UMS-05C6+, UMS-05D+, and UMS-06+ remain NOT AUTHORIZED.
  See the [UMS-05C4 Project-scope mutation proof](./proofs/runtime/2026-09-15-ums05c4-vault-project-scope-mutation-proof.md).

- **UMS-05C5 (Vault Persona attribution mutation, qualified on
  `feature/ums-continued`)**: the qualified mutation spine now supports
  canonical
  `PATCH /api/memory-vault/items/canonical/{memory_id}/persona-attribution`,
  exposing
  `MemoryVaultMutationService.set_persona_attribution(persona_subject_id,
  link_kind, present, ...)`. Stable attribution authority remains
  `persona_subjects.persona_subject_id`; canonical link-kind authority
  remains `MemoryPersonaLinkKind` (`captured_under`, `suggested_by`,
  `associated_with`). Mutable PersonaProfile identity, display names,
  prompts, profile manifests, and bindings are not attribution authority.
  Direct human desired-state mutation is supported: `present=True` adds
  one exact typed link for an active same-account subject;
  `present=False` removes one exact typed link whether the subject is
  active or retired; existing exact link to a retired subject remains as
  a fresh-CAS no-op rather than being silently pruned. Missing and
  foreign-account Persona subjects share a single unavailable posture
  (404 `Persona subject not available`); retired-subject new-attribution
  fails closed (409 `Persona subject is not active for new
  attribution`). Persona-link changes share the same record-level
  `memory_records.updated_at` CAS with pin, hold, and Project scope;
  cross-action stale-write protection is proven in both directions.
  Receipt payloads use the frozen `add_persona_attribution` /
  `remove_persona_attribution` action labels and carry only the
  canonical `link_id` / `persona_subject_id` / `link_kind` transition,
  never display name, PersonaProfile ID, prompt, profile manifest, or
  memory content. Different link kinds for the same subject coexist
  independently; one removal does not affect another. No Persona subject
  row, no Persona binding, and no Persona subject lifecycle is mutated;
  no retrieval / recall / ambient-eligibility / ownership / Project-scope
  / pin / hold / review / activation side effect exists. Memory Vault
  remains internal-only and hidden from public OpenAPI; no frontend
  control exists. This qualification is **branch-local** on
  `feature/ums-continued` and has NOT been merged into the current
  `main`, exposed via Preview, or treated as a release. UMS-05C5 is
  CLOSED on this branch; UMS-05C6 (direct user-authored Vault
  creation) alone is AUTHORIZED; UMS-05C7+, UMS-05D+, and UMS-06+
  remain NOT AUTHORIZED. See the
  [UMS-05C5 Persona-attribution mutation proof](./proofs/runtime/2026-09-22-ums05c5-vault-persona-attribution-mutation-proof.md).

- **UMS-05C6 (Vault direct user-authored creation, qualified on
  `feature/ums-continued`)**: a new dedicated
  `MemoryVaultCreationService` exposes the explicit authenticated
  human canonical-memory authoring authority admitted by the frozen UMS
  contract. The service constructor binds the authenticated account; no
  per-call owner / memory-ID override is permitted. `create_memory`
  accepts only `content` (and optional opaque `request_ref`); all other
  canonical dimensions — semantic species (fixed to
  `episodic_semantic_memory`), Project scope (NULL), Persona links
  (empty), pin/hold (false), review/activation (database-authored
  `reviewed_at`/`activated_at` driven), and server-generated memory ID —
  are owned by the creation service. Each call persists exactly one
  canonical `MemoryRecord` and exactly one initial `MemoryProvenance`
  creation receipt (`source_system=codexify`,
  `source_subject_kind=vault`, `is_imported=false`, action
  `create_memory`, action schema `memory-vault-mutation.v1`) in a
  single PostgreSQL transaction, with receipt payload containing only
  authoritative ID transitions and never the authored content. Forced
  receipt-flush failure rolls back both rows cleanly. The canonical
  readback uses `MemoryVaultReadService`; creation does not duplicate
  read-projection logic. Personal Facts are not created; no model calls,
  summarization, classification, or rewriting occur; ambient eligibility
  is not written. HTTP surface adds exactly `POST
  /api/memory-vault/items` (status 201) reusing the existing items
  path; the Vault router now exposes `GET + POST + PATCH` (no `PUT` or
  `DELETE`); all seven unique path templates remain hidden from public
  OpenAPI, internal-only on admitted profiles, feature-flag-removable,
  and quarantine-outranked. UMS-04 portability round-trip remains green
  with no export/restore implementation change. UMS-05C6 is CLOSED on
  this branch; UMS-05C7 (remaining mutation authority revalidation)
  alone is AUTHORIZED; UMS-05C8+, UMS-05D+, and UMS-06+ remain NOT
  AUTHORIZED. See the
  [UMS-05C6 direct creation proof](./proofs/runtime/2026-09-23-ums05c6-vault-direct-creation-proof.md).

- **UMS-05C7 (Remaining Memory Vault mutation authority revalidation,
  qualified on `feature/ums-continued`)**: documentation-only
  revalidation of the remaining UMS-05C capabilities. The current
  qualified surface covers pin/unpin, hold/release, Project-scope
  mutation, stable Persona attribution, and direct user-authored
  creation. The remaining categories — ordinary-memory content
  correction, ordinary-memory review/approve/reject/dispute, ordinary
  retire/restore, and Personal Facts HTTP-adapter review/lifecycle —
  have been classified. **Ordinary-memory content correction** is
  IMPLEMENTABLE_ON_CURRENT_PERSISTENCE (mutable `text_content` plus
  append-only `memory_provenance` lineage, UMS-04 round-trip proven).
  **Ordinary-memory review and ordinary retire/restore** each
  REQUIRES_CANONICAL_PERSISTENCE_PREREQUISITE: the current
  `memory_records` envelope exposes only `reviewed_at` and
  `activated_at` timestamp columns and a binary read projection
  (`approved`/`pending`, `active`/`inactive`); the contract's
  four-value review vocabulary
  (`pending`/`approved`/`rejected`/`disputed`) and three-value
  lifecycle vocabulary (`active`/`dormant`/`retired`) cannot be
  faithfully represented without new typed columns
  (`review_state`, `lifecycle_state`), corresponding
  `MemoryReviewState`/`MemoryLifecycleState` protocol tokens, and a
  migration that backfills from current timestamps. JSONB
  `extensions` cannot promote to authority. **Personal Facts review
  and lifecycle** DELEGATES_TO_EXISTING_SPECIALIZED_AUTHORITY
  (`PersonalFact.status`, `is_active`, `PersonalFactRevision` already
  exist; `guardian/routes/personal_facts.py` already exposes approve
  /reject/dispute routes). Per the spec's Priority 1 rule — the shared
  canonical persistence prerequisite for review and lifecycle — the
  sole next slice authorized on this branch is **UMS-05C8 Ordinary
  Memory Review and Lifecycle State Persistence**. UMS-05C9+,
  UMS-05D+, and UMS-06+ remain NOT AUTHORIZED. UMS-05C8 must not yet
  implement content correction, review actions, or retire/restore
  mutation services — it is the persistence prerequisite, not a
  mutation writer. This qualification is branch-local on
  `feature/ums-continued` and has NOT been merged into the current
  `main`, exposed via Preview, or treated as a release. See the
  [UMS-05C7 remaining mutation authority revalidation](./proofs/runtime/2026-09-25-ums05c7-remaining-mutation-authority-revalidation.md).

- **UMS-05C8 (Ordinary Memory Review and Lifecycle State Persistence,
  qualified on `feature/ums-continued`)**: the shared persistence
  prerequisite identified by C7 has been materialized. The canonical
  `MemoryReviewState` and `MemoryLifecycleState` enums are now
  registered in `guardian/protocol_tokens.py`. The canonical
  `review_state` and `lifecycle_state` columns have been added to
  `memory_records` with CHECK constraints
  (`memory_records_review_state_check`,
  `memory_records_lifecycle_state_check`); both columns are NOT NULL
  with server defaults (`pending`, `dormant`). The Alembic revision
  `8c2f4a6d9b10` backfilled existing rows from the legacy
  timestamp-only model deterministically without inventing history
  (no row was synthesized as `rejected`, `disputed`, or `retired`).
  The downgrade is fail-closed: it refuses to drop the new columns if
  any row carries a typed state that the legacy timestamp model cannot
  represent. The Memory Vault canonical read projection now derives
  `review_posture` and `lifecycle_posture` from the typed columns;
  `reviewed_at` and `activated_at` are preserved as durable history
  metadata but no longer substitute for posture authority. The C6
  direct-creation service continues to write `approved`/`active` plus
  the original C6 `reviewed_at = activated_at = database-authored now()`
  posture. UMS-04 `account-export.v4` now carries both typed fields;
  the restore path parses and validates them against the canonical
  vocabulary and includes them in identity/conflict comparison.
  Pre-C8 v4 payloads without these fields remain restorable through a
  bounded legacy derivation that NEVER infers `rejected`, `disputed`,
  or `retired`; invalid explicit values fail closed and abort the
  entire restore. Personal Facts retain specialized
  `status`/`is_active` authority; the Vault's Personal Facts posture
  branch still maps to the deprecated `inactive` posture literal
  (Personal Facts are not rewritten as ordinary-memory governance).
  C1–C5 mutation suites (pin/hold/project-scope/persona-attribution)
  remain green at 52 tests with no change to their public contracts;
  C8 added no new mutation methods for the new columns. This
  qualification is branch-local on `feature/ums-continued` and has NOT
  been merged into the current `main`, exposed via Preview, or treated
  as a release. UMS-05C8 is CLOSED on this branch; UMS-05C9 (ordinary
  memory content correction) alone is AUTHORIZED; UMS-05C10+,
  UMS-05D+, and UMS-06+ remain NOT AUTHORIZED. C9 must not yet
  implement review actions or retire/restore services — those slices
  remain blocked on this prerequisite having landed. See the
  [UMS-05C8 ordinary-memory governance persistence proof](./proofs/runtime/2026-09-25-ums05c8-ordinary-memory-governance-persistence-proof.md).

- **UMS-05C7 (Remaining Memory Vault mutation authority revalidation,
  re-run 2026-09-27, qualified on `feature/ums-continued`)**: the
  earlier 2026-09-25 C7 classification is superseded. Ordinary-memory
  `approve`/`reject`/`dispute` and `retire`/`restore` are now
  `CURRENT_PERSISTENCE_SUFFICIENT`, because UMS-05C8 gave
  `memory_records` the typed `review_state`
  (`pending | approved | rejected | disputed`) and `lifecycle_state`
  (`active | dormant | retired`) canonical authority, both NOT NULL,
  CHECK-constrained, and carried by `account-export.v4`. Ordinary-memory
  **content correction** is the one remaining category that is
  `NEW_CANONICAL_PERSISTENCE_REQUIRED`: `memory_provenance` has no
  typed prior-content column (every typed column is source identity),
  and its `extensions` field is explicitly non-authority and may not
  become a content-version store, so prior canonical text is not
  durably recoverable after an in-place correction. The repository
  contains no ordinary-memory revision family — only
  `personal_fact_revisions` (with typed `old_value`/`new_value`) and
  `persona_profile_revisions`. All six Personal Facts mutations are
  `CURRENT_PERSISTENCE_SUFFICIENT_WITH_SPECIALIZED_DELEGATION` against
  the existing `personal_facts.status` / `is_active` /
  `personal_fact_revisions` authority, with no second writable truth.
  The sole authorized successor is therefore **UMS-05C9 Ordinary Memory
  Content Revision Persistence + UMS-04 Portability**, not content
  correction implementation. Review/lifecycle mutation writers stay
  `NOT AUTHORIZED` despite being persistence-sufficient. No runtime,
  schema, route, or token was added by C7. Branch-local only; not merged
  into the current `main`, not deployed, not a release claim. See the
  [UMS-05C7 remaining mutation authority revalidation proof](./proofs/runtime/2026-09-27-ums05c7-remaining-mutation-authority-revalidation-proof.md).

- **UMS-05C8-Q (Memory governance-state migration qualification,
  qualified on `feature/ums-continued`)**: the dedicated PostgreSQL
  qualification that C7 recorded as missing for the C8 governance-state
  seam is now closed. The new
  `tests/migration/test_memory_governance_state_migration.py` proves
  revision `8c2f4a6d9b10` (parent `7e5a5fccf253`) on disposable
  PostgreSQL: clean migration to head; ORM/Alembic parity for
  `memory_records.review_state` and `memory_records.lifecycle_state`
  (both `character varying` NOT NULL, defaults `'pending'` / `'dormant'`,
  constrained by `memory_records_review_state_check` and
  `memory_records_lifecycle_state_check`); a populated pre-C8 upgrade
  proving the exact deterministic backfill (`reviewed_at` NULL →
  `pending`/`dormant`; reviewed-only → `approved`/`dormant`; reviewed +
  activated → `approved`/`active`) with **zero** manufactured
  `rejected`, `disputed`, or `retired` rows; preservation of every field
  C8 does not own including content, `pinned`, `held`, `extensions`,
  timestamps, and provenance; Personal Facts specialized authority left
  untouched and the governance columns proven absent from
  `personal_facts`; all 12 canonical review × lifecycle combinations
  accepted while out-of-vocabulary tokens, `archived`, and `inactive`
  are rejected at the database boundary; and repeatability across two
  independently created disposable databases. C8-Q is proof hardening
  only — it changed no runtime, migration, ORM, route, token, Personal
  Facts, export, restore, or frontend file. Two pre-existing failures
  in `tests/services/test_account_export_unified_memory.py`
  (`test_explicit_v4_serializes_exact_canonical_graph_and_manifest`,
  `test_v4_restore_remains_unsupported`) were captured unchanged as the
  **C9 entry baseline**; neither references the governance columns and
  neither was repaired here. C7's persistence classification remains in
  force. UMS-05C9 (ordinary-memory content revision persistence +
  UMS-04 portability) is the sole next authorized slice; UMS-05C10+
  remain NOT AUTHORIZED. Branch-local only; not merged into the current
  `main`, not deployed, not a release claim. See the
  [UMS-05C8-Q governance-state migration qualification proof](./proofs/runtime/2026-09-27-ums05c8-q-governance-state-migration-qualification-proof.md).

- **UMS-05C9 (Ordinary-memory content revision persistence and
  portability, qualified on `feature/ums-continued`)**: the shared
  persistence prerequisite C7 identified for ordinary-memory content
  correction now exists and is portable. A new canonical
  `memory_revisions` family (Alembic `c3d9f4e6a1b2`, parent
  `8c2f4a6d9b10`, single head) preserves one exact authored-text
  transition per row: server-generated `revision_id`, composite
  `(memory_id, user_id)` FK to `memory_records` with
  `ON DELETE CASCADE`, typed `old_text_content` / `new_text_content`
  text, an explicit per-memory `revision_number` with
  `UNIQUE (memory_id, revision_number)`, and DB-level rejection of
  both a sub-1 sequence number and a byte-identical no-op transition.
  `memory_records.text_content` remains the current content
  authority; `memory_revisions` is append-only canonical history and
  remains strictly separate from `memory_provenance` (source identity
  plus non-authority receipt extensions) and from
  `personal_fact_revisions` (still the specialized Personal Facts
  authority). Migration fabricates **zero** synthetic rows: no
  existing memory is given invented history. Portability required a
  new export schema version rather than widening the existing one:
  `account-export.v5` is the six-family canonical graph
  (`persona_subjects`, `persona_subject_bindings`, `memory_records`,
  `memory_persona_links`, `memory_provenance`, `memory_revisions`),
  while `account-export.v4` keeps its exact five-family meaning and
  its historical `restore_supported: false` posture. v5 restore
  validates revision ownership, ordering, chain continuity, and
  final-content reconciliation against the parent record, and fails
  closed on each; replay is idempotent and semantic conflicts roll
  back. A revision attached to a specialized Personal Facts parent is
  rejected at restore preflight, so C9 did not create a second
  Personal Facts revision authority. C9 also repaired a real
  pre-existing defect: canonical-memory restore trimmed authored
  `text_content`, which silently rewrote user whitespace and made
  revision reconciliation impossible. C9 was persistence and
  portability only; **content correction itself remained unimplemented**
  at the close of C9 and was closed by UMS-05C9-W below. Two known
  explicit-v4 export test failures remain unchanged baseline debt.
  Branch-local only; not merged into the current `main`, not
  deployed, not a release claim. See the
  [UMS-05C9 memory revision portability proof](./proofs/runtime/2026-09-27-ums05c9-memory-revision-portability-proof.md).

- **UMS-05C9-W (Ordinary-memory content correction writer, qualified on
  `feature/ums-continued`)**: authenticated direct correction of
  canonical ordinary episodic memory now exists as
  `MemoryVaultMutationService.correct_content`, exposed internally as
  `PATCH /api/memory-vault/items/canonical/{memory_id}/content`. A
  changed correction atomically produces the new
  `memory_records.text_content`, exactly one append-only
  `memory_revisions` row holding the exact prior and resulting text,
  exactly one existing-format `memory-vault-mutation.v1` receipt, and
  one new database-authored `memory_records.updated_at` CAS token; any
  failure rolls all four back. A byte-identical no-op creates neither a
  revision nor a receipt and leaves the CAS unchanged, while a stale
  token conflicts even when the requested text equals current content.
  Accepted content is never trimmed — blankness is judged on the
  stripped form only, so whitespace, newlines, Unicode, punctuation, and
  casing survive exactly. The existing revision tail is validated for
  contiguity and for reconciliation against canonical content before
  append; malformed history fails closed and is never repaired. The
  receipt references revision identity and number only and never carries
  authored old/new text. Authority stays constructor-bound, only
  `episodic_semantic_memory` is writable, and Personal Facts are refused
  rather than delegated. The route is a thin adapter: no SQL, no
  revision-number calculation, no CAS comparison, no row locking, no
  read-before-write. It is internal-only and hidden from public OpenAPI
  under the existing `memory_vault` profile posture. No migration, no
  schema change, no export-schema change, no retrieval change, no
  frontend, and no release claim expansion. Review/lifecycle writers,
  Personal Fact correction, and any revision browsing or read API remain
  unimplemented. Branch-local only; not merged into the current `main`,
  not deployed, not a release claim. See the
  [UMS-05C9-W memory content correction proof](./proofs/runtime/2026-09-28-ums05c9-w-memory-content-correction-proof.md).

- **UMS-05C10A-R (Ordinary-memory review-transition history authority
  revalidation, qualified on `feature/ums-continued`)**: before any
  approve / reject / dispute writer may exist, the branch-current
  architecture was inspected for whether a `review_state` transition
  needs canonical history beyond current state plus its intent
  receipt. Result: **`REVIEW_HISTORY_NEW_CANONICAL_PERSISTENCE_REQUIRED`**.
  Unified Memory Store contract §3.3 still requires that *every*
  authority-changing transition produce **a revision and an intent
  receipt**, and §5.3 already applies that posture to non-content
  authority changes such as Project scope and Persona attribution.
  C9's `memory_revisions` is defined by §4.16.5 as **content** history
  and does not discharge §3.3 for `review_state` or `lifecycle_state`;
  Personal Facts' generic `personal_fact_revisions` — which records
  review transitions as typed `field_changed` / `old_value` /
  `new_value` — remains the specialized equivalent that ordinary memory
  does not have. `memory_provenance` receipts and their `extensions`
  remain audit/evidence and explicitly non-authority. For the test
  sequence `pending → approved → disputed → approved → rejected`,
  **0 of 5** reconstructable facts (per-transition old state, new
  state, sequence, time, intent identity) are recoverable today. A
  second independent finding: **`TRANSITION_GRAPH: NOT EXPLICIT`** —
  no current contract states which review transitions are legal, and
  §5.3 has no row for approve / reject / dispute, so a writer must not
  invent one. Both findings block the C10A **writer**, which stays
  frozen; the single authorized successor is **UMS-05C10A-P** (ordinary
  review-transition revision persistence + UMS-04 portability, which
  would add a seventh canonical family beyond `account-export.v5`'s
  six). This slice changed documentation only: no runtime, schema,
  migration, export/restore, test, or frontend change, and no release
  claim expansion. A wording divergence between Memory Vault contract
  §5.1 (review rows list a receipt, not a receipt + revision) and
  §3.3 is recorded in the proof as an open documentation inconsistency;
  it was deliberately not repaired here, because choosing between two
  current normative statements is contract resolution, not
  revalidation. Branch-local only; not merged into the current `main`,
  not deployed, not a release claim. See the
  [UMS-05C10A-R review-transition history revalidation proof](./proofs/runtime/2026-09-28-ums05c10a-r-review-transition-history-revalidation-proof.md).

- **UMS-05C10A-P (Ordinary-memory review-transition revision persistence
  and portability, qualified on `feature/ums-continued`)**: the canonical
  persistence UMS-05C10A-R found missing now exists. A new
  `memory_review_revisions` family (Alembic `a7c3e91d4b60`, parent
  `c3d9f4e6a1b2`, single head) records ordinary review-state transitions:
  server-generated `review_revision_id`, composite
  `(memory_id, user_id)` FK to `memory_records` with `ON DELETE CASCADE`,
  typed `old_review_state` / `new_review_state` over
  `pending` / `approved` / `rejected` / `disputed`, an
  `actor_account_id` constrained to the owning account, per-memory
  `revision_number` with `UNIQUE (memory_id, revision_number)`, and
  DB-level rejection of a sub-1 sequence, an unknown token, and a
  no-op transition. Rows are immutable with no `updated_at`. Migration
  fabricates **zero** synthetic history and leaves every existing
  canonical row, content `memory_revisions`, provenance, and Personal
  Facts untouched. Four truth surfaces stay separate: current review
  authority is `memory_records.review_state`, `memory_revisions` is
  content history, `memory_review_revisions` is review-transition
  history, and `memory_provenance` remains intent/source/audit evidence
  with non-authority extensions. **No legal transition graph is
  encoded** — the database accepts any unequal pair of valid review
  tokens, proven by a test that persists `disputed → approved`,
  `approved → rejected`, and `rejected → pending`, the pairs a premature
  policy would likely have forbidden. Persistence capability is not
  mutation authorization. Portability required a new schema rather
  than widening an old one: `account-export.v6` is the seven-family
  canonical graph, while `account-export.v5` keeps its exact six-family
  meaning and a v5 archive is never treated as invalid for lacking
  review history. v6 export fails closed on malformed review history and
  never repairs it, including from provenance extensions; v6 restore
  validates ownership, actor, typed vocabulary, numbering, chain
  continuity, and reconciliation with the parent's current
  `review_state` before any write, persists parent before child in one
  transaction, is idempotent on identical replay, and rolls the whole
  restore back on semantic conflict, sequence-occupancy conflict, or a
  late persistence failure. **No review writer exists** — `approve`,
  `reject`, and `dispute` remain unimplemented, and which transitions
  are legal remains unresolved, so the C10A writer stays frozen. The
  sole next slice is UMS-05C10A-C contract resolution. Documentation
  only beyond the additive schema and export change: no route, service
  method, frontend, retrieval, or release claim change. Branch-local
  only; not merged into the current `main`, not deployed, not a release
  claim. See the
  [UMS-05C10A-P review revision portability proof](./proofs/runtime/2026-09-28-ums05c10a-p-review-revision-portability-proof.md).

- **ADR-088 (Ordinary Memory Review Transition Semantics, accepted on
  `feature/ums-continued`)**: the legal ordinary-memory review transition
  graph is now frozen, closing the `TRANSITION_GRAPH: NOT EXPLICIT` finding
  that UMS-05C10A-R recorded. Aligned with ADR-084 and does not modify or
  supersede it. Exactly three direct review actions exist — `approve`,
  `reject`, `dispute` — with an explicit legal matrix over `pending`,
  `approved`, `rejected`, `disputed`; the only non-transitions are
  same-state requests, which are no-ops after successful CAS validation
  (no review revision, no receipt, no `updated_at` advance) while a stale
  token still conflicts. **No direct action targets `pending`**: a reviewed
  memory is never reset, because `pending` means authoritative review has
  not occurred, and reusing it as a reset would make one token mean both
  never-reviewed and review-invalidated. Review and lifecycle independence
  is explicit — approval does not activate, rejection or dispute does not
  retire, and retire/restore do not change review state — so rejected and
  disputed memory becomes ambient-ineligible without any lifecycle
  mutation. `reviewed_at` is frozen as the timestamp of **first
  authoritative approval** and is preserved on re-approval and never
  cleared; transition timing belongs to
  `memory_review_revisions.created_at`. Every changed transition requires
  one canonical review revision plus one `memory-vault-mutation.v1` intent
  receipt, and neither substitutes for the other. Personal Facts remain
  specialized, suggestions cannot self-approve, and explicit `approved`
  direct creation stays distinct from a review transition. This also
  resolved the Memory Vault contract §5.1 review rows, which previously
  listed a receipt without a revision. **No review writer exists yet** —
  `approve`, `reject`, and `dispute` remain unimplemented — so the sole
  authorized successor is UMS-05C10A-W. Architecture only: no runtime,
  schema, migration, export, test, frontend, retrieval, or release claim
  change. Branch-local only; not merged into the current `main`, not
  deployed, not a release claim. See the
  [UMS-05C10A-C review transition contract proof](./proofs/runtime/2026-09-28-ums05c10a-c-review-transition-contract-proof.md).

- **UMS-05C10A-W (Ordinary-memory review transition writer, qualified on
  `feature/ums-continued`)**: ADR-088's frozen state machine is now
  implemented on the internal Memory Vault surface as
  `MemoryVaultMutationService.transition_review` plus
  `PATCH /api/memory-vault/items/canonical/{memory_id}/review`. Only
  `approve`, `reject`, and `dispute` are admitted, and the request model
  forbids extra fields, so a caller cannot supply a raw `review_state`,
  account, actor, revision, or lifecycle authority — `pending` is
  therefore unreachable as a target. Each **changed** transition commits,
  in one transaction, the `memory_records.review_state` update, the
  `reviewed_at` first-approval update when required, the database-authored
  CAS advance, exactly one `memory_review_revisions` row, and exactly one
  `memory-vault-mutation.v1` intent receipt; any failure rolls all of them
  back. Parent-row `SELECT ... FOR UPDATE` serializes concurrent review
  mutations, and CAS is validated **before** the no-op decision, so a stale
  token conflicts even when the action would otherwise change nothing. A
  same-state action under a fresh token is a no-op: no review revision, no
  receipt, no `updated_at` advance, and no `reviewed_at` backfill. Review
  history is validated for contiguity and for reconciliation with the
  parent's current `review_state` before append, and malformed history
  fails closed rather than being repaired. Review/lifecycle independence
  is preserved: approval does not activate, rejection and dispute do not
  retire, and lifecycle, content, pin, hold, Project, and Persona state are
  unchanged. Qualification confirmed two current-truth gates: direct
  creation already satisfies ADR-088 first-approval semantics by writing
  `review_state="approved"` and `reviewed_at=now()` together, and ambient
  eligibility is computed at read time with no stored or indexed
  derivative, so no review change can leave stale authoritative retrieval
  state. The route is a thin adapter performing no SQL, locking, CAS
  comparison, no-op decision, revision numbering, or `reviewed_at`
  decision, and remains internal-only and hidden from public OpenAPI
  under the existing `memory_vault` posture. No schema, migration,
  export/restore, frontend, retrieval, or release-claim change. **No
  lifecycle writer exists**, and the sole next Campaign slice is
  UMS-05C10B-R lifecycle mutation authority / history revalidation.
  Branch-local only; not merged into the current `main`, not deployed, not
  a release claim. See the
  [UMS-05C10A-W review transition writer proof](./proofs/runtime/2026-09-28-ums05c10a-w-review-transition-writer-proof.md).

- **UMS-05C10B-R (Ordinary-memory lifecycle authority and history
  revalidation, qualified on `feature/ums-continued`)**: lifecycle
  mutation remains unimplemented, and the revalidation found the
  prerequisite that blocks it. Result:
  `LIFECYCLE_HISTORY_NEW_CANONICAL_PERSISTENCE_REQUIRED` with
  `LIFECYCLE_TRANSITION_GRAPH: PARTIAL`. `memory_records.lifecycle_state`
  is confirmed as the sole present lifecycle authority over `active`,
  `dormant`, `retired`, and it is never mutated by any current
  canonical code path. Unified Memory Store contract §3.3 requires a
  revision and an intent receipt for every authority-changing
  transition, and that requirement has not been narrowed to
  receipt-only for lifecycle. No canonical family can record
  lifecycle transitions: `memory_revisions` is content history,
  `memory_review_revisions` is review-transition history, so neither
  is semantically applicable, and provenance remains non-authority.
  The load-bearing finding is the **restore posture**: §5.4 requires
  restore to return a retired record to its *pre-retirement governed
  posture*, but no field records it, so `active → retired → restore`
  and `dormant → retired → restore` are indistinguishable in current
  storage and the contractual rule is not implementable as written.
  Two related contract-ahead-of-implementation gaps were recorded
  without contradiction: §4.4 calls `dormant_at` / `retired_at`
  canonical and §10 requires lifecycle transition timestamps in the
  archive, yet neither column exists and `account-export.v6` carries
  no lifecycle transition timestamp. Of seven historical facts in a
  sample lifecycle sequence, **0 of 7** are reconstructable. The
  transition graph is partial: `active → dormant` is explicit
  governed policy forbidden while held, import creates `dormant` as
  an ingress state, and retire/restore carry account-principal
  authority — but retire source-state legality, the restore target
  set, same-state behavior, and any `dormant → active` reactivation
  edge are unresolved and were not invented. Review state *is*
  answerable through retire/restore, since it is independent
  present-state authority. Documentation only: no runtime, schema,
  migration, export/restore, frontend, retrieval, or release-claim
  change, and no ADR. The sole authorized successor is UMS-05C10B-P
  lifecycle-transition revision persistence plus UMS-04
  portability; the C10B writer stays frozen. Branch-local only; not
  merged into the current `main`, not deployed, not a release claim.
  See the
  [UMS-05C10B-R lifecycle authority/history revalidation proof](./proofs/runtime/2026-09-29-ums05c10b-r-lifecycle-authority-history-revalidation-proof.md).

- **UMS-05C10B-P (Ordinary-memory lifecycle-transition history
  persistence and portability, qualified on `feature/ums-continued`)**:
  the canonical persistence UMS-05C10B-R found missing now exists. A
  new `memory_lifecycle_revisions` family (Alembic `b8e2f4a6c901`,
  parent `a7c3e91d4b60`, single head) records ordered ordinary
  lifecycle-state transitions: server-generated
  `lifecycle_revision_id`, composite `(memory_id, user_id)` FK to
  `memory_records` with `ON DELETE CASCADE`, typed
  `old_lifecycle_state` / `new_lifecycle_state` over `active` /
  `dormant` / `retired`, per-memory `revision_number` with
  `UNIQUE (memory_id, revision_number)`, and an immutable
  `created_at` with no `updated_at`. The family deliberately carries
  **no** actor, reason, request reference, action, or extensions:
  those are intent/source evidence and belong to the receipt layer,
  and duplicating them would make revision authority a second
  evidence store. Migration fabricates **zero** synthetic history —
  a legacy `retired` record whose prior posture was never recorded
  is left zero-history rather than guessed. The load-bearing
  obligation is now met: **`active -> retired` preserves
  `old_lifecycle_state = active` and `dormant -> retired` preserves
  `dormant`**, proven at the DB, export, and restore layers, so the
  two retirement postures the restore contract must distinguish can
  no longer collapse. No parallel `pre_retirement_state` column was
  added; history itself carries the fact. **No legal transition
  graph is encoded**: the database accepts any unequal pair of valid
  lifecycle tokens — a dedicated test persists all six, explicitly
  stating that persistence representability is not runtime
  authorization. Portability required a new schema rather than
  widening an old one: `account-export.v7` is the eight-family
  canonical graph while `account-export.v6` keeps its exact
  seven-family meaning, and the global export default was
  deliberately not advanced. A currently-`retired` memory with no
  history stays exportable and restorable as zero-history; nothing
  is fabricated. Qualification also found and fixed a real executor
  defect: a sequence-occupancy scan gated on "a planned ID already
  exists" let a wholly new stable ID occupy a taken
  `(memory_id, revision_number)` slot and surface as a raw database
  constraint error instead of a clean conflict. **No retire, restore,
  activate, reactivate, or decay writer exists** — transition
  legality remains unresolved, so the C10B writer stays frozen and
  the sole next slice is UMS-05C10B-C contract resolution. No
  frontend, retrieval, or release-claim change. Branch-local only;
  not merged into the current `main`, not deployed, not a release
  claim. See the
  [UMS-05C10B-P lifecycle revision portability proof](./proofs/runtime/2026-09-29-ums05c10b-p-lifecycle-revision-portability-proof.md).

- **ADR-089 (Ordinary Memory Lifecycle Transition Semantics, accepted on
  `feature/ums-continued`)**: the ordinary-memory lifecycle state machine is
  now frozen, closing the `LIFECYCLE_TRANSITION_GRAPH: PARTIAL` finding
  UMS-05C10B-R recorded. Aligned with ADR-084; neither ADR-084 nor ADR-088 is
  modified or superseded. The Memory Vault lifecycle writer will expose
  **exactly two** generic direct actions, `retire` and `restore` — no generic
  `activate`, `reactivate`, or `set_lifecycle_state`. Retire is legal from both
  `active` and `dormant`, each recording its exact old state; retire on
  `retired` is a no-op. Restore is **not** "set active": it returns the record
  to its canonical pre-retirement `active`/`dormant` posture recovered from
  `memory_lifecycle_revisions`, so `active → retired → restore → active` and
  `dormant → retired → restore → dormant` stay distinct and neither is
  normalized. A currently retired record with no reconstructable history —
  including a legacy row C10B-P deliberately left zero-history — **fails
  closed**; posture is never guessed or inferred from provenance, timestamps,
  heat, review, hold, or pin. Restore against a current `active`/`dormant`
  record is an already-satisfied no-op, which makes direct actions retry-safe
  without creating a generic activation authority. CAS on
  `memory_records.updated_at` is validated **before** any no-op decision, so a
  stale token conflicts even on a same-state action. Neither action touches
  review state, hold, or pin: hold blocks governed automatic decay only and
  never an explicit user action, and restore never clears hold. Automatic decay
  (`active → dormant`, forbidden while held) remains a **separate** authority
  the direct writer does not own, and automatic `dormant → active` reactivation
  is deliberately not established — derived ranking must never become canonical
  lifecycle mutation. Dormant ingress is initialization, not a transition, so
  no history is fabricated. This also reconciled the Memory Vault contract's
  §5.1 retire/restore rows, which had promised only a receipt and diverged from
  the normative revision-plus-receipt rule. **No retire, restore, activation,
  or decay writer exists yet**; the Memory Vault remains internal-only.
  Architecture only: no runtime, schema, migration, export/restore, frontend,
  retrieval, or release-claim change. The sole next slice is UMS-05C10B-W.
  Branch-local only; not merged into the current `main`, not deployed, not a
  release claim. See the
  [UMS-05C10B-C lifecycle transition contract proof](./proofs/runtime/2026-09-29-ums05c10b-c-lifecycle-transition-contract-proof.md).

- **UMS-05C10B-W (Ordinary-memory retire / restore writer, qualified on
  `feature/ums-continued`)**: ADR-089's frozen lifecycle state machine is
  now implemented internally as
  `MemoryVaultMutationService.transition_lifecycle` plus
  `PATCH /api/memory-vault/items/canonical/{memory_id}/lifecycle`. The
  action vocabulary is exactly `retire` and `restore`; the service exposes
  no `set_lifecycle_state`, `activate`, or `reactivate`, and the request
  model forbids extra fields, so a raw lifecycle target cannot be
  submitted by a client. Restore is **not** set-active: it recovers the
  pre-retirement posture from the canonical lifecycle-history tail, so
  `active → retired → restore → active` and
  `dormant → retired → restore → dormant` stay distinct and neither is
  normalized, and a repeated cycle uses the *immediate* tail rather than
  the first retirement ever recorded. A retired record whose
  pre-retirement posture cannot be proven — including the legacy
  zero-history rows C10B-P deliberately created, and gapped, chained-
  broken, or tail-divergent history — **fails closed**; posture is never
  guessed and provenance extensions and derived state are never consulted
  as authority. CAS on `memory_records.updated_at` is validated before any
  no-op decision, so a stale token conflicts even when the action is
  already satisfied; a fresh no-op creates no revision, no receipt, and
  no CAS advance. Each changed transition commits the state update, the
  CAS advance, exactly one `memory_lifecycle_revisions` row, and exactly
  one `memory-vault-mutation.v1` receipt in one transaction, with
  parent-row `SELECT ... FOR UPDATE` serializing concurrent mutations so
  two transitions cannot claim the same revision number. Review state
  (all four states), hold, pin, content, Project scope, Persona
  attribution, and both other revision families are preserved unchanged;
  `memory_records` has no context-posture column on this branch, which is
  recorded rather than invented. Qualification found and fixed a defect
  introduced in this slice: a stray `@dataclass(slots=True)` decorator
  misattached to a new exception class, turning it into a dataclass and
  surfacing as a route `500`; it was caught by the route suite before
  commit. **Automatic decay remains a separate, unimplemented authority**
  and no automatic `dormant → active` behavior was introduced; the
  direct service is not called from any background decay path. The route
  is internal-only and hidden from public OpenAPI, and the control-plane
  delta is exactly +1 PATCH method and +1 path template. No schema,
  migration, export/restore, frontend, retrieval, or release-claim
  change. This closes **C10B and C10**; C11+ remains deliberately
  unauthorized pending Campaign revalidation against the UMS baseline
  and stop rule. Branch-local only; not merged into the current `main`,
  not deployed, not a release claim. See the
  [UMS-05C10B-W lifecycle transition writer proof](./proofs/runtime/2026-09-29-ums05c10b-w-lifecycle-transition-writer-proof.md).

- Accepted ADR-058 separating canonical Persona Profile authored authority from Imprint relational/presentation ownership; legacy Persona observation/status and canonical Persona Studio adoption remain unfinished. The Settings Inspector now observes the canonical read-only projection without changing those ownership boundaries, and no Beta/support claim changed.
- Merged phone sidebar/navigation and composer overflow work with focused frontend coverage; this is UI change evidence, not supported-path browser proof.
- Added a metering/billing foundation design sketch; it is explicitly unimplemented and does not affect release scope.
- Persona Profile authority, account-scoped persistence, export coverage, acceptance-time snapshots, and five-field runtime application landed with focused tests; broad Studio controls remain outside runtime enforcement.
- ShareSheet async handling now rejects stale search/send completions and surfaces relationship-load failure with retry coverage.
- A proof-only Tester worker lineage bridge confirmed that the historical bind/import race still applies to `main`; the fail-closed readiness predicate and fresh Tester runtime proof remain absent.
- Pi’s Anthropic coding default was reconciled to `claude-sonnet-4-6` with contract/proof coverage; this remains internal coding-worker qualification.
- Private-preview migration/recovery evidence and one-slot local chat-worker admission remain bounded prerequisites, not provider or persistence closure.

## Current supported reality

- The named supported install path is local Docker Compose using `v1-local-core-web-mcp` with `LLM_PROVIDER=local`, `CODEXIFY_LOCAL_ONLY_MODE=true`, and `ALLOW_CLOUD_PROVIDERS=false`.
- The intended Beta Supported boundary remains local inference, ordinary chat, durable threads/messages/tasks, upload → embed → readback, workspace-local retrieval, identity/ownership, migrations, and operator diagnostics; this is support doctrine, not current-tip qualification.
- Mainline has focused coverage for project lifecycle, conversation origin, document artifacts, Guardian Chat, account import, mobile shell, Persona Profile, and ShareSheet paths; supported-path and authenticated browser proof remain separate gates.
- Persona Studio persistence is account-scoped and runtime-active only through the current five-field projection; broad voice, tools, permissions, retrieval, and connector fields remain inert or local.
- Valid account-import multipart batches are accepted and durably staged on the server path; the Safari/WebKit envelope failure remains unrepaired.
- Private-preview live migration preservation/readback, scheduled reconciliation, Guardian secret rotation, Cloudflare ingress, and private-profile People/Share behavior have bounded evidence; these do not admit guests or widen Beta.
- Pi 0.82.1 wrapper/API, source-vendor, identity, framing, and telemetry changes remain internal, non-inference, or OAuth-readiness qualification.

## Not yet true / do not assume

- Do not treat merged ADR-087 acceptance-time fields and lock renewal as end-to-end deadline enforcement, graceful stop, finite drain, or provider/tool cancellation proof.

- Persona Profile deployed lineage is not yet proven, and authenticated Persona Studio browser save/backend readback is not yet proven. Repository/profile admission and focused tests do not establish that the running private-preview deployment contains this Persona branch/profile. Qualify the deployed lineage and `/api/persona-profiles` route before resuming live browser authority proof.

- Do not assume current-tip Compose health, model inventory, terminal chat, durable assistant readback, retrieval, queue/worker execution, locks, terminal events, or recovery closure.
- Do not treat the `b2c8d0e3f5a7` private-preview migration and scheduled-recovery proof, or the later `d4e0f2a5b7c9` Persona migration, as a canary or provider/persistence closure. The matching Persona application remains stopped after Chroma initialization failure, and all remaining preview gates stay open.
- Do not treat the Tester lineage bridge as a startup repair or fresh runtime qualification; no current bind-readiness predicate has landed.
- Do not treat private-preview admission serialization, migration/recovery, or health/read results as live provider, persistence, observability, isolation, or canary proof.
- Do not treat repository and disposable-PostgreSQL Project-ownership qualification as live private-preview application of revisions `c3d9e4f6a8b1` and `d4e8f1a2b6c9`, or as supported browser proof.
- Do not treat Persona Profile persistence, acceptance snapshots, ADR-082, or focused UI tests as broad configuration enforcement or browser proof.
- Do not treat CE-L1 OAuth readiness, Pi telemetry, wrapper tests, source-vendor closure, Chroma state, Atlas prototype work, hosted-sandbox partial conformance, or Watchdog contracts as live provider/model execution, coding-loop completion, persisted-result readback, or release-supported behavior.
- Do not treat Modal or E2B partial conformance as a qualified hosted sandbox, provider-enforced storage/read-only boundary, supported runtime path, or release support.
- Do not infer shipped reality from mutable `latest`, another checkout, local-only artifacts, planning language, or docs alone; realtime delivery, attachments, federation, and cross-node People messaging remain deferred.

## Active blockers

- ADR-087 graceful operator shutdown remains blocked pending end-to-end worker, provider streaming, child execution, PostgreSQL persistence/cleanup, turn-lock, and finite-drain enforcement plus runtime proof.

- Fresh supported-Compose closure is missing at the current `main` tip, including health, chat, persistence/readback, retrieval, queue/worker, locks, and terminal events.
- The Tester worker bind-readiness repair and fresh isolated runtime proof remain open; the historical diagnosis is applicable but static.
- Private-preview provider-specific execution, persistence, observability, tester isolation, and approved non-admin canary gates remain open; the bounded scheduled-recovery gate is now proven.
- Fresh-state Chroma startup/retrieval qualification remains unresolved; Chroma is derived state and no repair or historical restore is proven.
- CE-L1 still lacks live provider/model execution, terminal durable result, and source-thread readback.
- The friends-and-family canary is blocked on approved non-admin testers plus reruns of Access, isolation, provider, persistence, and bounded-observability gates; DeepSeek rotation/requalification remains open.
- Live private-preview application of Project-ownership revisions `c3d9e4f6a8b1` and `d4e8f1a2b6c9`, Safari multipart-envelope repair, authenticated browser gates, Watchdog policy/model, immutable image retention, and hosted-sandbox qualification remain unclosed.

## This week’s priorities

1. Land the bounded fail-closed Tester bind-readiness predicate, then run fresh isolated Tester proof.
2. Rerun current-main supported-Compose closure with the canonical local profile across health, chat, persistence/readback, retrieval, queue/worker, locks, and events; requalify Chroma.
3. Complete ADR-087 enforcement and qualify finite drain, graceful stop, late-result handling, and durable terminal truth.
4. Resume Private Preview qualification at queue/worker safe-start and multiprocess named-volume Chroma use, then prove authenticated persistence and isolation.
5. Requalify CE-L1/provider live execution/readback, browser/import, connector, Watchdog, retention, and hosted-sandbox gates; rotate/requalify the private-preview DeepSeek credential before tester execution.

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
/ do not assume" and "Active blockers" sections above continue to bound what
is provably green on the current `main` tip. Implementation presence in a
code path does not promote a capability to Beta Supported; only the
architecture-accepted support envelope under ADR-069 does.

### Beta Bounded / Conditional

Surfaces intentionally inside the Beta envelope but only under an explicit
authority, topology, provider, mode, or capability boundary. The
classification below is the current accepted one; no new bounded surface
is added by this section.

- Persona Studio: account-scoped profile creation / editing, persistence,
  selection, and application of the currently implemented five-field
  runtime projection to ordinary chat. TTS / voice execution, unsupported
  permission authoring, unsupported retrieval-policy execution, and
  "preview UI equals enforcement" claims are excluded from this
  promotion.
- Import / continuity entry surfaces: OpenAI / ChatGPT export import,
  Task Prompt Archive, owner-scoped retry / recovery behavior already
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
  pending; no `LIVE_EXECUTOR_PROVEN_CANONICAL` is emitted.
- **Hosted Rooms** — `remaining gate` requires: clean supported / tester
  startup and owner / guest live semantic proof after migration repair.
- **DeepSeek / private-preview provider lane** — `remaining gate` requires:
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
- graph-write / Neo4j-derived-write behavior where the supported path remains
  flagged off or quarantined
- remote / multi-user repository execution not covered by a separately
  accepted authority contract and live proof

## Release definition right now

- [x] Supported local Compose path, local-only defaults, and Beta boundary are defined on `main`.
- [x] Internal, bounded/conditional, qualification-pending, and Out-of-Beta surfaces remain separate from Beta Supported claims.
- [x] Private-preview migration preservation/readback and ingress proofs are bounded without guest admission or release widening.
- [ ] Current-tip Compose proves healthy startup, model inventory, terminal chat, persistence/readback, and retrieval.
- [ ] Queue, worker, deadline, graceful-stop, lock, migration, configuration, recovery, browser, and account-import claimed-path evidence gates are green.
- [ ] Every claimed preview/provider lane has current-main proof for live execution, durable readback, isolation, and scheduled recovery where applicable.

## How to read the rest of the KB

- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence/invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
