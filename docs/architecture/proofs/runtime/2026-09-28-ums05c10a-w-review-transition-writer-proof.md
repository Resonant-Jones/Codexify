# UMS-05C10A-W — Ordinary-Memory Review Transition Writer

**Status:** CLOSED
**Slice:** `UMS-05C10A-W` — approve / reject / dispute writer
**Campaign:** Unified Account-Owned Memory Store
**Date:** 2026-09-28
**ADR impact:** Implements **ADR-088** (Ordinary Memory Review Transition Semantics), aligned with ADR-084. No new ADR.
**Class:** Canonical mutation authority / optimistic concurrency / review-history append / API adapter

---

## 1. Lineage

| Field | Value |
|---|---|
| Branch | `feature/ums-continued` |
| Starting HEAD | `aa906f0051130a97f70c75bb2c8efefa31c12170` (C10A-C) |
| C10A-C | `aa906f0051130a97f70c75bb2c8efefa31c12170` (ancestor) |
| C10A-P | `a38c6ad81609cb967fa7e04a0ae072efab5c69e6` (ancestor) |
| C10A-R | `a49dff0044150eb142f4324b3bfa8684181d3248` (ancestor) |
| C9-W | `2c21cd0e0a6cfc242643d1ca029ed8e1d1b40888` (ancestor) |
| Alembic head before | `a7c3e91d4b60` (single head) |
| Alembic head after | `a7c3e91d4b60` (single head, unchanged) |
| Schema / migration change | none |
| Export / restore change | none |
| Push count | `0` |

---

## 2. Pre-implementation gates

### 2.1 Direct-creation `reviewed_at` obligation

```text
DIRECT CREATION REVIEWED_AT OBLIGATION: SATISFIED
```

`MemoryVaultCreationService.create_memory` writes
`review_state="approved"` and `reviewed_at=now()` in the **same** insert, from
one `now()` expression, and its post-flush readback explicitly fails closed if
`reviewed_at is None`. An approved ordinary memory therefore always carries a
first-authoritative-approval timestamp, which is exactly ADR-088's meaning. No
repair of creation semantics was needed or performed.

### 2.2 Derived review-eligibility obligation

```text
DERIVED REVIEW ELIGIBILITY UPDATE OBLIGATION:
NONE — ELIGIBILITY IS COMPUTED, NOT STORED
```

`ambient_eligible` appears in exactly one runtime place,
`guardian/core/memory_compatibility.py`, as a dataclass field of the read-time
compatibility projection. It is not a column in `guardian/db/models.py` or
`guardian/core/pgdb.py`, and no vector index, cache, or materialized
eligibility table derives from `memory_records.review_state`. Ambient
eligibility is computed from canonical state on read, so a review change cannot
leave a stale authoritative derivative. This was verified by implementation
search, not inferred from design intent.

---

## 3. Service authority

```python
MemoryVaultMutationService.transition_review(
    *,
    memory_id: str,
    expected_updated_at: datetime,
    action: str,
    reason: str | None = None,
    request_ref: str | None = None,
) -> VaultReviewTransitionResult
```

One canonical method owns review mutation. No second review service was
created. Account authority remains constructor-bound via
`authenticated_account_id`; no method argument can override it.

An action-oriented method was chosen over a generic `set_review_state(...)`
because ADR-088 admits only three actions and no `pending` target. The frozen
mapping is:

```text
approve → approved
reject  → rejected
dispute → disputed
```

Any other action — including `pending` — raises
`MemoryVaultReviewTransitionInvalid`. The caller can never supply a raw
`review_state`.

**Species boundary.** Only `episodic_semantic_memory` is writable. Personal
Facts and any other specialized species fail with
`MemoryVaultReviewTransitionUnsupported` and write nothing; this slice does not
delegate to the Personal Facts service.

**Locking.** Mutation authority is serialized on the canonical parent row via
the existing `_load_authorized_memory` helper, which issues
`SELECT ... FOR UPDATE`. That single lock covers CAS validation, the current
review-state read, the no-op decision, review-revision numbering, the
state mutation, and the receipt append. No process-global or application-global
lock was introduced.

