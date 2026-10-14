# Accepted chat loopback HTTP deadline participation

Date: 2026-10-03. Baseline: `59acd4fb3`. Classification:
`AUTHORIZED_IMPLEMENTATION`. Supported-Compose qualification remains `HOLD`.

## Atomic Task Spec

Bound the existing accepted-chat loopback HTTP child without changing command
authority, identity, public payloads, or replay behavior. Architecture-impact
lane, aligned with ADR-087, the Chat Runtime Contract, Agent Tool Loop Contract,
and Provider Tool Turn Boundary Contract. Execution is authorized by the active
ordinary-chat reliability Goal under the Codex Development Operator Goal.

This change belongs in `guardian/command_bus/loopback_http_adapter.py`.

Files:
- `guardian/command_bus/loopback_http_adapter.py`
- `guardian/command_bus/invoke.py`
- `guardian/core/chat_completion_service.py`
- `tests/command_bus/test_chat_loopback_accepted_deadline.py`
- `tests/core/test_chat_tool_admission_deadline.py`
- this receipt

Acceptance criteria:
1. Carry the exact typed, server-owned immutable snapshot from the shared tool
   loop through invoke to HTTP. Do not expose deadline authority in the public
   invocation schema or forwarded headers.
2. Bound total HTTP participation by the smaller of the existing 30-second
   child policy and remaining work time. Frames and redirects never reset it.
3. Expired work sends no HTTP request. Canonical accepted-deadline failure must
   propagate through invoke/service, record a failed command when the existing
   store accepts the write, and prevent follow-up generation.
4. Prove native client cancellation/connection closure on real loopback sockets;
   preserve fast/legacy success, ordinary errors, auth forwarding, and policy.
5. Explicitly retain remote-handler, database/terminal, internal-bridge, and
   full runtime qualification obligations. Client closure is not server stop.

Constitutional preflight: the accepted task snapshot owns time authority;
model output proposes a command but grants no authority. Existing Guardian
policy owns execution permission. Existing command runs/events retain their
scope; no new durable object or permission is introduced. Completion evidence
requires actual returned/persisted outcomes, not a client timeout alone.

Board metadata: P1 implementation slice; owner Codex; target Ready for review;
architecture/proof review; dependency is the immutable envelope and prior tool
admission repair. No issue/board mutation is authorized by this packet.

## Causal seam and repair

At baseline, the shared service guarded tool admission but did not pass the
accepted envelope to command execution. The adapter's `timeout=30.0` was an
HTTPX inactivity limit. Continuing response bytes or redirects could keep a
child alive past the parent deadline. Invoke also caught canonical deadline
HTTP exceptions and returned an ordinary failed command result.

The shared service now passes the validated snapshot internally. Invoke passes
it to HTTP and rethrows typed or reconstructed canonical deadline exceptions
after its existing failed-run/event writes. The public request model remains
unchanged and rejects a caller-supplied `accepted_deadline` field.

The adapter anchors the remaining absolute work time to the running loop's
monotonic clock once, checks admission again after preparation, and clips both
request inactivity settings and one total async timer. The timer covers
redirects, response-body reception, and native client cleanup. Cancellation is
awaited and the client closes in `finally`; no blocking request thread is
abandoned. Parent expiry uses the existing error code. A shorter child-policy
timeout remains an ordinary HTTP timeout; existing transport timeout objects
before parent expiry retain their type/identity. Legacy calls preserve the
original request path and omit the new internal keyword.

No command subset, actor, provider/model, permission, confirmation, idempotency,
request/turn identity, assistant schema, token domain, or automatic retry
semantics changed. No new ADR was needed.

## Evidence and validation

The new fixture uses actual HTTPX against an exact guarded `127.0.0.1` origin.
An immutable 720/780-second envelope is aged to a short remaining interval;
architecture intervals are not shortened. Delayed headers, silent body,
trickling body, and a redirect followed by trickling all exercise real sockets.
Assertions observe connection closure, closed clients, no outstanding async
request task, immutable timestamps, and fixture thread cleanup.

The silent-handler negative control remains active after the client observes
deadline exhaustion and disconnects. Teardown releases that synthetic server
work explicitly. This contradicts any claim that HTTP client cancellation
alone establishes remote quiescence.

