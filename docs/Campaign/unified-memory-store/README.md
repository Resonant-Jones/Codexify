# Unified Account-Owned Memory Store Campaign

- Campaign ID: `UMS-001`
- Campaign status: active architecture-impact Campaign
- Architecture status: **FROZEN**
- Runtime status: not implemented; no release claim
- Governing decision: [ADR-084: Unified Account-Owned Memory Store](../../architecture/adr/084-unified-account-owned-memory-store.md)
- Normative contract: [Unified Memory Store Contract](../../architecture/unified-memory-store-contract.md)
- Source evidence: [Source Evidence Appendix](./source-evidence-appendix.md)
- Current release truth: [00 Current State](../../architecture/00-current-state.md)

## Objective

Build one account-owned, Project-scoped, persona-attributed, user-governed
Memory Store that makes it straightforward to:

- tell an agent to remember a complete proposition;
- receive consented automatic memory suggestions;
- inspect, correct, approve, dispute, hold, pin, retire, restore, and purge
  memory after the fact;
- add memories outside chat through the Vault, import, API, and CLI;
- explicitly retrieve any non-purged account record without silently making it
  ambient context;
- preserve Personal Facts as a specialized governed subtype;
- preserve source and persona attribution across recall; and
- export, restore, and permanently erase sovereign memory state.

The Campaign implements this in dependency order. It must never be collapsed
into one issue, one migration, or one Codex task.

## Frozen doctrine

> **Account owns. Project scopes. Persona attributes. User approves. Pinning
> prioritizes. Holding suspends decay. The router widens only on explicit user
> intent. Every borrowed memory keeps its attribution.**

“Account-owned” is semantic. Existing correctly scoped `user_id` columns do not
need cosmetic renaming. Memory authority belongs to the authenticated account
user/principal, never merely to an infrastructure Operator or host.

## Current truth and dependency gates

### Current

- The repository has multiple memory-related implementations rather than one
  canonical user loop.
- Personal Facts have the mature review/evidence/revision safety boundary and
  only verified active facts may enter provider context.
- Existing memory entries use a small `user_id`, silo, content, tags, and pinned
  representation.
- The current MemoryOS retention implementations can evict or prune records and
  do not yet guarantee permanent direct retrievability.
- The active retrieval path treats some imported/pre-Codexify material with a
  ranking penalty rather than a hard context-eligibility barrier.
- Account export currently omits memory entries and Personal Facts.
- Anthropic account import currently handles conversations and deliberately
  excludes Projects and memories.
- `Persona` and `PersonaProfile` are distinct persistence models with different
  ownership semantics.

### Hard gates

1. Project-scoped memory cannot become load-bearing until ADR-081 Project
   ownership runtime/data convergence is proven.
2. Persona-aware memory cannot become load-bearing until stable account-owned
   persona subjects and deterministic bindings exist.
3. New automatic and imported memory writes cannot be enabled until export and
   restore preserve the canonical memory families.
4. Ambient provider context cannot consume unified memory until the computed
   eligibility and recall-grant boundaries are proven.
5. Supported user-facing sovereignty claims cannot ship until permanent purge,
   derived-store cleanup, and re-import resurrection suppression are proven.

### Current UMS-00 checkpoint

```text
UMS-00 DESIGN: FROZEN
UMS-00 VALIDATION: PASSED WITH DOCUMENTED DIAGRAM-FRESHNESS LIMITATION
UMS-00 COMMIT: INCLUDED IN THIS COMMIT
UMS-00 CAMPAIGN GATE: CLOSED
UMS-01: AUTHORIZED TO START
```

`FROZEN` describes the design state, while this checkpoint records the completed
repository transaction. The six-file governance packet is included in this
commit, so UMS-00 is closed and UMS-01 is authorized as the next atomic packet.
That closeout did not itself start or prove UMS-01; the following checkpoint
records the separately authorized UMS-01A execution slice.

### Current UMS-01 checkpoint

