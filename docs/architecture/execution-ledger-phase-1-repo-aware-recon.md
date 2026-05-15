# Execution Ledger Phase 1 Repo-Aware Recon

## Purpose
Map a Backlog.md-style durable task workflow onto existing Codexify architecture without implementing runtime changes in this task.

This recon is architecture-impacting and repo-aware. It is constrained to current truth and existing seams (Campaign Runner, Guardian-mediated coding execution, command bus, Codex lineage, task/run/event stores, and Command Center), so future implementation reuses canonical rails instead of creating a parallel control plane.

## Source Set
### Governing docs
- `docs/architecture/00-current-state.md`
- `docs/architecture/adr/adr-index.md`
- `docs/architecture/README.md`
- `docs/architecture/agent-protocol-operations.md`
- `docs/architecture/system-overview.md`
- `docs/architecture/flows.md`
- `docs/architecture/data-and-storage.md`
- `docs/architecture/modules-and-ownership.md`
- `docs/architecture/runtime-protocol-token-contract.md`
- `docs/architecture/chat-runtime-contract.md`
- `docs/architecture/account-export-restore-contract.md`
- `docs/architecture/self-extending-agent-plugin-system.md`

### Governing ADRs read for this recon scope
- `docs/architecture/adr/001-queue-based-completion-acceptance-model.md`
- `docs/architecture/adr/002-dual-state-machine-model.md`
- `docs/architecture/adr/006-flow-builder-elicitation-lane.md`
- `docs/architecture/adr/014-flow-builder-thread-draft-and-receipts-contract.md`
- `docs/architecture/adr/020-guardian-mediated-coding-agent-execution-contract.md`
- `docs/architecture/adr/022-guardian-intent-spine-and-cross-surface-control-plane.md`
- `docs/architecture/adr/024-context-command-active-connector-semantics.md`
- `docs/architecture/adr/027-flow-builder-typed-surface-and-run-receipt-contract.md`

### Supporting docs read
- `docs/Campaign/CAMPAIGN_2026-05-01_001_PI_CODER_INTEGRATION.md`
- `docs/Campaign/CAMPAIGN_2026-05-09_001_AUTOMATED_WORKER_CONTROL_PLANE/README.md`
- `docs/Campaign/CAMPAIGN_2026-05-09_001_AUTOMATED_WORKER_CONTROL_PLANE/00-current-shape.md`
- `docs/Campaign/CAMPAIGN_2026-05-09_001_AUTOMATED_WORKER_CONTROL_PLANE/08-campaign-runner-mvp-spine.md`
- `docs/tasks/TASK-2026-05-01-001_envelope_schema.md`
- `docs/tasks/TASK-2026-05-01-004_result_ingestion.md`
- `docs/tasks/TASK_2026_02_12_005_flow_runner_execute_trace.md`

### Inspected code anchors
- `guardian/routes/agent_orchestration.py`
- `guardian/routes/codex.py`
- `guardian/codex/lineage.py`
- `guardian/agents/store.py`
- `guardian/agents/events.py`
- `guardian/workers/agent_worker.py`
- `guardian/workers/coding_worker.py`
- `guardian/command_bus/contracts.py`
- `guardian/db/models.py`
- `guardian/protocol_tokens.py`
- `frontend/src/features/commandCenter/CommandCenterPage.tsx`
- `frontend/src/features/commandCenter/types.ts`
- `frontend/src/features/commandCenter/hooks/useCodingWorkOrders.ts`
- `frontend/src/features/commandCenter/hooks/useOrchestratorRecommendations.ts`
- `frontend/src/features/commandCenter/components/CodingWorkOrdersPanel.tsx`

### Additional code inspected to map existing seams
- `guardian/routes/coding_work_orders.py`
- `guardian/agents/campaign_runner_store.py`
- `guardian/agents/work_order_store.py`
- `guardian/agents/work_orders.py`
- `guardian/routes/command_bus.py`

### Missing or not-found anchors
- Missing path variant: `docs/architecture/adr/ADR Index.md`
- Present and used instead: `docs/architecture/adr/adr-index.md`

