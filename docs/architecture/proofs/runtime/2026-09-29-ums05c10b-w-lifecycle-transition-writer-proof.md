# UMS-05C10B-W — Ordinary-Memory Retire / Restore Writer

**Status:** CLOSED
**Slice:** `UMS-05C10B-W` — direct lifecycle mutation authority
**Campaign:** Unified Account-Owned Memory Store
**Date:** 2026-09-29
**ADR impact:** Aligned with ADR-084 and ADR-089. No new ADR. Implements frozen semantics without reopening them.
**Class:** Canonical lifecycle mutation authority / optimistic concurrency / lifecycle-history append / API adapter

---

## 1. Lineage

| Field | Value |
|---|---|
| Branch | `feature/ums-continued` |
| Starting HEAD | `69a523c25ebcceee3863cc8b5967c799b4218f05` |
| C10B-C | `69a523c25ebcceee3863cc8b5967c799b4218f05` |
| C10B-P | `3b4516894723848a04d1c26a330716b78762e2e6` (ancestor) |
| C10A-W | `39dbd7a4fe03da8deb0b95b2c6bd6a5b1ddc7d03` (ancestor) |
| Alembic head before | `b8e2f4a6c901` (single head) |
| Alembic head after | `b8e2f4a6c901` (single head, **unchanged**) |
| Opening index | empty |
| Untracked posture | only preserved `.precommit_cache/` / `.precommit_home/` entries |
| Push count | `0` |

---

## 2. Service authority

```python
MemoryVaultMutationService.transition_lifecycle(
    *,
    memory_id: str,
    expected_updated_at: datetime,
    action: str,
    reason: str | None = None,
    request_ref: str | None = None,
) -> VaultLifecycleTransitionResult
```

- **Account authority** is constructor-bound via `authenticated_account_id`;
  no per-call override exists.
- **Action vocabulary** is exactly `retire` / `restore`, held in
  `ACTION_RETIRE` / `ACTION_RESTORE`. The service exposes no
  `set_lifecycle_state`, `activate`, or `reactivate`; a test asserts those
  attribute names are absent, so the runtime action boundary stays narrower
  than the persistence vocabulary.
- **Species boundary:** only `episodic_semantic_memory` is writable. Personal
  Facts and other specialized species fail with
  `MemoryVaultLifecycleUnsupported` and write nothing. No delegation.
- **Row lock:** the existing `_load_authorized_memory` helper issues
  `SELECT ... FOR UPDATE`. That single lock covers the row read, CAS check,
  no-op decision, history integrity read, restore-target resolution,
  revision-number allocation, state mutation, and receipt append — because the
  parent mutation transaction holds it for the whole call. No application- or
  process-global lock was introduced.
- **CAS order:** the token is compared *before* the lifecycle state is even
  inspected, so a stale token conflicts even when the requested action is
  already satisfied. Verified for `retire` on `retired` and `restore` on
  `active` / `dormant`.

---

## 3. State machine (ADR-089 enforced)

| Current lifecycle | `retire` | `restore` |
| --- | --- | --- |
| `active` | → `retired` (changed) | no-op |
| `dormant` | → `retired` (changed) | no-op |
| `retired` | no-op | → history-derived `active` or `dormant` |

All six changed cases and all three no-op cases are proven by test.

---

## 4. Restore-history proof

Restore is **not** "set active." The target is recovered only from the
canonical lifecycle-history tail:

```text
active  -> retired -> restore -> active
dormant -> retired -> restore -> dormant
```

Both are proven, and a dedicated test proves the two retirement postures stay
distinguishable — restore never normalizes everything to `active`, nor
everything to `dormant`.

**Immediate tail, not the first retirement ever recorded.** A
three-transition history

```text
1 active  -> retired
2 retired -> active
3 active  -> retired
```

restores to `active` on transition 4, because the *current* tail supplies the
immediate pre-retirement state. The writer does not search backward for an
arbitrary earlier posture.

**Fail-closed cases proven**, none of which guess `active` or `dormant`:

- retired with **zero** lifecycle history (the legacy case C10B-P deliberately
  created) — fails closed;