One test runs the real shared completion service, invoke, in-memory command
store, and HTTP adapter together. Only provider output/context are synthetic:
the existing qualification-shaped tool decision triggers real command HTTP.
Deadline exhaustion produces one failed command, no second provider call, and
no successful completion. This is not live Whoosh'd, PostgreSQL, Redis, or
browser deadline qualification.

- Baseline HTTP proof: six behavioral failures (four slow-response shapes,
  expired admission, and shortened child-policy expiry); four controls passed.
  The initial two invoke cases hit a missing fixture loopback base and are not
  causal evidence. After correcting that fixture, both typed/serialized invoke
  cases failed on swallowed deadline truth; service snapshot inheritance failed
  while its legacy control passed. Logs retain both runs.
- Final focused adapter/service fixture: **30 passed**.
- Command Bus policies, raw invocation routes, service/worker tool loops,
  provider transport convergence, terminal integrity, local provider deadlines,
  worker rescue, and queue deadlines: **261 passed**, zero skips/failures in
  the retained JUnit report.
- Existing frontend failure presentation and inference-state tests: **68 passed**.
- Scoped adapter/invoke/test Ruff, Python compilation, and `git diff --check`:
  **passed**. Whole-service Ruff retains the same **15 pre-existing findings**
  as immutable baseline; no whole-service Ruff success is claimed.
- The wider backend group logs a server-thread connection reset during forced
  transport closure. Its pytest exit is zero and JUnit records zero errors.
  The focused fixture separately verifies its own threads are reaped. Node
  reports its existing localstorage-file warning; Ruff reports deprecated
  top-level configuration. These are retained warnings, not hidden failures.

Commands from repository root:

```sh
PYTHONPATH=. /Volumes/Dev_SSD/Codexify-main/.venv/bin/python -m pytest -o addopts='' -q \
  tests/command_bus tests/routes/test_command_bus_phase1_invoke.py \
  tests/core/test_chat_tool_admission_deadline.py \
  tests/core/test_chat_completion_service_tool_loop.py \
  tests/workers/test_chat_worker_tool_loop.py \
  tests/providers/test_tool_turn_transport_convergence.py \
  tests/core/test_completion_terminal_integrity.py \
  tests/core/test_chat_nonstream_accepted_deadline.py \
  tests/core/test_chat_stream_accepted_deadline.py \
  tests/workers/test_chat_worker_rescue_deadline.py \
  tests/workers/test_chat_worker_queue_deadline.py
cd frontend/src
pnpm exec vitest run --config vitest.config.ts \
  features/chat/__tests__/requestFailurePresentation.test.ts \
  features/chat/__tests__/useInferenceRequestState.test.tsx
```

Root checks: scoped `python -m ruff check`, `python -m py_compile` for the three
runtime and two test files, and `git diff --check`. Evidence root:
`/private/tmp/codexify-chat-loopback-deadline-59acd4fb3-20261003/` contains logs,
JUnit reports, immutable sources, lint comparison, and retained-runtime audit.

Staging is the exact six-file list above. Commit subject:
`fix(chat): bound accepted loopback HTTP execution`.

## Whole-path re-evaluation and remaining obligations

The canonical error reaches the existing worker fallback exclusion and frontend
execution-limit presentation paths; their scoped tests pass. No live terminal
event, durable deadline receipt, browser deadline state, or actual model-chosen
tool turn is qualified by this fixture.

The retained isolated Compose stack is healthy, but a fresh source audit finds
three stale tracked Python files: this adapter, invoke, and the shared service.
Its previous restart/browser success proof evaluated `e1ec21942`. The current
repair has not been loaded into those running processes. Fresh runtime proof
is the next independent proof obligation; the prior canary cannot qualify it.

The automatic ordinary-chat subset contains health and, when separately
authorized, repository search; it does not expose internal bridge commands.
Internal bridge execution, server-side health/search work, synchronous parsing
and preparation, DNS resolver work outside native cancellation guarantees,
Command Bus database writes, context/retrieval, cloud children, persistence,
terminal events/rollback/lock cleanup, and finite drain still need their own
inherited-envelope proof. This task does not declare ADR-087 Slice B/C/D done.

Active-worker-loss timing/ownership and partial-output `executed` meaning remain
unresolved human decisions. The intermittent cancellation test failure remains
unlocalized. Documentation follow-through is this receipt; no current-state
promotion, push, merge to main, deployment, runtime mutation, or memory update
occurred. The full Goal remains active.