**CAS order (mandatory).**

1. load the authorized parent under row lock;
2. compare `expected_updated_at` with `memory_records.updated_at`;
3. stale → conflict immediately, allocating nothing;
4. only after a fresh token may the same-state no-op be recognized.

A stale request therefore conflicts **even when the action would otherwise be a
no-op** — proven by `test_stale_cas_conflicts_even_on_same_state_action`.

---

## 4. ADR-088 enforcement

| Current state | `approve` | `reject` | `dispute` |
| --- | --- | --- | --- |
| `pending` | → `approved` | → `rejected` | → `disputed` |
| `approved` | no-op | → `rejected` | → `disputed` |
| `rejected` | → `approved` | no-op | → `disputed` |
| `disputed` | → `approved` | → `rejected` | no-op |

No path targets `pending`. A persisted `review_state` outside the canonical
vocabulary is treated as integrity corruption and fails closed; it is never
repaired.

---

## 5. No-op semantics

```text
fresh CAS + same target:
    changed = false
    receipt_id = null
    review_revision_id = null
    review_revision_number = null
    previous_review_state == resulting_review_state
    previous_updated_at == resulting_updated_at
    no review_state update
    no reviewed_at update
    no updated_at advance
    no review revision
    no receipt

stale CAS + same target:
    conflict (never a no-op success)
```

A same-state `approve` also does **not** backfill a missing `reviewed_at`;
provenance of a no-op is not a first approval.

---

## 6. Review history

**Numbering.** The next number is `1` when no review history exists, and
`latest + 1` otherwise. A direct-created `approved` memory therefore starts
review history at revision 1 with `old_review_state = "approved"` and **no
fabricated** prior revisions.

**Integrity gate.** Before every changed transition, existing
`memory_review_revisions` for the parent must satisfy `revision_count ==
max(revision_number)` (dense `1..N`) and `latest.new_review_state ==
memory_records.review_state`. Gapped history and divergent tails fail closed
and are never renumbered, repaired, deleted, or reconstructed from provenance
extensions.

**Server-authored fields.** `review_revision_id` (UUID), `revision_number`,
`actor_account_id` (the authenticated account), and `created_at` (database) are
all server-supplied. The review sequence is independent of the content
`memory_revisions` sequence — both may hold number 1 on the same memory.

---

## 7. `reviewed_at`

| Situation | Behavior |
| --- | --- |
| first transition to `approved` with `reviewed_at IS NULL` | set to `clock_timestamp()` |
| later re-approval (`reviewed_at` already set) | preserved exactly |
| transition to `rejected` | preserved |
| transition to `disputed` | preserved |
| same-state no-op | untouched |

Transition timing belongs to `memory_review_revisions.created_at`.

**Interaction with the frozen review-before-activation CHECK.** Qualification
surfaced a real constraint: `memory_records_review_activation_order_check`
requires `activated_at IS NULL OR (reviewed_at IS NOT NULL AND activated_at >=
reviewed_at)`. A memory with `reviewed_at IS NULL` must therefore also have
`activated_at IS NULL`. This is existing accepted architecture, not a defect,
and the writer respects it — it never sets `activated_at`.

---

## 8. Receipt

For each changed transition exactly one `memory_provenance` row is appended
with the existing `memory-vault-mutation.v1` schema, `mutation_source = vault`,
`actor_account_id` = authenticated account, `action` = the exact admitted
action, expected/resulting CAS evidence, and the optional `reason` /
`request_ref`.

Bounded transition evidence is recorded:

```text
previous_values: { review_state: <old> }
new_values:      { review_state: <new>,
                   review_revision_id: <id>,
                   review_revision_number: <n> }
```

The receipt contains no authored memory text — proven by asserting the memory
content string does not appear anywhere in the serialized receipt extensions.
The review revision is history authority; the receipt is intent/audit evidence.

---

## 9. Atomicity

One transaction, owned by the mutation service, covers:

```text
review_state update
reviewed_at update (first approval only)
CAS advance
memory_review_revisions append
memory_provenance receipt append
```

Forced-failure proofs:

- **Review-revision failure** (session `before_flush` seam): `review_state`,
  `reviewed_at`, and `updated_at` unchanged; zero review revisions; zero new
  receipts.
- **Receipt failure** (executor seam at `_build_receipt`): the staged review
  revision rolls back with the state change; zero committed review revisions;
  zero new receipts.

No production failure-injection hook was added.

---

## 10. Adjacent-state preservation

Explicitly confirmed unchanged by test:

```text
lifecycle changed: NO
content changed:   NO
pin changed:       NO
hold changed:      NO
project changed:   NO
persona changed:   NO
created_at changed: NO
```

Review revision and receipt append, plus `reviewed_at` on first approval, are
the only permitted collateral writes. Prior provenance is preserved and exactly
one receipt is appended.

---

## 11. HTTP

```text
PATCH /api/memory-vault/items/canonical/{memory_id}/review
```

Request: `action` (one of `approve` / `reject` / `dispute`),
`expected_updated_at`, optional `reason`, optional `request_ref`. The model
sets `extra="forbid"`, so caller-supplied authority fields — `user_id`,
`account_id`, `actor_account_id`, `review_revision_id`,
`review_revision_number`, `lifecycle_state`, `project_id`,
`persona_subject_id`, and `review_state` — are rejected with `422` rather than
silently ignored.

Response: `changed`, `action`, `receipt_id`, `review_revision_id`,
`review_revision_number`, `previous_review_state`, `resulting_review_state`,
`previous_updated_at`, `resulting_updated_at`, and the canonical `item`.

Status mapping:

| Condition | Status | Detail |
|---|---|---|
| blank account | `401` | — |
| missing / malformed / naive CAS, missing or unknown action, request-shape or authority-field errors | `422` | `Action must be one of: approve, reject, dispute` or FastAPI validation detail |
| missing or cross-account memory | `404` | `Memory not available` (identical body for both) |
| stale CAS | `409` | `Memory changed since it was read` |
| unsupported species, integrity failure, other mutation error | `409` | `Memory review transition unavailable` (sanitized) |

Sanitization is proven: the internal exception text, constraint names, and table
names never reach the response.

**Route delegation boundary.** The route performs request validation,
authenticated account resolution, service delegation, exception→HTTP mapping,
and response serialization. It performs no SQL, no parent lookup, no row
locking, no CAS comparison, no no-op determination, no state-machine
calculation, no review-revision numbering, no `reviewed_at` decision, no receipt
construction, and no read-before-write. Proven by asserting exactly one service
call carrying only request fields, and that the response contains no separate
content or old/new-state copy outside the canonical item.

---

## 12. Control plane

Route inventory measured from the mounted application, not from source grep:

| Inventory | Task opening | Task close | Delta |
|---|---|---|---|
| Path templates | 8 | 9 | **+1** |
| Methods | 9 | 10 | **+1** |

The only new path template is
`/api/memory-vault/items/canonical/{memory_id}/review` with method `PATCH`. No
existing Vault path or method was removed, re-pathed, or re-methoded, and no
new feature flag was created.

The route inherits the existing `memory_vault` internal-only posture:
`tests/routes/test_memory_vault_activation.py` now asserts the new PATCH path is
admitted internally for enabled admitted profiles, hidden from public OpenAPI,
and absent for quarantined profiles and when the feature flag is disabled.

---

## 13. Regression evidence

New review-transition coverage:

| Suite | Result |
|---|---|
| `tests/services/test_memory_vault_review_transition.py` | **44 passed** |
| `tests/routes/test_memory_vault_review_transition.py` | **30 passed** |
| `tests/routes/test_memory_vault_activation.py` (extended) | **7 passed** |

Full bounded Memory Vault sweep, discovered from the repository and run as
separate serial invocations per file to avoid disposable-database contention:

| File | Result |
|---|---|
| `tests/services/test_memory_vault_creation.py` | 15 passed |
| `tests/services/test_memory_vault_mutation.py` | 52 passed |
| `tests/services/test_memory_vault_read_projection.py` | 24 passed |
| `tests/services/test_memory_vault_content_correction.py` | 19 passed |
| `tests/services/test_memory_vault_review_transition.py` | 44 passed |
| `tests/routes/test_memory_vault.py` | 10 passed |
| `tests/routes/test_memory_vault_activation.py` | 7 passed |
| `tests/routes/test_memory_vault_content_correction.py` | 16 passed |
| `tests/routes/test_memory_vault_review_transition.py` | 30 passed |
| **Total** | **217 passed, 0 failed** |

