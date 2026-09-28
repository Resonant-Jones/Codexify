# UMS-05C10A-C — Freeze Ordinary-Memory Review Transition Semantics

**Status:** CLOSED
**Slice:** `UMS-05C10A-C` — review-transition contract resolution
**Campaign:** Unified Account-Owned Memory Store
**Date:** 2026-09-28
**ADR impact:** NEW ADR REQUIRED AND CREATED — **ADR-088 Ordinary Memory Review Transition Semantics**, aligned with ADR-084, not superseding it
**Class:** Authority semantics / state-machine contract resolution. Documentation only.

---

## 1. Lineage

| Field | Value |
|---|---|
| Branch | `feature/ums-continued` |
| Starting HEAD | `a38c6ad81609cb967fa7e04a0ae072efab5c69e6` |
| C10A-P commit | `a38c6ad81609cb967fa7e04a0ae072efab5c69e6` |
| C10A-R commit | `a49dff0044150eb142f4324b3bfa8684181d3248` (ancestor) |
| C9-W commit | `2c21cd0e0a6cfc242643d1ca029ed8e1d1b40888` (ancestor) |
| Alembic head | `a7c3e91d4b60` (single head, unchanged) |
| Index posture | clean; no runtime/schema commit follows C10A-P |
| New ADR | `docs/architecture/adr/088-ordinary-memory-review-transition-semantics.md` |
| Push count | `0` |

No runtime or schema work landed after C10A-P, so the opening posture required
no drift classification beyond confirming the lineage.

---

## 2. Persistence prerequisite (verified read-only)

Confirmed against the committed branch, not against the task spec:

```text
memory_review_revisions table/model/migration:  PRESENT
  guardian/db/models.py
  guardian/db/migrations/versions/a7c3e91d4b60_persist_ordinary_memory_review_revisions.py
  guardian/core/pgdb.py
  guardian/services/account_export.py
  guardian/services/account_restore.py

account-export.v6 constant:                     PRESENT
  guardian/services/account_export.py
  REVIEW_REVISION_MANIFEST_SCHEMA_VERSION = "account-export.v6"
```

A production ordinary review writer does **not** exist. A repository search for
`def approve` / `def reject` / `def dispute` and for `ACTION_APPROVE` /
`ACTION_REJECT` / `ACTION_DISPUTE` returns only Personal Facts surfaces
(`guardian/routes/personal_facts.py`, `guardian/core/pgdb.py:dispute_fact`)
and unrelated subsystems (delegation, install gate, extensions). None is an
ordinary `memory_records.review_state` writer. The canonical Memory Vault
mutation action vocabulary (`pin`, `unpin`, `hold`, `release_hold`,
`set_project_scope`, `clear_project_scope`, `add_persona_attribution`,
`remove_persona_attribution`, `content_correction`) does not name review
actions, so the frozen labels `approve` / `reject` / `dispute` conflict with no
existing token.

---

## 3. The contract gap this slice closed

UMS-05C10A-R recorded:

```text
REVIEW_HISTORY_NEW_CANONICAL_PERSISTENCE_REQUIRED
TRANSITION_GRAPH: NOT EXPLICIT
```

UMS-05C10A-P closed the first. The second remained: no current contract defined
which `source → target` review transitions were legal, whether `pending` could
be re-entered, whether approval activated a record, or what `reviewed_at` meant
after re-approval. A writer could not have been implemented without making those
architectural decisions inside code.

---

## 4. Frozen state machine

State meanings: `pending` is an ingress / unreviewed state, not a user review
outcome. `approved` is authenticated user acceptance as memory authority.
`rejected` is authenticated user rejection. `disputed` is authenticated user
contestation, distinct from both `pending` and `rejected`.

Direct actions: exactly `approve`, `reject`, `dispute`.

| Current state | `approve` | `reject` | `dispute` |
| --- | --- | --- | --- |
| `pending` | → `approved` | → `rejected` | → `disputed` |
| `approved` | no-op | → `rejected` | → `disputed` |
| `rejected` | → `approved` | no-op | → `disputed` |
| `disputed` | → `approved` | → `rejected` | no-op |

No other transition is legal.

**Same-state requests** are semantic no-ops, not transitions: no review
revision, no receipt, no `updated_at` advance. CAS is validated **first**, so a
stale token conflicts even when the target equals current state.

**No direct action targets `pending`.** `approved → pending`, `rejected →
pending`, and `disputed → pending` are illegal. `pending` encodes "authoritative
review has not occurred"; reusing it as a reset would make one token mean both
never-reviewed and review-invalidated, destroying the meaning of both review
history and `reviewed_at`.

---

## 5. Lifecycle independence

```text
approval auto-activates:   NO
reject auto-retires:       NO
dispute auto-retires:      NO
retire changes review_state: NO
restore auto-approves:     NO
```

Review and lifecycle remain independent axes. `approved + active`,
`approved + dormant`, and `approved + retired` are all valid. The existing
ambient-eligibility law is unchanged, so `pending`, `rejected`, and `disputed`
ordinary memory is ambient-ineligible without any lifecycle mutation. No stored
`ambient_eligible` field was introduced.

---

## 6. Timestamp semantics

```text
reviewed_at                        = first authoritative approval
memory_review_revisions.created_at = per-transition time
```

