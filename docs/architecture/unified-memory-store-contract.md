# Unified Memory Store Contract

> Classification: normative architecture contract
>
> Status: frozen design; implementation pending
>
> Governing ADR: [ADR-084](./adr/084-unified-account-owned-memory-store.md)
>
> Last updated: 2026-09-04

## 1. Purpose

This contract defines the target architecture for one account-owned logical
Memory Store across ordinary memories, imported memory, and the specialized
Personal Facts domain. It governs:

- ownership, Project scope, and stable persona attribution;
- review, lifecycle, context posture, priority, hold, and decay semantics;
- explicit writes, proposed writes, edits, retirement, and erasure;
- ambient eligibility and explicit-recall grants;
- automatic-suggestion consent and review reminders;
- import normalization and source-entity mapping;
- export, restore, projection rebuild, and purge suppression; and
- API, audit, failure, and proof boundaries.

This contract is implementation authority for later Campaign tasks. It is not
evidence that any described table, route, UI, worker, classifier, import, recall
path, export family, or purge behavior currently exists.

## 2. Governing law

> **Account owns. Project scopes. Persona attributes. User approves. Pinning
> prioritizes. Holding suspends decay. The router widens only on explicit user
> intent. Every borrowed memory keeps its attribution.**

The authenticated account user/principal is the authority for personal memory
inspection, approval, correction, scope changes, recall widening, retirement,
restore, and erasure. Infrastructure administration and product-user authority
are separate. A Host Operator or service administrator receives no memory
content capability merely by operating the instance.

“Account-owned” describes the semantic boundary established by ADR-005. It
does not require aesthetic renaming of correctly scoped `user_id` columns.
Schema work is justified only where authority, consistency, portability, or
runtime behavior requires it.

## 3. Authoritative state and normalized dimensions

### 3.1 One logical store, specialized physical domains

The Memory Vault and retrieval policy expose one logical store. Physical state
may remain separated where a subtype has stronger invariants.

The target shape is:

```text
memory_records
├── stable record identity
├── account and optional Project scope
├── kind, retention, context posture, hold, priority
├── provenance and source lineage
└── subtype reference

ordinary_memory_payloads
├── content
├── ordinary review authority
└── ordinary lifecycle authority

personal_facts
├── fact key/value
├── Personal Fact review and activation authority
├── guardrails
├── evidence
└── revisions

memory_persona_links
└── typed attribution to stable persona subjects

memory_activation_projection
└── rebuildable heat and ranking state
```

The implementation may evolve the existing `memory_entries` table rather than
perform an unnecessary table rename, but it must preserve this authority
separation and the migration guarantees below.

### 3.2 Normalized dimensions

| Dimension | Canonical question | Values |
| --- | --- | --- |
| Owner | Which account boundary contains the record? | authenticated account principal |
| Scope | Where may the record participate? | account or one Project |
| Kind | What semantic subtype is this? | ordinary memory, imported memory, Personal Fact, summary snapshot, or later registered kind |
| Retention | Which non-destructive rolloff policy applies? | `short_term`, `mid_term`, `long_term` |
| Review | Has the proposition been accepted? | pending, approved, rejected, disputed |
| Lifecycle | Is the record currently active? | active, dormant, retired |
| Context posture | May an otherwise eligible record enter ambient context? | `explicit_recall_only`, `ambient_context_eligible` |
| Decay control | May automatic rolloff transition this record? | normal, held |
| Priority | How is an already eligible record ranked? | ordinary, pinned |
| Provenance | Where did it originate and how was it transformed? | typed source lineage |
| Persona attribution | Which stable persona subject witnessed, suggested, or is associated with it? | zero or more typed links |

These are independent axes. A single field such as the legacy `silo` or a
comma-separated tag list must not answer multiple authority questions.

Canonical token values that cross backend, frontend, persistence constraints,
tests, or documentation must be added to the canonical token registry in the
implementation task before they spread.

### 3.3 Ordinary-memory authority

For ordinary memories:

- `review_state` is the sole review authority;
- `lifecycle_state` is the sole lifecycle authority;
- explicit user-authored remember actions may create an approved, active
  record;
- classifier, importer, assistant, web, and tool suggestions cannot create an
  approved record; and
- every authority-changing transition produces a revision and intent receipt.

There is no separate `archived` ordinary-memory lifecycle. `retired` is the
single reversible soft-removal state.

### 3.4 Personal Facts authority

For Personal Facts:

- `personal_facts.status` remains authoritative for fact review meaning;
- `personal_facts.is_active` remains authoritative for fact activation until a
  separately approved migration changes it;
- the Memory Store must not persist an independently mutable Personal Fact
  `review_state`, `activation_state`, or `ambient_eligible` flag;
- the unified read model derives review and lifecycle posture from the Personal
  Facts service; and
- every transition passes through the Personal Facts service in the same
  transaction as shared metadata and revision changes.

The compatibility resolver is:

| Personal Fact state | Unified read posture |
| --- | --- |
| `status=verified` and `is_active=true` | approved and active, subject to all other policy gates |
| `status=candidate` | pending and ambient-excluded |
| `status=disputed` | disputed and ambient-excluded |
| legacy `status=archived` | retired and ambient-excluded; no synthetic independent review value is written |
| any `is_active=false` fact | inactive/retired and ambient-excluded |

Shared scope, retention, context posture, hold, priority, provenance, and
persona attribution may be stored beside a Personal Fact. Those fields do not
override the Personal Facts lifecycle.

If transitional storage contains both envelope account identity and
`personal_facts.user_id`, writes must resolve one authenticated account
principal and persist/check both inside one service transaction. A mismatch is
a consistency defect and fails closed; request-time precedence is forbidden.

### 3.5 Computed eligibility

No client, model, importer, classifier, or UI writes final ambient eligibility.
Guardian computes it at read time:

```text
ambient_eligible =
    lifecycle_state == active
    AND review_authority == approved
    AND context_posture == ambient_context_eligible
    AND scope_is_authorized
    AND subtype_policy_allows
    AND no_exclusion_applies
```

For ordinary memory, review and lifecycle authority come from the ordinary
payload. For Personal Facts, they come from the Personal Facts lifecycle.

`no_exclusion_applies` includes diary exclusions, sensitive-identity policy,
Project or thread exclusions, purge tombstones, unresolved ownership conflicts,
unresolved persona bindings, guardrail blocks, and any later canonical
exclusion rule.

The eligibility evaluator returns reason tokens for inclusion and suppression.
It does not return content in telemetry.

## 4. Canonical data relationships

### 4.1 Shared memory envelope

Every logical Memory Store item must have or resolve to:

```text
record_id
account_user_id
project_id nullable
kind
retention_class
context_posture
decay_control
priority
source_system
source_record_id nullable
source_thread_id nullable
source_message_id nullable
source_import_job_id nullable
source_export_fingerprint nullable
created_at
updated_at
version
```

`account_user_id` may be physically named `user_id`. The semantic contract, not
the spelling, makes it account ownership.

The stable public/export identity should be a server-generated UUID independent
of local integer primary keys. Restore preserves it or records an explicit ID
mapping.

Project scope is nullable:

- null means account scope;
- non-null means exactly one Project governed by `projects.user_id`;
- display names, descriptions, import labels, active UI selection, and runtime
  Operator identity cannot infer or override Project authority.

### 4.2 Evidence and revisions

Ordinary memories gain typed evidence and append-only revisions. Every
authority-relevant write records:

- actor account principal;
- mutation source: Vault, explicit chat instruction, confirmed preview,
  classifier, importer, migration, restore, or system decay;
- source user-message or Vault-action receipt where applicable;
- previous and new values;
- reason/action token;
- timestamp and version;
- associated source evidence; and
- whether the change affected content, scope, persona attribution, review,
  lifecycle, context posture, hold, or priority.

Importer/classifier content never replaces an approved revision in place. It
creates a new pending candidate or pending proposed revision.

### 4.3 Stable persona subjects

Memory attribution targets a stable account-owned subject:

```text
persona_subjects
├── persona_subject_id
├── user_id
├── canonical display metadata
├── lifecycle
└── timestamps

persona_subject_bindings
├── persona_subject_id
├── ref_kind: persona | persona_profile
├── ref_id
├── valid_from
└── valid_until
```

Rules:

- `PersonaProfile` is mutable runtime configuration, not historical identity.
- Existing `Persona` and `PersonaProfile` rows are mapped through an explicit,
  account-scoped migration.
- Duplicating, replacing, or retiring a profile does not sever memory history.
- Ambiguous or cross-account bindings fail closed and enter reconciliation.
- A name snapshot may be retained for historical display but is
  non-authoritative.
- There is never an `owner_persona_id`.

Typed memory links are:

```text
captured_under
suggested_by
associated_with
```

A record may have multiple links. Freeform tags remain user organization only.

### 4.5 Persona-subject mapping contract (UMS-02A)

The conceptual model in §4.3 names the stable Persona-subject identity and the
binding surface. This section materializes that doctrine against the current
repository truth and freezes an implementation-ready mapping and enforcement
contract for UMS-02. It does not create tables, ORM models, or runtime code.
UMS-02A froze the lifecycle surface as the smallest prerequisite. UMS-02B
canonicalizes its exact token domain without adding persistence or transition
behavior. UMS-02C must introduce `persona_subjects` and
`persona_subject_bindings` ORM metadata and matching Alembic persistence as
one coherent slice.

#### 4.5.1 Current repository truth (read-only inventory)

The durable Persona-persistence surfaces at current `main` are:

| Durable surface | Table | Model | Stable identifier | Authoritative account ownership | Lifecycle / versioning |
| --- | --- | --- | --- | --- | --- |
| `Persona` | `personas` | `guardian.db.models.Persona` | autoincrement `id` (int) | direct `user_id` FK to `users.id` (`NOT NULL`); partial unique `(user_id, project_id) WHERE is_active` | mutable `is_active` (bool); no immutable revision history; multiple inactive rows may exist per `(user_id, project_id)` |
| `PersonaProfile` | `persona_profiles` | `guardian.db.models.PersonaProfile` | `id` (string, PK) | none on the row itself; account scope lives in `PersonaProfileBinding.owner_account_id` | mutable registry row with `current_revision`; CHECK `current_revision > 0`; CHECK `0.0 <= temperature <= 2.0` |
| `PersonaProfileRevision` | `persona_profile_revisions` | `guardian.db.models.PersonaProfileRevision` | `(profile_id, revision)` PK | per-row scope derived via parent `PersonaProfileBinding` | immutable authored V1 manifest snapshot; CHECK `revision > 0`; index on `(profile_id, created_at)` |
| `PersonaProfileBinding` | `persona_profile_bindings` | `guardian.db.models.PersonaProfileBinding` | `profile_id` PK (1:1) | `owner_account_id` FK to `users.id` (`NOT NULL`) | no lifecycle state column; `created_at` / `updated_at` only |
| Thread Persona/Profile pin | `chat_threads` | `guardian.db.models.ChatThread` | nullable `active_profile_id` (string), nullable `active_profile_revision` (int) | thread owner is `chat_threads.user_id` (`NOT NULL`) | CHECK `active_profile_revision IS NULL OR active_profile_revision > 0`; CHECK `active_profile_revision IS NULL OR active_profile_id IS NOT NULL`; FK `(active_profile_id, active_profile_revision) → persona_profile_revisions(profile_id, revision)` |

The conceptual `Persona` table introduced by the Imprint persona system
migration is currently durable at `main`. It is not part of the
`account-export.v3` family set (only `persona_profiles`,
`persona_profile_revisions`, and `persona_profile_bindings` are explicit
export families today). The conceptual mapping between `Persona` and
`PersonaProfile` is not currently preserved by any persistent foreign key
or binding row.

#### 4.5.2 Source-reference map

| `ref_kind` | Canonical source entity / table | Stable source identifier | Account-ownership evidence | Mutable configuration | Replaced / versioned | May establish subject continuity |
| --- | --- | --- | --- | --- | --- | --- |
| `persona` | `personas` | `personas.id` (autoincrement int) | `personas.user_id` (FK `users.id`, NOT NULL) | yes (`body`, `is_active`, `source`) | replaced by insert + activation (no immutable revision history) | no |
| `persona_profile` | `persona_profiles` (+ `persona_profile_revisions`) | `persona_profiles.id` (string) | `persona_profile_bindings.owner_account_id` (FK `users.id`, NOT NULL) | yes (manifest revisions; `current_revision` pointer advances on substantive update) | yes (immutable revisions under `(profile_id, revision)`) | yes, only with explicit durable continuity evidence defined in §4.5.5 |

