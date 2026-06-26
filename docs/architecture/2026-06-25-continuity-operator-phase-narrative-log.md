# Continuity Operator Phase Narrative Log

## Status

Narrative companion only. This is a human-readable build log for the reported
Continuity operator phase. It is **not** an architecture contract, **not** a
release claim, and **not** proof of runtime behavior.

This phase is documented as **test-only** and **quarantined**. The operator
surface is gated behind explicit profile + feature-flag + API-key requirements,
and it is deliberately excluded from the supported beta profile so supported
users cannot reach it.

Important honesty note (see the full list in `## Evidence Boundary`): the
governing ADRs, contracts, proof artifacts, and the regression test file that
this phase reportedly produced were **not present in this worktree** at the time
this narrative was written. This log therefore records the phase as it was
reported by the task brief and grounds the *why* in the continuity doctrine that
does exist (ADR-015 / ADR-016). It does **not** assert the six routes, the live
proof artifacts, or the regression test as verified runtime fact in this repo.
Where this narrative and the proof docs disagree, the proof docs and
`00-current-state.md` win; where proof docs are missing, the gap is an open
evidence boundary, not a silent claim.

## Audience

Written for Resonant Jones, Zac, future human collaborators, and future agents.
It is meant to be read *after* `00-current-state.md` and the continuity ADRs,
not instead of them. Treat it as the story around the proof, not as the proof.

## Why This Phase Existed

Codexify's chat runtime is thread-first. ADR-015 (`Continuity Engine Working Set
and Decay Contract`) names the precise gap: the system can preserve records, but
it has no governed, cross-thread continuity layer that preserves *continuity of
attention* across thread switches, project switches, and imported histories.

ADR-016 (`Continuity Governance Surface Contract`) adds the governance
discipline: any future continuity layer must stay user-governed, inspectable,
reversible, and provenance-aware. It must never collapse into a hidden heuristic,
a stale snapshot echo-chamber, imported-history overreach, persona/profile
confusion, or identity contamination.

The Continuity operator phase existed to give that doctrine a **bounded, gated,
operator-addressable surface** — a way to write, read back, and inspect
continuity state without turning continuity into ambient memory and without
widening the release promise. The phase was scoped to be test-only and
quarantined on purpose: the goal was to make continuity *inspectable by an
operator*, not *automatic for a user*.

## The Problem This Phase Solved

Before this phase, continuity was doctrine only. The phase set out to make a
minimum slice of continuity concrete enough to exercise, without crossing any of
these lines:

- continuity must not become ambient/automatic memory
- continuity must not widen the supported beta release promise
- continuity reads must not become search, retrieval, or graph traversal
- continuity diagnostics must not become a recommendation engine or "Project Pulse"
- the operator surface must not leak onto the supported beta profile

The phase's answer was: a small set of explicit operator write actions, a small
set of exact-ID readback routes, and aggregate diagnostics — all behind profile
gates that keep the supported beta profile locked out.

## Chronological Build Story

The story below is the reported arc of the phase. Each step that rests on a
proof artifact, route contract, or test file is flagged, because those backing
files were absent from this worktree (see `## Evidence Boundary`). The doctrine
steps (storage intent, governance intent, quarantine) are grounded in ADRs that
do exist.

### 1. Storage Became Real

The first move was to make continuity state something that could actually be
persisted rather than only described in doctrine. ADR-015 had defined continuity
as a *future* layer; the phase began turning "future layer" into a real storage
target that a write could land in and a readback could resolve.

The governing gate for this step was reportedly ADR-031 (`Continuity Phase A
Storage Migration Gate`), which was intended to keep the storage migration
bounded, explicit, and reversible. **That ADR was not present in this worktree**,
so this narrative cannot attest the migration's exact shape, tables, or
downgrade path. It is recorded here as the named storage gate, not as verified
schema.

### 2. Persistence Got an Explicit Adapter

