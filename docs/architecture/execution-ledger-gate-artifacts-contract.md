# Execution Ledger Gate Artifacts Contract

## Purpose
This document operationalizes ADR-028 by defining the documentation-level contract for Execution Ledger gate artifacts, implementation-plan artifacts, acceptance-criteria mapping, and completion/proof evidence mapping.

This document does not implement runtime behavior. It defines contract expectations for later implementation work.

## Status
- status: architecture contract
- governing ADR: ADR-028 Execution Ledger Campaign Runner Contract
- implementation status: docs-only contract; runtime implementation deferred

## Implementation Note: Backend Contract Models
- `guardian/agents/execution_ledger_contracts.py` now provides backend-only pure contract models for gate artifacts and acceptance criteria.
- The models use the bounded Execution Ledger token registry.
- The models are not yet persisted, routed, exposed through APIs, or wired into Campaign Runner execution.
- Future persistence or API adoption requires separate architecture-aligned implementation tasks and tests.
- Runtime behavior remains unchanged.

## Implementation Note: Backend Metadata Storage Seam
- `guardian/agents/execution_ledger_store.py` now provides a backend-internal storage helper for gate artifacts under work-order metadata.
- The storage seam uses existing work-order metadata and does not add schema.
- The seam is not exposed through routes or UI.
- The seam does not change Campaign Runner behavior, work-order lifecycle behavior, Guardian execution, Command Center, or release posture.
- Future API/UI adoption requires separate architecture-aligned implementation tasks and tests.
## Source Set
### Governing docs
- `docs/architecture/00-current-state.md`
- `docs/architecture/README.md`
- `docs/architecture/agent-protocol-operations.md`
- `docs/architecture/execution-ledger-phase-1-repo-aware-recon.md`
- `docs/architecture/runtime-protocol-token-contract.md`
- `docs/architecture/chat-runtime-contract.md`
- `docs/architecture/account-export-restore-contract.md`
- `docs/architecture/data-and-storage.md`
- `docs/architecture/modules-and-ownership.md`

### Governing ADRs
- `docs/architecture/adr/028-execution-ledger-campaign-runner-contract.md`
- `docs/architecture/adr/020-guardian-mediated-coding-agent-execution-contract.md`
- `docs/architecture/adr/001-queue-based-completion-acceptance-model.md`
- `docs/architecture/adr/002-dual-state-machine-model.md`
- `docs/architecture/adr/024-context-command-active-connector-semantics.md` (boundary reference when command invocation receipts are involved)

## Scope
### In scope
- gate artifact semantics
- acceptance-criteria mapping
- implementation-plan artifact requirements
- completion/proof evidence requirements
- mapping to Campaign Runner and Guardian execution surfaces
- future implementation constraints

### Out of scope
- migrations
- routes
- UI
- MCP tools
- CLI commands
- autonomous dispatch
- merge automation
- provider routing
- retrieval routing
- identity/persona modeling

## Current-Truth Anchors
- Campaign Runner and work-order surfaces are the canonical starting rails for Execution Ledger.
- `coding_work_orders` remain the canonical atomic execution units.
- `campaign_execution_attempts` and Guardian run/attempt records remain durable execution evidence surfaces.
- Source thread/message lineage must be preserved for chat-originated or Codex-originated ledger artifacts.
- File artifacts may reference canonical runtime IDs, but file artifacts are not canonical execution truth.
- Route acceptance is not completion.
- Task-event publication is not UI receipt.
- This contract does not introduce autonomous dispatch, merge automation, hidden progression, new runtime states, or release-promise widening.

## Canonical Mapping
| Ledger concept | Canonical Codexify surface | Notes |
|---|---|---|
| Ledger campaign | `campaign_goals` / `campaigns` | Top-level durable planning container |
| Ledger work order | `coding_work_orders` | Atomic execution unit |
| Implementation attempt | `campaign_execution_attempts` + Guardian run/attempt records | Durable execution evidence |
| Completion receipt | Guardian coding result / source-thread return path | Result linkage and delivery proof |
| Source lineage | Codex/artifact lineage + source thread/message references | Provenance requirement |
| Operator visibility | Command Center | First read-only surface |
| Planning docs | `docs/Campaign/` and `docs/tasks/` | Human-readable planning artifacts only |

