# Chat provider rescue preserves accepted deadline truth

## Authority and evaluated revision

Date: 2026-10-03. Baseline: `82bc0b13d` on
`codex/chat-local-nonstream-deadline-20261003`, based on `main` at `c5c14da8d`.
The active ordinary-chat reliability Goal authorizes this bounded repair under
ADR-087 Slice B, ADR-001/003, and the chat runtime contract. No new ADR, token,
replay policy, worker-loss policy, or release claim is introduced.

This receipt records controlled worker/service tests and frontend presentation
tests. Its directory does not make it supported-Compose or real-model proof.
Current release truth remains `HOLD`.

## Failure established before repair

The worker treated the canonical accepted-deadline HTTP error as eligible for
provider rescue. Candidate discovery ran even after authoritative expiry, and
`fallback_attempted` became true before a fallback passed its budget check.
If a rescue reached the accepted deadline, its error was appended to a fallback
error list and the worker rethrew the earlier provider error. That could hide
the canonical deadline outcome from consumers.

The original nine-case baseline suite ran before worker source changes:
**seven failed, two passed**, exit 1. Future-envelope and legacy rescue success
controls passed. The failure cases covered typed/reconstructed deadline errors,
expiry after initial provider failure, expiry during candidate discovery,
deadline failure inside rescue, and expiry before the next candidate.

An initial fixture run failed all nine cases because the evaluation-isolation
stub omitted a positional argument in the success path. Its signature was
corrected before using the baseline result. The initial logs are preserved.
A standalone harness-import probe also failed on `/app/data/media` before
pytest environment bootstrap; no environment repair was included. All claimed
tests below use the repository pytest bootstrap.

## Scoped repair

The worker now identifies deadline failure by the existing canonical error code,
including a reconstructed `HTTPException`. That outcome never enters candidate
discovery or provider rescue.

For otherwise permitted rescue, the worker checks the original accepted envelope
before and after candidate discovery, before every candidate, and after a failed
candidate. A refusal does not record a fallback attempt or emit a new rescue-start
log. The envelope is parsed without refreshing or repairing its timestamps.

If a rescue produces canonical deadline failure, the worker propagates it rather
than replacing it with the earlier provider error. Deadline context preserves
request/task/provider-attempt correlation, original attempted provider/model,
the most recently dispatched provider/model, visible-output evidence, and the
actual rescue-admission flag. Explicit selection, pinning, visible-output gates,
and permitted pre-deadline or legacy rescue behavior are retained.

The expanded tests caught one further boundary: an ordinary failure in the last
rescue candidate at expiry still restored the initial provider error when no
other candidate existed. A targeted probe produced **one failure, one pass**;
the post-candidate budget check repairs that case too.

## Proof and results

The final fixture contains **12 passing cases**. It drives the real worker
lifecycle and shared completion service with a controlled clock, provider
outcomes, candidate lists, in-memory persistence, and captured task events.
Cloud provider names are synthetic dispatch seams, not cloud execution or
supported-profile admission evidence. Redis publication, database writes,
evaluation scheduling, and provider generation are isolated by the fixture.

All failure cases establish:

- exactly one `task.failed` carrying
  `CHAT_ACCEPTED_TASK_DEADLINE_EXCEEDED`;
- no assistant persistence, `task.completed`, or `task.cancelled`;
- unchanged accepted timestamps and authored/request/task/thread/turn identity;
- matching provider-attempt correlation and owner-checked lock release;
- `fallback_attempted=false` when rescue was refused, and true only after a
  candidate was admitted;
- no new provider call after observed expiry; and
- no provider-offline/transport runtime classification inferred from this code.

The partial-output case preserves `visible_output_emitted=true`, first-output
evidence, and canonical worker `STREAMING` as the failed-after state. It produces
no assistant and invokes no later candidate. An intermediate assertion used
lower-case chat state instead of the worker token; it was corrected to
`TaskLifecycleState.STREAMING.value`. No worker token was changed to pass it.

The complete scoped backend suite passes **68 tests**, with eight existing
deprecation warnings. The five frontend presentation tests pass: the canonical
deadline code takes precedence over queued/streaming and provider-timeout
metadata. Vitest emits an existing Node localstorage-file warning. This is
consumer test evidence, not live event-to-browser delivery.

## Validation

From repository root:

```sh
PYTHONPATH=. /Volumes/Dev_SSD/Codexify-main/.venv/bin/python -m pytest -o addopts='' -q \
  tests/workers/test_chat_worker_rescue_deadline.py \
  tests/workers/test_chat_worker_streaming_chunks.py \
  tests/workers/test_chat_worker_queue_deadline.py \
  tests/workers/test_chat_worker_explicit_model_authority.py \
  guardian/tests/workers/test_chat_worker_completion_semantics.py \
  tests/core/test_chat_nonstream_accepted_deadline.py
/Volumes/Dev_SSD/Codexify-main/.venv/bin/python -m ruff check \
  tests/workers/test_chat_worker_rescue_deadline.py
python3 -m py_compile guardian/workers/chat_worker.py \
  tests/workers/test_chat_worker_rescue_deadline.py
git diff --check
```

From `frontend/src`:

```sh
pnpm exec vitest run --config vitest.config.ts \
  features/chat/__tests__/requestFailurePresentation.test.ts
```

All listed final commands pass. The new test is Black-formatted.
Whole-worker Ruff remains **failed** on two pre-existing findings. Baseline Git
source was checked via stdin; the normalized finding multiset is unchanged.
No unrelated lint repair or full-lint success is claimed.

Evidence root: `/private/tmp/codexify-chat-rescue-deadline-82bc0b13d-20261003/`.
It retains baseline/initial/intermediate/final logs and XML, the last-candidate
probe, initial test and baseline worker source, frontend output, lint comparison,
final source hashes, and final diff.

## Whole-path re-evaluation and limits

The tested worker now sends the canonical deadline outcome through its normal
failure projection and lock-cleanup path. The existing frontend prioritizes that
code as an execution-time-limit failure rather than a provider failure.
This does not prove live Redis delivery, durable attempt terminalization,
browser readback, or source-thread assistant reconciliation.

The partial-output fixture still records `completion_truth.executed=false`
alongside visible generation evidence. This task does not qualify that field's
generation-versus-success semantics; execution-truth reconciliation remains an
open audit item. No claim that every operator-visible field is now qualified
follows from the deadline repair.

Candidate discovery itself, context/retrieval, tool/command and cloud child
duration, PostgreSQL, terminal persistence/events, and cleanup outside the
transport still require finite-envelope proof/repair. This task only gates rescue
admission and preserves the authoritative failure once observed. It does not
claim complete ADR-087 B/C enforcement or safe Slice D drain.

The prior Goal branch's browser, terminal projection, and receipt repairs remain
separate from this branch and `main`. Active-worker-loss recovery still requires
the previously identified human timing/ownership decision; no option is selected
here, and automatic replay remains off.

Existing proof/Preview containers were inventoried but not changed. No live
queue, database, provider/model, service restart, push, merge, deploy, or memory
update occurred. Documentation follow-through is this receipt. Fresh complete
supported-Compose/browser qualification and release promotion remain deferred.
