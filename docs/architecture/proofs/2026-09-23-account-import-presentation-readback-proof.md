# Imported conversation presentation and readback proof — 2026-09-23

## Verdict and boundary

**I. Presentation and canonical message readback pass** in the retained isolated local runtime. The canonically imported OpenAI thread appeared in the owner-visible Imports Project, in the unfiltered and exact Project-scoped thread APIs, and in a fresh Chromium Guardian sidebar. Selecting its rendered row opened `/chat/1`; the message API returned canonical message IDs 1 and 2; ChatView rendered both messages once, in user/assistant order. A hard reload requested the same canonical messages and rendered them again. The full exercised chain is `proven-live-runtime` for this isolated runtime, with Playwright assertions also `proven-test`.

This proof ends at presentation/readback. It does not test semantic retrieval, continuity, embedding, provider execution, private preview, or complete supported-profile qualification. It does not resolve the current end-user import complaint or widen a release claim.

## Source and isolated runtime

- Evaluated source: `main` at `59448e4f6a0fd4de2fdee1689ec7093fcaab7579`. The initial working tree was clean (`main...origin/main [ahead 1]`), and `git merge-base --is-ancestor 71a58d7294814e60a8fbebea5a916aafa46ac521 HEAD` exited 0.
- Reused Compose project: `codexify_account_import_ui_probe_20260923`, with the retained project-labeled PostgreSQL volume. Compose sources: `docker-compose.yml`, `docker-compose.whooshd-smoke.yml`, `/private/tmp/codexify-account-import-ui-staging-20260923/compose.override.yml`. No new import or migration was run.
- Frontend origin: `http://127.0.0.1:5183`; backend origin: `http://127.0.0.1:8893`; isolated PostgreSQL: `codexify_account_import_ui_probe_20260923-db-1` (`127.0.0.1:5548`); Redis: `codexify_account_import_ui_probe_20260923-redis-1`. Backend and database health returned HTTP 200/healthy. Database revision: `a8d4c2f6b1e9`.
- Only PostgreSQL, Redis, backend, and frontend were reopened. `codexify_account_import_ui_probe_20260923-worker-account-import-1` remained stopped. Chat/completion and model/provider workers were not started for this proof. The normal development and private-preview stacks were untouched.

## Retained canonical preflight

Read-only PostgreSQL queries by `source_thread_id=axis-import-materialization-20260923-01` confirmed the prior job `788e5d0b-0aab-4df9-8772-39a0907b6eec` remained `completed` with 1 imported thread, 2 imported messages, and 0 failures. The exact imported row was thread `1`, title `Axis Import Materialization Probe`, `chat_threads.user_id=local`, `project_id=2`, `origin_system=openai`, unarchived. Project `2` was named `Imports` and had `projects.user_id=local`. Messages `1` and `2` belonged to thread `1`, had user and assistant roles in chronological order, and retained `source_message_id` values `axis-import-user-message-20260923-01` and `axis-import-assistant-message-20260923-01`. Content checks returned true only for the corresponding known synthetic sentinel in each row; raw bodies are omitted.

The same read-only query after browser proof still found the completed 1/2/0 job, the unchanged thread update timestamp `2026-09-23 15:45:15.151125+00`, and exactly the same two message IDs and source-message provenance. The proof did not create, rename, move, archive, delete, or append to the imported conversation.

## Project and thread API projection

The isolated frontend proxy, under the `local` browser/account posture, returned:

| Request | HTTP | Exact result |
| --- | ---: | --- |
| `GET /api/projects` | 200 | Project `2`, name `Imports`, `user_id=local` was present; General Project `1` was also present. |
| `GET /api/chat/threads?limit=200` | 200 | Thread `1`, `project_id=2`, `origin_system=openai`, exact title; `offset=0`, `next_offset=1`, `has_more=false`. |
| `GET /api/chat/threads?limit=200&project_id=2` | 200 | Same thread `1`, Project `2`, OpenAI origin and title; `has_more=false`. No origin filter was applied. |

These are API results, separate from the browser rendering proof below. The returned IDs, rather than the title alone, establish correlation.

## Fresh-browser Guardian readback

The focused Playwright scenario used a new browser context with no inherited storage origins. It did not pre-seed `cfy.lastProjectId`, an origin filter, or a thread selection. The current app opened through `/` and, if shown, its ordinary **Enter Codexify** control. The test opened the sidebar, selected the visible **Imports** Project tile, confirmed its active state, and observed the resulting `GET /api/chat/threads` request with `project_id=2` and no `origin_system` parameter. The rendered **All** origin control was pressed. That response contained exact thread ID `1`, and the sidebar rendered `Axis Import Materialization Probe` in `thread-tile-1`.

