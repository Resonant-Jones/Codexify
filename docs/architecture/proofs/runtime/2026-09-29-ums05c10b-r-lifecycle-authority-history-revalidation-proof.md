# UMS-05C10B-R — Revalidate Ordinary-Memory Lifecycle Mutation Authority and History

**Status:** CLOSED
**Slice:** `UMS-05C10B-R` — lifecycle authority / persistence / state-machine revalidation
**Campaign:** Unified Account-Owned Memory Store
**Date:** 2026-09-29
**ADR impact:** **Aligned with existing ADR(s)** — ADR-084 and ADR-088. No new ADR. No contract contradiction.
**Class:** Documentation / architecture qualification. No runtime, schema, route, or test change.

---

## 1. Terminal classifications

```text
LIFECYCLE_HISTORY_NEW_CANONICAL_PERSISTENCE_REQUIRED
LIFECYCLE_TRANSITION_GRAPH: PARTIAL
```

ADR impact:

```text
No ADR impact
```

---

## 2. Lineage

| Field | Value |
|---|---|
| Branch | `feature/ums-continued` |
| Starting HEAD | `39dbd7a4fe03da8deb0b95b2c6bd6a5b1ddc7d03` |
| C10A-W | `39dbd7a4fe03da8deb0b95b2c6bd6a5b1ddc7d03` (HEAD) |
| C10A-C | `aa906f0051130a97f70c75bb2c8efefa31c12170` (ancestor) |
| C10A-P | `a38c6ad81609cb967fa7e04a0ae072efab5c69e6` (ancestor) |
| C10A-R | `a49dff0044150eb142f4324b3bfa8684181d3248` (ancestor) |
| C9-W | `2c21cd0e0a6cfc242643d1ca029ed8e1d1b40888` (ancestor) |
| Alembic head | `a7c3e91d4b60` (single head) |
| Opening index | empty |
| Push count | `0` |

No post-C10A-W authority-changing work exists. Nothing required classification.

---

## 3. Canonical lifecycle vocabulary and present authority

Vocabulary is confirmed from current contract: `active`, `dormant`, `retired`. There is no
separate ordinary-memory `archived` lifecycle; `retired` is the single reversible soft-removal
state.

`memory_records.lifecycle_state` is the sole present ordinary-memory lifecycle authority
(§3.3), enforced by the frozen DB CHECK `memory_records_lifecycle_state_check` introduced by
C8.

`lifecycle_state` is **never mutated** by any current canonical code path. Repository-wide
inspection finds it only as: a read in the account-export row source, the C8 migration, and
unrelated concepts (ThreadSpace membership states, a chat-task `orphaned` status). No canonical
retire, restore, activation, or decay writer exists.

---

## 4. Governing contract (current, branch-truth)

| Topic | Current governing meaning | Source |
| --- | --- | --- |
| Lifecycle authority | `lifecycle_state` is the sole lifecycle authority | §3.3 |
| Authority-changing transitions | "every authority-changing transition produces a revision and intent receipt" — current, unamended, and it names lifecycle authority in the same list | §3.3 |
| Retirement | "Retire is reversible and removes ordinary ambient eligibility" | §5.4 |
| Restoration | "Restore returns a retired record to its **pre-retirement governed posture** only through an explicit account-principal action; it does not auto-approve a formerly unapproved record" | §5.4 |
| Lifecycle timestamps | "Lifecycle transition timestamps such as `dormant_at` and `retired_at` remain canonical because the transition itself is canonical" | §4.4 |
| Decay | "System decay transitions active to dormant \| audited policy transition; forbidden while held" | §5.3 |
| Agent proposals | "Agent proposes retire/restore \| proposal only; action requires explicit user intent" | §5.3 |
| Decay behavior | Heat *recommends* `active -> dormant`; a held record cannot be transitioned by decay; a pinned record can decay when not held; vector indexes, summaries and heat projections are rebuildable | §11 |
| Hold | "Hold/release controls whether decay may change lifecycle" | §5.4 |
| Recall | "Explicit recall does not approve, activate, restore, edit, pin, hold, or change context posture" | §6 |
| Export | The account archive must include "lifecycle transition timestamps" | §10 |
| Review independence | Approval does not activate; rejection/dispute do not retire; retire/restore do not change review authority | §3.3.1, ADR-088 |

