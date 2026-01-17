# TASK-2026-01-17-003 — ChatGPT Imports Project

## Task Prompt

Codexify Task Prompt

TASK-ID
TASK-2026-01-17-003_CHATGPT_IMPORTS_PROJECT

Context
You’re operating on the local Codexify repo.

Codexify is project-based. The current ChatGPT import migration code assigns imported threads to a hard-coded project named “Loose Threads”. We want imports to land in a dedicated “Imports” project (user-facing, movable/renameable later), while remaining backward-compatible with existing DBs where “Loose Threads” may already exist.

Objective
Update the ChatGPT export migration so imported threads are assigned to an Imports project instead of Loose Threads, with safe fallback behavior.

Important Rules (read first)
- Follow Runner_Protocol.md two-phase commit pattern (Commit A implementation + Commit B task artifact finalize).
- Do NOT attempt to embed Commit B’s hash inside the artifact file (that creates a paradox). In the artifact, write:
  Finalize-artifact hash: (reported in final output mapping)
- Include the TASK-ID in BOTH commit messages (Commit A and Commit B).
- After completing both commits, output the mapping:
  TASK-2026-01-17-003_CHATGPT_IMPORTS_PROJECT -> [<impl_hash>, <finalize_hash>]

Requirements
- Imports should go into a project named "Imports" with a clear description.
- Backward compatibility:
  - If "Imports" exists, use it.
  - Else if legacy "Loose Threads" exists, use it (do not attempt to rename DB rows in this task unless there is a clearly supported DB API method).
  - Else create "Imports" and use it.
- Do not change behavior beyond project assignment and naming/description logic.
- Keep error handling + logging consistent with current style.

Files allowed to edit (only)
- backend/rag/chatgpt_migration.py
- docs/tasks/TASK_2026_01_17_003_chatgpt_imports_project.md

Implementation Notes
In backend/rag/chatgpt_migration.py:
- Replace _resolve_loose_threads_id(...) with a more accurate helper name (e.g., _resolve_imports_project_id(...)).
- Update logic:
  1) Try ensure_project("Imports", "Default bucket for imported threads")
  2) If that fails, list_projects() and:
     - Prefer a project named "Imports"
     - Else fall back to "Loose Threads" if present
     - Else raise the same RuntimeError as before
- Update the import loop to use the new helper variable name and semantics.

Checks to run
Run:
- pytest -v

Git steps (two-phase)

Commit A (implementation)
1) git status --porcelain (must show only expected changes)
2) pytest -v (must pass)
3) git add backend/rag/chatgpt_migration.py
4) git commit -m "TASK-2026-01-17-003_CHATGPT_IMPORTS_PROJECT: route ChatGPT import to Imports project"

Commit B (finalize task artifact)
1) Create/update docs/tasks/TASK_2026_01_17_003_chatgpt_imports_project.md with:
   - Task Prompt (copy this entire prompt in)
   - Summary:
     - Files changed
     - Checks run + results
     - git status confirmation
   - Commit mode: two-phase
   - Implementation hash: <hash A>
   - Finalize-artifact hash: (reported in final output mapping)
2) git add docs/tasks/TASK_2026_01_17_003_chatgpt_imports_project.md
3) git commit -m "TASK-2026-01-17-003_CHATGPT_IMPORTS_PROJECT: finalize task summary"

Output required
After finishing, output:
- Summary of changes
- Commands run + pass/fail
- git status --porcelain (must be empty)
- The mapping:
  TASK-2026-01-17-003_CHATGPT_IMPORTS_PROJECT -> [<impl_hash>, <finalize_hash>]

## Summary

- Files changed: backend/rag/chatgpt_migration.py
- Checks: pytest -v (pass)
- git status --porcelain: clean
- Commit mode: two-phase
- Implementation hash: 1551451178f4277e1f04001acc616ae7699487d3
- Finalize-artifact hash: (reported in final output mapping)