## Gate Artifact Model
### 1. Intent/scope gate artifact
- purpose: bound the requested work order before implementation planning.
- required owner/reviewer: requester plus assigned reviewer with scope authority.
- required input: work-order intent draft, scope constraints, initial acceptance-criteria draft.
- required output: explicit scope decision and bounded artifact.
- required evidence: rationale, reviewer identity, timestamp, and linkage to affected scope.
- canonical runtime IDs it should reference: `work_order_id`, `campaign_id`, and source lineage IDs when available.
- what it must not imply: execution started, validation passed, or completion proven.
- candidate storage location for future implementation: `coding_work_orders.extra_meta` or a dedicated gate-artifact store.
- artifact backing posture: docs-only now; future-backed for runtime persistence.

### 2. Implementation-plan gate artifact
- purpose: authorize a bounded execution attempt plan before work begins.
- required owner/reviewer: implementer author plus reviewer accountable for blast radius.
- required input: approved intent/scope artifact and explicit implementation plan draft.
- required output: approved or rejected plan decision with revision notes.
- required evidence: reviewer decision, scope compliance notes, validation command plan, and timestamp.
- canonical runtime IDs it should reference: `work_order_id`, linked intent/scope artifact ID, and campaign reference.
- what it must not imply: code correctness, test pass, or delivery success.
- candidate storage location for future implementation: work-order metadata first, dedicated plan table if metadata becomes insufficient.
- artifact backing posture: docs-only now; future-backed for runtime persistence.

### 3. Completion/proof gate artifact
- purpose: evaluate whether completion claims are supported by durable attempt evidence.
- required owner/reviewer: proof reviewer accountable for acceptance or follow-up creation.
- required input: attempt records, run/result evidence, validation outputs, and changed-files summary.
- required output: completion/proof decision with rationale and any follow-up references.
- required evidence: attempt/run IDs, delivery evidence, validation outputs, and timestamp.
- canonical runtime IDs it should reference: `work_order_id`, `attempt_id`, Guardian run ID when available, command run ID when applicable.
- what it must not imply: guaranteed UI receipt, release readiness, or autonomous next-step dispatch.
- candidate storage location for future implementation: `campaign_execution_attempts` evidence extensions, run-artifact linkage, or dedicated proof-receipt table.
- artifact backing posture: docs-only now; future-backed for runtime persistence.

## Intent/Scope Gate
Required fields for a future intent/scope gate artifact:
- `work_order_id`
- `campaign_id`
- `source_thread_id`, if applicable
- `source_message_id`, if applicable
- title
- intent summary
- scope statement
- in-scope list
- out-of-scope list
- affected files or domains
- acceptance criteria draft
- reviewer
- decision
- decision rationale
- timestamp

Approval means only that the task is bounded enough to plan. It does not mean execution started.

## Implementation Plan Gate
Required fields for a future implementation-plan artifact:
- `work_order_id`
- `plan_id` or future equivalent
- linked intent/scope artifact
- expected files to read
- expected files to modify
- validation commands
- rollback plan
- risk/blast-radius notes
- dependency notes
- reviewer
- decision
- decision rationale
- timestamp

Approval means only that execution may be attempted under the approved boundary. It does not mean validation passed or completion is proven.

## Completion/Proof Gate
Required fields for a future completion/proof artifact:
- `work_order_id`
- `attempt_id`
- Guardian run ID, if available
- command run ID, if applicable
- completion receipt reference
- validation commands run
- validation result
- changed files summary
- acceptance criteria checklist
- delivery status
- follow-up work-order IDs, if applicable
- reviewer
- decision
- decision rationale
- timestamp