**The revision requirement has not been narrowed for lifecycle.** No accepted document says
lifecycle transitions are receipt-only. The existence of the content and review revision families
does not narrow "revision" for a third authority dimension.

---

## 5. Persistence inventory

`memory_records` has exactly seventeen columns: `memory_id`, `user_id`, `project_id`,
`semantic_species`, `text_content`, `fact_key`, `fact_value`, `fact_confidence`, `reviewed_at`,
`activated_at`, `pinned`, `held`, `review_state`, `lifecycle_state`, `extensions`, `created_at`,
`updated_at`.

| Surface | Current lifecycle authority | Historical authority | Portable | Restore-posture capable |
| --- | --- | --- | --- | --- |
| `memory_records.lifecycle_state` | **Yes** — sole authority | No (present only) | Yes (v6 family 3) | No |
| `memory_records.activated_at` | No — ingress/activation metadata | No | Yes | No |
| `memory_records.reviewed_at` | No — review dimension | No | Yes | No |
| `memory_records.updated_at` | No — CAS token | No — last write, not per-transition | Yes | No |
| `memory_records.held` | No — decay control | No | Yes | No |
| `memory_records.pinned` | No — ranking priority | No | Yes | No |
| `memory_records.extensions` | No | No — non-authority free-form | Yes | No |
| `memory_revisions` | No | **Content history only** (§4.16.5) | Yes (v6 family 6) | No — semantically inapplicable |
| `memory_review_revisions` | No | **Review-transition history only** (§4.16.5b) | Yes (v6 family 7) | No — semantically inapplicable |
| `memory_provenance` | No | No — intent/audit evidence | Yes (v6 family 5) | No |
| `memory_provenance.extensions` | No | No — explicitly non-authority | Yes | No |
| `dormant_at` | **Column does not exist** | — | — | — |
| `retired_at` | **Column does not exist** | — | — | — |
| pre-retirement posture field | **Does not exist** | — | — | — |
| `context_posture` | **Column does not exist** | — | — | — |
| lifecycle revision family | **Does not exist** | — | — | — |
| `personal_fact_revisions` | No — Personal Facts only | PF field history | Not ordinary | No |
| MemoryOS heat / mid-term state | No | No | No | No — legacy, non-canonical |
| Federation trust decay | No | No | No | No — unrelated |
| `AuditLog` / `GuardianEventLog` | No | No | No | No — not account canonical memory state |

**Two contract requirements are not met by storage:**

1. §4.4 declares `dormant_at` and `retired_at` **canonical**. Neither column exists. (Dormancy is
   derivable *present-state* from `activated_at IS NULL` via the C8 backfill
   `CASE WHEN activated_at IS NULL THEN 'dormant' ELSE 'active' END`, but that is a present-state
   derivation, not a transition timestamp.)
2. §10 requires "lifecycle transition timestamps" in the account archive. The v6
   `memory_records` required-field set contains `reviewed_at` and `activated_at` and **no**
   lifecycle transition timestamp.

This is a contract-versus-implementation gap, **not** a contradiction between documents: no two
current authoritative documents disagree with each other. The contract is internally consistent
and simply ahead of the implementation. That is why the classification is
`NEW_CANONICAL_PERSISTENCE_REQUIRED` rather than `CONTRACT_CONTRADICTION`.

---

## 6. Reconstructability

Sample sequence:

```text
active → dormant → active → retired → restored-to-? → retired
```

| Fact | Reconstructable today? | Reason |
| --- | --- | --- |
| Old lifecycle state per transition | **No** | no lifecycle history family |
| New lifecycle state per transition | **No** (final value only) | present `lifecycle_state` only |
| Transition sequence | **No** | no ordered lifecycle history |
| Transition timestamp | **No** | no `dormant_at` / `retired_at` |
| Actor / authority class | **No** | no lifecycle revision row |
| User-directed vs governed decay | **No** | no actor class persisted |
| **Pre-retirement governed posture for restore** | **No** | not stored anywhere |

