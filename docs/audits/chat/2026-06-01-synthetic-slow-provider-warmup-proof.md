# Synthetic Slow Provider / Warmup Proof

## Scope

This proof targets reachable-but-slow local provider first-output behavior in the primary Guardian chat completion loop. It exercises a synthetic OpenAI-compatible provider that accepts the request and withholds first output past an isolated proof timeout.

This proof does not change runtime behavior, timeout defaults, provider fallback behavior, frontend behavior, Obsidian behavior, provider policy, supported profiles, or release posture.

## Repository Safety

- Working directory: `/Volumes/Dev_SSD/Codexify-main`
- Git root: `/Volumes/Dev_SSD/Codexify-main`
- Branch: `codex/fix-chat-slash-commands`
- Remote: `origin https://github.com/Resonant-Jones/Codexify.git`
- HEAD before artifact: `5f27e7b1fff248263eaf03e7503d7dc5ce00ab7d`
- Dirty/untracked files before proof: one pre-existing untracked `pi-session-2026-05-29T19-11-01-538Z_019e7525-a3a1-74ec-a56c-37d959d27d30.html` was observed during the initial safety check; it was not read, edited, staged, or committed. A later post-proof status check was clean.
- Git root matched `/Volumes/Dev_SSD/Codexify-main`; the `codexify.space` checkout was not touched.

Recent commit surface verification:

- `3dff6c5ffd08e97e92f52e08cd80781e5a79e8c0` changed provider first-token timeout classification surfaces: `guardian/core/ai_router.py`, `guardian/workers/chat_worker.py`, and focused provider/worker/health tests.
- `ffff2f30788e326fa43e5d4594c686e603833a87` changed provider failure/transport token surfaces: `guardian/protocol_tokens.py`, `guardian/core/ai_router.py`, `guardian/workers/chat_worker.py`, `guardian/routes/health.py`, and focused token/provider tests.
- `e500ac1ec80e28290111e35b9c5cb596c4284a96` repaired registry/catalog validation by touching `guardian/core/provider_registry.py`, `guardian/tests/core/test_provider_registry.py`, and `tests/routes/test_llm_catalog.py`.
- `52cba4819280a99f7fc0be5357bcbbce7c3bc3a3` updated the provider tokenization containment review artifact only.
- `bc33d1de01fe1b4648833fdd9858f033c8d383e2` changed frontend timeout/offline presentation contracts, helper code, and focused GuardianChat/runtime token tests.
- `f66f8e50ff0c7eec75eb48fe1d330f9a76c95b66` added the frontend timeout/offline containment review artifact only.
- `9dd9883da0b55962453a79256b97351265ea8003` repaired GuardianChat fixture drift in frontend test files only.

No reviewed recent commit showed vault files, raw note text, real vault paths, supported-profile changes, DB migrations, or release-truth widening.

## Proof Setup

Synthetic provider method:

- A temporary Python proof harness was created at `/private/tmp/codexify_slow_provider_proof.py`.
- The harness started a local `ThreadingHTTPServer` on `127.0.0.1` with OpenAI-compatible endpoints:
  - `GET /v1/models`
  - `POST /v1/chat/completions`
- The stub did not call a real model and required no network egress.
- The temporary server was stopped after the proof.

Temporary timeout method:

- The proof process used in-memory environment overrides only:
  - `LLM_PROVIDER=local`
  - `LOCAL_BASE_URL=http://127.0.0.1:<proof-port>/v1`
  - `CODEXIFY_LOCAL_ENDPOINT_CHAIN=http://127.0.0.1:<proof-port>/v1`
  - `LOCAL_CHAT_MODEL=synthetic-slow-model`
  - `LOCAL_LLM_MODEL=synthetic-slow-model`
  - `LLM_REQUEST_TIMEOUT_SECONDS=1`
  - `LOCAL_REQUEST_CONNECT_TIMEOUT_SECONDS=0.2`
- No committed `.env`, supported profile, or default timeout value was changed.

