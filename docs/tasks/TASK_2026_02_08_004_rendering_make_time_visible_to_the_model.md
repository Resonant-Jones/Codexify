TASK-2026-02-08-004 — Rendering: make time visible to the model

Goal: Prevent “soup perception” by anchoring each memory line.
This change belongs in: the function that formats context sent to the model (context packer / prompt builder / broker).
Instructions:
 1. Prefix each message with:
 • timestamp (source_created_at preferred)
 • thread label (thread id or human label if available)
 • turn_index
 • role
 2. Keep formatting stable and compact:
 • [YYYY-MM-DD HH:MM | thread:<id> | turn:<n> | <role>] <text>
 3. Do not change retrieval semantics here—only formatting.

Tests: pytest -v (backend) + snapshot/format test if you have a pattern for that.
Git:

git add <rendering_files_here> <test_files_here>
git commit -m "Context: render migrated memories with explicit chronological anchors"

Expected Output:
 • Summary of formatting changes
 • Test results
 • Commit hash

# TASK-2026-02-08-004 — Rendering: make time visible to the model

## Goal
Prevent “soup perception” by anchoring each memory line with explicit chronological metadata so the model perceives ordered history.

## This change belongs in
The function/module that formats context sent to the model (context packer / prompt builder / broker).

(Use the repo’s existing context formatting entrypoint—do not create a parallel renderer.)

## Instructions

### 1) Add explicit chronological anchors (required)
When rendering any migrated message (and ideally all messages), prefix each line with:

- timestamp (prefer `source_created_at`)
- thread label (`source_thread_id` or a human label if available)
- `turn_index`
- role (`user|assistant|system|tool`)

### 2) Stable, compact format (required)
Use a consistent, compact format. Example:

- `[YYYY-MM-DD HH:MM | thread:<id> | turn:<n> | <role>] <text>`

Rules:
- Do not vary field order across messages.
- Use a stable timestamp representation (UTC/ISO or local; choose one and keep it consistent).
- Truncate text safely if needed (do not exceed the context formatter’s expected limits).
- Preserve original message text content (no rewriting).

### 3) Fallback behavior (required)
Messages may have partial metadata. Render with safe fallbacks:

- If `source_created_at` is missing:
  - use `imported_at` if present; otherwise render `timestamp:unknown`
- If `turn_index` is missing:
  - render `turn:?`
- If thread id is missing:
  - render `thread:unknown`
- If role is missing:
  - render `role:unknown`

Do not drop messages solely due to missing fields.

### 4) Scope boundary
- Do not change retrieval semantics here (TASK-003 handles retrieval).
- Do not change migration logic (TASK-001).
- Do not add indexes/constraints (TASK-002).
- Do not add era tagging policy (TASK-005).
- This task is formatting-only.

## Tests
Backend tests:

```bash
pytest -v
```

Add/extend a format-oriented test (follow existing patterns in the repo):
- Given a small set of messages with known `source_created_at/source_thread_id/turn_index/role`, verify rendered output matches the expected stable format.
- Include at least one fallback case (missing timestamp or turn_index) to ensure deterministic rendering.
- Prefer snapshot-style tests if the repo already uses them; otherwise assert string equality.

## Post-run verification (required)
- Verify output is stable across runs for the same input.
- Verify every rendered line includes the anchor bracket prefix.

## Git
```bash
git add <rendering_files_here> <test_files_here>
git commit -m "Context: render migrated memories with explicit chronological anchors"
```

## Expected Output
- Summary of formatting changes (module/function name)
- Test results
- Commit hash