```text
RECONSTRUCTABLE: 0 of 7
```

Dormancy is the one partial exception, and only for *present state*: `activated_at IS NULL` means
dormant. That is insufficient for history, because a memory that went `active → dormant → active`
and one that was ingested dormant are indistinguishable.

---

## 7. Restore-posture analysis (load-bearing)

The contract requires restore to return the **pre-retirement governed posture**. Nothing stores
that posture. Each case:

### Case A — `active → retired → restore`

Prior posture was `active`, but no field records it. After retirement the only lifecycle value is
`retired`. A restore implementation would have to *assume* the prior posture was `active`.

### Case B — `dormant → retired → restore`

Prior posture was `dormant`. After retirement it is indistinguishable from Case A. A restore
implementation would have to assume `active` and would be **wrong** for this record.

**Cases A and B are indistinguishable in current storage.** This is the decisive finding: the
contract's restore rule is unimplementable without either inventing a persistence field or
choosing a target the contract does not state.

### Case C — `rejected + active → retired → restore`

Review state is independent (§3.3, ADR-088), and §5.4 explicitly says restore "does not
auto-approve a formerly unapproved record". So `rejected` must be preserved. That part **is**
answerable from present state: `review_state` is untouched by lifecycle.

### Case D — `pending + dormant → retired → restore`

Same as Case C: `pending` must be preserved. `review_state` is present-state authority and is
answerable.

### Case E — retired record with no reconstructable pre-retirement history

Current contract requires a "pre-retirement governed posture" that does not exist in storage.
The contract is therefore **incomplete for this case**: it states an obligation it cannot be
satisfied from, and it does not specify a fallback target (for example, always `active`, or a
user-supplied target). This slice does not choose one.

**Findings:** "restore always targets active" is **not** stated; "restore returns the prior state"
**is** stated but is not representable; a user-supplied restore target is **not** stated. Contract
incomplete for Case E.

---

## 8. Dormancy authority

| Route to `dormant` | Authority class | Implemented? |
| --- | --- | --- |
| Import / ingestion | **Initialization / ingress state** — OpenAI/Anthropic import creates "dormant, `explicit_recall_only` record" (§5.1, §9) | Canonical column defaults to `dormant`; C6 direct creation sets `active` |
| System decay `active → dormant` | **Governed automatic policy** — heat *recommends*; an audited policy transition, forbidden while held (§5.3, §11) | **No.** No canonical decay code exists; MemoryOS decay is legacy and non-canonical |
| `dormant → active` (reactivation) | **Unresolved** | No |
| User activation | **Absent.** No activation action exists in the Vault contract, and ADR-088 explicitly states approval does not activate | No |

Hold/decay: a held record **cannot** be transitioned by decay; a pinned record **can** decay when
not held (§11). Pin is ranking priority, not lifecycle authority.

Import-time dormancy is distinguished from user mutation: it is ingress posture set at
creation, not a transition performed by an operator.

**Decay is a recommendation surface, not a canonical writer.** §11 states heat can *recommend*
`active -> dormant` and that projections are rebuildable. No current code writes
`memory_records.lifecycle_state`. Whether a future governed decay should append to the same
canonical lifecycle history family as human retire/restore is **unresolved** and is recorded as a
later prerequisite, not decided here.

---

## 9. Transition graph

```text
LIFECYCLE_TRANSITION_GRAPH: PARTIAL
```