Runtime path used:

- The harness invoked the real worker/provider execution seam:
  - `guardian.workers.chat_worker._run_chat_task`
  - `guardian.core.chat_completion_service._execute_bounded_tool_turn_completion`
  - `guardian.core.ai_router.stream_local`
  - HTTP `POST /v1/chat/completions` against the synthetic provider
- Persistence and event publication were captured with in-process fakes to avoid writing production chat rows or requiring live Redis/Postgres.
- The normal route/queue entrypoint was not used in this proof; route acceptance is already contractually distinct from completion, and this proof targets the worker/provider first-output wait.

Temporary files:

- `/private/tmp/codexify_slow_provider_proof.py`
- `/private/tmp/codexify_slow_provider_media`

Both lived outside the repo and were removed after the proof.

No real vault content, Obsidian route, Obsidian indexer, or real-vault path was used.

## Synthetic Provider Behavior

- Endpoint reachability was proven by `GET /v1/models` returning HTTP `200` with `synthetic-slow-model`.
- The chat request was accepted at `POST /v1/chat/completions`.
- The posted payload requested streaming: `stream=true`.
- The stub sent `200` response headers for `text/event-stream`, flushed headers, and intentionally withheld the first SSE data line for `2.2s`.
- The isolated proof read timeout was `1.0s`, so first output was withheld longer than the configured request timeout.
- The stub recorded one chat completion request and the paths `["/v1/models", "/v1/chat/completions"]`.

This tested the streaming first-output path. No provider token was emitted before the timeout.

## Chat Runtime Proof

Task path:

- Synthetic task id: `task-synthetic-slow-provider-proof`
- Synthetic thread id: `9001`
- Synthetic turn id: `22222222-2222-4222-8222-222222222222`
- Provider: `local`
- Model: `synthetic-slow-model`

Lifecycle events observed:

- `task.state` with `state=QUEUED`
- `task.running`
- `task.state` with `state=AWAITING_MODEL`
- `task.state` with `state=AWAITING_FIRST_TOKEN`
- terminal `task.failed`
- live `completion.error`

Terminal task evidence:

- `failure_kind=provider_timeout`
- `transport_classification=timeout`
- `runtime_status=timeout`
- `failed_after_state=AWAITING_FIRST_TOKEN`
- `provider_request_started=true`
- `first_output_observed=false`
- `first_token_at` absent
- `first_output_at` absent
- `duration_ms=1002`
- `completion_truth.accepted=true`
- `completion_truth.attempted=true`
- `completion_truth.completed=false`
- `completion_truth.executed=false`
- `completion_truth.fallback_attempted=false`

Assistant persistence check:

- Captured assistant `create_message` calls: `0`
- The timed-out attempt did not persist fake assistant output.
- No fake `first_token_at` or `first_output_at` was fabricated.

## Health and Operator Truth

The proof separated provider reachability from completion success:

- Provider/runtime reachability was proven by the synthetic provider answering `GET /v1/models` with HTTP `200`.
- Completion still failed because the accepted provider request withheld first output past the read timeout.
- The failed attempt evidence came from worker task events and terminal metadata, not from health surfaces.

Queue/worker truth remains distinct from provider-output truth:

- The proof observed worker lifecycle events through `QUEUED`, `AWAITING_MODEL`, and `AWAITING_FIRST_TOKEN`.
- `/health/chat` is still queue/worker truth rather than proof of eventual completion.
- `/api/health/llm` is still provider/runtime truth rather than proof that any given completion attempt will finish.
- Focused health endpoint validation remained green after the proof.

## Frontend Presentation Check

No live browser UI was used. Frontend interpretation was checked through the focused presentation/runtime tests already added for this feature.

Frontend evidence:

- `GuardianChat.lifecycle-timing.test.tsx` and `GuardianChat.offline-banner.test.tsx` passed together.
- `runtimeTokens` tests passed.
- The broad `GuardianChat` target passed after the fixture cleanup commit.

