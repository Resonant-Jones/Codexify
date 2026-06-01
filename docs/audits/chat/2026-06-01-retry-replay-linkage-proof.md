# Retry / Replay Linkage Proof

## Scope

This proof targets transcript and source-message linkage across a timed-out
provider attempt and a later successful explicit second attempt in the primary
Guardian chat completion loop.

This proof does not change runtime behavior, timeout defaults, provider fallback
behavior, frontend behavior, provider registry/catalog semantics, Obsidian
retrieval behavior, supported profiles, database schema, migrations, ADRs, or
release posture.

## Repository Safety

- Working directory: `/Volumes/Dev_SSD/Codexify-main`
- Git root: `/Volumes/Dev_SSD/Codexify-main`
- Branch: `codex/fix-chat-slash-commands`
- Remote: `origin https://github.com/Resonant-Jones/Codexify.git`
- HEAD before artifact: `2ec2144cb9df605b7896402a6b667dfc7acd0aa4`
- Dirty/untracked files before proof: none; `git status --short` was empty.
- Git root matched `/Volumes/Dev_SSD/Codexify-main`; the `codexify.space`
  checkout was not touched.

Recent commit surface verification:

- `3dff6c5ffd08e97e92f52e08cd80781e5a79e8c0` touched provider first-token
  timeout classification, chat worker, and focused provider/worker/health tests.
- `ffff2f30788e326fa43e5d4594c686e603833a87` touched provider/runtime token,
  router, health, worker, and focused token/provider tests.
- `e500ac1ec80e28290111e35b9c5cb596c4284a96` touched provider registry and
  catalog validation repair surfaces only.
- `52cba4819280a99f7fc0be5357bcbbce7c3bc3a3` touched only the provider
  tokenization containment review artifact.
- `bc33d1de01fe1b4648833fdd9858f033c8d383e2` touched frontend timeout/offline
  presentation contracts, helpers, components, and focused tests only.
- `f66f8e50ff0c7eec75eb48fe1d330f9a76c95b66` touched only the frontend
  timeout/offline containment review artifact.
- `9dd9883da0b55962453a79256b97351265ea8003` touched GuardianChat frontend
  test fixtures only.
- `2ec2144cb9df605b7896402a6b667dfc7acd0aa4` touched only
  `docs/audits/chat/2026-06-01-synthetic-slow-provider-warmup-proof.md`.

No reviewed recent commit showed vault files, raw note text, real vault paths,
supported-profile edits, DB migrations, or release-truth widening.

## Proof Setup

Provider stub method:

- A temporary Python harness was created at
  `/private/tmp/codexify_retry_replay_linkage_proof.py`.
- The harness started a local OpenAI-compatible `ThreadingHTTPServer` on
  `127.0.0.1` with:
  - `GET /v1/models`
  - `POST /v1/chat/completions`
- The first chat request sent streaming headers, accepted the request, and
  withheld first output for `2.2s`.
- The second chat request returned a normal streaming assistant response.
- The stub did not call a real model and required no network egress.

Timeout method:

- The proof process used isolated in-memory environment overrides only:
  - `LLM_PROVIDER=local`
  - `LOCAL_BASE_URL=http://127.0.0.1:<proof-port>/v1`
  - `CODEXIFY_LOCAL_ENDPOINT_CHAIN=http://127.0.0.1:<proof-port>/v1`
  - `LOCAL_CHAT_MODEL=synthetic-retry-model`
  - `LOCAL_LLM_MODEL=synthetic-retry-model`
  - `LLM_REQUEST_TIMEOUT_SECONDS=1`
  - `LOCAL_REQUEST_CONNECT_TIMEOUT_SECONDS=0.2`
- No committed `.env`, supported profile, or default timeout value was changed.

Retry/replay method:

- The proof modeled retry/replay as a second explicit `ChatCompletionTask` for
  the same authored source user message.
- Both attempts used the same synthetic `thread_id`, `turn_id`, and
  `latest_turn_message_id`.
- Each attempt used a distinct `task_id` and `request_id`.

Runtime path used:

- `guardian.workers.chat_worker._run_chat_task`
- `guardian.core.chat_completion_service._execute_bounded_tool_turn_completion`
- `guardian.core.ai_router.stream_local`
- HTTP `POST /v1/chat/completions` against the synthetic provider

Persistence and event publication were captured with in-process fakes so the
proof did not write production chat rows or require live Redis/Postgres. The
route/Redis enqueue seam was not used; route acceptance remains distinct from
completion proof.

Temporary files:

- `/private/tmp/codexify_retry_replay_linkage_proof.py`
- `/private/tmp/codexify_retry_replay_media`

Both lived outside the repo and were removed after the proof.

No real vault content, Obsidian route, Obsidian indexer, or real-vault path was
used.

