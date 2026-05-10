# Symphony Spec Adaptation Matrix for Codexify Worker Control Plane

## Purpose
Interpret the imported Symphony service specification as a **reference architecture** for Codexify's Automated Worker Control Plane campaign, without changing runtime behavior.

This document is planning-only. It does not implement runtime code, schema changes, routes, workers, UI behavior, tracker integration, dispatch behavior, Git operations, or workflow execution.

## Source documents
### Campaign and architecture anchors
- [docs/architecture/00-current-state.md](../../../architecture/00-current-state.md)
- [docs/architecture/README.md](../../../architecture/README.md)
- [docs/architecture/agent-protocol-operations.md](../../../architecture/agent-protocol-operations.md)
- [docs/architecture/system-overview.md](../../../architecture/system-overview.md)
- [docs/architecture/flows.md](../../../architecture/flows.md)
- [docs/architecture/data-and-storage.md](../../../architecture/data-and-storage.md)
- [docs/architecture/modules-and-ownership.md](../../../architecture/modules-and-ownership.md)
- [docs/architecture/runtime-protocol-token-contract.md](../../../architecture/runtime-protocol-token-contract.md)
- [docs/Ops/SOLO_OPERATOR_CODING_WORKER_RUNBOOK.md](../../../Ops/SOLO_OPERATOR_CODING_WORKER_RUNBOOK.md)
- [README.md](../README.md)
- [01-domain-model.md](../01-domain-model.md)
- [02-task-state-machine.md](../02-task-state-machine.md)
- [03-worktree-lease-contract.md](../03-worktree-lease-contract.md)
- [04-worker-receipt-contract.md](../04-worker-receipt-contract.md)
- [05-orchestrator-policy.md](../05-orchestrator-policy.md)
- [06-api-surface-sketch.md](../06-api-surface-sketch.md)
- [07-rollout-plan.md](../07-rollout-plan.md)

### Imported reference spec
- [docs/specs/Symphony-Spec-Seed.md](../../../specs/Symphony-Spec-Seed.md) (`Symphony Service Specification`)

## Interpretation rule
1. Symphony's issue tracker model maps to **future WorkOrder ingestion**, not replacement of Codexify's durable `WorkOrder` API.
2. Symphony's workspace manager maps to **future worktree lease allocation**, not bypass of existing lease contract/store.
3. Symphony's orchestrator maps to **Codexify deterministic policy + future bounded dispatch**, not persona-style or unbounded autonomy.
4. Symphony `WORKFLOW.md` is evaluated as a **repo-owned policy template candidate**, not adopted blindly.
5. Symphony in-memory orchestrator truth does **not** override Codexify Postgres-backed control-plane truth.
6. Symphony's "rich UI is out of scope" non-goal does not transfer directly; Codexify intentionally exposes operator truth through Command Center.
7. Symphony tracker-write boundary is useful and should be preserved: orchestrator should read/schedule/reconcile, while ticket comments/state transitions remain bounded tool/command-bus concerns unless a future ADR says otherwise.

## Executive summary
- Symphony and Codexify are aligned on deterministic orchestration intent, bounded execution, workspace isolation, retry thinking, and operator observability.
- Codexify already has stronger durable control-plane foundations (WorkOrder API, lease contract/store, recommendation policy route, Command Center panel surface, canonical runtime token doctrine).
- The largest mismatch is Symphony's single-process in-memory scheduler truth versus Codexify's durable Guardian-owned state and route acceptance/completion boundaries.
- Recommended path: keep current campaign phases intact, add an optional future adaptation phase for tracker/workflow ingestion, and reject in-memory-authoritative orchestration state as a design transplant.

## What Symphony is
Symphony is a long-running tracker-driven automation service with:
- repository-owned `WORKFLOW.md` policy/config,
- Linear-oriented issue ingestion and reconciliation,
- deterministic per-issue workspaces,
- bounded concurrency/retry orchestration,
- app-server session lifecycle handling,
- structured logs and optional runtime status views.

