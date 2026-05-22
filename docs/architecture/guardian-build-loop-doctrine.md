# Guardian Build Loop Doctrine

Purpose: define the canonical end-to-end doctrine for Guardian-mediated build work in Codexify so Unity Audit, delegation, coding-worker execution, Codex Runner, Pi-style harnesses, command-bus authority, proof surfaces, and human review all map to one bounded governance loop instead of competing loop names.

Last updated: 2026-05-22

Source anchors:
- `docs/architecture/00-current-state.md`
- `docs/architecture/README.md`
- `docs/architecture/unity-audit-doctrine.md`
- `docs/architecture/agent-protocol-operations.md`
- `docs/architecture/self-extending-agent-plugin-system.md`
- `docs/architecture/agent-tool-loop-contract.md`
- `docs/architecture/pi-invocation-boundary-contract.md`
- `docs/architecture/chat-runtime-contract.md`
- `docs/architecture/runtime-protocol-token-contract.md`
- `docs/architecture/account-export-restore-contract.md`
- `docs/architecture/flows.md`
- `docs/architecture/delegation-runtime.md`
- `docs/architecture/delegation-operator-manual.md`
- `docs/Ops/SOLO_OPERATOR_CODING_WORKER_RUNBOOK.md`
- `guardian/routes/agent_orchestration.py`
- `guardian/workers/coding_worker.py`
- `guardian/agents/store.py`
- `guardian/agents/adapters/__init__.py`
- `guardian/agents/test_results.py`

## Classification

- Classification: Aligned with existing ADR(s)
- Governing ADRs/contracts:
  - Unity Audit doctrine
  - Agent Protocol Operations Index
  - Self-Extending Agent Plugin System / ADR-010
  - Agent Tool Loop Contract
  - Pi Invocation Boundary Contract
  - Chat Runtime Contract
  - Runtime Protocol Token Contract
  - Account Export + Restore Contract
  - Current-state release truth doctrine
  - Solo Operator Coding Worker Runbook
- Brief reason:
  - This consolidates overlapping doctrine around an existing bounded coding-worker substrate without changing runtime behavior.

## Purpose

Codexify has accumulated multiple nearby concepts for build and delegation work:

- Unity Audit
- Guardian delegation
- Codex Runner
- coding-worker execution
- Pi invocation
- command-bus authority
- future self-build behavior

These concepts are related, but they are not interchangeable. This document makes one doctrine canonical:

- `Guardian Build Loop` is the umbrella governance pipeline.
- Other documents describe inputs, authority seams, execution harnesses, proof surfaces, or future boundary contracts inside that loop.

This document does not introduce a new runtime subsystem. It is a doctrine consolidation over existing bounded runtime seams and existing doctrine.

## Canonical Definitions

### Guardian Build Loop

The Guardian Build Loop is Codexify's umbrella governance pipeline for supervised build work. It spans intake, diagnosis, proposal framing, packaging, review, delegation, execution, validation, proof, result return, and durable recordkeeping.

Guardian owns:

- policy
- identity and provenance boundaries
- authority to delegate or refuse
- source-thread lineage
- result return semantics
- proof interpretation

### Unity Audit

Unity Audit is the diagnosis and coherence input to the loop. It helps detect fragmentation across runtime truth, doctrine, operator reality, and public narrative. It is not an execution harness and not an approval authority.

### Guardian Delegation

Guardian Delegation is the authority and lineage seam inside the loop. It governs:

- who may delegate
- what request lineage is required
- how supervised review works
- how results must return to the source thread or durable artifact layer

Delegation is not the execution substrate. It is the governance handoff and result-return contract.

### Codex Runner / Coding Worker

Codex Runner and the coding-worker path are the execution harness and adapter substrate already present in the repo. They are the bounded mechanism that can:

- select an adapter
- enqueue execution on Redis
- run inside the coding worker
- enforce mutation scope
- run bounded validation retries
- optionally isolate work in a disposable worktree
- capture patch artifacts
- optionally commit after green when explicitly enabled and lease-bound

They do not replace Guardian authority.

### Pi Codex Runner

Pi Codex Runner is one possible adapter or harness path under the execution substrate. It is not the authority model, not the governance loop, and not the definition of Guardian delegation.

### Command Bus

The command bus is the bounded internal command authority lane. It remains the canonical path for Codexify-owned actions and must not be bypassed by Pi-like harnesses or future build-loop language.

### Human Review Gate

Human review is the required approval boundary for architecture-impacting and release-impacting changes. Human review is a governance requirement of the loop, not an optional UX detail.

### Commit-After-Green

Commit-after-green is an opt-in backend seam inside the coding-worker substrate. It is not general autonomous release behavior, not auto-merge, and not release proof.

### Patch Artifacts

Patch artifacts are review evidence captured from isolated runs. They are not auto-apply semantics, not promotion into the operator checkout, and not release proof.

