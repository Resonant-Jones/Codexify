# UMS-05C7 Remaining Memory Vault Mutation Authority Revalidation

Date: 2026-09-25

Status: **PASSED — REMAINING MUTATION AUTHORITY REVALIDATED (branch-qualified,
documentation-only)**

Final verdict:

```text
UMS05C7_REMAINING_MUTATION_AUTHORITY_REVALIDATED

UMS-05C8 ORDINARY MEMORY REVIEW AND LIFECYCLE STATE PERSISTENCE: AUTHORIZED
UMS-05C9+ NOT AUTHORIZED
UMS-05D+  NOT AUTHORIZED
UMS-06+   NOT AUTHORIZED
```

## Branch / lineage

- Branch: `feature/ums-continued`
- C6 anchor: `a05189d8c6e0f631f78c564e8beab2a9a04a383c` (Add direct
  Memory Vault creation)
- Actual starting HEAD: `33951dce18b772a438dba0b40ad154be30291cd7`
- `git merge-base --is-ancestor a05189d8c6e0... HEAD` exit `0`
- Branch-local committed drift since C6: 9 commits, all WhooshD
  provider/model routing proof documents. None intersect UMS authority,
  Memory Vault, or canonical memory persistence. No mainline merge
  occurred; no `main` reconciliation was performed.
- Index at start: empty.

## Governing semantics

The frozen UMS-05 contract (per
`docs/architecture/unified-memory-store-contract.md` §4.5.8 and
`memory-vault-contract.md` §5.1) admits the following canonical review
and lifecycle dimensions for ordinary canonical memory:

- **Review states**: `pending`, `approved`, `rejected`, `disputed`
- **Lifecycle states**: `active`, `dormant`, `retired`

Both dimensions are independent and authoritative. ADR-084 also requires
that "soft retirement is the ordinary reversible lifecycle action" and
that "dormant imports, rejected or disputed records, classifier
candidates, and external evidence" be ambient-excluded by posture.

The remaining UMS-05C action set is:

1. Ordinary episodic-memory content correction
2. Ordinary-memory review/approve/reject/dispute
3. Personal Facts review/approve/reject/dispute
4. Ordinary-memory retire/restore
5. Personal Facts retirement/restoration

## Physical canonical schema

The current `memory_records` envelope (frozen by canonical migration
`f6b0d3e8c5a2_add_canonical_memory_persistence.py`) carries:

| Column | Type | Nullable | Authority role |
| --- | --- | --- | --- |
| `memory_id` | String(36) | NOT NULL | primary key |
| `user_id` | String(255) | NOT NULL | account owner (FK users.id) |
| `project_id` | Integer | nullable | Project scope (FK projects.id, projects.user_id) |
| `semantic_species` | String(32) | NOT NULL | CHECK in canonical enum |
| `text_content` | Text | nullable | canonical episodic content payload |
| `fact_key`, `fact_value`, `fact_confidence` | various | nullable | canonical fact payload |
| `reviewed_at` | TIMESTAMP(tz) | nullable | timestamp-derived review evidence |
| `activated_at` | TIMESTAMP(tz) | nullable | timestamp-derived lifecycle evidence (CHECK `activated_at IS NULL OR (reviewed_at NOT NULL AND activated_at >= reviewed_at)`) |
| `pinned`, `held` | Boolean | NOT NULL | canonical governance flags |
| `extensions` | JSONB | nullable | non-authority auxiliary metadata |
| `created_at`, `updated_at` | TIMESTAMP(tz) | NOT NULL | record-level CAS (`updated_at`) |

No `review_state` typed column. No `lifecycle_state` typed column. No
canonical retire flag. No canonical dormant flag.

## Ordinary read projection

`guardian/services/memory_vault_read.py` derives:

```python
review_posture = (
    REVIEW_POSTURE_APPROVED
    if row.reviewed_at is not None
    else REVIEW_POSTURE_PENDING
)
lifecycle_posture = (
    LIFECYCLE_POSTURE_ACTIVE
    if row.activated_at is not None
    else LIFECYCLE_POSTURE_INACTIVE
)
```