```text
UMS-01 PROJECT OWNERSHIP RUNTIME AUTHORITY: PROVEN IN UMS-01A
UMS-01 MATCHING-ENVELOPE MIGRATION: QUALIFIED ON DISPOSABLE POSTGRESQL
UMS-01 LEGACY LOCAL OWNER RECONCILIATION: QUALIFIED ON DISPOSABLE POSTGRESQL
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
UMS-03D CANONICAL MEMORY PERSISTENCE: AUTHORIZED TO RESUME
UMS-03: OPEN
UMS-03E: NOT AUTHORIZED
UMS-04: NOT AUTHORIZED
```

UMS-02A freezes the implementation-ready Persona-subject mapping and
enforcement contract in [§4.5 of the Unified Memory Store Contract](../../architecture/unified-memory-store-contract.md).
The contract records the current Persona-persistence inventory
(`personas`, `persona_profiles`, `persona_profile_revisions`,
`persona_profile_bindings`, and the `chat_threads` profile pin), the
`ref_kind` mapping for `persona` and `persona_profile`, the
subject-creation rule, the four coalescing categories, the
binding-history semantics, the cross-account enforcement mechanism, the
legacy/ambiguous migration policy, and the export-shape review. The
canonical `persona_subjects.lifecycle` token domain is now
`active | retired`. It is identity-persistence vocabulary only: no
Persona-subject table, ORM model, Alembic revision, lifecycle transition,
route, service, memory attribution, export, or restore behavior exists yet.
The UMS-02A qualification receipt records the mapping proof.

UMS-02C introduced `persona_subjects` and `persona_subject_bindings`
ORM schema with a matching Alembic migration
(`d4e8f1a2b6c9 → e5a9c2f7b4d1`), deterministic legacy Persona/Profile
backfill, account-consistency and binding-history enforcement, and
PostgreSQL qualification. The complete disposable-PostgreSQL
qualification is recorded in the
[2026-09-07 UMS-02C persistence proof](../../architecture/proofs/runtime/2026-09-07-ums02c-persona-subject-persistence-proof.md).
Two narrow test-harness repairs were required to obtain a faithful
PostgreSQL proof: explicit `CAST(:profile_id AS TEXT)` in a JSONB
fixture helper, and a test-only `_historical_guardian_db(db_url)`
helper that mirrors the existing `_PostgresGuardianDB.__new__` pattern
already used in `tests/core/test_project_lifecycle.py` and
`tests/core/test_chat_message_provenance_persistence.py` so that the
historical-revision migration test no longer requires current-head
schema verification. No production runtime, ORM, or migration code was
changed by these repairs; the implementation-only fingerprint is
identical before and after the qualification run. ADR-081, ADR-082, and
ADR-084 remain unchanged.

The combined migration suite ran as 10/10 with zero failures and zero
skips; the generic ORM/Alembic parity ran 1/1; the resolver and legacy
Persona regressions ran 17/17; the adjacent export regression ran
27/27; fresh target upgrade reached `e5a9c2f7b4d1`; repeat upgrade was a
no-op; the live PostgreSQL constraint inventory matches the contract.
The disposable PostgreSQL 17 container was destroyed after the proof.
This does not qualify private-preview or production migration
application, and does not widen Beta.

UMS-03A froze the canonical memory envelope and the legacy compatibility-
read boundary as semantic doctrine in
[§4.6–§4.15 of the Unified Memory Store Contract](../../architecture/unified-memory-store-contract.md).
The frozen surface is documented as four self-consistent slices: the
memory-bearing source inventory (current persistence truth), the
canonical envelope semantic categories, the semantic-species taxonomy
(episodic/semantic memory, verified personal fact, candidate/unreviewed
fact), and the compatibility-read matrix for every admitted legacy
source. The contract records that `memory_entries` and `personal_facts`
are currently OMITTED from `account-export.v3`; that
`personal_facts.user_id` does not declare a database-level FK to
`users.id` and UMS-03B must add one; that the external `Memoryos`
library is library-internal and is `not safely mappable` to the
canonical envelope today; and that ownership, scope, and Persona
attribution remain three independent authorities. Activation,
retrieval, and ambient influence are explicitly independent states.
Provenance spine requirements and eight fail-closed cases are
recorded. UMS-03A introduced no SQL schema, no migration, no ORM model,
no runtime reader/writer, no retrieval behavior change, and no export
implementation change. No ADR was created or modified; ADR-084
remains controlling. UMS-04 remains NOT AUTHORIZED.

