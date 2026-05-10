# 03 Worktree Lease Contract (Proposed)

## Purpose
Define the proposed branch/worktree lease envelope that gives each worker run an isolated mutable workspace with explicit lifecycle and cleanup policy.

## Contract status
- Contract types and validation helpers now exist in code.
- Durable lease store operations now exist in code.
- Coding worker now honors lease-bound execution when lease context is provided.
- Runtime allocation and Git branch/worktree creation are still not implemented.

## Implementation anchor
- `guardian/agents/worktree_leases.py`
- `guardian/agents/worktree_lease_store.py`
- `guardian/workers/coding_worker.py`
- `guardian/db/models.py`
- `guardian/db/migrations/versions/8c9d0e1f2a3b_add_worktree_leases.py`
- The contract anchor provides canonical tokens, request/contract/result shapes, validation helpers, and durable storage lifecycle methods.
- It now includes worker-side lease resolution and lease-bound cwd enforcement.
- It does not allocate filesystem worktrees, create Git branches, execute commit/merge policy, or expose API/UI behavior.

## Required fields
- `lease_id`: unique lease identifier.
- `work_order_id`: owning work-order identity.
- `run_id`: run attempt identity bound to the lease.
- `worker_id`: worker instance identity.
- `base_ref`: immutable source ref used to create branch/worktree.
- `branch_name`: worker-owned branch for this lease.
- `worktree_path`: absolute lease workspace path.
- `status`: lease lifecycle token (`active`, `expired`, `released`, `abandoned`, `cleanup_pending`, `cleaned`, `blocked`, `failed`).
- `created_at`: lease creation timestamp.
- `expires_at`: lease expiry timestamp used for stale detection.
- `preserve_on_failure`: boolean policy for retaining workspace for human review.
- `cleanup_policy`: policy token for cleanup behavior (`cleanup_on_merge`, `preserve_on_fail`, `manual_cleanup_required`).
- `last_heartbeat_at`: latest worker liveness heartbeat.

## Lifecycle rules
1. A lease is created only from `ready` work order state.
2. A lease binds one `work_order_id` to one branch/worktree mutable namespace.
3. Retries for the same run family occur inside the same lease unless policy explicitly re-issues.
4. Lease heartbeats update `last_heartbeat_at` while worker is active.
5. Lease expiration triggers recovery or escalation, not silent reassignment.

## Cleanup rules
### Successful merge cleanup
- On `merge_ready -> merged`, cleanup is attempted automatically per `cleanup_on_merge` policy.
- Cleanup evidence should include branch disposition and worktree removal result.
- Cleanup failure does not rewrite merge outcome; it opens cleanup follow-up state.

### Failed validation preserve/cleanup policy
- If `preserve_on_failure=true`, worktree remains for review and is marked `cleanup_pending`.
- If `preserve_on_failure=false`, cleanup can run immediately after terminal failure.
- Regardless of policy, receipt must capture whether workspace was preserved or removed.

### Abandoned lease recovery
- If heartbeat expires and run is nonterminal, lease enters `abandoned` candidate state.
- Recovery requires policy check and no evidence of active worker ownership.
- Reassignment must create a new lease; abandoned lease remains auditable.

### Conflict handling
- Branch/worktree collision at creation time is terminal for the lease request (`blocked` or `failed` with reason).
- Recovery may synthesize a deterministic suffix, but only if policy marks it safe and auditable.
- Cross-lease branch reuse is forbidden unless prior lease is terminal and cleaned or preserved by policy.

## Invariant: no shared mutable worktree
- No two live worker runs may mutate the same `worktree_path`.
- No two live worker runs may push commits to the same active lease branch simultaneously.
- Read-only inspection of a preserved lease is allowed; mutable reuse is not.

## Durable and transient aspects
- Durable: lease identity, owner bindings, policy fields, timestamps, terminal cleanup outcome.
- Transient: heartbeat freshness, runtime process liveness, local filesystem contention events.