The thread pin (`chat_threads.active_profile_id`,
`chat_threads.active_profile_revision`) is not a `ref_kind`. It is a
runtime configuration reference and is never authoritative for Persona-
subject identity.

#### 4.5.3 Ownership evidence and uniqueness

The authoritative account-ownership sources are exactly:

- `personas.user_id`
- `persona_profile_bindings.owner_account_id`

No secondary ownership authority may be defined for Persona-subject identity.

A binding from `persona_subjects` to either `ref_kind` is valid only when the
source's authoritative account is provably equal to the subject's owning
account. The schema enforces that equality by carrying both:

- `persona_subjects.user_id` (FK to `users.id`, `NOT NULL`); and
- a binding-row `source_account_id` (FK to `users.id`, `NOT NULL`) populated
  at insert time from the source's authoritative account.

The DB-level rule rejects any insert or update where
`source_account_id != subject_user_id`.

#### 4.5.4 Subject-creation rule

A migration may create a `persona_subjects` row only when both:

```text
proven account ownership
+
proven source identity
↓
stable persona_subject
```

are satisfied. None of the following may create or coalesce a Persona
subject:

```text
same name
same prompt
same Project
same avatar
same model
active at same time
looks equivalent
↓
same subject
```

For `ref_kind = persona_profile`, the durable evidence is the existence of
`(persona_profile_bindings.profile_id, owner_account_id)` and the
corresponding `persona_profiles.id`.

For `ref_kind = persona`, the durable evidence is the existence of a
`personas` row whose `user_id` is provably equal to the subject's user_id.

#### 4.5.5 Coalescing rule

Coalescing follows four explicit categories:

- **proven same subject** — explicit durable continuity evidence exists;
  the binding may be created or merged.
- **proven distinct subjects** — repository evidence requires separation;
  the binding must not be coalesced.
- **ownership known but identity equivalence unknown** — do not merge;
  references remain separate bindings, each pointing at its own Persona
  subject.
- **ambiguous or contradictory mapping** — fail closed; the row remains
  unresolved until separately authorized reconciliation.

No heuristic matching is permitted. Coalescing cannot infer identity from
names, prompts, descriptions, avatars, Project membership, profile
similarity, active-thread selection, or model output.

If the current repository has no durable evidence capable of proving that a
legacy `Persona` reference and a `PersonaProfile` reference share the same
identity, the contract records that absence and preserves them as separate,
non-coalesced references.

#### 4.5.6 Binding-history semantics

`persona_subject_bindings` fields have the following meanings:

- `valid_from` — the earliest moment at which the binding is authoritative.
  Inclusivity is fixed: a binding with `valid_from = T` is authoritative for
  any attribution event whose recorded time is at or after `T`.
- `valid_until` — the latest moment at which the binding stops being
  authoritative. Inclusivity is exclusive: the binding does not cover events
  at or after `valid_until`. A `NULL` `valid_until` denotes an open-ended,
  currently active binding.
- An active binding is represented as the unique binding for a given
  `(ref_kind, ref_id)` whose `valid_until IS NULL`. No separate `is_active`
  column is required; the active state is derived.

Cardinality and non-overlap invariants:

- A single source reference has at most one active binding at any moment.
  Enforced by a partial-unique index
  `(ref_kind, ref_id) WHERE valid_until IS NULL`.
- A single source reference cannot have two bindings whose validity
  intervals overlap. Enforced by a CHECK constraint
  `valid_until IS NULL OR valid_until > valid_from` plus a service-level
  half-open interval check.
- A single Persona subject may have multiple active bindings, one per
  `ref_kind` (or more, when the contract specifically authorizes it).

Replacement semantics:

```text
stable persona_subject_id
│
├── old PersonaProfile binding     [historical / closed]
│
└── replacement PersonaProfile     [current / active]
```

A replacement closes the predecessor binding by setting its
`valid_until = T` and opens the successor binding with `valid_from = T` and
`valid_until = NULL`. The transition is atomic; the database must reject
overlap or gap on the source side. The historical binding row is never
deleted; it remains queryable for attribution.

Historical attribution resolution: given an attribution event at time `E`,
the unique binding for `(ref_kind, ref_id)` whose interval
`[valid_from, valid_until)` contains `E` is the authoritative attribution
target. If none exists, attribution fails closed.

Deletion or retirement of mutable configuration:

- Deleting or retiring the referenced source row does not delete historical
  bindings; the historical rows remain queryable for attribution.
- Future bindings for that source are forbidden; new mappings must start a
  new subject.

#### 4.5.7 Account-isolation enforcement

Cross-account binding is forbidden:

```text
account A subject
↓
account B Persona/Profile reference
```

The rule is enforced by database and service authority, not by UI
filtering or model behavior. The minimum authoritative surface is:

- `persona_subjects.user_id` (FK `users.id`, NOT NULL);
- `persona_subject_bindings.subject_user_id` (FK `users.id`, NOT NULL),
  derived from the subject row at insert time;
- `persona_subject_bindings.source_account_id` (FK `users.id`, NOT NULL),
  populated at insert time from `personas.user_id` or
  `persona_profile_bindings.owner_account_id`;
- a CHECK constraint `source_account_id = subject_user_id` that the
  database rejects on insert and update.

The polymorphic binding shape cannot enforce account consistency without the
`source_account_id` column above. This is the minimum required shape
refinement UMS-02C must introduce; it does not create a second
ownership authority and reuses `persona_profile_bindings.owner_account_id`
as the single source of account truth for `ref_kind = persona_profile`.

#### 4.5.8 Lifecycle semantics (canonicalized in UMS-02B)

`PersonaSubjectLifecycle` is the canonical lifecycle domain for
`persona_subjects.lifecycle`:

```text
active
retired
```

- **`active`** — a current durable attribution identity. Future persistence
  and runtime work may create current bindings or new attribution to an active
  subject only when the frozen ownership and authority rules permit it.
- **`retired`** — a durable historical attribution identity retained for
  history, but not a current attribution target.

Retirement does not delete historical bindings, rewrite historical
attribution, transfer ownership, merge the subject with another subject,
delete memory, or grant another Persona access to its history. It is not
`deleted`, `purged`, `merged`, or an ownership transfer. No retirement
transition service is implemented by this token slice.

This is an identity-persistence lifecycle vocabulary, not evidence that a
Persona-subject table, route, binding, memory attribution, or runtime behavior
exists. The Imprint persona system's `personas.is_active` remains a separate
runtime toggle and is not this lifecycle domain. `persona_subjects.lifecycle`
must use this registered canonical domain when persistence is introduced;
ad-hoc lifecycle strings are prohibited.

UMS-02C owns the next persistence slice: matching `persona_subjects` and
`persona_subject_bindings` ORM schema plus Alembic migration, deterministic
legacy Persona/Profile backfill, account-consistency and binding-history
enforcement, and disposable-PostgreSQL qualification. It must introduce ORM
and migration truth together rather than create metadata/migration drift.

UMS-02C is now PostgreSQL-qualified on a disposable PostgreSQL 17
database; the migration `d4e8f1a2b6c9 → e5a9c2f7b4d1` reached `head`,
repeat upgrade is a no-op, and the live PostgreSQL constraint inventory
matches §4.5.3, §4.5.6, and §4.5.7. The complete qualification record,
including the two narrow test-harness repairs that were required to
obtain a faithful proof, lives in the
[UMS-02C stable Persona-subject persistence proof](./proofs/runtime/2026-09-07-ums02c-persona-subject-persistence-proof.md).
This is internal persistence qualification only; it does not imply any
user-facing Persona-subject route, binding transition, recall, or
release-capability change. UMS-02 is closed and UMS-03 is authorized to
start; UMS-03 itself must still pass its own acceptance criteria before
any memory storage, retrieval, or release widening is claimed.

#### 4.5.9 Legacy and ambiguous migration policy

| Source condition | Deterministic handling |
| --- | --- |
| valid account-bound `PersonaProfile` (`persona_profile_bindings` exists; account proven) | create one `persona_subjects` row; open one active `persona_subject_bindings` row with `ref_kind = persona_profile`, `valid_from = source_created_at`, `valid_until = NULL`; preserve any historical binding intervals |
| unbound `PersonaProfile` (no `persona_profile_bindings` row) | do not create `persona_subjects`; do not assign an account; record the row as unresolved until separately authorized reconciliation |
| cross-account contradiction (source account ≠ would-be subject account, or two competing account signals) | do not create `persona_subjects`; surface the contradiction for separately authorized reconciliation; no partial binding may be persisted |
| multiple candidate subjects for one source (no deterministic continuity evidence) | do not coalesce; remain unresolved; require separately authorized reconciliation |
| duplicate source-reference binding (would create a second open-ended binding for the same source) | reject the duplicate; preserve the existing binding; surface as a deterministic conflict |
| source reference already bound (active binding exists) | reject the redundant binding; preserve the existing binding; do not overwrite history |
| replacement `PersonaProfile` with explicit continuity evidence | close predecessor binding at the boundary; open successor binding; preserve stable subject |
| source record with no provable account | do not assign an account; do not create `persona_subjects`; remain unbound or quarantined |
| legacy `Persona` row (`personas` is currently durable at `main`) | treat as `ref_kind = persona` source with `personas.user_id` as authoritative account; create one `persona_subjects` row only when `user_id` is provable; otherwise remain unbound or quarantined |
| zero-user / multi-user legacy situations | fail closed; no account is inferred; remain unbound or quarantined until separately authorized reconciliation |

Classification must occur before mutation. No name-based fallback is
permitted.

#### 4.5.10 Export-shape requirements (review only)

The minimum future portable state needed for stable Persona attribution,
when the exporter / restore surface is later authorized, is:

- stable `persona_subject_id`;
- owning account relationship;
- canonical display snapshot / metadata (descriptive only);
- lifecycle state from the canonical domain recorded in §4.5.8;
- binding source kind and identifier (`ref_kind`, `ref_id`);
- binding history timestamps (`valid_from`, `valid_until`);
- explicit relationship records required to remap account-local IDs safely.

Source IDs and display names are provenance and reference data only, not
authority.

UMS-02A does not modify exporter or restore code; this section freezes the
export-shape review only.

### 4.6 Memory-bearing source inventory (current persistence truth, read-only)

UMS-03A freezes the canonical memory envelope as semantic doctrine.
Before any future canonical migration, the contract records the durable
memory-bearing persistence surfaces that exist at the current `main`
HEAD and that later Campaign slices must integrate with or read
through. The inventory is read-only. No durable surface is reclassified
or merged in UMS-03A.

For each legacy source family, the inventory records the canonical
table/model, the account-ownership authority in place today, the Project
scope posture today, the Persona attribution posture today, the
semantic meaning, the lifecycle/status fields, the provenance fields
that already exist, the retrieval consumers today, the write authority
today, the current export coverage, and whether the source is canonical
or derived today.

