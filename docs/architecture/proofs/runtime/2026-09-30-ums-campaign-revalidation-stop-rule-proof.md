# UMS Campaign Revalidation — Stop-Rule Determination

**Status:** CLOSED
**Class:** Campaign governance revalidation / maturity classification / intake-gate adjudication
**Campaign:** Unified Account-Owned Memory Store
**Date:** 2026-09-30
**ADR impact:** Aligned with ADR-084, ADR-088, ADR-089. No new ADR. This proof adjudicates campaign state; it opens no architecture question.
**Authorized edits:** documentation only — this proof, `docs/Campaign/unified-memory-store/README.md`, `docs/architecture/00-current-state.md`. No production, schema, migration, route, retrieval, UI, or release change.

---

## 1. Terminal outcome

```text
UMS_FOUNDATIONAL_GAP_REMAINS
```

The governed UMS architectural baseline is **not** complete, so the campaign
**does not** stop, and **new foundation expansion remains frozen except for
exactly one item**: the audited permanent-erasure capability the Campaign's own
governance already declares mandatory.

```text
UMS ARCHITECTURAL BASELINE: COMPLETE EXCEPT PERMANENT ERASURE
NEW FOUNDATION EXPANSION: FROZEN
UMS-05C11+: NOT AUTHORIZED
UMS-05D+: NOT AUTHORIZED
UMS-06+ (EXCEPT UMS-11): NOT AUTHORIZED
UMS-11 AUDITED PERMANENT ERASURE: ADMIT_NOW (sole authorized successor)
UMS-12 SUPPORTED USER-FACING PROOF: NOT AUTHORIZED — BLOCKED ON UMS-11
REMAINING REFINEMENT / UX / ADVANCED ITEMS: PARKED
```

Task numbering was not treated as evidence of necessity. Every remaining packet
was independently tested against the five-point intake gate (§6). Only UMS-11
passed.

---

## 2. Lineage

| Field | Value |
|---|---|
| Branch | `feature/ums-continued` |
| Starting HEAD | `e4d0f12af6e5d6bd7abe0bef71b7181309f033b5` |
| C10B-W commit | `464195477c5c3c2d2a1b4fdc356bf12f7ddb2dd0` (ancestor) |
| C10B-W / bookkeeping reconciliation | `e4d0f12af6e5d6bd7abe0bef71b7181309f033b5` (opening tip) |
| Alembic head before | `b8e2f4a6c901` (single head) |
| Alembic head after | `b8e2f4a6c901` (single head, **unchanged**) |
| Opening index | empty |
| Untracked posture | only preserved `.precommit_cache/` / `.precommit_home/` entries |
| Push count | `0` |
| Implementation surface | read-only. Zero production, test, schema, or migration edits. |

No merge, rebase, fetch, pull, reset, or cherry-pick was performed.

---

## 3. Method

Each remaining Campaign item was classified by **maturity** across ten
dimensions, then admitted or parked strictly by the intake gate. Three
distinctions were held throughout, because collapsing them is how a
documentation-only revalidation goes wrong:

- **architecture-exists** — the semantics are frozen in a contract or ADR.
- **runtime-exists** — a supported implementation path and its proof exist.
- **proof-exists** — end-to-end supported-user evidence exists.

Missing proof over a runtime-proven capability is `COMPLETE_BUT_PROOF_PENDING`.
It is **not** a `FOUNDATIONAL_GAP`. A capability with no runtime and no owning
authorized slice **is** a `FOUNDATIONAL_GAP`. A missing UI is product
maturation, not architecture failure.

---

## 4. Maturity assessment — ten dimensions

