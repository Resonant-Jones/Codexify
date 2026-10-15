# UMS-05C10A-R — Revalidate Ordinary-Memory Review-Transition History Authority

**Status:** CLOSED
**Slice:** `UMS-05C10A-R` — review-transition history authority revalidation
**Campaign:** Unified Account-Owned Memory Store
**Date:** 2026-09-28
**ADR result:** ALIGNED WITH ADR-084 — no new ADR
**Class:** Documentation / architecture qualification. No runtime, schema, route, or test change.

---

## 1. Terminal classification

```text
REVIEW_HISTORY_NEW_CANONICAL_PERSISTENCE_REQUIRED
```

A second, independent finding is recorded but is **not** the terminal history classification:

```text
TRANSITION_GRAPH: NOT EXPLICIT
```

The two findings point at the same successor for different reasons, and only one successor is
authorized. See §8.

---

## 2. The question

What canonical historical evidence, if any, must an ordinary-memory `review_state` transition
preserve, in addition to current state and its intent receipt?

This slice answers that from current branch truth only. It does not answer it from memory, from
older planning prose, or from the C7/C8/C9 narrative.

---

## 3. Lineage

| Field | Value |
|---|---|
| Branch | `feature/ums-continued` |
| Expected starting HEAD (spec) | `2c21cd0e0a6cfc242643d1ca029ed8e1d1b40888` |
| Actual starting HEAD | `cdd7dbde03324b55a23f4cf2432085c3bc68f8ad` |
| C9-W `2c21cd0e0` in ancestry | yes |
| Alembic head | `c3d9f4e6a1b2` (single head, unchanged) |
| Index at start | empty |

### 3.1 Classification of the extra commit

`HEAD` is one commit past the expected starting point:

```text
cdd7dbde0 Correct C9-W campaign labels and record control-plane delta
```

Classification: **C9-W documentation closeout correction.** It touches three documentation files
only — the Campaign README, `00-current-state.md`, and the C9-W proof receipt. It changed the
campaign labels from `C10`/`C10B` to the specified `UMS-05C10: OPEN` / `C10A` / `C10B` form and
added the control-plane route-inventory delta to the C9-W proof.

It contains **no production code, no schema, no migration, no test, and no export/restore
change**. No C9-W implementation was silently absorbed into this task, and nothing after
`2c21cd0e0` changed any authority surface this revalidation examines. Proceeding was correct.

---

## 4. Governing language

### 4.1 Current normative statements about authority-changing transitions

**Unified Memory Store contract §3.3 "Ordinary-memory authority"** (lines 112–120). This is the
governing rule and it is **current and unamended**:

```text
For ordinary memories:
- `review_state` is the sole review authority;
- `lifecycle_state` is the sole lifecycle authority;
- explicit user-authored remember actions may create an approved, active record;
- classifier, importer, assistant, web, and tool suggestions cannot create an
  approved record; and
- every authority-changing transition produces a revision and intent receipt.
```

A review transition is an authority-changing transition. On the face of the current contract it
requires **both** a revision and an intent receipt.

**Unified Memory Store contract §4.8** (line 723), the same document, the same commit: the
`Content form` cell for `episodic_semantic_memory` reads

```text
mutable in place; revisioned on authority transitions
```

**Unified Memory Store contract §5.3 "Edit and reapproval behavior"** (lines 1978–1986), same
commit. Two *non-content* authority changes are described as revisioned:

| Mutation source | Required result |
| --- | --- |
| User changes Project scope | **explicit revisioned action**; Project authority revalidated |
| User changes persona association | **explicit revisioned action**; persona ownership revalidated |

This is the decisive precedent: the current contract already requires revisioning for authority
changes that are **not** content edits. Content revisioning is therefore not a special case that
absorbs all revision obligations.

### 4.2 The countervailing text, and why it does not win

**Memory Vault contract §5.1 "UMS-05 admitted direct actions"** lists review actions with a
receipt and no revision:

| Action | Resulting mutation | Receipt |
| --- | --- | --- |
| Direct Vault creation … | new canonical `memory_records` row … | durable mutation receipt **+ revision** |
| Approve (where the subtype permits) | canonical review-state transition | durable mutation receipt |
| Reject / dispute (where the subtype permits) | canonical review-state transition | durable mutation receipt |
| Correct / edit user-governed content | new canonical revision, audit-trailed | durable mutation receipt |

This diverges from §3.3 for the review rows. It was examined against the spec's Option-B test and
does not qualify as an intentional accepted refinement:

1. **Lineage.** The table was introduced by `12e200541 "Freeze Memory Vault operator contract"`,
   which corresponds to `UMS-05A MEMORY VAULT OPERATOR CONTRACT: CLOSED`. It is later than the
   §3.3 freeze (`4d2de549e "Freeze unified memory store architecture"`), but lateness alone is not
   a refinement.
2. **No proof lineage.** `12e200541` added 492 lines of contract and **no proof artifact** — its
   full file list is the contract, the architecture README, `00-current-state.md`, and the
   Campaign README. No adjudication of review-revision authority is recorded anywhere. The
   revalidation sweep found **no** proof artifact in `docs/architecture/proofs/runtime` that
   addresses review-transition history authority.
3. **No explicit statement.** Path 2 of the spec's sufficiency rule requires the contract to
   *explicitly* establish that `review_state` + intent receipt is the complete review mutation
   record. §5.1 does not say that. It lists a receipt in a column headed `Receipt`; it makes no
   claim that a canonical review revision is unnecessary.
4. **The table's own placement is inconsistent**, which weakens any inference from a cell's
   contents. The creation row puts a revision in the `Receipt` column; the edit row puts its
   revision in the `Resulting mutation` column. A review row's silence in `Receipt` is therefore
   weak evidence of intent.
5. **It is contradicted on the same subject by the same contract family.** §5.3 calls Project
   scope and persona association "explicit revisioned action[s]", yet §5.1's rows for those same
   two actions likewise name only a durable mutation receipt. The table and §5.3 disagree about
   revisioning for actions §5.3 explicitly calls revisioned, which shows the divergence is a
   documentation inconsistency rather than a considered decision.

The correct reading is that §5.1 enumerates durable **evidence** per action and does not restate
§3.3's revision requirement, except where the row author chose to highlight it. **C10A must not
read §5.1 as permission to skip the revision.** This slice does not repair §5.1; see §9.

### 4.3 C9's contribution, and what it did not do

`memory_revisions` was added by C9 at Unified Memory Store contract §4.16.5, which defines it as
the canonical append-only **content** history:

> Added by UMS-05C9. `memory_revisions` is the canonical append-only **content** history for
> ordinary memory.

C9 **did not** amend §3.3, §4.8, or §5.3. C9 added a content-revision family; it did not
narrow, supersede, or reinterpret "every authority-changing transition produces a revision and
intent receipt" for non-content authority transitions. There is therefore **no** later accepted
contract that explicitly distinguishes content revisions from non-content authority revisions in
a way that narrows §3.3.

**Meaning of "revision" under the current contract:** the contract uses "revisioned" for at
least three distinct things — content transitions (§4.16.5 `memory_revisions`), non-content
ordinary authority changes such as Project scope and Persona attribution (§5.3), and Personal
Fact field transitions (`personal_fact_revisions`). C9's `memory_revisions` satisfies only the
first. It is not a general authority-transition revision store, and its name does not make it
one.

---

## 5. Persistence inventory

| Surface | Current-state authority | Historical authority | Portable | Applicable to review transitions |
| --- | --- | --- | --- | --- |
| `memory_records.review_state` | **Yes** — sole review authority (§3.3) | No | Yes (family 3 of v5) | Present state only |
| `memory_records.reviewed_at` | Supporting | No | Yes (with family 3) | No — contract defines it as "Timestamp at which user review **first** approved the row" |
| `memory_records.updated_at` | CAS token | No | Yes | No — last-write, not per-transition |
| `memory_records.lifecycle_state` | Sole lifecycle authority | No | Yes | Independent dimension (§3.3) |
| `memory_revisions` | No | **Content history only** (§4.16.5) | Yes (family 6 of v5) | **No** — typed `old_text_content` / `new_text_content`; semantically inapplicable |
| `memory_provenance` | No | No — audit/evidence | Yes (family 5 of v5) | No — receipts are evidence, `extensions` non-authority |
| `memory_provenance.extensions` | No | No — explicitly non-authority | Yes | **No** — must not be repurposed as canonical semantic state |
| `personal_fact_revisions` | No (PF only) | Yes, for Personal Facts | PF portability, not ordinary | **No** — Personal Facts are specialized and out of generic ordinary authority |
| `AuditLog` / `GuardianEventLog` / other event surfaces | No | No | No — not a v5 family, not account-owned canonical memory state | No — unrelated |
| Legacy `memory_entries` | No — pre-canonical | No | v3 era, not v5 | No |

### 5.1 The specialized reference specimen

