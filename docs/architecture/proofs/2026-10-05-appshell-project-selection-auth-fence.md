# AppShell Project Selection Auth Fence

Date: 2026-10-05. Focused account-isolation repair for the AppShell-owned
default Project projection. This receipt is `proven-test` and
`proven-code-path`; it is not authenticated browser or release qualification.

## Task Spec

### Objective

On an in-place authenticated-session change, re-read the existing
account-scoped `GET /api/projects` list before AppShell uses its persisted
`cfy.generalProjectId` hint for document context or Gallery uploads. Preserve
the selected Project only when it belongs to the current session's returned
list; otherwise use the current account's existing General Project. Fence
late responses from an earlier session.

### Authority and scope

PostgreSQL Project rows and their canonical `projects.user_id` ownership remain
authoritative. `GET /api/projects` filters by the request's resolved account;
the browser's numeric Project ID and auth-session key are hints/fencing state,
not identity or authorization. This is aligned with ADR-005 and ADR-081 and
introduces no new persistence model, route, owner representation, export field,
or chat execution behavior.

This slice owns AppShell's default Project hint and its Gallery uploader and
Documents fallback. It does not change or claim to repair the separate
`cfy.projectsCache` / `cfy.lastProjectId` caches, Guardian chat session
rehydration, thread assignment, or chat execution/recovery behavior.

### Allowed files

- `frontend/src/components/persona/layout/AppShell.tsx`
- `frontend/src/components/persona/layout/__tests__/AppShell.test.tsx`
- `docs/architecture/proofs/2026-10-05-appshell-project-selection-auth-fence.md`

### Acceptance criteria

1. A token change while AppShell remains mounted triggers a fresh project-list
   request.
2. The prior session's Project ID is not supplied to the Gallery uploader or
   Documents fallback while the new list is unresolved.
3. A response from a prior session cannot validate a Project ID for the new
   session.
4. A stored ID is retained only if present in the current list; otherwise
   AppShell adopts that list's General Project or clears the value if the list
   is empty.
5. A user-selected ID is accepted only when it appears in the list validated
   for the current session.
6. Focused tests, lint, and whitespace checks pass. No runtime/release claim is
   made from mocked API tests.

## Change

AppShell now keys its one-time project-list guard to the authenticated session
token rather than component lifetime. Each response is fenced against the
current auth state. Until the current session's list is acknowledged, the
previous Project ID is omitted from the Documents fallback, the Gallery
uploader is disabled, and the legacy trusted marker is cleared. The selected
ID is retained only when it appears in the returned Project list; otherwise
the existing General Project is selected. Manual AppShell selection events
must refer to an ID in that validated list.

The token is used only as a client-side invalidation key. Server-side
`projects.user_id` and route authorization remain the account boundary.

## Validation

- `vitest run components/persona/layout/__tests__/AppShell.test.tsx --reporter=dot`
  — 63 passed. The suite emits its existing onboarding API mock warning
  (`buildAuthenticatedFetchInit` absent); it did not fail tests.
- Focused rerun of the stored-ID, auth-transition, and Guardian-to-Documents
  cases — 3 passed, 60 skipped.
- ESLint on the changed test module — exit 0, four existing `any` warnings.
  The AppShell source file is excluded by the repository's lint ignore rules.
- `git diff --check` — passed.

The API is mocked in these tests. No live two-account browser session,
PostgreSQL read, backend interruption, or reload/reopen was exercised here.

## Current truth and remaining work

At the start of this task, `main` was `ff57597cc02a9b4bb8ca40f4fa417126dd1e3e53`;
`docs/architecture/00-current-state.md` still reports supported-Compose
qualification `HOLD`. Core Runtime Reliability / Goal #1 was active in
`/Volumes/Dev_SSD/offload/codex/worktrees/chat-postgres-deadline/Codexify-main`
on `codex/chat-stop-diagnostic-mainline-20261005`, HEAD
`7a103e55656745e58e52947e6c29ebea76d74278`, 28 commits ahead of `origin/main`
and clean at the last check. Its AppShell diff is confined to Stop/cancellation
observation; this task touched other AppShell sections and changed no shared
execution semantics. Restart recovery, worker/attempt/provider behavior,
cancellation, terminal events, turn locks, and final supported-Compose
qualification remain upstream Goal #1 dependencies.

The per-session fence does not preserve a different non-General selected
Project for each account: `cfy.generalProjectId` remains a single legacy slot,
so a switch to another account can replace its value. The Guardian chat-side
`cfy.projectsCache` and `cfy.lastProjectId` are also separate account-agnostic
projections and need their own bounded investigation before account/thread
isolation is claimed complete. This receipt does not close Persistence,
Recovery & Continuity.
