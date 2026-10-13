# UMS-05C10B-P — Persist Portable Ordinary-Memory Lifecycle Transition History

**Status:** CLOSED
**Slice:** `UMS-05C10B-P` — lifecycle-transition revision persistence + UMS-04 portability
**Campaign:** Unified Account-Owned Memory Store
**Date:** 2026-09-29
**ADR impact:** Aligned with ADR-084. No new ADR. No contract contradiction.
**Class:** Canonical persistence + migration + account export/restore portability

---

## 1. Lineage

| Field | Value |
|---|---|
| Branch | `feature/ums-continued` |
| Starting HEAD | `0d9ec9ef10f590adc9c2a00aec14c655d4f350e8` |
| C10B-R closeout | `768321114a720b3c289d8b9d30cabba9703e7651` (ancestor) |
| C10B-R follow-up | `0d9ec9ef10f590adc9c2a00aec14c655d4f350e8` (HEAD) |
| C10A-W | `39dbd7a4fe03da8deb0b95b2c6bd6a5b1ddc7d03` (ancestor) |
| C10A-C | `aa906f0051130a97f70c75bb2c8efefa31c12170` (ancestor) |
| C10A-P | `a38c6ad81609cb967fa7e04a0ae072efab5c69e6` (ancestor) |
| Opening Alembic head | `a7c3e91d4b60` (single head) |
| New migration | `b8e2f4a6c901` |
| Migration parent | `a7c3e91d4b60` |
| Opening index | empty |
| Push count | `0` |

### 1.1 Intervening non-authority commit

```text
f4fc22b8e chore: add repo0qydupms
```

Sits between C10A-W and C10B-R. It is entirely `.precommit_cache/` and
`.precommit_home/` plumbing created by the sandbox-local `PRE_COMMIT_HOME`,
touching no `guardian/`, no `docs/architecture/`, and no migration. Already
classified in the C10B-R proof §2.1. It changes no authority surface and
required no re-investigation here.

---

## 2. Schema

```text
table: memory_lifecycle_revisions
```

| Column | Type | Null | Default |
|---|---|---|---|
| `lifecycle_revision_id` | `String(36)` | NOT NULL | — (server/application generated) |
| `memory_id` | `String(36)` | NOT NULL | — |
| `user_id` | `String(255)` | NOT NULL | — |
| `revision_number` | `Integer` | NOT NULL | — |
| `old_lifecycle_state` | `String(32)` | NOT NULL | — |
| `new_lifecycle_state` | `String(32)` | NOT NULL | — |
| `created_at` | `TIMESTAMPTZ` | NOT NULL | `now()` |

| Constraint / index | Meaning |
|---|---|
| `pk_memory_lifecycle_revisions` | stable primary identity |
| `fk_memory_lifecycle_revisions_memory_account` | composite `(memory_id, user_id)` → `memory_records(memory_id, user_id)`, `ON DELETE CASCADE` |
| `uq_memory_lifecycle_revisions_memory_number` | `UNIQUE (memory_id, revision_number)` |
| `memory_lifecycle_revisions_number_check` | `revision_number >= 1` |
| `memory_lifecycle_revisions_old_state_check` | old state in `active` / `dormant` / `retired` |
| `memory_lifecycle_revisions_new_state_check` | new state in `active` / `dormant` / `retired` |
| `memory_lifecycle_revisions_change_check` | `old_lifecycle_state <> new_lifecycle_state` |
| `ix_memory_lifecycle_revisions_memory_id` | parent lookup |

`revision_number` is scoped to the lifecycle-history family and is **not**
shared with content or review revision numbering.

**Deliberately absent** and proven absent by test: `actor_account_id`,
`action`, `reason`, `request_ref`, `transition_kind`, `extensions`, generic
JSON metadata, `review_state`, `text_content`, `project_id`,
`persona_subject_id`, and any `updated_at`. Intent/source/actor evidence
belongs to the receipt layer; making revision authority a second evidence
store was rejected.

---

## 3. Migration proof

| Proof | Result |
|---|---|
| Clean `head` migration | passes; ORM ↔ live parity; absent-field assertions hold |
| Populated upgrade from `a7c3e91d4b60` | `COUNT(*) FROM memory_lifecycle_revisions == 0` |
| Existing-row preservation | active / dormant / retired rows byte-identical before/after |
| Content + review + provenance preservation | 1 / 1 / 1 rows survive unchanged |
| Repeatability | two runs on independent disposable databases, both green |
| Topology | exactly one head, `b8e2f4a6c901`, with `a7c3e91d4b60` in lineage |

```text
existing canonical memories:
  synthetic lifecycle rows fabricated = 0
```

In particular the populated upgrade seeds a **legacy `retired` memory** and
still creates zero rows: the migration does not guess whether it was retired
from `active` or `dormant`. Historical information that was never canonically
stored is not invented.

---

## 4. Semantic boundary

```text
content revision family reused:         NO
review revision family reused:          NO
provenance used as lifecycle authority: NO
Personal Fact lifecycle duplicated:     NO
legal lifecycle transition graph encoded: NO
```