- **gapped** history;
- **broken chain**;
- **tail/current-state mismatch**;
- a provenance extension *claiming* `lifecycle_history: [active, retired]` is
  **not** consulted as authority and does not unblock the restore.

Malformed history is never repaired, renumbered, deleted, or synthesized.

---

## 5. No-op proof

```text
fresh CAS + already-satisfied action:
    changed = false
    receipt_id = null
    lifecycle_revision_id = null
    lifecycle_revision_number = null
    previous_lifecycle_state == resulting_lifecycle_state
    previous_updated_at == resulting_updated_at
    no lifecycle revision
    no receipt
    no CAS advance

stale CAS + already-satisfied action:
    conflict
```

`reason` / `request_ref` do not convert a no-op into a mutation. No
`retired -> retired` history is invented.

---

## 6. Revision proof

Each changed transition appends exactly one `memory_lifecycle_revisions` row
with server-authored identity, number, and timestamp. A first retirement from
zero history starts at revision 1 with no fabricated prior history. Exact
`old_lifecycle_state` / `new_lifecycle_state` are persisted.

Numbering is proven independent of both other families: with a content
revision and a review revision already at number 1, the first lifecycle
transition still receives number 1.

No new columns were added. ADR-089 and C10B-C explicitly left the stale
`dormant_at` / `retired_at` prose ahead of physical storage; C10B-W did not
create them. Transition time lives in `memory_lifecycle_revisions.created_at`.

---

## 7. Receipt proof

Each changed transition appends exactly one `memory-vault-mutation.v1` receipt
whose `action` is exactly `retire` or `restore`, carrying bounded
previous/resulting lifecycle evidence plus the lifecycle revision identity and
number. Authored memory content is asserted absent from the receipt. A no-op
creates no receipt.

The receipt is intent/audit evidence; the lifecycle revision is canonical
transition history. Neither is promoted to the other's role.

---

## 8. Independence

```text
review_state changed:   NO   (all of approved/pending/rejected/disputed)
hold changed:            NO   (held memory can explicitly retire and restore)
pin changed:             NO
content changed:         NO
project changed:         NO
persona links changed:   NO
context posture changed: NO / NOT PHYSICALLY PRESENT
```

**Context posture finding:**

```text
CONTEXT POSTURE PHYSICAL FIELD: NOT PRESENT
```

`memory_records` has no context-posture column on this branch. Recorded, not
invented, and not repaired by lifecycle mutation.

---

## 9. Atomicity

```text
lifecycle_state update
updated_at / CAS advance
lifecycle revision append
mutation receipt append
```

One transaction owned by the service.

- **Forced lifecycle-revision failure** (session `before_flush` seam): state,
  CAS, review, hold, and pin all unchanged; zero new lifecycle revisions; zero
  new receipts.
- **Forced receipt failure** (`_build_receipt` seam): state and CAS unchanged;
  the staged lifecycle revision rolls back with it; zero new receipts.

No production failure-injection hook was added.

---

## 10. Control plane

| Inventory | Task opening | Task close | Delta |
|---|---|---|---|
| Path templates | 9 | 10 | **+1** |
| Methods | 10 | 11 | **+1** |

The only new template is
`/api/memory-vault/items/canonical/{memory_id}/lifecycle` with method `PATCH`.
No existing Vault path or method was removed, re-pathed, or re-methoded, and no
new feature flag was created. The route inherits the existing `memory_vault`
internal-only posture and stays hidden from public OpenAPI.

---

## 11. Derived lifecycle eligibility classification

```text
DERIVED LIFECYCLE ELIGIBILITY UPDATE OBLIGATION:
NONE — eligibility is computed from canonical state; no stored or indexed
       derived eligibility surface exists on this branch
```

Verified by implementation search, consistent with the C10A-W finding: ambient
eligibility is computed read-time in `guardian/core/memory_compatibility.py`
and there is no vector index, materialized membership, or cache keyed on
`memory_records.lifecycle_state`. Changing lifecycle state therefore cannot
leave an authoritative derivative stale.

---

## 12. Automatic decay boundary

