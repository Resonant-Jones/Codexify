# ADR-088: Ordinary Memory Review Transition Semantics

**Status:** Accepted — design frozen

**Date:** 2026-09-28

## Context

ADR-084 froze the Unified Account-Owned Memory Store architecture, including
the ordinary-memory review axis. Since then the campaign has established the
persistence this ADR builds on, in three slices.

**UMS-05C8 / C8-Q** provided *present-state* persistence.
`memory_records.review_state` is the sole current ordinary-memory review
authority, typed over `pending`, `approved`, `rejected`, `disputed`.

**UMS-05C10A-R** revalidated review-transition *history* authority and found
two separate gaps:

```text
REVIEW_HISTORY_NEW_CANONICAL_PERSISTENCE_REQUIRED
TRANSITION_GRAPH: NOT EXPLICIT
```

Nothing in canonical storage could reconstruct a review transition sequence
such as `pending → approved → disputed → approved → rejected`, and no current
contract defined which transitions were legal.

**UMS-05C10A-P** closed the first gap. It added the canonical
`memory_review_revisions` family and carried it through `account-export.v6`. It
deliberately did **not** encode legal source→target pairs: the database accepts
any unequal pair of valid review tokens, because encoding a policy the
architecture had not accepted would have been an unrecorded architectural
decision inside a persistence slice.

That leaves the second gap open, and it is now the only thing standing between
the accepted architecture and a review writer. An `approve` implementation must
know whether it may act on an already-disputed record, whether approving
activates it, and what `reviewed_at` means after re-approval. Those are durable
runtime semantic decisions. Reconstructing them from an implementation later
would make the state machine an emergent property of code rather than accepted
architecture.

This ADR freezes that state machine. It narrows itself to ordinary-memory
review transitions and implements nothing.

Four truth surfaces now exist and must not be merged:

```text
memory_records.review_state    = current review authority
memory_review_revisions        = historical review-authority transitions
memory_revisions               = authored content history
memory_provenance              = intent / source / audit evidence
review transition contract     = which user actions may legally change review authority
```

This ADR governs the last one.

## Decision

### State definitions

**`pending`** — the proposition is stored but has not received an authoritative
user review decision. `pending` is an ingress / unreviewed state, not a user
review outcome. Automatic classifiers, importers, assistant suggestions, and
web/tool-derived capture may create or preserve `pending` under their governing
contracts.

**`approved`** — the authenticated user has accepted the proposition as
approved ordinary memory. Approval alone determines no lifecycle state.

**`rejected`** — the authenticated user has explicitly rejected the proposition
as memory authority. The row may remain durably stored for provenance and
history unless separately erased under the permanent-erasure policy.

**`disputed`** — the authenticated user has explicitly marked the proposition as
contested or not presently accepted as reliable memory authority. `disputed` is
distinct from both `pending` and `rejected`: it records an affirmative user
judgment of unreliability, not an absence of judgment.

### Direct review actions

The Memory Vault review writer will expose exactly three direct review actions:

```text
approve
reject
dispute
```

There is no direct `set_pending`, `reset_review`, or `unreview` action. A
future feature may introduce one only through a separately governed contract
change.

### Legal transition graph

| Current state | `approve` | `reject` | `dispute` |
| --- | --- | --- | --- |
| `pending` | → `approved` | → `rejected` | → `disputed` |
| `approved` | no-op | → `rejected` | → `disputed` |
| `rejected` | → `approved` | no-op | → `disputed` |
| `disputed` | → `approved` | → `rejected` | no-op |

These are all legal direct user review transitions. No other transition is
legal.

### Same-state requests

A request whose target equals the current state is a semantic no-op:

```text
approved → approved
rejected → rejected
disputed → disputed
```

A no-op is not a transition. The future writer must return unchanged state
**without** creating a review revision, creating a mutation receipt, or advancing
`memory_records.updated_at`. CAS must still be validated *before* the no-op is
recognized, following established Memory Vault mutation doctrine: a stale token
conflicts even when the requested target equals current state.