The committed UMS-03A artifact at `12075540e29077a40a7d578eef315bc4277c0841`
was independently reverified at
`09a13039cc6309188d66782f18514cc2856733b3` by a second harness against the
full UMS-03A acceptance surface (38/38 verdicts PASS, including the
acknowledged documentation gap that ADR-083 is not present in the
canonical ADR registry). The reverification recorded every committed
file as byte-identical to its UMS-03A state, performed
`scripts/validate_docs.py` and `git diff --check HEAD^ HEAD` in a detached
worktree at the exact target commit, and added no other change. The
UMS-03A reverification proof is preserved as historical evidence at
[2026-09-07 UMS-03A reverification proof](../../architecture/proofs/runtime/2026-09-07-ums03a-reverification-proof.md).

UMS-03A-A is a documentation-only contract amendment that froze the
canonical serialized spellings for the three semantic species in
[§4.8 of the Unified Memory Store Contract](../../architecture/unified-memory-store-contract.md):

```text
episodic_semantic_memory
verified_personal_fact
candidate_unreviewed_fact
```

The amendment resolves the slash-joined prose ambiguity
(`Episodic / semantic memory`, `Candidate / unreviewed fact`) without
splitting any species, merging any species, or changing any species
meaning. The human-readable labels remain descriptive and
non-authoritative for serialization. No new ADR was created; ADR-084
remains controlling. No SQL schema, no migration, no ORM model, no
runtime reader/writer, no retrieval behavior, and no export
implementation changed. No release claim widened. UMS-03B was
previously BLOCKED because the two slash-joined species did not
provide unambiguous canonical token spellings; UMS-03A-A removes that
block. The full amendment evidence is at
[2026-09-07 UMS-03A-A spelling proof](../../architecture/proofs/runtime/2026-09-07-ums03a-a-memory-species-token-spelling-proof.md).

UMS-03B registered the two closed vocabularies frozen by UMS-03A
and UMS-03A-A as canonical protocol tokens in
`guardian/protocol_tokens.py`:

- `MemorySemanticSpecies` — the three semantic species
  `episodic_semantic_memory`, `verified_personal_fact`,
  `candidate_unreviewed_fact`.
- `MemoryPersonaLinkKind` — the three Persona-attribution
  relationship kinds `captured_under`, `suggested_by`,
  `associated_with` (already frozen by UMS-02A and re-affirmed
  in §4.3 / §4.9 of the contract).

UMS-03B is a token-only implementation slice. It added the two
enum classes plus their `MEMORY_SEMANTIC_SPECIES_VALUES` and
`MEMORY_PERSONA_LINK_KIND_VALUES` aggregate frozen sets in
`guardian/protocol_tokens.py`, registered them in `__all__`,
added two new contract tests in
`tests/contracts/test_protocol_tokens.py` (35/35 tests pass), and
updated [the Runtime Protocol Token Contract](../../architecture/runtime-protocol-token-contract.md)
and [§4.8.2 of the Unified Memory Store Contract](../../architecture/unified-memory-store-contract.md).
UMS-03B introduced no SQL schema, no migration, no ORM model, no
runtime writer, no runtime reader, no retrieval path, and no
export path. No ADR was created or modified; ADR-084 remains
controlling. UMS-03C is now authorized to start; UMS-04 remains
NOT AUTHORIZED. The complete qualification is recorded in the
[2026-09-07 UMS-03B token proof](../../architecture/proofs/runtime/2026-09-07-ums03b-memory-envelope-token-proof.md).

UMS-03C froze the canonical memory persistence schema as
DDL-contract precision in
[§4.16 of the Unified Memory Store Contract](../../architecture/unified-memory-store-contract.md).
The contract defines three new tables:

- `memory_records` — the canonical envelope row, with
  typed columns for identity, account ownership, optional
  Project scope (with a composite FK to `(projects.id,
  projects.user_id)` that DB-enforces same-account
  integrity), semantic species (consuming only the
  `MemorySemanticSpecies` token domain via a CHECK
  constraint), species-appropriate payload columns
  (`text_content` for episodic memory; `fact_key`,
  `fact_value`, `fact_confidence` for personal-fact
  species), governance state (`reviewed_at` and
  `activated_at` timestamps with a `NOT (reviewed_at IS
  NULL AND activated_at IS NOT NULL)` activation-must-
  follow-review CHECK, plus independent `pinned` and
  `held` booleans), and a non-authority `extensions JSONB`.
- `memory_persona_links` — typed stable-Persona
  attribution relationships consuming only the
  `MemoryPersonaLinkKind` token domain, with composite FKs
  to `(memory_records.memory_id, memory_records.user_id)`
  and to `(persona_subjects.persona_subject_id,
  persona_subjects.user_id)`, a `CHECK (user_id =
  persona_user_id)` for same-account enforcement, and a
  `UNIQUE (memory_id, persona_subject_id, link_kind)` per-
  (memory, persona, kind) dedup constraint.
- `memory_provenance` — first-class durable lineage with
  one-to-many multiplicity per memory (preserving
  evidence/revision append-only semantics), closed
  `source_system` and `source_subject_kind` vocabularies,
  and `source_thread_id` / `source_message_id` FKs to
  existing chat tables.

UMS-03C is documentation-only: no SQL table was created,
no ORM model was changed, no Alembic migration was added,
no runtime writer / reader / retrieval / export behavior
was changed, and no new ADR was created. ADR-084 remains
controlling. The first migration is explicitly frozen as
additive only: the three tables are created empty, no
legacy backfill is performed, no source row is mutated,
and the legacy memory / personal-fact stores remain the
durable authority. The runtime cutover to canonical
authority belongs to a later UMS-03 slice and is
explicitly not in UMS-03D. UMS-03D is now authorized to
introduce the schema; UMS-04 remains NOT AUTHORIZED. The
complete freeze evidence is at
[2026-09-07 UMS-03C schema proof](../../architecture/proofs/runtime/2026-09-07-ums03c-canonical-memory-persistence-schema-proof.md).

UMS-03C-A is a documentation-only contract amendment that
clarified the canonical review-before-activation ordering
in [§4.16.2a of the Unified Memory Store Contract](../../architecture/unified-memory-store-contract.md).
The amendment resolves the contradiction the UMS-03D
preflight caught between the frozen §4.16 prose and its
SQL CHECK. The canonical rule is now:

```text
activated_at IS NULL
OR (
    reviewed_at IS NOT NULL
    AND activated_at >= reviewed_at
)
```

Review and activation remain distinct governance states,
but they may share the same recorded timestamp. Activation
is forbidden from being recorded before review, but it is
permitted to be recorded at the same instant as review.
The earlier UMS-03C prose that claimed "activation is a
strictly later event than review" and the earlier CHECK
`NOT (reviewed_at IS NULL AND activated_at IS NOT NULL)`
were both retracted. No ORM model, no Alembic migration,
and no runtime code changed. ADR-084 remains controlling.
The Alembic head remains `e5a9c2f7b4d1`. UMS-03D is now
authorized to resume; UMS-04 remains NOT AUTHORIZED. The
complete amendment evidence is at
[2026-09-07 UMS-03C-A ordering proof](../../architecture/proofs/runtime/2026-09-07-ums03c-a-review-activation-ordering-proof.md).

UMS-03C-B is a documentation-only contract amendment that
froze the canonical enabling Project relational target in
[§4.16.2b of the Unified Memory Store Contract](../../architecture/unified-memory-store-contract.md):

```sql
ALTER TABLE projects
ADD CONSTRAINT uq_projects_id_user_id
UNIQUE (id, user_id);
```

