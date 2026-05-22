Purpose: define the canonical Guardian Build Loop doctrine for Codexify so Unity Audit, delegation, coding-worker execution, Codex Runner, Pi-style harnesses, command-bus authority, human review, proof, and result return can be discussed as one governed pipeline without inventing a second competing loop.
Last updated: 2026-05-23
Source anchors:
- docs/architecture/00-current-state.md
- docs/architecture/README.md
- docs/architecture/unity-audit-doctrine.md
- docs/architecture/agent-protocol-operations.md
- docs/architecture/self-extending-agent-plugin-system.md
- docs/architecture/agent-tool-loop-contract.md
- docs/architecture/pi-invocation-boundary-contract.md
- docs/architecture/chat-runtime-contract.md
- docs/architecture/runtime-protocol-token-contract.md
- docs/architecture/account-export-restore-contract.md
- docs/architecture/flows.md
- docs/architecture/delegation-runtime.md
- docs/architecture/delegation-operator-manual.md
- docs/Ops/SOLO_OPERATOR_CODING_WORKER_RUNBOOK.md
- guardian/routes/agent_orchestration.py
- guardian/workers/coding_worker.py
- guardian/agents/store.py
- guardian/agents/adapters/__init__.py
- guardian/agents/test_results.py

# Guardian Build Loop Doctrine

## Classification

- Classification: aligned with existing ADRs and contracts
- Governing ADRs/contracts:
  - Unity Audit doctrine
  - Agent Protocol Operations Index
  - Self-Extending Agent Plugin System / ADR-010
  - Agent Tool Loop Contract
  - Pi Invocation Boundary Contract
  - Chat Runtime Contract
  - Runtime Protocol Token Contract
  - Account Export + Restore Contract
  - current-state release truth doctrine
  - Solo Operator Coding Worker Runbook
- Brief reason:
  - This consolidates overlapping doctrine around an existing bounded coding-worker substrate without changing runtime behavior, release rules, authority ownership, or identity boundaries.

## Why This Exists

Codexify now has multiple adjacent surfaces that can be mistaken for different "loops":

- Unity Audit
- Guardian Delegation
- Codex Runner naming
- coding-worker execution
- Pi invocation boundary docs
- command-bus tool execution
- future self-build or self-extension doctrine

Those surfaces are related, but they are not interchangeable. Without one canonical umbrella, the repo risks naming the same governed pipeline multiple times and quietly widening claims beyond current runtime proof.

The Guardian Build Loop is that umbrella.

## Canonical Definition

The `Guardian Build Loop` is the end-to-end governance pipeline by which Codexify:

1. accepts a build or coding request,
2. diagnoses what kind of change is being proposed,
3. packages bounded execution context,
4. delegates supervised work to a governed execution substrate,
5. validates and proves outcomes,
6. returns results through Guardian-owned lineage,
7. and records durable evidence for later review.

Guardian Build Loop is not a single worker, single adapter, single provider, or single automation primitive.

It is the umbrella pattern that keeps authority, provenance, review, execution, proof, and return semantics aligned.

## Relationship Map

| Surface | Canonical role in the Build Loop | What it is not |
|---|---|---|
| `Unity Audit` | Diagnosis and coherence input surface | Not execution authority, not runtime proof by itself |
| `Guardian Delegation` | Authority, lineage, policy, review, and result-return semantics | Not the execution harness itself |
| `Codex Runner / coding-worker substrate` | Execution harness and adapter substrate | Not the umbrella governance loop |
| `Pi Codex Runner` | One possible adapter or harness path | Not the authority model |
| `Command Bus` | Bounded internal command authority lane | Not a general autonomous build loop |
| `Human Review Gate` | Required approval boundary for architecture-impacting or release-impacting work | Not an optional cosmetic step |
| `Patch artifacts` | Review evidence from bounded execution | Not auto-apply, not release proof |
| `Commit-after-green` | Opt-in backend seam after bounded validation in approved paths | Not auto-merge, not release approval |

