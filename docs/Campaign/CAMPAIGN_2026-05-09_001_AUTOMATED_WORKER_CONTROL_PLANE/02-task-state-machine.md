# 02 Task State Machine (Proposed)

## Purpose
Define a proposed state vocabulary and transition policy for `WorkOrder` lifecycle management. This is a future contract sketch, not current runtime behavior.

## Proposed states
- `draft`
- `ready`
- `leased`
- `running`
- `validating`
- `retrying`
- `passed`
- `failed`
- `blocked`
- `escalated`
- `merge_ready`
- `merged`
- `archived`
- `cancelled`

## Implementation note
- Canonical work-order status tokens and transition validation now exist in code at `guardian/agents/work_orders.py`.
- Durable work-order rows now persist status values in `coding_work_orders` via `guardian/agents/work_order_store.py`.
- This phase does not claim full worker-driven lifecycle progression for every state.

## Allowed transitions
1. `draft -> ready` when objective/scope/dependencies are defined.
2. `ready -> leased` when an exclusive `WorktreeLease` is granted.
3. `leased -> running` when worker run starts under lease.
4. `running -> validating` when adapter execution returns success-like result and validation is configured.
5. `validating -> retrying` when validation fails and retry budget remains.
6. `retrying -> running` when next bounded attempt starts in the same lease.
7. `validating -> passed` when validation passes.
8. `validating -> failed` when validation fails with no retry budget.
9. `running -> failed` when adapter/runtime execution fails before validation.
10. `running -> blocked` when policy prerequisites are missing or ambiguous.
11. `running -> escalated` when failure requires human/operator intervention.
12. `passed -> merge_ready` when commit/review prerequisites are satisfied.
13. `merge_ready -> merged` when merge policy and review gate pass.
14. `failed -> archived` when retained for history with no immediate retry plan.
15. `blocked -> ready` when blockers are resolved and re-queued.
16. `escalated -> ready` when human resolution approves another run.
17. `ready -> cancelled` when operator cancels before lease.
18. `leased -> cancelled` when operator cancels and cleanup policy executes.
19. `merged -> archived` when active lifecycle is complete.
20. `cancelled -> archived` when cleanup and audit closure are complete.

## Transition rules
- Rule 1: Only one active lease per `WorkOrder` at a time.
- Rule 2: `retrying` is bounded and must retain same `lease_id` and `worktree_path`.
- Rule 3: `passed` is validation evidence only; it does not imply merge.
- Rule 4: `merge_ready` requires explicit policy gate, not implicit pass-through.
- Rule 5: `blocked` and `escalated` are operator-visible and must include reason codes.
- Rule 6: Acceptance/queueing events are orthogonal to terminal lifecycle state.
- Rule 7: All transitions should emit canonical event tokens and durable state mutation.

## Forbidden transitions
1. `draft -> running` (must become `ready` then `leased`).
2. `ready -> running` (no run without lease).
3. `leased -> merge_ready` (must execute and validate first).
4. `running -> merged` (merge cannot bypass validation/review gates).
5. `failed -> merged` (requires new run path and new validation evidence).
6. `cancelled -> running` (must rehydrate as `ready` or new work order).
7. `archived -> running` (archived entities are immutable history).
8. `merged -> running` (post-merge reruns require new work order or explicit fork semantics).

## Ambiguity handling
If dependency state, policy state, or receipt state is ambiguous, the default behavior is fail-closed to `blocked` or `escalated`, never optimistic transition to execution.
