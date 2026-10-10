# UMS-05C10B-C — Freeze Ordinary-Memory Lifecycle Transition Semantics

**Status:** CLOSED
**Slice:** `UMS-05C10B-C` — lifecycle state-machine / authority contract resolution
**Campaign:** Unified Account-Owned Memory Store
**Date:** 2026-09-29
**ADR impact:** **Requires new ADR — created:** `docs/architecture/adr/089-ordinary-memory-lifecycle-transition-semantics.md` (ADR-089, Accepted). Aligned with ADR-084; does not modify or supersede ADR-084 or ADR-088.
**Class:** Documentation / architecture contract slice. No runtime, schema, migration, or test change.

---

## 1. Lineage

| Field | Value |
|---|---|
| Branch | `feature/ums-continued` |
| Starting HEAD | `3b4516894723848a04d1c26a330716b78762e2e6` |
| C10B-P commit | `3b4516894723848a04d1c26a330716b78762e2e6` (HEAD) |
| C10B-R | `768321114a720b3c289d8b9d30cabba9703e7651` (ancestor) |
| C10A-W | `39dbd7a4fe03da8deb0b95b2c6bd6a5b1ddc7d03` (ancestor) |
| C10A-C (review ADR) | `aa906f0051130a97f70c75bb2c8efefa31c12170` (ancestor) |
| Alembic head | `b8e2f4a6c901` (single head, **unchanged**) |
| Opening index | empty |
| Untracked posture | only preserved `.precommit_cache/` / `.precommit_home/` entries |
| Push count | `0` |

Opening truth matched the expected values exactly; no drift classification was
required, and the branch was not reset to any expected SHA.

### 1.1 ADR number determination

Determined from the **branch-local** canonical index
`docs/architecture/adr/adr-index.md` plus actual filenames, not from `main`,
another branch, or memory. Highest existing was `088`
(`088-ordinary-memory-review-transition-semantics.md`), so the new ADR is
**089**.

`docs/architecture/README.md` was checked: it lists neither ADR-087 nor
ADR-088, so the branch convention does **not** require a per-ADR entry there.
It was therefore not edited.

---

## 2. Persistence prerequisite (verified read-only)

| Item | Status |
|---|---|
| `memory_lifecycle_revisions` model | present (`guardian/db/models.py`) |
| `memory_lifecycle_revisions` migration `b8e2f4a6c901` | present |
| `memory_lifecycle_revisions` row source | present (`guardian/core/pgdb.py`) |
| `account-export.v7` | present (`guardian/services/account_export.py`) |
| v7 restore preflight + executor | present (`guardian/services/account_restore.py`) |
| `active -> retired` distinguishable | proven by C10B-P at DB, export, and restore layers |
| `dormant -> retired` distinguishable | proven by C10B-P at all three layers |
| ordinary retire/restore writer | **does not exist** |
| `def retire` / `def restore` / `def transition_lifecycle` in vault mutation or routes | none found |

No lifecycle writer exists, exactly as C10B-P left it.

---

## 3. State meanings frozen

```text
active
    lifecycle-eligible to participate in normal memory behavior, subject to
    all independent review, context-posture, scope, subtype and exclusion
    gates. Does not imply approved, ambient eligible, pinned, held, or
    in-scope for every request.

dormant
    canonically stored and recallable under explicit authorized widening,
    but excluded from ordinary ambient participation by lifecycle.
    Non-destructive, not rejected, not retired, not purge, not a synonym
    for `archived`.

retired
    canonically stored but reversibly soft-removed from normal lifecycle
    participation. Reversible, ambient-ineligible, distinct from dormant,
    not purge, and the sole ordinary-memory soft-removal state.
```

There is no separate canonical `archived` lifecycle state.

---

## 4. Direct action graph

The Memory Vault lifecycle writer exposes **exactly two** generic direct
actions. No generic `activate`, `reactivate`, `set_active`, `set_dormant`,
`set_lifecycle_state`, or `archive`.

| Current lifecycle | `retire` | `restore` |
| --- | --- | --- |
| `active` | -> `retired` | no-op |
| `dormant` | -> `retired` | no-op |
| `retired` | no-op | -> pre-retirement governed posture |

### 4.1 Retire

- `active -> retired` — legal under explicit account-principal authority,
  recording `old_lifecycle_state = active`.
- `dormant -> retired` — legal under explicit account-principal authority,
  recording `old_lifecycle_state = dormant`.
