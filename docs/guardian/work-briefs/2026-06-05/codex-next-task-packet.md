# Guardian Work Brief - Codex Next-Task Packet - 2026-06-05

## Next Task
Restore or port the Guardian brief generation path into this branch, or explicitly mark this branch as lacking the automation generator until it rejoins the lineage that contains `make guardian-brief`.

## Why This Task
The requested automation target does not exist in the current checkout. Manual packets preserve daily evidence, but they do not provide the repeatable generator/runbook behavior expected by the automation. The branch is also ahead of upstream by two commits, so generator restoration should record branch drift without attempting cleanup.

## Acceptance Criteria
- `make guardian-brief` exists and runs from repo root, or the branch-local absence is documented as intentional.
- The generator creates the same four reporting surfaces expected by the automation: Axis brief, Codex next-task packet, truth ledger, and decision log.
- Generated output records repo branch, head, upstream delta, dirty state, and target errors without attempting to fix branch state.
- The generated brief does not invoke marketing generation, daily audits, heartbeat bundles, public export, or release claim machinery.
- The output preserves the current-state truth boundary: planning docs cannot widen supported runtime claims.

## Suggested Implementation Slice
1. Compare this branch against the lineage where `make guardian-brief` exists, if available.
2. Port only the Makefile target, generator script, runbook, and focused generator tests if they still match current repo conventions.
3. Run the generator on the current side-branch state and confirm it reports branch drift/untracked files rather than mutating them.
4. Keep runtime route, worker, provider, queue, UI, audit, heartbeat, and marketing changes out of the patch.

## Validation
- `make guardian-brief`
- `git diff --check`
- Focused generator tests if generator/test files are restored.

## Non-Goals
- No runtime route, worker, provider, queue, or UI changes.
- No marketing packets.
- No release claim expansion.
- No daily audit, heartbeat, public export, or campaign artifact generation.