Rather than letting continuity writes touch storage ad hoc, the phase reportedly
introduced an explicit persistence adapter — a typed seam between "an operator
wants to record continuity" and "a row/snapshot is durably written." The point
of an explicit adapter is the same pattern the graph lane already follows
(ADR-019 style): keep the write behind a contract so the surface never silently
couples to storage internals. The adapter definition itself was not located in
this worktree, so it is listed as an evidence boundary.

### 3. Writes Became Named Operator Actions

This is the conceptual heart of the phase. Continuity writes were framed as
**named operator actions**, not as free-form memory appends or as something the
chat runtime emits automatically.

The flagship concept is the **Reality Stamp**: an **explicit, operator-initiated
write** that stamps a continuity record with its reality/provenance. Reality
Stamp is deliberately **not ambient memory**:

- it is not written automatically by chat turns
- it is not emitted by workers, the command bus, providers, retrieval, browser
  activity, heartbeats, tools, or sync
- it is not shared/dyadic runtime state
- it is an operator-authored stamp with explicit provenance, not the system
  silently remembering on the user's behalf

The defining contract for this was reportedly `continuity-write-action-contract.md`.
**That contract was not present in this worktree**, so this narrative describes
Reality Stamp at the conceptual level the doctrine supports and does not invent
field-level schema, request bodies, or token vocabularies for it.

### 4. Six Operator Routes Became Inspectable

The phase reportedly exposed a **six-route operator surface** so that continuity
could be written and read back under inspection. The route set was meant to stay
narrow and inspection-oriented. Based on the named contracts, four route roles
can be described faithfully:

| # | Route role (reported) | Intended payload boundary |
|---|------------------------|---------------------------|
| 1 | **Write / Reality Stamp action** | Accepts an explicit, operator-authored continuity stamp; returns a commit identifier/link. Boundary: explicit write only — never ambient memory, never chat-turn emission. |
| 2 | **Exact-ID readback** | Returns a single continuity record by exact identifier. Boundary: inspection tool only — not search, not retrieval, not discovery, not graph traversal, not relationship expansion. |
| 3 | **State / commit-link readback** | Resolves a commit link to its continuity state. Boundary: exact-ID resolution only — does not expand neighbors or walk relationships. |
| 4 | **Aggregate diagnostics** | Returns aggregate operator truth (what continuity exists, at what coverage). Boundary: a summary of what is present — not a recommendation engine, not an action proposer, not Project Pulse. |

Routes 5 and 6, plus the concrete HTTP paths, exact request/response schemas, and
status tokens for all six, live in the route contract
(`continuity-operator-readback-route-contract.md`,
`continuity-operator-state-commit-link-readback-contract.md`) and the surface
test (`tests/continuity/test_continuity_operator_six_route_surface.py`).
**None of those files were present in this worktree**, so the two unnamed routes
and every concrete binding are recorded as an evidence boundary rather than
asserted here. This table describes *intended roles and boundaries*, not
verified route contracts.

### 5. Profile Quarantine Kept the Gates Locked

This is the one part of the phase that is backed by real, present code.
Codexify already has a supported-profile system with quarantine enforcement
(`guardian/core/supported_profile.py` and the supported-profile / quarantine
test suite, including the supported beta profile `v1-local-core-web-mcp`).

The phase reportedly relied on two profile postures:

- a **`test-continuity` profile** that exposes the operator surface only when a
  feature flag and API-key requirement are both met
- the **supported beta profile (`v1-local-core-web-mcp`)** that **quarantines**
  the operator routes so they cannot be reached on the supported path

Profile quarantine is the reason **supported beta cannot accidentally expose the
operator routes**. It is the structural guarantee that route presence does not
equal release support: the routes can exist in the codebase and still be
unreachable by any supported user. (The `test-continuity` profile wiring that
reportedly exposes the operator surface was not located as a distinct continuity
surface in this worktree; the quarantine mechanism itself, however, is real and
tested.)

### 6. Proof and Regression Guardrails Closed the Loop