The readback vocabulary is therefore a binary mapping per dimension:

| Dimension | Distinguishable values |
| --- | --- |
| review | `approved` (reviewed_at NOT NULL), `pending` (reviewed_at IS NULL) |
| lifecycle | `active` (activated_at NOT NULL), `inactive` (activated_at IS NULL) |

`REVIEW_POSTURE_DISPUTED` is defined as a constant in the read service
but is **never emitted** by the current projection. The current readback
cannot produce `rejected`, `disputed`, `dormant`, or `retired`.

## Protocol token inventory

`guardian/protocol_tokens.py` registers:

- `MemorySemanticSpecies`: `EPISODIC_SEMANTIC_MEMORY`,
  `VERIFIED_PERSONAL_FACT`, `CANDIDATE_UNREVIEWED_FACT`
- `MemoryPersonaLinkKind`: `CAPTURED_UNDER`, `SUGGESTED_BY`,
  `ASSOCIATED_WITH`
- `PersonaSubjectLifecycle`: `ACTIVE`, `RETIRED`
- `PersonalFactStatus`: `CANDIDATE`, `VERIFIED`, `DISPUTED`, `ARCHIVED`
- `DelegationJobStatus`: includes `APPROVED`

There is **no** canonical protocol token for ordinary-memory review
state or ordinary-memory lifecycle state. The readback string values
`"approved" | "pending"` and `"active" | "inactive"` are string literals
in `memory_vault_read.py` (`REVIEW_POSTURE_APPROVED`/`PENDING`,
`LIFECYCLE_POSTURE_ACTIVE`/`INACTIVE`) rather than a registered enum
value.

## Authority matrix