The amendment was required because PostgreSQL correctly
rejected the UMS-03D migration's composite foreign key
`(project_id, user_id) → projects (id, user_id)` with
`psycopg.errors.InvalidForeignKey: there is no unique
constraint matching given keys for referenced table
"projects"`. The `projects` table's primary key covers
`id` alone, and the only existing unique index is a partial
`(user_id, system_role) WHERE system_role IS NOT NULL` that
cannot serve as a composite FK target. The new constraint
is mathematically non-destructive: because `projects.id`
is already a primary key, no existing row can violate
`UNIQUE (id, user_id)`. The amendment explicitly authorizes
the UMS-03D migration to add the constraint in the same
additive revision that creates the three canonical memory
tables, rather than introducing a separate prerequisite
Alembic revision. UMS-03C-B does not change Project
ownership semantics, does not change `projects.id` as the
canonical Project identity, and does not authorize any
Project row mutation. UMS-03D was previously BLOCKED; it
is now AUTHORIZED TO RESUME. The uncommitted UMS-03D WIP
(models + migration + tests) is preserved by this
amendment. ADR-081 and ADR-084 remain controlling. No SQL
was added by this amendment; the constraint will be
implemented by UMS-03D. The Alembic head remains
`e5a9c2f7b4d1` (the untracked `f6b0d3e8c5a2` migration
file is part of the protected UMS-03D WIP, not committed
truth). The complete amendment evidence is at
[2026-09-07 UMS-03C-B project target proof](../../architecture/proofs/runtime/2026-09-07-ums03c-b-project-composite-ownership-target-proof.md).

UMS-01A removes description-envelope authority from the covered Project and
Media runtime paths, stops new envelope writes, and adds a fail-closed
classify-before-mutate cleanup revision. Matching envelopes recover exact human
description text without changing canonical ownership; conflicting envelopes
block direct operations and are suppressed from normal lists. The revision has
not been applied to the live private-preview database. UMS-01B adds a
self-contained successor revision that classifies every legacy
`projects.user_id == 'local'` Project from all canonical referencing threads,
reconciles only one exact non-local canonical owner, preflights built-in role
uniqueness, and aborts before mutation on any unresolved candidate. Its
always-on unit proof and the runtime regressions pass. The complete
 disposable-PostgreSQL qualification is recorded in the
[2026-09-06 qualification proof](../../architecture/proofs/runtime/2026-09-06-project-ownership-postgresql-qualification-proof.md), including clean replay, schema parity, ownership cases, and runtime regressions. No ownership revision was applied to live private preview.

UMS-01R retains the reconciled Persona Studio tail and one Alembic head,
`d4e8f1a2b6c9`; its historical receipt remains the lineage evidence. UMS-01Q
has now passed, closing UMS-01 and authorizing UMS-02. This does not qualify
private-preview or production migration application.

## Workstreams

1. **Authority and identity** — account principal, Project authority, stable
   persona subjects, intent receipts, and recall grants.
2. **Canonical persistence** — shared envelope, ordinary-memory lifecycle,
   Personal Facts specialization, evidence/revisions, and derived activation
   projections.
3. **Portability and erasure** — export/restore, tombstones, purge fan-out, and
   resurrection suppression.
4. **User control** — Memory Vault, explicit commands, review, edit, pin, hold,
   retire, restore, and purge.
5. **Retrieval and context** — computed eligibility, orthogonal Project/persona
   routing, explicit widening, inert evidence, and attribution.
6. **Ingestion** — bounded imports and consent-gated automatic suggestions.
7. **Proof and release** — migration, isolation, runtime, portability,
   injection, recovery, and purge qualification.

## Dependency-ordered task map

The Campaign contains thirteen atomic packets, UMS-00 through UMS-12. Every
task below requires its own work packet, exact target-file discovery,
validation commands, scoped staging, commit, and closeout evidence.

### UMS-00 — Freeze memory governance

