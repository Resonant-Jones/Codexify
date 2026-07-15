# Project Pulse Implementation Target Inspection

## Purpose

This document records a read-only inspection of the existing Continuity
implementation seams that a future Project Pulse task would need to understand.
It maps current files, routes, adapters, tests, and contracts without
authorizing edits to those seams or implementing Project Pulse.

## Status

This is a **read-only inspection/proof document**.

- This document does not implement Project Pulse.
- No runtime behavior is implemented.
- No route, service, schema, migration, UI, CLI, worker, command bus, provider
  call, retrieval change, graph traversal, browser capture, export/restore,
  test, fixture, or write path is added.
- This document does not widen supported beta.

## Source contracts read

- docs/architecture/00-current-state.md
- docs/architecture/adr/adr-index.md
- docs/architecture/README.md
- docs/architecture/project-pulse-read-only-contract.md
- docs/architecture/project-pulse-contract-follow-through.md
- docs/architecture/continuity-protocol-suite.md
- docs/architecture/continuity-token-domain-proposal.md
- docs/architecture/continuity-storage-schema-proposal.md
- docs/architecture/continuity-persistence-adapter-contract.md
- docs/architecture/continuity-operator-readback-route-contract.md
- docs/architecture/continuity-operator-state-commit-link-readback-contract.md
- docs/architecture/continuity-operator-diagnostics-truth-surface-contract.md
- docs/architecture/continuity-write-action-contract.md
- docs/architecture/continuity-operator-loop-proof-chain.md
- docs/architecture/agent-protocol-operations.md
- docs/architecture/data-and-storage.md
- docs/architecture/modules-and-ownership.md

## Inspection commands

The following read-only searches and source inspections were run from the repo
root:

    git status --short --branch --untracked-files=all
    git log --oneline --decorate --graph --max-count=30
    git grep -n "Project Pulse" -- docs guardian frontend tests
    git grep -n "continuity" -- guardian tests docs/architecture | head -200
    find guardian -iname '*continuity*' -print | sort
    find tests -iname '*continuity*' -print | sort
    find docs -iname '*continuity*' -o -iname '*project*pulse*' | sort
    rg -n 'load_|list_|save_|link_|deleted_at|select\(' guardian/continuity/persistence.py
    rg -n '@router\.(get|post)|read_|operator_|diagnostics' guardian/routes/continuity_operator.py
    rg -n '^def test_|continuity_operator|readback|diagnostics|profile' tests/continuity

The branch was created from origin/main after the confirmed PR #582 merge
commit 179d80207434ecde3c224e8e2425feffda9351ce.

## Current Project Pulse truth

- Project Pulse is currently defined only by
  docs/architecture/project-pulse-read-only-contract.md and
  docs/architecture/project-pulse-contract-follow-through.md.
- No Project Pulse runtime implementation file, route, service, CLI, UI,
  worker, storage object, migration, or test exists.
- Project Pulse remains a future read-only interpretive surface, not a write
  path, compiler, diagnostics replacement, chat-runtime feature, or provider
  call site.
- The current Project Pulse read posture is exact-ID reads only through a
  governed Continuity read surface after separate authorization.
- Project Pulse must not list, search, query, paginate, traverse, mutate, or
  infer beyond available evidence.
- 00-current-state.md remains authoritative for release truth, and Project
  Pulse is not supported beta behavior.

## Target inventory

### Continuity persistence adapter files

- guardian/continuity/persistence.py — implemented Phase A persistence
  adapter. It contains writes plus load_reality_state,
  load_latest_reality_state, and list_reality_commits read methods.
- guardian/continuity/contracts.py — domain contracts and validation for
  Context Packets, Reality States, Reality Commits, provenance, and scope.
- guardian/db/models.py — persisted Continuity row models and soft-delete
  columns. It is an inspection anchor, not an authorized edit target here.
- docs/architecture/continuity-persistence-adapter-contract.md — governing
  adapter boundary and future read/write contract.

### Continuity exact-ID readback routes

- guardian/routes/continuity_operator.py — current operator route module with
  these exact-ID readbacks:
  - GET /api/operator/continuity/context-packets/{packet_id}
  - GET /api/operator/continuity/reality-states/{state_id}
  - GET /api/operator/continuity/reality-commits/{commit_id}
  - GET /api/operator/continuity/state-packet-links/{link_id}
- docs/architecture/continuity-operator-readback-route-contract.md — packet
  readback contract.
