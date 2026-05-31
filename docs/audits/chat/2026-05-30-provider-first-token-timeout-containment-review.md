# Provider First-Token Timeout Containment Review

## Scope

This is a containment review for commit `3dff6c5ffd08e97e92f52e08cd80781e5a79e8c0`, which changed provider/runtime timeout classification around `AWAITING_FIRST_TOKEN`.

This review does not change runtime behavior, provider timeout policy, Obsidian retrieval behavior, frontend behavior, database schema, migrations, protocol tokens, or release posture.

## Repository Safety

- Working directory: `/Volumes/Dev_SSD/Codexify-main`
- Git root: `/Volumes/Dev_SSD/Codexify-main`
- Branch: `codex/fix-chat-slash-commands`
- Remote: `origin https://github.com/Resonant-Jones/Codexify.git`
- HEAD before review artifact: `3dff6c5ffd08e97e92f52e08cd80781e5a79e8c0`
- Dirty/untracked files before review: none; `git status --short` was empty.
- `docs/audits/chat/` did not exist before this review and was created only to hold this artifact.

Recent commit surface verification:

- `3dff6c5ffd08e97e92f52e08cd80781e5a79e8c0` touched only provider routing, chat worker failure evidence, and focused provider/worker/health tests:
  - `guardian/core/ai_router.py`
  - `guardian/workers/chat_worker.py`
  - `tests/core/test_ai_router.py`
  - `tests/routes/test_health_endpoints.py`
  - `tests/workers/test_chat_worker_first_token_timing.py`
  - `tests/workers/test_chat_worker_lifecycle_events.py`
  - `tests/workers/test_chat_worker_streaming_chunks.py`
- `fa7d2aeb70bec17495c03a713cd8d43a02003188` touched only `docs/audits/obsidian/2026-05-30-real-vault-scoped-index-proof.md`.
- `a8bf3799ea76521c377d31d49cf67cc571d4ed08` touched only `docs/audits/obsidian/2026-05-30-real-vault-index-rollback.md`.
- The scoped proof artifact and rollback artifact both exist.
- The recent proof commits did not commit vault files, raw note text, real vault paths, screenshots, secrets, or sensitive attachments according to their committed artifact surfaces and repository file lists.

## Reviewed Change Surface

Provider timeout fix files:

- `guardian/core/ai_router.py`
- `guardian/workers/chat_worker.py`
- `tests/core/test_ai_router.py`
- `tests/routes/test_health_endpoints.py`
- `tests/workers/test_chat_worker_first_token_timing.py`
- `tests/workers/test_chat_worker_lifecycle_events.py`
- `tests/workers/test_chat_worker_streaming_chunks.py`

Behavior added:

- Local provider request timeouts now raise structured provider failure details instead of only generic upstream failures.
- Structured details include `failure_kind=provider_timeout`, `transport_classification=timeout`, provider/model/endpoint metadata, and local-runtime endpoint-resolution context when applicable.
- Chat worker terminal `task.failed` metadata now records the request-state evidence needed to distinguish provider timeout after provider dispatch from queue delay, context assembly failure, and task-event visibility gaps.
- Worker timing distinguishes first token from first provider output. Streaming token paths set `first_token_at`; streaming chunk and body-output paths set `first_output_at` without fabricating `first_token_at`.

Tests added or updated by the fix:

- AI router tests assert structured timeout details for local body and streaming provider calls.
- First-token timing tests assert timeout metadata after `AWAITING_FIRST_TOKEN`, no fake `first_token_at`, and no fake `first_output_at`.
- Lifecycle and streaming chunk tests assert state/event ordering remains intact for successful body and streaming completions.
- Health endpoint tests preserve queue/worker and provider/runtime health semantics.

## Token Discipline Review

Reviewed values:

| Value | Surface | Canonical today | Review |
| --- | --- | --- | --- |
| `provider_timeout` | Provider failure metadata, worker `task.failed` metadata, provider registry/model-index failures, tests | Not in `guardian/protocol_tokens.py` | Contract-bearing because it is machine-readable, API/test visible, and repeated across provider surfaces. Follow-up tokenization recommended. |
| `timeout` | Transport classification and worker `runtime_status` metadata | Not in `guardian/protocol_tokens.py` | Contract-bearing as a classification value. Follow-up tokenization recommended with the broader provider failure-kind set. |
| `failed_after_state` | `task.failed` metadata field key | Field key is not tokenized; values come from `guardian.tasks.types.TaskLifecycleState` | Acceptable for this containment slice. The field is event-visible and should be included if a task-event schema/tokenization follow-up formalizes metadata keys. |
| `provider_request_started` | `task.failed` metadata field key | Not tokenized | Acceptable as a boolean evidence field. It is schema-bearing if task-event metadata becomes canonicalized. |
| `first_output_observed` | `task.failed` metadata field key | Not tokenized | Acceptable as a boolean evidence field. It is schema-bearing if task-event metadata becomes canonicalized. |

The current non-tokenized usage is acceptable for this review because the behavior is consistent, test-covered, and does not introduce conflicting vocabulary. It is still close enough to the Runtime Protocol Token Contract to deserve a focused follow-up before this classification surface grows.

Final recommendation: `follow-up tokenization recommended`.

## Timeout Classification Review

Provider timeout is represented as structured failure metadata with:

- `failure_kind=provider_timeout`
- `transport_classification=timeout`
- `runtime_status=timeout`
- `failed_after_state=AWAITING_FIRST_TOKEN` when the worker has dispatched to provider execution and no output has been observed
- `provider_request_started=true`
- `first_output_observed=false`

Offline provider, timeout, context, queue, and task-event visibility classes remain distinguishable:

- Provider timeout is a provider transport/read-timeout classification on the failed attempt.
- Offline provider remains a provider/runtime health or connection-resolution condition, not a synonym for slow provider output.
- Queue and worker delay remain visible through `/health/chat`, queue/worker health, `task.created`, and worker lifecycle evidence.
- Context assembly failures occur before provider dispatch and therefore should not report `AWAITING_FIRST_TOKEN` or `provider_request_started=true`.
- Task-event visibility degradation remains separate from worker execution truth; event publication or UI receipt is not treated as completion.

`failed_after_state` is accurate for the proven seam. It derives from worker-observed lifecycle timings: `STREAMING` if first output was observed, `AWAITING_FIRST_TOKEN` if provider execution started without observed output, `AWAITING_MODEL` if provider execution was not reached, and `QUEUED` for earlier failures. This is request-state evidence, not a claim about provider internals beyond what the worker observed.

## Transcript Integrity Review

Provider timeout does not persist fake assistant output. The exception path publishes terminal failure metadata and exits before assistant response persistence.

The fix avoids fabricating `first_token_at`. Token streaming paths set both `first_token_at` and `first_output_at`; chunk/body paths set `first_output_at` only. Failures before first output preserve both as absent.

Message and request linkage behavior was not broadened by the fix. The worker continues to operate on the existing task payload/source-message contract. The focused validation preserves source-mode behavior, context-directive behavior, and Obsidian-only retrieval behavior. Retry/replay linkage was not live-proven in this review and remains a useful follow-up proof target.

## Task Event and Worker Evidence Review

The worker emits enough lifecycle evidence to classify the failed attempt:

- `task.created` and queue acceptance remain route/queue evidence.
- `task.running` remains worker-start evidence.
- `task.state` events expose request-state movement through queued/model/first-token/streaming/completed phases.
- Terminal `task.failed` includes failure metadata, terminal timings, `failed_after_state`, `provider_request_started`, and `first_output_observed`.

First output is observed accurately for both body and streaming paths:

- Streaming token paths mark the first token and first output.
- Streaming chunk paths mark first output without claiming token-level evidence.
- Non-streaming body completions mark first output without claiming token-level evidence.

Cancellation paths are separated from provider failure paths and were not converted into provider timeouts. They continue to publish `task.cancelled` rather than `task.failed`.

## Health and Operator Truth Review

No health endpoint runtime semantics drift was found.

- `/health/chat` remains queue/worker truth. It can indicate queue and worker availability, heartbeat state, and configured provider context, but it does not prove that a specific chat attempt will complete.
- `/api/health/llm` remains provider/runtime truth. It can report provider reachability and model/runtime posture, but it does not prove per-message completion or first-token delivery.
- A green health surface still must not be interpreted as eventual completion. Operators still need task events and persisted assistant rows to classify a specific failed or completed turn.