Persistence accepts every unequal pair of valid lifecycle tokens. A dedicated
migration test is explicitly titled `test_persistence_representability_is_not_runtime_authorization`
and persists all six unequal pairs, including `retired -> active` and
`retired -> dormant`, which a premature policy would likely have forbidden.
No DB check encodes transition legality; `old <> new` is a historical
transition-shape constraint, not a mutation policy.

A restore-side companion test proves preflight likewise does not enforce the
unresolved graph.

---

## 5. Pre-retirement posture

This is the obligation C10B-R identified, and the reason this family exists.

```text
active -> retired   preserves old_lifecycle_state = active
dormant -> retired  preserves old_lifecycle_state = dormant
```

Both are proven three ways: at the DB layer, through v7 export, and through
v7 restore round-trip. A dedicated test asserts the two retirement postures
remain **distinguishable** in both the archive and after restore, so
`active-retired` can never silently collapse into `dormant-retired`.

**No parallel `pre_retirement_state` column was added.** The historical
old-state is the canonical fact, exactly as the accepted design requires.

This slice does **not** implement restore behavior that consumes the posture.
The persistence can preserve the fact; deciding what a writer does with it is
UMS-05C10B-C's job.

---

## 6. `account-export.v7`

| Schema | Canonical UMS families | Count |
|---|---|---|
| `account-export.v6` | persona_subjects, persona_subject_bindings, memory_records, memory_persona_links, memory_provenance, memory_revisions, memory_review_revisions | 7 |
| `account-export.v7` | the seven above plus `memory_lifecycle_revisions` | 8 |

`FULL_PAYLOAD_ORDER` and the v6 constants stay bound to v6 in code, so v6
semantics cannot be widened by editing a shared constant. v6 export provably
emits no lifecycle family and its manifest does not claim one.

The global export default was **not** advanced: the production default remains
`account-export.v3`, which is not the newest canonical schema, and no accepted
policy requires newest-schema default behavior.

v6 compatibility proven: exact family list unchanged, no lifecycle payload,
v6 not reinterpreted as malformed because v7 exists.

v7 behavior proven:

- stable IDs, sequence, exact old/new states, and timestamps preserved;
- deterministic ordering by `memory_id`, then `revision_number`, then
  `lifecycle_revision_id`, with **`revision_number` sorted numerically** — a
  dedicated test proves 10 follows 9 rather than 2. (The earlier C9-era
  content family sorts revision numbers lexically; that defect was **not**
  copied into this family and v5/v6 ordering was left untouched.)
- exact `memory_lifecycle_revisions` count in `entity_counts`;
- zero-history account and zero-history currently-retired memory export
  validly, with nothing fabricated.

Export fails closed on orphan parent, account mismatch, unsupported species,
invalid token, no-op transition, non-positive number, duplicate stable ID,
duplicate `(memory_id, revision_number)`, sequence gap, chain mismatch, and
final-state mismatch. A test proves malformed history is **not** repaired from
provenance extensions: a claimed `lifecycle_history` in extensions is ignored
and history stays zero.

---

## 7. `account-export.v7` restore

`UnifiedMemoryRestorePreflight` and the existing `CanonicalMemoryRestoreExecutor`
were extended in place. No parallel lifecycle restore system was created.

Preflight fails closed on missing parent, cross-account/ownership mismatch,
duplicate stable ID, duplicate sequence slot, invalid token, no-op history,
non-positive numbering, sequence gap, chain discontinuity, final-state
mismatch, unsupported Personal Fact parent, and malformed payload.

Ordering: `memory_records` is persisted before `memory_lifecycle_revisions`
inside the same transaction, so the composite parent FK always has its parent.

The parent's `lifecycle_state` is **never** mutated from history rows. It
remains present-state authority; history reconciles to it when history exists.

Zero-history handling: a currently-retired memory with no history restores as
retired with zero lifecycle rows. Restore synthesizes no creation, import,
decay, or retirement revision and no pre-retirement posture.

Replay: identical second restore creates 0 rows and reports 1 identical.
Semantic conflict and sequence-occupancy conflict both fail closed with the
original history intact.

Atomicity:

- a semantic preflight failure produces zero partial canonical restore
  (preflight runs before any write);
- a forced late `_insert_lifecycle_revisions` failure rolls back the whole
  restore, leaving `memory_records` and `memory_lifecycle_revisions` both at
  zero. No production failure-injection hook was added; the test patches the
  executor seam.

### 7.1 Defect found and fixed during this slice

The first implementation gated the sequence-occupancy scan on "at least one
planned stable ID already exists in the database." Under that gate, a wholly
**new** stable ID attempting to occupy an already-populated
`(memory_id, revision_number)` slot was not detected, and the attempt
surfaced as a raw `UniqueViolation` from the database instead of a clean
`memory_lifecycle_revision_sequence_conflict`.

The scan is now unconditional for the lifecycle family, and
`test_sequence_occupancy_conflict_fails_closed` proves the clean conflict is
raised and the original history is preserved.

