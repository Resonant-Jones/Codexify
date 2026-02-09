TASK-2026-02-08-003 — Retrieval: relevance → stitch window → sort chronologically

Goal: Convert “relevant hits” into coherent ordered context.
This change belongs in: the memory/retrieval service that assembles context for the LLM (e.g. /guardian/... retrieval module).
Instructions:
 1. After semantic retrieval returns message IDs (top-K):
 • For each hit, fetch neighbors within the same thread via turn_index window (±N turns) or time window (±T minutes).
 2. Deduplicate, then sort results by:
 • (source_created_at, turn_index) with safe fallbacks if timestamps missing.
 3. Return a single ordered context block (or structured list) suitable for rendering.

Tests: pytest -v (backend) + add unit test for stitching/sorting.
Git:

git add <retrieval_module_files_here> <test_files_here>
git commit -m "Memory: stitch neighbor windows and sort context chronologically"

Expected Output:
 • Summary of retrieval behavior change
 • Test results
 • Commit hash

# TASK-2026-02-08-003 — Retrieval: relevance → stitch window → sort chronologically

## Goal
Convert “relevant hits” into coherent, chronologically ordered context so memories feel like a timeline instead of legacy chat soup.

## This change belongs in
The memory/retrieval service that assembles context for the LLM (e.g. a `/guardian/...` retrieval module).

(Use the repo’s existing retrieval entrypoint—do not create a parallel retrieval pipeline.)

## Instructions

### 1) Implement a two-phase retrieval pipeline (required)
**Phase A — semantic relevance**
1. Perform the existing semantic retrieval and obtain top-K hits (message IDs + their thread IDs if available).
2. Preserve the similarity score (or whatever relevance score exists) for diagnostics only; do not sort final output purely by similarity.

**Phase B — chronological stitching**
For each hit:
1. Identify the message’s `source_thread_id` (thread/conversation scope).
2. Fetch neighbors from the same thread using one of these deterministic window strategies:

- **Turn window (preferred):** fetch messages whose `turn_index` is within ±N of the hit.
- **Time window (fallback):** fetch messages within ±T minutes of the hit’s `source_created_at` (only if turn_index is missing/unavailable).

Window rules:
- Do not cross threads when stitching.
- Keep windows bounded (avoid pulling an entire long thread).
- Choose defaults that are small but useful (e.g. `N=3..8` turns); avoid large unbounded loads.

### 2) Deduplicate deterministically (required)
Because windows will overlap, deduplicate by a stable key:
- Prefer `source_message_id` (or your canonical message id).
- Fallback to database primary key if needed.

Dedup rules:
- Deterministically retain a single copy.
- Preserve enough metadata to maintain ordering later.

### 3) Sort chronologically with stable tie-breakers (required)
Sort the stitched set with this precedence:

1. `source_created_at` ascending (prefer non-null)
2. `turn_index` ascending (within thread)
3. Stable final tie-breaker:
   - `source_message_id` (or DB primary key) ascending

Fallback behavior:
- If `source_created_at` is missing, treat it as “latest” for ordering but do not drop the row (unless your retrieval policy explicitly excludes inferred/unknown time).
- If `turn_index` is missing, treat it as `+inf` within the same timestamp, or use DB primary key as the tie-breaker.

### 4) Output shape (required)
Return a single ordered context block (or a structured list) suitable for rendering, with enough fields for the renderer:

- `source_created_at`
- `source_thread_id`
- `turn_index`
- `role`
- `content`
- idempotency key (`source_message_id` or equivalent)

Do not modify rendering format in this task (TASK-004 handles formatting).

### 5) Scope boundary
- Do not change migration ingestion (TASK-001).
- Do not add DB indexes/constraints (TASK-002).
- Do not change rendering format (TASK-004).
- Do not add “era tagging” policy (TASK-005).

## Tests
Backend tests:

```bash
pytest -v
```

Add a unit test covering:
- Given top-K hits in a single thread, window stitching returns neighbors.
- Overlapping windows deduplicate correctly.
- Sorting yields deterministic chronological order (including tie-breakers).
- Multi-thread hits do not cross-contaminate ordering (threads stitched separately then merged chronologically by `source_created_at`, or returned as separate blocks—use the repo’s existing expectation).

If the repo already has a retrieval test pattern, follow it; do not invent a new harness.

## Post-run verification (required)
Add a minimal diagnostic verification path (dev-only) or test assertion that confirms:
- final output is monotonic by `(source_created_at, turn_index, id)`.

## Git
```bash
git add <retrieval_module_files_here> <test_files_here>
git commit -m "Memory: stitch neighbor windows and sort context chronologically"
```

## Expected Output
- Summary of retrieval behavior change (where the stitching/sort lives)
- Test results
- Commit hash