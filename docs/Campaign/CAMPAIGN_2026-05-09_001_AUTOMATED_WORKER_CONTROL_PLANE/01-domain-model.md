# 01 Domain Model (Proposed)

## Scope
This model is a proposed control-plane shape for future implementation. It is not a statement of current runtime entities.

## WorkOrder
- Purpose: Durable unit of planned coding work that can be queued, leased, executed, and reviewed.
- Proposed fields: `work_order_id`, `campaign_id`, `title`, `objective`, `scope`, `priority`, `status`, `dependency_policy`, `created_by`, `created_at`, `updated_at`, `cancel_reason`.
- Lifecycle ownership: Guardian control-plane intake and policy boundary.
- Durable vs ephemeral: Durable.
- Implementation anchor: `guardian/agents/work_orders.py`, `guardian/agents/work_order_store.py`, `guardian/routes/coding_work_orders.py`.
- Durable storage table/module: `coding_work_orders` via `guardian/agents/work_order_store.py`.

## WorkerRun
- Purpose: Attempt-scoped execution record for a `WorkOrder`.
- Proposed fields: `run_id`, `work_order_id`, `attempt_index`, `worker_id`, `adapter_kind`, `status`, `started_at`, `completed_at`, `stop_reason`, `receipt_id`.
- Lifecycle ownership: Coding worker runtime under Guardian-issued envelope.
- Durable vs ephemeral: Durable with event-stream side channel.
- Future likely storage table or module: `coding_worker_runs` plus run-event append path.
- Implementation status: still represented through existing run/deployment seams; no task-board run table/API was added in this phase.

## WorktreeLease
- Purpose: Enforce isolated branch/worktree ownership for one run at a time.
- Proposed fields: `lease_id`, `work_order_id`, `run_id`, `worker_id`, `base_ref`, `branch_name`, `worktree_path`, `status`, `created_at`, `expires_at`, `last_heartbeat_at`, `cleanup_policy`, `preserve_on_failure`.
- Lifecycle ownership: Guardian policy allocator + worker heartbeat updates.
- Durable vs ephemeral: Durable state with heartbeat freshness as ephemeral signal.
- Future likely storage table or module: `coding_worktree_leases` and lease manager module under `guardian/agents/`.

## ValidationReceipt
- Purpose: Bounded normalized record of validation command execution.
- Proposed fields: `validation_receipt_id`, `run_id`, `attempt_index`, `command`, `status`, `exit_code`, `fail_signature`, `stdout_preview`, `stderr_preview`, `started_at`, `finished_at`.
- Lifecycle ownership: Worker validation subsystem.
- Durable vs ephemeral: Durable normalized record; full logs remain ephemeral or separately gated.
- Future likely storage table or module: `coding_validation_receipts` + normalization helpers in `guardian/agents/test_results.py`.

## WorkerReceipt
- Purpose: Terminal structured receipt summarizing run outcome and proof-critical evidence.
- Proposed fields: `receipt_id`, `work_order_id`, `run_id`, `lease_id`, `adapter_kind`, `status`, `files_changed`, `validation_summary`, `commit_hash`, `merge_ready`, `human_review_required`, `next_actions`, `created_at`.
- Lifecycle ownership: Worker finalization path with Guardian ingestion boundary.
- Durable vs ephemeral: Durable.
- Future likely storage table or module: `coding_worker_receipts` persisted via `AgentStore`-style seam.

## MergeCandidate
- Purpose: Represent a run output that is eligible for human or policy-driven merge flow.
- Proposed fields: `merge_candidate_id`, `work_order_id`, `run_id`, `branch_name`, `commit_hash`, `status`, `review_state`, `policy_checks`, `created_at`, `updated_at`.
- Lifecycle ownership: Guardian merge policy module with human review gate.
- Durable vs ephemeral: Durable.
- Future likely storage table or module: `coding_merge_candidates` and policy evaluator module.
- Implementation status: not implemented in this phase.

## OrchestratorDecision
- Purpose: Durable policy decision stating why a specific next action was recommended or dispatched.
- Proposed fields: `decision_id`, `campaign_id`, `work_order_id`, `decision_kind`, `decision_reason`, `inputs_digest`, `recommended_action`, `dispatch_authority`, `created_at`.
- Lifecycle ownership: Orchestrator policy engine (not persona).
- Durable vs ephemeral: Durable decision summary with optional ephemeral scoring details.
- Future likely storage table or module: `coding_orchestrator_decisions` in a control-plane policy package.
- Implementation status: not implemented in this phase.

## Campaign
- Purpose: Top-level planning container for related work orders and rollout phases.
- Proposed fields: `campaign_id`, `name`, `goal`, `phase`, `status`, `owner`, `created_at`, `updated_at`, `notes_ref`.
- Lifecycle ownership: Human/operator governance with Guardian-tracked state.
- Durable vs ephemeral: Durable.
- Future likely storage table or module: `coding_campaigns` or docs-backed registry with sync seam.

## TaskDependency
- Purpose: Declare prerequisite edges between work orders.
- Proposed fields: `dependency_id`, `work_order_id`, `depends_on_work_order_id`, `dependency_type`, `satisfaction_status`, `created_at`.
- Lifecycle ownership: Planning/control-plane rules.
- Durable vs ephemeral: Durable.
- Future likely storage table or module: `coding_task_dependencies`.

## HumanReviewGate
- Purpose: Explicit hold point requiring operator decision before merge or next sensitive action.
- Proposed fields: `gate_id`, `work_order_id`, `run_id`, `gate_reason`, `required_role`, `status`, `opened_at`, `resolved_at`, `resolved_by`, `resolution_note`.
- Lifecycle ownership: Human operator with Guardian enforcement.
- Durable vs ephemeral: Durable.
- Future likely storage table or module: `coding_human_review_gates`.

## Boundary notes
- Source-of-truth ownership: Postgres for durable control-plane state; Redis/events for transient delivery and progress signaling.
- Consistency target: request acceptance is immediate, while run/receipt/merge state is eventual but durable.
- Identity binding: all entities must remain tied to Guardian-resolved actor and provenance lineage.