| Legacy source family | Table / model | Account ownership today | Project scope today | Persona attribution today | Semantic meaning | Lifecycle / status | Provenance today | Retrieval consumers | Write authority | Export coverage today | Canonical or derived today |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `memory_entries` | `memory_entries` / `guardian.db.models.MemoryEntry` | `user_id` (FK `users.id`, NOT NULL, `ON DELETE CASCADE`) | none | none | episodic / semantic memory organized by retention silo | `silo ∈ {ephemeral, midterm, longterm}`; `pinned` (priority); `content` (mutable in place via existing UPDATE path) | none (no `source_system`, no `source_record_id`, no `source_thread_id`) | `guardian.core.pgdb` CRUD; `guardian.routes.memory`; `guardian.context.broker` semantic lane | `guardian.routes.memory`; external `Memoryos` integration | OMITTED from `account-export.v3` (see `guardian.services.account_export.OMITTED_FAMILIES`) | canonical for its purpose; lacks envelope governance |
| `personal_facts` | `personal_facts` / `PersonalFact` | `user_id` (`String(255)`, NOT NULL, no explicit database-level FK declared; implicit via the `(user_id, key)` unique index and application authority) | none | none | correctable verified / candidate facts about the user | `status ∈ {candidate, verified, disputed, archived}`; `is_active`; `confidence ∈ [0.0, 1.0]`; `last_confirmed_at`; `guardrail_metadata` (JSONB) | indirect via `personal_fact_evidence.source_type` | `guardian.routes.personal_facts`; `guardian.context.broker` (verified+active only per ADR-013) | `guardian.services.personal_facts`; `guardian.fact_candidate_pipeline` | OMITTED from `account-export.v3` | canonical for its purpose; specialized per ADR-013 and ADR-084 |
| `personal_fact_evidence` | `personal_fact_evidence` / `PersonalFactEvidence` | via `fact_id` FK to `personal_facts` (`ON DELETE CASCADE`) | none | none | evidence backing a Personal Fact | none (append-only via `fact_id`) | `source_type ∈ {chatgpt_import, runtime_extraction, user_stated, user_corrected, claude_import}`; nullable `source_message_id` FK to `chat_messages`; `evidence_meta` (JSONB); `modality`; `excerpt` | Personal Facts service; broker evidence rendering | Personal Facts service | OMITTED | derived from fact creation, but durable |
| `personal_fact_revisions` | `personal_fact_revisions` / `PersonalFactRevision` | via `fact_id` FK to `personal_facts` (`ON DELETE CASCADE`) | none | none | audit trail of fact updates | none (append-only) | `actor`; `action`; `field_changed`; `old_value`; `new_value`; `reason`; `created_at` | Personal Facts service | Personal Facts service | OMITTED | canonical audit trail |
| Candidate / unreviewed fact (subset of `personal_facts`) | same as `personal_facts` with `status ∈ {candidate, disputed, archived}` or `is_active = false` | same as `personal_facts` | none | none | pending fact extraction from live chat or import before user review | same as `personal_facts` | `personal_fact_evidence.source_type` distinguishes live-chat (`runtime_extraction`), explicit Vault (`user_stated`), and import (`chatgpt_import`, `claude_import`) | Personal Facts service | `guardian.fact_candidate_pipeline` (live chat); import pipeline; Vault explicit remember | OMITTED | durable candidate per ADR-084; storage ≠ ambient influence |
| Verified personal fact (subset of `personal_facts`) | `personal_facts` with `status='verified'` AND `is_active=true` | same as `personal_facts` | none | none | already-approved fact eligible for ambient influence per ADR-013 | same as `personal_facts` | same evidence trail | broker verified-active filter | Personal Facts service | OMITTED | canonical for its purpose; review authority owned by Personal Facts service |
| `Memoryos` library state | external library `guardian/memoryos/`; library-internal short_term / mid_term / long_term storage; not currently Postgres-backed | embedded account-keyed file paths | none | none | short / mid / long-term memory with heat-based retention in the external library | library-internal | library-internal | Memoryos `Retriever`; chat completion prompt assembly | Memoryos `Updater`; `memoryos.mid_term.compute_segment_heat` | not part of account export | not currently Postgres-canonical; reconciliation into the canonical envelope is deferred to a later contract and proof slice |

Notes on the inventory:

- `memory_entries` and `personal_facts` (together with their dependent
  tables `personal_fact_evidence` and `personal_fact_revisions`) are
  currently OMITTED from the `account-export.v3` family set in
  `guardian/services/account_export.py`. Their future export coverage
  is the responsibility of the Account Export + Restore Contract under
  UMS-04. UMS-03A does not authorize that export implementation.
- `personal_facts.user_id` does not declare a database-level FK to
  `users.id`. Account ownership is currently enforced by the
  `(user_id, key)` unique index, by application-layer authority checks
  in `guardian.services.personal_facts`, and by ADR-005's
  `AccountBoundary` rule. UMS-03B must add an explicit FK at the time
  it introduces the canonical envelope so account ownership is
  enforceable at the database layer, not only by application
  convention.
- The external `Memoryos` library is treated as a read-only inventory
  source in UMS-03A. It is not currently backed by Postgres, its
  storage shape is library-internal, and its reconciliation into the
  canonical envelope is explicitly deferred to a later task that must
  introduce its own contract and proof.
- No `memory_records`, `memory_ordinary_payloads`,
  `memory_persona_links`, or `memory_activation_projection` tables
  exist at the current `main` HEAD. Their existence and physical shape
  are deferred to UMS-03B.

### 4.7 Canonical envelope semantic categories

§4.1 above names the field list of the canonical shared memory envelope.
That list is a semantic declaration; physical column names, types, and
table layouts are deferred to UMS-03B. This subsection re-states the
envelope as a small set of independent semantic categories. Every
future canonical memory record must populate or resolve every category
below:

| Category | Conceptual question | Required? |
| --- | --- | --- |
| Identity | What is the stable record identity used for routing, audit, and export? | yes |
| Ownership | Which authenticated account principal owns the record? | yes |
| Scope | Is the record account-scoped or Project-scoped? | yes |
| Semantic species | Which of the species in §4.8 is this record? | yes |
| Content / payload | What is the species-appropriate canonical payload or payload reference? | yes |
| Persona attribution | Which stable persona subjects (if any) witnessed, suggested, or are otherwise associated with this record? | optional; zero or more |
| Provenance | Where did the record originate and how was it transformed? | yes |
| Governance | What review, activation, and user-authority state applies? | yes |
| Lifecycle | What are the timestamps and any retirement / tombstone posture? | yes |
| Priority / decay control | Is the record pinned, held, or under normal decay? | yes |
| Compatibility | For records read through a legacy source, which legacy source family and identifier produced this view? | required for compatibility reads; absent for canonical-only records |

The categories are independent. A single field (such as the legacy
`silo` column, the legacy `pinned` boolean, or a comma-separated tag
list) must not answer more than one category's question. The legacy
`tags` text column on `memory_entries` is descriptive metadata only and
is not authority for any category above. The legacy `silo` column is
retention class only and is not authority for review or activation.

### 4.8 Semantic species taxonomy

The canonical serialized token is the protocol authority for
every species defined in this section. Human-readable species
labels are descriptive and may use natural-language punctuation
or explanatory phrasing; they are not authoritative for
serialization. No alternate serialized aliases are accepted.

The canonical serialized spellings frozen by this contract are:

| Human-readable species      | Canonical serialized token  |
| --------------------------- | --------------------------- |
| Episodic / semantic memory  | `episodic_semantic_memory`  |
| Verified personal fact      | `verified_personal_fact`    |
| Candidate / unreviewed fact | `candidate_unreviewed_fact` |

These three spellings together are the closed canonical
serialization of the three-species taxonomy. No future contract
amendment may introduce a fourth species, split an existing
species, or merge two species without a separately authorized
ADR / contract slice.

The minimum semantic species required by current persistence are:

1. **Episodic / semantic memory.** A record of an explicit user-
   authored memory statement or of an ordinary memory lane entry.
   Today this is the `memory_entries` row family with
   `silo ∈ {ephemeral, midterm, longterm}` as its retention class.
   May be created by explicit user remember, by Vault authoring, or
   by legacy ordinary-memory writes. Review authority is the user;
   ambient context eligibility is the default, subject to §3.5 and
   §5.1.

2. **Verified personal fact.** A record that has passed the Personal
   Facts service's review authority with `status='verified'` and
   `is_active=true`. Today this is the `personal_facts` row family
   in the verified+active subset. May be created by explicit user
   approval, by an approved fact merge, or by an explicitly
   authorized classifier path. Review and activation authority remain
   Personal Facts service authority.

3. **Candidate / unreviewed fact.** A pending fact that has not been
   approved. Today this is the `personal_facts` row family in the
   `status ∈ {candidate, disputed, archived}` subset, the live-chat
   pipeline `runtime_extraction` evidence, and the
   `chatgpt_import` / `claude_import` imported facts before approval.
   Storage of a candidate is durable collection; ambient influence
   authority is forbidden until the record passes the relevant
   review authority per ADR-084 and §5.1.

The taxonomy is closed under current persistence. New species must be
introduced by a future ADR / contract slice; this contract does not
admit speculative species for capabilities that have no current
evidence.

For each species the contract fixes:

- what the record means;
- which authority may create it;
- whether user review is required before ambient influence;
- whether it may be explicitly retrieved before activation;
- its provenance requirements;
- whether its content is mutable, revisioned, or append-only;
- how it maps from current persistence (see §4.12).

| Species | Canonical token | Creator authority | Review before ambient | Explicit recall before activation | Provenance required | Content form | Map from current persistence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Episodic / semantic memory | `episodic_semantic_memory` | user (Vault, explicit remember) or legacy ordinary-memory writer | yes, by default | yes | yes (§4.10) | mutable in place; revisioned on authority transitions | `memory_entries` row, all silos |
| Verified personal fact | `verified_personal_fact` | Personal Facts service only | yes (already verified) | yes | yes (Personal Facts evidence trail) | revisioned, append-only mutations | `personal_facts` row where `status='verified'` AND `is_active=true` |
| Candidate / unreviewed fact | `candidate_unreviewed_fact` | Personal Facts service or import pipeline | required before ambient | yes (explicit grant only) | yes (Personal Facts evidence) | revisioned, append-only mutations | `personal_facts` row where `status ∈ {candidate, disputed, archived}` OR `is_active=false` |

#### 4.8.1 Amendment provenance

UMS-03A-A (`docs/architecture/proofs/runtime/2026-09-07-ums03a-a-memory-species-token-spelling-proof.md`)
froze the canonical serialized spellings above without
modifying the three-species taxonomy, the species meanings, the
review / activation / retrieval / ambient-influence posture, the
provenance requirements, the mutation / revision semantics, or
the legacy compatibility mapping. The slash-joined prose
(`Episodic / semantic memory`, `Candidate / unreviewed fact`)
remains a single human-readable combined label per affected
species, not a list of protocol aliases. The amendment
authorizes UMS-03B to consume the spellings above without
re-deciding the underlying semantic taxonomy.

#### 4.8.2 Token implementation checkpoint (UMS-03B)

UMS-03B registered the two closed vocabularies frozen above as
canonical protocol tokens in `guardian/protocol_tokens.py`:

- `MemorySemanticSpecies` — the three semantic species above.
- `MemoryPersonaLinkKind` — the three already-frozen Persona-
  attribution relationship kinds (`captured_under`,
  `suggested_by`, `associated_with`).

The token registration is a vocabulary-only implementation. It
does not introduce SQL persistence, an ORM model, an Alembic
migration, a runtime writer, a runtime reader, a retrieval path,
an export path, or any other consumer. The freeze of the
three-species taxonomy and the Persona-link vocabulary is the
controlling doctrine; the tokens are the protocol representation
of that doctrine. Future persistence, retrieval, and export
surfaces must import these registered tokens rather than
introduce inline string values. The acceptance criteria for
later UMS-03 slices will require that the registered values are
the only values emitted by those surfaces.

### 4.9 Ownership, scope, and attribution independence

Three independent authorities govern every canonical record:

```text
memory owner         = authenticated account principal
memory scope         = account or one Project (ADR-081 governed)
memory attribution   = zero or more typed links to stable persona
                       subjects (UMS-02 governed; never mutable
                       PersonaProfile)
```

These three authorities must not be conflated. The following
anti-patterns are forbidden by this contract:

- `owner_persona_id` — a persona never owns memory;
- `persona_profile_id` as durable attribution — runtime profile
  configuration is not identity and must not be the attribution target;
- `projects.user_id` as the canonical memory owner — Project authority
  scopes but does not own;
- display names, names, prompts, avatars, similarity, Project IDs,
  Persona IDs, or PersonaProfile IDs as identity authority;
- `tags` as governance authority.

The future typed Persona link vocabulary follows the direction already
frozen by this contract:

```text
captured_under
suggested_by
associated_with
```

These three values are sufficient to represent current proven
behavior. No additional typed-link value is required by current
evidence. A future slice that requires a new typed-link value must add
it to the canonical token registry before it appears in code, tests,
or documentation that cross the backend, frontend, or persistence
boundary.

### 4.10 Activation versus retrieval separation

Activation, retrieval, and ambient influence are three independent
states. The contract freezes their independence:

- **stored** — a row exists and is queryable by its owner through a
  scoped query path;
- **retrievable** — the owner may issue an explicit recall grant that
  resolves the row and renders it into a turn-scoped context;
- **ambient-eligible** — the row may enter provider context without
  an explicit recall grant, only after all policy gates in §3.5 pass.

A record may be stored without being ambient-eligible (every candidate
fact). A record may be retrievable without being ambient-eligible
(every imported fact in dormant posture). A record may become
ambient-eligible only after review authority and activation authority
both approve, the policy gates in §3.5 pass, and the explicit user
consent state permits collection.

The governing doctrine is preserved unchanged:

```text
Automatic capture, explicit activation.
Retrievable != authorized for ambient influence.
```

No client, model, importer, classifier, or UI writes final ambient
eligibility. Guardian computes it at read time per §3.5.

### 4.11 Provenance spine requirements

Every canonical memory record must retain, where applicable, the
minimum provenance required to support replay, attribution,
export / restore, and fail-closed governance:

```text
source_system           ∈ {codexify, openai, anthropic, future registered}
source_record_id        stable source identifier when present
source_thread_id        nullable; canonical chat_threads row reference when present
source_message_id       nullable; canonical chat_messages row reference when present
source_import_job_id    nullable; account_import_jobs row reference for imported material
source_export_fingerprint
                         nullable; export hash when material was imported from an export
source_subject_kind     taxonomy of the originating surface
                         (chat, vault, importer, classifier, future registered)
source_subject_id       stable identifier of the originating surface entity
created_at, updated_at  server-generated authoritative timestamps
```

Imported content may normalize into Codexify semantic species but must
preserve its external lineage. The presence of external provenance
does not confer activation authority.

### 4.12 Compatibility-read boundary and authority order

Before any future canonical migration, the authority order is:

```text
legacy source row         = durable authority for that legacy record
compatibility envelope    = normalized read projection only
```

After any future canonical migration, the authority order becomes:

```text
canonical memory row      = durable authority
legacy compatibility path = migration / transition support only
```

UMS-03A does not authorize the authority transition. That transition
belongs to a future implementation + migration proof slice whose
acceptance criteria will require UMS-03B's persistence substrate,
UMS-03C's dual-read sequencing, and UMS-04's export / restore
preservation.

Compatibility reads must:

- remain read-only with respect to legacy persistence in UMS-03A;
- not backfill canonical rows;
- not mutate source rows;
- not upgrade candidate material to approved material;
- not infer Persona attribution;
- not infer missing Project scope;
- not erase provenance;
- not silently widen retrieval;
- not introduce a second permanent source of truth.

### 4.13 Compatibility-read matrix

The matrix below names every durable memory-bearing source identified
in §4.6 and assigns its canonical envelope read-projection shape.
Where a source cannot be mapped without inventing authority, the row
is marked `not safely mappable` and the failure reason is recorded.

| Legacy source family | Envelope species | Owner derivation | Project scope derivation | Persona attribution derivation | Provenance derivation | Activation / review interpretation | Lossless fields (read projection) | Fields that cannot yet be represented | Fail-closed conditions |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `memory_entries` (any `silo`) | episodic / semantic memory | `user_id` | absent today → account scope | absent today → zero links | absent today → `source_system='codexify'`, `source_record_id='memory_entries:<id>'`; no `source_thread_id` / `source_message_id` | absent today → read posture is "ambient-eligible by default"; promotion to ambient must still pass §3.5 gates | `id`, `user_id`, `silo`, `content`, `tags`, `pinned`, `created_at`, `updated_at` | full §4.11 spine beyond `source_system` + `source_record_id`; Project scope; Persona attribution; canonical `source_thread_id` / `source_message_id` | rows with malformed `silo` or missing `user_id`; rows whose `user_id` does not resolve to a real `users.id`; rows whose `content` cannot be losslessly represented |
| `personal_facts` (`status='verified'`, `is_active=true`) | verified personal fact | `user_id` | absent today → account scope | absent today → zero links | primary `source_type` from latest `personal_fact_evidence`; latest `evidence_meta`; `source_message_id` when present | unified read posture = approved, active | `id`, `user_id`, `key`, `value`, `status`, `confidence`, `is_active`, `last_confirmed_at`, `guardrail_metadata`, `created_at`, `updated_at`; full evidence rows; revisions | Project scope; Persona attribution; canonical `source_thread_id` for facts whose evidence lacks `source_message_id` | rows with evidence whose `source_type` is outside the enumerated set; rows whose `evidence_meta` is non-JSON or self-referential |
| `personal_facts` (`status ∈ {candidate, disputed, archived}` or `is_active=false`) | candidate / unreviewed fact | `user_id` | absent today → account scope | absent today → zero links | `personal_fact_evidence` rows; `source_type` distinguishes live-chat vs import vs user_stated | unified read posture = pending, ambient-excluded | same as verified; additionally the `status` value and `is_active` | same as verified | same as verified |
| `personal_fact_evidence` | read alongside its parent fact; never independently a memory record | n/a (derived) | n/a | n/a | `source_type`; `source_message_id`; `evidence_meta`; `modality`; `excerpt` | n/a (derived audit row) | every column | none — fully lossless | `source_type` outside the current enumerated set |
| `personal_fact_revisions` | read alongside its parent fact; never independently a memory record | n/a (derived) | n/a | n/a | `actor`; `action`; `field_changed`; `old_value`; `new_value`; `reason`; `created_at` | n/a (derived audit row) | every column | none — fully lossless | none |
| `Memoryos` library state | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | `not safely mappable` — current storage is library-internal, has no current account-export coverage, and has no current provenance spine; reconciliation into the canonical envelope is deferred to a future slice |
| `memory_entries` rows with malformed `silo`, missing `user_id`, or with a `user_id` not resolvable to a real `users.id` | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | `not safely mappable` — account ownership authority is ambiguous |
| `personal_facts` rows with `user_id` not resolvable to a real `users.id`, with `status` outside the enumerated set, or with evidence rows whose `source_type` is unknown | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | `not safely mappable` — review authority is ambiguous; provenance spine is incomplete |

### 4.14 Fail-closed cases for compatibility reads

A future implementation must fail closed (not "best effort") when:

- account ownership cannot be proven (`user_id` not resolvable to a
  real `users.id`);
- legacy semantic species cannot be determined (`silo`, `status`,
  `source_type`, or `is_active` outside its enumerated set);
- activation status cannot be mapped safely (for example, a
  `personal_facts` row whose `evidence_meta` is malformed or
  self-referential);
- provenance required for a source cannot be preserved (for example,
  evidence without a recognized `source_type`);
- Persona attribution would require heuristic inference (for example,
  inferring a persona from a thread pin or a recent selection);
- Project scope would require guessing (for example, inferring a
  Project from a recent chat thread);
- one source maps ambiguously to multiple incompatible species (for
  example, an imported fact whose `source_type` is unknown and whose
  status is unverifiable);
- normalization would erase revision or evidence semantics (for
  example, flattening `personal_fact_revisions` into a single current
  value).

A future migration may not "best effort" any of these cases. The
acceptance criteria for the future migration proof slice must
enumerate the same fail-closed cases and prove each one is honored.

### 4.15 Deferred physical-design questions

The following physical-design choices are intentionally left to
UMS-03B / UMS-03C and are not pre-selected by this contract:

- exact canonical table name and physical schema;
- exact primary-key representation (server-generated UUID versus current
  autoincrement integer) and the export-stable identity contract;
- JSON column versus typed columns for species payload;
- normalized provenance tables versus embedded provenance columns;
- physical design of the Persona-link table, the link-type registry,
  and the half-open validity semantics for attribution history;
- exact lifecycle token registries (`active` / `dormant` / `retired` /
  `purged`) and which of them are physical columns versus derived
  projections;
- exact revision table physical design;
- canonical migration revision identifier and the data-preservation
  acceptance criteria it must satisfy;
- write adapter surface for the Vault, explicit remember commands,
  classifier, and import paths;
- compatibility reader implementation shape (view, function, service);
- cutover and dual-read sequencing (which readers run when, how
  drift is detected, when the legacy source row stops being the
  durable authority).

This contract constrains those later choices but does not pre-select
them. UMS-03B is the next slice authorized on PASS of UMS-03A.

### 4.16 Canonical memory persistence schema (UMS-03C)

UMS-03C freezes the physical persistence contract that UMS-03D will
implement. It is DDL-contract precision: table identity, column
identity, type, nullability, defaults, foreign-key authority,
uniqueness, token-derived CHECK constraints, payload placement,
Persona-link structure, governance representation, FK delete
behavior, index strategy, and first-migration posture are all
frozen here. UMS-03C creates no table, no ORM model, no Alembic
migration, and no runtime code.

This section sits between §4.15 (which deferred physical design
and was the previous end of the deferred-physical-design chain)
and §4.4 (the activation-projection section, which is
schema-independent). §4.4, §4.11, and §15 together remain
authoritative for derived/heat state.

#### 4.16.1 Canonical table inventory

The canonical UMS-03 persistence substrate consists of exactly
three new tables:

```text
memory_records
    the canonical envelope row; one row per canonical memory atom

memory_persona_links
    typed stable-Persona attribution relationships for a memory
    record; zero or more rows per memory record

memory_provenance
    first-class durable lineage of a memory record; one or more
    rows per memory record
```

The three table names are unclaimed in the current
`guardian/db/models.py` (verified at the start of UMS-03C) and
introduce no collision with existing persistence. The names were
preferred by the UMS-03C spec and are accepted here as the
canonical table identifiers. No alternative name is admitted by
this contract. A future ADR / contract amendment is required to
introduce any of these names with different meaning.

No other table is added by the canonical envelope. Derived
projection state (heat, ranking, embeddings, working-set
membership, suggestion ranking, UI grouping) is explicitly
excluded from canonical persistence and is owned by UMS-10.
Permanent erasure semantics are deferred to UMS-11. Export /
restore implementation is deferred to UMS-04.

#### 4.16.2 Canonical envelope — `memory_records`

`memory_records` is the canonical authority-bearing row for every
canonical memory atom. It owns every authority-bearing envelope
field and references `users`, `projects`, and `persona_subjects`
by relational foreign key.

| Column                | Type                          | Null    | Default   | Authority meaning |
|-----------------------|-------------------------------|---------|-----------|-------------------|
| `memory_id`           | `String(36)` (UUID) PK        | NOT NULL | —        | Stable canonical memory identity (export-stable, portable, suitable for `memory_persona_links` and `memory_provenance` references) |
| `user_id`             | `String(255)` FK `users.id`   | NOT NULL | —        | Account ownership; CASCADE on user delete |
| `project_id`          | `Integer` FK `projects.id`    | NULL    | NULL      | Optional Project scope; `NULL` means account scope; ON DELETE RESTRICT |
| `semantic_species`    | `String(32)`                  | NOT NULL | —        | Closed `MemorySemanticSpecies` value (only the three frozen values; no aliases) |
| `text_content`        | `Text`                        | NULL    | NULL      | Free-text content for `episodic_semantic_memory`; non-authority payload |
| `fact_key`            | `String(255)`                 | NULL    | NULL      | Fact identifier for personal-fact species; non-authority payload |
| `fact_value`          | `Text`                        | NULL    | NULL      | Fact content for personal-fact species; non-authority payload |
| `fact_confidence`     | `Float` (range 0.0–1.0)       | NULL    | NULL      | Fact confidence for personal-fact species; non-authority payload |
| `reviewed_at`         | `TIMESTAMP(timezone=True)`    | NULL    | NULL      | Timestamp at which user review first approved the row; non-NULL means reviewed |
| `activated_at`        | `TIMESTAMP(timezone=True)`    | NULL    | NULL      | Timestamp at which the row became ambient-eligible; non-NULL means activated |
| `pinned`              | `Boolean`                     | NOT NULL | `false`  | Priority flag; pinning changes priority only, not truth or ownership |
| `held`                | `Boolean`                     | NOT NULL | `false`  | Decay-suspension flag; held rows do not transition lifecycle through decay |
| `extensions`          | `JSONB`                       | NULL    | NULL      | Auxiliary non-authority metadata only; not source of ownership, scope, Persona identity, activation, or review |
| `created_at`          | `TIMESTAMP(timezone=True)`    | NOT NULL | `now()`  | Row creation timestamp |
| `updated_at`          | `TIMESTAMP(timezone=True)`    | NOT NULL | `now() + onupdate` | Row last-modified timestamp |