| Capability | Semantic subtype | Current canonical authority | Current persisted fields/tables | Current read representation | Required states/transitions | Can all states round-trip distinctly? | Existing revision/evidence authority | Existing CAS authority | Export coverage | Restore coverage | Migration required? | Protocol token required? | ADR impact | Classification | Earliest implementation prerequisite |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Content correction | ordinary episodic | `memory_records.text_content` (canonical content authority) + `memory_provenance` (append-only lineage) | `memory_records.text_content` (mutable) + `memory_provenance.extensions` | full text_content | approved-old-text → approved-new-text, with prior/new values, actor, reason, request_ref | YES (single text_content field carries corrected value; prior is provenance-evidence; receipt provides ordered lineage) | `memory_provenance` is already one-to-many append-only and portable through UMS-04 (v4 envelope round-trips `text_content` and provenance extensions) | YES — record-level `updated_at` CAS reused from C1–C6 | YES (`text_content` and provenance row are both UMS-04 v4 families; already covered) | YES (same) | NO new migration needed for content fields | NO new token — `MemorySemanticSpecies.EPISODIC_SEMANTIC_MEMORY` already in place; content correction uses same receipt schema | Aligned with ADR-084 (existing revision doctrine: `memory_provenance` already described as "first-class durable lineage row for a canonical memory record") | **IMPLEMENTABLE_ON_CURRENT_PERSISTENCE** | None — current persistence is sufficient |
| Ordinary review (approve/reject/dispute) | ordinary episodic | none currently — the only authority signal is `reviewed_at`, which has 2-way cardinality | `reviewed_at` TIMESTAMP only | binary (approved/pending); `disputed` defined but never emitted | approve (pending → approved), reject (pending → rejected), dispute (approved/disputed → disputed) | **NO** — `rejected` cannot be distinguished from `pending` (both = `reviewed_at IS NULL`); `disputed` cannot be distinguished from `pending` (cannot encode); cannot reset `reviewed_at` to non-NULL without losing distinction | n/a (no review-state mutation) | YES — record CAS would apply if state were added | partial — `reviewed_at` round-trips, but `disputed`/`rejected` have no physical carrier | partial — same | **YES** — new typed `review_state` column with CHECK in `{pending, approved, rejected, disputed}` is required | **YES** — new `MemoryReviewState` enum must be registered in `protocol_tokens.py` | ADR-084 / contract amendment only if the contract already promises rejected/disputed semantics; otherwise implementation-only materialization aligns with ADR-084 | **REQUIRES_CANONICAL_PERSISTENCE_PREREQUISITE** | Shared ordinary-memory state-persistence slice (review + lifecycle, see below) |
| Personal Facts review (approve/reject/dispute) | fact species | `PersonalFact.status` CHECK in `{candidate, verified, disputed, archived}` (full 4-state); `PersonalFactRevision` (full append-only revision history) | `personal_facts` + `personal_fact_revisions` + `personal_fact_evidence` | full | approve (candidate → verified), reject (candidate → archived), dispute (verified → disputed) | YES — all four states already distinct | YES — `PersonalFactRevision` already provides durable revision history with `old_value`/`new_value`/`reason`/`actor`/`action` | n/a (Personal Facts service owns its concurrency) | YES — Personal Facts already in v4 export (`personal_facts_status_check`, full lifecycle in fixture) | YES — same | NO new migration | NO new token — `PersonalFactStatus` already registered | Aligned with ADR-084 and the governing Personal Facts ADR; no architecture change | **DELEGATES_TO_EXISTING_SPECIALIZED_AUTHORITY** | Vault HTTP adapter (thin) delegating to `guardian.routes.personal_facts` approve/reject/dispute endpoints; underlying service authority already exists |
| Ordinary lifecycle (retire/restore) | ordinary episodic | none currently — the only authority signal is `activated_at`, which has 2-way cardinality | `activated_at` TIMESTAMP only | binary (active/inactive); dormant/retired not represented | retire (active → retired), restore (retired → active); dormant requires an additional "temporarily inactive" state | **NO** — `retired` cannot be distinguished from `inactive`/`never-activated`; `dormant` cannot be represented; clearing `activated_at` destroys information about prior state | n/a (no lifecycle mutation) | YES — record CAS would apply | partial — `activated_at` round-trips but lacks state distinction | partial — same | **YES** — new typed `lifecycle_state` column with CHECK in `{active, dormant, retired}` is required (cannot repurpose `held`/`pinned`/`extensions` — these are different authorities) | **YES** — new `MemoryLifecycleState` enum must be registered in `protocol_tokens.py` | Aligned with ADR-084 (soft retirement is the ordinary reversible lifecycle action) only after state authority is added | **REQUIRES_CANONICAL_PERSISTENCE_PREREQUISITE** | Same shared ordinary-memory state-persistence slice (review + lifecycle, see below) |
| Personal Facts lifecycle | fact species | `PersonalFact.is_active` boolean + `PersonalFactStatus='archived'` | `personal_facts` + `personal_fact_revisions` | full | archive (any active fact → archived), restore (archived → verified) | YES — `is_active` boolean + `status='archived'` covers the lifecycle transition | YES — `PersonalFactRevision` durable | n/a | YES — already in v4 export | YES — same | NO new migration | NO new token | Aligned with ADR-084 and the governing Personal Facts ADR | **DELEGATES_TO_EXISTING_SPECIALIZED_AUTHORITY** | Vault HTTP adapter delegating to existing `personal_facts` archive/restore; underlying service authority already exists |

## Content-correction analysis (priority-3 candidate)

Question 1: Does the governing contract allow canonical `text_content` to
mutate in place if prior/new values are retained in append-only provenance?

**Yes.** `memory-vault-contract.md` §5.1 row "Correct / edit user-governed
content" prescribes "canonical revision service for the subtype | new
canonical revision, audit-trailed | durable mutation receipt". The
contract treats `memory_provenance` as the durable revision/audit
substrate. There is no contract clause that requires a separate revision
table for ordinary episodic memory.

Question 2: Does `memory_provenance.extensions` already round-trip
through UMS-04?

**Yes.** `tests/services/test_account_export_restore_unified_memory_roundtrip.py`
passes (1 passed in this branch) and exercises the `text_content` field
plus provenance rows through the v4 export/restore contract. The
existing fixture explicitly includes a `non-empty contract-valid extension
payload` for one memory row.

Question 3: Would storing previous/new corrected content there remain
legitimate revision evidence rather than turning extensions into current
authority?