| # | Dimension | Classification | Evidence |
|---|---|---|---|
| 1 | Ownership | `RUNTIME_PROVEN` | `memory_records.user_id` FK → `users.id` `ON DELETE CASCADE`; two-account export/restore isolation proven |
| 2 | Canonical persistence | `RUNTIME_PROVEN` | Six canonical families in `guardian/db/models.py`: `memory_records`, `memory_persona_links`, `memory_provenance`, `memory_revisions`, `memory_review_revisions`, `memory_lifecycle_revisions` |
| 3 | Mutation governance | `RUNTIME_PROVEN` | `MemoryVaultMutationService` provides `set_pinned`, `set_held`, `set_project_scope`, `set_persona_attribution`, `correct_content`, `transition_review`, `transition_lifecycle`; CAS-before-no-op, append-only revision history, receipts separate from history authority |
| 4 | Retrieval authority | `ARCHITECTURE_SPECIFIED` / `RUNTIME_ABSENT` for persona-aware grants | `MemoryRecallGrant` appears only in `docs/architecture/unified-memory-store-contract.md:2437` and the Campaign packet. **Zero occurrences in any `.py`.** Direct authorized recall of dormant/retired non-purged records does work |
| 5 | Ingestion / import | `RUNTIME_ABSENT` for UMS bounded import | `guardian/services/openai_account_import.py` is account-level import, a different subsystem. UMS-08 bounded Anthropic Project/memory import is unbuilt |
| 6 | Retention / decay | `NOT_IMPLEMENTED` and **vacuously non-destructive** | No heat/decay/retention implementation in the UMS vault path. The only `session.delete` in `memory_vault_mutation.py:599` removes a persona *link*, never canonical content. Nothing destructively ages out today |
| 7 | **Permanent erasure** | **`ARCHITECTURE_SPECIFIED` / `RUNTIME_ABSENT` / `PROOF_ABSENT` / `NO OWNING SLICE`** | See §5 |
| 8 | Portability | `RUNTIME_PROVEN` | `account-export.v7` (7 canonical families); v5 revisions → v6 review revisions → v7 lifecycle revisions. Replay idempotency and chain integrity proven |
| 9 | Operator / user surface | `PRODUCT_MATURATION` | Memory Vault is internal-only. No UMS work widened the public Beta surface |
| 10 | End-to-end supported-user proof | `BLOCKED` — see §7 | Not `COMPLETE_BUT_PROOF_PENDING`, because the blocking prerequisite has no runtime |

---

## 5. The single foundational gap: permanent erasure

### 5.1 It is mandatory, and the repo says so in four independent places

1. **ADR-084** — "Supported user-facing release remains blocked until permanent
   erasure and re-import suppression are proven."
   (`docs/architecture/adr/084-unified-account-owned-memory-store.md:199-200`)
2. **Contract §12** — "Permanent purge is mandatory before supported
   user-facing release." (`docs/architecture/unified-memory-store-contract.md:2731-2733`)
3. **Campaign global proof matrix** — invariant `Permanent erasure`, minimum
   proof "canonical/derived purge fan-out plus resurrection suppression".
   (`docs/Campaign/unified-memory-store/README.md:1064`)
4. **Campaign account-ownership proof matrix row** — requires purge isolation
   across route, repository, retrieval, export, and restore.
   (`docs/Campaign/unified-memory-store/README.md:1054`)

Because row 4 folds purge into the **account ownership** invariant, the gap is
not confined to the release gate: the ownership invariant the closed slices
established is only *fully* proven once purge exists.

### 5.2 The architecture is specified — and explicitly disowned

The contract does define the shape, so this is not an architecture void:

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

(`docs/architecture/unified-memory-store-contract.md:2746-2755`), with re-import
suppression at §9.4 (`:2673-2677`).

But the contract **twice disowns its own implementation**:

- `:1221` — "Permanent erasure semantics are deferred to UMS-11."
- `:2066-2068` — "Permanent erasure semantics are explicitly not implemented
  here; the contract documents that UMS-11 owns permanent purge and the
  surviving `memory_purge_tombstone` semantics."

### 5.3 The runtime is entirely absent — verified, not assumed