## Direct Distinctions

### Guardian Build Loop vs Codex Runner

- Guardian Build Loop is the end-to-end governance pattern.
- Codex Runner is one execution substrate inside that loop.
- The loop decides whether, why, and under which policy a run may happen.
- The runner executes a bounded task after intake and delegation have already happened.

### Guardian Build Loop vs Guardian Delegation

- Guardian Build Loop is the full pipeline.
- Guardian Delegation is one phase boundary inside the loop.
- Delegation handles authority, lineage, review posture, and result-return obligations.
- The loop still includes diagnosis, packaging, execution, proof, and recordkeeping beyond delegation itself.

### Pi Invocation Boundary vs Pi Codex Runner Adapter Execution

- Pi Invocation Boundary is the doctrine and validation contract for future Pi-like harness invocation.
- Pi Codex Runner adapter execution is one concrete adapter path in the current coding-worker substrate when present and selected.
- The boundary says what must remain true about Guardian ownership, command authority, and lineage.
- The adapter is only a harness implementation choice; it does not redefine policy or provenance.

## Current Runtime Truth

The repo already contains a bounded coding-worker execution substrate with:

- `POST /api/agents/coding/execute` route in `guardian/routes/agent_orchestration.py`
- coding execution queue via Redis
- `CodingWorker` in `guardian/workers/coding_worker.py`
- `adapter_kind` selection with alias normalization and fail-closed unknown adapters
- `codex`, `claudecode`, and `pi_codex_runner` adapter semantics when present
- `AgentStore.store_coding_result()` persistence and result-return semantics
- normalized validation result contracts in `guardian/agents/test_results.py`
- mutation scope guard
- bounded validation retry
- optional worktree isolation
- patch artifact capture for isolated runs
- opt-in commit-after-green seam

Current ownership truth:

- Guardian remains the owner of intake, policy, lineage, result return, and durable recordkeeping.
- The coding-worker substrate is an execution harness, not an autonomous authority.
- Human review remains required for architecture-impacting and release-impacting changes.
- Runtime proof remains separate from docs, patch artifacts, validation success, and coding-worker success.

## What Is Already Implemented

- Guardian-owned coding-task intake and run creation
- deployment-spec persistence of adapter and review settings
- queued coding execution
- registered adapter selection
- coding-result persistence and source-thread return path
- normalized validation result contracts
- bounded validation retry
- mutation scope guard
- optional worktree lease resolution
- optional disposable worktree isolation
- patch artifact capture for isolated runs
- opt-in commit-after-green inside lease-bound worktrees

## What Remains Doctrine Only

- a fully autonomous self-build loop
- recursive or self-authorizing agent authority
- release signoff from worker success alone
- a generalized self-modification runtime
- automatic merge or branch-push behavior
- Pi invocation as a live fully implemented external harness boundary
- any doctrine that collapses Guardian authority into adapter choice

## Non-Goals / Not Yet True

This doctrine does not claim:

- autonomous self-modification
- unbounded retry until green
- auto-merge
- branch push
- silent promotion into the operator checkout
- release-readiness proof from coding-worker success alone
- bypass of ADR review
- bypass of human review
- recursive tool or agent loop authority

## Duplication Control

- Do not create new loop names unless they introduce a genuinely new runtime contract.
- Prefer `adapter` or `harness` for execution backends.
- Prefer `Guardian Build Loop` for the end-to-end governance pattern.
- Future docs must map new execution systems back to this loop.
- Existing Codex Runner, Pi, and delegation docs should be cross-referenced rather than redefined.

## Canonical Phases