## Conceptual Target
Execution Ledger in Codexify terms should mean:
- Durable task artifacts:
  - Planning artifacts in existing campaign/task docs
  - Durable runtime execution evidence in Postgres-backed run/attempt records
- Bounded agent execution units:
  - One work order or coding task envelope per execution unit
  - Attempt identity separate from authored task identity
- Acceptance criteria:
  - Explicit scope, file boundaries, validation command, and completion condition
- Implementation plans:
  - Human/agent-authored plan linked to the same task/work-order identity
- Review gates:
  - Intent/scope gate, implementation plan gate, completion/proof gate
- Execution logs:
  - Event streams plus durable event/attempt records, not logs alone
- Provenance and lineage:
  - Source thread/message lineage carried through task, run, and result receipt
- Test/validation proof:
  - Validation results and attempt summaries as first-class evidence
- Commit or run boundary:
  - Attempt-scoped run boundary with optional commit-after-validation metadata
- Future MCP/command surface:
  - If added, route through existing command bus and intent governance rather than a second dispatcher.

## Current-Truth Anchors
### What is true now
- Campaign Runner MVP backend spine exists:
  - Durable entities: `campaign_goals`, `campaigns`, `campaign_execution_attempts`
  - Routes: `/api/coding/campaign-runner/*`
- Guardian-mediated coding-agent execution exists as bounded backend seam:
  - `/api/agents/coding/execute` creates deployment/run and enqueues execution
  - `coding_worker` processes queue tasks and returns bounded `coding_result`
- Command bus exists as canonical command execution lane:
  - `/api/guardian/commands/manifest`
  - `/api/guardian/commands/invoke`
  - `/api/guardian/commands/runs/{run_id}/events`
  - Durable `command_runs` and `command_run_events`
- Codex/artifact lineage guard exists:
  - `guardian/codex/lineage.py` enforces source thread/message lineage existence
  - `guardian/routes/codex.py` gates source access with lineage validation
- Agent run/event stores exist:
  - `AgentStore` persists `agent_deployments`, `agent_runs`, `agent_run_steps`, attempts, artifacts
  - `AgentEventPublisher` persists and streams run events
- Task/campaign doc structures already exist:
  - `docs/Campaign/` and `docs/tasks/` are established planning artifacts
- Current token domains exist for runtime/campaign/task semantics:
  - `guardian/protocol_tokens.py` includes task event types, campaign statuses, attempt statuses, orchestration reason codes
- Execution/run models are durable where architecture says so:
  - Postgres is durable truth for runs/attempts and command/campaign records
  - Redis is queue/event transport
- Command Center has work-order and recommendation surfaces:
  - Reads/writes work-order control-plane APIs
  - Uses recommendation-only orchestrator endpoint
- Coding result return path is currently proven on the supported path:
  - Bounded source-thread `coding_result` return, idempotent replay handling, durable terminal run convergence
  - Latest live proof still recorded a terminal `failed` run due adapter timeout; delivery/control-plane proof passed
- Supported deployment constraints are explicit:
  - Local Docker Compose path is supported
  - Release posture remains local-only and conservative

### What is not yet true
- No accepted ADR yet defines an Execution Ledger contract spanning task artifact gates + campaign/work-order execution semantics end-to-end.
- No release-true autonomous dispatch/scheduler loop for work orders.
- No release-true merge automation or hands-free progression through review gates.
- No proof that adding new ledger semantics is already governed by existing campaign/work-order status contracts.

### What this recon may assume
- Existing Campaign Runner + work-order + attempt ledger surfaces are the starting control-plane seam.
- Existing Guardian coding execution envelope/result lineage is mandatory reuse.
- Existing command bus and token governance remain canonical for command-facing semantics.
- `00-current-state.md` overrides older/broader docs for short-horizon release truth.

### What this recon must not assume
- Must not assume route acceptance means completion.
- Must not assume task-event publication means UI receipt.
- Must not assume file artifacts are canonical execution truth.
- Must not assume ADR-022 (status: proposed) is already accepted runtime law.
- Must not assume any widen-release claim beyond current local Compose supported posture.

