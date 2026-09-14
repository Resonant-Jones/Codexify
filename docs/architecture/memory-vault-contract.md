# Memory Vault Operator Contract

**Status:** Frozen by UMS-05A.
**Governing ADR:** [ADR-084 — Unified Account-Owned Memory Store](./adr/084-unified-account-owned-memory-store.md)
**Governing normative architecture:** [Unified Memory Store Contract](./unified-memory-store-contract.md)
**Parent Campaign:** [UMS-001 Unified Account-Owned Memory Store](../Campaign/unified-memory-store/README.md)
**Slice:** UMS-05A — operator contract only. Runtime Vault API/UI is not implemented by this task.

This contract freezes the human operator surface that sits on top of the
qualified canonical Memory Store substrate. It is **architecture-only**;
no Vault runtime, API, service, route, repository, migration, or frontend
component is implemented by UMS-05A.

---

## 1. Purpose

The **Memory Vault** is:

> the authenticated human operator surface over the canonical
> account-owned Unified Memory Store.

It is the place where a human, signed in as the account principal,
inspects, governs, and (under bounded direct authority) creates
canonical memory for their own account.

The Memory Vault is **not**:

- a new persistence domain;
- the unrelated `guardian/modules/memory_key_vault.py` / `MemoryKeyVault`
  in-memory summary encryption object;
- a retrieval router;
- a conversational / chat command parser;
- an importer of any external memory corpus;
- an automatic suggestion engine;
- an activation / heat / decay projection engine;
- a permanent-erasure implementation;
- a parallel writable authority.

### Naming collision warning

The repository already contains:

    guardian/modules/memory_key_vault.py

which implements `MemoryKeyVault` — an in-memory Fernet-based summary
encryption helper. That object is **unrelated** to UMS-05 Memory Vault
and shares no authority, persistence semantics, or governance. This
contract must not rename, remove, wire, or modify `MemoryKeyVault`.
The Memory Vault described here is a **projection and control surface
over canonical UMS authority**, not an in-memory encryption helper.

---

## 2. Logical item model

A Vault item is the operator-facing projection of one canonical
memory record (and any of its admitted compatibility projections) plus
its attached Persona link and provenance envelope.

Every Vault item resolves, where applicable, to authoritative:

| Field | Authority source |
| --- | --- |
| Stable memory identity | canonical `memory_records.id` |
| Account owner | canonical `memory_records.user_id` (FK to `users.id`) |
| Optional Project scope | canonical `memory_records.project_id` (FK to `projects.id`) |
| Semantic species | canonical `memory_records.species` (`episodic_semantic_memory`, `verified_personal_fact`, `candidate_unreviewed_fact`) |
| Canonical payload / content | canonical `memory_records.payload` / `fact_payload` |
| Review posture | canonical `memory_records.review_status` |
| Activation / lifecycle posture | canonical `memory_records.lifecycle` and `memory_records.activation` |
| Context posture | canonical `memory_records.context_state` where admitted |
| Pin state | canonical `memory_records.pinned` |
| Hold state | canonical `memory_records.held` |
| Stable Persona attribution | canonical `memory_persona_links` against `persona_subjects` |
| Provenance | canonical `memory_provenance` rows |
| Source lineage | canonical `memory_provenance.source_kind` + `external_source_id` |
| Timestamps / version | canonical `memory_records.created_at`, `updated_at`, `revision` |
| Non-authority extensions | canonical `memory_records.extensions` (explicitly labelled non-authority) |

### Personal Facts posture

When the underlying canonical row corresponds to a `verified_personal_fact`
or `candidate_unreviewed_fact` species, the Vault may display the **derived
unified posture** (review + activation + lifecycle + eligibility) but must
**not** create or display a competing writable envelope field.

The Personal Facts service remains the sole authority for Personal Facts
review and activation transitions. The Vault renders what that authority
publishes; it does not write to it.

---

## 3. List surface

The Vault list is the account-owned projection over canonical memory.

Each visible item exposes enough information to distinguish one canonical
record from another:

- stable memory identity (display only — never the write key);
- content / summary preview;
- semantic species;
- scope (account-scoped vs Project-scoped);
- stable Persona attribution;
- review posture;
- lifecycle posture;
- source system (canonical `memory_provenance.source_kind`);
- pinned state where currently true;
- held state where currently true;
- created / last-updated timestamps.

### Frozen canonical filter dimensions

The Vault list admits filtering and sorting only along canonical-backed
dimensions:

- semantic species;
- Project scope;
- stable Persona subject;
- review posture;
- lifecycle posture;
- source system;
- pinned (boolean);
- held (boolean).

The Vault list must **not** admit:

- fuzzy ranking;
- AI-generated grouping / clustering;
- heat-derived ordering;
- automatic suggestion scoring;
- cross-Project "similar" surfacing;
- Project-scope widening of a single Project list;
- Persona-scope widening of a single Persona list.

Sort order is restricted to canonical timestamp fields or canonical
boolean flags (e.g. `pinned DESC, updated_at DESC`).

### Account isolation

The list is strictly scoped to the authenticated account's
`memory_records.user_id`. There is no list cross-account, list by
Project owner other than the calling account, list by infrastructure
Operator, or list by Host Operator.

---

## 4. Detail surface

The Vault detail is the operator-truth surface for one logical record.

The detail must make visible:

- stable record identity (`memory_records.id`);
- full payload / content (canonical);
- owner / account boundary (canonical `user_id`);
- Project scope (canonical `project_id`);
- semantic species;
- review / lifecycle / activation authority;
- Persona links with exact link kind (`captured_under`,
  `suggested_by`, `associated_with`) and stable Persona subject;
- provenance records and source IDs (canonical `memory_provenance`);
- timestamps and version;
- pin / hold state;
- extensions, marked **explicitly as non-authority** (advisory /
  cosmetic / classifier hints — not load-bearing for governance).

Where a field is derived rather than persisted, the contract labels
its authority source. The Vault detail never displays a field whose
authority is undefined.

---

## 5. Direct human Vault actions

The Vault admits direct authenticated human actions only where the
underlying canonical subtype authorizes them. Each action has a
named authority owner, preconditions, resulting canonical mutation,
revision / audit / intent receipt, and fail-closed cases.

### 5.1 UMS-05 admitted direct actions

| Action | Authority owner | Resulting mutation | Receipt |
| --- | --- | --- | --- |
| Direct Vault creation of a user-authored canonical memory | canonical user-authored memory service | new canonical `memory_records` row with `source_subject_kind = 'vault'` and `authentication_principal = account_user` | durable mutation receipt + revision |
| Approve (where the subtype permits) | subtype-specific authority (e.g. Personal Facts review service) | canonical review-state transition | durable mutation receipt |
| Reject / dispute (where the subtype permits) | subtype-specific authority | canonical review-state transition | durable mutation receipt |
| Correct / edit user-governed content | canonical revision service for the subtype | new canonical revision, audit-trailed | durable mutation receipt |
| Change Project scope (within the calling account) | canonical scope mutation service | canonical `memory_records.project_id` change with provenance note | durable mutation receipt |
| Add / remove stable Persona attribution | canonical Persona link service | canonical `memory_persona_links` insert / delete | durable mutation receipt |
| Pin / unpin | canonical pin service | canonical `memory_records.pinned` flip | durable mutation receipt |
| Hold / release hold | canonical hold service | canonical `memory_records.held` flip | durable mutation receipt |
| Retire | canonical retirement service | canonical retirement (reversible soft removal) | durable mutation receipt |
| Restore from retirement | canonical retirement service | canonical re-instatement | durable mutation receipt |

For Personal Facts, every action above delegates to the Personal Facts
service rather than mutating competing envelope state.

### 5.2 Not UMS-05 actions (explicitly deferred)

| Capability | Deferred to |
| --- | --- |
| Conversational remember / forget / edit commands through chat | UMS-06 |
| Persona-aware recall grants and retrieval widening | UMS-07 |
| Anthropic / external corpus import | UMS-08 |
| Consent-gated automatic suggestion acceptance flow | UMS-09 |
| Heat / activation projections | UMS-10 |
| Permanent purge / erasure | UMS-11 |

The Vault UI may render a disabled / placeholder affordance for any of
the above **only** with explicit "Not available in this build" copy.
It must not describe them as live, must not preview them, and must not
emit a mutation intent for them.

---

## 6. Creation semantics

A direct authenticated human Vault creation is considered
**explicit user-authored intent**. It is admitted as:

    approved + active

**only** when the existing UMS contract permits explicit user-authored
memory to enter canonical state that way. The Vault creation path
must not extend that rule to:

- classifier output;
- imported content;
- assistant suggestions;
- tool output;
- batch import;
- any flow where the operator is not the explicit author.

Those remain pending / unreviewed unless a later governing flow
explicitly permits otherwise. Each canonical mutation that is not
directly user-authored must keep its existing canonical review /
activation posture and must not be silently upgraded.

The Vault creates a new canonical row only by going through the
canonical user-authored memory service. It must not directly insert
into canonical tables from the UI layer.

---

## 7. Mutation authority

The Vault mutation authority is fixed:

    Vault UI
      → authenticated Guardian service
      → authority validation
      → canonical subtype service
      → transaction
      → revision / intent receipt
      → canonical readback