### Re-entry to `pending`

Direct user review actions must not transition a reviewed memory back to
`pending`. These are therefore illegal:

```text
approved → pending
rejected → pending
disputed → pending
```

`pending` means authoritative review has not yet occurred for the current
proposition. It is not a fourth user judgment alongside approve/reject/dispute.
A workflow that must invalidate a prior review because the proposition itself
changed materially must define its own authority semantics explicitly rather
than silently reusing `pending`.

Current content correction (UMS-05C9-W) preserves review state and is unchanged
by this decision.

### Review / lifecycle independence

Review and lifecycle remain independent axes. Explicitly:

```text
approval auto-activates:   NO
reject auto-retires:       NO
dispute auto-retires:      NO
retire changes review_state: NO
restore auto-approves:     NO
```

Approval and activation are separate user-governed dimensions. A memory may
validly be `approved + active`, `approved + dormant`, or `approved + retired`,
subject to other existing invariants. Rejection and dispute do not retire a
record: the review state is itself sufficient to make the record ineligible for
ambient context.

### Ambient eligibility

This ADR does not alter the existing computed eligibility law. For ordinary
memory, ambient eligibility continues to require, among other gates:

```text
lifecycle_state == active
AND review_state == approved
AND context_posture == ambient_context_eligible
AND scope_is_authorized
AND subtype_policy_allows
AND no_exclusion_applies
```

Consequently `rejected`, `disputed`, and `pending` memory is ambient-ineligible
without any lifecycle mutation. No stored `ambient_eligible` field is introduced.

### `reviewed_at` semantics

`reviewed_at` is frozen as the timestamp of **first authoritative approval**. It
is not the latest review transition time, not a current-review-state timestamp,
not a rejection time, not a dispute time, and not review-history authority.

Rules for the future writer:

- on transition to `approved`, if `reviewed_at IS NULL`, set it to a
  database-authored timestamp;
- on a later re-approval, preserve the existing first-approval timestamp;
- on transition to `rejected` or `disputed`, do not clear or rewrite
  `reviewed_at`.

Transition timing belongs to `memory_review_revisions.created_at`.

### Review revision and receipt requirement

Every **changed** legal review transition must create exactly one
`memory_review_revisions` row carrying old review state, new review state, the
per-memory review revision number, the authenticated account actor, and an
immutable transition timestamp.

Every **changed** legal review transition must also create exactly one
`memory-vault-mutation.v1` intent receipt.

The receipt does not replace the review revision, and the review revision does
not replace the receipt. They satisfy distinct obligations and neither may be
promoted to the other's role.

### Future action labels

The future mutation receipt actions are frozen as `approve`, `reject`, and
`dispute`. The current canonical Memory Vault mutation action vocabulary
(`pin`, `unpin`, `hold`, `release_hold`, `set_project_scope`,
`clear_project_scope`, `add_persona_attribution`, `remove_persona_attribution`,
`content_correction`) does not already name these actions, so no existing token
conflicts and no new runtime token is created by this ADR.

### Personal Facts boundary

Nothing in this ADR applies direct ordinary review transitions to Personal
Facts. Personal Facts remain governed by `personal_facts.status`,
`personal_facts.is_active`, `personal_fact_revisions`, and Personal Facts
service authority, as established by ADR-084 and the Unified Memory Store
contract. Personal Fact state mappings are not redefined here, and the future
ordinary writer must fail or delegate at the specialized boundary.

### Actor authority

The future review writer is an authenticated human/operator Memory Vault
action, and the authoritative actor is the authenticated account principal. A
model, importer, classifier, assistant, web result, tool result, or other
suggestion-producing subsystem may not directly promote a pending ordinary
memory to approved authority merely by emitting tool arguments or candidate
output. This preserves the existing rule that automatic and suggested material
cannot self-approve.

### Import and automatic-capture boundary

