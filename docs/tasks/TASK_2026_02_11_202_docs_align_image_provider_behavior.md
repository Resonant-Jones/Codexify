# Task 001 - Align roadmap docs with actual provider behavior
Preflight: git status --porcelain -uall must be empty

Source finding: FINDING-2026-02-11-009
Risk: LOW

Goal: remove retired placeholder-image claim and document current status: OpenAI functional path, local/stability return explicit not-implemented (503) behavior.

Allowed files:
- docs/codexify-mvp-roadmap.md

Dependencies/prereqs (commands):
- command -v rg

Command checklist:
1. Preflight: git status --porcelain -uall must be empty
2. git status --porcelain -uall
3. If step 2 is non-empty, STOP and run: git stash push --include-untracked --message 'preflight-CAMPAIGN_2026_02_11_FOLLOWUP_DOCS_DRIFT-001-cleanup'
4. rg -n 'Returns 1x1 placeholder' docs/codexify-mvp-roadmap.md
5. rg -n 'not implemented' guardian/image_gen/providers/local.py guardian/image_gen/providers/stability.py
6. git status --porcelain -uall | awk '{print $2}' | grep -Ev '^(docs/codexify-mvp-roadmap.md)$'
7. If step 6 prints any path, STOP and run: git stash push --include-untracked --message 'cleanup-CAMPAIGN_2026_02_11_FOLLOWUP_DOCS_DRIFT-001-out-of-scope'
8. rg -n 'placeholder|not implemented|OpenAI' docs/codexify-mvp-roadmap.md

Expected outputs:
- Step 2 returns no lines.
- Step 6 returns no lines (grep exit 1).
- Placeholder claim is removed from roadmap docs.
- Updated roadmap explicitly matches current provider behavior.

Rollback/cleanup commands:
- git stash push --include-untracked --message 'rollback-CAMPAIGN_2026_02_11_FOLLOWUP_DOCS_DRIFT-001'
- git restore --staged --worktree docs/codexify-mvp-roadmap.md

Runner constraints:
- Must not proceed with dirty tree.
- Must stop if out-of-scope files appear.
- No product decision changes are allowed in this docs-only task.