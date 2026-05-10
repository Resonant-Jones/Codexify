# 05 Orchestrator Policy (Proposed)

## Purpose
Define the orchestrator as deterministic policy/control logic that recommends or dispatches safe next work, without introducing a persona-style autonomous authority model.

## Contract status
Partially implemented in Phase 6:
- Deterministic recommendation policy exists in `guardian/agents/orchestrator_policy.py`.
- Recommendation route exists at `GET /api/coding/orchestrator/next`.
- Dispatch remains unimplemented.

## Implementation anchor
- `guardian/agents/orchestrator_policy.py`
- `guardian/routes/coding_work_orders.py` (`/api/coding/orchestrator/next`)
- `guardian/tests/agents/test_orchestrator_policy.py`
- `guardian/tests/routes/test_coding_work_orders.py`

## Policy inputs
- Work-order lifecycle state.
- Dependency graph (`TaskDependency`).
- Latest worker receipts and validation receipts.
- Lease availability and conflict signals.
- Human review gate status.
- Merge-candidate status where applicable.

## How next task is selected
1. Filter to `ready` work orders whose dependencies are satisfied.
2. Exclude work orders that conflict on active file scopes or branch/worktree ownership.
3. Prefer tasks with highest policy priority and lowest ambiguity.
4. Require explicit skip reasons for non-selected ready tasks.
5. Emit explicit recommendation/skip decisions with bounded reason codes.

## Dependency behavior
- Hard dependencies block transition from `draft/ready` to `leased`.
- Soft dependencies can still allow recommendation with explicit risk tag.
- Circular or unresolved dependency graphs force `blocked` until human resolution.

## Blocked/escalated handling
- `blocked` tasks require explicit blocker reason and suggested unblock actions.
- `escalated` tasks require human/operator resolution before redispatch.
- Re-dispatch from `escalated` must reference a resolved review gate or decision record.

## Concurrency and conflicting edits
- Orchestrator should avoid concurrent dispatch for tasks with overlapping mutable file scope.
- Overlap detection can use declared file scope hints + observed receipt-level touched files.
- Conflict uncertainty defaults to fail-closed (`blocked` or recommendation-only).

## Ambiguity stop rule
When key control-plane facts are ambiguous (state mismatch, missing receipt lineage, dependency uncertainty, lease contention without clear owner), orchestrator stops and emits recommendation-only output with required human follow-up.

## Recommendation vs execution authority
- Recommendation: proposes next action and rationale; does not change runtime state.
- Dispatch authority: explicitly granted policy path that enqueues/leases a run.
- Every dispatch must cite decision lineage and respect Guardian policy boundary.

Current implementation note:
- Recommendation behavior is live in backend policy + route.
- Dispatch behavior is intentionally deferred.

## Non-goals
- No anthropomorphic planner behavior.
- No hidden retries outside bounded worker policy.
- No silent merge execution.
- No bypass of human review gates.
