# UMS-03A Canonical Memory Envelope Contract Proof

Date: 2026-09-07

Status: **PASSED — DOCUMENTATION/CONTRACT FREEZE**

## Qualification identity

- Execution lane: Architecture-Impact
- Task kind: docs (contract / inventory proof; no live-runtime qualification)
- Evidence posture: documented contract plus current persistence inventory;
  UMS-01 and UMS-02 are PostgreSQL-qualified prerequisites
- Campaign: Unified Account-Owned Memory Store
- Execution slice: UMS-03A
- Starting HEAD: `716b481f217d51348e6e00af7a3a68bea8b7a440`
- Starting Alembic head: `e5a9c2f7b4d1`
- Prerequisite state:
  - UMS-01: CLOSED
  - UMS-02: CLOSED
  - UMS-03: AUTHORIZED
- This proof does not run a live PostgreSQL qualification. It is a
  contract/inventory freeze. Its evidence is the current persistence
  surface, the frozen doctrine, and the deferred physical-design
  questions.

## Inspected sources

The contract freeze is grounded in the following inspected surfaces,
all read-only:

- `docs/architecture/00-current-state.md` (release truth and current
  blockers)
- `docs/architecture/README.md`
- `docs/architecture/adr/adr-index.md`
- `docs/architecture/adr/081-project-ownership-authority.md`
- `docs/architecture/adr/082-persona-profile-manifest-and-binding-authority.md`
- `docs/architecture/adr/084-unified-account-owned-memory-store.md`
- `docs/architecture/unified-memory-store-contract.md` (this slice
  extends it)
- `docs/Campaign/unified-memory-store/README.md` (extended by this slice)
- `docs/architecture/data-and-storage.md`
- `docs/architecture/account-export-restore-contract.md`
- `docs/architecture/router-decision-table.md`
- `guardian/db/models.py` (the four memory-bearing ORM models:
  `MemoryEntry`, `PersonalFact`, `PersonalFactEvidence`,
  `PersonalFactRevision`)
- `guardian/db/migrations/versions/` (the migration lineage that
  introduced and reconciled each table, including
  `f2b3c4d5e6f8_add_user_id_to_core_entities.py`,
  `a1b2c3d4e5f6_add_temporal_and_personal_facts.py`,
  `b5e6c55f0f0c_postgres_chatlog_only.py`)
- `guardian/core/pgdb.py` (`memory_entries` CRUD paths and the
  `fetch_imported_chatgpt_threads_for_user` provenance filter)
- `guardian/routes/memory.py` (`memory_entries` write authority)
- `guardian/routes/personal_facts.py` (Personal Facts read authority)
- `guardian/services/account_export.py` (the `OMITTED_FAMILIES` list
  that currently excludes memory-bearing families from
  `account-export.v3`)
- `guardian/fact_candidate_pipeline.py` (live-chat candidate creation
  path that writes `PersonalFact` rows with `status='candidate'`)
- `guardian/personal_facts/guardrail_policy.py` (the canonical
  `source_type` enumeration used for evidence)
- `guardian/memoryos/` (the external `Memoryos` library integration;
  treated as read-only inventory; library-internal storage)
- `guardian/context/broker.py` (verified-active Personal Facts
  filtering and `personal_facts_context` assembly)

## ADR note

The task spec names ADR-081, ADR-082, ADR-083, and ADR-084. ADR-083
("MemoryOS") is not present in the current ADR registry — the ADR
index jumps from `082-persona-profile-manifest-and-binding-authority`
to `084-unified-account-owned-memory-store`. There is no ADR file at
`docs/architecture/adr/083-*.md`. This is a documentation gap rather
than an architecture conflict: the only memory architecture ADR is
ADR-084, and `Memoryos` is treated as a read-only library-internal
source in §4.6. UMS-03A does not create or modify an ADR; ADR-084
remains controlling; ADR-081 and ADR-082 remain unchanged.

## Memory-source inventory (current persistence truth, read-only)

The full inventory is recorded in §4.6 of the contract. Summary:

| Family | Account ownership today | Project scope today | Persona attribution today | Lifecycle / status today | Provenance today | Export coverage today |
| --- | --- | --- | --- | --- | --- | --- |
| `memory_entries` | `user_id` FK `users.id` CASCADE | none | none | `silo`; `pinned` | none | OMITTED |
| `personal_facts` | `user_id` (no explicit DB FK) | none | none | `status`; `is_active`; `confidence` | indirect via evidence | OMITTED |
| `personal_fact_evidence` | via `fact_id` FK | none | none | append-only | `source_type` enumeration | OMITTED |
| `personal_fact_revisions` | via `fact_id` FK | none | none | append-only | `actor`/`action`/`reason` | OMITTED |
| Candidate / unreviewed fact | same as `personal_facts` | none | none | `status='candidate'` | `source_type='runtime_extraction'` | OMITTED |
| Verified personal fact | same as `personal_facts` | none | none | `status='verified'` AND `is_active=true` | evidence trail | OMITTED |
| `Memoryos` library state | embedded account-keyed paths | none | none | library-internal | library-internal | not in account export |

Observations that are durable and not addressed by any other slice:

- `memory_entries` and `personal_facts` (with their dependent tables)
  are currently OMITTED from `account-export.v3`. Future export
  coverage is the responsibility of UMS-04 under the Account Export +
  Restore Contract. UMS-03A does not authorize that implementation.
- `personal_facts.user_id` does not declare a database-level FK to
  `users.id`. Account ownership is currently enforced by the
  `(user_id, key)` unique index, by application-layer authority
  checks, and by ADR-005's AccountBoundary rule. UMS-03B must add an
  explicit FK at the time it introduces the canonical envelope.
- The external `Memoryos` library is library-internal and is
  `not safely mappable` to the canonical envelope today. Its
  reconciliation is deferred to a future slice.
- No `memory_records`, `memory_ordinary_payloads`,
  `memory_persona_links`, or `memory_activation_projection` tables
  exist at the current `main` HEAD.

## Frozen semantic species

The minimum semantic species required by current persistence are:

1. **Episodic / semantic memory** — `memory_entries` row family with
   `silo ∈ {ephemeral, midterm, longterm}` as its retention class.
2. **Verified personal fact** — `personal_facts` row where
   `status='verified'` AND `is_active=true`.
3. **Candidate / unreviewed fact** — `personal_facts` row where
   `status ∈ {candidate, disputed, archived}` OR `is_active=false`,
   plus the live-chat `runtime_extraction` and import
   `chatgpt_import` / `claude_import` paths before approval.

The taxonomy is closed under current persistence. New species must be
introduced by a future ADR/contract slice; this contract does not
admit speculative species.

## Canonical envelope semantic categories

Every canonical memory record must populate or resolve every category
below:

- Identity
- Ownership
- Scope
- Semantic species
- Content / payload
- Persona attribution (optional; zero or more)
- Provenance
- Governance
- Lifecycle
- Priority / decay control
- Compatibility (required for compatibility reads; absent for
  canonical-only records)

The categories are independent. No single field answers more than one
category. The legacy `tags` text column on `memory_entries` is
descriptive metadata only and is not authority for any category. The
legacy `silo` column is retention class only and is not authority for
review or activation.

## Ownership, scope, and attribution independence

Three independent authorities govern every canonical record:

```text
memory owner         = authenticated account principal
memory scope         = account or one Project (ADR-081 governed)
memory attribution   = zero or more typed links to stable persona
                       subjects (UMS-02 governed; never mutable
                       PersonaProfile)
```

Forbidden anti-patterns (recorded so that no future implementation
drifts into them):

- `owner_persona_id`
- `persona_profile_id` as durable attribution
- `projects.user_id` as canonical memory owner
- display names, names, prompts, avatars, similarity, Project IDs,
  Persona IDs, PersonaProfile IDs as identity authority
- `tags` as governance authority

The typed Persona link vocabulary follows the direction already
frozen by this contract:

```text
captured_under
suggested_by
associated_with
```

These three values are sufficient to represent current proven
behavior. No additional typed-link value is required by current
evidence. A future slice that requires a new typed-link value must
add it to the canonical token registry before it appears in code,
tests, or documentation that cross the backend, frontend, or
persistence boundary.

## Activation versus retrieval separation

Three independent states:

- **stored** — the row exists and is queryable by its owner through a
  scoped query path;
- **retrievable** — the owner may issue an explicit recall grant that
  resolves the row and renders it into a turn-scoped context;
- **ambient-eligible** — the row may enter provider context without
  an explicit recall grant, only after all §3.5 policy gates pass.

A record may be stored without being ambient-eligible (every
candidate fact). A record may be retrievable without being
ambient-eligible (every imported fact in dormant posture). The
governing doctrine is preserved unchanged:

```text
Automatic capture, explicit activation.
Retrievable != authorized for ambient influence.
```

No client, model, importer, classifier, or UI writes final ambient
eligibility. Guardian computes it at read time per §3.5.

## Provenance spine requirements

Every canonical memory record must retain, where applicable:

```text
source_system
source_record_id
source_thread_id
source_message_id
source_import_job_id
source_export_fingerprint
source_subject_kind
source_subject_id
created_at, updated_at
```

Imported content may normalize into Codexify semantic species but
must preserve its external lineage. External provenance does not
confer activation authority.

## Compatibility-read authority order

Before any future canonical migration:

```text
legacy source row         = durable authority for that legacy record
compatibility envelope    = normalized read projection only
```

After any future canonical migration:

```text
canonical memory row      = durable authority
legacy compatibility path = migration / transition support only
```

UMS-03A does not authorize the authority transition. The transition
belongs to a future implementation + migration proof slice whose
acceptance criteria will require UMS-03B's persistence substrate,
UMS-03C's dual-read sequencing, and UMS-04's export / restore
preservation.

## Compatibility-read matrix (summary)

The full matrix is in §4.13. `not safely mappable` rows:

- `Memoryos` library state — library-internal storage, no current
  account-export coverage, no current provenance spine.
- `memory_entries` rows with malformed `silo`, missing `user_id`, or
  with a `user_id` not resolvable to a real `users.id`.
- `personal_facts` rows with `user_id` not resolvable to a real
  `users.id`, with `status` outside the enumerated set, or with
  evidence rows whose `source_type` is unknown.

All other admitted sources have a defined read-projection shape
recorded in §4.13.

## Fail-closed cases for compatibility reads

A future implementation must fail closed (not "best effort") when:

1. account ownership cannot be proven (`user_id` not resolvable to a
   real `users.id`);
2. legacy semantic species cannot be determined (`silo`, `status`,
   `source_type`, or `is_active` outside its enumerated set);
3. activation status cannot be mapped safely (e.g., `evidence_meta`
   malformed or self-referential);
4. provenance required for a source cannot be preserved (e.g.,
   evidence without a recognized `source_type`);
5. Persona attribution would require heuristic inference;
6. Project scope would require guessing;
7. one source maps ambiguously to multiple incompatible species;
8. normalization would erase revision or evidence semantics.

## Derived-state exclusions

The contract explicitly excludes the following from canonical memory
truth:

- heat;
- recency score;
- retrieval score;
- embedding vector;
- ranking score;
- decay projection;
- working-set membership;
- suggestion ranking;
- UI grouping.

These may reference canonical memory but must remain reproducible /
derived where possible. UMS-10 owns derived heat projections.

## Deferred physical-design questions

Intentionally left to UMS-03B / UMS-03C and not pre-selected by this
contract:

- exact canonical table name and physical schema;
- exact primary-key representation and the export-stable identity
  contract;
- JSON column versus typed columns for species payload;
- normalized provenance tables versus embedded provenance columns;
- physical design of the Persona-link table and the link-type
  registry;
- exact lifecycle token registries and which are physical columns
  versus derived projections;
- exact revision table physical design;
- canonical migration revision identifier and the data-preservation
  acceptance criteria;
- write adapter surface for Vault, explicit remember, classifier, and
  import paths;
- compatibility reader implementation shape;
- cutover and dual-read sequencing.

## ADR impact

- ADR-081 (Project ownership authority): unchanged.
- ADR-082 (Persona Profile manifest and binding authority): unchanged.
- ADR-083 (MemoryOS): not present in the ADR registry; no file
  exists; no conflict detected because ADR-084 is the controlling
  memory architecture decision and the `Memoryos` library is
  library-internal.
- ADR-084 (Unified Account-Owned Memory Store): unchanged; remains
  controlling.

No ADR was created or modified in UMS-03A. No architecture-impact
stop condition was triggered.

## Documentation-only nature

UMS-03A is documentation-only. The following were not changed:

- no SQL schema added;
- no Alembic migration added;
- no ORM model changed;
- no runtime reader or writer changed;
- no retrieval behavior changed;
- no export implementation changed;
- no account export/restore code touched;
- no protocol/domain token registry added;
- no Project authority doctrine reinterpreted;
- no Personal Facts lifecycle authority reinterpreted;
- no Persona attribution semantics reinterpreted.

## Release and runtime impact

```text
UMS-03A CANONICAL MEMORY ENVELOPE CONTRACT: PASSED
UMS-03: OPEN
UMS-03B: AUTHORIZED TO START
UMS-04: NOT AUTHORIZED
RUNTIME/RELEASE IMPACT: NONE
```

No runtime or release capability changed. No Beta claim widened. No
canonical memory persistence implementation exists yet. The frozen
doctrine constrains the next implementation slice without pre-
selecting its physical schema.