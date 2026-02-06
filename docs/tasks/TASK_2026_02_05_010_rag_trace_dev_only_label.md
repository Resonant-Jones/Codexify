# TASK-2026-02-05-010_rag_trace_dev_only_label: label rag trace as dev-only

## Task Metadata
Campaign-ID: CAMPAIGN-2026-02-05-CODEXIFY_AUDIT_FOLLOWUP
Task-ID: TASK-2026-02-05-010_rag_trace_dev_only_label
Task title: label rag trace as dev-only
Task artifact path: docs/tasks/TASK_2026_02_05_010_rag_trace_dev_only_label.md
Risk: LOW
Allowed files list:
- frontend/src/hooks/useRagTrace.ts
- frontend/src/components/**
- frontend/src/vite.config.ts
- README.md
Command checklist (exact commands to run):
- git status --porcelain -uall
- rg -n "rag-trace" guardian/routes/chat.py frontend/src/hooks/useRagTrace.ts
- npm --prefix frontend install
- npm --prefix frontend run build
- git status --porcelain -uall
Expected outputs:
- UI labels rag trace as dev-only and non-persistent.
- README.md notes the in-memory debug nature of rag traces.
- Frontend build completes or failure is documented in task summary.
Rollback/cleanup commands:
- git checkout -- frontend/src/hooks/useRagTrace.ts README.md
- git checkout -- frontend/src/components
Dependencies/Prereqs (commands):
- npm --prefix frontend install

## Commit Plan
Commit A message EXACT:
"TASK-2026-02-05-010_rag_trace_dev_only_label: label rag trace dev-only"
Commit B message EXACT:
"TASK-2026-02-05-010_rag_trace_dev_only_label: docs finalize + mapping"
Campaign mapping format EXACT:
TASK-2026-02-05-010_rag_trace_dev_only_label -> [<commitA>, <commitB>]
Manual git commands (explicit file paths):
- git status --porcelain -uall
- git add frontend/src/hooks/useRagTrace.ts frontend/src/components README.md
- git commit --no-verify -m "TASK-2026-02-05-010_rag_trace_dev_only_label: label rag trace dev-only"
- git log -1 --oneline
- git add docs/tasks/TASK_2026_02_05_010_rag_trace_dev_only_label.md docs/Campaign/CAMPAIGN_2026_02_05_CODEXIFY_AUDIT_FOLLOWUP.md
- git commit --no-verify -m "TASK-2026-02-05-010_rag_trace_dev_only_label: docs finalize + mapping"
- git log -1 --oneline

## Scope Control
- Only modify files in the Allowed files list.
- No mega-tasks; keep changes minimal and observable.

## Summary
- Status: IN PROGRESS.
- Implementation: cecfc011.
- Change: /Users/resonant_jones/Keep/Resonant_Constructs/Codexify/frontend/src/components/diagnostics/RagTracePanel.tsx shows a dev-only/in-memory notice.
- Change: /Users/resonant_jones/Keep/Resonant_Constructs/Codexify/README.md documents the RAG trace debug endpoint as in-memory.
- Change: /Users/resonant_jones/Keep/Resonant_Constructs/Codexify/frontend/src/vite.config.ts sets workbox mode to development to avoid SW minify failure.
- Test: npm --prefix frontend install (no output).
- Test: npm --prefix frontend run build (passed).