| Search | Scope | Result |
|---|---|---|
| `purge`, `permanent_erasure`, `hard_delete`, `resurrect` | `guardian/`, `tests/` | Only `guardian/queue/redis_queue.py` `_purge_if_expired` (queue key expiry) and one unrelated `tests/migration/test_uploaded_documents_project_required_migration.py` test name |
| `memory_purge_tombstone`, `memory_purge` | `guardian/`, `tests/` | **Zero occurrences** |
| Account erasure / `erase_account` / `delete_account` / GDPR | `guardian/` | **Zero occurrences** |
| `POST /api/memory/records/{record_id}/purge` (contract §13) | `guardian/routes/`, `guardian/api/` | **Absent.** `guardian/routes/memory_vault.py` exposes only item list/canonical/read/patch/post mutation routes |
| Purge or erasure proof artifact | `docs/architecture/proofs/runtime/` | **None** |

No canonical memory content deletion path exists anywhere in the UMS runtime.

### 5.4 `retired` is not erasure

C10B-W shipped retire/restore. That is **not** a substitute. The contract is
explicit that `retired` is "not purge, and the sole [state that] remains
canonically retrievable" (`unified-memory-store-contract.md:202-204`). Retire
retains content; purge must remove it. Treating the closed lifecycle writer as
partial erasure would be precisely the collapse this revalidation must avoid.

### 5.5 Why this is a gap and not "proof pending"

Proof of erasure requires erasure to exist. A capability that is
contract-sketched, disowned to an unauthorized packet, and absent from every
persistence, service, route, and test surface is not
`COMPLETE_BUT_PROOF_PENDING`. It is unimplemented, and its architecture has no
owning slice in flight. That is the definition of a foundational gap.

---

## 6. Intake gate — per remaining packet

An item is admitted only if it satisfies at least one criterion:
**(a)** closes a baseline structural gap, **(b)** resolves an inconsistency,
**(c)** removes a proof-immune blocker, **(d)** materially simplifies baseline
work, **(e)** proves dependency order wrong.

| Packet | (a) | (b) | (c) | (d) | (e) | Verdict | Disposition |
|---|:-:|:-:|:-:|:-:|:-:|---|---|
| **UMS-11** audited permanent erasure | **Y** | Y | **Y** | Y | – | **ADMIT** | `ADMIT_NOW` |
| UMS-06 explicit memory commands | N | N | N | N | N | park | `PARK_PRODUCT_REFINEMENT` |
| UMS-07 persona-aware recall grants | N | N | N | N | N | park | `PARK_ADVANCED` |
| UMS-08 bounded imports | N | N | N | N | N | park | `PARK_ADVANCED` |
| UMS-09 consent-gated suggestions | N | N | N | N | N | park | `PARK_PRODUCT_REFINEMENT` |
| UMS-10 heat → projection | N | N | N | N | N | park | `PARK_ADVANCED` |
| UMS-12 supported user-facing proof | – | – | **N** | N | N | **blocked** | `NOT AUTHORIZED` |
| UMS-05C11+ / UMS-05D+ | – | – | N | N | N | park | `NOT AUTHORIZED` |

Notes on the parks, recorded so a future pass does not re-derive them:

- **UMS-06** layers `memory.remember` and receipts over mutation authority that
  already exists in full. It is a UX surface, not structure.
- **UMS-07** is genuinely architecture-specified but unbuilt. It is *not* a
  release precondition under ADR-084, which gates only on erasure and re-import
  suppression. Retrieval already works through direct authorized recall.
- **UMS-08** is additionally blocked from the outside: ADR-084 holds Anthropic
  Project import "until ADR-081's runtime normalization and legacy
  reconciliation are proven" (`adr/084:196-197`). Recorded as a live external
  precondition, not as a UMS failure.
- **UMS-10** replaces destructive heat with a projection. There is no
  destructive heat in the UMS canonical path to replace (§4 dim 6), so it
  proposes a future design alternative rather than fixing a live defect.
- **UMS-05C11+** was **not invented to preserve numbering.** No packet beyond
  C10 exists. A gap is recorded as a gap; it is not given a C11 identity to make
  the sequence look continuous.