The phase reportedly closed the loop with a proof and guardrail set. As conveyed
by the task brief, the intended proof surface included:

- six live proof artifacts
- a regression guardrail test file
- a hardening rerun
- a proof-chain map
- a current-state update
- a documentation alignment audit
- a milestone handoff

**None of these proof/audit/handoff artifacts were present in this worktree.**
Specifically missing: the proof-chain map
(`continuity-operator-loop-proof-chain.md`), the milestone handoff
(`2026-06-25-continuity-operator-six-route-milestone-handoff.md`), the hardening
rerun (`2026-06-25-continuity-operator-six-route-hardening-regression-rerun.md`),
the documentation alignment audit
(`2026-06-25-continuity-operator-documentation-alignment-audit.md`), and the
regression test (`tests/continuity/test_continuity_operator_six_route_surface.py`).

This narrative does **not** claim those proofs were run or passed. Their absence
is the central evidence boundary of this log (see below).

## What Exists Now

Honest inventory, split by what is actually present versus what is reported but
unverified in this worktree.

**Genuinely present in this KB/repo:**

- This narrative log (the file you are reading).
- Continuity **doctrine**: ADR-015 (working set + decay) and ADR-016 (governance
  surface) — accepted, planning/contract level, above the thread-first chat
  runtime.
- A real supported-profile system with quarantine enforcement
  (`guardian/core/supported_profile.py`, supported-profile + quarantine tests,
  and the supported beta profile `v1-local-core-web-mcp`).
- `00-current-state.md` as the release-truth gate — and it does **not** list any
  Continuity operator surface as part of the current release promise.

**Reported by the phase but NOT present/verifiable in this worktree:**

- The six operator routes and their concrete bindings.
- The Reality Stamp write-action contract and schema.
- The persistence/storage adapter and the Phase A storage migration gate.
- The live proof artifacts, regression test, hardening rerun, proof-chain map,
  milestone handoff, and documentation alignment audit.
- Any `test-continuity` profile wiring as a distinct continuity operator surface.

## What This Does Not Mean

To keep release truth clean, state explicitly what this phase does **not** mean:

- This is **test-only** and **quarantined**.
- This is **not supported beta behavior**.
- This is **not user-facing UI**.
- This is **not Project Pulse**.
- This is **not export/restore inclusion** (continuity stamps are not part of the
  export/restore contract).
- This is **not list/search**.
- This is **not graph traversal** (exact-ID readback is not relationship walking).
- This is **not chat runtime continuity** (the chat runtime is still thread-first).
- This is **not** integration with worker, command bus, provider, retrieval,
  browser, sync, or any shared/dyadic runtime.
- Route presence is **not** release support.
- Reality Stamp is **not** automatic/ambient memory.
- Diagnostics are **not** a summary engine or action recommender.

## Why This Phase Matters

The phase matters because it tried to make continuity *addressable* before making
it *automatic*. By forcing continuity through explicit operator actions,
exact-ID readbacks, and aggregate diagnostics — all behind a quarantined profile
gate — the design keeps the system honest: nothing remembers on the user's
behalf until someone decides, explicitly, what remembering should mean. That is
the same discipline ADR-015/016 require, applied to a minimum inspectable slice.

Even with the evidence boundary below, the *shape* of the phase is valuable: it
isolates continuity writes from ambient memory, isolates readbacks from
search/traversal, and isolates the operator surface from the supported beta
profile.

## Why The Phase Stops Here

The phase stops at a deliberate boundary: a test-only, quarantined, exact-ID
operator surface with aggregate diagnostics. It does not cross into any of the
lanes listed in `## Safe Next Moves`, because each of those is a separate
release-affecting decision that needs its own contract, proof, and (where
relevant) supported-profile change.

Specifically, the phase stops before:

- turning the operator surface into supported beta behavior
- exposing any continuity UI to users
- letting chat turns, workers, providers, retrieval, browser, sync, or tools
  write continuity