In Codexify context, Symphony is a reference design input, not a governing architecture source.

## What Codexify already has
- Guardian-mediated control-plane campaign with explicit phase docs.
- Durable `WorkOrder` API (`POST/GET/list/detail/cancel`) and state model.
- Recommendation-only orchestrator route (`GET /api/coding/orchestrator/next`).
- Worktree lease contracts, durable lease store, and lease-bound worker execution seam.
- Commit-after-green gate for lease-bound validated runs.
- Command Center worker-control panel surface consuming current WorkOrder/orchestrator endpoints.
- Canonical runtime token discipline and explicit "acceptance is not completion" doctrine.

## Major similarities
- Deterministic orchestration policy emphasis.
- Bounded execution/retry posture instead of unbounded loops.
- Isolation of mutable workspace per unit of work.
- Explicit state transitions and terminal reasoning.
- Operator-visible observability expectations.

## Major differences
- Symphony default orchestration truth is in-memory; Codexify control-plane truth is durable and Guardian-owned.
- Symphony centers tracker polling as primary intake; Codexify centers explicit WorkOrder acceptance today.
- Symphony treats status surfaces as optional; Codexify explicitly invests in Command Center/operator truth.
- Symphony allows broad workflow hooks from `WORKFLOW.md`; Codexify requires stricter policy/lineage boundaries.
- Symphony spec assumes tracker is central (`linear` v1); Codexify keeps tracker ingestion as a future optional capability.

## Adaptation matrix

