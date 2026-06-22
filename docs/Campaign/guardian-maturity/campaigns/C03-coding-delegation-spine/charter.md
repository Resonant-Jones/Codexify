# C03: Coding Delegation Spine

## Metadata

- **Campaign ID**: C03
- **Title**: Coding Delegation Spine
- **Wave**: 2
- **Status**: `in-progress`
- **Owner**: resonant_jones
- **Risk**: HIGH
- **Architecture Impact**: yes
- **Governing ADRs/Contracts**:
  - [00-current-state.md](../../../architecture/00-current-state.md)
  - [Agent Tool Loop Contract](../../../architecture/agent-tool-loop-contract.md)
  - [Pi Invocation Boundary Contract](../../../architecture/pi-invocation-boundary-contract.md)
  - [Self-Extending Agent Plugin System](../../../architecture/self-extending-agent-plugin-system.md)
  - [Runtime Protocol Token Contract](../../../architecture/runtime-protocol-token-contract.md)
  - [Chat Runtime Contract](../../../architecture/chat-runtime-contract.md)
  - [Completion Pipeline](../../../architecture/completion_pipeline.md)
  - [Flows](../../../architecture/flows.md)
  - [Modules and Ownership](../../../architecture/modules-and-ownership.md)
  - [ADR-020 Guardian Mediated Coding Agent Execution Contract](../../../architecture/adr/020-guardian-mediated-coding-agent-execution-contract.md)
  - [ADR-022 Guardian Intent Spine and Cross-Surface Control Plane](../../../architecture/adr/022-guardian-intent-spine-and-cross-surface-control-plane.md)

## Purpose

Prove and later mature the Guardian-mediated coding delegation spine from authored operator intent through work-order artifact, policy boundary, execution/validation seam, receipt/artifact return, and operator-visible proof.

## Current Truth Anchors

What is true now:
- C00 is `go` — all health/catalog/model inventory surfaces agree.
- C02 is functionally complete — authenticated chat, provider states, orphan surfacing all proven.
- C11 route audit confirmed coding work-order, delegation, command bus, and agent orchestration routes exist but are feature-gated and not runtime-verified.
- C11 confirmed Pi/Coder validation logic exists (`guardian/pi/`) but has zero route registration.
- ADR-020 defines the Guardian-mediated coding-agent execution contract (contract-only, not live execution).
- `00-current-state.md` explicitly excludes delegation, Pi/Coder execution, and federation from the release promise.

## Scope

- Coding work-order artifacts (CRUD via `coding_work_orders.py`)
- Delegation draft/plan artifacts (`delegations.py`, `guardian_delegations.py`)
- Command bus adjacency (manifest, invoke, run events)
- Pi/Coder boundary contracts (envelope, receipt, artifact, validation)
- Agent orchestration routes (plans, deployments, coding/execute)
- Agent worker and delegation worker
- Frontend coding work-order panel and hooks
- Lineage and source-thread binding
- Acceptance versus execution semantics
- Operator-visible proof surfaces

## Non-Goals

- No live Pi/Coder execution in this proof task
- No new backend routes
- No new frontend UI
- No autonomous coding-agent loop
- No command execution
- No repository mutation
- No release-claim expansion
- No graph write, federation, or cloud provider support

## Invariants

- Do not treat work-order creation as execution proof.
- Do not treat command-bus manifest presence as command execution proof.
- Do not treat command-bus invocation as Pi/Coder proof.
- Do not treat route presence as runtime proof.
- Do not treat docs or contracts as shipped runtime behavior.
- Do not widen release claims.
- Guardian remains policy, lineage, transcript, and result-return owner.

## Dependencies

- C00 (Truth Gate) — `go`
- C02 (Chat Runtime State) — functionally complete
- C11 (API Route Audit) — `go`

Campaigns this enables:
- C04 (Pi/Coder Invocation Boundary) — needs governed delegation drafts
- C09 (Execution Ledger) — needs delegation runs to track
- C10 (Recovery) — needs delegation runs to recover

## Done-When

The campaign is done when:
1. Existing route and code seams are mapped.
2. Safe proof surfaces are identified.
3. Absent blockers are named.
4. Downstream implementation tasks can be planned without guessing.
5. Coding delegation drafts can be created from threads with source lineage.
6. Delegation execution is bounded and governed.
7. Result artifacts return through Guardian mediation.

## Risks

- **HIGH**: Feature-gated routes have unknown runtime availability. Proof must verify before UI enables affordances.
- **HIGH**: Pi/Coder invocation routes don't exist — C04 is blocked on route registration.
- **MED**: Agent worker and delegation worker exist but execution semantics are unproven.
- **MED**: Command bus adjacency could be confused with coding-agent execution — must keep boundaries explicit.

## Task Queue

Tasks are tracked in [`backlog.md`](./backlog.md).