### Document/code disagreements captured
- `docs/architecture/flows.md` still contains workspace-local retrieval wording that marks selection/injection as under active validation, while `docs/architecture/00-current-state.md` now marks this seam as live-proven.  
  Current-truth override applied: `00-current-state.md` wins for release interpretation.

## ADR Impact
- classification: `Requires new ADR`
- governing ADRs found:
  - ADR-001 Queue-Based Completion Acceptance Model
  - ADR-002 Dual State Machine Model
  - ADR-020 Guardian Mediated Coding Agent Execution Contract
  - ADR-022 Guardian Intent Spine and Cross-Surface Control Plane (proposed)
  - ADR-024 Context Command and Active Connector Semantics
  - ADR-006 / ADR-014 / ADR-027 Flow Builder contract family (receipt and authoring governance patterns)
- reason:
  - Existing ADRs govern adjacent seams (acceptance semantics, coding-execution envelope/result lineage, intent normalization, token discipline), but none canonizes Execution Ledger semantics across task identity, review gates, plan states, and campaign/work-order attempt linkage as one governed contract.
  - Implementing ledger states/gates without a dedicated ADR risks token and state-machine drift across work orders, attempt ledger, Command Center, and docs-task artifacts.
- whether implementation should proceed without a new ADR:
  - Runtime/schema/API implementation should not proceed without a focused Execution Ledger ADR.
  - A docs-only ADR creation task should be the first implementation step.

## Existing Surfaces This Should Reuse
| Existing surface | Current role | How Execution Ledger should reuse it | Risk if duplicated |
|---|---|---|---|
| `campaign_goals`, `campaigns` + `/api/coding/campaign-runner/*` | Durable goal/campaign container and summary view | Use as top-level ledger container (goal -> campaign) instead of inventing a second parent hierarchy | Conflicting campaign identity and diverging status transitions |
| `coding_work_orders` + `WorkOrderStore` + `/api/coding/work-orders/*` | Durable atomic work-order state machine | Treat work orders as canonical execution units for backlog items | Parallel task objects and ambiguous source of truth |
| `campaign_execution_attempts` + `CampaignRunnerStore.record_execution_attempt` | Durable attempt ledger keyed by run/attempt identity | Use as canonical execution evidence timeline for ledger runs | Competing run ledgers and inconsistent historical evidence |
| `AgentStore` (`agent_deployments`, `agent_runs`, steps, attempts, artifacts) | Guardian-owned execution tracking and receipts | Reuse for run/attempt internals and artifact linking from work order to run evidence | Fragmented run state and broken run-to-receipt traceability |
| `AgentEventPublisher` + task event streams | Durable + streamed lifecycle events | Keep event publication on existing task/run streams with canonical event types | Ad hoc event channels and UI event drift |
| `store_coding_result(...)` + source-thread injection | Canonical result return path with lineage and delivery status | Keep completion receipts tied to source thread/message and work order markers | Orphaned execution outcomes not visible in source thread |
| `guardian/command_bus/contracts.py` + `command_runs`/`command_run_events` | Canonical command invocation contract and run receipts | If ledger actions become command-triggered, route through command bus contract and receipts | Second command universe and policy bypass |
| `guardian/codex/lineage.py` + `guardian/routes/codex.py` | Source lineage validation for codex artifacts | Reuse lineage doctrine for durable ledger artifacts referencing thread/message origins | Parallel lineage semantics and provenance ambiguity |
| `guardian/protocol_tokens.py` + token contract docs | Canonical runtime token vocabulary | Extend canonical token registries for any new repeated ledger runtime literals | Literal drift across backend/frontend/docs |
| `frontend/src/features/commandCenter/*` | Operator-facing diagnostic/control-plane panels including work orders and recommendations | Extend existing Command Center panels for read-only ledger visibility first | Duplicate diagnostics surface with conflicting interpretations |
| `docs/Campaign/` and `docs/tasks/` | Existing planning artifact ecosystem | Reuse as human-authored planning/intent artifacts only (non-canonical runtime truth) | File artifacts mistaken for canonical execution truth |

