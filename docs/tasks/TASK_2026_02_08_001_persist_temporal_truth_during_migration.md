
# TASK-2026-02-08-001 — Persist temporal truth during migration

## Goal
Capture timestamps + stable ordering at import time so migrated history can be reconstructed chronologically (no “legacy chat soup”).

## This change belongs in
`/backend/rag/chatgpt_migration.py` (or the exact migration ingestion file that inserts chat messages).

## Instructions

### 1) Persist required temporal fields for every imported message
Ensure every imported message persists:

- `source_created_at` (original ChatGPT timestamp)
- `imported_at` (Codexify ingestion time)
- `source_thread_id` (ChatGPT conversation id)
- `source_message_id` (ChatGPT message node id; stable per export)
- `turn_index` (deterministic per thread; do not depend solely on timestamp)
- `role` (`user|assistant|system|tool`)

### 2) Determinism rules (required)
These rules must be deterministic across reruns on the same export.

**2.1 `source_created_at` derivation precedence**
- Prefer the message-level timestamp from the ChatGPT export (the canonical field used by the migrator).
- If missing, fall back to the conversation-level timestamp (if present).
- If still missing, set `source_created_at = imported_at` and mark the row as inferred (e.g., `source_created_at_inferred=true` or equivalent).

**2.2 Canonical timeline linearization for tree/DAG exports**
ChatGPT exports can be a tree/DAG. For v1, compute a single canonical “mainline” timeline:

- Identify the conversation’s active leaf/current node (as represented in the export).
- Walk parent pointers from that node back to the root.
- Reverse to get a stable root → leaf sequence.
- Assign `turn_index = 0..n-1` along that mainline path.

Non-canonical branches:
- Do not interleave branches into the mainline ordering in v1.
- (Optional for later) Branch content may be imported with a `branch_id` and `branch_turn_index`, but it must not disturb the canonical `turn_index`.

**2.3 Idempotency keys and rerun behavior**
- Treat `source_message_id` as the stable idempotency key for a migrated message.
  - If needed, use `(source_thread_id, source_message_id)` as a composite key.
- On rerun:
  - Do not churn/renumber existing `turn_index` values unless they are missing/null.
  - Do not overwrite an existing `imported_at` unless it is missing/null.
  - Updates should be additive (fill missing fields) rather than destructive.

**2.4 Role mapping**
Map export roles into the canonical set: `user|assistant|system|tool`.
- If an unknown role is encountered, store the raw role (e.g. `source_role_raw`) and map to a safe fallback (prefer `tool` or `system`, whichever is more appropriate for your schema).

### 3) Scope boundary
Do not alter retrieval or rendering in this task.

## Tests
Backend tests:

```bash
pytest -v
```

## Post-run verification (required)
After running the migration, run or validate equivalent checks:

- **No silent null time:** `source_created_at` is never null (or is explicitly tracked as inferred).
- **Ordering sanity:** for each `source_thread_id`, `turn_index` is contiguous and stable.
- **Idempotency:** no duplicates for the idempotency key (`source_message_id` or composite key).

(Use the repo’s actual table/column names for the verification queries.)

## Git
```bash
git add backend/rag/chatgpt_migration.py
git commit -m "Migration: persist source timestamps and turn ordering"
```

## Expected Output
- Summary of fields added/ensured during insert
- Test results
- Commit hash
