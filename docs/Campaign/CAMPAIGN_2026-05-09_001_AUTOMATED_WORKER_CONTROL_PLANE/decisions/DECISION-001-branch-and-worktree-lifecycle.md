# DECISION-001 Branch and Worktree Lifecycle

## Status
Accepted for campaign planning.

## Date
2026-05-09

## Decision
1. One `WorkOrder` should receive one branch/worktree lease for mutable execution.
2. Validation retries should occur inside the same leased worktree unless policy explicitly requires re-leasing.
3. Commits should occur only after green validation (implemented in a future phase).
4. Cleanup should occur after successful merge under explicit cleanup policy.
5. Failed runs should preserve workspace when human review is required.
6. No shared mutable worktree is allowed between concurrent workers.

## Rationale
- Maintains deterministic provenance between task, run, branch, and filesystem state.
- Reduces cross-run interference and race conditions.
- Keeps retry evidence and failure context localized for human inspection.
- Supports bounded cleanup and recovery behavior without hiding operational debt.

## Consequences
- Requires durable lease lifecycle tracking.
- Requires explicit policy for lease expiry, abandonment, and cleanup failures.
- Increases storage/ops surface area for branch/worktree metadata.

## Deferred implementation
- Lease allocator runtime behavior.
- Cleanup executor implementation details.
- Merge gate integration and human review UX.