```text
direct retire/restore:                 IMPLEMENTED
automatic active->dormant decay:       NOT IMPLEMENTED BY THIS TASK
automatic dormant->active:             NOT INTRODUCED
direct activation:                     NOT IMPLEMENTED
```

No decay code path, worker, or cron integration was added, and the direct
service is not called from any background decay path. Hold still governs
automatic decay per ADR-089, and no decay implementation exists to weaken.

---

## 13. HTTP

```text
PATCH /api/memory-vault/items/canonical/{memory_id}/lifecycle
```

Request: `action` (`retire` | `restore`), `expected_updated_at`, optional
`reason`, optional `request_ref`. The model sets `extra="forbid"`, so account,
actor, revision identity, revision number, prior posture, review, hold, pin,
project, and persona fields are all rejected rather than silently ignored, and
a raw lifecycle target cannot be submitted.

Response: `changed`, `action`, `receipt_id`, `lifecycle_revision_id`,
`lifecycle_revision_number`, `previous_lifecycle_state`,
`resulting_lifecycle_state`, `previous_updated_at`, `resulting_updated_at`, and
the canonical `item`. No internal history diagnostic is exposed.

| Condition | Status | Detail |
|---|---|---|
| blank account | `401` | — |
| missing / malformed / naive CAS, unknown action, authority field | `422` | `Action must be one of: retire, restore` or validation detail |
| missing or cross-account memory | `404` | `Memory not available` (identical body for both) |
| stale CAS | `409` | `Memory changed since it was read` |
| unsupported species, integrity failure, incl. zero-history restore | `409` | `Memory lifecycle transition unavailable` (sanitized) |

Sanitization is proven: the internal exception text, constraint names, and table
names never reach the response.

**Route delegation boundary.** The route performs request validation,
account resolution, service invocation, exception mapping, and serialization.
It performs no SQL, parent lookup, row lock, CAS comparison, lifecycle
state-machine logic, no-op determination, lifecycle-history read,
restore-target resolution, revision numbering, receipt construction, or
read-before-write — proven by asserting exactly one service call carrying only
the request fields.

---

## 14. Regressions

Focused suites:

| Suite | Result |
|---|---|
| `tests/services/test_memory_vault_lifecycle_transition.py` | **52 passed** |
| `tests/routes/test_memory_vault_lifecycle_transition.py` | **39 passed** |
| `tests/routes/test_memory_vault_activation.py` | **7 passed** |

Full bounded Memory Vault sweep, discovered from the repository and run as
separate serial invocations per file:

| File | Result |
|---|---|
| `tests/services/test_memory_vault_creation.py` | 15 passed |
| `tests/services/test_memory_vault_mutation.py` | 52 passed |
| `tests/services/test_memory_vault_read_projection.py` | 24 passed |
| `tests/services/test_memory_vault_content_correction.py` | 19 passed |
| `tests/services/test_memory_vault_review_transition.py` | 44 passed |
| `tests/services/test_memory_vault_lifecycle_transition.py` | 52 passed |
| `tests/routes/test_memory_vault.py` | 10 passed |
| `tests/routes/test_memory_vault_activation.py` | 7 passed |
| `tests/routes/test_memory_vault_content_correction.py` | 16 passed |
| `tests/routes/test_memory_vault_review_transition.py` | 30 passed |
| `tests/routes/test_memory_vault_lifecycle_transition.py` | 39 passed |
| **Total** | **308 passed, 0 failed** |

Lifecycle test contribution to the sweep: 52 service + 39 route = **91**.

Portability and persistence regressions:

| Suite | Result |
|---|---|
| Lifecycle portability (v7 export + restore) | **44 passed** (20 + 24) |
| Review portability (v6) | **41 passed** |
| Content portability (v5) | **23 passed** |
| `test_account_restore_unified_memory.py` | **48 passed** |
| Migration: governance | **7 passed** |
| Migration: C9 revision | **10 passed** |
| Migration: C10A review revision | **16 passed** |
| Migration: C10B-P lifecycle revision | **13 passed** |
| Alembic head | `b8e2f4a6c901`, one, unchanged |
| `test_account_export_unified_memory.py` | same 2 known v4 reds, no new failure |