`personal_fact_revisions` is the architectural precedent for how this codebase records a review
transition. Its columns are `actor`, `action`, `field_changed`, `old_value`, `new_value`,
`reason`, `created_at` — a **generic typed field-transition revision**. A Personal Fact review
transition is recorded as `field_changed='status'`, `old_value`, `new_value`.

That is exactly the shape an ordinary `review_state` transition would need, and ordinary memory
has no equivalent. The asymmetry is deliberate and documented: Personal Facts are specialized
(§3.4) and every Personal Fact transition passes through the Personal Facts service together with
its revision changes. Ordinary memory has no such family, because no ordinary review writer has
ever been implemented.

---

## 6. Reconstructability

Test case — an ordinary memory with this review history:

```text
pending → approved → disputed → approved → rejected
```

Current canonical storage was asked to reconstruct, per transition, without parsing non-authority
free-form metadata, guessing from timestamps, treating current state as historical state, or
reading logs not governed as canonical account state.

| Fact to reconstruct | Reconstructable today? | Reason |
| --- | --- | --- |
| Old state of each transition | **No** | No typed old-state storage for `review_state` anywhere |
| New state of each transition | **No** (final value only) | Only `review_state = rejected` survives, as present state |
| Transition sequence | **No** | No ordered history; `reviewed_at` is a single first-approval timestamp |
| Transition time | **No** | `reviewed_at` = first approval only; `updated_at` = last write, not per-transition |
| Intent / action identity | **No** | No review writer exists, so no review receipt has ever been written |

```text
RECONSTRUCTABLE: 0 of 5
```

Two independent failures are visible here, and they should not be conflated:

1. **Even a receipt alone would not reconstruct the sequence.** A receipt is a row per mutation,
   but §3.3 requires a **revision** in addition, and the contract assigns receipts an audit/evidence
   role, not canonical state authority. Recording `review_state` transitions in
   `memory_provenance.extensions` would violate the explicit non-authority rule and is forbidden.
2. **Nothing exists today because no writer exists.** Approve, reject, and dispute have no
   production method and no route; `review_state` is written in exactly one place, the C6 creation
   service, which sets `review_state="approved"` at creation. So the absence of review history is
   currently untested by any runtime path — the gap is architectural, not an observed data defect.

---

## 7. C9 interaction

Does C9's content revision persistence satisfy review history?

**No.** On current semantic meaning, not on table naming:

- `memory_revisions` stores typed `old_text_content` / `new_text_content`. A review transition has
  no authored-text dimension; writing a review state into those columns would corrupt the
  content chain the table exists to preserve and would break C9's own restore reconciliation,
  which asserts the final revision's `new_text_content` equals `memory_records.text_content`.
- The table carries a DB-level `CHECK (old_text_content <> new_text_content)` and a
  `UNIQUE (memory_id, revision_number)` chain whose meaning is authored-text continuity. A
  review-transition sequence has neither property.
- §4.16.5 defines its meaning as content history, and the C9 proof records the species boundary
  as a deliberate semantic limit.

`memory_revisions` therefore does not count as a review-transition revision family, exactly as
the spec requires. Naming is not meaning.

---

## 8. Transition graph

```text
TRANSITION_GRAPH: NOT EXPLICIT
```

Evidence:

- A repository search for state machine, transition matrix, legal transition, and "may only"
  rules in the Unified Memory Store contract returns **no matches**.
- §3.3 fixes the vocabulary (`pending`, `approved`, `rejected`, `disputed`) and the authority
  owner, but no legal-transition rules.
- §5.3 "Edit and reapproval behavior" enumerates content edits, dictation, agent proposals,
  importer suggestions, Project scope, Persona association, agent-proposed retire/restore, and
  decay — it has **no row** for user approve, reject, or dispute.
- The Memory Vault contract §5.1 names the three review actions as admitted actions but states no
  preconditions or legal source→target pairs.

Accordingly this slice does **not** assert rules such as "rejected may only return to pending" or
"disputed may only become approved". Those rules are not currently accepted architecture.

Two related couplings are also **not explicit**:

- Approval → activation. §4.16.2a establishes review-*before*-activation ordering, but no current
  contract states that approving must activate.
- Reject/dispute → retirement. No current contract couples a review outcome to lifecycle. §5.4
  does state one real rule in the other direction: restore "does not auto-approve a formerly
  unapproved record."

**This is a C10A writer blocker, and C10A-P does not clear it.** A review-transition *revision
table* can record whatever transitions occur without knowing which are legal. Legality is a
writer concern. The C10A writer must not invent the graph, and the successor authorized here does
not resolve it.

---

## 9. Why this is not a contract contradiction, and what is still open