## Surfaces It Must Not Duplicate
- Do not create a second task state machine separate from existing `coding_work_orders` lifecycle and campaign attempt ledger.
- Do not emit ad hoc task/campaign/event literals outside canonical token governance.
- Do not treat file-based artifacts as canonical execution truth when Postgres-backed run/attempt records already exist.
- Do not create a parallel lineage system outside existing source thread/message lineage conventions.
- Do not create a separate diagnostics UI outside existing Command Center/approved diagnostic surfaces.
- Do not encode execution policy as prompt-only doctrine; contract-bearing policy must live in governed docs/contracts/code seams.
- Do not fork command dispatch behavior away from command bus and Guardian-owned orchestration boundaries.

## Proposed Phase 1 Shape
Option evaluation against current repo:
- `1. docs-only workflow contract`:
  - Useful for governance, but alone does not anchor execution to existing campaign/work-order rails.
- `2. Postgres-backed task/run contract extension`:
  - Viable later, but too broad as first move and can skip existing Campaign Runner seams.
- `3. Campaign Runner extension`:
  - Best fit: directly reuses goals/campaigns/work orders/attempt ledger and recommendation-only doctrine.
- `4. Command Center surface extension`:
  - UI-first; risky before canonical ledger semantics are governed.
- `5. file-based repo-local task artifacts`:
  - High risk of duplicate truth if treated as runtime canonical.
- `6. hybrid artifact + Postgres lineage model`:
  - Useful later, but should come after canonical Campaign Runner ledger contract is fixed.

Recommended Phase 1 path: `3. Campaign Runner extension`

Boundary for this recommendation:
- First implementation task is governance-only (new ADR defining Execution Ledger contract over Campaign Runner seams).
- Runtime/schema/UI changes follow only after ADR acceptance.

## Proposed Data Model Touchpoints
Phase 1 implementation task (recommended first step) should not touch models:
- No migrations
- No DB schema changes

If later runtime tasks are approved, candidate touchpoints are:
- `coding_work_orders`:
  - Candidate fields for explicit plan-gate and review-gate references if existing status + `extra_meta` prove insufficient
- `campaign_execution_attempts`:
  - Candidate evidence expansion for gate outcomes and acceptance-criteria verification snapshots
- `agent_run_artifacts`:
  - Candidate normalized linkage for gate receipt artifacts before/after execution boundaries

Rationale:
- Existing tables already encode most required identities (work order, run, attempt, source lineage, delivery evidence).
- New schema should be deferred until ADR defines exact invariants and tokenized states.

## Proposed Token Domains
Potential new repeated literals to govern:
- Ledger task states (if distinct from existing work-order statuses)
- Review gate states (`intent_scope_review`, `plan_review`, `completion_proof_review`)
- Execution plan states
- Acceptance-criterion validation statuses
- Run boundary states (if expanded beyond existing run/attempt statuses)
- Escalation reasons (if beyond existing orchestrator and error code sets)

Placement recommendation:
- Runtime-visible lifecycle/event/error tokens:
  - `guardian/protocol_tokens.py`
- Work-order-local contract tokens:
  - Keep bounded in `guardian/agents/work_orders.py` if scope remains work-order-only
  - Promote to protocol tokens only when they become cross-surface runtime truth
- Frontend interpretation tokens:
  - Mirror backend canon in `frontend` contract types; no independent literal invention
- Avoid:
  - Inline literals in routes/workers/components as final truth

## Proposed Runtime Boundaries
Docs-only in first implementation task:
- Execution Ledger ADR definition
- Explicit mapping of ledger semantics to existing Campaign Runner and Guardian seams

Backend runtime behavior in later tasks:
- Any new ledger gate transitions, gate receipts, or status extensions
- Any campaign/work-order/attempt mutation behavior changes

UI-only in later tasks:
- Command Center read-only ledger visibility and gate-state projection
- No implicit dispatch or hidden automation in UI surfaces

Invariants to preserve:
- Route acceptance is not completion
- Task-event publication is not UI receipt
- Postgres is durable orchestration truth where current architecture says so
- Redis is transport, not canonical ledger truth
- Graph writes remain default-off unless explicitly governed otherwise
- Internal command-bus surfaces are not automatically release promises

