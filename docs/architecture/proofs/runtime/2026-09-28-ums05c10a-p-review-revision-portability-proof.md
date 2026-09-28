# UMS-05C10A-P — Persist Portable Ordinary-Memory Review-Transition Revisions

**Status:** CLOSED
**Slice:** `UMS-05C10A-P` — ordinary-memory review-transition revision persistence + UMS-04 portability
**Campaign:** Unified Account-Owned Memory Store
**Date:** 2026-09-28
**ADR impact:** ALIGNED WITH ADR-084 — no new ADR
**Class:** Canonical persistence + migration + account portability

---

## 1. What this slice did

UMS-05C10A-R classified the ordinary-memory review-history gap as
`REVIEW_HISTORY_NEW_CANONICAL_PERSISTENCE_REQUIRED` and separately recorded
`TRANSITION_GRAPH: NOT EXPLICIT`. This slice supplies the missing canonical
persistence and its portability, and nothing else.

It adds one canonical family, `memory_review_revisions`, and one new immutable
account export schema, `account-export.v6`.

It does **not** implement `approve`, `reject`, or `dispute`, does not define
which transitions are legal, and does not add any route, service method, or UI.

---

## 2. Lineage

| Field | Value |
|---|---|
| Branch | `feature/ums-continued` |
| Starting HEAD | `a49dff0044150eb142f4324b3bfa8684181d3248` (C10A-R closeout) |
| C9-W `2c21cd0e0` in ancestry | yes |
| Opening Alembic head | `c3d9f4e6a1b2` (single head) |
| New migration | `a7c3e91d4b60` |
| Migration parent | `c3d9f4e6a1b2` |
| Final Alembic head | `a7c3e91d4b60` (single head) |
| Migrations created | exactly one |
| Index posture at start | empty |
| Push count | `0` |

---

## 3. Scope deviation reported

The task named `guardian/db/pgdb.py` as the production export row-source. The
actual row-source is `guardian/core/pgdb.py`; `guardian/db/` holds `models.py`
and `migrations/`. Export **schema authority** (which families belong to which
version) lives in `guardian/services/account_export.py`, which is authorized and
is the file that actually changed the schema map.

This was treated as a path discrepancy on an intended surface rather than as new
scope: the row-source fetcher was plainly required to emit a new family, no
additional authority file had to be touched, and no design decision moved. It is
recorded here rather than silently absorbed.

---

## 4. Schema

```text
table: memory_review_revisions
```

| Column | Type | Null | Default |
|---|---|---|---|
| `review_revision_id` | `String(36)` | NOT NULL | — (server/application generated) |
| `memory_id` | `String(36)` | NOT NULL | — |
| `user_id` | `String(255)` | NOT NULL | — |
| `revision_number` | `Integer` | NOT NULL | — |
| `old_review_state` | `String(32)` | NOT NULL | — |
| `new_review_state` | `String(32)` | NOT NULL | — |
| `actor_account_id` | `String(255)` | NOT NULL | — |
| `created_at` | `TIMESTAMPTZ` | NOT NULL | `now()` |

Constraints and index:

| Name | Meaning |
|---|---|
| `pk_memory_review_revisions` | stable primary identity |
| `fk_memory_review_revisions_memory_account` | composite `(memory_id, user_id)` → `memory_records(memory_id, user_id)`, `ON DELETE CASCADE` |
| `uq_memory_review_revisions_memory_number` | `UNIQUE (memory_id, revision_number)` |
| `memory_review_revisions_number_check` | `revision_number >= 1` |
| `memory_review_revisions_old_state_check` | old state in `pending/approved/rejected/disputed` |
| `memory_review_revisions_new_state_check` | new state in `pending/approved/rejected/disputed` |
| `memory_review_revisions_change_check` | `old_review_state <> new_review_state` |
| `memory_review_revisions_actor_account_check` | `actor_account_id = user_id` |
| `ix_memory_review_revisions_memory_id` | parent lookup |

Deliberately absent, per the accepted design: `reason`, `request_ref`,
`receipt_id`, action/extension/metadata JSON, `lifecycle_state`, `text_content`,
`project_id`, `persona_subject_id`, and any `updated_at`. Intent and receipt
evidence stay in `memory_provenance`.

Cascade is `c` (CASCADE): history may not outlive legitimate permanent erasure
of its parent memory.

`revision_number` is scoped to this family and is **not** shared with content
`memory_revisions`.

---

## 5. Migration proof