## Distinctions That Must Stay Explicit

### What is the difference between Guardian Build Loop and Codex Runner?

- `Guardian Build Loop` is the full governance pattern: intake, diagnosis, delegation, execution, validation, proof, result return, and recording.
- `Codex Runner` is execution substrate language for a worker or adapter path inside that loop.
- A runner can be swapped, extended, or added later. The Build Loop remains the governing pattern.

### What is the difference between Guardian Build Loop and Guardian Delegation?

- `Guardian Build Loop` includes diagnosis, packaging, proof, and recordkeeping around the whole change arc.
- `Guardian Delegation` is the authority and lineage contract for handing supervised work to an execution system and getting results back safely.
- Delegation is one governed phase family inside the Build Loop, not the entire loop.

### What is the difference between Pi Invocation Boundary and Pi Codex Runner adapter execution?

- `Pi Invocation Boundary` is the architecture contract that keeps Guardian ownership, provider separation, provenance, and command authority explicit.
- `Pi Codex Runner` is one adapter or harness implementation path that may execute inside that boundary when selected.
- The boundary defines what must remain true. The adapter is one execution backend that must obey that boundary.

### What is already implemented?

Implemented or partially implemented seams already exist for:

- `POST /api/agents/coding/execute` route intake
- Redis-backed coding execution queue
- `CodingWorker`
- deployment-spec-driven `adapter_kind` selection with alias normalization
- registered `codex`, `claudecode`, and `pi_codex_runner` adapter paths when present
- Guardian-owned coding-result persistence through `AgentStore.store_coding_result()`
- normalized validation result contracts in `guardian/agents/test_results.py`
- mutation scope guard
- bounded validation retry
- optional worktree lease binding
- optional detached worktree isolation
- patch artifact capture for isolated runs
- opt-in commit-after-green seam
- Guardian-owned result return into the source thread when lineage is available

### What remains doctrine only?

The following remain doctrine-only, partial, or explicitly future:

- autonomous self-modification
- recursive build or remediation authority
- unbounded retry-until-green behavior
- automatic merge or push
- silent promotion from isolated worktree into the operator checkout
- coding-worker success as release proof
- Pi SDK runtime invocation as a shipped live path
- general self-extending plugin execution as a live autonomous build runtime

### What must not be duplicated under new names?

Do not rename the same governed pipeline into separate "build loop", "runner loop", "delegation loop", or "Pi loop" docs unless a genuinely new runtime contract exists.

## Current Runtime Truth

The repo already contains a concrete coding-worker execution substrate.

### Runtime surfaces present now

- `/api/agents/coding/execute` exists in `guardian/routes/agent_orchestration.py`.
- Coding execution is enqueued onto a Redis-backed queue and processed asynchronously.
- `guardian/workers/coding_worker.py` is the execution control point.
- `adapter_kind` is persisted in Guardian-owned deployment spec state and resolved by the worker.
- The adapter registry includes `codex`, `claudecode`, and `pi_codex_runner`.
- `AgentStore.store_coding_result()` persists bounded coding result evidence and returns it through Guardian into the source thread when lineage is present.
- Validation evidence is normalized through `guardian/agents/test_results.py`.
- The worker enforces a Git-backed mutation scope guard when it can prove repository boundaries.
- Validation retries are bounded and policy-constrained.
- Lease-bound execution exists when a valid worktree lease is supplied.
- Detached isolated worktree execution exists behind env-gated worker settings.
- Patch artifacts can be captured for isolated runs as review evidence.
- Commit-after-green exists as an opt-in seam after validation, with explicit human-review metadata.

### Runtime interpretation

- This is a real execution substrate.
- It is not the same thing as a shipped autonomous build loop.
- It is a bounded worker-and-adapter rail that the Build Loop doctrine should consolidate around instead of redefining.

## Canonical Phases