DB-enforced invariants (CHECK / UNIQUE / FK):

- `UNIQUE (memory_id, user_id)` — binds memory identity to its
  account so composite FKs from child tables can prove
  same-account.
- `FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE`
  — account teardown removes the account's memory; aligns with
  existing `projects.user_id` and `persona_subjects.user_id`
  delete behavior.
- `FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE
  RESTRICT` — Project deletion is blocked while any memory is
  attached; the application must first detach (or archive) the
  memory. This prevents Project deletion from silently converting
  Project-scoped memory into account-wide memory. The composite
  FK below additionally enforces that the Project belongs to the
  same account as the memory.
- `FOREIGN KEY (project_id, user_id) REFERENCES projects(id,
  user_id)` — when `project_id IS NOT NULL`, the Project's
  `user_id` must equal the memory's `user_id`. This is the
  DB-enforced cross-account prevention required by §4.9 and
  §3.2 (no `Project scope = Project owned by a different
  account`).
- `CHECK (semantic_species IN ('episodic_semantic_memory',
  'verified_personal_fact', 'candidate_unreviewed_fact'))` —
  derived from the canonical `MemorySemanticSpecies` token
  domain. The constraint is named
  `memory_records_semantic_species_check`. No additional values,
  no aliases (`episodic_memory`, `semantic_memory`,
  `candidate_fact`, `unreviewed_fact` are all rejected).
- `CHECK (fact_confidence IS NULL OR (fact_confidence >= 0.0
  AND fact_confidence <= 1.0))` — preserves the current
  `personal_facts.confidence` semantic.
- `CHECK ((project_id IS NULL) OR (text_content IS NOT NULL OR
  fact_key IS NOT NULL))` — every row must carry some
  species-appropriate payload; pure shells are rejected.
- `CHECK (semantic_species = 'episodic_semantic_memory'
  IMPLIES (text_content IS NOT NULL AND fact_key IS NULL AND
  fact_value IS NULL AND fact_confidence IS NULL))` — the
  episodic species must use the text payload and must not
  use the fact payload.
- `CHECK (semantic_species IN ('verified_personal_fact',
  'candidate_unreviewed_fact') IMPLIES (fact_key IS NOT NULL
  AND fact_value IS NOT NULL AND text_content IS NULL))` —
  the personal-fact species must use the fact payload and must
  not use the text payload.
- `CHECK (activated_at IS NULL OR (reviewed_at IS NOT NULL
  AND activated_at >= reviewed_at))` — a row may not be
  activated before it is reviewed. Activation may be
  recorded at the same instant as review. Review and
  activation remain distinct governance states. The full
  ordering rule and the valid / invalid boundary cases
  are recorded in §4.16.2a.
- `CHECK (NOT held OR NOT pinned) OR true` — pin and hold are
  independent flags; the CHECK is a no-op (it preserves the
  pin/hold independence the spec required) and is documented
  for clarity. Pinning changes priority only; holding suspends
  decay only. Neither flag ever changes ownership, scope, or
  Persona attribution.

`memory_id` is a server-generated `String(36)` UUID chosen
because:

- `persona_subjects.persona_subject_id` already uses the same
  shape and the canonical export-stable identity contract in
  §4.1 already references UUID-style stable IDs;
- the existing autoincrement `BigInteger` pattern used by
  `memory_entries.id` and `personal_facts.id` is a poor
  fit for export / restore portability (auto-increment
  values must be remapped on import, and §4.1 expressly
  forbids silent remapping);
- the foreign key from `memory_persona_links` and
  `memory_provenance` to `memory_records.memory_id` is
  stable across instances.

#### 4.16.2a Canonical review-before-activation ordering

The frozen `memory_records` CHECK constraint
`activated_at IS NULL OR (reviewed_at IS NOT NULL
AND activated_at >= reviewed_at)` encodes the canonical
review-before-activation ordering rule:

```text
Review and activation are distinct governance states.

An activated memory must be reviewed.

Activation may be recorded at the same instant as review,
including when both governance transitions are applied
atomically by a single user-authoritative action.

Activation must never be recorded before review.
```

The governance states are logically distinct but need not
occupy different wall-clock instants. Atomic
review-and-activate operations may persist one timestamp
for both transitions. Artificial timestamp offsets (for
example, an artificial `+1 microsecond` separation) are
forbidden as a way to satisfy the schema. Timestamp
equality does not collapse the two governance states into
one state.

The boundary cases that this rule accepts and rejects are
the direct UMS-03D migration-test contract.

**Valid** (the row must satisfy the CHECK above):

```text
reviewed_at  = NULL
activated_at = NULL

reviewed_at  = T
activated_at = NULL

reviewed_at  = T
activated_at = T          (same instant)

reviewed_at  = T1
activated_at = T2         where T2 > T1
```

**Invalid** (the row is rejected by the CHECK above):

```text
reviewed_at  = NULL
activated_at = T          (activated without review)

reviewed_at  = T2
activated_at = T1         where T1 < T2   (activated before review)
```

The `memory_records_review_activation_order_check`
constraint name is the canonical identifier for this rule
in the resulting PostgreSQL schema; UMS-03D must use the
exact name above.

The UMS-03A retrieval governance doctrine remains
authoritative: row existence, review, activation,
explicit retrieval, and ambient influence remain five
conceptually distinct states. The CHECK above enforces
the activation-vs-review boundary; the other boundaries
are computed at read time per §3.5 and §6.1. Activation
alone (even when correctly ordered) does not confer
ambient influence.

The previous prose claim that "activation is a strictly
later event than review" and the previous CHECK
`NOT (reviewed_at IS NULL AND activated_at IS NOT NULL)`
were both retracted by UMS-03C-A. UMS-03C-A
documentation-only; no ORM model, no Alembic migration,
and no runtime code changed.

#### 4.16.2b Project composite ownership target (UMS-03C-B)

The frozen `memory_records` composite foreign key
`(project_id, user_id) REFERENCES projects (id, user_id)`
(`ON DELETE RESTRICT`) requires that the `projects` table
carry an unconditional `UNIQUE` (or `PRIMARY KEY`) constraint
on the column pair `(id, user_id)`. PostgreSQL refuses to
define a composite foreign key whose referenced columns are
not covered by a unique constraint at the target.

Repository inspection at the UMS-03D preflight confirmed:

```text
projects.id          = PRIMARY KEY
projects.user_id      = canonical Project account authority
projects(id, user_id) = no UNIQUE / no PRIMARY KEY
```

The only existing uniqueness on `projects` is the partial
unique index
`uq_projects_user_id_system_role ON (user_id, system_role)
WHERE system_role IS NOT NULL`,
which cannot serve as a composite FK target because it is
partial and indexes the columns in the wrong order.

UMS-03C-B freezes the canonical enabling relational
constraint:

```sql
ALTER TABLE projects
ADD CONSTRAINT uq_projects_id_user_id
UNIQUE (id, user_id);
```

Properties of this constraint, frozen by this contract:

- The new constraint lives on the existing `projects` table
  and does not change the canonical Project identity
  (`projects.id`) or the canonical Project ownership field
  (`projects.user_id`).
- `projects.id` remains the canonical Project primary key.
  The new constraint does not replace or extend it.
- The new constraint is mathematically non-destructive. The
  existing `projects.id` primary key guarantees that no two
  rows share `id`; therefore no row can violate
  `UNIQUE (id, user_id)`. The migration that adds the
  constraint cannot reject any valid existing Project row.
- The new constraint does not imply that `(id, user_id)` is a
  replacement identifier for Project. The canonical Project
  identity remains `projects.id`.
- The new constraint is added solely to provide a legal
  PostgreSQL composite foreign key target for the
  same-account `memory_records` FK, and for any future
  same-account composite FK that needs the same Project
  authority pair.
- The new constraint does not alter Project ownership
  semantics. Ownership remains governed by
  `projects.user_id` per ADR-081.

ORM representation (the UMS-03D ORM must declare this on
the `Project` table metadata):

```python
UniqueConstraint(
    "id",
    "user_id",
    name="uq_projects_id_user_id",
)
```

Migration representation (the UMS-03D first migration must
create the constraint before it creates the
`memory_records` composite FK). UMS-03C-B explicitly rejects
a separate Alembic prerequisite revision. The UMS-03D first
migration is the single additive persistence-groundwork
revision; its frozen upgrade scope becomes:

```text
1. add uq_projects_id_user_id
2. create memory_records
3. create memory_persona_links
4. create memory_provenance
5. create their frozen indexes / constraints
```

The `memory_records` composite FK
`(project_id, user_id) → projects (id, user_id)` is created
only after step 1 has succeeded. Step 1 cannot succeed if
`projects` has a row whose `(id, user_id)` would violate the
new constraint; that cannot happen under the live schema
because `id` is already unique.

The UMS-03D downgrade must drop all UMS-03D canonical-memory
schema objects before dropping the enabling Project
constraint, because dropping the constraint first would leave
the memory composite FK pointing at an unsupported target
during the gap. The frozen downgrade order is:

```text
1. drop memory_provenance
2. drop memory_persona_links
3. drop memory_records
4. drop uq_projects_id_user_id
```

UMS-03D qualification on disposable PostgreSQL must prove
all of the following:

- `uq_projects_id_user_id` exists after the upgrade.
- `memory_records (project_id, user_id) → projects (id,
  user_id)` is accepted by PostgreSQL.
- An existing-schema upgrade preserves every `projects` row
  byte-for-byte (the constraint changes schema, never data).
- An account-A memory row referencing an account-A Project
  is accepted.
- An account-A memory row referencing an account-B Project
  is rejected at the relational boundary, with the rejection
  attributable to the composite FK rather than to
  application-only enforcement.

This sub-section is the only UMS-03C/03C-A change introduced
by UMS-03C-B. All other §4.16 decisions (memory identity,
semantic species, payload strategy, review/activation
ordering, Persona-link schema, provenance schema, FK delete
behavior, index strategy, first-migration posture except as
extended here, compatibility-reader posture) are unchanged.

#### 4.16.2c UMS-03D implementation checkpoint

UMS-03D introduced matching SQLAlchemy ORM metadata and one
Alembic revision (`f6b0d3e8c5a2`) that mechanically implements
the §4.16 contract and the §4.16.2b precondition. UMS-03D
qualification on disposable PostgreSQL 17 confirmed:

- the migration is one additive revision with predecessor
  `e5a9c2f7b4d1`;
- the migration adds `uq_projects_id_user_id` before
  creating any dependent memory FK;
- the canonical memory tables `memory_records`,
  `memory_persona_links`, and `memory_provenance` exist empty
  after the migration;
- the composite FK
  `memory_records (project_id, user_id) → projects (id, user_id)`
  is accepted by PostgreSQL and live in the resulting schema;
- the frozen review/activation ordering CHECK
  (`activated_at IS NULL OR (reviewed_at IS NOT NULL AND
  activated_at >= reviewed_at)`) accepts equal timestamps
  and rejects earlier-than-review activation;
- the canonical tables are not yet runtime read/write
  authority — legacy memory sources remain authoritative.

UMS-03D is a structural implementation slice only. It does not
implement compatibility readers, runtime readers, runtime
writers, dual reads, legacy backfill, authority cutover, or
export / restore. The UMS-03D proof receipt
(`docs/architecture/proofs/runtime/2026-09-07-ums03d-canonical-memory-persistence-proof.md`)
records the qualification evidence. The frozen §4.16 contract
is unchanged by UMS-03D.

#### 4.16.3 Persona-attribution table — `memory_persona_links`

`memory_persona_links` is the typed stable-Persona attribution
relationship table for canonical memory records. It expresses
attribution only; it never confers memory ownership.