Completion/proof approval depends on durable attempt evidence, not task-event visibility alone.

## Acceptance Criteria Mapping
Acceptance criteria are structured proof obligations, not prompt decoration.

Each criterion should eventually support:
- stable criterion ID
- human-readable requirement
- validation mode
- expected evidence
- observed evidence
- result
- linked attempt/run evidence

Allowed validation modes for this docs contract:
- `manual_review`
- `unit_test`
- `integration_test`
- `typecheck`
- `lint`
- `runtime_probe`
- `docs_validation`
- `diff_inspection`

These are candidate contract vocabulary values only. They are not runtime tokens in this task and require token governance before runtime use.

## Implementation Plan Semantics
- Plans are pre-execution artifacts.
- Plans must be linked to a work order.
- Plans must identify expected blast radius.
- Plans must list validation commands.
- Plans must not authorize scope expansion without review.
- Plans are not proof of completion.

## Completion Evidence Semantics
Completion evidence may include:
- attempt records
- Guardian run records
- command-run records
- task events
- terminal status
- source-thread result delivery
- validation command output
- changed-files summary
- commit hash, if applicable
- follow-up work-order references

Contract interpretation:
- task events are visibility evidence, not durable proof by themselves
- durable records and persisted result/receipt linkage are stronger proof surfaces
- UI receipt must not be inferred from event publication

## File Artifact Boundary
- docs artifacts may seed or summarize ledger artifacts
- docs artifacts may link to canonical IDs
- docs artifacts must not become canonical execution truth
- `.codexify/tasks/` remains rejected as a parallel runtime control plane under ADR-028

## Token Governance Notes
Candidate token domains for future implementation:
- gate decisions
- plan states
- acceptance criterion validation modes
- acceptance criterion results
- proof decisions
- escalation reasons

Governance rules:
- Do not use these as runtime literals until they are canonicalized.
- Runtime-visible tokens must be added through `guardian/protocol_tokens.py` or a bounded approved registry.
- Frontend must mirror backend canonical values.

## Future Storage Options
| Option | Benefit | Risk | When it becomes justified |
|---|---|---|---|
| `coding_work_orders.extra_meta` | Fastest path to attach gate/plan metadata without new table fan-out | Metadata bloat and weaker query ergonomics for audit/reporting | Early pilot when artifact volume is low and read patterns are simple |
| `campaign_execution_attempts` evidence fields | Keeps proof material near existing attempt ledger | Can overload attempt rows with non-attempt semantics | When proof-only linkage is needed and plan/gate records remain minimal |
| dedicated gate receipt table | Strong queryability and explicit gate lineage | New schema complexity and migration burden | When gate lifecycle becomes first-class runtime behavior |
| dedicated plan artifact table | Clear plan versioning and review history | Additional joins and lifecycle coordination | When plans need revision history and cross-work-order reporting |
| Guardian run/artifact linkage | Reuses existing run/artifact evidence and lineage seams | Can blur authored-gate artifacts with execution artifacts if not bounded | When proof receipts must directly reference run artifacts with durable lineage |

## Invariants
- no duplicate canonical truth surface
- no prompt-only control plane
- no acceptance/completion collapse
- no event-publication/UI-receipt collapse
- no private identity/persona leakage into public task artifacts
- no durable trait inference through task artifacts
- no bypass of command bus or Guardian-mediated orchestration policy seams
- no runtime statuses outside canonical token governance
- no release-promise widening

## Proof Surface for Future Implementation
Later implementation tasks must prove:
- backend store/route tests for gate artifact creation and readback
- protocol token tests if token domains are added
- worker/attempt tests if execution behavior changes
- docs validation
- Command Center UI tests only if UI is touched
- supported-path runtime proof only if runtime behavior changes

## Follow-Up Task Recommendation
Next task recommendation:
- Add a token-domain proposal for Execution Ledger gate decisions, plan states, and acceptance criterion validation results, without runtime behavior changes.
