TASK-2026-02-08-005 (Optional) — Era tagging: “archive vs live”

Goal: Imported history behaves like an archive unless explicitly needed.
This change belongs in: migration + retrieval policy layer.
Instructions:
 1. Tag imported rows with:
 • origin="chatgpt_import" (or similar)
 • optional era="pre_codexify"
 2. Retrieval policy:
 • Prefer live data by default
 • Allow archival inclusion when highly relevant or when user asks historical questions
 3. Keep this policy minimal and testable.

Tests: pytest -v (backend).
Git:

git add <migration_files_here> <retrieval_files_here> <test_files_here>
git commit -m "Memory: tag imported history as archival and adjust retrieval policy"

Expected Output:
 • Summary of formatting changes
 • Test results
 • Commit hash

# TASK-2026-02-08-005 (Optional) — Era tagging: “archive vs live”

## Goal
Ensure imported ChatGPT history behaves like an archive by default (older “era”), so the system prefers live/local memories unless archival history is explicitly relevant.

## This change belongs in
- Migration layer (where imported messages are written)
- Retrieval policy layer (where candidates are selected/weighted)

(Use the repo’s existing migration + retrieval entrypoints; do not create parallel pipelines.)

## Instructions

### 1) Tag imported rows at ingest time (required if you run this task)
For every ChatGPT-imported message, persist:

- `origin = "chatgpt_import"` (or the repo’s equivalent field)
- `era = "pre_codexify"` (optional, but recommended if you support eras)
- Optionally, store an import batch marker:
  - `import_batch_id` or similar (helps auditing/reruns)

Idempotency rules:
- On rerun, do not overwrite an existing `origin/era` unless missing/null.
- Ensure tags are stable and do not churn.

### 2) Retrieval policy: prefer live by default, include archive when justified (required)
Update retrieval so that, when `origin="chatgpt_import"` (archival), it is not treated as equally “present” as live messages.

Implement as a minimal, testable policy:
- Default behavior:
  - Prefer non-archival (“live”) candidates.
- Allow archival inclusion when:
  - The user explicitly asks about the past / imported history, OR
  - The archival candidate is significantly more relevant than live candidates (define a threshold), OR
  - A thread-scoped continuation requires it (same thread).

Suggested simple implementation options (choose one consistent with existing code):
- **Score penalty:** apply a small relevance penalty multiplier to archival candidates (e.g. `score *= 0.85`) unless an override condition is met.
- **Two-lane retrieval:** retrieve live candidates first; if insufficient coverage, fill from archival candidates.
- **Hard filter w/ override:** exclude archival by default, include when explicitly requested.

Do not over-engineer; keep the policy minimal and reversible.

### 3) Make archival inclusion explicit in the returned metadata (recommended)
When a retrieved memory is archival:
- include `origin` and/or `is_archival=true` in the returned structure so the renderer (TASK-004) can label it if desired in the future.

### 4) Scope boundary
- Do not change migration temporal fields (TASK-001).
- Do not change stitching/sort logic (TASK-003).
- Do not change rendering format (TASK-004).
- This task is strictly tagging + retrieval selection policy.

## Tests
Backend tests:

```bash
pytest -v
```

Add/extend tests to cover:
- Imported messages are tagged with `origin="chatgpt_import"` (migration behavior).
- Retrieval prefers live by default (archival is deprioritized/filtered).
- Override behavior allows archival inclusion when conditions are met (explicit user request or strong relevance threshold).
- Idempotency: rerun does not duplicate or churn tags.

If CI lacks real imported data, use fixtures to simulate records with `origin` values.

## Post-run verification (required)
- Confirm that default retrieval does not overuse archival history when live data exists.
- Confirm that explicit “past/history/import” queries include archival candidates.

## Git
```bash
git add <migration_files_here> <retrieval_files_here> <test_files_here>
git commit -m "Memory: tag imported history as archival and adjust retrieval policy"
```

## Expected Output
- Summary of tags added and where policy is applied
- Test results (note if any archival override test is skipped)
- Commit hash