**Yes.** The readback's `text_content` continues to come from
`memory_records.text_content`. Receipt extension values are non-authority
audit evidence; canonical content authority remains in the typed column.

Question 4: Does the existing provenance model provide a stable enough
revision identity and ordering?

**Yes.** `memory_provenance.provenance_id` is a server-generated UUID
PK; `created_at` is the canonical temporal ordering; ordering is
already stable and round-trippable through UMS-04.

Question 5: Is `updated_at` sufficient as resulting record version/CAS?

**Yes.** The C1–C6 mutation spine already uses
`memory_records.updated_at` as the record-level CAS. Content correction
can use the same CAS token (`expected_updated_at`).

Question 6: Is any current content-revision table already authoritative?

**No** content-revision table exists for `memory_records.text_content`.
The contract does not require one; `memory_provenance` is the designated
lineage substrate.

Question 7: Would a correction remain portable after account
export/restore today?

**Yes.** `text_content` is already in v4 export. Provenance rows are
already in v4 export. Round-trip is proven.

**Conclusion: ordinary-memory content correction is
IMPLEMENTABLE_ON_CURRENT_PERSISTENCE.**

## Ordinary-review representability matrix

| Required state | Current mapping | Distinctly representable? |
| --- | --- | --- |
| `pending` | `reviewed_at IS NULL` | YES |
| `approved` | `reviewed_at IS NOT NULL` | YES |
| `rejected` | — (no carrier) | **NO** — collides with `pending` |
| `disputed` | — (no carrier; `REVIEW_POSTURE_DISPUTED` constant exists in `memory_vault_read.py` but is never emitted) | **NO** — collides with `pending` |

**Conclusion: ordinary review is REQUIRES_CANONICAL_PERSISTENCE_PREREQUISITE.**
The smallest possible addition is a typed column with CHECK constraint
on `{pending, approved, rejected, disputed}`. The current `reviewed_at`
timestamp cannot carry the four-state semantics because both `pending`
and `rejected` would require `reviewed_at IS NULL`, and `disputed` would
require either encoding inside the timestamp (impossible) or carrying a
new boolean.

