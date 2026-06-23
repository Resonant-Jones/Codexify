# Wave 4 Selection After C07 Closeout

## Gate Decision

**`go`** — Selected: **C09: Pi/Coder Execution Authority**

## Scope

This is a docs-only campaign selection artifact. It selects the next Guardian Maturity campaign after C07 closeout. It does **not** implement C09, add execution authority, start C10 or C11, modify runtime behavior, or widen release support.

## Current Guardian Maturity Trail

| Campaign | Status | Proof Layer | Remaining Boundary |
|----------|--------|-------------|--------------------|
| C03 | closed | Delegation spine — work orders, command runs, receipts | — |
| C04 | closed | Invocation boundary — contracts, dry-run route, evidence adapter | No execution authority |
| C05 | closed | Tool turn observability — bounded evidence, redaction | — |
| C06 | closed | Operator workspace — composed read-only truth surfaces | — |
| C08 | closed | Local runtime spine — endpoint health, model identity, context fidelity, operator truth | No live daemon availability proof |
| C07 | closed | Persona Studio V1 — bounded config surface, no memory/chat/execution | — |

## Board State After C07

### What Is True

- Delegation spine is closed.
- Invocation boundary exists but remains contract-only (C04).
- Tool turn observability is closed.
- Operator workspace is closed.
- Local runtime spine is closed.
- Persona Studio V1 boundary is closed.
- C09/C10/C11 remain deferred.
- Execution authority remains unimplemented.

### What Is Not Yet True

- No governed execution authority.
- No Pi/Coder execution.
- No result return lineage beyond C04 bounded surfaces.
- No sandbox worker proof.
- No tool execution authority.
- No daemon execution authority.
- No autonomous workflow execution.
- No widened release support.

## Candidate Slate

| Candidate | Readiness | Dependencies | Risk | Decision |
|-----------|-----------|-------------|------|----------|
| C09: Pi/Coder Execution Authority | C04 boundary + C07 config + C08 runtime proven | C04 + C07 + C08 | HIGH | **Selected** |
| C10: Pi/Coder Result Return & Receipt Lineage | Needs C09 first | C09 | MED | Deferred |
| C11: Pi/Coder Sandbox Worker | Needs C09 first | C09 + C10 | HIGH | Deferred |
| Stabilizing: recovery/repair tooling | Independent | None | LOW | Not selected |
| Stabilizing: auth/session hardening | Independent | None | LOW | Not selected |
| Stabilizing: observability hardening | Independent | None | LOW | Not selected |

### Why C09 Now

C04 proved the invocation boundary but intentionally stopped before execution. C07 proved Persona Studio config/permission/retrieval boundaries. C08 proved the local runtime spine. C03/C05/C06 provide delegation, observability, and operator surface context. The system has enough boundary proof to begin C09 as an audit/contract campaign — not as immediate execution implementation.

C10 and C11 both depend on first defining and proving governed execution authority. Stabilizing campaigns remain available but are not the sharpest lever after C04/C07/C08 closure.

### Why Not Stabilizing

Recovery/repair, auth/session, and observability hardening are valuable but can be rotated in if C09 audit discovers blocking architecture debt. They should not preempt the highest-value deferred boundary.

## Selection Decision

**Selected: C09: Pi/Coder Execution Authority**

## C09 Risk Posture

| Classification | Value |
|---------------|-------|
| Risk | **HIGH** |
| Architecture impact | Architecture-impacting |
| Must begin with | Audit and contract proof |
| Must not begin with | Execution implementation |

The cage door does not open in the selection task. The first C09 task must be a current-state and authority-seam audit. Any execution path must require explicit acceptance semantics, proof surfaces, operator-visible truth, and non-silent failure handling before runtime behavior changes.

## Architecture-Impact Classification

- **Classification**: Aligned with existing ADR(s) / architecture contracts
- **Governing contracts**: Current State, Pi Invocation Boundary Contract, Agent Tool Loop Contract, Agent Protocol Operations, Self-Extending Agent Plugin System, Runtime Protocol Token Contract, Chat Runtime Contract, Chat Runtime State Contract, Router Decision Table, Config and Ops, Modules and Ownership, Data and Storage, Account Export + Restore Contract, C03/C04/C05/C06/C08/C07 closeouts
- **Brief reason**: Selecting C09 changes campaign focus to governed execution authority. This is architecture-impacting, but this task records selection only and does not modify accepted runtime behavior.

## Current-Truth Anchors

- **What is true now**: C09 is selected only after this artifact gates `go`. Execution authority is not implemented by this task. C10 and C11 remain deferred. C09 must start with audit/contract proof, not implementation.
- **What is not yet true**: C09 is not implemented. Pi/Coder execution is not implemented. C10/C11 are not started.
- **What the next C09 task may assume**: It may inspect docs and repo seams. It may create a C09 seam audit artifact. It may name future C09 tasks by name only.
- **What the next C09 task must not assume**: It must not assume execution authority exists. It must not assume execution implementation can begin without audit/contract proof.

## Invariants

- No execution authority in this task.
- No Pi/Coder execution in this task.
- No command-bus execution behavior change.
- No tool execution behavior change.
- No daemon control behavior change.
- No result-return lineage claim.
- No sandbox worker claim.
- No memory/chat-history/permission/provider/retrieval change.
- No release claim widening.
- C10 remains deferred.
- C11 remains deferred.
- First C09 task must be audit/contract proof only.

## Proof Surfaces Required Before C09 Implementation

C09 must establish:

- Authority seam map
- Current dry-run route map
- Accepted invocation contract
- Operator approval or acceptance contract
- Command-bus execution boundary
- Failure/timeout/cancel semantics
- Evidence receipt requirements
- Audit log requirements
- Security and permission boundary
- Memory/chat-history boundary
- Provider/runtime boundary
- Result non-forgery boundary
- Rollback/recovery posture
- Tests required before runtime execution changes

## Deferred Campaigns

| Campaign | Reason |
|----------|--------|
| C10: Result Return & Receipt Lineage | Depends on defining governed execution authority first |
| C11: Sandbox Worker | Depends on C09 + C10 |
| Stabilizing campaigns | Available if C09 audit discovers blockers |

## Final Gate

- **Decision**: `go`
- **Next task by name only**: `C09-T001: Pi/Coder execution authority current-state and seam audit`
