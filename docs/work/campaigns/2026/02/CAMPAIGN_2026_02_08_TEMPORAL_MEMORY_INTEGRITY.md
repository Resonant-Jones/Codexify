CAMPAIGN — Temporal Memory Integrity (Anti-Soup)

Metadata
 • Campaign-ID: CAMPAIGN-2026-02-08-TEMPORAL_MEMORY_INTEGRITY
 • Codename: ANTI_SOUP
 • Owner: resonant_jones
 • Risk: MED (touches schema + retrieval path)
 • Commit mode: one-commit-per-task (atomic)
 • Scope boundary: Do not mix with Neo4j graph logging wiring tasks.

⸻

Executive Objective

Make migrated chat history feel chronologically real, not “legacy chat soup,” by treating time and ordering as first-class signals in:
 1. Ingestion / migration (truth capture)
 2. Schema + indexes (queryability)
 3. Retrieval (stitching coherence)
 4. LLM context rendering (perception of time)
 5. (Optional) Era tagging (archive vs live)

⸻

Success Criteria
 • Imported messages have stable ordering (turn_index) and original timestamps (source_created_at).
 • Timeline queries are fast and deterministic (indexes exist).
 • Retrieval returns relevant memories with neighbors and sorted chronologically.
 • Context presented to the model includes clear temporal anchors (timestamp, thread, turn, role).
 • CI remains green; Neo4j is not required for these tasks.

⸻

Task List

TASK-2026-02-08-001 — Persist temporal truth during migration

Goal: Capture timestamps + stable ordering at import time.
This change belongs in: /backend/rag/chatgpt_migration.py (or the exact migration ingestion file that inserts chat messages).
Instructions:
 1. Ensure every imported message persists:
 • source_created_at (original ChatGPT timestamp)
 • imported_at (ingestion time)
 • source_thread_id (ChatGPT conversation id)
 • source_message_id (ChatGPT message node id)
 • turn_index (deterministic per thread; do not depend solely on timestamp)
 • role (user|assistant|system|tool)
 2. If the export is a tree/DAG, linearize a canonical path deterministically and assign sequential turn_index.
 3. Do not alter retrieval or rendering in this task.

Tests: pytest -v (backend).
Git:

git add backend/rag/chatgpt_migration.py
git commit -m "Migration: persist source timestamps and turn ordering"

Expected Output:
 • Summary of fields added/ensured during insert
 • Test results
 • Commit hash

⸻

TASK-2026-02-08-002 — Add DB/index support for chronological queries

Goal: Make timeline retrieval fast + deterministic.
This change belongs in: the schema/migration layer (e.g. /guardian/db/models/... or your Alembic migrations), whichever is authoritative in Codexify.
Instructions:
 1. Add indexes:
 • (source_thread_id, turn_index)
 • (source_thread_id, source_created_at)
 2. Add uniqueness where safe:
 • source_message_id unique (or (source_thread_id, source_message_id) if needed)
 3. Ensure nullable behavior is safe for legacy rows (backfill strategy optional but do not implement backfill here unless trivial).

Tests: pytest -v (backend).
Git:

git add <schema_or_migration_files_here>
git commit -m "DB: index and constrain migrated message chronology fields"

Expected Output:
 • Schema/migration changes summary
 • Test results
 • Commit hash

⸻

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

⸻

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

⸻

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

⸻

Notes / Guardrails
 • Atomicity: one task = one commit. Do not combine tasks.
 • No NLP extraction in this campaign. This campaign is about time + ordering + coherent recall, not entity discovery.
 • Avoid schema churn: prefer additive fields/indexes; avoid breaking changes unless necessary.
 • Determinism > cleverness: turn_index should remain stable across reruns.

⸻

Completion Checklist
 • TASK-001 merged: imported messages have source_created_at + turn_index
 • TASK-002 merged: indexes exist and queries are fast
 • TASK-003 merged: retrieval stitches neighbors + sorts chronologically
 • TASK-004 merged: context formatting anchors time visibly
 • TASK-005 optional merged: archive policy prevents “past as present”