`REVIEW_HISTORY_CONTRACT_CONTRADICTION` was considered and rejected.

The contradiction rule targets the case where implementing *either* posture would require
choosing new architecture. That is not the situation here. §3.3 states the revision requirement
for authority-changing transitions explicitly, three times across two independent framings
(§3.3 rule, §4.8 content form, §5.3 revisioned-action precedent). The substantive answer is the
same no matter how §5.1's table cell is read: a review transition needs a typed revision, and none
exists. §5.1's divergence therefore does not change the classification.

It is recorded as an **open documentation inconsistency** instead, and this slice deliberately does
not repair it:

- Rewriting §5.1's cells to add "+ revision" would be this slice *choosing* to settle a
  normative question between two current documents. That is contract resolution, which belongs to
  a successor, not to a revalidation.
- Removing the divergence in the other direction would silently convert "revision + receipt" into
  "receipt only", which the spec explicitly forbids.

What this slice does instead is make the *unambiguous* half explicit: C9's content-revision family
is content-only and does not discharge §3.3 for non-content authority transitions. That is a
permitted clarification and requires no architectural choice.

---

## 10. Successor

Persistence is required, so the terminal history classification authorizes the persistence
prerequisite. The transition-graph gap is recorded as a blocker on the later writer slice, which
is already frozen; it does not create a competing successor.

```text
UMS-05C10A-P ORDINARY MEMORY REVIEW-TRANSITION REVISION PERSISTENCE
                + UMS-04 PORTABILITY: AUTHORIZED
```

Smallest sufficient prerequisite, per the spec's new-persistence rule:

- a typed canonical review-transition revision family for ordinary memory, semantically distinct
  from `memory_revisions` (content) and from `personal_fact_revisions` (Personal Facts), carrying
  old and new review state, transition sequence, actor, and timestamp;
- UMS-04 portability, which today would mean a **seventh** canonical family in a new
  `account-export.v6` — v5's six families are `persona_subjects`, `persona_subject_bindings`,
  `memory_records`, `memory_persona_links`, `memory_provenance`, `memory_revisions`;
- C10A-P must not invent a transition graph, and must not design the writer.

The C10A writer remains frozen, now with two explicit prerequisites: C10A-P persistence, and a
separately-authorized resolution of the transition graph. C10A-P was not begun.

---

## 11. Invariants check

```text
"revision" silently reinterpreted:            NO
content revision authority widened:            NO
review state stored in old/new_text_content:   NO
review history encoded into provenance
  extensions:                                  NO
receipts treated as canonical state authority: NO
review_state remains sole present authority:   YES
review and lifecycle kept independent:         YES
approval coupling to activation invented:      NO
reject/dispute coupling to retire invented:    NO
Personal Facts kept specialized:              YES
implementation performed:                      NONE
schema change:                                 NONE
migration change:                              NONE
export/restore change:                         NONE
test change:                                   NONE
frontend change:                               NONE
release claim expansion:                       NONE
```

---

## 12. Runtime boundary

```text
REVIEW WRITER (approve/reject/dispute):   NOT IMPLEMENTED
LIFECYCLE WRITER (retire/restore):        NOT IMPLEMENTED
PERSONAL FACT MUTATION:                   UNCHANGED, SPECIALIZED
REVISION-HISTORY READ API:                NOT IMPLEMENTED
FRONTEND / UI:                            NONE
RETRIEVAL CHANGE:                         NONE
SCHEMA CHANGE:                            NONE
EXPORT SCHEMA CHANGE:                     NONE
RELEASE CLAIM CHANGE:                     NONE
```

---

## 13. Closeout

```text
UMS05C10AR_REVIEW_HISTORY_PERSISTENCE_REQUIRED
```

Campaign transition:

```text
UMS-05C9-W ORDINARY MEMORY CONTENT CORRECTION WRITER: CLOSED
UMS-05C10: OPEN
UMS-05C10A-R REVIEW-TRANSITION HISTORY REVALIDATION: CLOSED
UMS-05C10A ORDINARY MEMORY REVIEW TRANSITION WRITER:   FROZEN
UMS-05C10A-P REVIEW-TRANSITION REVISION PERSISTENCE
              + UMS-04 PORTABILITY:                    AUTHORIZED
UMS-05C10B ORDINARY MEMORY LIFECYCLE WRITER:          NOT AUTHORIZED
UMS-05C11+: NOT AUTHORIZED
UMS-05D+:  NOT AUTHORIZED
UMS-06+:   NOT AUTHORIZED
```

`UMS-05C10A-P` is the sole successor. It was not begun.