The covered frontend semantics remain:

- Provider timeout evidence with `provider_timeout`, `timeout`, `failed_after_state=awaiting_first_token`, `provider_request_started=true`, and `first_output_observed=false` renders as retryable delayed provider/timeout state, not offline.
- True provider-health offline evidence still renders as offline.
- Generic provider failures remain terminal failures and do not masquerade as successful completion.
- Timeout failure does not display a fake assistant message unless a real persisted assistant message exists.

## Negative Control

A separate offline/unreachable provider control used an unused local port with the same local provider code path.

Observed offline-control evidence:

- Exception type: `HTTPException`
- HTTP status: `502`
- `failure_kind=transport_error`
- `transport_classification=connection_refused`
- `endpoint_resolution.state=degraded`

This is distinct from the reachable slow-provider proof, which produced:

- `failure_kind=provider_timeout`
- `transport_classification=timeout`
- `failed_after_state=AWAITING_FIRST_TOKEN`
- `provider_request_started=true`
- `first_output_observed=false`

The negative control confirms that a reachable provider that withholds first output does not collapse into an offline/unreachable classification.

## What This Proof Does Not Prove

- It does not prove every provider timeout class.
- It does not prove retry/replay linkage.
- It does not prove a full live Redis/Postgres/browser route round trip.
- It does not prove real-vault behavior.
- It does not prove cloud-provider beta support.
- It does not widen release posture.
- It does not alter Obsidian retrieval semantics.

## Caveats

- The proof used a temporary local provider stub rather than a real local model.
- The read timeout was shortened to `1.0s` only inside the disposable proof process.
- The proof was backend/event-focused and did not use live browser automation.
- The route/Redis enqueue seam was not used; the worker/provider seam was exercised directly with captured task events.
- Health-route interpretation was validated by tests and provider reachability checks, not by running live health HTTP routes against the temporary stub.
- The first temporary run required sandbox escalation because the Codex sandbox blocked binding a temporary `127.0.0.1` server.

## Rollback / Cleanup

- Temporary HTTP server: stopped by the proof harness.
- Temporary script: `/private/tmp/codexify_slow_provider_proof.py` removed.
- Temporary media directory: `/private/tmp/codexify_slow_provider_media` removed.
- Committed config changes: none.
- Runtime code changes: none.
- Frontend code changes: none.
- Backend code changes: none.
- Vault files: none.
- Real-vault indexing: not run.

## Validation

Runtime/backend checks:

- `./.venv/bin/pytest -v tests/core/test_ai_router.py`: `17 passed`
- `./.venv/bin/pytest -v tests/workers/test_chat_worker_first_token_timing.py`: `5 passed`
- `./.venv/bin/pytest -v tests/routes/test_health_endpoints.py`: `9 passed, 4 warnings`
- `./.venv/bin/pytest -v tests/contracts/test_protocol_tokens.py`: `24 passed, 1 warning`

Frontend checks:

- `pnpm test -- GuardianChat.lifecycle-timing.test.tsx GuardianChat.offline-banner.test.tsx`: `2 files passed, 6 tests passed`
- `pnpm test -- runtimeTokens`: `1 file passed, 6 tests passed`
- `pnpm test -- GuardianChat`: `11 files passed, 82 tests passed`

Frontend warnings observed but not failures:

- Vitest/node `--localstorage-file` path warning.
- Duplicate `refreshSnapshot` object-literal warnings in existing test mocks.
- Browserslist data age warning.
- React `act(...)` warnings in existing GuardianChat/sidebar tests.

Documentation/diff checks:

- `python3 scripts/validate_docs.py`: passed
- `git diff --check`: passed

## Final Result

PASS.

The proof exercised a reachable synthetic provider over HTTP, caused an intentional first-output read timeout, observed provider timeout classification through the worker/provider runtime seam, distinguished it from a connection-refused offline control, verified no fake assistant output or first-token timestamp was persisted, avoided real-vault content entirely, and kept runtime/frontend validation green.