This state machine does not change capture policy. Non-authoritative capture may
produce `pending` under existing contracts. It may not directly produce an
authoritative user transition such as `pending → approved` unless the action is
an explicitly authenticated user-authority path already allowed by contract.
Import and classifier workflows are not redesigned here.

### Direct creation boundary

Existing explicit user-authored direct memory creation may create an `approved`
memory directly where the Unified Memory Store contract already allows it. That
initial creation is not represented as `pending → approved` unless creation
persistence explicitly records such a transition.

No historical review revision may be fabricated for direct creation merely
because the resulting state is `approved`. This ADR governs mutation of an
existing record's review authority. UMS-05C6 creation semantics are unchanged.

## Consequences

- The review writer becomes deterministic: every legal action has one defined
  target from every reachable state, and illegal actions have a defined refusal.
- Rejected and disputed memory becomes ambient-ineligible without any lifecycle
  mutation, keeping review and lifecycle genuinely independent.
- Changing a reviewed state remains reversible through another explicit review
  action; reversibility comes from a competing legal edge, not from a reset.
- No "reset to pending" exists, so `pending` retains a single unambiguous
  meaning and review history is never ambiguous about its origin.
- The lifecycle writer remains independently governed under UMS-05C10B.
- Review revision history remains canonical and portable through
  `account-export.v6`, and now has a defined legal vocabulary to describe.

## Alignment

```text
Aligned with ADR-084: YES
Supersedes ADR-084:     NO
Modifies ADR-084:       NO
```

This ADR narrows itself to ordinary-memory review transitions. It does not
change account ownership, Project scope, Persona attribution, lifecycle
authority, Personal Fact authority, retrieval authority, or portability
architecture.

## Rejected alternatives

1. **Make review transitions irreversible.** Rejected: a user who later
   discovers a disputed memory is sound must be able to say so without erasing
   and recreating the record. Irreversibility would convert a correctable
   judgment into permanent data loss, and would make the competing-edge
   reversibility in the frozen matrix impossible.

2. **Automatically retire rejected or disputed memory.** Rejected: retirement
   is a lifecycle decision owned by a separate, explicitly user-governed
   action. Coupling them would let a review action silently destroy ambient
   eligibility semantics that already exist, blur the two independent axes, and
   couple this slice to the unauthorized UMS-05C10B writer. Review state is
   already sufficient for ambient exclusion.

3. **Automatically activate approved memory.** Rejected: approval and
   activation are distinct user-governed dimensions, and ADR-084 treats
   activation as an explicit governance act. Auto-activation would let a review
   action make a record ambient-eligible as a side effect.

4. **Allow direct transition back to `pending`.** Rejected: `pending` encodes
   "authoritative review has not occurred". Using it as a reset would make the
   same token mean both never-reviewed and review-invalidated, destroying the
   meaning of review history and of `reviewed_at`. A materially changed
   proposition needs its own explicit authority semantics.

5. **Treat mutation receipts as sufficient history.** Rejected: receipts are
   audit/evidence and their `extensions` are explicitly non-authority. This was
   the exact question UMS-05C10A-R examined and answered
   `REVIEW_HISTORY_NEW_CANONICAL_PERSISTENCE_REQUIRED`; the resulting
   `memory_review_revisions` family is the canonical answer.

6. **Reuse content `memory_revisions`.** Rejected: that family stores typed
   authored text with an authored-text chain and a no-op constraint on text. A
   review transition has no authored-text dimension, and reusing the table
   would corrupt content reconciliation and break C9's restore invariants.

7. **Encode the graph as a database constraint instead of freezing it here.**
   Rejected: the graph is a runtime mutation-authority decision, not a storage
   fact. C10A-P correctly kept persistence permissive so that no unaccepted
   policy was frozen into the schema.

## Current-truth boundary

Architecture only. This ADR creates no review writer, route, service method,
schema, migration, export or restore behavior, or UI. `approve`, `reject`, and
`dispute` remain unimplemented. `[00 Current State](../00-current-state.md)`
remains release authority.