`reviewed_at` is not the latest transition time, not a current-state timestamp,
not a rejection or dispute time, and not review-history authority. First
approval sets it when `NULL`; re-approval preserves it; transition to `rejected`
or `disputed` never clears or rewrites it.

---

## 7. History requirement

```text
changed review transition:
    memory_records.review_state update
    + one memory_review_revisions row
    + one memory-vault-mutation.v1 intent receipt

same-state request:
    no review revision
    no receipt
    no CAS advance
```

The receipt is not canonical history, and the revision is not a receipt.

---

## 8. Boundaries frozen

**Personal Facts.** Nothing in ADR-088 applies direct ordinary review
transitions to Personal Facts. They remain governed by `personal_facts.status`,
`personal_facts.is_active`, `personal_fact_revisions`, and Personal Facts
service authority. The future ordinary writer must refuse or delegate at that
boundary.

**Actor authority.** The authoritative actor is the authenticated account
principal. A model, importer, classifier, assistant, web result, or tool result
may not promote a pending ordinary memory to approved authority by emitting
output.

**Automated capture.** Non-authoritative capture may produce `pending`; it may
not directly produce `pending → approved` outside an explicitly authenticated
user-authority path. Capture policy is otherwise unchanged.

**Direct creation.** Explicit user-authored creation may still create an
`approved` record where the UMS contract allows it. That is not a
`pending → approved` transition and must not be given a fabricated review
revision. UMS-05C6 creation semantics are unchanged.

---

## 9. Contract reconciliation

The Memory Vault contract §5.1 review rows previously read
"canonical review-state transition / durable mutation receipt", diverging from
the normative UMS §3.3 rule that an authority-changing transition produces a
revision **and** a receipt. UMS-05C10A-R recorded that divergence and
deliberately left it open.

This slice resolves it in favor of the normative §3.3 rule:

- the §5.1 Approve and Reject/dispute rows now state the
  `memory_records.review_state` transition **plus** one `memory_review_revisions`
  row, with receipt **+ canonical review revision**;
- §5.1.1 is rewritten from "gate" to contracted future behavior, restating the
  ADR's matrix, no-op, CAS, timestamp, and delegation rules so the operator
  surface is self-describing;
- UMS contract §3.3.1 makes the state machine normative;
- UMS contract §4.16.5a and §4.16.5b, which still described the graph as
  "not explicit" / "unresolved", now point to §3.3.1 and ADR-088, so no section
  contradicts the frozen graph.

No new ADR was created for a table design, and ADR-084 was neither modified nor
superseded.

---

## 10. ADR index

The canonical index's highest existing number was `087`, so the new ADR is
`088`. It was added in both existing index conventions: the numbered summary
list and the detailed per-ADR bullet list.

`docs/architecture/README.md` was **not** updated: the last three accepted ADRs
(`085`, `086`, `087`) are likewise absent from it, so the repository convention
does not require an entry there.

---

## 11. Runtime boundary

```text
approve writer:                   NOT IMPLEMENTED
reject writer:                    NOT IMPLEMENTED
dispute writer:                   NOT IMPLEMENTED
review route:                     NOT IMPLEMENTED
lifecycle writer:                 NOT IMPLEMENTED
schema change:                    NONE
migration change:                 NONE
export schema change:             NONE
test change:                      NONE
frontend change:                  NONE
retrieval change:                 NONE
release claim change:             NONE
```

---

## 12. Invariants closeout

```text
review transition graph explicit:            YES
direct target pending allowed:               NO
same-state request is mutation:              NO
approval auto-activates:                     NO
reject auto-retires:                         NO
dispute auto-retires:                        NO
lifecycle mutation changes review authority: NO
reviewed_at means first approval:            YES
changed transition requires review revision: YES
changed transition requires intent receipt:  YES
receipt treated as canonical history:        NO
Personal Fact authority changed:             NO
runtime writer implemented:                  NO
schema changed:                              NO
export schema changed:                       NO
frontend changed:                            NO
retrieval changed:                           NO
release claim expanded:                      NO
```

---

## 13. Closeout

```text
UMS05C10AC_REVIEW_TRANSITION_CONTRACT_COMMITTED
```

Campaign transition:

```text
UMS-05C9-W ORDINARY MEMORY CONTENT CORRECTION WRITER: CLOSED
UMS-05C10: OPEN
UMS-05C10A-R REVIEW-TRANSITION HISTORY REVALIDATION: CLOSED
UMS-05C10A-P REVIEW-TRANSITION REVISION PERSISTENCE
              + UMS-04 PORTABILITY: CLOSED
UMS-05C10A-C REVIEW-TRANSITION CONTRACT RESOLUTION: CLOSED
UMS-05C10A-W ORDINARY MEMORY REVIEW TRANSITION WRITER: AUTHORIZED
UMS-05C10B ORDINARY MEMORY LIFECYCLE WRITER: NOT AUTHORIZED
UMS-05C11+: NOT AUTHORIZED
UMS-05D+:  NOT AUTHORIZED
UMS-06+:   NOT AUTHORIZED
```

`UMS-05C10A-W` is the sole successor and was not begun. It may now implement
`approve`, `reject`, and `dispute` against the frozen graph and the C10A-P
persistence without making further architectural decisions.

Gitleaks was skipped narrowly: the sandbox cannot bootstrap the Go toolchain.
Every other executable pre-commit hook ran. `gitleaks` is required at branch
integration.