| Symphony concept | Classification | Symphony meaning | Codexify equivalent | Current Codexify status | Recommended action | Required future files/modules if implemented | Proof expectation | Risks/cautions |
|---|---|---|---|---|---|---|---|---|
| `WORKFLOW.md` loader | `defer` | Repo-owned workflow policy source loaded at runtime. | Future repo-owned worker policy template feeding WorkOrder/orchestrator decisions. | Not implemented. No repository-owned workflow-policy loader in coding runs. | Keep as optional Phase 9 track; require Guardian-owned parsing/validation contract before runtime use. | Candidate new bounded loader module under `guardian/agents/` plus campaign docs/tests. | Docs contract + parser tests + proof that no runtime widening occurs without explicit enablement. | Blind adoption can bypass canonical tokens, policy ownership, and acceptance/completion boundaries. |
| YAML front matter config | `needs_discovery` | Typed runtime config in workflow file front matter. | Possible future constrained policy header for worker orchestration defaults. | No control-plane front-matter parser. | Discovery first: define minimal schema and safety constraints before any implementation task. | Candidate schema contract doc, parser tests, allowlist validator module. | Contract tests prove reject-by-default for unknown or unsafe keys. | Config sprawl and hidden authority transfer into repo text files. |
| prompt template body | `adapt` | Markdown prompt template rendered per issue. | Existing instruction envelopes + future WorkOrder-linked template injection seam. | Partial analogs exist via coding instructions; no `WORKFLOW.md` template engine for control plane. | Adapt to Codexify instruction envelope only after policy fields and lineage keys are fixed. | `guardian/agents/` prompt assembly seam + tests around deterministic rendering. | Proof that prompt rendering is deterministic, bounded, and traceable per run lineage. | Template drift could create unreviewed behavior changes across runs. |
| issue tracker client | `defer` | Tracker adapter fetches candidate/reconciliation/terminal issue sets. | Future external ingestion into durable `WorkOrder` intake. | Not implemented for worker control plane. | Defer to optional external-ingestion phase; keep WorkOrder API as authoritative intake seam. | Candidate tracker adapter + ingestion translator modules + new tests. | End-to-end proof: tracker item -> WorkOrder row with explicit mapping and no dispatch side effects. | Direct tracker coupling can collapse explicit intake review and policy gates. |
| Linear-compatible issue model | `adapt` | Normalized issue payload for orchestration. | Mapping layer from tracker issue fields into `WorkOrder`/dependency/policy fields. | No Linear ingestion model in current campaign implementation. | Adapt as translator only; never make Linear payload the durable source-of-truth schema. | Candidate translator contract and validation tests under `guardian/agents/`. | Mapping tests cover priorities, labels, dependencies, and identity normalization. | Field mismatch can produce silent policy drift or wrong dispatch recommendations. |
| active issue states | `adapt` | Tracker states eligible for dispatch. | Eligibility mapping into `WorkOrder` statuses (`ready`, etc.) and policy filters. | Tracker-state mapping not implemented. | Add explicit mapping table in future ingestion contract, not implicit string checks. | Candidate policy mapping module + tests. | Deterministic mapping tests for state transitions and skip reasons. | Ambiguous mapping can dispatch work that should remain blocked. |
| terminal issue states | `adapt` | Tracker states that end orchestration/cleanup behavior. | Mapping to cancellation/archive/escalation semantics and cleanup policies. | Tracker-terminal-state mapping not implemented. | Define explicit terminal translation semantics with fail-closed defaults. | Candidate reconciliation policy module + tests. | Tests for terminal transition behavior and cleanup intent records. | Wrong terminal mapping can leak stale workspaces or kill valid work prematurely. |
| tracker polling cadence | `defer` | Fixed orchestrator poll tick. | Future ingestion scheduler cadence for external tracker sync. | No tracker poller for this campaign. | Defer; prioritize manual control-plane proof and recommendation/dispatch contracts first. | Candidate scheduler module and ops config surface. | Poll cadence tests + rate-limit/backoff behavior under failure. | Aggressive polling can create rate-limit issues and noisy control-plane churn. |
| bounded concurrency | `adapt` | Global/per-state cap on simultaneous issue runs. | Future orchestrator dispatch caps combined with lease exclusivity and conflict rules. | Recommendation policy exists; dispatch/concurrency governor not implemented. | Add explicit dispatch caps only when dispatch route exists; tie to lease capacity and conflict policy. | `guardian/agents/orchestrator_policy.py`, future dispatch route/store, tests. | Route/policy tests prove no over-dispatch and deterministic skip reasons. | Concurrency without lease-aware limits risks mutable workspace collisions. |
| in-memory orchestrator state | `reject` | In-process authoritative state maps and retry timers. | Codexify durable Postgres-backed control-plane truth + explicit event lineage. | Durable truth direction already established in campaign docs. | Reject as normative design for Codexify control-plane truth. Allow ephemeral caches only as derivations. | N/A | Architecture docs and implementation tasks continue to enforce durable source-of-truth boundaries. | In-memory authority risks state loss, replay ambiguity, and operator-truth drift after restarts. |
| retry queue | `adapt` | Orchestrator retry scheduling for failed runs/continuations. | Future durable retry intent/state plus bounded worker attempt policy. | Bounded validation retry exists in coding worker; orchestrator-level retry queue for work orders not implemented. | Adapt into durable retry records keyed by work-order/run lineage. | Candidate retry-state fields/store + policy tests. | Tests prove retry scheduling is bounded, auditable, and idempotent. | Non-durable retry timing can create duplicate or lost attempts. |
| exponential backoff | `defer` | Retry delay increases with cap. | Future retry policy for ingestion/dispatch failures. | Not implemented in work-order orchestrator path. | Defer until retry queue exists; codify cap and jitter contract in same task. | Candidate retry policy module/tests. | Timing tests show cap, jitter, and stop conditions are deterministic. | Backoff without clear stop rules can hide stuck work indefinitely. |
| reconciliation for issue state changes | `adapt` | Re-check issue state and stop/release ineligible runs. | Future tracker-to-WorkOrder reconciliation plus lease/run termination rules. | No tracker reconciliation loop implemented. | Adapt as explicit reconciliation pass that mutates durable state with reason codes. | Candidate reconciliation job/service + tests. | Proof that non-active/terminal transitions reconcile safely and preserve lineage. | Unsafe reconciliation can terminate active valid runs or miss stop conditions. |
| deterministic per-issue workspace mapping | `adapt` | Stable issue -> workspace directory mapping. | Future deterministic `WorkOrder`/tracker identifier -> lease/worktree path allocator. | Lease path fields and lease-bound cwd enforcement exist; automatic allocator not implemented. | Build deterministic allocator only inside lease contract boundaries. | `guardian/agents/worktree_leases.py`, lease allocator module, tests. | Lease allocator tests for deterministic mapping and collision handling. | Non-deterministic mapping undermines reproducibility and cleanup correctness. |
| workspace root | `adapt` | Configured root path that bounds issue workspaces. | Policy-controlled allowed lease/worktree roots. | No automatic root allocator; lease worktree path is externally provided today. | Introduce root allowlist and path normalization when allocator is added. | Lease allocator + policy validation modules. | Tests prove all lease paths remain under configured root and reject escapes. | Path traversal or root drift can violate boundary and security assumptions. |
| workspace hooks | `needs_discovery` | Lifecycle shell hooks (`after_create`, `before_run`, etc.). | Possible future bounded preflight/postflight policy actions. | No control-plane workspace-hook runtime. | Do not import raw shell hooks directly; investigate guarded alternative through explicit policy commands. | Potential command-bus mediated hook runner with strict allowlist. | Security tests prove hook execution cannot escape policy envelope. | Arbitrary hooks can bypass Guardian policy and broaden attack surface. |
| agent runner | `already_implemented` | Component that executes agent sessions inside workspace and streams outcomes. | `coding_worker` + registered adapters (`pi_codex_runner`, `codex`, `claudecode`) under Guardian queue/control. | Implemented as Guardian-mediated worker execution seam; dispatch and tracker-driven orchestration are separate/unimplemented surfaces. | Preserve existing worker seam; extend only via explicit phase tasks. | Existing modules only unless future extension requires new adapter contracts. | Existing worker/route tests remain passing; any extension adds focused regression tests. | Overloading runner with orchestration policy can blur boundaries and weaken determinism. |
| app-server session metadata | `needs_discovery` | Session IDs and token/turn telemetry tracked during live runs. | Candidate richer run/session telemetry linked to run/receipt lineage. | Partial run/event metadata exists; no Symphony-like full session telemetry contract in campaign docs. | Discovery task to define minimal session telemetry schema with privacy bounds. | Candidate `AgentStore` schema extensions and event contracts. | Proof that telemetry is bounded, non-secret-bearing, and lineage-linked. | Excess telemetry can leak sensitive context and create storage bloat. |
| structured logs | `adapt` | Structured context logs (`issue_id`, `session_id`, outcomes). | Existing structured runtime logging plus future control-plane-specific fields (`work_order_id`, `run_id`, `lease_id`). | Structured logging exists; worker-control-specific standard field set is not fully standardized. | Add control-plane log field conventions in future implementation tasks. | Logging helper module and tests/lint checks where available. | Evidence that logs show dispatch/skip/retry outcomes without raw secret payloads. | Inconsistent fields weaken operator diagnosis and auditability. |
| optional status surface | `already_implemented` | Optional dashboard/terminal status view for operators. | Command Center worker-control panel and recommendation/work-order visibility surface. | UI surface exists; live proof is partially incomplete for end-to-end command-center runtime rendering. | Preserve as operator truth surface; do not treat as completion proof by itself. | Existing frontend feature modules/tests plus future proof artifacts. | UI proof + backend route proof aligned; explicit limitations documented when blocked. | Status UI can drift from backend truth if route/event semantics are not aligned. |
| tracker writes handled by agent/tooling rather than orchestrator | `adopt` | Orchestrator reads/schedules; ticket writes happen through agent tools. | Align with Guardian command-bus/tooling boundary for future tracker writes. | No tracker integration yet; boundary is compatible with current architecture direction. | Adopt as guiding policy for future tracker integration unless a future ADR changes it. | Future tracker tool contracts in command-bus/tooling layer. | Proof that orchestrator remains read/schedule/reconcile only while writes are bounded and auditable. | Boundary creep can unintentionally turn orchestrator into business-logic mutation authority. |
| handoff states such as `Human Review` | `adapt` | Successful run can stop at non-terminal handoff state. | Existing proposed states and receipt fields (`merge_ready`, `human_review_required`, `escalated`). | Present in campaign contracts; not fully implemented as end-to-end dispatch lifecycle behavior. | Preserve and formalize handoff tokens in future dispatch/reconciliation tasks. | `guardian/agents/work_orders.py`, receipt/store contracts, route tests. | State-machine and receipt tests prove handoff states are explicit and auditable. | Handoff ambiguity can cause false completion claims or premature closure. |