| Column                 | Type                                    | Null    | Default | Authority meaning |
|------------------------|-----------------------------------------|---------|---------|-------------------|
| `link_id`              | `String(36)` (UUID) PK                  | NOT NULL | —      | Stable link identity |
| `memory_id`            | `String(36)` FK `memory_records.memory_id` | NOT NULL | —  | Memory record being annotated |
| `user_id`              | `String(255)` FK `users.id`             | NOT NULL | —      | Account of the memory; CASCADE on user delete |
| `persona_subject_id`   | `String(36)` FK `persona_subjects.persona_subject_id` | NOT NULL | — | Stable Persona subject |
| `persona_user_id`      | `String(255)` FK `users.id`             | NOT NULL | —      | Account of the Persona subject; RESTRICT on Persona subject's account deletion (covered by Persona subject CASCADE) |
| `link_kind`            | `String(32)`                            | NOT NULL | —      | Closed `MemoryPersonaLinkKind` value |
| `created_at`           | `TIMESTAMP(timezone=True)`              | NOT NULL | `now()`| Link creation timestamp |

DB-enforced invariants:

- `FOREIGN KEY (memory_id, user_id) REFERENCES
  memory_records(memory_id, user_id) ON DELETE CASCADE` — the
  link follows its memory's account; deleting a memory
  removes its links.
- `FOREIGN KEY (persona_subject_id, persona_user_id) REFERENCES
  persona_subjects(persona_subject_id, user_id) ON DELETE
  RESTRICT` — a Persona subject with active memory links
  cannot be deleted; the application must first retire the
  Persona subject (UMS-02 governance) and accept the link
  retention as historical evidence. This mirrors the
  §4.5.6 historical-binding retention rule.
- `CHECK (user_id = persona_user_id)` — DB-enforced
  same-account integrity between the memory and the
  attributed Persona subject. This is the same-account rule
  required by §4.9 and §4.5.7 and the UMS-03A cross-account
  attribution prohibition.
- `CHECK (link_kind IN ('captured_under', 'suggested_by',
  'associated_with'))` — derived from the canonical
  `MemoryPersonaLinkKind` token domain. Named
  `memory_persona_links_link_kind_check`. No additional
  relationship kinds are accepted.
- `UNIQUE (memory_id, persona_subject_id, link_kind)` — at
  most one link of each kind per memory per Persona subject.
  Multiple Persona subjects and multiple kinds are allowed on
  the same memory; the constraint is a per-(memory, persona,
  kind) dedup rule, not a per-memory or per-persona rule.

`persona_user_id` is a denormalized copy of the linked
`persona_subjects.user_id`. It exists so the same-account CHECK
can be expressed at the relational boundary without a
sub-select. It must always equal `persona_subjects.user_id` for
the row referenced by `(persona_subject_id, persona_user_id)`;
that equality is enforced by the composite FK to
`persona_subjects`. No mutable `PersonaProfile` FK is present;
no `PersonaProfile.id` is a valid target here. Display names,
similarity scores, prompts, and avatars are not authority for
the link identity.

#### 4.16.4 Provenance table — `memory_provenance`

`memory_provenance` is the first-class durable lineage row for
every canonical memory record. It preserves external lineage
without becoming a parallel authority surface.

| Column                       | Type                          | Null    | Default | Authority meaning |
|------------------------------|-------------------------------|---------|---------|-------------------|
| `provenance_id`              | `String(36)` (UUID) PK        | NOT NULL | —      | Stable provenance identity |
| `memory_id`                  | `String(36)` FK `memory_records.memory_id` | NOT NULL | — | Memory record this lineage belongs to |
| `user_id`                    | `String(255)` FK `users.id`   | NOT NULL | —      | Account of the memory; CASCADE on user delete |
| `source_system`              | `String(32)`                  | NOT NULL | —      | Closed source-system set; see below |
| `source_record_id`           | `String(255)`                 | NULL    | NULL    | Stable identifier of the source row when present |
| `source_thread_id`           | `BigInteger` FK `chat_threads.id` | NULL | NULL   | Canonical chat-thread reference when present |
| `source_message_id`          | `BigInteger` FK `chat_messages.id` | NULL | NULL  | Canonical chat-message reference when present; `SET NULL` on chat-message delete |
| `source_import_job_id`       | `String(36)`                  | NULL    | NULL    | Opaque import-job ref when present (no relational FK today; the import-job table is not a stable public surface) |
| `source_export_fingerprint`  | `String(128)`                 | NULL    | NULL    | Opaque export hash when the material came from an export |
| `source_subject_kind`        | `String(32)`                  | NULL    | NULL    | `chat`, `vault`, `importer`, `classifier`, or future-registered |
| `source_subject_id`          | `String(255)`                 | NULL    | NULL    | Stable identifier of the originating surface entity when present |
| `is_imported`                | `Boolean`                     | NOT NULL | `false` | Imported-vs-native posture; provenance is durable even for native rows but `is_imported=true` rows came from an external source |
| `extensions`                 | `JSONB`                       | NULL    | NULL    | Auxiliary non-authority metadata only |
| `created_at`                 | `TIMESTAMP(timezone=True)`    | NOT NULL | `now()`| Provenance row creation timestamp |

DB-enforced invariants:

- `FOREIGN KEY (memory_id, user_id) REFERENCES
  memory_records(memory_id, user_id) ON DELETE CASCADE` —
  provenance follows the memory and its account.
- `CHECK (source_system IN ('codexify', 'openai',
  'anthropic', 'future_registered'))` — closed source-system
  vocabulary matching the UMS-03A §4.11 spine. The trailing
  `future_registered` value is the future-proofing slot; no
  new value is admitted by this contract.
- `CHECK (source_subject_kind IS NULL OR source_subject_kind
  IN ('chat', 'vault', 'importer', 'classifier',
  'future_registered'))` — closed source-surface vocabulary.
  Same `future_registered` future-proofing slot; no additional
  values are accepted by this contract.
- The `extensions` JSONB column must never be a source of
  authority: a separate application-layer invariant (and a
  future ADR-gated migration if needed) shall reject any
  authorization decision that consults `extensions` for
  ownership, scope, activation, review, or Persona identity.

Provenance multiplicity is **one-to-many**. A single canonical
memory may have multiple `memory_provenance` rows: e.g., one
`source_system = 'codexify'` row for the native creation event,
one `source_system = 'openai'` row for the import that
introduced the candidate, and one `source_system = 'codexify'`
row for a later user correction. This is the relational
counterpart of the UMS-03A evidence/revision append-only
semantics for ordinary memories. There is no
`(memory_id, source_system)` UNIQUE constraint: collapsing
multiple lineage records by source would erase the very
revision evidence the table exists to preserve.

#### 4.16.5 Payload strategy decision

The UMS-03A deferred question "shared typed columns vs.
species-specific relational tables vs. JSONB species payload"
is resolved as follows:

- **Authority-bearing data** (account ownership, Project
  scope, semantic species, review / activation timestamps,
  pin / hold, identity, FK targets) lives in **typed
  relational columns** on `memory_records` and its child
  tables. None of this data is stored in JSON.
- **Species-specific non-authority content** lives in
  **typed columns on the same canonical envelope**
  (`text_content`, `fact_key`, `fact_value`,
  `fact_confidence`). The `semantic_species` CHECK
  constraints above enforce which combination is valid per
  species. This preserves semantic distinction (the three
  species keep their distinct shapes) without inventing a
  parallel table for each species or flattening the payload
  into one untyped text column.
- **Auxiliary non-authority metadata** (e.g., a future
  import-routing note or a future export-side annotation)
  lives in `extensions JSONB` on each table that needs it.
  `extensions` is explicitly forbidden from carrying any
  authority question's answer; ownership, scope, Persona
  identity, activation, and review never come from JSON.

The rejected alternatives:

- A single generic `content JSONB` per row was rejected
  because it would force the three species to share one
  payload shape, erasing the UMS-03A semantic distinction
  between episodic memory and personal facts.
- A separate relational table per species (e.g.,
  `memory_episodic_payload`, `memory_verified_fact_payload`,
  `memory_candidate_fact_payload`) was rejected because
  the three species are all governed by the same envelope
  doctrine, share the same FK targets, and the typed
  columns above already carry the species-specific content
  without a join.

#### 4.16.6 Governance state physical representation

The UMS-03A distinctions (`stored != reviewed != activated
!= explicitly retrievable != ambiently influential`) are
physically represented as follows, with no new closed
protocol-token vocabulary invented:

- `stored` — the row exists. No column is required; row
  presence is the representation.
- `reviewed` — represented by `reviewed_at TIMESTAMPTZ NULL`.
  `NULL` means unreviewed; non-NULL is the review timestamp.
- `activated` — represented by `activated_at TIMESTAMPTZ
  NULL`. `NULL` means not activated; non-NULL is the
  activation timestamp. The CHECK constraint
  `activated_at IS NULL OR (reviewed_at IS NOT NULL
  AND activated_at >= reviewed_at)`
  enforces the canonical review-before-activation ordering
  recorded in §4.16.2a: activation may be recorded at the
  same instant as review, and activation may never be
  recorded before review.
- `explicitly retrievable` — not stored; computed at read
  time from `(account authorization, scope, activation,
  explicit recall grant)` per §3.5 and §6.1. No canonical
  column is added for it.
- `ambiently influential` — not stored; computed at read
  time per §3.5. No canonical column is added for it.

Boolean and timestamp columns preserve all required
distinctions without losing current source semantics. No
monolithic lifecycle enum is introduced. The two
lifecycle-event timestamps plus the pin / hold booleans
are the full governance physical representation.

#### 4.16.7 Cross-table integrity invariants

- **Account ownership** of any canonical memory row is
  expressed by `memory_records.user_id` and DB-enforced via
  `FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE
  CASCADE`.
- **Project scope same-account** is DB-enforced by the
  composite FK `(project_id, user_id) REFERENCES
  projects(id, user_id)` on `memory_records` when
  `project_id IS NOT NULL`. Cross-account Project scope
  cannot be silently permitted.
- **Persona-link same-account** is DB-enforced by the
  composite FKs on `memory_persona_links` plus the
  `CHECK (user_id = persona_user_id)` constraint.
- **Provenance same-account** is DB-enforced by the
  composite FK `(memory_id, user_id)` on `memory_provenance`.
- **Stable identity, not display**, is the rule for every
  FK target. `memory_id` is a UUID; `persona_subject_id` is
  a UUID; `user_id` is the canonical `users.id` string; no
  display name, prompt, or tag is a key.
- **PersonaProfile is absent from durable attribution
  identity.** No `memory_persona_links` column references
  `persona_profiles`; the only target is
  `persona_subjects.persona_subject_id`.

#### 4.16.8 Foreign-key delete behavior

| FK reference                          | On parent delete | Rationale |
|---------------------------------------|------------------|-----------|
| `memory_records.user_id → users.id`   | CASCADE          | Aligns with `projects.user_id` and `persona_subjects.user_id`; account teardown removes the account's memory. |
| `memory_records.project_id → projects.id` | RESTRICT    | Prevents Project deletion from silently converting Project-scoped memory into account-wide memory. Application must detach / archive first. |
| `memory_persona_links.memory_id → memory_records.memory_id` (composite) | CASCADE | A memory and its links are deleted together. |
| `memory_persona_links.user_id → users.id` | CASCADE      | Account teardown removes the account's links. |
| `memory_persona_links.persona_subject_id → persona_subjects.persona_subject_id` (composite) | RESTRICT | A Persona subject with active memory links cannot be deleted; retirement is governed by UMS-02. |
| `memory_provenance.memory_id → memory_records.memory_id` (composite) | CASCADE | A memory and its provenance are deleted together. |
| `memory_provenance.user_id → users.id` | CASCADE          | Account teardown removes the account's provenance. |
| `memory_provenance.source_thread_id → chat_threads.id` | RESTRICT (default) | Avoids silently losing source-thread identity when a thread is deleted; chat-thread deletion is rare and should be a separate contract decision. |
| `memory_provenance.source_message_id → chat_messages.id` | SET NULL | Aligns with `personal_fact_evidence.source_message_id`; allows chat-message deletion without losing the memory's existence, while preserving the rest of the provenance row. |

Permanent erasure semantics are explicitly not implemented
here; the contract documents that UMS-11 owns permanent purge
and the surviving `memory_purge_tombstone` semantics.

#### 4.16.9 Index strategy

The minimum required indexes for the canonical envelope are:

- `memory_records (user_id)` — account-scoped memory lookup.
- `memory_records (user_id, project_id)` — account +
  Project lookup, with a partial unique index
  `(user_id, project_id, semantic_species)` to be defined
  later by the implementation slice if multi-row semantics
  are required.
