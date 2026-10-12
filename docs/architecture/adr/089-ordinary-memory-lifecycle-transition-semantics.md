# ADR-089: Ordinary Memory Lifecycle Transition Semantics

**Status:** Accepted — design frozen

**Date:** 2026-09-29

## Context

ADR-084 froze the Unified Account-Owned Memory Store architecture, including
ordinary-memory lifecycle. Present-state authority has existed since UMS-05C8:
`memory_records.lifecycle_state` is the sole lifecycle authority over `active`,
`dormant`, and `retired`, enforced by a frozen database CHECK.

Three Campaign slices then established what was missing and what was not.

**UMS-05C10B-R** revalidated lifecycle authority and found a hard gap. The
contract requires restore to return a retired record to its *pre-retirement
governed posture*, but no canonical state recorded that posture. A memory
retired from `active` and a memory retired from `dormant` were both simply
`lifecycle_state = retired`; nothing distinguished them. The revalidation also
recorded `LIFECYCLE_TRANSITION_GRAPH: PARTIAL` and found that the Memory Vault
§5.1 retire/restore rows still promised only a receipt, diverging from the
normative §3.3 revision rule.

**UMS-05C10B-P** closed the persistence half. `memory_lifecycle_revisions` and
`account-export.v7` now preserve ordered typed transitions, so
`active -> retired` and `dormant -> retired` are distinguishable through
persistence, export, and restore. Critically, that slice deliberately encoded
**no** transition policy: all six unequal state pairs are structurally
representable, and persistence representability is not runtime authorization.

**The remaining blocker is semantics.** A future writer must know which
transitions are legal, what restore targets, what a repeated action does, and
whether hold, pin, or review constrain explicit user actions. Those are durable
authority decisions. Reconstructing them from a writer implementation later
would make the lifecycle state machine an emergent property of code rather
than accepted architecture — the exact failure mode ADR-088 was created to
prevent for review transitions.

## Decision

### State meanings

**`active`** — the record is lifecycle-eligible to participate in normal memory
behavior, subject to all independent review, context-posture, scope, subtype,
and exclusion gates. `active` does not imply approved, ambient eligible,
pinned, held, or in scope for every request.

**`dormant`** — the record remains canonically stored and recallable under
explicit authorized widening, but is excluded from ordinary ambient
participation by lifecycle. Dormancy is non-destructive, not rejected, not
retired, not equivalent to purge, and not a synonym for `archived`.

**`retired`** — the record remains canonically stored but is reversibly
soft-removed from normal lifecycle participation. Retired is reversible,
ambient-ineligible, distinct from dormant, not purge, and the sole
ordinary-memory soft-removal state. There is no separate canonical `archived`
lifecycle state.

### Direct Memory Vault lifecycle actions

C10B-W exposes exactly two generic direct lifecycle actions: `retire` and
`restore`. It must **not** add generic `activate`, `reactivate`,
`set_active`, `set_dormant`, `set_lifecycle_state`, or `archive`. Direct
promotion or activation of a dormant memory, if a later import or promotion
workflow needs it, requires its own governed contract or an already-accepted
owning workflow. It must not be smuggled in through retire/restore.

### Direct action matrix

| Current lifecycle | `retire` | `restore` |
| --- | --- | --- |
| `active` | -> `retired` | no-op |
| `dormant` | -> `retired` | no-op |
| `retired` | no-op | -> pre-retirement governed posture |

where the pre-retirement governed posture is in `{active, dormant}` and is
recovered **only** from canonical lifecycle history.

### Retire semantics

`active -> retired` and `dormant -> retired` are both legal under explicit
account-principal authority. The lifecycle revision records the exact
`old_lifecycle_state` in each case.

`retired + retire` is an idempotent semantic no-op after successful CAS
validation. It creates no lifecycle revision, no receipt, and no CAS advance.
`retired -> retired` history is never invented.

### Restore semantics

Restore is not "set active." Restore means:

> Undo the current retirement and return the record to the governed lifecycle
> posture that immediately preceded that retirement.

```text
active   -> retired -> restore -> active
dormant  -> retired -> restore -> dormant
```

The two histories remain distinct. Restore must **not** normalize every record
to `active`, and must **not** normalize every record to `dormant`.

### Restore history gate

For a currently retired record, restore requires canonical evidence of its
immediately preceding governed posture. The future writer must find a
lifecycle-history tail reconciling as:

```text
latest.new_lifecycle_state == retired
latest.old_lifecycle_state  in {active, dormant}
```

and then produce `retired -> X`, appending that transition to canonical
lifecycle history.

