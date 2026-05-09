# 04 Worker Receipt Contract (Proposed)

## Purpose
Define the structured terminal receipt returned by a coding worker run so orchestration, human review, and follow-up decisions operate on bounded normalized evidence.

## Contract status
Proposed only. Not implemented.

## Required fields
- `work_order_id`
- `run_id`
- `lease_id`
- `adapter_kind`
- `branch_name`
- `worktree_path`
- `files_changed`
- `validation_command`
- `validation_results`
- `final_validation_status`
- `final_fail_signature`
- `commit_hash`
- `stop_reason`
- `merge_ready`
- `human_review_required`
- `next_suggested_actions`
- `created_at`

## Field notes
- `files_changed`: bounded list or digest, not unbounded patch payload.
- `validation_results`: normalized attempt list (status, exit code, bounded previews, timestamps).
- `final_validation_status`: canonical token (`passed`, `failed`, `not_run`, `error`).
- `final_fail_signature`: deterministic token/string for failure clustering when available.
- `stop_reason`: canonical terminal reason token.
- `next_suggested_actions`: recommendation list; never implicit execution authority.

## Evidence constraints
1. Receipt evidence must be bounded and normalized.
2. Receipts must not include secrets, API keys, auth headers, or credential-bearing env values.
3. Receipts must not embed unbounded stdout/stderr logs.
4. Receipts must preserve lineage keys (`work_order_id`, `run_id`, `lease_id`) for deterministic replay and audit.

## Ownership and durability
- Ownership: worker produces; Guardian ingests and persists.
- Durable truth: receipt row plus linked validation receipts.
- Non-durable adjuncts: verbose raw logs, transient console output, process memory context.

## Recommended envelope extension fields
- `receipt_id`
- `attempt_count`
- `event_sequence_high_watermark`
- `provenance` (source thread/message references)

These extensions are optional for v1 planning and remain outside current implementation scope.