# CAMPAIGN — Temporal Memory Integrity (Anti-Soup)

## Metadata
- **Campaign-ID:** CAMPAIGN-2026-02-08-TEMPORAL_MEMORY_INTEGRITY
- **Codename:** ANTI_SOUP
- **Owner:** resonant_jones
- **Risk:** MED (touches schema + retrieval path)
- **Commit mode:** one-commit-per-task (atomic)
- **Scope boundary:** **Do not mix** with Neo4j graph logging wiring tasks.

---

## Executive Objective
Make migrated chat history feel chronologically real (not “legacy chat soup”) by treating time + ordering as first-class signals in:

1) Ingestion / migration (truth capture)  
2) Schema + indexes (queryability)  
3) Retrieval (stitching coherence)  
4) LLM context rendering (perception of time)  
5) (Optional) Era tagging (archive vs live)

---

## Success Criteria
- Imported messages have stable ordering (`turn_index`) and original timestamps (`source_created_at`) with explicit inference tracking when missing.
- Timeline queries are fast and deterministic (indexes exist).
- Retrieval returns relevant memories with bounded neighbors and sorted chronologically.
- Context presented to the model includes clear temporal anchors (timestamp, thread, turn, role).
- CI remains green; Neo4j is not required for these tasks.

---

## Task Files
(Authoritative task specs live here; this campaign doc is the index.)
- `docs/work/tasks/2026/02/TASK_2026_02_08_001_persist_temporal_truth_during_migration.md`
- `docs/work/tasks/2026/02/TASK_2026_02_08_002_add_db_index_support_for_chronological_queries.md`
- `docs/work/tasks/2026/02/TASK_2026_02_08_003_Retrieval_relevance_stitch_window_sort_chronologically.md`
- `docs/work/tasks/2026/02/TASK_2026_02_08_004_rendering_make_time_visible_to_the_model.md`
- `docs/work/tasks/2026/02/TASK_2026_02_08_005_era_tagging_archive_vs_live.md`

---

## Task List

### TASK-2026-02-08-001 — Persist temporal truth during migration
**Goal:** Capture timestamps + stable ordering at import time (deterministic, rerunnable).  
**This change belongs in:** `/backend/rag/chatgpt_migration.py` (or the exact ingestion file that inserts chat messages).  

**Key requirements:**
- Persist per-message fields: `source_created_at`, `imported_at`, `source_thread_id`, `source_message_id`, `turn_index`, `role`.
- Deterministic rules:
  - `source_created_at` precedence: message timestamp → conversation timestamp → fallback to `imported_at` **with explicit inferred flag**.
  - Canonical mainline linearization for tree/DAG exports: follow active leaf → parents → reverse to root→leaf; assign `turn_index` sequentially.
  - Do not interleave branch paths into mainline `turn_index` in v1.
- Idempotency:
  - Use `source_message_id` (or `(source_thread_id, source_message_id)`) as the stable upsert key.
  - Reruns must not churn: preserve existing `turn_index` and `imported_at` unless missing/null.
- Role mapping: map to `user|assistant|system|tool`, store raw role if unknown and fallback safely.

**Tests:** `pytest -v`  
**Git:**
```bash
git add backend/rag/chatgpt_migration.py
git commit -m "Migration: persist source timestamps and turn ordering"
```

---

### TASK-2026-02-08-002 — Add DB/index support for chronological queries
**Goal:** Make timeline queries fast, deterministic, and safe for reruns.  
**This change belongs in:** the repo’s authoritative schema/migration layer (models + migrations).  

**Key requirements:**
- Add indexes on the migrated message table:
  - `(source_thread_id, turn_index)`
  - `(source_thread_id, source_created_at)`
- Add uniqueness (choose the safe strategy for your data):
  - Prefer unique `source_message_id` if globally unique
  - Otherwise unique `(source_thread_id, source_message_id)`