## Recommended adoption path
1. Keep current Phase 0-8 campaign direction unchanged for initial manual worker-control proof.
2. Add optional future adaptation work as a separate phase (external tracker/workflow adaptation), not as a hidden extension to current phases.
3. Preserve these hard boundaries in all follow-up tasks:
   - WorkOrder API remains durable intake source-of-truth.
   - Lease contract/store remains workspace authority.
   - Orchestrator remains deterministic policy logic, not persona autonomy.
   - Tracker writes remain bounded tool/command-bus concern.
4. Treat `WORKFLOW.md` concepts as candidate policy input, gated by discovery, schema allowlists, and explicit Guardian ownership.

## Explicit non-adoptions
- Do not adopt Symphony in-memory orchestrator state as Codexify durable truth.
- Do not bypass WorkOrder API with direct tracker-to-dispatch mutation.
- Do not bypass lease contract/store with ad hoc workspace provisioning.
- Do not import arbitrary workspace shell hooks without Guardian policy enforcement.
- Do not treat Symphony as normative architecture authority over Codexify current-state docs and ADRs.

## Future task candidates
1. Define external tracker ingestion contract that maps tracker issues into durable WorkOrders.
2. Define bounded repository-owned workflow policy file schema (if any) with allowlisted keys.
3. Add deterministic lease allocator contract (identifier -> branch/worktree path) within existing lease boundaries.
4. Add durable retry/reconciliation state contract for external-ingestion workflows.
5. Add explicit dispatch concurrency governor and backoff policy after dispatch route exists.
6. Standardize worker-control structured log fields and bounded session telemetry contract.
7. Add reconciliation stop-condition proofs for state transitions into handoff/terminal outcomes.