| Proof | Result |
|---|---|
| Clean `head` migration | passes; ORM ↔ live PostgreSQL parity; no `updated_at`; `created_at` is `TIMESTAMPTZ` |
| Populated upgrade from `c3d9f4e6a1b2` | `COUNT(*) FROM memory_review_revisions == 0` |
| Existing `memory_records` preservation | `review_state`, `lifecycle_state`, exact `text_content`, pin, hold, timestamps unchanged |
| Content `memory_revisions` preservation | untouched (`before` → `after` survives) |
| `memory_provenance` preservation | untouched |
| Account identity | orphan parent and cross-account parent both rejected |
| Actor containment | actor outside the owning account rejected |
| Vocabulary | all four tokens accepted; unknown token rejected |
| Sequence | `0` and `-1` rejected; duplicate `(memory_id, revision_number)` rejected |
| No-op | `old == new` rejected |
| Multi-transition readback | 4 rows read back in deterministic `revision_number` order |
| Account isolation | per-account counts exact |
| Cascade | parent delete removes history |
| Repeatability | two runs on independent disposable databases, both green |
| Topology | exactly one head, `a7c3e91d4b60`, with `c3d9f4e6a1b2` in lineage |

```text
existing canonical memories:
  synthetic review rows fabricated = 0
```

### 5.1 C9 head-assertion reconciliation

`tests/migration/test_memory_revision_persistence_migration.py` previously
asserted that the repository's terminal head **is** `c3d9f4e6a1b2`. Adding an
intentional descendant made that terminal-value assertion false. It was
reconciled to assert topology instead of a terminal value — exactly one head,
and C9 present in its lineage. No C9 migration assertion was weakened or removed.

---

## 6. Semantic boundary

```text
content revision family reused:            NO
provenance used as review-history authority: NO
Personal Fact revision authority duplicated: NO
legal transition graph encoded:             NO
synthetic historical review rows created:   NO
review/lifecycle coupling introduced:       NO
```

**Why no transition graph.** The database accepts any *unequal* pair of valid
review tokens. This is proven, not asserted: a dedicated migration test writes
`disputed → approved`, `approved → rejected`, and `rejected → pending`
transitions — precisely the pairs a premature policy would likely have forbidden
— and PostgreSQL accepts all of them. A matching restore test proves those
histories plan and restore without policy enforcement.

`old_review_state <> new_review_state` is a historical-transition constraint (an
identical pair is not a transition), not a mutation policy. **Persistence
capability is not mutation authorization.**

Personal Facts keep `personal_fact_revisions`; the species boundary is enforced
in export validation, restore preflight, and future service authority, and is
deliberately not backed by a trigger.

---

## 7. `account-export.v6`

| Schema version | Canonical UMS families |
|---|---|
| `account-export.v5` | `persona_subjects`, `persona_subject_bindings`, `memory_records`, `memory_persona_links`, `memory_provenance`, `memory_revisions` |
| `account-export.v6` | the six above plus `memory_review_revisions` |

`FULL_PAYLOAD_ORDER` remains bound to v5 in code, so v5 semantics cannot be
widened by editing a shared constant. v6 has its own explicit constant and its
own payload order.

The production default export is `account-export.v3`; v4/v5/v6 are selected
explicitly. The default was **not** advanced, because the production default is
not the newest canonical schema.

v6 behavior proven:

- exact stable IDs, revision numbers, typed old/new states, actor, and
  timestamps preserved;
- deterministic ordering by `memory_id`, then `revision_number` (numeric), then
  `review_revision_id`;
- exact `memory_review_revisions` count in `entity_counts`;
- zero-history account and zero-history memory export validly, with no
  fabricated history;
- account scoping;
- fail-closed on personal-fact parent, invalid token, no-op transition, sequence
  gap, chain mismatch, final-state mismatch, actor mismatch, orphan, and
  duplicate sequence occupancy;
- a test proves malformed history is **not** repaired from provenance
  extensions.

Ordering note: review revisions are sorted with numeric awareness rather than
through the generic string-comparing family loop, so revision 10 follows 9
rather than 2. This is proven by a dedicated test. v5 ordering is unchanged.

---

## 8. `account-export.v6` restore

`UnifiedMemoryRestorePreflight` and the existing `CanonicalMemoryRestoreExecutor`
were extended in place. No parallel restore system was created.

Fail-closed preflight proven: missing parent, cross-account, actor mismatch,
duplicate stable ID, duplicate `(memory_id, revision_number)`, invalid token,
no-op transition, non-positive numbering, sequence gap, chain discontinuity,
final-state mismatch, specialized Personal Fact parent, and malformed payload.

Ordering: `memory_records` is persisted before `memory_review_revisions` inside
the same transaction, so the composite parent FK always has its parent.

Reconciliation: the restored `memory_records.review_state` remains the canonical
present value. History reconciles to it and never overrides it — proven by a test
asserting the parent state and untouched exact text after restore.

Replay: an identical second restore creates 0 rows and reports 3 identical. A
semantic conflict and a sequence-occupancy conflict both fail closed, leaving the
original history intact.

