# Chat reliability repair integration

Date: 2026-10-03. Classification: `AUTHORIZED_IMPLEMENTATION` under the
ordinary supported chat reliability Goal. This is local integration evidence;
complete supported-Compose qualification remains `HOLD`.

## Atomic Task Spec and source identity

Combine the preserved terminal/model, authored-message, route, durable attempt,
and receipt repairs at `55935fc4b9496d27a7e110933e48819f71169037` with the
local non-streaming accepted-deadline and rescue-deadline repairs at
`90efaf37ddbd7c8b6f9bd82682cf8bf9e2770c39`. Use the local branch
`codex/chat-integrated-runtime-proof-20261003`; preserve both original branches
and leave `main` synchronized to `origin/main` at
`c5c14da8dca1c161ccffe81374ad804cad98f264`. No publication is authorized.

The merge applied automatically. Review of the staged worker diff confirmed
that rescue guards/context now coexist with the durable terminal-receipt and
post-persistence reconciliation code. No conflict resolution or new behavior
was added. The merge adds the eight existing deadline-repair files plus this
receipt. Accepted chat authority, identity, provider selection, persistence,
and lifecycle vocabulary remain governed by the existing chat contracts and
ADR-087; no new ADR is introduced.

## Validation

Evidence: `/private/tmp/codexify-chat-integrated-20261003/`.

- Backend worker, terminal, receipt, streaming/non-streaming deadline,
  explicit-model authority, turn-integrity, and migration consistency group:
  **144 passed, 3 skipped**, with 20 existing warnings. `backend.log` and
  `backend.xml` retain the result and exact test identities.
- The three skipped checks were then run against disposable databases on
  the retained proof Postgres: **3 passed**, with 7 existing warnings.
  They prove upgrade/data preservation, atomic assistant/attempt success
  binding, and extension schema-chain consistency. `postgres.log` and
  `postgres.xml` retain the results. Existing application databases were not
  migrated or cleared by these tests.
- Frontend changed-surface and neighboring request/lock/stream regression
  group: final result **205 passed across 11 files** (`frontend-final.log`).
  The initial group had **204 passed, 1 failed**: the global accepted-stop
  cancellation case observed an early second completion call. Its six-case
  subset passed, the entire 68-case lock/cancellation suite passed alone,
  and the complete group subsequently passed without source changes.
  `frontend.log`, `cancel-retry-probe.log`, and `cancel-retry-full-probe.log`
  preserve those runs. The intermittent cause remains unlocalized; no claim
  of deterministic cancellation-test reliability follows from the rerun.
- `git diff --cached --check` and `git diff --check`: **passed**.

The disposable Postgres test runner obtained credentials in process, retained
only redacted output, and used the existing test-owned database cleanup.
Neither credentials nor environment files were staged.

## Whole-path re-evaluation and remaining obligations

Both repair histories can now be evaluated together. These static and
disposable-database checks do not prove live queue delivery, actual Whoosh'd
generation, browser projection, or a full restart on this integrated source.
The retained runtime snapshot still differed in four Python files during this
task: `accepted_deadline_transport.py`, `ai_router.py`,
`chat_completion_service.py`, and `chat_worker.py`. Prior runtime observations
therefore do not qualify the integration. No running service was changed by
this integration task.

Partial output still accompanies `completion_truth.executed=false` in the
deadline fixture. The inspected chat contracts and shared provider-truth helper
do not define whether this field means observed generation or successful
provider return. Its meaning was not changed here. Active-worker-loss
reconciliation still awaits the previously identified timing/ownership choice;
automatic replay remains disabled.

Context/retrieval, tool/cloud children, PostgreSQL operations, terminal event
publication, cleanup, active-worker recovery, finite drain, and complete
supported-path qualification remain separate unfinished obligations. Mainline
and release claims were not promoted. Documentation follow-through is this
receipt; push, GitHub merge, deployment, and memory updates did not occur.