| Edge | Status | Authority class | Evidence |
| --- | --- | --- | --- |
| ingress → `dormant` | **Explicit** | initialization | import posture; column default `dormant` |
| `active → dormant` | **Explicit** | governed automatic policy | §5.3, §11 |
| `dormant → active` | **Not explicit** | — | no activation action exists anywhere |
| `active → retired` | **Partial** | explicit user | retire exists; source-state legality not enumerated |
| `dormant → retired` | **Not explicit** | — | no statement |
| `retired → active` | **Not explicit** | — | §5.4 implies "prior posture", not a fixed target |
| `retired → dormant` | **Not explicit** | — | same |
| `retired → prior posture` | **Partial** — intent stated, target set unenumerated and not representable | explicit user | §5.4 |
| same-state `retire` | **Not explicit** | — | no rule (the review same-state no-op rule does not cover lifecycle) |
| same-state `restore` | **Not explicit** | — | same |

**Missing edges/authority classes, stated exactly:**

1. Whether `retire` is legal from `active`, from `dormant`, or both.
2. Same-state `retire` and same-state `restore` semantics.
3. The complete legal target set for `restore`.
4. Whether `dormant → active` reactivation exists at all, and under whose authority.
5. Whether governed automatic decay appends to the same canonical lifecycle history family as
   human retire/restore.

No missing edge was invented.

---

## 10. Retire action inventory

| Question | Finding | Evidence |
| --- | --- | --- |
| valid from `active`? | **Partial** — retire exists, source legality unenumerated | Vault contract §5.1 Retire row |
| valid from `dormant`? | **Not explicit** | no statement |
| `retire` on `retired` is a no-op? | **Not explicit** | no rule |
| remembers pre-retirement posture? | **Required by §5.4, NOT IMPLEMENTED** | no field exists |
| changes review state? | **NO** | §3.3 / ADR-088 independence; review actions do not retire and retire does not change review |
| changes context posture? | **Unresolved** | no `context_posture` column exists at all |
| changes pin/hold? | **Unresolved** | no statement; hold is a decay control, pin is ranking |

**§5.1 divergence (carried forward, not repaired).** The Memory Vault contract §5.1 Retire and
Restore rows still list only a "durable mutation receipt" with no revision, diverging from the
normative §3.3 rule — the same divergence C10A-C resolved for review. It is **deliberately not
repaired here**, because no lifecycle revision family exists; editing the table now would promise
persistence that has not been built. It is recorded as an open documentation inconsistency for
the successor.

---

## 11. Restore action inventory

| Question | Finding |
| --- | --- |
| source must be `retired` | **Not explicit** (implied by "a retired record", §5.4) |
| target is `active` | **Not stated** |
| target is `dormant` | **Not stated** |
| target is prior posture | **Stated** (§5.4) but not representable in storage |
| restore on non-retired | **Unresolved** — no-op vs invalid not stated |
| requires explicit account-principal action | **Explicit** (§5.4) |
| preserves review state | **Explicit** — "does not auto-approve a formerly unapproved record" |
| preserves pin/hold/context posture | **Unresolved** |
| can override hold | **Unresolved** |
| interacts with decay clocks/timestamps | **Unresolved**, and unresolvable while no lifecycle timestamps exist |

---

## 12. Automatic decay boundary

`active → dormant` is **not currently implemented** for canonical memory. There is no code that
writes `memory_records.lifecycle_state`, and no canonical decay audit trail exists. MemoryOS
`mid_term` heat decay and the federation trust engine are unrelated legacy/subsystem logic and
carry no canonical authority. The frozen C8 migration deliberately refused to create the
governance column if any pre-existing row was `rejected`, `disputed`, or `retired`, so it never
manufactured a retired row.

Per current contract, decay is an *audited policy transition* forbidden while held, and heat only
*recommends* it (§5.3, §11). Whether a future governed decay transition must append to the same
canonical lifecycle history family as human retire/restore is unresolved and is recorded as a
later prerequisite.

---

## 13. Portability

| Required authority | Portable in `account-export.v6`? |
| --- | --- |
| present lifecycle state | **Yes** — `memory_records.lifecycle_state` |
| pre-retirement posture | **No** — not persisted, not exported |
| ordered lifecycle history | **No** — no family exists |
| automatic decay history (if canonical) | **No** — nothing exists to export |
| user retire/restore history | **No** — nothing exists to export |