- Legacy/null safety:
  - No backfill in this task.
  - Use partial indexes or constraint strategy that won’t fail on existing nulls/violations (document follow-up if needed).

**Tests:** `pytest -v`  
**Git:**
```bash
git add <schema_or_migration_files_here>
git commit -m "DB: index and constrain migrated message chronology fields"
```

---

### TASK-2026-02-08-003 — Retrieval: relevance → stitch window → sort chronologically
**Goal:** Turn relevant hits into coherent ordered context (bounded stitching, deterministic ordering).  
**This change belongs in:** the repo’s existing memory/retrieval module (no parallel pipeline).  

**Key requirements:**
- Two-phase pipeline:
  1) semantic retrieval → top-K hits (diagnostic scores retained, not final sort)
  2) stitch neighbors within the same thread
- Window rules:
  - Prefer turn window ±N via `turn_index`; fallback to time window ±T only if needed.
  - Never cross threads; keep windows bounded.
- Deduplicate deterministically by stable key (`source_message_id` preferred).
- Sort with stable tie-breakers:
  1) `source_created_at` asc
  2) `turn_index` asc
  3) stable id (`source_message_id` or PK) asc
- Output includes fields needed by renderer; rendering format unchanged here.

**Tests:** `pytest -v` + unit test for stitching/dedup/sort monotonicity  
**Git:**
```bash
git add <retrieval_module_files_here> <test_files_here>
git commit -m "Memory: stitch neighbor windows and sort context chronologically"
```

---

### TASK-2026-02-08-004 — Rendering: make time visible to the model
**Goal:** Prevent soup perception by adding explicit chronological anchors in context rendering.  
**This change belongs in:** the existing context renderer/packer (formatting-only).  

**Key requirements:**
- Prefix each rendered message with: timestamp, thread id/label, `turn_index`, role.
- Stable compact format (example):
  - `[YYYY-MM-DD HH:MM | thread:<id> | turn:<n> | <role>] <text>`
- Safe fallbacks for missing fields (do not drop messages).

**Tests:** `pytest -v` + format/snapshot test including at least one fallback case  
**Git:**
```bash
git add <rendering_files_here> <test_files_here>
git commit -m "Context: render migrated memories with explicit chronological anchors"
```

---

### TASK-2026-02-08-005 (Optional) — Era tagging: “archive vs live”
**Goal:** Treat imported history as archival by default; include when justified.  
**This change belongs in:** migration tagging + retrieval selection policy (minimal and reversible).  

**Key requirements:**
- Tag imported rows at ingest: `origin="chatgpt_import"` (and optional `era="pre_codexify"`), optionally `import_batch_id`.
- Retrieval policy: prefer live by default; allow archival inclusion when:
  - user explicitly asks for past/import/history, OR
  - archival candidate is significantly more relevant, OR
  - same-thread continuation requires it.
- Make archival inclusion explicit in metadata (`is_archival` / `origin`) for downstream rendering (future).

**Tests:** `pytest -v` + tests for default preference + override + idempotent tagging  
**Git:**
```bash
git add <migration_files_here> <retrieval_files_here> <test_files_here>
git commit -m "Memory: tag imported history as archival and adjust retrieval policy"
```

---

## Notes / Guardrails
- **Atomicity:** one task = one commit. Do not combine tasks.
- **No NLP extraction** in this campaign. This is time + ordering + coherent recall, not entity discovery.
- **Avoid schema churn:** prefer additive fields/indexes; avoid breaking changes unless necessary.
- **Determinism > cleverness:** `turn_index` must remain stable across reruns.

---

## Completion Checklist
- [ ] TASK-001 merged: imported messages have `source_created_at` + `turn_index` (+ inferred tracking when needed)
- [ ] TASK-002 merged: indexes/constraints exist and timeline queries are fast
- [ ] TASK-003 merged: retrieval stitches neighbors + dedups + sorts chronologically (monotonic)
- [ ] TASK-004 merged: context formatting anchors time visibly with stable output
- [ ] TASK-005 optional merged: archive policy prevents “past as present”