| Phase | Owner | Input | Output | Allowed side effects | Prohibited side effects | Proof surface | Current implementation status |
|---|---|---|---|---|---|---|---|
| `1. Intake` | Guardian route layer | User-authored coding request, source thread/message, permission policy, adapter choice | Guardian-owned deployment and queued run request | Persist deployment metadata, create run row, enqueue task, emit created event | Silent execution without Guardian ownership, implicit scope widening, direct commit/merge | `guardian/routes/agent_orchestration.py`, run creation, queue enqueue, `task.created` visibility | `implemented` |
| `2. Diagnose` | Human operator plus Unity Audit and current-state truth | Current-state docs, Unity Audit, release posture, task scope | Decision on whether the request is architecture-impacting, release-impacting, or safe to proceed as bounded work | Docs review, audit review, operator classification | Treat docs presence as runtime proof, bypass release truth, invent autonomous authority | `00-current-state.md`, `unity-audit-doctrine.md`, Unity Audit scaffold, operator review notes | `partial` |
| `3. Propose` | Guardian authority layer with human-authored request | Instructions, context summary, allowed paths, validation command, review requirements | Bounded execution proposal encoded in deployment spec and task payload | Persist bounded spec, capture approval posture, carry lineage fields | Implicit permission expansion, hidden provider or adapter changes | deployment `spec_json`, `CodingAgentTaskEnvelope`, stored permission policy | `implemented` |
| `4. Package` | Guardian plus adapter substrate preparation | Deployment spec, cwd, optional lease, optional worktree-isolation config | Execution package with resolved adapter, cwd/worktree, validation plan, mutation boundary | Resolve adapter alias, create isolated worktree when enabled, resolve lease, capture preflight Git scope | Writing outside approved scope, direct source-checkout promotion, unbounded packaging mutation | `guardian/workers/coding_worker.py`, worktree metadata, mutation preflight, lease validation | `implemented` |
| `5. Review` | Human Review Gate | Proposed change scope, architecture impact, review requirements | Explicit approval or rejection before risky promotion or merge-adjacent actions | Human approval metadata, manual inspection, task scoping decisions | Bypass of required human review, automatic merge approval, treating commit-after-green as sufficient | `require_human_review_before_merge`, runbook, architecture task ritual docs | `partial` |
| `6. Delegate` | Guardian Delegation semantics | Bounded package, chosen adapter, Guardian-owned run identity | Supervised handoff to worker/adapter substrate | Queue execution, emit run events, preserve lineage and source pointers | Delegating authority itself to the adapter, bypassing Guardian lineage, bypassing command-bus rules | `delegation-runtime.md`, `delegation-operator-manual.md`, run events, deployment/run store | `partial` |
| `7. Execute` | CodingWorker plus selected adapter | Queued coding task, resolved adapter, bounded cwd/worktree, policy | Adapter result bundle, file-change set, artifacts, errors | Execute bounded adapter work, heartbeat lease, capture patch artifact, emit running/worktree events | Autonomous recursion, direct identity mutation, command-bus bypass for internal authority, silent promotion into operator checkout | `guardian/workers/coding_worker.py`, adapter registry, task events, patch artifact events | `implemented` |
| `8. Validate` | CodingWorker validation seam | Success-like adapter result, validation command, shell policy, mutation guard | Normalized validation result, retry decision, final validation status | Run bounded validation command, normalize results, bounded retry, stop on mutation violation | Infinite retry, raw stdout-only truth, retry after scope violation, hidden downgrade of failed validation | `guardian/agents/test_results.py`, validation task events, worker metadata, runbook | `implemented` |
| `9. Prove` | Human operator plus runtime proof surfaces | Validation results, patch artifacts, current-state release criteria, live proof needs | Decision about what is proven, what is only code-path, and what still needs live runtime proof | Collect evidence, compare against release doctrine, keep patch artifacts for review | Treat coding-worker success as release signoff, treat patch artifact as release proof, collapse code-path proof into live proof | `00-current-state.md`, supported-path live proof docs, patch artifacts, validation summaries | `partial` |
| `10. Return` | Guardian result-return path | Run result, lineage fields, artifacts, validation summary, review metadata | Source-thread coding result plus durable metadata | Persist bounded result, inject source-addressable thread message, emit terminal events | Orphaned result publication, bypass of Guardian-owned transcript return, silent loss of lineage | `AgentStore.store_coding_result()`, source thread message, `extra_meta`, terminal task events | `implemented` |
| `11. Record` | Guardian persistence and provenance layer | Final result, lineage payload, validation summary, worktree/commit metadata | Durable record for later review, export-safe provenance, operator forensics | Persist artifacts, lineage metadata, commit metadata, validation summary | Silent provenance loss, hiding adapter path, erasing source linkage, redefining export obligations | `guardian/agents/store.py`, `account-export-restore-contract.md`, run artifacts, source-thread message metadata | `implemented` |

