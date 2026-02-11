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

## Completion Summary (Runner)

- Status: success

- Summary: Updated roadmap documentation to reflect current image provider behavior and removed outdated placeholder-image claims in `docs/codexify-mvp-roadmap.md`.

Changes made:
- Replaced “other providers are stubs” wording with explicit fail-closed behavior language.
- Updated Stability/Local provider table rows from “Returns 1x1 placeholder” to “Returns HTTP 503 (not implemented)”.
- Updated supported-model bullets to state Stability/Local are not implemented and return 503.
- Updated gap-analysis row for generation to reflect OpenAI works while local/stability return 503.

- Implementation commit hash: 60a00801bfaa7848b60f9fee4f4519e6150df11f

- Receipt update commit hash: (see campaign mapping)

- Tests ran: rg -n "Returns 1x1 placeholder|1x1 placeholder" docs/codexify-mvp-roadmap.md (no matches), rg -n "OpenAI|Stability Provider|Local Provider|HTTP 503|not implemented" docs/codexify-mvp-roadmap.md (verified updated statements), git diff -- docs/codexify-mvp-roadmap.md (verified only intended edits), git status --short (only docs/codexify-mvp-roadmap.md modified)

- Notes: No code/runtime changes were required; docs-only update completed.

<details>
<summary>Structured task_result.json</summary>

```json
{
  "status": "success",
  "summary": "Updated roadmap documentation to reflect current image provider behavior and removed outdated placeholder-image claims in `docs/codexify-mvp-roadmap.md`.\n\nChanges made:\n- Replaced \u201cother providers are stubs\u201d wording with explicit fail-closed behavior language.\n- Updated Stability/Local provider table rows from \u201cReturns 1x1 placeholder\u201d to \u201cReturns HTTP 503 (not implemented)\u201d.\n- Updated supported-model bullets to state Stability/Local are not implemented and return 503.\n- Updated gap-analysis row for generation to reflect OpenAI works while local/stability return 503.",
  "tests_ran": [
    "rg -n \"Returns 1x1 placeholder|1x1 placeholder\" docs/codexify-mvp-roadmap.md (no matches)",
    "rg -n \"OpenAI|Stability Provider|Local Provider|HTTP 503|not implemented\" docs/codexify-mvp-roadmap.md (verified updated statements)",
    "git diff -- docs/codexify-mvp-roadmap.md (verified only intended edits)",
    "git status --short (only docs/codexify-mvp-roadmap.md modified)"
  ],
  "commit_hash": "60a00801bfaa7848b60f9fee4f4519e6150df11f",
  "implementation_commit_hash": "60a00801bfaa7848b60f9fee4f4519e6150df11f",
  "receipt_update_commit_hash": "",
  "notes": "No code/runtime changes were required; docs-only update completed."
}
```

</details>
