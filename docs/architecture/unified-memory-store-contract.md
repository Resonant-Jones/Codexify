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

### 4.4 Activation projection

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
