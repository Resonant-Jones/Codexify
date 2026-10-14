# Returned command failure cannot become chat success

Date: 2026-10-03. Baseline: `afeaeb209`. Classification:
`AUTHORIZED_IMPLEMENTATION`; architecture-impact lane. Full qualification
remains `HOLD`.

## Atomic Task Spec and authority

Stop the existing shared tool loop when invoke returns `failed` or `blocked`,
before reinjection/final generation/persistence. Preserve command run and
message/request/tool-turn identity, status, and bounded diagnostics in existing
failure metadata. Keep completed-command continuation, provider authority,
read-only flags, deadline precedence, and existing worker failure/receipt
behavior. Do not reinterpret HTTP statuses or asynchronous command states.

This change belongs in `guardian/core/chat_completion_service.py`.

Files: that shared service, `tests/core/test_chat_command_result_truth.py`,
`tests/workers/test_chat_worker_tool_loop.py`, and this receipt. Validation is
the scoped backend command below, Ruff on changed tests, Python compilation,
immutable service lint comparison, and `git diff --check`. Stage those four
files only; commit subject: `fix(chat): stop on returned command failure`.
Closeout requires changes/files, validation, commit, ADR classification,
documentation, whole-path assessment, and limits. P1; owner Codex; target Ready
for review; architecture/proof review.

Authority is the explicit reliability Goal under the Codex Development Operator
Goal. The Agent Tool Loop Contract's Failure Rules require command failure to
stop the runtime with `tool_command_failed`; provider/advertised authority
remains under the Provider Tool Turn Boundary Contract. Existing blocked-command
semantics use `tool_command_blocked`. ADR-087's deadline check remains before
returned-result classification, so parent exhaustion still wins. No new ADR or
canonical token was introduced.

Preflight: the returned command status is execution evidence; Guardian policy
owns command authority; the accepted snapshot owns deadline authority. Only
existing worker-controlled failure writes/events are used. No new durable
object, permission, state domain, or automatic replay policy is created.

## Baseline and repair

The service already stopped on thrown invocation errors. For a returned failed
result, however, it still reinjected that result, requested a final answer, and
assigned `toolTurnState=completed` / `tool_turn_completed`. Returned blocked
results briefly set a blocked reason, then overwrote it with completion too.

The new guard raises the existing `ToolLoopExecutionError` before either
reinjection or final provider dispatch. Metadata retains exact identities,
command run, actual status, and the matching failed/blocked canonical reason.
The diagnostic uses existing credential scrubbing and a 1,024-character bound;
arguments, headers, and full command results are not copied into the failure.

The worker already excludes this error class from provider rescue and forwards
the bounded tool fields into `task.failed`. No worker production change was
required. A successful returned command still invokes the provider exactly
twice and completes through the existing bounded path.

## Validation and evidence

Synthetic Whoosh'd strict-structured and DeepSeek native carrier fixtures run
the real shared service with sync/async returned failed and blocked results.
These fixtures verify one command, one provider call, unchanged timestamps,
read-only/confirmation flags, and retained identity/status/reason. Completed
controls retain their second provider call. Diagnostic controls check bounded
credential-safe projection. Neither provider is live in this fixture.

The existing worker harness runs the real worker/shared service with a mocked
command result, provider, message adapter, and event sink. For returned failed
and blocked results, it proves no assistant insert call, one `task.failed`, no
`task.completed`, no fallback discovery, and matching failure metadata. This is
test evidence, not actual durable PostgreSQL/Redis or browser failure proof.

- Baseline: **10 failed, 4 passed**. Eight service cases wrongly continued;
  both worker cases called assistant persistence once and published completion.
- Initial repaired service/worker group: **17 passed**.
- Final scoped group, including diagnostic controls: **114 passed**, zero
  failures/errors/skips in JUnit.
- Changed-test Ruff, Python compilation, `git diff --check`: **passed**.
- Whole-service Ruff remains at the same **15 pre-existing findings** as the
  immutable baseline after source-line normalization; no full lint pass claimed.
- Existing synthetic-worker baseline logs include unavailable durable-link/eval
  fixture capabilities and graph warnings. Those mocks do not establish durable
  behavior. Ruff also reports the existing deprecated top-level configuration.

```sh
PYTHONPATH=. /Volumes/Dev_SSD/Codexify-main/.venv/bin/python -m pytest -o addopts='' -q \
  tests/core/test_chat_command_result_truth.py \
  tests/core/test_chat_completion_service_tool_loop.py \
  tests/core/test_chat_tool_admission_deadline.py \
  tests/workers/test_chat_worker_tool_loop.py \
  tests/workers/test_chat_worker_rescue_deadline.py \
  tests/providers/test_tool_turn_transport_convergence.py \
  tests/command_bus/test_chat_loopback_accepted_deadline.py \
  tests/core/test_completion_terminal_integrity.py
```

Evidence: `/private/tmp/codexify-chat-command-truth-afeaeb209-20261003/` contains
baseline/final logs and XML, immutable service source, and lint comparison.

## Whole-path re-evaluation

The last live ordinary success at `065fb06e7` automatically advertised zero
tools and used a plain answer. It remains valid for its evaluated revision and
does not qualify this new returned-result guard. The retained runtime has not
loaded this service repair. A fresh runtime canary is still required.

The frontend's current task-failure presenter labels this typed tool failure
with its generic Provider error text. That is a separate identified presentation
gap; it is not silently repaired in this task. Important failure/recovery proof,
server-side command/context/PostgreSQL/terminal bounds, worker-loss authority,
and full supported-Compose qualification remain open. Documentation follow-
through is this receipt. No current-state promotion, push, main merge, runtime
mutation, deployment, or memory update occurred. The broader Goal stays active.