**Observation left deliberately un-changed:** the C10A review-revision
classification block contains the same conditional gate. Its existing test
passes only because that plan happens to retain one already-known revision
ID, which incidentally makes the scan run. Tightening it would change
C10A review restore behavior, which is explicitly outside this slice's
regression contract, so it is reported here as a follow-up observation rather
than silently altered. It is not a data-integrity risk: the database unique
constraint still rejects the duplicate, so the worst case is a raw constraint
error instead of a clean conflict.

---

## 8. Regression evidence

Opening baselines were captured **before** any export/restore edit:

| Suite | Opening | Closing |
|---|---|---|
| C10A review portability (export + restore) | 41 passed | 41 passed |
| C9 content portability (export + restore) | 23 passed | 23 passed |
| `test_account_restore_unified_memory.py` | 48 passed | 48 passed |
| `test_account_export_unified_memory.py` | 2 failed / 19 passed | same 2 known reds, no new failure |

New C10B-P suites: migration qualification 13 (twice, independent DBs),
v7 export, v7 restore. Migration regression across governance, C9 revision,
C10A review revision, and C10B-P lifecycle revision was run serially with a
single head.

Migration suites were run serially. The known disposable-child-database
teardown contention appeared again (`permission denied to terminate process`)
and was distinguished from code failure by isolated rerun: affected files pass
completely when run alone, and no test assertion ever failed. The one genuine
defect it surfaced is the sequence-occupancy gate in §7.1, which was a real
logic bug, not contention.

---

## 9. Invariants closeout

```text
current lifecycle authority remains memory_records.lifecycle_state: YES
canonical lifecycle history added:                                   YES
pre-retirement posture preservable from canonical history:           YES
synthetic lifecycle history created:                                 NO
content revision authority widened:                                  NO
review revision authority widened:                                   NO
lifecycle history stored in provenance extensions:                   NO
Personal Fact lifecycle authority duplicated:                        NO
lifecycle transition graph invented:                                 NO
retire writer implemented:                                           NO
restore writer implemented:                                          NO
direct activation writer implemented:                                NO
automatic decay writer implemented:                                  NO
v6 silently redefined:                                              NO
v7 lifecycle-history portability proven:                             YES
frontend changed:                                                    NO
retrieval changed:                                                   NO
release claim expanded:                                              NO
```

---

## 10. Runtime boundary

```text
lifecycle history persistence:  IMPLEMENTED
lifecycle portability:          IMPLEMENTED THROUGH V7

retire writer:                  NOT IMPLEMENTED
restore writer:                 NOT IMPLEMENTED
direct activate writer:         NOT IMPLEMENTED
automatic decay mutation:       NOT IMPLEMENTED BY THIS TASK
lifecycle transition graph:     NOT RESOLVED BY THIS TASK
review writer:                  UNCHANGED
Personal Fact lifecycle authority: UNCHANGED
frontend:                       NONE
retrieval redesign:             NONE
release claim:                  NONE
```

---

## 11. Scope note: the Memory Vault §5.1 gate

UMS-05C10B-R left the Memory Vault contract §5.1 Retire/Restore rows
open, still listing only a "durable mutation receipt" and diverging from
the normative §3.3 revision rule.

Updating that gate is **not** in this slice's authorized documentation set,
and it is deliberately left unchanged. Reconciling the §5.1 rows is the
natural companion of UMS-05C10B-C, which must first freeze the legal
lifecycle transition graph; doing it before that freeze would imply a
transition policy this persistence slice is explicitly forbidden from
choosing. The C10B-R gate text therefore still describes C10B-P as
"missing" — that sentence is stale from C10B-R's vantage and is
corrected by UMS-05C10B-C, not here.

---

## 12. Closeout

```text
UMS05C10BP_LIFECYCLE_REVISION_PORTABILITY_COMMITTED
```

Campaign transition:

```text
UMS-05C10A ORDINARY MEMORY REVIEW TRANSITION WRITER: CLOSED
UMS-05C10A: CLOSED
UMS-05C10B-R LIFECYCLE AUTHORITY / HISTORY REVALIDATION: CLOSED
UMS-05C10B-P LIFECYCLE-TRANSITION REVISION PERSISTENCE
              + UMS-04 PORTABILITY: CLOSED
UMS-05C10B-C LIFECYCLE TRANSITION CONTRACT RESOLUTION: AUTHORIZED
UMS-05C10B WRITER: FROZEN
UMS-05C11+: NOT AUTHORIZED
UMS-05D+:  NOT AUTHORIZED
UMS-06+:   NOT AUTHORIZED
```

`UMS-05C10B-C` is the sole authorized successor and was not begun. It must
freeze the lifecycle state machine: retire source states, restore target
semantics, active vs dormant pre-retirement restoration, same-state behavior,
whether direct activation exists, the system decay boundary, hold
interaction, and review-state preservation.

Gitleaks was skipped narrowly: the sandbox cannot bootstrap the Go toolchain.
Every other executable pre-commit hook ran. `gitleaks` is required at branch
integration.