If a currently retired memory has zero lifecycle history, a gapped history, a
divergent tail, a latest transition that does not end in `retired`, or an
invalid old token, generic restore must **fail closed**. It must not guess
`active`, must not guess `dormant`, and must not infer posture from provenance
extensions, timestamps, heat or ranking state, imported-source metadata, review
state, current hold or pin state, or logs.

### Repeated restore semantics

A direct `restore` against a current `active` or `dormant` record is already
satisfied and is a semantic no-op after successful CAS validation. This gives
retry-safe direct actions **without** creating a generic activation authority.

### CAS doctrine

Direct retire and restore follow existing Memory Vault mutation doctrine: the
future writer validates `memory_records.updated_at` **before** determining
whether an action is a no-op. Therefore stale CAS plus retire on `retired`, or
stale CAS plus restore on `active`/`dormant`, is a **conflict**, not a
successful no-op. Fresh-CAS semantic no-ops do not advance CAS.

### Review-state preservation

Lifecycle actions preserve review authority exactly. Neither retire nor restore
approves, rejects, disputes, or resets to pending. No lifecycle transition
auto-approves a record.

```text
approved + active  -> retire -> approved + retired -> restore -> approved + active
pending  + dormant -> retire -> pending + retired  -> restore -> pending + dormant
```

### Hold interaction

Hold governs automatic decay only. It does not prevent an explicit
authenticated account-principal retire or restore. Direct retire and restore
preserve the hold field unchanged, and must never clear hold during restore. A
restored `active` held memory remains protected from future automatic decay
while held.

### Pin interaction

Pin and unpin remain ranking metadata. Direct retire and restore preserve pin
state, do not infer lifecycle from pin, do not unpin on retirement, and do not
pin on restoration. Pin is not activation.

### Context-posture interaction

Direct retire and restore preserve any independent context-posture authority.
Lifecycle mutation must not silently rewrite context posture; lifecycle
eligibility alone is sufficient to exclude `dormant` and `retired` records from
normal ambient use. As of this ADR the canonical `memory_records` relation has
**no** context-posture column; that fact is recorded here and no column is
invented, because no schema change is authorized.

### Ambient eligibility consequence

The existing computed eligibility law is unchanged. `dormant` and `retired` are
ambient-ineligible without any change to review state. No stored final
ambient-eligibility authority is created.

### Automatic decay boundary

Automatic decay is a **different** mutation authority from direct Vault
retire/restore. The currently accepted automatic transition `active -> dormant`
is a governed automatic policy transition, forbidden while the record is held.
A governed automatic decay transition is still authority-changing and must
therefore use canonical `memory_lifecycle_revisions` plus the appropriate
auditable policy/evidence receipt, applied atomically with the present-state
mutation.

C10B-W is the direct authenticated account-principal retire/restore writer and
does **not** own automatic decay.

| Current lifecycle | automatic decay |
| --- | --- |
| `active`, decay normal | -> `dormant` |
| `active`, held | blocked / no mutation |
| `dormant` | no lifecycle change |
| `retired` | no lifecycle change |

This table documents authority separation. It does not authorize C10B-W to
implement decay.

### Automatic reactivation

Automatic `dormant -> active` is **not** established by this ADR. No current
accepted contract establishes automatic heat-based or time-based reactivation
as lifecycle authority. Derived ranking activity must never silently become
canonical lifecycle mutation. If a later heat or promotion system needs such
behavior, it must be separately governed.

### Dormant ingress

A record may be initialized as `dormant` where an accepted ingress or import
contract explicitly permits that state. Initial creation as `dormant` is
**initialization**, not `active -> dormant`, and therefore does not fabricate a
lifecycle revision. Likewise direct creation as `active` does not fabricate a
lifecycle transition. C10B-P's zero-synthetic-history doctrine is unchanged.

### Explicit recall boundary

Explicit recall of a dormant or retired record does not mutate lifecycle. Recall
may temporarily widen request-scoped access under recall-grant authority. It
does not activate, restore, retire, change review, or change context posture.
Reading is not mutation.

### Lifecycle revision and receipt doctrine

Every changed direct retire or restore produces exactly one
`memory_lifecycle_revisions` row plus exactly one canonical Vault mutation
receipt (`memory-vault-mutation.v1`). The lifecycle revision is canonical
historical authority; the receipt is intent/source/audit evidence. Neither
replaces the other, and no parallel `pre_retirement_state` current-state field
is required, because history itself preserves the posture.

### Receipt action vocabulary

Direct user lifecycle receipt actions are `retire` and `restore`. No current
centralized canonical mutation vocabulary conflicts with these tokens, and no
runtime token is created by this ADR. Automatic decay must use a distinct
policy/audit action identity and must never masquerade as an authenticated user
`retire` or `restore`; its exact tokenization may be deferred to its
implementation slice if no accepted centralized token exists.