The Vault UI **must not** write directly to the canonical database.
Frontend code may never call canonical persistence writers. All
authority-changing direct human Vault mutations travel through a
server-side canonical service that produces a durable receipt.

### Named authority per action category

| Action category | Authority service |
| --- | --- |
| Direct Vault creation | canonical user-authored memory service |
| Review / approval / rejection | subtype-specific review service (Personal Facts review for `*_personal_fact` species; canonical memory review for `episodic_semantic_memory`) |
| Content correction | canonical revision service for the subtype |
| Project scope change | canonical scope mutation service |
| Persona attribution change | canonical Persona link service |
| Pin / hold | canonical pin / hold service |
| Retire / restore | canonical retirement service |

The Vault contract does not assume these services already exist; UMS-05B/05C
are the implementation slices that bring them into runtime truth. The
contract fixes what each one must do when it does exist.

---

## 8. Read authority

The Vault read model combines:

- canonical memory records;
- canonical Persona links and provenance;
- admitted compatibility projections;
- specialized Personal Facts authority.

The read model must label or preserve canonical-vs-compatibility
provenance internally. A view of a compatibility projection must
never silently migrate it into canonical persistence; the projection
stays a projection even when the Vault renders it.

The read authority for any cross-Account or cross-Project scope is
denied by default. The Vault has no Host-Operator-mode memory-content
read authority.

---

## 9. Failure behavior

The Vault must fail closed for:

- wrong account;
- Project owner mismatch;
- unresolved stable Persona subject;
- missing canonical parent (e.g. thread, project, memory);
- unsupported subtype for the requested action;
- invalid review / lifecycle transition for the canonical state machine;
- stale version / optimistic-concurrency conflict;
- Personal Fact authority mismatch (the subtype authority refuses);
- unsupported deferred capability (UMS-06+ action requested through Vault).

Failures are surfaced as explicit, named errors. The Vault never falls
back to:

- account-global scope;
- a fallback Persona;
- a default owner;
- a guessed authority;
- a hidden "fix-up" rewrite of canonical state.

A failed action leaves no canonical write. The transaction (or its
absence) guarantees no partial row.

---

## 10. Concurrency / stale-write posture

The Vault must not silently overwrite a newer authoritative revision
via last-write-wins.

This contract fixes one of two options:

1. **Existing canonical optimistic-concurrency mechanism** — the
   current canonical memory record carries a version / revision; the
   Vault mutation service checks it and raises a stale-version error
   on mismatch.

2. **Explicit version / CAS semantics** — if no current revision seam
   exists, UMS-05C must introduce one before Vault mutations are
   qualified.

This contract does **not** invent a third concurrency mechanism in
documentation. The chosen posture is recorded by the implementation
slice that proves it. The operator contract for editing stale state
is: a clear "this memory changed since you opened it" message, an offer
to re-read and re-attempt, and no silent overwrite.

---

## 11. Audit and receipts

Every authority-changing Vault action leaves a durable receipt that
includes, at minimum:

- authenticated account actor;
- stable memory identity;
- mutation source = `Vault`;
- action / reason token;
- previous authoritative values;
- new authoritative values;
- timestamp and resulting version;
- the originating Vault action / request reference where one exists.

The contract reuses the existing revision / audit authority rather
than creating a second audit ledger concept.

---

## 12. Privacy / operator boundary

- Account users inspect their own canonical memory only.
- Infrastructure / Host Operator status does **not** confer
  memory-content authority.
- Cross-account Vault access fails closed.
- Vault diagnostics do not leak memory content into generic telemetry.
- Personal Fact content carries the same boundary; the Personal Facts
  service is the only authority that can read or modify it through
  the Vault.

---

## 13. Empty, partial, and compatibility states

The Vault must render truthful empty / partial states:

| State | Truthful rendering |
| --- | --- |
| No memories exist for the account | "No memory yet." with no fabricated items |
| Only compatibility-projected memories exist | Show projection label explicitly |
| A subtype exposes fewer canonical dimensions | Show only the admitted dimensions; do not synthesize missing ones |
| Provenance is unavailable under an admitted legacy projection | Render projection; expose absence of provenance truthfully |
| A later-Campaign feature is not active | Disabled affordance + "Not available in this build" |

No fabricated values. No synthetic placeholders presented as truth.
No silent promotion of compatibility state into canonical state.

---

## 14. Capability matrix

The implementation boundary for UMS-05 is frozen by this matrix.

