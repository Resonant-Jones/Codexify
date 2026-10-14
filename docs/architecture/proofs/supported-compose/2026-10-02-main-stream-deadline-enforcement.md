# Current-main accepted local stream deadline enforcement

Date: 2026-10-02. Baseline: `f41d2b7cc9e262a3c032f8163d4b1c9216e2a788`,
branch `main`. Authority: active ordinary-chat reliability Goal and Development
Operator Level 0. Architecture-impact implementation follows the real-HTTP
failure proof in `2026-10-02-main-stream-deadline-probe.md`.

Governing sources: current-state HOLD; ADR-001/002/003/038/087; canonical chat
runtime and terminal-evidence contracts. No new ADR, runtime token, acceptance
budget, release claim, dependency, or runtime topology is introduced.

## Repair

The shared completion attempt reads and validates the existing immutable
deadline envelope before provider entry. Expired or malformed in-memory inputs
cannot start provider HTTP. Valid deadline authority reaches `stream_local`.

Deadline-bearing local streams use the existing HTTPX dependency for native
async HTTP I/O behind the synchronous parser interface. One owned event loop
handles the stream; header acquisition, error bodies, and each streamed read
inherit the same absolute work bound. UTC authority is translated once to a
conservative monotonic limit, never renewed by frames, tokens, or endpoint
retries. Connect/read inactivity limits are additionally clipped to remaining
work time. An absolute timeout cancels the actual async I/O operation; it does
not abandon a blocking Requests read in another thread.

The existing streaming parser, terminal evidence, model and endpoint selection,
and request/task/execution-attempt headers remain authoritative. Legacy absent-
envelope calls retain Requests. The shared attempt explicitly closes its
iterator on every outcome, including cancellation and callback failure.

Expiry raises the existing `CHAT_ACCEPTED_TASK_DEADLINE_EXCEEDED` error. The
attempt retains correlation and partial-output observation without mapping
expiry to a provider outage or user cancellation. Partial output never returns
as successful terminal evidence. The shared completion path's assistant insert
is downstream of this throwing boundary; no persistence mechanism is changed.

Deadline cleanup may abort the correlated Whoosh'd request during the existing
terminal reserve. It uses an owned response header or an exact request/task/
execution-attempt inventory match; absent identity and foreign inventory cannot
authorize an abort. The RPC uses an absolute two-second child ceiling clipped
to remaining terminal time. Cleanup is best effort and does not set the
user-cancellation monitor's flag or fabricate confirmation from missing/failed
RPC evidence. Transport teardown closes the client, owned async generators,
loop, and thread within the terminal bound. Explicit cancellation retains its
separate terminal outcome.

Files: `guardian/tasks/chat_deadline.py`,
`guardian/core/accepted_deadline_transport.py`, `guardian/core/ai_router.py`,
`guardian/core/chat_completion_service.py`,
`tests/core/test_chat_stream_accepted_deadline.py`,
`tests/tasks/test_chat_completion_deadline.py`, and this receipt.

## Red and green evidence

The prior eight-case real-HTTP probe established six deadline violations and
two success controls against the baseline. The initial regression suite had
six failures and three passes; its retry fixture offered only one endpoint and
therefore exercised model rejection rather than retry. That fixture was corrected.

An expanded baseline process compiled the exact two core modules from Git
`f41d2b7cc` under their original module names and ran the 14-case actual HTTP
fixture: **10 failed, four passed**, no fixture errors. The baseline uses the
real Requests transport; responses and parser are not mocked. Frozen baseline
source, runner, copied test, log, and XML remain in the external evidence pack.

Final repaired suite: **122 passed across nine files**, exit 0. The 14 stream
cases cover delayed headers, silent bodies, continuing tokenless frames, early
partial output, two-endpoint retry, blocked error bodies, valid success, legacy
success, expired zero-call admission, genuine child inactivity timeout,
explicit cancellation, foreign-request protection, malformed input, and a
trickling abort-response body. Teardown verifies no surviving owned HTTP loop
or cancellation-monitor thread. Deadline fields remain unchanged on failure
and success; observed partial output is retained in failure metadata.

