# Project Pulse Contract Follow-Through

## Purpose

This document converts the existing Project Pulse read-only contract into a
small implementation-readiness map after the resume gate and LFS fixture
cleanup proof. It identifies the next safe slice without implementing Project
Pulse or creating a new runtime surface.

## Status

This is **docs-only architecture follow-through**.

- This document does not implement Project Pulse.
- No runtime behavior is implemented.
- No route, service, schema, migration, worker, UI, command bus, provider,
  retrieval, graph, browser, export/restore, or write path is added.
- This document does not widen supported beta.

## Source contracts read

- `docs/architecture/00-current-state.md`
- `docs/architecture/adr/adr-index.md`
- `docs/architecture/README.md`
- `docs/architecture/continuity-protocol-suite.md`
- `docs/architecture/continuity-token-domain-proposal.md`
- `docs/architecture/continuity-storage-schema-proposal.md`
- `docs/architecture/continuity-operator-diagnostics-truth-surface-contract.md`
- `docs/architecture/continuity-operator-readback-route-contract.md`
- `docs/architecture/continuity-operator-state-commit-link-readback-contract.md`
- `docs/architecture/continuity-write-action-contract.md`
- `docs/architecture/agent-protocol-operations.md`
- `docs/architecture/data-and-storage.md`
- `docs/architecture/modules-and-ownership.md`
- `docs/architecture/project-pulse-read-only-contract.md`
- `docs/guardian/work-briefs/2026-07-12/project-pulse-resume-gate.md`
- `docs/guardian/work-briefs/2026-07-12/lfs-audit-fixture-cleanup-proof.md`

## Resume prerequisites

- PR #565 produced a Project Pulse resume gate and held on unrelated fixture
  drift.
- PR #568 proved the fixture drift condition clear with `Outcome: go`.
- Project Pulse may now proceed only through one explicit follow-through slice
  at a time.

The cleanup proof clears the specific resume condition. It does not prove
Project Pulse runtime readiness, supported-path health, or release approval.

## Current truth

- Project Pulse exists only as
  `docs/architecture/project-pulse-read-only-contract.md`.
- It is a future read-only interpretive brief surface.
- It may conceptually read governed Continuity records only after
  implementation is separately authorized.
- The current read posture is exact-ID reads only through governed Continuity
  read surfaces.
- It must not list, search, query, or paginate Continuity records yet.
- It must not write Continuity state.
- It must not mutate memory.
- It must not call providers.
- It must not alter context broker behavior.
- It must not become UI or supported beta in this task.

## What is not yet true

- No Project Pulse output artifact is registered or implemented.
- No Project Pulse service, route, CLI, UI, storage, migration, worker, or
  runtime adapter exists.
- No Project Pulse exact-ID proof fixture exists.
- No Project Pulse implementation target has been inspected and documented as
  the bounded next task.
- No Project Pulse behavior has been proven on the supported local Compose
  path.

## Existing Project Pulse contract summary

The read-only contract defines Project Pulse as interpretation over governed
Continuity records, not as a storage layer, write action, compiler, diagnostics
replacement, chat-runtime feature, or provider-backed summarizer. Its current
read model is adapter-only and exact-ID-only. It requires provenance,
freshness and missing-evidence handling, explicit confidence boundaries, and
fail-closed behavior. It keeps graph, browser, provider, worker, retrieval,
command-bus, export/restore, and supported-beta behavior outside the surface.

## Candidate next slices

### Define Project Pulse output artifact schema

- **Lane:** architecture-impact
- **What it would change:** Produce a docs-only candidate artifact contract
  for a future Pulse brief, including provenance, freshness, confidence, and
  non-claim fields.
- **What it must not change:** No Pydantic model, API response, route, UI,
  storage schema, token registry, migration, or runtime behavior.
- **Validation surface:** Contract review against the read-only contract,
  ADR-030/031, token-domain proposal, `00-current-state.md`, and docs
  validation.
- **Risk level:** medium

### Inspect Project Pulse implementation targets

- **Lane:** proof
- **What it would change:** Produce a read-only inspection/proof document
  mapping current Continuity persistence, exact-ID readback, diagnostics, and
  operator-test seams that a future implementation would need to use.
- **What it must not change:** No runtime files, route registration, adapter
  behavior, schema, migration, service, UI, CLI, or Project Pulse code.
- **Validation surface:** Source-path inventory, contract-to-target mapping,
  negative-boundary checks, `git diff --check`, and docs validation.
- **Risk level:** low

### Define Project Pulse exact-ID read proof fixture

- **Lane:** proof
- **What it would change:** Define a static, bounded fixture shape for proving
  one authorized exact-ID read and its missing-evidence or gate behavior.
- **What it must not change:** No runtime fixture loader, database seed,
  migration, route, service, query/list behavior, or Continuity write.
- **Validation surface:** Fixture shape review against the readback contracts,
  provenance boundaries, redaction rules, and static/docs validation.
- **Risk level:** low

### Add Project Pulse read-only service skeleton

- **Lane:** architecture-impact
- **What it would change:** Add a future service boundary for adapter-only,
  exact-ID Project Pulse reads after implementation authorization.