- widening exact-ID readback into search/list/traversal
- promoting diagnostics into Project Pulse or any recommendation/action layer
- including continuity in export/restore

Stopping here is the safety property, not a limitation to be rushed past.

## Evidence Boundary

This section is load-bearing. The following required pre-read files were **not
present** in this worktree at authoring time. Per task rules, their contents were
**not invented**. They are listed so future collaborators can find or restore
them, and so this narrative is not mistaken for proof.

Missing governing ADRs:

- `docs/architecture/adr/030-continuity-protocol-suite-runtime-gate.md`
- `docs/architecture/adr/031-continuity-phase-a-storage-migration-gate.md`

Neither ADR appears in `docs/architecture/adr/adr-index.md`. The highest numbered
indexed ADRs are ADR-029, ADR-036, ADR-037; there is no ADR-030 or ADR-031 entry.

Missing operator contracts:

- `docs/architecture/continuity-write-action-contract.md`
- `docs/architecture/continuity-operator-readback-route-contract.md`
- `docs/architecture/continuity-operator-state-commit-link-readback-contract.md`

Missing proof / audit / handoff docs:

- `docs/architecture/continuity-operator-loop-proof-chain.md`
- `docs/architecture/2026-06-25-continuity-operator-six-route-milestone-handoff.md`
- `docs/architecture/2026-06-25-continuity-operator-six-route-hardening-regression-rerun.md`
- `docs/architecture/2026-06-25-continuity-operator-documentation-alignment-audit.md`

Missing test:

- `tests/continuity/test_continuity_operator_six_route_surface.py` (the
  `tests/continuity/` directory does not exist in this worktree).

Code search confirmed: there are no references to `continuity operator` or
`reality stamp` anywhere in `guardian/` or `tests/`, and there is no continuity
route file under `guardian/routes/`.

Because all of the above are missing, the following statements in this log are
**descriptions of reported/intended scope, not verified runtime fact**: the six
route names and bindings, the Reality Stamp schema, the persistence adapter, the
Phase A storage migration, the live proof artifacts, and the regression
guardrail. The only continuity material actually present is the ADR-015/ADR-016
doctrine; the only operator-adjacent mechanism actually present is the
supported-profile quarantine.

If a future task restores these files, this narrative should be re-grounded
against them and this section shortened accordingly.

## Safe Next Moves

These are named as **separate future lanes only**. This task does not select,
design, or implement any of them. Each needs its own contract, proof, and
release-truth update before it becomes real.

- **Pause and harden** — keep the surface test-only, harden the existing routes,
  and add more regression coverage without widening scope.
- **Export/restore continuity inclusion contract** — decide whether and how
  continuity stamps travel inside export/restore. Distinct contract; not implied
  by this phase.
- **Project Pulse contract** — if aggregate diagnostics should ever become a
  higher-level pulse/summary, that is a new contract and explicitly **not** what
  diagnostics are today.
- **List/search contract** — any discovery surface over continuity is a new,
  bounded contract; exact-ID readback must not silently become search.
- **Supported beta activation contract** — any path to letting the operator
  surface exist outside `test-continuity` is a release-affecting decision with
  its own proof and profile work.
- **Zac onboarding documentation** — a dedicated onboarding doc for operating
  the test-only surface, separate from this narrative.

## Bottom Line

The Continuity operator phase, as reported, made a minimum slice of continuity
inspectable through explicit operator writes (Reality Stamp), exact-ID
readbacks, and aggregate diagnostics — test-only and quarantined behind the
supported-profile gate so it cannot reach supported beta users. The *why* is
solidly grounded in the real ADR-015/ADR-016 continuity doctrine and the real
supported-profile quarantine code. The *proof*, however, currently lives in
files that are absent from this worktree, so this narrative is a companion to
evidence that still needs to be located or restored — it is not itself proof,
not a release claim, and not a widening of the current release promise. Treat
`00-current-state.md` as the gate; it does not yet list any Continuity operator
surface as shipped.