| Phase | Owner | Input | Output | Allowed side effects | Prohibited side effects | Proof surface | Current implementation status |
|---|---|---|---|---|---|---|---|
| `1. Intake` | Guardian route and source thread boundary | Authored request, source thread/message lineage, scoped intent | Bounded intake envelope or rejected request | Create deployment/run/task intake records, record policy inputs | Direct repo mutation, silent approval, bypass of lineage | `guardian/routes/agent_orchestration.py`, deployment spec, run row | `implemented` |
| `2. Diagnose` | Guardian plus Unity Audit inputs | Current-state truth, architecture docs, operator evidence, source request | Diagnosis of scope, risk, coherence, and needed seams | Read docs, inspect runtime truth, classify risk | Treat diagnosis as execution, widen runtime claims | `00-current-state.md`, Unity Audit, architecture docs | `partial` |
| `3. Propose` | Guardian planning layer | Diagnosis, governing contracts, bounded request | Proposed plan, execution framing, review scope | Draft proposals, bounded specs, artifact planning | Silent execution, hidden authority expansion | architecture docs, task/campaign artifacts where present | `partial` |
| `4. Package` | Guardian packaging layer | Approved proposal, execution parameters, permission policy | Deployment spec, run payload, adapter choice, validation settings | Persist deployment spec, record adapter and permission posture | Mutate repo before delegation/execution | `guardian/routes/agent_orchestration.py`, deployment spec hash | `implemented` |
| `5. Review` | Human operator with Guardian support | Proposal, package, scope, architecture impact | Approval, refusal, or narrowed delegation | Record supervised trust state, keep human review requirement explicit | Auto-approve architecture-impacting work, bypass review | delegation docs, deployment trust state, current-state doctrine | `partial` |
| `6. Delegate` | Guardian delegation seam | Approved package, lineage, supervision posture | Run creation and governed handoff | Create run, emit created event, enqueue execution | Treat acceptance as completion, orphan source linkage | `guardian/routes/agent_orchestration.py`, `delegation-runtime.md`, run events | `implemented` |
| `7. Execute` | Coding worker plus selected adapter | Enqueued coding task, adapter kind, cwd/worktree context, permission policy | Adapter result, artifacts, changed paths, execution metadata | Run bounded adapter execution, optional isolated worktree, lease heartbeat | Bypass Guardian authority, unbounded recursion, silent promotion into operator checkout | `guardian/workers/coding_worker.py`, adapter registry, queue events | `implemented` |
| `8. Validate` | Coding worker validation seam | Success-like adapter result, validation command, permission posture | Normalized validation result and bounded retry decision | Run one supervised validation command per attempt, bounded retry, mutation-scope inspection | Retry until green, parse raw logs as contract truth, ignore scope violations | `guardian/agents/test_results.py`, worker validation events, mutation guard metadata | `implemented` |
| `9. Prove` | Guardian proof interpretation plus operator review | Validation result, patch artifact, task outcome, current-state truth | Proof posture: code-path only, test-backed, or live-runtime evidence | Capture patch artifacts, emit bounded evidence, compare against current-state truth | Claim release proof from worker success alone, claim live proof from docs only | patch manifest, validation result, current-state docs, live proof artifacts when present | `partial` |
| `10. Return` | Guardian result-return seam | Terminal worker result with lineage | Source-thread summary and durable coding-result record | Persist coding result, inject bounded result back into source thread when lineage exists | Publish orphaned result, collapse lineage, bypass Guardian | `guardian/agents/store.py`, source-thread message, result artifacts | `implemented` |
| `11. Record` | Guardian persistence and audit layer | Intake, execution, validation, proof, return metadata | Durable run history, artifacts, lineage, review evidence | Persist run/result metadata and artifact references | Treat transient events as sole truth, erase provenance | `AgentStore`, run rows, artifacts, export/restore doctrine | `implemented` |

## Minimal Viable Network

Nodes:

- source thread and message
- Guardian backend
- Postgres
- Redis queue and task-event transport
- coding worker
- selected adapter or harness
- optional isolated worktree or lease-bound worktree
- human reviewer

Trust boundaries:

- user and source-thread boundary
- Guardian policy boundary
- queue and worker boundary
- adapter or harness boundary
- filesystem or worktree mutation boundary
- human review and approval boundary

Threat model:

- honest-but-buggy worker or adapter
- stale or degraded queue visibility
- mutation outside approved scope
- missing or broken lineage
- overclaiming proof from partial evidence

What breaks first:

- route acceptance can succeed while downstream execution fails
- execution can succeed while visibility degrades
- validation can pass while proof remains insufficient for release claims
- patch artifacts can exist while human review is still pending

## Invariants

- Do not implement runtime behavior in this doctrine.
- Do not add routes, workers, DB tables, command-bus commands, or UI.
- Do not introduce another competing loop name.
- Do not imply autonomous self-modification exists.
- Do not widen beta release claims.
- Do not weaken Guardian authority, provenance, identity, command-bus, or provider boundaries.
- Do not treat patch artifacts, validation success, or commit-after-green as release proof.

## Current-Truth Anchors

What is true now:

- Codexify has multiple partial loop doctrines and execution seams.
- The repo already proves a partial coding-worker and Codex Runner substrate.
- Guardian remains the authority, policy, lineage, and result-return owner.
- Human review remains required for architecture-impacting and release-impacting changes.
- Runtime proof remains separate from docs and coding-worker success.

What this document does not change:

- no new runtime behavior
- no new release claim
- no new autonomous loop
- no change to supported-path truth in `00-current-state.md`

## Related Reading

- [Unity Audit Doctrine](./unity-audit-doctrine.md)
- [Delegation Runtime Contract](./delegation-runtime.md)
- [Delegation Operator Manual](./delegation-operator-manual.md)
- [Pi Invocation Boundary Contract](./pi-invocation-boundary-contract.md)
- [Agent Tool Loop Contract](./agent-tool-loop-contract.md)
- [Self-Extending Agent Plugin System](./self-extending-agent-plugin-system.md)
- [Solo Operator Coding Worker Runbook](../Ops/SOLO_OPERATOR_CODING_WORKER_RUNBOOK.md)