## Risks and cautions
- Architectural drift risk: importing Symphony semantics directly can bypass Codexify's existing Guardian-mediated contracts.
- State-authority risk: in-memory-first orchestration semantics conflict with durable/auditable control-plane truth.
- Security risk: unrestricted workflow hooks can weaken policy boundaries and increase command-surface exposure.
- Observability risk: UI/status visibility can be mistaken for completion without durable receipt/lineage proof.
- Scope risk: external tracker features can expand release promises unless explicitly marked optional and deferred.

## Open questions
1. Should future workflow policy files be parsed server-side only, or route-scoped with explicit signing/ownership metadata?
2. Which minimal tracker fields are required for WorkOrder ingestion without importing full Linear semantics into durable schema?
3. Should retry orchestration be represented as explicit durable rows or embedded in WorkOrder/run status transitions?
4. Which handoff tokens should be canonicalized first (`human_review_required`, `merge_ready`, `blocked`, `escalated`) under runtime token discipline?
5. What is the minimum viable reconciliation cadence model (event-driven, polling, hybrid) that preserves deterministic behavior and operator visibility?

## ADR impact classification
- Classification: No ADR impact.
- Governing ADRs/contracts for interpretation:
  - [ADR-020](../../../architecture/adr/020-guardian-mediated-coding-agent-execution-contract.md)
  - [ADR-022](../../../architecture/adr/022-guardian-intent-spine-and-cross-surface-control-plane.md)
  - [Runtime Protocol Token Contract](../../../architecture/runtime-protocol-token-contract.md)
- Reason: this artifact is adaptation analysis only and introduces no runtime semantic change.