Portability and migration regressions:

| Suite | Result |
|---|---|
| C10A-P portability: review export + restore | **41 passed** |
| C9 v5 portability: content export + restore | **23 passed** |
| `tests/services/test_account_restore_unified_memory.py` | **48 passed** |
| `tests/services/test_account_export_unified_memory.py` | same 2 known v4 baseline reds, no new failure |
| `tests/migration/test_memory_revision_persistence_migration.py` | **10 passed** |
| `tests/migration/test_memory_review_revision_persistence_migration.py` | **16 passed** |
| `tests/migration/test_memory_governance_state_migration.py` | **7 passed** |
| Alembic head | `a7c3e91d4b60`, single and unchanged |

Migration suites were run serially. The known disposable-child-database
teardown contention was distinguished from code failure by isolated rerun, as
in prior accepted UMS proofs: batched runs intermittently reported teardown
`ERROR`s on *different* tests each attempt, and every affected file passed
completely when run alone. No test assertion ever failed.

---

## 14. Invariants closeout

```text
current review authority remains memory_records.review_state:  YES
ADR-088 transition graph enforced:                             YES
direct target pending available:                               NO
same-state action mutates canonical state:                     NO
stale same-state action conflicts:                              YES
changed transition creates review revision:                    YES
changed transition creates intent receipt:                     YES
review history stored in provenance extensions:                NO
content revision authority widened:                            NO
Personal Fact generic review mutation added:                   NO
approval auto-activates:                                       NO
reject auto-retires:                                           NO
dispute auto-retires:                                          NO
lifecycle state changed:                                       NO
reviewed_at preserves first approval:                          YES
schema changed:                                                NO
export/restore changed:                                        NO
frontend changed:                                              NO
retrieval redesigned:                                          NO
release claim expanded:                                        NO
```

---

## 15. Runtime boundary

```text
ordinary review writer:     IMPLEMENTED INTERNAL-ONLY
approve:                    IMPLEMENTED
reject:                     IMPLEMENTED
dispute:                    IMPLEMENTED

direct target pending:      NOT IMPLEMENTED
lifecycle writer:           NOT IMPLEMENTED
Personal Fact generic review mutation: NOT IMPLEMENTED
review-history read API:    NOT IMPLEMENTED
frontend:                   NONE
retrieval redesign:         NONE
release claim expansion:    NONE
```

---

## 16. Closeout

```text
UMS05C10AW_REVIEW_TRANSITION_WRITER_COMMITTED
```

Campaign transition:

```text
UMS-05C10A-R REVIEW-TRANSITION HISTORY REVALIDATION: CLOSED
UMS-05C10A-P REVIEW-TRANSITION REVISION PERSISTENCE
              + UMS-04 PORTABILITY: CLOSED
UMS-05C10A-C REVIEW-TRANSITION CONTRACT RESOLUTION: CLOSED
UMS-05C10A-W ORDINARY MEMORY REVIEW TRANSITION WRITER: CLOSED
UMS-05C10A: CLOSED
UMS-05C10B-R ORDINARY MEMORY LIFECYCLE MUTATION
              AUTHORITY / HISTORY REVALIDATION: AUTHORIZED
UMS-05C10B WRITER: NOT AUTHORIZED
UMS-05C11+: NOT AUTHORIZED
UMS-05D+:  NOT AUTHORIZED
UMS-06+:   NOT AUTHORIZED
```

`UMS-05C10B-R` is the sole successor. It must first determine whether ordinary
lifecycle transitions require additional canonical historical persistence and
whether the lifecycle transition graph is already explicit. It was not begun.

Gitleaks was skipped narrowly: the sandbox cannot bootstrap the Go toolchain.
Every other executable pre-commit hook ran. `gitleaks` is required at branch
integration.
