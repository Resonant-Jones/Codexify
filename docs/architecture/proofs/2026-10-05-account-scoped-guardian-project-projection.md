# Account-Scoped Guardian Project Projection

Date: 2026-10-05. Focused frontend account-isolation repair. This receipt is
`proven-test` and `proven-code-path`; it is not authenticated browser or
release qualification.

## Objective

Load the Sidebar Project list from the authenticated `GET /api/projects`
response for each auth session. Keep the last-selected Project as a
per-account UI preference, and expose it only when the returned list proves
that the Project belongs to the current account.

## Authority and scope

PostgreSQL Project rows and canonical `projects.user_id` ownership remain
authoritative. The client auth-session key fences stale responses and cache
visibility; the account identifier is accepted only from a consistent owner
field across the server-returned Project list. Neither browser storage nor a
Project ID grants access. This follows ADR-005 and ADR-081 and adds no route,
schema, ownership representation, or server persistence.

This slice owns the Guardian Sidebar project-list projection and last-selected
Project preference. It does not change thread/session hydration, assignment,
completion attempts, or chat execution/recovery semantics.

## Acceptance criteria

1. No Project list is loaded from `cfy.projectsCache`; a fresh authenticated
   session fetches `/api/projects` and late prior-session responses are ignored.
2. Account scope is derived only when every returned Project has the same
   non-empty `user_id`.
3. The saved last Project uses an account-specific key. The legacy global key
   is migrated only when its ID appears in the current account's returned list.
4. A selected Project is exposed and persisted only while it remains in the
   current account's returned list; a removed Project clears the current
   selection and its stale preference.
5. Focused mocked tests and docs/whitespace checks pass. No live two-account,
   PostgreSQL, browser-reload, or release claim is made here.

## Change

`useProjectsCache` no longer restores or writes a project-list snapshot to
localStorage. It hides the prior list immediately when the auth-session scope
changes, fences old responses, and returns the account scope only when the
server's Project owners are consistent. The legacy cache key is removed.

`GuardianChatWithSidebar` stores the selected Project under
`cfy.lastProjectId.account.<encoded-user-id>`. A legacy `cfy.lastProjectId` is
used only when the current server list contains that ID. Selection state is
gated by current auth, owner, and list membership; deletion from the returned
list clears the stale selection. The existing Sidebar persistence receives
the account key only after a current selection has been hydrated.

## Validation

- `vitest run components/sidebar/__tests__/useProjectsCache.test.tsx components/persona/layout/__tests__/GuardianChatWithSidebar.terminal-projection.test.tsx --reporter=dot` — 13 passed.
- `vitest run components/sidebar/__tests__/useProjectsCache.test.tsx components/persona/layout/__tests__/GuardianChatWithSidebar.stability.test.tsx --reporter=dot` — both suites passed, including the selection remount/account-switch case.
- ESLint on the changed TypeScript files — exit 0, warnings only (import-order and explicit-`any` warnings remain).
- `python3 scripts/validate_docs.py` — passed.
- `git diff --check` — passed.

## Current truth and limitations

`docs/architecture/00-current-state.md` continues to mark supported-Compose
qualification `HOLD`. All evidence in this receipt is local frontend test and
code-path evidence. The API is mocked; the reopen check remounts the component
within one test process and is not a real browser reload. No authenticated
two-account browser run, live PostgreSQL ownership read, backend restart,
durable thread reload/reopen, or release qualification was performed.