## Review Gates
1. intent/scope review
- owner: human operator / task author
- input artifact: campaign goal + work-order draft + scope/file boundaries
- output artifact: approved scoped work order (`draft -> ready`) with explicit acceptance criteria
- current repo surface it could use: `docs/tasks/*`, `/api/coding/work-orders`, `coding_work_orders.extra_meta`
- future implementation seam: explicit gate receipt record linked to `work_order_id`

2. implementation plan review
- owner: operator + Guardian-mediated orchestration policy
- input artifact: work-order plan, dependency IDs, validation command, lease/commit policy
- output artifact: plan-approved execution unit ready for run creation
- current repo surface it could use: work-order contract fields + `/api/agents/coding/execute` envelope + deployment spec hash
- future implementation seam: explicit `plan_gate_status` token and plan receipt linkage to run/deployment

3. completion/proof review
- owner: operator/reviewer
- input artifact: coding result summary, validation evidence, attempt ledger, delivery status, optional commit metadata
- output artifact: terminal decision (`merge_ready`, `archived`, or follow-up work order)
- current repo surface it could use: `store_coding_result`, `campaign_execution_attempts`, `latest_receipt_id`, Command Center inspection
- future implementation seam: explicit proof checklist contract and review decision receipt

## Proof Surface
Future implementation proof should include:
- backend tests:
  - `guardian/tests/routes/test_coding_work_orders.py`
  - `guardian/tests/routes/test_agent_orchestration_events.py`
  - `guardian/tests/workers/test_coding_worker.py`
  - `guardian/tests/agents/test_work_order_store.py`
  - `guardian/tests/agents/test_orchestrator_policy.py`
- docs validation:
  - `python3 scripts/validate_docs.py`
- token contract tests if new canonical tokens are added:
  - `tests/contracts/test_protocol_tokens.py`
- runtime proof:
  - required only when runtime behavior changes
- UI tests:
  - required only when Command Center/UI surfaces change

This recon task itself does not claim runtime proof.

## Invariants
- no unreviewed architecture drift
- no prompt-only control plane
- no duplicate canonical truth surface
- no private identity/persona leakage into public task artifacts
- no durable trait inference through task artifacts
- no bypass of existing command bus / agent orchestration policy seams
- no new runtime statuses outside canonical token governance
- no release-promise widening

## Recommended Task Sequence
1. `TASK-A`: Add ADR for Execution Ledger over Campaign Runner seams (no runtime changes)
2. `TASK-B`: Add docs contract for gate artifacts and acceptance-criteria mapping to existing work-order/attempt fields
3. `TASK-C`: Add token-domain proposal and contract tests for any newly accepted ledger literals
4. `TASK-D`: Add backend store/route extensions only if ADR-approved gaps remain after reuse of existing fields
5. `TASK-E`: Add Command Center read-only ledger/gate visibility aligned to canonical backend fields
6. `TASK-F`: Add optional controlled progression workflow (still recommendation-first unless explicitly widened)

## Open Questions
- Should Execution Ledger gate states live entirely inside existing work-order statuses, or be modeled as separate gate receipts?
- Should plan/gate evidence be normalized into dedicated tables, or remain in bounded metadata until usage proves schema pressure?
- Should ADR-022 (proposed) be accepted/updated first, or should Execution Ledger ADR stand independently with explicit dependency notes?
- What is the minimum canonical artifact identity that links docs task artifacts to `work_order_id` without making docs canonical runtime truth?
- Which ledger fields are operator-facing diagnostics versus release-claim surfaces?
- What is the deprecation/migration strategy if existing campaign/work-order statuses need renaming under token governance?

## Final Recommendation
First implementation task after this recon:
- Create a new architecture ADR that defines Execution Ledger semantics as a Campaign Runner extension over existing `campaign_goals` / `campaigns` / `coding_work_orders` / `campaign_execution_attempts` plus Guardian run/result lineage rules.

Do not begin runtime/schema/UI implementation until that ADR is accepted.