Known disposable-child-database teardown contention recurred in batched
runs (intermittent setup/teardown `ERROR`s naming a different test each
attempt). Every affected file passed completely in isolated rerun, and **no
test assertion ever failed**. No genuine defect was hidden under that
classification: the only real defect found in this slice, the misattached
`@dataclass` decorator in §15, surfaced as a deterministic assertion failure
and is recorded there.

---

## 15. Defect found and fixed during this slice

A `@dataclass(slots=True)` decorator that belonged to
`VaultReviewTransitionResult` was misattached to the newly inserted
`MemoryVaultLifecycleInvalid` class. That silently turned an exception class
into a dataclass, so raising it with a message failed with
`TypeError: __init__() takes 1 positional argument but 2 were given` and surfaced
as a `500` at the route. The decorator was removed and the result dataclass
re-verified. It was an editing-splice error introduced in this slice, not a
pre-existing defect, and it was caught by the route suite before commit.

---

## 16. Invariants closeout

```text
current lifecycle authority remains memory_records.lifecycle_state: YES
ADR-089 state machine enforced:                                 YES
generic direct activation added:                                NO
automatic decay added:                                          NO
restore uses canonical lifecycle history:                       YES
restore defaults to active:                                     NO
restore defaults to dormant:                                    NO
zero-history retired restore guessed:                           NO
stale no-op bypasses CAS:                                       NO
changed transition creates lifecycle revision:                  YES
changed transition creates intent receipt:                      YES
lifecycle history stored in provenance extensions:             NO
content revision authority widened:                             NO
review revision authority widened:                              NO
review state changed by lifecycle writer:                       NO
hold changed by lifecycle writer:                               NO
pin changed by lifecycle writer:                                NO
Personal Fact generic lifecycle mutation added:                 NO
schema changed:                                                 NO
export/restore changed:                                         NO
frontend changed:                                               NO
retrieval redesigned:                                           NO
release claim expanded:                                         NO
```

---

## 17. Runtime boundary

```text
direct ordinary lifecycle writer:        IMPLEMENTED INTERNAL-ONLY
retire:                                  IMPLEMENTED
restore:                                 IMPLEMENTED

direct activate:                         NOT IMPLEMENTED
direct dormant:                          NOT IMPLEMENTED
generic set_lifecycle_state:             NOT IMPLEMENTED
automatic decay:                         NOT IMPLEMENTED BY THIS TASK
automatic reactivation:                  NOT IMPLEMENTED
Personal Fact generic lifecycle mutation: NOT IMPLEMENTED
lifecycle-history read API:              NOT IMPLEMENTED
frontend lifecycle controls:             NONE
retrieval redesign:                      NONE
release claim expansion:                 NONE
```

---

## 18. Parked follow-up

```text
C10A review restore sequence-occupancy error shaping:
    PARKED / NON-BLOCKING / UNCHANGED
```

Account restore code and C10A review behavior were not edited. This is not a
C10B-W prerequisite and is not a second successor.

---

## 19. Closeout

```text
UMS05C10BW_LIFECYCLE_TRANSITION_WRITER_COMMITTED
```

Campaign transition:

```text
UMS-05C10A: CLOSED
UMS-05C10B-R: CLOSED
UMS-05C10B-P: CLOSED
UMS-05C10B-C: CLOSED
UMS-05C10B-W: CLOSED
UMS-05C10B: CLOSED
UMS-05C10:  CLOSED
UMS-05C11+: NOT AUTHORIZED
UMS-05D+:  NOT AUTHORIZED
UMS-06+:   NOT AUTHORIZED
NEXT ACTION: CAMPAIGN REVALIDATION REQUIRED
```

C11+ is deliberately **not** authorized. C10B-W completes the governed
review/lifecycle mutation seam; the next move is Campaign revalidation against
the UMS baseline and stop rule, not automatic feature expansion.

Gitleaks was skipped narrowly: the sandbox cannot bootstrap the Go toolchain.
Every other executable pre-commit hook ran. `gitleaks` is required at branch
integration.