- docs/architecture/continuity-operator-state-commit-link-readback-contract.md
  — staged state, commit, and link readback contract.

### Continuity diagnostics route

- guardian/routes/continuity_operator.py —
  GET /api/operator/continuity/diagnostics reports profile, gate, aggregate
  count, and hard-false flag posture.
- docs/architecture/continuity-operator-diagnostics-truth-surface-contract.md
  — diagnostics-only boundary; no raw payloads, ID lists, summarization, or
  Project Pulse behavior.

### Continuity operator tests

The discovered operator proof and regression targets are:

- tests/continuity/test_persistence_adapter.py
- tests/continuity/test_continuity_operator_route.py
- tests/continuity/test_continuity_operator_readback_route.py
- tests/continuity/test_continuity_operator_diagnostics_route.py
- tests/continuity/test_continuity_operator_state_readback_route.py
- tests/continuity/test_continuity_operator_commit_readback_route.py
- tests/continuity/test_continuity_operator_link_readback_route.py
- tests/continuity/test_continuity_operator_profile_activation.py
- tests/continuity/test_continuity_operator_six_route_surface.py
- tests/continuity/test_contracts.py
- tests/continuity/test_phase_a_storage_schema.py
- tests/continuity/test_write_actions.py

No Project Pulse test target was found.

### Continuity architecture contracts

- docs/architecture/continuity-protocol-suite.md
- docs/architecture/continuity-token-domain-proposal.md
- docs/architecture/continuity-storage-schema-proposal.md
- docs/architecture/continuity-persistence-adapter-contract.md
- docs/architecture/continuity-operator-readback-route-contract.md
- docs/architecture/continuity-operator-state-commit-link-readback-contract.md
- docs/architecture/continuity-operator-diagnostics-truth-surface-contract.md
- docs/architecture/continuity-write-action-contract.md
- docs/architecture/continuity-operator-loop-proof-chain.md
- docs/architecture/adr/015-continuity-engine-working-set-and-decay-contract.md
- docs/architecture/adr/016-continuity-governance-surface-contract.md
- docs/architecture/adr/030-continuity-protocol-suite-runtime-gate.md
- docs/architecture/adr/031-continuity-phase-a-storage-migration-gate.md

### Project Pulse contracts

- docs/architecture/project-pulse-read-only-contract.md
- docs/architecture/project-pulse-contract-follow-through.md

No Project Pulse implementation target was found beyond these documentation
contracts.

## Target classification table

| Target | Category | Present? | Future role | Safe future use | Must not do | Notes |
|---|---|---:|---|---|---|---|
| docs/architecture/project-pulse-read-only-contract.md | Project Pulse contract | Yes | Governs interpretation, provenance, freshness, and read boundaries | Constrain any future output and read model | Implement runtime behavior or imply release support | Normative Project Pulse contract only |
| docs/architecture/project-pulse-contract-follow-through.md | Project Pulse contract | Yes | Sequences safe follow-through slices | Use as task-order and scope guard | Authorize implementation by itself | Recommends inspection before implementation |
| guardian/continuity/persistence.py; docs/architecture/continuity-persistence-adapter-contract.md | Persistence adapter | Yes | Owns governed Continuity persistence and future adapter reads | Use adapter-only, exact-ID reads after the adapter seam is aligned | Bypass the adapter or invoke write methods from Pulse | Adapter has state exact-ID read, scoped latest-state read, and commit listing; packet/commit/link exact-ID coverage is not complete |
| docs/architecture/continuity-write-action-contract.md; guardian/continuity/write_actions.py | Write boundary | Yes | Defines explicit writes that Pulse must never invoke | Use only as a negative import/call-site boundary | Create records, call write actions, or invoke compiler persistence | Four explicit write actions are implemented but remain outside Pulse |
| guardian/routes/continuity_operator.py; docs/architecture/continuity-operator-readback-route-contract.md | Exact-ID readback | Yes | Provides test-only operator readback evidence | Use route behavior and response semantics as proof references | Copy direct SQLAlchemy access into a future Pulse service | Current route methods query sessions directly; this does not satisfy Pulse adapter-only contract |
| docs/architecture/continuity-operator-state-commit-link-readback-contract.md | State/commit/link readback | Yes | Defines staged exact-ID response and no-expansion semantics | Use response fields, missing-record behavior, and hard-false flags as constraints | Add traversal, list/search, or payload expansion | Routes are implemented in the shared operator module |
| docs/architecture/continuity-operator-diagnostics-truth-surface-contract.md; guardian/routes/continuity_operator.py | Diagnostics | Yes | Defines aggregate operator truth and gate posture | Use hard-false and no-write signals as boundary checks | Turn counts into narrative or combine diagnostics with Pulse | project_pulse_enabled remains false |
| docs/architecture/continuity-operator-loop-proof-chain.md | Proof chain | Yes | Maps six-route implementation and live-proof boundaries | Use to identify proven versus unproven seams | Treat test-only proof as supported beta or Pulse proof | Six routes are quarantined under test-continuity |
| tests/continuity/ operator tests listed above | Operator tests | Yes | Guard response shape, profile gates, auth, no-write, and route inventory | Use as future regression/proof seams after separate authorization | Add or change tests in this task | No Project Pulse tests exist |
| docs/architecture/00-current-state.md | Release truth | Yes | Controls supported-path and beta claims | Check before and after any future task | Infer release support from docs, routes, or tests | Remains authoritative |