## Command Bus Relationship

The `Command Bus` remains the canonical bounded internal command authority lane.

That means:

- it governs one-turn assistant tool execution today,
- it remains the right lane for Codexify-owned internal command authority,
- and it must not be replaced by a second freeform command universe inside a build-loop doc.

The Guardian Build Loop can include command-bus-backed actions where appropriate, but it does not redefine command authority.

## Human Review Gate

Human review remains required when:

- the change is architecture-impacting,
- the change is release-impacting,
- the change touches authority, identity, provenance, or command boundaries,
- the change is moving from patch evidence to merge or release decisions,
- or the worker metadata explicitly says review is required.

Human review is not an optional afterthought. It is part of the governed loop boundary.

## Patch Artifacts and Commit-After-Green

Patch artifacts are:

- review evidence,
- bounded execution output,
- and useful proof of what the isolated worker attempted.

Patch artifacts are not:

- automatic application into the operator checkout,
- release proof,
- merge approval,
- or a replacement for human review.

Commit-after-green is:

- an opt-in backend seam after bounded validation,
- tied to governed execution context,
- and explicitly separate from merge, push, or release approval.

Commit-after-green is not:

- general autonomous release behavior,
- automatic merge,
- or evidence that the change is production- or beta-ready.

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
- The coding-worker and Codex Runner substrate is partially implemented in repo-local runtime code.
- Guardian remains authority, policy, lineage, and result-return owner.
- Human review remains required for architecture-impacting and release-impacting changes.
- Runtime proof remains separate from docs and coding-worker success.

What this document adds:

- one canonical umbrella name for the governed end-to-end build/change loop,
- explicit separation between governance doctrine and execution substrate,
- duplication control so future build-loop language does not fork into competing doctrines.

What this document does not add:

- no runtime behavior,
- no new routes, workers, tables, commands, or UI,
- no widened release support,
- no autonomous authority,
- no change to supported-path truth in `00-current-state.md`.

## Related Reading

- [Unity Audit Doctrine](./unity-audit-doctrine.md)
- [Delegation Runtime Contract](./delegation-runtime.md)
- [Delegation Operator Manual](./delegation-operator-manual.md)
- [Pi Invocation Boundary Contract](./pi-invocation-boundary-contract.md)
- [Agent Tool Loop Contract](./agent-tool-loop-contract.md)
- [Self-Extending Agent Plugin System](./self-extending-agent-plugin-system.md)
- [Solo Operator Coding Worker Runbook](../Ops/SOLO_OPERATOR_CODING_WORKER_RUNBOOK.md)

## Maintenance Rule

If future work changes:

- coding-worker authority boundaries,
- adapter semantics,
- command-bus relationship,
- result-return lineage,
- review gates,
- patch artifact meaning,
- or commit-after-green posture,

then update this doctrine in the same change set and keep the operational details routed to `docs/Ops/SOLO_OPERATOR_CODING_WORKER_RUNBOOK.md`.