## Attempt Model

Current runtime attempt identity:

- Durable authored message identity: `latest_turn_message_id=501`
- Turn correlation identity: `turn_id=33333333-3333-4333-8333-333333333333`
- Failed attempt task id: `task-retry-linkage-timeout`
- Failed attempt request id: `request-retry-linkage-timeout`
- Successful attempt task id: `task-retry-linkage-success`
- Successful attempt request id: `request-retry-linkage-success`

The runtime does not currently expose a durable per-attempt database row for
chat completion attempts. The proof therefore uses task IDs, request IDs where
surfaced, terminal task events, `latest_turn_message_id`, trace metadata, and
assistant-message metadata as the current evidence set.

Both attempts were linked to the same authored source message by:

- `thread_id=9102`
- `turn_id=33333333-3333-4333-8333-333333333333`
- `latest_turn_message_id=501`
- `messageId=501` in the successful completion payload/metadata
- successful assistant `extra_meta.turn_id` matching the shared `turn_id`

Caveat: the proof does not claim first-class durable replay semantics. It proves
the current explicit-second-attempt path preserves linkage and transcript
integrity under the available identity surfaces.

## Failed Attempt Evidence

Task id: `task-retry-linkage-timeout`

Lifecycle events observed:

- `task.state` with `state=QUEUED`
- `task.running`
- `task.state` with `state=AWAITING_MODEL`
- `task.state` with `state=AWAITING_FIRST_TOKEN`
- terminal `task.failed`
- live `completion.error`

Terminal failure metadata:

- `failure_kind=provider_timeout`
- `transport_classification=timeout`
- `runtime_status=timeout`
- `failed_after_state=AWAITING_FIRST_TOKEN`
- `provider_request_started=true`
- `first_output_observed=false`
- `latest_turn_message_id=501`
- `turn_id=33333333-3333-4333-8333-333333333333`
- `completion_truth.accepted=true`
- `completion_truth.attempted=true`
- `completion_truth.completed=false`
- `completion_truth.executed=false`
- `completion_truth.fallback_attempted=false`

Assistant persistence check:

- Assistant messages after failed attempt: `0`
- No fake assistant message was persisted.
- No fake first-output evidence was emitted.

## Later Successful Attempt Evidence

Task id: `task-retry-linkage-success`

Provider success behavior:

- The second synthetic provider request returned a streaming assistant response
  within the isolated timeout.
- Successful lifecycle sequence:
  - `QUEUED`
  - `AWAITING_MODEL`
  - `AWAITING_FIRST_TOKEN`
  - `STREAMING`
  - `COMPLETED`

Assistant persistence evidence:

- Persisted assistant message id: `701`
- `persistence_outcome=persisted`
- `completion_truth.completed=true`
- `completion_truth.executed=true`
- `message.created` domain event carried:
  - `task_id=task-retry-linkage-success`
  - `thread_id=9102`
  - `message_id=701`
  - `role=assistant`
  - the shared `turn_id`

Source thread and source message linkage:

- Successful terminal payload carried `latest_turn_message_id=501`.
- Successful terminal payload carried `messageId=501` as source-message
  identity and `message_id=701` as assistant-message identity.
- Successful trace carried:
  - `latest_turn_message_id=501`
  - `retrieval_target=latest_turn`
  - `retrieval_query_matches_latest_turn=true`
  - `requestId=request-retry-linkage-success`
- Assistant message metadata carried `turn_id` matching the source turn.

Ordering evidence:

- Transcript order after both attempts:
  - user/source message `501`
  - assistant message `701`

The failed attempt terminal event remained distinct under
`task-retry-linkage-timeout`; the successful attempt did not overwrite or
backfill the failed attempt's terminal evidence.

## Transcript Integrity

After both attempts:

- User/source message count for source id `501`: `1`
- Total user messages: `1`
- Total assistant messages: `1`
- Failed-attempt assistant messages: `0`
- Successful-attempt assistant messages: `1`
- Assistant turn ids: `33333333-3333-4333-8333-333333333333`

Ghost reply check:

- No assistant message existed after the failed attempt.
- The only assistant message was created by the successful task.
- The assistant message carried the shared `turn_id` and remained in the same
  synthetic thread.

Duplicate assistant check:

- Exactly one assistant message was persisted after the second attempt.
- The failed attempt did not create a duplicate or placeholder assistant row.
- The successful attempt did not create multiple assistant rows.

Source-thread truth interpretation:

- The authored source turn remains the single user message.
- The first attempt is a failed execution attempt against that message.
- The second attempt is an explicit later execution attempt against the same
  message.
- The transcript represents one user turn answered once, not two user turns or a
  detached assistant reply.

## Event and Operator Truth

Task-event distinction:

- Failed attempt: `task-retry-linkage-timeout`, terminal `task.failed`.
- Successful attempt: `task-retry-linkage-success`, terminal
  `task.completed`.
- Both attempts carried the same `turn_id` and `latest_turn_message_id`.
- Terminal payloads remained separately observable by task id.

Route acceptance versus completion:

- This proof did not use the route/Redis enqueue seam.
- The architecture contract still holds: route acceptance proves lock/enqueue,
  not completion.
- Attempt completion truth comes from worker events and assistant persistence.

Health versus request truth:

- Provider reachability was proven by `GET /v1/models` returning HTTP `200`.
- The first completion attempt still failed because first output exceeded the
  read timeout.
- Health surfaces cannot prove a specific attempt completed.
- Operators must read health, task events, and persisted assistant rows as
  distinct evidence surfaces.

Operators can infer from this proof that the current explicit-second-attempt
path can preserve source-message linkage after a timeout. Operators cannot infer
that automatic retry/replay exists or that durable attempt rows exist.

## Frontend Presentation Check

No live browser UI was used. Frontend interpretation was checked through the
focused presentation/runtime tests already added for this feature.

Frontend evidence:

- `GuardianChat.lifecycle-timing.test.tsx` and
  `GuardianChat.offline-banner.test.tsx` passed together.
- `runtimeTokens` tests passed.
- The broad `GuardianChat` target passed.

Covered frontend semantics remain:

- Failed provider-timeout attempt remains a retryable timeout state, not
  offline.
- True provider-health offline remains distinct.
- Later assistant output is displayed only when real assistant output exists.
- Generic provider failures do not masquerade as successful completion.

## Negative Control

The proof included a true unreachable-provider control using a copied settings
object pointed at an unused local port.

Observed offline-control evidence:

- Exception type: `HTTPException`
- HTTP status: `502`
- `failure_kind=transport_error`
- `transport_classification=connection_refused`

This remains distinct from the reachable timeout attempt:

- `failure_kind=provider_timeout`
- `transport_classification=timeout`
- `failed_after_state=AWAITING_FIRST_TOKEN`
- `provider_request_started=true`
- `first_output_observed=false`

## What This Proof Does Not Prove

- It does not prove every provider timeout class.
- It does not prove automatic retry behavior.
- It does not prove a first-class durable replay/attempt table.
- It does not prove a full live Redis/Postgres/browser route round trip.
- It does not prove full real-vault behavior.
- It does not prove cloud-provider beta support.
- It does not widen release posture.

## Caveats

- The proof used a temporary local provider stub rather than a real local model.
- The read timeout was shortened to `1.0s` only inside the disposable proof
  process.
- The route/Redis enqueue seam was not used; the worker/provider seam was
  exercised directly with captured task events and fake persistence.
- Current runtime evidence uses task IDs, request IDs, `turn_id`, and
  `latest_turn_message_id`; it does not include durable per-attempt rows.
- Live browser UI was not used.
- The first temporary proof run required sandbox escalation because the Codex
  sandbox blocked binding a temporary `127.0.0.1` provider server.

## Rollback / Cleanup

- Temporary HTTP server: stopped by the proof harness.
- Temporary script: `/private/tmp/codexify_retry_replay_linkage_proof.py`
  removed.
- Temporary media directory: `/private/tmp/codexify_retry_replay_media`
  removed.
- Committed config changes: none.
- Runtime code changes: none.
- Frontend code changes: none.
- Backend code changes: none.
- Vault files: none.
- Real-vault indexing: not run.

## Validation

Runtime/backend checks:

- `./.venv/bin/pytest -v tests/core/test_ai_router.py`: `17 passed`
- `./.venv/bin/pytest -v tests/workers/test_chat_worker_first_token_timing.py`:
  `5 passed`
- `./.venv/bin/pytest -v tests/workers/test_chat_worker_lifecycle_events.py`:
  `2 passed`
- `./.venv/bin/pytest -v tests/workers/test_chat_worker_streaming_chunks.py`:
  `2 passed`
- `./.venv/bin/pytest -v tests/routes/test_health_endpoints.py`:
  `9 passed, 4 warnings`
- `./.venv/bin/pytest -v tests/contracts/test_protocol_tokens.py`:
  `24 passed, 1 warning`

Frontend checks:

- `pnpm test -- GuardianChat.lifecycle-timing.test.tsx GuardianChat.offline-banner.test.tsx`:
  `2 files passed, 6 tests passed`
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

The proof exercised a failed reachable-provider timeout attempt and a later
successful explicit second attempt against the same source message. The failed
attempt persisted no assistant output, the successful attempt persisted exactly
one assistant output, both attempts remained attributable to the same authored
source turn, no ghost reply or duplicate assistant output appeared, no
real-vault content was used, and validation passed.