## Positive implementation seams

These are seams a future implementation task may inspect or use after a new
task authorizes implementation. They are not edits authorized by this task:

- Adapter-only exact-ID reads, with the adapter contract as the governing
  dependency boundary.
- No-write diagnostics posture: counts and gate state only, with no write,
  compiler, event, or Project Pulse call.
- Test-only profile gate behavior under test-continuity with
  CODEXIFY_ENABLE_CONTINUITY_OPERATOR_ROUTES=true.
- Hard-false flags for graph_used, runtime_event_published,
  project_pulse_enabled, and export_restore_enabled.
- Missing-record behavior using found=false without fabricating evidence.
- Provenance-preserving response fields on the readback contracts and
  persistence contract.
- Soft-delete-aware reads where existing adapter and route contracts require
  deleted_at IS NULL.
- Release-truth boundary checks through 00-current-state.md, profile
  quarantine, and the loop proof chain.

The current route implementation is useful proof evidence, but its direct
session.query(...) reads are not a positive Pulse service seam. The adapter
boundary must be resolved before future Pulse code can safely consume these
records.

## Forbidden implementation seams

Future Project Pulse work must not use or add:

- Direct SQLAlchemy reads that bypass the persistence adapter.
- Continuity write actions.
- Compiler persistence calls.
- List, search, query, or paginate behavior for Continuity records.
- Graph traversal.
- Browser context reads.
- Provider or model calls.
- Retrieval-router changes.
- Context broker injection.
- Command bus invocation.
- Cron or worker scheduling.
- Export/restore inclusion.
- Supported beta activation.
- UI exposure.

## Exact-ID read boundary

The current operator surface proves exact-ID readback for one packet, one
Reality State, one Reality Commit, or one state-packet link at a time. The
routes return found=false for missing or soft-deleted records and do not
expand linked records, traverse commit history, or perform graph lookups.

That route behavior is a proof reference, not permission to build Pulse on the
route module. The existing adapter's list_reality_commits(...) method is a
scoped list operation and therefore is not an allowed Project Pulse read seam
under the current exact-ID contract. A future task must first define or prove
the required adapter-level exact-ID methods and their response/provenance
mapping.

## Diagnostics boundary

GET /api/operator/continuity/diagnostics is an aggregate operator truth
surface. It reports profile and feature-flag posture, non-deleted row counts,
last packet timestamp, and hard-false flags. It does not return raw payloads,
packet ID lists, summaries, retrieval results, compiler output, provider state,
or Project Pulse output.

Diagnostics may verify that a route is quarantined or that no Project Pulse
surface is active. It must not be used as a narrative input or combined with
Project Pulse to manufacture project state.

## Persistence adapter boundary

The future Pulse read path must depend on ContinuityPersistenceAdapter and
the domain contracts in guardian/continuity/contracts.py. It must inherit
adapter validation, session, soft-delete, provenance, and error semantics. It
must not import ContinuityWriteActionService, write_actions.py, or compiler
persistence functions.

Inspection found a concrete boundary gap: persistence.py has
load_reality_state(...) and load_latest_reality_state(...), plus
list_reality_commits(...), while the operator readback routes directly query
the SQLAlchemy models for packet, state, commit, and link reads. The gap is
recorded here for a future contract/proof task; it is not repaired here.

## Test/proof surfaces

The existing proof surfaces are useful for future inspection and regression
planning:

- tests/continuity/test_persistence_adapter.py covers adapter result shapes,
  validation, provenance, soft-delete-aware reads, and persistence behavior.
- The four exact-ID route test files cover response shapes, found/missing
  behavior, hard-false flags, and live round-trip seams where Postgres is
  available.
- tests/continuity/test_continuity_operator_diagnostics_route.py covers
  diagnostics response and no-write posture.
- tests/continuity/test_continuity_operator_profile_activation.py covers
  profile and feature-flag quarantine.
- tests/continuity/test_continuity_operator_six_route_surface.py pins the
  six-route inventory, auth, profile boundary, and forbidden expansion.
- tests/continuity/test_contracts.py covers domain contract validation and
  import boundaries.
- docs/architecture/continuity-operator-loop-proof-chain.md consolidates
  the implementation and live-proof boundaries; it is not itself runtime
  proof.

No tests or fixtures are added or modified by this inspection task.

## Open questions

The following questions remain unresolved and would block later schema,
service, or route work:

- Should the adapter gain exact-ID methods for context packets, commits, and
  state-packet links, or should Project Pulse be limited to the exact state
  method already present?
- What domain-level response shape maps adapter rows to Pulse provenance,
  freshness, missing evidence, and confidence without exposing forbidden raw
  payloads or portable DB identity?
- Which future caller owns authorization and profile gating if Pulse is not an
  operator route?
- What canonical token registry entries, if any, are required for the future
  output artifact without inventing tokens inline?
- What freshness threshold and scope-resolution rules are authorized for a
  Pulse read, and where are conflicts between records surfaced?
- What live proof is required before any future Pulse route or UI can be
  described as supported behavior?

## Recommended next slice

### Define Project Pulse exact-ID read proof fixture

This is the safest next task because the inspection found identifiable target
seams but also a concrete adapter/route boundary mismatch. A docs/proof-only
fixture definition should pin one authorized exact-ID read, missing-record
behavior, provenance preservation, soft-delete handling, hard-false flags, and
the adapter-only expectation before output schema, service, route, or UI work is
considered.

That next task must remain static and proof-only. It must not add a fixture
loader, database seed, runtime service, route, or test behavior unless a later
task separately authorizes those changes.

## Explicit non-goals

- No Project Pulse runtime behavior.
- No route.
- No service.
- No schema.
- No migration.
- No UI.
- No CLI behavior.
- No worker or cron behavior.
- No command bus integration.
- No provider or model call.
- No retrieval or router behavior.
- No graph traversal.
- No browser capture.
- No export/restore behavior.
- No Project Pulse records.
- No Continuity record mutation.
- No Continuity write-action import or invocation.
- No tests.
- No fixtures.
- No supported-beta activation or release claim expansion.

## ADR impact

**Classification:** Aligned with existing ADRs and architecture contracts.

Governing ADRs and contracts:

- ADR-015 Continuity Engine Working Set and Decay Contract
- ADR-016 Continuity Governance Surface Contract
- ADR-030 Continuity Protocol Suite Runtime Gate
- ADR-031 Continuity Phase A Storage Migration Gate
- docs/architecture/project-pulse-read-only-contract.md
- docs/architecture/project-pulse-contract-follow-through.md
- docs/architecture/continuity-protocol-suite.md
- docs/architecture/continuity-persistence-adapter-contract.md
- docs/architecture/continuity-operator-readback-route-contract.md
- docs/architecture/continuity-operator-state-commit-link-readback-contract.md
- docs/architecture/continuity-operator-diagnostics-truth-surface-contract.md
- docs/architecture/continuity-write-action-contract.md
- docs/architecture/00-current-state.md

This task maps existing seams and records one adapter/route boundary blocker.
It does not alter an accepted runtime contract, add a schema or route, or
widen the supported beta promise. No new ADR is required.

## Release-truth boundary

docs/architecture/00-current-state.md remains authoritative. The existence
of guardian/continuity, operator routes, tests, live-proof documents, or
these inspection notes does not make Project Pulse supported beta behavior.

The Continuity operator surface remains test-only, API-key-gated, and profile
quarantined. Project Pulse remains docs-only, exact-ID-only by contract, and
unimplemented. This document is not runtime proof, release approval, or a
supported-path claim.

## Validation results

- Read-only target searches and source inspections: completed.
- No automated runtime tests apply; no tests were added or run.
- git diff --check: passed.
- test -f and required content checks: passed.
- python3 scripts/validate_docs.py: passed.