- **Lane:** architecture-impact documentation
- **Status:** design frozen, documentation validated, governance packet included
  in this commit, and Campaign gate closed
- **Objective:** freeze ownership, scope, persona attribution, approval,
  subtype authority, recall grants, canonical-versus-derived state,
  portability, consent, and erasure doctrine.
- **Proof:** docs validation, link validation, task-scoped diff, and human
  architecture acceptance.
- **Non-goals:** no schema, API, runtime, UI, queue, import, export, or release
  behavior.

### UMS-01 — Close the Project ownership prerequisite

- **Lane:** architecture-impact persistence and authorization
- **Depends on:** ADR-081
- **Objective:** remove legacy description-envelope authority from Project
  request-time normalization; classify existing rows; preserve human
  descriptions; reconcile only evidence-safe legacy `local` ownership; fail
  closed on conflicts.
- **Acceptance:** every Project authorization read uses `projects.user_id`;
  matching legacy envelopes are safely unwrapped; conflicts are reported and
  not guessed; second-account isolation passes; migration lineage is qualified.
- **Proof:** focused service/route tests, clean and existing database migration
  proof, conflict fixtures, account-isolation tests, and supported deployment
  migration proof where required by current state.
- **Non-goals:** no memory schema or Anthropic Project import.

### UMS-02 — Establish stable persona subjects

- **Lane:** architecture-impact identity persistence
- **Depends on:** UMS-00; Project authority only where a persona is
  Project-scoped
- **Objective:** create stable account-owned persona subjects and explicit
  bindings from existing `Persona` and `PersonaProfile` records.
- **Acceptance:** profile replacement does not change subject identity;
  cross-account bindings are impossible; ambiguous legacy mappings fail closed;
  name snapshots remain non-authoritative.
- **Proof:** migration tests, account-isolation tests, replacement/versioning
  tests, ambiguous-mapping fixtures, export-shape review.
- **Non-goals:** no memory links or persona-owned memory.

### UMS-03 — Add canonical memory storage and compatibility reads

- **Lane:** architecture-impact persistence
- **Depends on:** UMS-01 and UMS-02
- **Objective:** add the shared memory envelope, ordinary-memory review and
  lifecycle authority, evidence/revisions, typed persona links, intent
  receipts, source-entity map, consent state, purge tombstones, and derived
  activation projection.
- **Acceptance:** existing memory entries and Personal Facts backfill without
  changing approval; Personal Facts retain one review/activation authority;
  account mismatches fail closed; all constraints use canonical tokens; legacy
  reads can run through a normalized compatibility view.
- **Proof:** Alembic single-head check, clean upgrade, existing-data upgrade,
  downgrade or explicit non-downgrade policy, idempotent backfill, account
  isolation, transaction rollback, and shadow-read comparison.
- **Non-goals:** no new user writes, ambient recall, imports, or classifier.

### UMS-04 — Make memory portable before adding ingestion

- **Lane:** architecture-impact export/restore
- **Depends on:** UMS-03
- **Objective:** remove memory and Personal Facts from omitted export families
  and preserve all canonical memory state, provenance, persona identity,
  consent, source maps, and purge suppression.
- **Acceptance:** export never queries another user's boundary; repeated restore
  is idempotent; restored dormant/rejected state remains excluded; incompatible
  heat projection is safely discarded; purge tombstones still suppress the same
  source atoms after restore.
- **Proof:** export → restore → export semantic-equivalence tests, multi-account
  isolation, corrupted/missing payload failures, stable-ID/remap receipts, and
  a real Postgres round trip.
- **Non-goals:** no imported-memory or classifier enablement.

### UMS-05 — Add the Memory Vault

- **Lane:** architecture-impact backend and frontend
- **Depends on:** UMS-03 and UMS-04
- **Objective:** expose unified account-memory inspection and direct
  user-authoritative governance.
- **Acceptance:** the account user can filter by Project, persona, review,
  lifecycle, kind, provenance, posture, hold, and priority; inspect evidence and
  revisions; edit with optimistic versions; approve/dispute/reject; pin/hold;
  retire/restore; and see automatic-capture consent and pending-review posture.
