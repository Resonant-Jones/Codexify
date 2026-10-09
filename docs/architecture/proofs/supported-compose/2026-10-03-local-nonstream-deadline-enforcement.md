# Local non-streaming accepted-deadline enforcement

## Evaluated scope and authority

Date: 2026-10-03. Baseline: `c5c14da8dca1c161ccffe81374ad804cad98f264`.
Task branch: `codex/chat-local-nonstream-deadline-20261003`.

The active ordinary-chat reliability Goal authorizes this bounded repair under
accepted ADR-087 Slice B. ADR-001, ADR-003, and the chat runtime contract retain
acceptance/completion, identity, provider authority, and canonical failure
boundaries. No new architecture or release claim is introduced.

This receipt is controlled real-HTTP and focused regression evidence. Its location
in this directory does **not** make it supported-Compose qualification. Release
truth remains `HOLD` in `00-current-state.md`.

## Proven failure and repair

The shared completion service selected a separate non-streaming route for the
qualified Whoosh'd structured target. That route called `chat_with_ai` and
`call_local` without the accepted envelope. Requests' finite inactivity policy
did not bound total headers/body duration or endpoint retries to remaining task
time. The existing local streaming transport did not participate in that route.

The initial nine-case real loopback HTTP suite ran before source changes:
**six failed, three passed**, exit 1. Delayed headers, silent body, trickling body,
delayed error body, endpoint retry, and the foreign-inventory case failed deadline
expectations. Future and legacy success plus expired-task zero-call controls
passed. Baseline XML, log, initial test, and source are preserved externally.

The repair passes the existing immutable envelope through the service and router
into local non-streaming inference. One `AcceptedDeadlineTransport` remains owned
through the entire endpoint sequence. Headers and complete body reads share its
single absolute monotonic work limit. The completed body is cached before native
HTTP I/O closes, so existing response parsing does not schedule more body I/O.

Deadline failure stays the canonical
`CHAT_ACCEPTED_TASK_DEADLINE_EXCEEDED` exception, with request/task/provider-attempt
correlation and `visible_output_emitted=false`. It is not enriched with misleading
provider-error terminal evidence. No late response is returned as success by the
tested HTTP cases.

The existing streaming request-abort logic is shared with non-streaming inference.
It uses the active response's Whoosh'd request header or an inventory entry
matching **all three** request/task/attempt identifiers. The request-scoped abort
uses the terminal reserve and existing two-second control-RPC child limit. A
foreign inventory entry is not aborted. No automatic replay, model selection,
tool authority, queue identity, persistence, or release policy changes.

## Proof surface and results

The final new fixture has **13 passing cases**:

- delayed headers, silent body, trickling body, delayed error body, and two-endpoint
  retry terminate with the canonical deadline failure;
- task deadline timestamps remain unchanged, correlation matches actual HTTP
  headers, and the five expiring cases make one correlated abort request;
- expired admission makes zero provider requests;
- valid future-envelope and legacy structured responses retain the exact output
  and strict request shape;
- future-envelope and legacy plain local non-streaming calls retain their output
  and do not acquire structured request fields;
- a foreign inventory entry remains untouched;
- genuine child inactivity remains a provider timeout rather than deadline
  exhaustion; and
- a trickling abort response cannot escape the two-second terminal child bound.

The fixture uses synthetic settings, model alias, tool definition, and responses,
with real Requests/HTTPX network I/O to one ephemeral loopback server. The active
supported-profile selection is disabled in this controlled fixture; base-candidate
selection is restricted to its server. Network guards reject other destinations.
Teardown checks that no owned `accepted-chat-http` thread survives. No real model,
Whoosh'd execution/abort acknowledgement, Guardian command execution, queue,
PostgreSQL, or browser runtime is proven by this fixture.

The five-file provider/stream/tool regression suite passes **98 tests**. The six
worker/deadline/cancellation files pass **61 tests** with eight existing
deprecation warnings. Three frontend failure/presentation/lifecycle files pass
**136 tests**, including canonical deadline `task.failed` and `completion.error`
projection. These are test evidence for the existing consumers, not proof that a
live queue event reached a browser or that a terminal outcome became durable.

## Validation

From repository root:

```sh
PYTHONPATH=. /Volumes/Dev_SSD/Codexify-main/.venv/bin/python -m pytest -o addopts='' -q \
  tests/core/test_chat_nonstream_accepted_deadline.py \
  tests/core/test_chat_stream_accepted_deadline.py tests/core/test_ai_router.py \
  tests/providers/test_whooshd_tool_adapter.py \
  tests/core/test_chat_completion_service_tool_loop.py

PYTHONPATH=. /Volumes/Dev_SSD/Codexify-main/.venv/bin/python -m pytest -o addopts='' -q \
  tests/tasks/test_chat_completion_deadline.py \
  tests/workers/test_chat_worker_queue_deadline.py \
  tests/workers/test_chat_worker_queued_cancellation.py \
  tests/workers/test_chat_worker_explicit_model_authority.py \
  tests/workers/test_chat_worker_lifecycle_events.py \
  guardian/tests/workers/test_chat_worker_completion_semantics.py

/Volumes/Dev_SSD/Codexify-main/.venv/bin/python -m ruff check \
  guardian/core/accepted_deadline_transport.py \
  tests/core/test_chat_nonstream_accepted_deadline.py
python3 -m py_compile guardian/core/ai_router.py \
  guardian/core/accepted_deadline_transport.py guardian/core/chat_completion_service.py
git diff --check
```

From `frontend/src`:

```sh
pnpm exec vitest run --config vitest.config.ts \
  features/chat/__tests__/requestFailurePresentation.test.ts \
  features/chat/__tests__/useInferenceRequestState.test.tsx \
  features/chat/__tests__/GuardianChat.turn-lock-lifecycle.test.tsx
```

All listed commands pass. The new test file is Black-formatted. Core-wide scoped
Ruff for `ai_router.py` and `chat_completion_service.py` remains **failed** on 16
pre-existing findings. Baseline Git source was checked via stdin and compared
independently: the finding multiset is unchanged after normalizing definition
line numbers. No unrelated lint repair or full-lint success is claimed.

Evidence root:
`/private/tmp/codexify-local-nonstream-c5c14da8d-20261003/`.
It retains baseline and final logs/XML, the initial baseline test and source,
worker/frontend results, lint comparison, final diff, and final source hashes.

## Whole-path re-evaluation and remaining limits

The existing worker delegates to this shared service, and the existing frontend
recognizes the same canonical deadline failure. Their focused tests pass.
This closes the tested local non-streaming HTTP escape hatch only; it does not
complete ADR-087 Slice B or qualify the entire supported user path.

Inventory/context/retrieval before dispatch, cloud and tool/command children,
worker rescue admission, PostgreSQL, assistant persistence, terminal evidence
durability/publication, and rollback/cleanup outside this transport still need
their own deadline proof/repair. Slice D graceful drain remains downstream of
complete B/C enforcement and runtime qualification.

The prior Goal branch `codex/chat-terminal-model-projection-20261003` retains its
22 commits, including browser hydration, terminal projection, durable receipt,
and worker-restart work; they are not integrated into this branch or `main`.
Active-worker-loss recovery still needs the human decision already identified
between immutable-deadline reconciliation and task-scoped confirmed-loss
authority. Neither option is chosen by this repair; automatic replay stays off.

The observed proof and Preview containers were inventoried but not modified.
No live queue, database, provider/model, service restart, push, merge, deploy, or
Axis memory update occurred. Documentation follow-through is this receipt;
current-state release promotion and complete fresh supported-Compose/browser
qualification remain deferred.