### Personal Facts boundary

Nothing in this ADR gives the ordinary lifecycle writer authority over Personal
Facts. Personal Facts retain their specialized lifecycle authority
(`personal_facts.status`, `personal_facts.is_active`,
`personal_fact_revisions`, and the Personal Facts service). The future ordinary
C10B-W writer must fail or delegate at that boundary, and must never
generic-write Personal Fact activation, retirement, or restore state.

### Legacy retired records

C10B-P intentionally fabricated no history, so an existing retired record may
legitimately have `lifecycle_state = retired` with zero lifecycle revisions.
That is valid, portable historical truth: the system knows the record is
retired, but not the posture that preceded retirement.

This ADR must not rewrite that uncertainty. Generic C10B-W restore fails closed
for such a row. A later explicit operator repair or reclassification workflow
may allow a human to choose a target posture with a new authoritative receipt.
That workflow is deferred and is not C10B-W.

## Consequences

- Retire becomes deterministic from both `active` and `dormant`.
- Restore becomes reversible without ever collapsing `dormant` into `active`,
  because the posture is recovered from canonical history rather than assumed.
- Repeated direct actions are retry-safe through no-op semantics that still
  validate CAS first, so a stale token never masquerades as a harmless retry.
- Legacy retired rows whose prior posture is unknowable fail closed instead of
  being silently restored to a guessed state.
- Review state remains fully independent, so lifecycle can never approve.
- Hold blocks policy decay but never blocks an explicit user lifecycle action.
- Lifecycle history now carries restoration posture, which is what makes the
  contractual restore rule implementable at all.
- Direct activation remains deliberately outside C10B-W, so no generic
  activation authority leaks in through retire/restore.
- Automatic decay remains a separate authority path with its own evidence.

## Alignment

```text
Aligned with ADR-084: YES
Supersedes ADR-084:    NO
Modifies ADR-084:      NO
```

This ADR narrows itself to ordinary-memory lifecycle transition semantics. It
does not change account ownership, Project scope, Persona attribution, review
authority, Personal Fact authority, retrieval authority, or portability
architecture. It does not modify ADR-088.

## Rejected alternatives

1. **Restore always to `active`.** Rejected: a record retired from `dormant`
   would be silently promoted into normal lifecycle participation on restore,
   and the two distinct histories C10B-P now preserves would collapse. It also
   converts a lifecycle restore into a de facto activation authority.
2. **Restore always to `dormant`.** Rejected: symmetric failure. A record
   retired from `active` would return permanently excluded from ambient
   participation, silently changing lifecycle rather than undoing a change.
3. **Store a parallel mutable `pre_retirement_state` column.** Rejected: it
   duplicates history in a mutable current-state field, invites drift between
   the two, and the append-only history already records the fact exactly.
4. **Infer prior posture from provenance extensions.** Rejected: extensions are
   explicitly non-authority, and C10A-R/C10B-R both established that history
   may not be reconstructed from them.
5. **Infer prior posture from timestamps or derived heat state.** Rejected:
   timestamps are presence-only markers and heat is a rebuildable projection;
   neither is canonical lifecycle history.
6. **Clear or reset review state on retire.** Rejected: review and lifecycle
   are independent axes, and review actions already do not touch lifecycle.
7. **Auto-approve on restore.** Rejected: the contract explicitly states
   restore does not auto-approve a formerly unapproved record, and approval
   would silently change ambient eligibility.
8. **Let hold block explicit retire or restore.** Rejected: hold governs
   automatic decay only. Blocking explicit operator intent would make hold a
   lifecycle authority it was never defined to be.
9. **Collapse `dormant` and `retired`.** Rejected: they are distinct in
   meaning, in reversibility, and in ambient consequence.
10. **Add a generic unrestricted `set_lifecycle_state`.** Rejected: it would
    expose exactly the transition authority this ADR is freezing, and would
    make illegal pairs a runtime caller's choice.
11. **Make C10B-W own automatic decay.** Rejected: automatic policy transition
    and explicit user action are different authority classes with different
    evidence; merging them would misattribute policy outcomes to the user.
12. **Invent automatic `dormant -> active` reactivation.** Rejected: no
    accepted contract establishes it, and derived ranking activity must never
    silently become canonical lifecycle mutation.

## Current-truth boundary

Architecture only. This ADR creates no retire writer, no restore writer, no
activation writer, no decay implementation, no route, no schema, no migration,
and no export/restore behavior change. The Memory Vault remains internal-only.
`[[../00-current-state|00 Current State]]` remains release authority.