The first repaired run caught a candidate-monitor leak on header failure. The
candidate is now stopped on every exceptional exit. The expanded retry test
also caught an assertion expecting the first endpoint's abort path; it now
verifies the correlated active endpoint. Failed intermediate runs are retained;
they are not used as passing evidence.

## Preserved external HTTP probe

Rerun the original eight network stimuli against repaired source, adding an
exact loopback-port guard for HTTPX as well as Requests. No response, frame,
timeout policy, or parser is replaced to obtain green. Only the accepted stream
transport changes to the implementation above. The fixture's base selection,
synthetic settings/model/key, and supported-profile override remain controlled.

Result: **exit 0**, fixture controls PASS, zero deadline violations. All six
expiring cases produce the canonical deadline error with no output after
expiry; both future and legacy controls retain success. Deadline snapshots are
unchanged, and no owned I/O loop or cancellation monitor remains. Measured
terminal return occurs shortly after the work boundary while bounded cleanup
uses the terminal reserve; this is not late generation.

The external probe does not provide a live Whoosh'd abort acknowledgement.
Request-scoped abort and slow-RPC interruption are instead proven against the
controlled HTTP fixture. Actual Whoosh'd generation/abort readback remains a
separate runtime qualification requirement.

## Validation

From repository root:

```sh
PYTHONPATH=. /Volumes/Dev_SSD/Codexify-main/.venv/bin/python -m pytest -o addopts='' -q \
  tests/core/test_chat_stream_accepted_deadline.py \
  tests/tasks/test_chat_completion_deadline.py \
  tests/core/test_ai_router.py \
  tests/core/test_completion_terminal_integrity.py \
  tests/workers/test_chat_worker_queue_deadline.py \
  tests/workers/test_chat_worker_queued_cancellation.py \
  tests/workers/test_chat_worker_explicit_model_authority.py \
  tests/workers/test_chat_worker_lifecycle_events.py \
  guardian/tests/workers/test_chat_worker_completion_semantics.py

PYTHONPATH=. /Volumes/Dev_SSD/Codexify-main/.venv/bin/python \
  /private/tmp/codexify-main-stream-enforcement-f41d2b7cc-20261002/probe.py

/Volumes/Dev_SSD/Codexify-main/.venv/bin/python -m ruff check \
  guardian/core/accepted_deadline_transport.py guardian/tasks/chat_deadline.py \
  tests/core/test_chat_stream_accepted_deadline.py tests/tasks/test_chat_completion_deadline.py

python3 -m py_compile guardian/core/accepted_deadline_transport.py \
  guardian/tasks/chat_deadline.py guardian/core/ai_router.py guardian/core/chat_completion_service.py
git diff --check
```

Pytest, external probe, four-file scoped Ruff, compilation, and diff check
passed. Pytest emitted eight existing deprecation warnings. Combined core
Ruff remains **failed** on 16 pre-existing findings. Exact baseline files were
independently checked via stdin; the finding multiset matches after normalizing
the old-definition line number in F811's message. No unrelated lint repair is
included, and no full lint success is claimed.

Evidence root: `/private/tmp/codexify-main-stream-enforcement-f41d2b7cc-20261002/`.
Includes baseline/intermediate/final XML and logs, external probe/results,
baseline/current Ruff JSON, and `final-source-sha256.json` for the six source/
test files. Final source hashes are checked before commit.

## Remaining limits

This is controlled real HTTP and focused regression evidence, not supported
Compose, browser, real-model, or PostgreSQL qualification. Context/inventory,
structured/non-streaming and tool/cloud children, persistence/terminal events,
rollback/cleanup outside this transport, and graceful drain remain unqualified
under ADR-087. Safe shutdown is not established by this slice.

Fresh frozen-tip success/failure/recovery evidence through the entire supported
user path remains required. Release truth stays HOLD. No service restart, live
model mutation, queue/PG mutation, push, merge, deploy, or Axis KB addition
occurred. Documentation follow-through is this receipt only.