Atomicity:

- a semantic preflight failure produces zero partial canonical restore
  (preflight runs before any write);
- a forced late `_insert_review_revisions` failure rolls back the whole restore,
  leaving `memory_records` and `memory_review_revisions` both at zero. The
  production code gained no failure-injection hook; the test patches the
  executor seam exactly as the accepted UMS-04/C9 proof did.

---

## 9. v5 backward compatibility

Explicit v5 export emits no `memory_review_revisions` payload, its manifest does
not claim the seventh family, and it remains exactly six canonical families —
proven by test. v5 restore semantics are unchanged. A v5 archive whose memory has
no reconstructable review history is not invalid, and v5 restore does not
fabricate history.

---

## 10. Regression evidence

Migration suites were run **serially** against disposable PostgreSQL: running
two disposable-DB migration files in one session produced a spurious
`permission denied to terminate process` teardown error, and the affected test
passed in isolation. This is the known disposable-child-database contention, not
a defect.

| Suite | Result |
|---|---|
| `tests/migration/test_memory_review_revision_persistence_migration.py` (run 1) | **16 passed** |
| `tests/migration/test_memory_review_revision_persistence_migration.py` (run 2, independent DB) | **16 passed** |
| `tests/migration/test_memory_revision_persistence_migration.py` (C9) | **10 passed** |
| `tests/migration/test_memory_governance_state_migration.py` | **7 passed** |
| `tests/services/test_account_export_memory_review_revisions.py` | **18 passed** |
| `tests/services/test_account_restore_memory_review_revisions.py` | **23 passed** |
| C9 v5 portability: export + restore | **23 passed** |
| `tests/services/test_account_restore_unified_memory.py` | **48 passed** |

### 10.1 Known explicit-v4 baseline

Captured before any export/restore edit and again after:

```text
before: 2 failed, 19 passed
after:  same 2 failed
```

```text
test_explicit_v4_serializes_exact_canonical_graph_and_manifest
test_v4_restore_remains_unsupported
```

Unchanged, not repaired, and no additional failure appeared. This historical
debt is outside C10A-P scope.

---

## 11. Invariants closeout

```text
current review authority remains memory_records.review_state: YES
canonical review history added:                                  YES
content revision authority widened:                              NO
review history stored in provenance extensions:                  NO
Personal Fact revision authority duplicated:                     NO
synthetic historical review rows created:                        NO
legal transition graph invented:                                 NO
review/lifecycle coupling introduced:                            NO
v5 silently redefined:                                           NO
v6 review-history portability proven:                             YES
review writer implemented:                                       NO
lifecycle writer implemented:                                    NO
frontend changed:                                                NO
retrieval changed:                                               NO
release claim expanded:                                          NO
```

---

## 12. Runtime boundary

```text
approve writer:                   NOT IMPLEMENTED
reject writer:                    NOT IMPLEMENTED
dispute writer:                   NOT IMPLEMENTED
legal review-transition graph:    NOT RESOLVED
lifecycle writer:                 NOT IMPLEMENTED
Personal Fact review authority:   UNCHANGED
revision-history read API:        NOT IMPLEMENTED
frontend:                         NONE
retrieval:                        NONE
schema change:                    additive only (one new table)
export schema change:             account-export.v6 added; v5 immutable
release claim:                    NONE
```

---

## 13. Closeout

```text
UMS05C10AP_REVIEW_REVISION_PORTABILITY_COMMITTED
```

Campaign transition:

```text
UMS-05C9-W ORDINARY MEMORY CONTENT CORRECTION WRITER: CLOSED
UMS-05C10: OPEN
UMS-05C10A-R REVIEW-TRANSITION HISTORY REVALIDATION: CLOSED
UMS-05C10A-P REVIEW-TRANSITION REVISION PERSISTENCE
              + UMS-04 PORTABILITY: CLOSED
UMS-05C10A ORDINARY MEMORY REVIEW TRANSITION WRITER: FROZEN
UMS-05C10A-C REVIEW-TRANSITION CONTRACT RESOLUTION: AUTHORIZED
UMS-05C10B ORDINARY MEMORY LIFECYCLE WRITER: NOT AUTHORIZED
UMS-05C11+: NOT AUTHORIZED
UMS-05D+:  NOT AUTHORIZED
UMS-06+:   NOT AUTHORIZED
```

`UMS-05C10A-C` is the sole successor. Its job is to resolve the missing legal
transition graph — and, if the review/lifecycle coupling questions prove
load-bearing, the §5.1 / §3.3 wording divergence recorded by C10A-R — before the
C10A writer can be authorized. It was not begun.

Gitleaks was skipped narrowly: the sandbox cannot bootstrap the Go toolchain.
Every other executable pre-commit hook ran. `gitleaks` is required at branch
integration.
