# Chat Slow-Path Suite Boundary Verification

## Scope

Verification only. No runtime code, tests, or configuration were changed.

- Current checkout branch: `codex/delegation-main-fix`
- Current checkout HEAD: `1bb0140909b92774e06f6c0912e81a94fea6a596`
- Inspected commit: `11e642db4ac793332a8a82d42b23869aa8d5a3d3`
- Parent commit: `906e6b5edfa103d2eed2d0e64faba920c966f7fc`
- Inspection mode: detached temporary worktree for the inspected commit and a separate detached temporary worktree for the parent

## Commands Run

Environment setup:

- `git branch --show-current`
- `git rev-parse HEAD`
- `git rev-parse --verify 11e642db4^{commit}`
- `git worktree add /tmp/codexify-suite-boundary-verify 11e642db4`
- `pnpm install --frozen-lockfile --ignore-scripts`
- `git worktree add /tmp/codexify-suite-boundary-verify-parent 11e642db4^`
- `pnpm install --frozen-lockfile --ignore-scripts`

Inspected commit:

- `pnpm --dir frontend/src exec vitest run features/chat/__tests__/useInferenceRequestState.test.tsx features/chat/__tests__/GuardianChat.test.tsx --reporter=dot`
- `pnpm test`
- `pnpm test 2>&1 | rg '^( FAIL  | ❯ )'`

Parent commit:

- `pnpm --dir frontend/src exec vitest run features/chat/__tests__/useInferenceRequestState.test.tsx features/chat/__tests__/GuardianChat.test.tsx --reporter=dot`
- `pnpm test`
- `pnpm test 2>&1 | rg '^( FAIL  | ❯ )'`

## Results On Inspected Commit

Targeted chat tests still pass on `11e642db4`.

- `features/chat/__tests__/useInferenceRequestState.test.tsx`
- `features/chat/__tests__/GuardianChat.test.tsx`

Result: `2 passed, 0 failed`

Repo-wide frontend suite fails on `11e642db4`.

- Result: `12 failed files, 38 failed tests`

Failing suite inventory on the inspected commit:

| Suite | Representative error |
| --- | --- |
| `components/persona/layout/AppShell.runtimeHealth.test.tsx` | runtime health banner text not found for degraded runtime states |
| `components/sidebar/__tests__/ThreadList.test.tsx` | esbuild transform failed because `SourceDockHarness` was declared twice |
| `components/sidebar/__tests__/useProjectsCache.test.tsx` | duplicate `General` alias cleanup assertions timed out |
| `features/chat/__tests__/GuardianChat.thread-config.test.tsx` | render failure rooted at `features/chat/GuardianChat.tsx:2627-2628` |
| `features/chat/__tests__/GuardianChat.turn-lock-lifecycle.test.tsx` | render failure rooted at `features/chat/GuardianChat.tsx:2627-2628` |
| `features/settings/SettingsView.test.tsx` | save-flow success message not found after system prompt save resolves |
| `features/settings/__tests__/SettingsView.profile-awareness.test.tsx` | `System Prompt` control not found in the restricted-profile flow |
| `features/workspace/__tests__/WorkspacePane.preview.test.tsx` | `ReferenceError: isPdfMediaUrl is not defined` |
| `features/workspace/__tests__/WorkspacePreview.test.tsx` | same preview helper failure as `WorkspacePane.preview` |
| `features/workspace/__tests__/WorkspaceTabs.test.tsx` | segmented-rail expectations still fail for `glass-pill`, `pill-tab`, dividers, close controls, and truncation |
| `test/asset_context_menu.test.tsx` | mocked `@/lib/runtimeConfig` was missing `isTauriRuntime` |
| `test/thread_documents_rehydration.test.tsx` | bootstrap plan text could not be found during thread rehydration |

## Results On Parent Commit

The exact two-file targeted chat command could not be compared directly on the parent tree because Vitest reported `No test files found` for those exact paths there. I did not guess a result for that comparison.

Repo-wide frontend suite on the parent also fails, but with a different boundary:

- Result: `10 failed files, 29 failed tests`

Parent failing suite inventory:

- `components/persona/layout/AppShell.runtimeHealth.test.tsx`
- `components/sidebar/__tests__/ThreadList.test.tsx`
- `components/sidebar/__tests__/useProjectsCache.test.tsx`
- `features/settings/SettingsView.test.tsx`
- `features/settings/__tests__/SettingsView.profile-awareness.test.tsx`
- `features/workspace/__tests__/WorkspacePane.preview.test.tsx`
- `features/workspace/__tests__/WorkspacePreview.test.tsx`
- `features/workspace/__tests__/WorkspaceTabs.test.tsx`
- `test/asset_context_menu.test.tsx`
- `test/thread_documents_rehydration.test.tsx`

Comparison summary:

- Every non-chat failure on `11e642db4` also failed on the parent with materially similar errors.
- The two GuardianChat suites failed on `11e642db4` but did not appear in the parent full-suite failure list.
- The parent therefore establishes a pre-existing failure surface for the shared workspace, settings, sidebar, and runtime-health areas.

## Classification Table

| Suite | Parent comparison | Bucket | Rationale |
| --- | --- | --- | --- |
| `components/persona/layout/AppShell.runtimeHealth.test.tsx` | Fails on parent with the same runtime-health banner assertions | pre-existing unrelated | Shared failure surface predates `11e642db4` |
| `components/sidebar/__tests__/ThreadList.test.tsx` | Fails on parent with the same esbuild duplicate-declaration error | pre-existing unrelated | Test file transform issue predates `11e642db4` |
| `components/sidebar/__tests__/useProjectsCache.test.tsx` | Fails on parent with the same alias-cleanup assertions | pre-existing unrelated | Same cache behavior failure on parent |
| `features/chat/__tests__/GuardianChat.thread-config.test.tsx` | Parent full suite passed this file | introduced by inspected commit | New failure only appears on `11e642db4` |
| `features/chat/__tests__/GuardianChat.turn-lock-lifecycle.test.tsx` | Parent full suite passed this file | introduced by inspected commit | New failure only appears on `11e642db4` |
| `features/settings/SettingsView.test.tsx` | Fails on parent with the same save-flow assertion | pre-existing unrelated | Same failure on parent |
| `features/settings/__tests__/SettingsView.profile-awareness.test.tsx` | Fails on parent with the same restricted-profile assertions | pre-existing unrelated | Same failure on parent |
| `features/workspace/__tests__/WorkspacePane.preview.test.tsx` | Fails on parent with the same preview helper error | pre-existing unrelated | Same failure on parent |
| `features/workspace/__tests__/WorkspacePreview.test.tsx` | Fails on parent with the same preview helper error | pre-existing unrelated | Same failure on parent |
| `features/workspace/__tests__/WorkspaceTabs.test.tsx` | Fails on parent with the same segmented-rail expectations | pre-existing unrelated | Same failure on parent |
| `test/asset_context_menu.test.tsx` | Fails on parent with the same missing mock export error | pre-existing unrelated | Same failure on parent |
| `test/thread_documents_rehydration.test.tsx` | Fails on parent with the same bootstrap/thread-rehydration assertion | pre-existing unrelated | Same failure on parent |

Shared-surface / ambiguous:

- None observed from the available evidence.

Unable to classify:

- None observed from the available evidence.

## Final Verdict

The evidence supports a mixed boundary: most repo-wide failures predate the inspected commit, but two GuardianChat suites are newly failing on `11e642db4`.

VERDICT: one or more repo-wide failures appear introduced by 11e642db4
