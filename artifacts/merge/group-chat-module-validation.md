# Group Chat Module Merge Validation

Branch: `chore/resolve-group-chat-module-merge`

## Passed

- `git diff --check`
- `pytest tests/core/test_ai_router.py tests/core/test_chat_completion_service_retrieval_query_cleaning.py`

Result:
- 22 passed in 1.27s
- Covered the local routing path in `guardian/core/ai_router.py`
- Covered the merged retrieval-query cleaner in `guardian/core/chat_completion_service.py`

## Failed or blocked

- `pytest tests/core/test_chat_completion_service_latest_turn.py tests/core/test_chat_completion_service_latest_turn_trace.py tests/core/test_chat_completion_service_latest_turn_retrieval.py tests/core/test_ai_router.py`
  - Blocked by missing `pytest-asyncio` in the active Python environment.
  - The async latest-turn retrieval tests were not runnable here; the sync `ai_router` tests in that file still passed.

- `frontend/node_modules/.pnpm/typescript@5.8.3/node_modules/typescript/bin/tsc -p frontend/src/tsconfig.json --noEmit`
  - Failed on existing frontend dependency/type issues, starting with `cypress.config.ts` missing module declarations.

- `frontend/node_modules/.pnpm/typescript@5.8.3/node_modules/typescript/bin/tsc -p frontend/src/tsconfig.app.json --noEmit`
  - Failed on repo-wide frontend type gaps unrelated to this merge, including missing React/Node declarations and pre-existing type errors in shared app code.

- `node frontend/node_modules/.pnpm/vitest@3.2.4_@types+debug@4.1.12_@types+node@25.3.3_jiti@2.6.1_jsdom@26.1.0_lightningcss@1.31.1_terser@5.44.0/node_modules/vitest/dist/cli.js run --config frontend/src/vitest.config.ts frontend/src/test/App.routing.test.tsx frontend/src/components/sidebar/__tests__/ProjectList.test.tsx frontend/src/features/chat/__tests__/GuardianChat.session-tabs.test.tsx`
  - Failed because the local install is missing the optional Rollup native package `@rollup/rollup-darwin-arm64`.

## Notes

- The repo-wide conflict-marker grep was only noisy in generated/docs/cache content; the strict scan over changed files found no real `<<<<<<<`, `=======`, or `>>>>>>>` markers.
- The top-level `frontend/package.json` `typecheck` script is currently broken because it delegates to a nested package that does not expose a `typecheck` script.