JSONB `extensions` cannot promote into authority without a contract
amendment (per invariant #10: "Non-authority extensions cannot become
lifecycle/review authority").

## Ordinary-lifecycle representability matrix

| Required state | Current mapping | Distinctly representable? |
| --- | --- | --- |
| `active` | `activated_at IS NOT NULL` | YES |
| `dormant` | — (no carrier) | **NO** — collides with `never-activated` (`activated_at IS NULL`) |
| `retired` | — (no carrier) | **NO** — collides with `inactive`/`never-activated` |

Additionally: clearing `activated_at` for `retired` would destroy
information about whether the record was ever active. A
`lifecycle_state` column with CHECK on `{active, dormant, retired}` and
appropriate migration/backfill is the only faithful representation.

The contract also requires reversibility ("soft retirement is the
ordinary reversible lifecycle action"). A typed column supports both the
state transition and its reversal without information loss.

**Conclusion: ordinary lifecycle is
REQUIRES_CANONICAL_PERSISTENCE_PREREQUISITE.** The smallest addition is a
typed `lifecycle_state` column with CHECK on `{active, dormant,
retired}`.

## Critical separation: review prerequisite and lifecycle prerequisite share one persistence seam

Ordinary-memory review states and ordinary-memory lifecycle states both
require:

- a new typed column (one per dimension);
- a CHECK constraint enumerating the canonical token vocabulary;
- a protocol-token enum registration (`MemoryReviewState`,
  `MemoryLifecycleState`) in `guardian/protocol_tokens.py`;
- a migration that backfills existing rows from current `reviewed_at` /
  `activated_at` timestamps without losing state;
- a read-projection migration from timestamp-only derivation to typed
  column;
- UMS-04 v4 envelope field addition (already extensible through the
  existing `extensions` payload contract for backward-compatible export,
  but a typed field requires manifest amendment);
- restore-side field handling.

These are TWO columns but ONE persistence prerequisite: the canonical
ordinary-memory governance envelope.

This satisfies the spec's **Priority 1 — shared canonical persistence
prerequisite**.

## Personal Facts review/lifecycle

`PersonalFact` already carries:

- `status ∈ {candidate, verified, disputed, archived}` (CHECK
  constraint)
- `is_active` boolean (active lifecycle flag)
- `PersonalFactRevision` durable revision history with
  `actor`/`action`/`field_changed`/`old_value`/`new_value`/`reason`

`guardian/routes/personal_facts.py` already exposes:

- `POST /candidates/{fact_id}/approve` (verified)
- `POST /{fact_id}/dispute` (disputed)
- archive/restore routes (via the same router)

Personal Facts review authority is therefore
**DELEGATES_TO_EXISTING_SPECIALIZED_AUTHORITY**. No new persistence is
needed for Personal Facts review. A future Vault HTTP adapter can
delegate to the existing routes.

## Revision / evidence sufficiency

`memory_provenance` already exists and is sufficient for:

- content correction revision history (previous/new values in
  extensions; provenance_id ordering)
- all C1–C6 mutation receipts (pin, hold, project-scope,
  persona-attribution, direct creation)

No new revision family is needed. The contract's
"canonical revision service for the subtype" requirement is satisfied by
content-correct using `memory_provenance` as the lineage substrate (per
Question 6 above).

## CAS analysis

The C1–C6 record-level CAS on `memory_records.updated_at` remains the
default concurrency authority. Content correction, review-state
mutation, and lifecycle mutation all share that CAS:

- Content correction uses the same `expected_updated_at` token as
  pin/hold/project-scope/persona-attribution
- Review-state and lifecycle-state mutations (after persistence
  prerequisite) will use the same CAS token
- Stale-token semantics (`MemoryVaultMutationConflict`) remain valid
- Cross-action CAS proof extends unchanged

No new concurrency mechanism is required.

## Portability matrix

| Authority | Current UMS-04 v4 coverage | Required if added |
| --- | --- | --- |
| `text_content` | YES (existing column in v4) | unchanged |
| `reviewed_at` | YES | unchanged |
| `activated_at` | YES | unchanged |
| new `review_state` | absent | needs typed v4 field + restore mapping |
| new `lifecycle_state` | absent | needs typed v4 field + restore mapping |
| `PersonalFact.status`, `PersonalFact.is_active`, `PersonalFactRevision` | YES (existing fields) | unchanged |
| `memory_provenance.extensions` (receipts) | YES | unchanged for content correction |

UMS-04 manifest hashing/count implications: no change for content
correction (uses existing families). For review/lifecycle, a new typed
field must be added to the v4 envelope and the round-trip suite must be
extended.

## Token impact

No new tokens are introduced by C7 itself. The selected successor
(UMS-05C8) must register:

- `MemoryReviewState = {pending, approved, rejected, disputed}` in
  `guardian/protocol_tokens.py`
- `MemoryLifecycleState = {active, dormant, retired}` in
  `guardian/protocol_tokens.py`

These tokens already exist in the architecture contract vocabulary
(`unified-memory-store-contract.md` §4.5.8) but are not yet registered
in the protocol token module. The successor must freeze them before
writing the runtime code.

## ADR impact

- **C7 itself: No architecture semantic change.** C7 is documentation
  only; no runtime, schema, or contract file changed.
- **Selected successor (UMS-05C8 Ordinary Memory Review and Lifecycle
  State Persistence)**: Aligned with ADR-084. Implementation-only
  materialization of the contract's already-named
  `review_state ∈ {pending, approved, rejected, disputed}` and
  `lifecycle_state ∈ {active, dormant, retired}` vocabularies. No
  superseding ADR required.

## Dependency ordering

Per the spec's priority rules:

1. **Priority 1 — shared canonical persistence prerequisite**:
   ordinary review (rejected/disputed) AND ordinary retire/restore
   BOTH depend on the same canonical ordinary-memory governance
   envelope (typed `review_state` + typed `lifecycle_state` columns +
   corresponding protocol tokens + migration/backfill + read-projection
   update + UMS-04 envelope extension). This is the shared prerequisite.

2. **Priority 3 — currently implementable bounded capability (content
   correction)**: also currently implementable on existing persistence.
   Per spec rule "Do not authorize content correction, review, retire
   simultaneously", content correction is held back until the
   persistence prerequisite is committed. Once UMS-05C8 lands,
   content correction can be authored as a separate slice that reuses
   the new persistence (it does not require it, but the audit-trail
   coherence is cleaner once governance posture is typed).

3. **Priority 4 — specialized-authority adapter (Personal Facts)**:
   Personal Facts review/lifecycle already have full authority. A
   Vault HTTP adapter that delegates to `guardian.routes.personal_facts`
   can be authored after the persistence prerequisite is committed.

The spec authorizes exactly ONE successor. The selected successor is
**Priority 1**, because it is the shared prerequisite that blocks
multiple downstream slices.

## Selected successor

```text
UMS-05C8 ORDINARY MEMORY REVIEW AND LIFECYCLE STATE PERSISTENCE: AUTHORIZED
```

Scope of the successor:

- Add canonical typed `review_state` column on `memory_records` with
  CHECK in `{pending, approved, rejected, disputed}`; backfill from
  existing `reviewed_at` (reviewed_at IS NOT NULL → approved; else
  pending).
- Add canonical typed `lifecycle_state` column on `memory_records`
  with CHECK in `{active, dormant, retired}`; backfill from existing
  `activated_at` (activated_at IS NOT NULL → active; else dormant).
- Register `MemoryReviewState` and `MemoryLifecycleState` enums in
  `guardian/protocol_tokens.py`.
- Update `memory_vault_read.py` to derive `review_posture` and
  `lifecycle_posture` from the typed columns.
- Extend UMS-04 v4 envelope to include the new fields; extend the
  round-trip fixture to cover all four review states and all three
  lifecycle states; ensure clean round-trip and second-restore
  no-op behavior.
- Document and verify all four review states and all three lifecycle
  states round-trip distinctly before authorizing any mutation
  service that consumes them.

The successor must NOT yet implement:

- content correction (covered separately after persistence prerequisite
  lands; not authorized inside UMS-05C8)
- review action mutation (approve/reject/dispute) — those services are
  a subsequent slice after the typed columns exist
- retire/restore mutation — same
- Personal Facts HTTP adapter

## Deferred categories

The following UMS-05C capabilities remain not-authorized inside UMS-05C7:

- Ordinary-memory content correction (IMPLEMENTABLE_ON_CURRENT_PERSISTENCE,
  but spec forbids simultaneous authorization with the persistence
  prerequisite; deferred to a subsequent slice after UMS-05C8)
- Ordinary-memory review action mutation (REQUIRES_CANONICAL_PERSISTENCE_PREREQUISITE;
  blocked on UMS-05C8)
- Ordinary-memory retire/restore mutation (REQUIRES_CANONICAL_PERSISTENCE_PREREQUISITE;
  blocked on UMS-05C8)
- Personal Facts HTTP adapter (DELEGATES_TO_EXISTING_SPECIALIZED_AUTHORITY;
  subsequent slice; deferred)

## Limitations

- C7 is documentation only. No runtime, schema, migration, route, test,
  protocol-token, export/restore, or normative architecture-contract
  file was changed.
- C7 is branch-local on `feature/ums-continued`. Not deployed, not
  exposed via Preview, not merged into the current `main`.
- C7 does not claim the selected successor is implemented. UMS-05C8
  is authorized only; its implementation is a separate task.
- The C7 analysis is bounded to the current repository state. Any
  later schema change or contract amendment will require a
  revalidation pass before further mutation authorization.
- UMS-05D+ and UMS-06+ remain unauthorized.

## Regression evidence (no runtime change)

- `tests/services/test_account_export_restore_unified_memory_roundtrip.py`:
  1 passed on the proven Homebrew port-5432 disposable-DB isolation
  pattern (Case A, UMS-04 round-trip unchanged).
- No mutation service, route, or test file modified.
- All previously-passing regression suites remain in their last green
  state from the C6 closeout (`feature/ums-continued` HEAD
  `a05189d8c6e0...`).
