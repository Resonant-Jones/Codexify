# 00 Current Shape

## Purpose
Capture what is true now for Guardian-mediated coding-worker behavior and what remains unbuilt for a full automated worker control plane.

## Current implementation baseline
1. Adapter selection exists for coding execution (`adapter_kind` with registry-backed resolution).
2. Coding-worker validation can produce normalized evidence (status, exit code, fail signature, bounded output previews).
3. Single-attempt validation remains the default behavior when no retry budget is configured.
4. Bounded validation retry support exists as a supervised loop (capped attempts, explicit stop conditions).
5. Coding results return through Guardian result lineage before user-visible finalization.
6. Durable state is Postgres-centric and queue/task transport is Redis-backed.
7. Acceptance semantics remain explicit: accepted route/task is not completion.

## Explicitly unbuilt surfaces
1. Worktree lease system (branch/worktree lifecycle contract is not yet runtime-owned).
2. Commit-after-green gate (no enforced commit gate contract in worker runtime yet).
3. Durable task board/work-order system for coding workers.
4. Orchestrator next-task selector for safe autonomous sequencing.
5. Merge-candidate workflow with policy gates and review states.
6. Operator/UI inspection surface dedicated to worker-run ledgers and receipts.

## Design constraints carried forward
1. Guardian remains owner of request identity, policy, transcript lineage, worker events, and result receipts.
2. Canonical token discipline must be preserved for statuses/events/contracts.
3. Bounded evidence should be normalized; raw unbounded logs are diagnostics, not control-plane truth.
4. Queue acceptance and task creation do not prove dequeue, success, or delivery visibility.

## Do not claim
- Do not claim autonomous coding convergence exists.
- Do not claim a worktree lease allocator exists.
- Do not claim commit-on-green or merge automation is live.
- Do not claim a scheduler/orchestrator currently chooses next coding tasks.
- Do not claim an inspection command center for worker runs is implemented.
- Do not claim production readiness for automated workers.
- Do not claim release promise changes from this campaign.