No item qualified as `OBSOLETE`, `SUPERSEDED`, or `NOT_UMS`. The `PROOF_ONLY`
slot is deliberately left **unused**: the sole proof-shaped candidate is
UMS-12, and it is not provable (§7).

---

## 7. Why UMS-12 cannot be authorized

UMS-12 is the only packet whose intent is proof rather than construction, so
it is the natural candidate for a bounded "architecture is done, prove it"
stop. It fails on the repo's own text, three times over:

1. **Its stated dependency.** "Depends on: every prior task" — which includes
   UMS-11. (`docs/Campaign/unified-memory-store/README.md:1017`)
2. **Its acceptance requires purge.** "...hold/decay, retirement, and purge all
   pass with account isolation and truthful failure receipts." (`:1020-1022`)
3. **Its proof requires purge fan-out.** "...export/restore archive validation,
   **purge fan-out**, and current-state update only after all gates pass."
   (`:1023-1025`)

Authorizing UMS-12 before UMS-11 would authorize a task that is guaranteed to
fail its own acceptance, and would invite a release-truth update that the same
packet forbids before all gates pass. It is blocked, not parked — blocking is
dependency-driven and clears the moment UMS-11 closes.

---

## 8. Stop-rule verdict

### A. Expected baseline

Does Codexify now possess the structural primitives expected of a mature
governed memory store?

```text
expected baseline satisfied: NO
```

Nine of the ten required primitives are runtime-proven — ownership, scope,
provenance, review authority, lifecycle authority, history, mutation safety,
portability, and recall authority. **Erasure semantics are not.** ADR-084
enumerates the baseline and the Campaign proof matrix enumerates it again, and
both include permanent erasure. A baseline that excludes a primitive its own
governing documents require is not satisfied.

### B. Foundational paths

Are the primary paths implemented, or at least bounded by one clearly
identified proof gate?

```text
foundational paths sufficiently implemented: NO
```

Nine paths are implemented. The tenth — permanent erasure — is neither
implemented nor bounded by a proof gate. It is bounded by **no gate at all**,
because it is the gate. `UMS-12` is precisely the proof gate for erasure
("purge fan-out" is one of its required proofs), so the path is circular: the
only gate covering erasure is a gate that erasure itself blocks. That
circularity is the formal statement of the gap.

### C. Remaining gaps

Are the remaining gaps predominantly UI, product refinement, automatic
convenience, observability, optimization, advanced retrieval, consolidation,
recommendation, or differentiators?

```text
remaining gaps mainly refinement/proof/advanced: NO
```

Almost all of them are. Six of the seven remaining packets are UI, refinement,
or advanced capability. But one is not, and it is load-bearing:

```text
UMS-11 audited permanent erasure — FOUNDATIONAL
```

A dominant pattern does not make a foundational gap optional. One concrete
baseline capability is actually absent, and proof alone cannot close it.

### Verdict

```text
architectural stop rule satisfied: NO
```

Test A fails, so the conjunction (A and B and C) fails. Outcome B is excluded
by its own condition — "do not choose this while a current mandatory UMS proof
obligation remains unresolved," and the permanent-erasure obligation is
unresolved. Outcome A is excluded by its own admission rule, which requires
proof that UMS-12's required capabilities *are implemented*; they are not.
Outcome D was tested and rejected in §12.

```text
UMS_FOUNDATIONAL_GAP_REMAINS
```

### Final stop-rule report

```text
foundational ownership complete:          YES
foundational persistence complete:        YES
foundational mutation governance complete: YES
foundational retrieval authority complete: NO  (architecture-only for persona-aware grants; direct authorized recall works)
foundational lifecycle complete:          YES
foundational portability complete:        YES
permanent-erasure implementation complete: NO
remaining UMS architecture gap exists:    YES
remaining UMS proof gap exists:           YES
remaining work mainly refinement/UI/advanced: YES
architectural stop rule satisfied:        NO
```