| Capability | Vault status | Authority | UMS slice | Writable? | Notes |
| --- | --- | --- | --- | --- | --- |
| List (account-scoped) | Live in UMS-05B | canonical memory read | UMS-05B | No | filters limited to canonical-backed dimensions |
| Detail (one record) | Live in UMS-05B | canonical memory read + Persona link read + provenance read | UMS-05B | No | extensions labelled non-authority |
| Provenance inspection | Live in UMS-05B | canonical `memory_provenance` | UMS-05B | No | external source IDs remain opaque |
| Stable Persona attribution inspection | Live in UMS-05B | canonical `memory_persona_links` against `persona_subjects` | UMS-05B | No | never derives from display names |
| Direct Vault creation (user-authored) | Live in UMS-05C | canonical user-authored memory service | UMS-05C | Yes | enters approved + active per UMS contract for explicit user-authored memory |
| Review action (approve / reject / dispute) | Live in UMS-05C | subtype-specific review service (Personal Facts review for fact species) | UMS-05C | Yes | Personal Facts delegates |
| Content correction | Live in UMS-05C | canonical revision service | UMS-05C | Yes | revisioned; previous values in receipt |
| Project scope change | Live in UMS-05C | canonical scope mutation service | UMS-05C | Yes | provenance noted |
| Persona attribution change | Live in UMS-05C | canonical Persona link service | UMS-05C | Yes | stable Persona subject only |
| Pin / unpin | Live in UMS-05C | canonical pin service | UMS-05C | Yes | affects priority only |
| Hold / release hold | Live in UMS-05C | canonical hold service | UMS-05C | Yes | suspends decay only |
| Retire | Live in UMS-05C | canonical retirement service | UMS-05C | Yes | reversible soft removal |
| Restore from retirement | Live in UMS-05C | canonical retirement service | UMS-05C | Yes | re-instatement |
| Persona-aware recall grant | **Deferred** | not in Vault | UMS-07 | n/a | UI may show disabled affordance |
| Explicit chat remember / forget / edit command | **Deferred** | not in Vault | UMS-06 | n/a | UI may show disabled affordance |
| External corpus import | **Deferred** | not in Vault | UMS-08 | n/a | not exposed |
| Automatic suggestion acceptance | **Deferred** | not in Vault | UMS-09 | n/a | not exposed |
| Heat / activation projection | **Deferred** | not in Vault | UMS-10 | n/a | not exposed |
| Permanent erasure | **Deferred** | not in Vault | UMS-11 | n/a | no live purge action |
| Ambient eligibility override | **Never** | n/a | n/a | n/a | always computed |
| Cross-account Vault access | **Never** | n/a | n/a | n/a | fails closed |
| Host Operator memory-content read | **Never** | n/a | n/a | n/a | fails closed |

This matrix is the UMS-05 implementation boundary. Any future change
that wants to flip a row from `Live` to `Deferred`, add a row, or
introduce a new capability must do so via a later Campaign slice and
its own contract update.

---

## 15. Implementation slices

UMS-05 is decomposed into bounded dependency order:

| Slice | Scope |
| --- | --- |
| **UMS-05A** | Memory Vault operator contract (this task) |
| **UMS-05B** | Vault backend read projection — account-scoped list, detail, filters, provenance / Persona readback; **no writes** |
| **UMS-05C** | Vault direct human mutation service — canonical direct creation, supported review / edit / scope / Persona / pin / hold / retire / restore actions, revision / receipt, Personal Facts delegation; **no UI yet** |
| **UMS-05D** | Vault frontend / operator surface — list, detail, filters, mutation controls, truthful disabled / deferred states |
| **UMS-05E** | Integrated PostgreSQL + frontend qualification — account isolation, read truth, mutation readback, stale-write / fail-closed behavior, operator-truth closeout |

Only **UMS-05B** is authorized immediately after UMS-05A. UMS-05C/05D/05E
remain NOT AUTHORIZED until UMS-05B qualifies the read surface.

If repository discovery proves this dependency order wrong, UMS-05B
must document the reason before any later slice starts; the Campaign
order is not silently reshuffled.

---

## Doctrinal reaffirmation

The Vault inherits and does not alter the governing doctrine:

- Account owns.
- Project scopes.
- Persona attributes.
- User approves.
- Pinning prioritizes.
- Holding suspends decay.
- The router widens only on explicit user intent.
- Every borrowed memory keeps its attribution.
- Storage does not imply ambient influence.
- Recall does not imply approval.
- Approval does not imply scope widening.
- Project scope does not imply Persona attribution.
- Persona attribution does not imply retrieval authority.
- Ambient eligibility is computed, never written.

---

## Closure

```text
UMS05A_MEMORY_VAULT_OPERATOR_CONTRACT_FROZEN

UMS-05B VAULT BACKEND READ PROJECTION AUTHORIZED
UMS-05C+ NOT AUTHORIZED
UMS-06+ NOT AUTHORIZED
```

The Memory Vault runtime is not implemented by this contract. It is
implementation-ready. UMS-05B is the next authorized slice.