The v6 `memory_records` required-field set contains `reviewed_at` and `activated_at` and no
lifecycle transition timestamp, so §10's "lifecycle transition timestamps" export requirement is
unmet. **Required lifecycle authority is not portable, so history persistence is not sufficient.**

---

## 14. Terminal classification

```text
LIFECYCLE_HISTORY_NEW_CANONICAL_PERSISTENCE_REQUIRED
```

All six conditions of the new-persistence rule hold:

1. lifecycle transitions are authority-changing — **yes**, §3.3 names `lifecycle_state` as
   authority and requires a revision plus intent receipt for every authority-changing transition;
2. the contract still requires revision + receipt for lifecycle — **yes**, unamended, with no
   accepted narrowing to receipt-only;
3. no existing canonical family represents lifecycle transitions — **yes**, no such family
   exists;
4. content and review revisions are semantically inapplicable — **yes**, both are typed to their
   own authority dimension;
5. provenance remains non-authority — **yes**;
6. restore semantics require historical knowledge current state cannot preserve — **yes**, Cases A
   and B are indistinguishable in storage.

Neither sufficiency path holds. Path 1 fails because no lifecycle history relation exists. Path 2
fails because no accepted document states that `lifecycle_state` plus supporting fields plus a
receipt is the complete lifecycle record; §4.4 in fact says the opposite.

Contradiction was considered and rejected: no two current authoritative documents disagree. The
gap is contract-ahead-of-implementation, which is exactly what a persistence prerequisite
resolves.

---

## 15. Invariants closeout

```text
current lifecycle authority remains memory_records.lifecycle_state: YES
review/lifecycle independence preserved:                                 YES
content revision authority widened:                                     NO
review revision authority widened:                                      NO
provenance extensions used as lifecycle authority:                       NO
Personal Fact lifecycle authority changed:                               NO
retire writer implemented:                                              NO
restore writer implemented:                                             NO
decay implementation changed:                                           NO
lifecycle transition rule invented:                                     NO
lifecycle revision schema invented:                                     NO
schema changed:                                                         NO
export/restore changed:                                                 NO
frontend changed:                                                       NO
retrieval changed:                                                      NO
release claim expanded:                                                 NO
```

---

## 16. Runtime boundary

```text
retire writer:            NOT IMPLEMENTED
restore writer:           NOT IMPLEMENTED
activate / reactivate:    NOT IMPLEMENTED
automatic decay:          NOT IMPLEMENTED
lifecycle history family: NOT IMPLEMENTED
review writer:            IMPLEMENTED INTERNAL-ONLY (unchanged, separate)
Personal Fact lifecycle:  UNCHANGED
```

---

## 17. Closeout

```text
UMS05C10BR_LIFECYCLE_HISTORY_PERSISTENCE_REQUIRED
```

Campaign transition:

```text
UMS-05C10A ORDINARY MEMORY REVIEW TRANSITION WRITER: CLOSED
UMS-05C10A: CLOSED
UMS-05C10B-R LIFECYCLE AUTHORITY / HISTORY REVALIDATION: CLOSED
UMS-05C10B-P ORDINARY MEMORY LIFECYCLE-TRANSITION REVISION PERSISTENCE
              + UMS-04 PORTABILITY: AUTHORIZED
UMS-05C10B WRITER: FROZEN
UMS-05C10B-C LIFECYCLE TRANSITION CONTRACT RESOLUTION: NOT AUTHORIZED (later prerequisite)
UMS-05C11+: NOT AUTHORIZED
UMS-05D+:  NOT AUTHORIZED
UMS-06+:   NOT AUTHORIZED
```

`UMS-05C10B-P` is the sole authorized successor and was not begun. It must resolve the
missing lifecycle history family and its UMS-04 portability, and must record the §5.1
documentation divergence. The partial transition graph is recorded as a later prerequisite
(UMS-05C10B-C), **not** as a second authorized successor, and the C10B writer stays frozen.

Gitleaks was skipped narrowly: the sandbox cannot bootstrap the Go toolchain. Every other
executable pre-commit hook ran. `gitleaks` is required at branch integration.