The fix improves per-attempt failure evidence without collapsing health truth into request truth.

## Normal Behavior Preservation

Plain non-streaming provider success remains intact through worker body-output lifecycle coverage and AI router coverage.

Streaming provider success remains intact through worker streaming chunk coverage and AI router streaming coverage.

Malformed or failing provider output behavior remains bounded by the existing exception path and structured provider failure details. This review found no evidence that cloud/local fallback behavior was accidentally widened or suppressed.

Existing Obsidian source-mode, context-directive, and Obsidian-only retrieval tests remain green. Obsidian retrieval semantics were not changed.

Known unrelated failures: none observed in the required validation set.

## Real-Vault Safety

This review did not run real-vault indexing and did not call `/api/obsidian/index`.

This review did not inspect, print, summarize, or commit vault contents. It inspected committed audit artifacts and runtime/test source only.

No vault files were committed by the scoped proof or rollback commits reviewed here. The scoped proof and rollback artifacts remain intact.

## Findings

### High

None.

### Medium

None.

### Low

- Provider failure/runtime classification literals are now repeated and test-visible without being canonical protocol tokens. This is not a containment blocker because the implementation is internally consistent and covered, but it should not be allowed to drift as the failure taxonomy grows.

### Non-blocking follow-ups

- Tokenize provider failure-kind and transport-classification values in a dedicated follow-up, including `provider_timeout`, `transport_error`, `timeout`, `connection_refused`, `dns_error`, and `request_error` if they remain API-visible.
- Consider formal task-event metadata keys if `failed_after_state`, `provider_request_started`, and `first_output_observed` become part of a documented event schema.
- Prove reachable-but-slow local provider warmup behavior with synthetic or approved scoped context, not real-vault expansion.
- Audit frontend request-state presentation so reachable-but-slow provider timeout is not displayed as offline.
- Add a focused retry/replay linkage proof for timeout followed by a later successful attempt.

## Required Fixes Before Next Phase

None.

## Recommended Follow-Up Tasks

1. Create a focused protocol-token follow-up for provider failure kinds, transport classifications, and any task-event metadata keys promoted to contract surface.
2. Run a synthetic provider warmup/slow-first-output proof to confirm operator-visible behavior outside mocks.
3. Audit frontend request-state mapping for provider timeout versus offline presentation.
4. Add a retry/replay linkage proof that a timed-out attempt and a later completion remain attached to the correct user/source message.

## Validation

Focused provider/runtime validation:

- `./.venv/bin/pytest -v tests/core/test_ai_router.py` - passed, 17 tests.
- `./.venv/bin/pytest -v tests/workers/test_chat_worker_first_token_timing.py` - passed, 5 tests.
- `./.venv/bin/pytest -v tests/workers/test_chat_worker_lifecycle_events.py` - passed, 2 tests.
- `./.venv/bin/pytest -v tests/workers/test_chat_worker_streaming_chunks.py` - passed, 2 tests.
- `./.venv/bin/pytest -v tests/routes/test_health_endpoints.py` - passed, 9 tests.

Adjacent source/context/Obsidian validation:

- `./.venv/bin/pytest -v tests/core/test_chat_completion_service_context_directives.py` - passed, 11 tests.
- `./.venv/bin/pytest -v tests/routes/test_chat_context_directives.py` - passed, 11 tests.
- `./.venv/bin/pytest -v tests/routes/test_chat_source_mode.py -k "slash or obsidian or context"` - passed, 13 selected tests, 5 deselected.
- `./.venv/bin/pytest -v tests/core/test_obsidian_only_retrieval.py` - passed, 2 tests.

Protocol token validation:

- `./.venv/bin/pytest -v tests/contracts/test_protocol_tokens.py` - passed, 23 tests.

Documentation and diff validation:

- `python3 scripts/validate_docs.py` - passed.
- `git diff --check` - passed.

## Final Verdict

`PASS WITH FOLLOW-UPS`

The provider first-token timeout fix is safely contained for the reviewed seam. It preserves transcript integrity, keeps health semantics distinct from per-request completion truth, and leaves Obsidian retrieval/source-mode behavior intact. The main follow-up is protocol-token discipline for the now-repeated provider failure and transport-classification vocabulary.