- **Proof:** service/route authorization tests, frontend interaction and
  accessibility tests, second-account privacy-oracle tests, revision/conflict
  tests, responsive browser proof.
- **Non-goals:** no model-mediated commands or purge release claim.

### UMS-06 — Add explicit memory commands

- **Lane:** architecture-impact intent and mutation
- **Depends on:** UMS-03 through UMS-05
- **Objective:** implement `memory.remember`, exact-target preview,
  user-confirmed update, and user-confirmed retirement using server-created
  intent receipts.
- **Acceptance:** complete “remember that” statements can become approved;
  ambiguous “remember this” never commits without exact preview; model-proposed
  update/retire cannot mutate without matching user intent; every semantic
  change produces a revision.
- **Proof:** Turn Intake fixtures, tool authorization tests, replay/expiry tests,
  assistant/web/tool injection fixtures, and provider-payload inspection.
- **Non-goals:** no automatic classifier or broad recall.

### UMS-07 — Enforce persona-aware recall grants

- **Lane:** architecture-impact retrieval and context
- **Depends on:** UMS-02, UMS-03, and UMS-06
- **Objective:** implement computed eligibility, server-issued
  `MemoryRecallGrant`, orthogonal Project/persona routing, inert evidence
  rendering, and source attribution.
- **Acceptance:** ordinary recall excludes other-persona-only records; explicit
  shared/named-persona recall widens only within the grant; direct recall never
  activates records; forged/broadened grants fail; diagnostics report scope and
  suppression without content.
- **Proof:** full retrieval matrix, cross-account and cross-persona negative
  tests, prompt-injection fixtures, exact provider-context snapshots, and
  attribution response tests.
- **Non-goals:** no import or automatic suggestion enablement.

### UMS-08 — Add bounded Anthropic Project and memory imports

- **Lane:** architecture-impact import and persistence
- **Depends on:** UMS-01 through UMS-04 and UMS-07
- **Objective:** keep conversation, Project/document, and memory adapters
  separately authorized while sharing import-job provenance and source-entity
  mapping.
- **Acceptance:** source Project UUIDs map to canonical Projects;
  `project_memories` resolve through that map; only real orphans use Imports;
  memory starts dormant and `explicit_recall_only`; Personal Facts remain
  candidates; purge tombstones suppress re-import; replay is idempotent.
- **Proof:** fixture matrix for complete, orphaned, repeated, conflicting,
  malformed, injection-shaped, and previously purged exports; queue retry and
  dead-letter tests; export/restore after import.
- **Non-goals:** no automatic approval or one parser with unrelated write
  authority.

### UMS-09 — Add consent-gated automatic suggestions

- **Lane:** architecture-impact event, queue, classifier, and user consent
- **Depends on:** UMS-03 through UMS-07
- **Objective:** offer automatic suggestions in onboarding, enqueue only after
  recorded consent, and create pending candidates through a local,
  failure-isolated classifier.
- **Acceptance:** unset/paused/declined consent produces no classifier job;
  enabled consent uses an account/message/classifier-version idempotency key;
  retries do not duplicate candidates; chat persists through classifier
  failure; sensitive inference remains separately blocked; Guardian reminders
  receive metadata only.
- **Proof:** consent state-transition tests, queue/replay/backpressure tests,
  local-only/no-cloud-fallback tests, classifier fixtures, reminder
  rate-limit/snooze tests, and logs proving no content leakage.
- **Non-goals:** no automatic activation or approval.

### UMS-10 — Replace destructive heat behavior with projection

- **Lane:** architecture-impact retention and retrieval
- **Depends on:** UMS-03 and UMS-07
- **Objective:** make heat, counters, and vector ranking derived while lifecycle
  transitions remain canonical and non-destructive.
- **Acceptance:** capacity pressure cannot delete canonical memory; projection
  loss/rebuild changes rank only; pin does not block decay; hold does; dormant
  and retired non-purged records remain explicitly retrievable.