- `memory_records (user_id, semantic_species)` — account +
  species lookup.
- `memory_records (user_id, activated_at)` — ambient-
  eligible lookup at read time.
- `memory_persona_links (user_id)` — account-scoped link
  lookup.
- `memory_persona_links (persona_subject_id)` — Persona-
  attributed memory lookup.
- `memory_persona_links (memory_id, link_kind)` — already
  covered by the existing `UNIQUE (memory_id,
  persona_subject_id, link_kind)` constraint, but the
  implementation may add a non-unique supporting index if
  its query plan requires it.
- `memory_provenance (memory_id)` — provenance lookup for
  one memory.
- `memory_provenance (user_id, source_system)` — account +
  source lookup.
- `memory_provenance (source_thread_id)` — only when
  `source_thread_id IS NOT NULL`; covered by the FK index
  on that column.

The following derived-state indexes are explicitly
**excluded** from canonical persistence: ranking, heat,
embedding, recency score, working-set membership, suggestion
ranking, and UI grouping. Those concerns are owned by UMS-10
and will not be persisted as canonical `memory_records`
data.

#### 4.16.10 First-migration posture

UMS-03D is authorized to introduce the canonical schema
above as one new Alembic revision whose properties are:

- The migration is **additive only**.
- The three new tables are created empty.
- No legacy backfill is performed.
- No legacy source row is mutated, deleted, or read by the
  migration.
- No runtime writer is redirected to the canonical tables.
- No runtime reader is redirected to the canonical tables.
- No compatibility reader is implemented by this migration.
- No authority transfer occurs. The pre-migration authority
  order remains in force after the migration:

  ```text
  legacy source row         = durable authority
  memory_records            = structurally available but not
                              yet runtime authority
  ```

The migration's acceptance criteria are:

- `alembic upgrade head` succeeds on a clean disposable
  PostgreSQL 17 instance.
- `alembic upgrade head` succeeds on a disposable PostgreSQL
  17 instance seeded with the current live schema.
- `alembic downgrade -1` either succeeds and is lossless for
  the new tables (the new tables are dropped) or is
  explicitly forbidden by the revision with a documented
  reason.
- All canonical CHECK / UNIQUE / FK constraints are
  present in the resulting schema.
- No legacy data was read, mutated, or migrated by the
  upgrade.

The runtime cutover that promotes the canonical tables to
durable authority belongs to a later UMS-03 slice and is
explicitly not in UMS-03D.

#### 4.16.11 ORM/Alembic parity requirement

UMS-03D must introduce the SQLAlchemy ORM metadata and the
Alembic migration together. No migration-only table may be
added without matching `Base` metadata. No ORM-only class
may exist without matching Alembic schema. The future
implementation must preserve the existing generic
PostgreSQL Alembic/ORM parity smoke used by other UMS
slices (e.g., UMS-02C).

#### 4.16.12 Compatibility reader relationship to persistence

A compatibility reader projects legacy rows into the canonical
envelope shape without writing to `memory_records`. The
projection is structurally compatible with the schema frozen
in this section. The compatibility reader:

- must not write canonical rows;
- must not assign canonical durable authority;
- must not infer missing ownership, Project scope, or
  Persona attribution;
- must not upgrade review or activation state;
- must not destroy provenance;
- must fail closed for any row whose canonical envelope
  shape cannot be constructed without inventing authority
  (per UMS-03A §4.14).

UMS-03E implemented the first such reader for the
`memory_entries` source family only. The reader lives in
`guardian.core.memory_compatibility` and exposes one public
function, `read_memory_entry_projection(session, *,
authenticated_account_id, memory_entry_id)`, returning a
`MemoryCompatibilityProjection` dataclass or `None`. The
projection type is intentionally not registered in
`Base.metadata`; it is a semantic read view, not an ORM
mirror of `memory_records`.

UMS-03F added the second reader for the verified + active
`personal_facts` subset only. It exposes
`read_verified_personal_fact_projection(session, *,
authenticated_account_id, personal_fact_id)`, enforcing the
canonical eligibility predicate
`status='verified' AND is_active=true` in the query itself.
Candidate / disputed / archived / inactive rows return
`None` identically to not-found / not-owned. The same
`MemoryCompatibilityProjection` dataclass is reused; the
verified-fact shape populates `fact_key`, `fact_value`,
`confidence`, `last_confirmed_at`, `guardrail_metadata`,
`evidence` (full one-to-many lineage), and `revisions`
(historical only). Evidence rows whose `source_type` is
outside the closed vocabulary, or whose `evidence_meta` is
self-referential on the parent fact id, fail closed with
`MemoryCompatibilityReadError`. The candidate / unreviewed
fact compatibility is not covered by UMS-03F and remains
deferred. The compatibility reader was explicitly not in
UMS-03D.

#### 4.16.13 Explicit deferrals

The following are outside UMS-03C and remain deferred to
later slices:

- ORM model implementation (UMS-03D);
- Alembic migration implementation (UMS-03D);
- PostgreSQL qualification (UMS-03D proof slice);
- compatibility reader implementation (later UMS-03 slice);
- runtime write path (later UMS-03 slice);
- runtime read cutover (later UMS-03 slice);
- legacy backfill (later UMS-03 slice);
- export / restore implementation (UMS-04);
- Vault UI (UMS-05);
- explicit memory commands (UMS-06);
- Persona-aware recall (UMS-07);
- automatic suggestions (UMS-09);
- heat / decay projection (UMS-10);
- permanent erasure semantics (UMS-11).

#### 4.4 Activation projection

Heat and ranking state are derived:

```text
memory_activation_projection
├── record_id
├── heat_score
├── activation_count
├── last_activated_at
├── last_decay_evaluated_at
├── projection_version
└── rebuilt_at
```

Projection loss may degrade ranking but cannot change content, approval,
ownership, lifecycle, or direct recall. Lifecycle transition timestamps such as
`dormant_at` and `retired_at` remain canonical because the transition itself is
canonical.

## 5. Mutation authority

### 5.1 Origin-sensitive creation

| Source | Stored posture | Explicit recall | Ambient context |
| --- | --- | --- | --- |
| User: “Remember that I prefer X” | approved, active, revisioned | yes | yes when all policy gates pass |
| User: “Remember this” referring to assistant, web, tool, or mixed content | exact target preview or pending proposal | yes during preview/review | only after exact confirmation |
| Automatic post-turn classifier | pending candidate | review surface only unless explicitly requested | no |
| OpenAI/Anthropic memory import | dormant, `explicit_recall_only` record; optional candidate fact | yes through a turn-scoped grant | no until approved and activated |
| Web/tool claim about the user | quarantined evidence | explicit inspection only | never by itself |
| Assistant personality/identity inference | candidate/quarantine | explicit inspection only | no until explicit approval and subtype policy allows |

The user statement itself supplies approval only when it contains a complete,
unambiguous proposition to remember. A command that points at external or
generated content must resolve the exact proposition before commitment.

### 5.2 Intent receipts

Authority-changing model-mediated actions require a server-created
`MemoryIntentReceipt` bound to:

```text
account_user_id
source_user_message_id
request_id
intent_kind
target_record_id nullable
content_digest or preview_digest
allowed_mutation
issued_at
expires_at
consumed_at nullable
```

The model cannot mint or broaden a receipt. A receipt is single-use for writes.
Vault actions use an equivalent authenticated user-action receipt.

### 5.3 Edit and reapproval behavior

| Mutation source | Required result |
| --- | --- |
| User edits content directly in the Vault | authoritative revision; remains approved because the UI presents a direct user edit |
| User explicitly dictates replacement content | authoritative revision; may remain approved; requires a matching intent receipt |
| Agent proposes an edit | preview only; no mutation until user confirmation |
| Importer or classifier suggests changed meaning | new pending revision or new candidate; cannot overwrite approved content |
| User changes Project scope | explicit revisioned action; Project authority revalidated |
| User changes persona association | explicit revisioned action; persona ownership revalidated |
| Agent proposes retire/restore | proposal only; action requires explicit user intent |
| System decay transitions active to dormant | audited policy transition; forbidden while held |

A unique record ID resolves the target but does not establish authority.
Optimistic version checks prevent silent last-write-wins replacement.

### 5.4 Pin, hold, retire, restore, and purge

- Pin/unpin changes ranking metadata only.
- Hold/release controls whether decay may change lifecycle.
- Retire is reversible and removes ordinary ambient eligibility.
- Restore returns a retired record to its pre-retirement governed posture only
  through an explicit account-principal action; it does not auto-approve a
  formerly unapproved record.
- Purge is permanent and follows Section 12.

## 6. Recall authority and routing

### 6.1 Human request versus executable grant

A human-facing recall request may ask for Project, persona, source, review, or
lifecycle widening. Those fields are request preferences, not permissions.

Guardian derives a bounded capability:

```text
MemoryRecallGrant
├── account_user_id
├── source_user_message_id or authenticated_vault_action_id
├── request_id
├── allowed_project_scope
├── allowed_persona_scope
├── allowed_review_states
├── allowed_lifecycle_states
├── allowed_source_classes
├── attribution_required
├── issued_at
└── expires_with_request
```

Rules:

- The model cannot mint, widen, persist, replay, or reuse a grant.
- The repository and Context Broker require the grant for any non-ambient
  record.
- The grant is bound to one authenticated account principal and one request.
- Wrong-account, expired, replayed, or scope-expanded grants fail closed.
- Pending, rejected, disputed, dormant, retired, imported, or quarantined
  content requires explicit user intent naming the relevant widening.
- Explicit recall does not approve, activate, restore, edit, pin, hold, or
  change context posture.

### 6.2 Ordinary recall order

Persona filtering applies inside every durable scope:

1. Active-thread evidence.
2. Active Project:
   - records with no persona association;
   - records associated with the active persona subject.
3. Account scope:
   - records with no persona association;
   - records associated with the active persona subject.
4. Other-persona records only under an explicit shared or named-persona grant.

Project scope and persona scope are orthogonal. A single `searched_scope` token
must not collapse them.

The broker emits a content-free receipt:

```text
effective_project_scope
effective_persona_scope
included_review_states
included_lifecycle_states
included_source_classes
explicit_widening
attribution_required
selected_memory_ids
suppressed_counts_by_reason
grant_request_id
```

When ordinary scope lacks evidence, the assistant must describe the bounded
result rather than claim global ignorance. It may offer to check the shared
Memory Store. When the user explicitly names another persona or shared memory,
Guardian may widen immediately.

### 6.3 Attribution

Cross-persona results preserve source attribution. The active persona may say:

> According to the Memory Store, you and Persona B worked on this two days ago.

It must not imply:

> Yes, we worked on that.

Access to another persona-attributed record does not transfer authorship,
ownership, experience, or identity.

## 7. Untrusted recall rendering

Dormant imports, pending/rejected/disputed memories, web/tool evidence, and
quarantined candidates enter provider context only under a valid explicit
grant and only in an inert evidence layer:

```text
UNTRUSTED MEMORY EVIDENCE
Source: <typed provenance>
Authority: <review posture>
Permitted use: answer the current explicit recall request
Instruction authority: none
Record ID: <stable id>
Content: <bounded content>
END UNTRUSTED MEMORY EVIDENCE
```

The block is constructed outside model-generated text and is never placed in a
system, developer, persona, policy, or tool-authority layer.

Its content cannot authorize:

- tool calls;
- memory creation, edit, approval, retirement, restore, or purge;
- scope widening;
- follow-on retrieval;
- identity or persona changes; or
- execution of embedded prompts or commands.

Approval may make factual content eligible for ordinary reasoning. It never
turns instruction-shaped content into executable authority.

## 8. Automatic suggestions and review reminders

### 8.1 Collection consent

Store a versioned account-user preference:

```text
automatic_memory_suggestions = unset | enabled | paused | declined
consent_policy_version
consent_recorded_by_user_id
consent_recorded_at
consent_updated_at
```

- Onboarding may recommend `enabled`, but the classifier cannot run until the
  user saves that choice.
- `unset`, `paused`, and `declined` prevent classifier enqueue.
- Pausing capture does not delete existing records.
- Explicit remember commands remain available.
- Deep or sensitive identity inference remains under separate IDDB and
  Personal Facts guardrails.