- **What it must not change:** No route, UI, storage, migration, provider,
  retrieval, graph, browser, worker, command bus, write import, or supported
  beta activation.
- **Validation surface:** New architecture review, import and write-path
  audits, focused tests, and explicit runtime/profile proof. These checks are
  outside this task.
- **Risk level:** high

### Add Project Pulse diagnostics-only CLI probe

- **Lane:** standard
- **What it would change:** Add a bounded operator probe for inspecting
  diagnostics or a separately authorized exact-ID proof result.
- **What it must not change:** No Project Pulse narrative generation, record
  listing/search, provider call, write action, route activation, UI, or release
  claim.
- **Validation surface:** CLI contract tests, negative-boundary tests, profile
  quarantine checks, and operator-proof review.
- **Risk level:** medium

### Defer Project Pulse implementation

- **Lane:** docs
- **What it would change:** Preserve the current docs-only contract and record
  that no implementation slice is authorized yet.
- **What it must not change:** No runtime behavior, storage, routes, UI,
  workers, adapters, providers, retrieval, graph, browser, export/restore, or
  supported beta posture.
- **Validation surface:** Current-state alignment, docs validation, and proof
  that no implementation files changed.
- **Risk level:** low

## Recommended next slice

### Inspect Project Pulse implementation targets

Before adding schema, service, route, CLI, or UI, the repo should inspect
current Continuity adapters, readback routes, diagnostics routes, and available
test seams so implementation does not guess target files or accidentally bypass
the persistence adapter.

This recommendation authorizes inspection and proof documentation only. It does
not authorize implementation in the current task.

## Explicitly deferred slices

- Project Pulse output schema
- Project Pulse route
- Project Pulse service
- Project Pulse UI
- Project Pulse CLI
- Project Pulse storage
- Project Pulse migrations
- Project Pulse query/list/search behavior
- Project Pulse graph behavior
- Project Pulse browser-context behavior
- Project Pulse provider/model behavior
- Project Pulse command bus behavior
- Project Pulse export/restore behavior
- Project Pulse supported-beta activation

## Invariants

- Project Pulse remains read-only and exact-ID-only until a separate contract
  authorizes a broader read posture.
- Project Pulse must use the governed Continuity persistence boundary if it is
  later implemented.
- Project Pulse must not create, update, delete, or mutate Continuity records.
- Project Pulse must not mutate memory, invoke write actions, or invoke the
  Continuity compiler.
- Project Pulse must not call model providers or alter retrieval, router, or
  context broker behavior.
- Project Pulse must not read graph mounts, browser contexts, provider state,
  worker state, or live chat runtime without separate authorization.
- Diagnostics counts and gate flags must not be converted into narrative
  project truth.
- Docs, stubs, tests, or route presence must not be treated as supported beta
  proof.
- `docs/architecture/00-current-state.md` remains authoritative for release
  truth.

## Proof surface for the recommended next slice

The next task should be a read-only inspection/proof document, not
implementation. It should name and map the current target seams without
editing them:

- Continuity persistence adapter files
- Continuity exact-ID readback routes
- Continuity diagnostics route
- Continuity operator tests
- continuity architecture contracts
- the current Project Pulse read-only contract

The proof should record which targets are present, what each target proves,
which gates or profiles constrain it, and which boundaries remain unproven. It
must not add a route, service, schema, fixture loader, CLI, test behavior, or
runtime import.

## Documentation follow-through

- Added this follow-through map after the PR #565 resume gate and PR #568 LFS
  cleanup proof.
- Added a pointer from the Project Pulse read-only contract to this map.
- Added the map to the architecture README doc map with its inspection-first
  and docs-only boundary.
- Added a bounded current-state note recording the inspection-first next step.
- No ADR was created or changed; the existing ADR alignment is recorded below.

## ADR impact

**Classification:** Aligned with existing ADRs and architecture contracts.

Governing contracts are:

- ADR-015 Continuity Engine Working Set and Decay Contract
- ADR-016 Continuity Governance Surface Contract
- ADR-030 Continuity Protocol Suite Runtime Gate
- ADR-031 Continuity Phase A Storage Migration Gate
- `docs/architecture/project-pulse-read-only-contract.md`
- `docs/architecture/continuity-protocol-suite.md`
- `docs/architecture/continuity-storage-schema-proposal.md`
- `docs/architecture/continuity-operator-diagnostics-truth-surface-contract.md`
- `docs/architecture/continuity-operator-readback-route-contract.md`
- `docs/architecture/continuity-operator-state-commit-link-readback-contract.md`
- `docs/architecture/continuity-write-action-contract.md`
- `docs/architecture/00-current-state.md`

This document maps the next bounded follow-through path. It does not alter
accepted runtime contracts, create storage, add routes, or widen the supported
beta promise, so no new ADR is required.

## Release-truth boundary

`docs/architecture/00-current-state.md` remains authoritative for current
release truth. This document does not prove Project Pulse runtime readiness,
supported-path health, or release approval. It does not convert the resume gate
or LFS cleanup proof into Project Pulse implementation proof.

Project Pulse remains a docs-only, future read-only contract and is not part of
the supported beta surface. The recommended next slice is inspection of
implementation targets; any later schema, service, route, UI, or runtime work
requires its own scoped task, validation, and release-truth review.