- `retired + retire` — idempotent semantic no-op after successful CAS. No
  lifecycle revision, no receipt, no CAS advance. `retired -> retired` history
  is never invented.

### 4.2 Restore

Restore is **not** "set active." It means: undo the current retirement and
return the record to the governed posture that immediately preceded it.

```text
active   -> retired -> restore -> active
dormant  -> retired -> restore -> dormant
```

The two remain distinct. Restore never normalizes every record to `active`, and
never normalizes every record to `dormant`.

**History gate.** A currently retired record is restorable only when canonical
history reconciles as `latest.new_lifecycle_state == retired` with
`latest.old_lifecycle_state ∈ {active, dormant}`. Zero history, gapped
history, divergent tail, a latest transition not ending in `retired`, or an
invalid old token must **fail closed**. Posture is never inferred from
provenance extensions, timestamps, heat/ranking state, imported-source
metadata, review state, hold/pin state, or logs.

**Repeated restore.** A direct `restore` against a current `active` or `dormant`
record is already satisfied: a semantic no-op after successful CAS. This gives
retry-safe actions without creating a generic activation authority.

### 4.3 CAS

`memory_records.updated_at` is validated **before** any no-op determination.
Stale CAS plus retire on `retired`, or plus restore on `active`/`dormant`, is a
**conflict**, not a successful no-op. Fresh-CAS no-ops do not advance CAS.

---

## 5. Independence

```text
retire changes review_state:  NO
restore changes review_state: NO
retire changes hold:          NO
restore changes hold:         NO
retire changes pin:           NO
restore changes pin:          NO
```

Neither action approves, rejects, disputes, or resets to pending. Hold governs
automatic decay only and never blocks an explicit user action; restore never
clears hold. Pin stays ranking metadata and is not activation.

Context posture: `memory_records` currently has **no** context-posture column.
That fact is recorded rather than repaired, because no schema change is
authorized in this slice.

---

## 6. Decay boundary

```text
governed automatic decay active -> dormant:   CONTRACTED
automatic decay while held:                  FORBIDDEN
automatic decay implemented by C10B-W:       NO
automatic dormant -> active:                 NOT ESTABLISHED
```

Automatic decay is a separate authority from direct retire/restore. It is still
an authority-changing transition and must use canonical
`memory_lifecycle_revisions` plus the appropriate auditable policy/evidence
receipt, applied atomically. Its receipt action identity is distinct and must
never masquerade as an authenticated user `retire` or `restore`.

Automatic `dormant -> active` is deliberately not established. Derived ranking
activity must never silently become canonical lifecycle mutation.

---

## 7. Activation boundary

```text
generic direct activate in C10B-W:  NO
generic direct set_lifecycle_state:  NO
```

Direct promotion or activation of a dormant memory, if a later import or
promotion workflow needs it, requires its own governed contract or an
already-accepted owning workflow. It must not be smuggled in through
retire/restore.

---

## 8. Ingress and recall

Dormant ingress: creation as `dormant` under an accepted import/ingress
contract is **initialization**, not `active -> dormant`, and fabricates no
revision. Direct creation as `active` likewise fabricates no transition. The
C10B-P zero-synthetic-history doctrine is unchanged.

Explicit recall: reading a dormant or retired record does not mutate
lifecycle. Recall may widen request-scoped access under recall-grant authority
and never activates, restores, retires, or changes review or context posture.
Reading is not mutation.

---

## 9. History and receipt requirement

Every changed direct retire or restore produces exactly one
`memory_lifecycle_revisions` row plus exactly one canonical Vault mutation
receipt. The revision is canonical historical authority; the receipt is
intent/source/audit evidence. Neither replaces the other.

No parallel `pre_retirement_state` field is required: history itself preserves
the posture through `old_lifecycle_state`. Direct receipt action tokens are
`retire` and `restore`.

---

## 10. Personal Facts boundary

Nothing in ADR-089 gives the ordinary lifecycle writer authority over Personal
Facts. Personal Facts retain `personal_facts.status`,
`personal_facts.is_active`, `personal_fact_revisions`, and Personal Facts
service authority. The future ordinary writer must fail or delegate at that
boundary and must never generic-write Personal Fact activation, retirement, or
restore state.

---

## 11. Memory Vault contract reconciliation

C10B-P deliberately left the Memory Vault C10B gate stale because transition
policy was not yet frozen. C10B-C owns that reconciliation and performed it:

- the §5.1 **Retire** row now states the canonical `lifecycle_state` transition
  plus one `memory_lifecycle_revisions` row, with receipt **+ canonical
  lifecycle revision**;
- the §5.1 **Restore** row now states the transition back to the recovered
  pre-retirement `active`/`dormant` posture, plus one
  `memory_lifecycle_revisions` row;
- §5.1.2 is rewritten from "lifecycle gate" to contracted semantics, recording
  both closed prerequisites, the full contracted behavior table, and the
  fail-closed missing-history posture;
- the stale wording that described C10B-P persistence as "missing" is removed.

This resolves the `§5.1` versus `§3.3` receipt-only divergence that
UMS-05C10B-R recorded, in the same direction UMS-05C10A-C resolved it for
review rows. No runtime route is claimed.

The UMS contract was likewise reconciled: new **§3.3.2** makes the lifecycle
state machine normative, and the former "graph unresolved" record is
reorganized as **§4.16.5d**, which now states that both C10B-R findings are
closed by different slices. The §4.4 / §10 `dormant_at` / `retired_at` wording is
acknowledged as still ahead of storage, with their content preserved instead
by `old_lifecycle_state` and per-row `created_at`. No column is invented.

---

## 12. Parked follow-up

C10B-P identified a latent conflict-shaping issue in the C10A review restore
preflight: a wholly new stable review-revision ID occupying an already-used
`(memory_id, revision_number)` slot may reach the database unique constraint
instead of producing the intended clean semantic conflict.

```text
PARKED
NON-BLOCKING
NOT MODIFIED BY C10B-C
```

Database integrity is protected and no data is corrupted; the effect is error
shaping, not a correctness failure. Fixing it changes C10A review restore
behavior and is outside the C10B lifecycle dependency chain. It is **not** a
C10B-C prerequisite and **not** a second successor. Account restore code was
not edited in this slice.

---

## 13. Runtime boundary

```text
lifecycle persistence:              IMPLEMENTED
lifecycle portability v7:           IMPLEMENTED

retire writer:                      NOT IMPLEMENTED
restore writer:                     NOT IMPLEMENTED
direct activation writer:           NOT IMPLEMENTED
automatic decay writer:             NOT IMPLEMENTED BY THIS SLICE
frontend:                           NONE
retrieval:                          NONE
schema change:                      NONE
migration change:                   NONE
export/restore change:              NONE
release claim change:               NONE
```

---

## 14. Invariants closeout

```text
lifecycle transition graph explicit:               YES
retire active->retired:                            YES
retire dormant->retired:                           YES
retire retired->retired revision created:          NO
restore returns pre-retirement posture:            YES
restore collapses dormant to active:               NO
missing restore history guessed:                   NO
stale no-op bypasses CAS:                          NO
retire changes review authority:                   NO
restore changes review authority:                  NO
hold blocks automatic decay:                       YES
hold blocks explicit retire/restore:               NO
generic direct activation added:                  NO
automatic dormant->active invented:                NO
lifecycle revision remains canonical history:      YES
receipt treated as canonical history:              NO
Personal Fact lifecycle changed:                   NO
runtime writer implemented:                        NO
schema changed:                                    NO
export/restore changed:                            NO
frontend changed:                                  NO
retrieval changed:                                 NO
release claim expanded:                            NO
```

---

## 15. Closeout

```text
UMS05C10BC_LIFECYCLE_TRANSITION_CONTRACT_COMMITTED
```

Campaign transition:

```text
UMS-05C10A: CLOSED
UMS-05C10B-R: CLOSED
UMS-05C10B-P: CLOSED
UMS-05C10B-C: CLOSED
UMS-05C10B-W ORDINARY MEMORY RETIRE / RESTORE WRITER: AUTHORIZED
UMS-05C10B: OPEN UNTIL C10B-W PASSES
UMS-05C11+: NOT AUTHORIZED
UMS-05D+:  NOT AUTHORIZED
UMS-06+:   NOT AUTHORIZED
```

`UMS-05C10B-W` is the sole successor and was not begun. It may now implement
`retire` and `restore` against the frozen graph and the C10B-P persistence
without making further architectural decisions.

Gitleaks was skipped narrowly: the sandbox cannot bootstrap the Go toolchain.
Every other executable pre-commit hook ran. `gitleaks` is required at branch
integration.