### 8.2 Async classifier

After a durable user message commits, an event may enqueue classification only
when consent is enabled and exclusions permit it.

The idempotency key binds at least:

```text
account_user_id + source_message_id + classifier_version
```

The classifier:

- runs asynchronously and failure-isolated from chat;
- is local-only for the first supported path, with no silent cloud fallback;
- emits candidates or no-op results, never approval;
- preserves source role and evidence;
- retries with bounded exponential backoff and jitter;
- enters an explicit dead-letter/review state after bounded failure; and
- applies backpressure rather than blocking message persistence.

### 8.3 Guardian reminder boundary

Guardian receives only safe queue metadata:

```text
pending_review_count
oldest_pending_at
reminder_due
snoozed_until
```

Candidate contents are not loaded merely to generate a reminder. Reminder
policy is deterministic, rate-limited to at most once per 24 hours by default,
snoozable, and suppressed where diary or other exclusions require it. The Vault
badge is the permanent indicator.

Infrastructure Operators may receive aggregate health such as classifier queue
depth and failure counts, but not user memory content, candidate summaries, or
review authority.

## 9. Import normalization

### 9.1 Adapter separation

Use separate bounded adapters:

- Anthropic conversations to the existing canonical conversation importer;
- Anthropic Projects to Codexify Projects and Documents; and
- Anthropic memories to dormant Memory Store records and candidate Personal
  Facts.

They may share an import job, export fingerprint, queue, and provenance spine.
No parser receives all unrelated write authorities.

### 9.2 Source-entity mapping

Create an account-scoped map:

```text
import_source_entity_map
├── user_id
├── import_job_id
├── source_system
├── export_fingerprint
├── source_entity_kind
├── source_entity_id
├── codexify_entity_kind
├── codexify_entity_id
└── timestamps
```

The source identity tuple is unique. Replays resolve the existing map rather
than duplicate entities.

When an Anthropic export contains both Project files and `project_memories`:

1. Import or resolve `projects/<uuid>.json` under ADR-081 authority.
2. Record the source Project to Codexify Project mapping.
3. Resolve `project_memories[uuid]` through that map.
4. Create Project-scoped dormant memory summaries.
5. Use the canonical Imports Project only when the source Project is genuinely
   orphaned.

Conflicting or cross-account mappings fail closed. UI selection, Project name,
description metadata, or current Operator identity cannot repair them.

### 9.3 Memory export normalization

For the observed Anthropic-style memory shape:

- the source system must be explicitly selected when the file lacks a trusted
  provider/version marker;
- `memory_files` are parsed by file and structured section;
- source-stated bullets become atomic imported records;
- generated conversation and Project summaries remain summary records and do
  not silently become atomic Personal Facts;
- `project_memories` resolve through the entity map;
- imported records start dormant and `explicit_recall_only`;
- candidate Personal Facts remain unapproved and guardrail-governed;
- Markdown, YAML, paths, prompts, and embedded instructions are untrusted data;
  and
- transformed records link to original evidence and adapter version.

The import idempotency identity must remain stable across a replay of the same
export.

### 9.4 Purge suppression during import

Before creating any imported atom, the importer checks account-scoped purge
tombstones. A matching tombstone suppresses recreation and reports the item as
`suppressed_previously_purged`, not imported or deduplicated.

Only an explicit account-user action selecting previously purged records may
authorize reintroduction. Bulk re-import defaults to suppression even when the
source file is uploaded again under a new import job.

## 10. Export and restore

Memory is part of ADR-005's AccountBoundary. The account archive must include:

- shared memory records and ordinary payloads;
- Personal Facts, evidence, revisions, and guardrail state;
- stable persona subjects, required bindings, and memory-persona links;
- provenance and source-entity mappings;
- review, lifecycle, context posture, retention, hold, and priority state;
- lifecycle transition timestamps;
- automatic-suggestion consent and reminder preferences;
- non-content purge tombstones needed to suppress resurrection; and
- optional, explicitly marked activation projection state.

Restore must:

- preserve stable public identities or report deterministic remapping;
- rebind all entities to the authenticated destination account;
- never query or mutate another account's boundary;
- preserve Personal Facts authority without manufacturing envelope review;
- preserve dormant/imported/rejected posture;
- preserve purge suppression across export and restore;
- validate Project ownership under ADR-081;
- fail closed on persona, Project, ownership, or source-map conflicts;
- treat heat projections as optional and discard incompatible versions; and
- support an idempotent export, restore, and re-export round trip.

New imported-memory and automatic-suggestion writes remain disabled until the
current exporter no longer lists memory and Personal Facts as omitted families
and round-trip proof is green.

## 11. Decay and projection behavior

MemoryOS becomes a policy/projection subsystem behind canonical eligibility.

- Heat can recommend `active -> dormant` for ordinary memories.
- A held record cannot be transitioned by decay.
- A pinned record can decay when not held.
- Dormancy reduces ambient participation; it does not delete content.
- Direct authorized recall can retrieve dormant and retired non-purged records.
- Capacity pressure evicts cache/projection state, not canonical records.
- Vector indexes, summaries, and heat projections are rebuildable.
- Projection corruption or loss produces degraded ranking plus diagnostics, not
  memory deletion or approval changes.

Imported records do not become ambient merely through heat or repeated direct
recall. Activation and approval remain explicit authority transitions.

## 12. Permanent erasure and resurrection suppression

Permanent purge is mandatory before supported user-facing release.

The operation requires an explicit, authenticated account-user action and a
preview of the exact target and affected linked evidence. It removes or
cryptographically destroys:

- canonical content;
- content-bearing revisions and evidence excerpts;
- persona links where they reveal the erased record;
- vectors, summaries, caches, and heat projections;
- queued derived work and retry payloads; and
- exported working artifacts under the application's immediate control.

The purge may retain only a minimum non-content tombstone:

```text
memory_purge_tombstone
├── user_id
├── opaque purged-record fingerprint
├── source_system nullable
├── source_entity_kind nullable
├── versioned source-atom fingerprint nullable
├── purge_receipt_id
├── purged_at
└── suppress_reimport = true
```

The source-atom fingerprint is a versioned, deterministic, non-reversible
digest over the minimum source identity needed for replay detection. It must
not contain content, tags, excerpts, embeddings, plaintext source payloads, or
reversible source identifiers. It is exported and restored so suppression
survives migration to another Codexify instance.

Re-import rules:

- the same source atom is suppressed across repeated imports and new import
  jobs;
- suppression is reported without recreating content;
- importer retries are idempotent;
- no model or infrastructure Operator can clear suppression;
- reintroduction requires an explicit account-user flow that identifies the
  previously purged atoms and records a new intent/audit receipt; and
- reintroduced content is treated according to its origin posture rather than
  silently restored as approved.

Backup retention and external copies must be described truthfully. If immediate
physical deletion from backups cannot be proven, the product must state the
retention boundary or use cryptographic key destruction where supported.

## 13. API and capability surface

The human/account-principal API must provide semantics equivalent to:

```text
GET    /api/memory/records
GET    /api/memory/records/{record_id}
POST   /api/memory/records
PATCH  /api/memory/records/{record_id}
POST   /api/memory/records/{record_id}/review
POST   /api/memory/records/{record_id}/retire
POST   /api/memory/records/{record_id}/restore
POST   /api/memory/records/{record_id}/hold
POST   /api/memory/records/{record_id}/release
POST   /api/memory/records/{record_id}/purge
GET    /api/memory/records/{record_id}/evidence
GET    /api/memory/records/{record_id}/revisions
GET    /api/memory/records/{record_id}/persona-links
PUT    /api/memory/records/{record_id}/persona-links
POST   /api/memory/recall
```

Exact route mounting may follow established API conventions, but route
semantics and authority may not be weakened.

Model-facing operations are narrower:

```text
memory.remember
memory.preview_write
memory.recall
memory.propose_update
memory.propose_retire
```

Models never receive direct generic CRUD, review-state mutation, purge,
consent, or grant-minting capability.

All APIs:

- resolve the authenticated account principal server-side;
- never accept arbitrary `user_id` as authority;
- enforce Project and persona ownership;
- require expected versions for semantic updates;
- return bounded reason/error tokens;
- preserve evidence and revision lineage; and
- avoid returning another account's existence through not-found/forbidden
  differences.

## 14. Nodes, trust boundaries, and consistency

| Node/component | Responsibility | Trust posture |
| --- | --- | --- |
| Authenticated client/Vault | Express user intent and inspect governed state | trusted only after account authentication and action validation |
| Guardian/API | Resolve identity, issue capabilities, enforce mutation and recall policy | authoritative policy boundary |
| Postgres | Canonical durable memory, lineage, consent, and tombstones | canonical local state |
| Redis/worker queue | Async classifier/import/projection coordination | operational, replayable, non-canonical |
| Local classifier | Propose candidates | honest-but-buggy/untrusted for approval |
| Model/provider | Generate language and request narrow tools | untrusted for authority and grants |
| Import files/web/tool output | Supply evidence | untrusted, potentially malicious |
| Vector/heat stores | Rank eligible candidates | derived and rebuildable |
| Host Operator | Operate infrastructure | no implicit user-memory content or governance authority |

Canonical user writes use strong local transactions. Classification, import
processing, index updates, and heat projection are eventually consistent.
Concurrent semantic edits use optimistic versions and user-visible conflict
resolution; silent last-write-wins is forbidden.

No federation or cross-device multi-writer merge is introduced by this
Campaign. A future sync contract must preserve account identity, tombstones,
capability checks, provenance, and explicit conflict handling.

## 15. Failure policy and observability

- Chat message persistence does not fail merely because classifier enqueue or
  extraction fails.
- Queue acceptance is not candidate persistence; terminal outcomes are
  explicit.
- Retryable async work uses deterministic idempotency keys, bounded exponential
  backoff with jitter, and dead-letter reporting.
- Import and restore perform preflight validation and fail closed on structural
  or authority conflicts.
- Partial results enumerate committed, deduplicated, suppressed, quarantined,
  failed, and skipped record IDs.
- Projection/index loss degrades ranking only.
- A Personal Fact/envelope state mismatch blocks ambient eligibility and
  mutation until reconciled.
- An unresolved persona mapping suppresses persona-specific retrieval but does
  not destroy the record.
- Purge fan-out is retryable and remains incomplete until every canonical and
  derived target has a terminal receipt.
- Metrics and traces carry IDs, counts, reason tokens, durations, queue depth,
  and projection versions; they do not carry memory contents or excerpts.

## 16. Proof and release gates

Later implementation is incomplete until tests prove:

1. Personal Facts have one review/activation authority and mismatches fail
   closed.
2. Review, lifecycle, posture, hold, and priority remain orthogonal.
3. Pin does not approve or suspend decay; hold does suspend decay.
4. Persona history survives `PersonaProfile` replacement and cross-persona
   output retains attribution.
5. Forged, replayed, expired, and broadened recall grants fail.
6. Untrusted memory cannot authorize prompts, tools, retrieval, or writes.
7. Direct Vault edits and explicit dictated edits create revisions, while
   importer/classifier edits remain pending.
8. Classifier enqueue is impossible before recorded consent.
9. Source Project UUIDs resolve through the entity map and only true orphans use
   the Imports Project.
10. Export/restore preserves all canonical memory families and purge
    suppression without cross-account queries.
11. Heat projection can be dropped and rebuilt without changing canonical
    truth.
12. Retired and dormant records remain explicitly retrievable until purged.
13. Purge removes canonical and derived content and prevents silent re-import
    resurrection.

Documentation and unit tests do not establish supported runtime behavior. The
Campaign requires migration proof on clean and existing databases, authenticated
multi-account isolation proof, supported-path runtime proof, export/restore
round-trip proof, and purge fan-out proof before release language changes.

## 17. Non-goals

This contract does not:

- implement the Memory Store;
- rename every `user_id` column;
- merge Personal Facts into generic blobs;
- make personas account principals or memory owners;
- grant infrastructure Operators user-memory authority;
- introduce federation or multi-master memory sync;
- infer sensitive identity under general memory consent;
- claim current MemoryOS, import, Vault, classifier, export, or purge support;
- change `docs/architecture/00-current-state.md`; or
- authorize one task to implement the entire Campaign.