- **Proof:** deterministic heat tests, projection rebuild, cache/index-loss
  recovery, hold/pin matrix, concurrency tests, and direct-recall regression.
- **Non-goals:** no purge through retention policy.

### UMS-11 — Implement audited permanent erasure

- **Lane:** architecture-impact privacy and destructive lifecycle
- **Depends on:** UMS-03 through UMS-10
- **Objective:** provide explicit permanent purge across canonical and derived
  state, retain only minimum non-content suppression tombstones, and prevent
  import resurrection.
- **Acceptance:** exact-target confirmation is required; canonical content,
  evidence, content-bearing revisions, vectors, caches, projections, and queued
  payloads are removed or cryptographically destroyed; retries are idempotent;
  tombstones contain no content; normal re-import suppresses the atom; explicit
  user reintroduction is separately audited and restores origin-appropriate
  posture.
- **Proof:** purge fan-out and retry tests, database/index/queue inspection,
  tombstone content audit, export/restore suppression test, and repeated
  OpenAI/Anthropic re-import tests.
- **Non-goals:** no unverifiable claim of immediate deletion from external
  backups.

### UMS-12 — Qualify the supported user-facing feature

- **Lane:** proof and release
- **Depends on:** every prior task
- **Objective:** prove the complete governed loop on the supported local
  profile before changing release truth.
- **Acceptance:** explicit write, consented suggestion, review, edit, persona
  recall, direct dormant recall, import, export/restore, hold/decay, retirement,
  and purge all pass with account isolation and truthful failure receipts.
- **Proof:** current-main supported Compose, authenticated browser workflow,
  Postgres persistence/readback, queue/worker terminal evidence, provider
  context inspection, export/restore archive validation, purge fan-out, and
  current-state update only after all gates pass.
- **Non-goals:** no federation or cross-node memory sync.

## Stop conditions

Pause the affected task and require architecture review if:

- Personal Facts gain a second writable review or activation authority;
- an infrastructure Operator is used as user-memory authority;
- Project scope becomes load-bearing before ADR-081 convergence;
- persona links target only mutable `PersonaProfile` configuration;
- a model can manufacture recall scope, approval, update, retirement, or purge
  authority;
- pending, imported, rejected, disputed, or quarantined content enters ambient
  context through ranking instead of policy;
- automatic candidate collection runs before recorded user consent;
- new ingestion is enabled before export/restore proof;
- heat, capacity, or retention deletes canonical content;
- a purge leaves retrievable content or re-import silently resurrects it;
- a task combines unrelated Campaign phases or claims release support from docs
  or code-path evidence alone; or
- exact lineage, migration, account isolation, or proof requirements cannot be
  established.

## Global proof matrix

| Invariant | Minimum proof |
| --- | --- |
| Account ownership | two-account route, repository, retrieval, export, restore, and purge isolation |
| Personal Facts single authority | transaction and mismatch tests across shared metadata and fact lifecycle |
| Project scope | ADR-081 convergence plus Project authorization tests |
| Stable persona attribution | profile replacement and ambiguous-binding tests |
| Explicit approval | origin-sensitive write and edit matrix |
| Recall widening | forged/expired/replayed/broadened grant negatives |
| Inert evidence | provider-context injection fixtures and tool/mutation denial |
| Consent | no enqueue before affirmative recorded choice |
| Portability | export → restore → export semantic equivalence |
| Non-destructive decay | projection rebuild and direct dormant/retired recall |
| Permanent erasure | canonical/derived purge fan-out plus resurrection suppression |
| Release truth | supported-path runtime and browser proof at exact current main |

## Campaign non-goals

- No bulk implementation in a single task.
- No cosmetic mass rename from `user_id` to `account_id`.
- No persona-owned memory silo.
- No flattening Personal Facts into generic content rows.
- No cloud classifier fallback in the first supported local path.
- No automatic deep or sensitive identity inference.
- No federation, CRDT, cross-node sync, or remote multi-writer conflict policy.
- No current-state or Beta claim until UMS-12 passes.