Clicking that tile made its row active, routed the browser to `/chat/1`, and caused `GET /api/chat/1/messages?limit=100&offset=0` → HTTP 200. The response reported total 2, canonical message IDs `[1, 2]`, roles `[user, assistant]`, and both expected synthetic sentinels. ChatView displayed exactly two `chat-message` elements in the same order; the first had the user-message bubble and the second was assistant-authored. No empty-thread state replaced them.

A hard page reload at `/chat/1` caused a new `GET /api/chat/1/messages?limit=100&offset=0` → HTTP 200 with the same IDs, roles, count, and sentinel checks. Both messages rendered again, and the sidebar retained the imported title/thread identity. No import event or manual refresh was used.

The test's network guard recorded **zero** requests to completion, import, or search API routes and zero chat thread/message mutation requests. An initial guard version falsely matched a Vite source-module GET containing `/features/imports/`; that test-only matcher was narrowed to import API routes and the final focused run passed. Worker and provider services remained stopped. This supports absence of completion/retrieval execution in the exercised browser path; it is not a system-wide traffic audit.

## Historical comparison

The [2026-09-03 private-preview history incident](./2026-09-03-chat-history-disappearance-proof.md) had account-owned threads linked to legacy `local` Projects omitted by the signed-in Project API, followed by a persisted empty Project filter. This synthetic isolated thread has matching `local` Project/thread ownership, its Project is visible through `/api/projects`, and the correct Project-scoped thread API returns it. The local pass neither repairs nor disproves that historical private-preview ownership/filter incident.

## Validation and follow-through

| Command | Result | Evidence posture |
| --- | --- | --- |
| `CODEXIFY_IMPORT_PRESENTATION_THREAD_ID=1 CODEXIFY_IMPORT_PRESENTATION_PROJECT_ID=2 CODEXIFY_IMPORT_PRESENTATION_MESSAGE_IDS=1,2 CODEXIFY_IMPORT_PRESENTATION_TITLE='Axis Import Materialization Probe' pnpm --dir frontend/src exec playwright test tests/playwright/account_import_presentation_readback.spec.ts --config=/private/tmp/codexify-account-import-ui-staging-20260923/playwright.config.mjs --project=chromium --grep 'renders and rehydrates a canonically imported conversation'` | Final run: 1 passed | `proven-live-runtime` for the observed browser/backend/Postgres chain; `proven-test` assertions |
| `pnpm --dir frontend/src exec vitest run components/sidebar/__tests__/ThreadList.test.tsx components/sidebar/__tests__/useSidebarThreads.test.tsx components/sidebar/__tests__/ProjectList.test.tsx components/persona/layout/__tests__/GuardianChatWithSidebar.stability.test.tsx` | 4 modules, 61 passed | `proven-test` |
| `pnpm --dir frontend/src exec vitest run features/chat/__tests__/useChat.test.ts` | 1 module, 10 passed | `proven-test` |
| `.venv/bin/python -m pytest -v tests/routes/test_chat_routes.py::TestChatThreadsGet tests/routes/test_chat_routes.py::TestChatMessagesGet tests/routes/test_chat_origin_filter.py` | 26 passed, 8 warnings | `proven-test` |
| `pnpm --dir frontend/src exec eslint tests/playwright/account_import_presentation_readback.spec.ts` | Passed | `proven-test` style/static check |

The focused browser scenario was first run with an overbroad test-only network matcher and failed at its final guard despite passing the presentation and reload assertions. After narrowing that matcher, the final scenario passed. The repository's package layout requires `pnpm --dir frontend/src`, and the temporary Playwright config is the same isolated Chromium configuration used by the preceding import proofs.

Only the focused Playwright test and this proof artifact changed. After readback, the four isolated services were stopped and their volumes retained for review. Production code, canonical Project/thread/messages, ownership, provenance, sidebar and message API semantics, schema, UMS, retrieval, and provider behavior were unchanged. No real user import or private-preview state was accessed. **ADR impact: No ADR impact. Documentation follow-through: proof artifact only. Current-state change: none. Release-claim change: none.**

Next prerequisite: **Trace the canonically visible imported conversation through the governed retrieval/continuity path and prove whether a new Guardian thread can recall its imported content under the intended source/depth policy.**