Two gaps are reported honestly rather than collapsed. The **architecture gap**
is permanent erasure: absent runtime, absent persistence, absent route, absent
proof, and no owning slice. The **proof gap** is UMS-12's end-to-end
supported-user evidence. They are different gaps with a different remedy — one
needs construction, the other needs qualification — and the proof gap is
strictly downstream of the architecture gap. Reporting only the proof gap would
have produced Outcome A and a green checkmark over an unerasable memory store.

---

## 9. Sole successor

```text
UMS-11 — Implement audited permanent erasure
```

One atomic prerequisite. Not a bundle. It is the smallest slice that removes
the blocker, because the blocker *is* a single missing capability: no part of
purge can be built without the tombstone relation that suppresses resurrection,
and no part of resurrection suppression can be built without the purge that
produces the tombstone. Fan-out and suppression are one coherent unit or
neither is provable.

```text
UMS-12 supported-user proof:  BLOCKED on UMS-11
Contract-resolution slice:     NOT REQUIRED (no contradiction found)
NONE - Campaign closed:        NOT SELECTED
```

Exactly one successor is authorized. It was not begun.

---

## 10. Parked work

Parked categories, recorded so a future pass does not silently re-promote them.
Parking is not a dependency: nothing below is required for UMS-11 or UMS-12 to
close.

| Category | Items | Basis |
|---|---|---|
| **Product refinement** | UMS-06 explicit memory commands; UMS-09 consent-gated suggestions | UX and convenience over mutation authority that already exists in full |
| **Mature UX** | Memory Vault frontend surface | The Vault is internal-only by design. UI absence is product maturation, not architecture failure |
| **Advanced** | UMS-07 persona-aware recall grants; UMS-08 bounded imports; UMS-10 heat → projection | Capability beyond the baseline, unbuilt, and not release-gating under ADR-084 |
| **Differentiator** | *(none classified)* | No remaining packet was found whose distinguishing value rather than structural necessity was the whole of its case |

The differentiator row is deliberately empty. Promoting a differentiator into
baseline work is the specific failure this revalidation exists to prevent, and
none of the remaining packets earned it.

---

## 11. Campaign stop-condition check

The Campaign's own stop conditions were checked for **active** violations, so
that "no violation" is not confused with "no gap."

| Stop condition (README:1033-1048) | Status |
|---|---|
| Personal Facts gain a second writable review/activation authority | **Not violated** — `personal_fact_revisions` authority remains separate |
| Infrastructure Operator used as user-memory authority | **Not violated** |
| Project scope load-bearing before ADR-081 convergence | **Not violated** |
| Persona links target only mutable `PersonaProfile` config | **Not violated** — links target stable `persona_subjects` |
| A model can manufacture recall/approval/update/retire/purge authority | **Not violated** |
| Pending/imported/rejected/disputed content enters ambient context via ranking | **Not violated** — UMS-08/09 unbuilt |
| New ingestion enabled before export/restore proof | **Not violated** — export/restore proven at v7; ingestion unbuilt |
| Heat, capacity, or retention deletes canonical content | **Not violated** — no UMS heat/decay/retention path exists |
| **A purge leaves retrievable content or re-import silently resurrects it** | **Unmitigated risk** — no purge exists, so the failure mode cannot yet occur. The capability that would create it is also the capability that must prevent it |
| Task claims release support from docs or code-path evidence alone | **Not violated** — no UMS release claim exists |

**No stop condition is actively violated.** That is a statement about the
closed slices' discipline, not a licence to stop: the Campaign still carries a
mandatory invariant (§5.1) with no runtime and no owning slice.

---

## 12. Governance-contradiction determination

Outcome `UMS_REVALIDATION_GOVERNANCE_CONTRADICTION` was tested and **rejected**.

Campaign bookkeeping was verified directly rather than trusted, because the
C10B-W closure gate had previously found a duplicate/stale-entry defect at
exactly this layer. Re-reading the committed state at `e4d0f12af`:

- `UMS-05C2` … `UMS-05C10` — every slice marked `CLOSED` exactly once, no
  duplicate, no stale `OPEN`, no `FROZEN` residue. (`README.md:138-158`)
- `UMS-05C10A` and `UMS-05C10B` both roll up to `CLOSED`, matching
  `UMS-05C10: CLOSED`. (`:156-158`)
- `UMS-05C11+: NOT AUTHORIZED`, `UMS-05D+: NOT AUTHORIZED`, `UMS-06+: NOT
  AUTHORIZED`. (`:159-163`)
- `NEXT ACTION: CAMPAIGN REVALIDATION REQUIRED` — the advertised next action is
  precisely the action this proof performs. (`:160`)
- `docs/architecture/00-current-state.md:145-150` agrees with the Campaign on
  every line of the state block.

The campaign document and the current-state document are **mutually
consistent**. The one movement the state block needed — replacing
`NEXT ACTION: CAMPAIGN REVALIDATION REQUIRED` with the determined outcome — is
the movement this slice performs. No contradiction was found; nothing was
reconciled beyond that.

---

## 13. Closeout

### 13.1 Determination

```text
UMS_FOUNDATIONAL_GAP_REMAINS
```

The UMS campaign is **not** complete and does **not** stop. It is complete
except for permanent erasure, which the Campaign itself declared mandatory
before supported user-facing release and which has no runtime, no persistence,
no route, no test, and no authorized owner.

### 13.2 Sole authorized successor

```text
UMS-11 — Implement audited permanent erasure: ADMIT_NOW
```

UMS-11 satisfies the intake gate on two independent criteria — it closes a
baseline structural gap (a required canonical relation that does not exist) and
it removes a proof-immune blocker (the ADR-084 release gate, plus the
account-ownership purge-isolation proof row). It is the one item that is not
expansion: it is a declared mandatory precondition.

### 13.3 Invariants confirmed

```text
erasure implemented:                          NO
memory_purge_tombstone relation exists:       NO
purge route exists:                           NO
re-import resurrection suppression exists:    NO
retired treated as purge:                     NO
UMS-12 authorized:                            NO
UMS-11 authorized:                            YES (sole)
UMS-05C11+ invented to preserve numbering:    NO
UMS-06+ other than UMS-11 authorized:         NO
UMS-05D+ authorized:                          NO
schema changed:                               NO
migration head changed:                       NO (b8e2f4a6c901)
retrieval behavior changed:                   NO
route surface changed:                        NO
UI changed:                                   NO
public release claim changed:                 NO
new ADR:                                      NO
production / test / schema edit:              NO
push count:                                   0
```

### 13.4 Handed forward, without acting on it

Two findings are recorded for whoever writes the UMS-11 specification. Neither
was acted on; widening scope here would be exactly the expansion this
revalidation was chartered to prevent.

- **Dependency-order note.** UMS-11's packet declares "Depends on: UMS 03
  through UMS 10" (`README.md:998`), yet UMS-08's own acceptance includes
  purge-tombstone suppression. UMS-11 therefore both precedes and follows UMS-08
  depending on which leg is meant. Canonical/derived purge fan-out does not
  require UMS-08; the re-import suppression proof does. This is a
  **code-path-only** observation from packet text, not a proven runtime claim,
  and no packet was rewritten.
- **UMS-12 blanketing dependency.** UMS-12's "depends on: every prior task"
  (`:1017`) is stronger than the evidence requires, since UMS-12's substantive
  gates are the governed loop plus purge. Recorded as an observation only;
  UMS-12 is blocked on UMS-11 regardless.

### 13.5 ADR impact

```text
ADR IMPACT: ALIGNED WITH ADR-084, ADR-088, ADR-089
NEW ADR: NO
```

This proof applies existing governance. It decides nothing new about erasure
semantics — contract §12 already owns them — and opens no architecture question
requiring a decision record.
