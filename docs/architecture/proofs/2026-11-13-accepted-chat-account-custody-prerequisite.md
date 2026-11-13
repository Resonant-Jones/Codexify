# Accepted-chat account custody prerequisite

Date: 2026-11-13. Governing decision: [ADR-112](../adr/112-trusted-worker-account-bound-dispatch.md).
Base: `663d14990acfa0b189eb9bce68092a1fa6b86761`, the authoritative merge of PR #1060.
This is an isolated implementation candidate, not deployed or release-qualified.

## Why this authority chain applies

Inspection of the isolated connector pilot `8f731fabcb99c87ce29888d0ec0254f196232fd7`
established the actual path, not merely architectural similarity:

- `chat_complete` authenticates account scope and queues ordinary chat.
- `enqueue_chat_completion` persists `ChatCompletionAttempt` before publishing.
- `chat_worker._run_chat_task` observes the durable attempt. Its compatibility
  completion wrapper calls the shared `_prepare_chat_tool_exposure` and
  `_execute_bounded_tool_turn_completion`.
- The pilot's Knowledge decision branch rechecks provider availability, then
  uses the shared `freeze_chat_tool_decision` before Command Bus invocation.
- Unbound completions are denied before tool dispatch. Ordinary-lane origin
  excludes voice and hosted rooms. Local transport eligibility still rejects
  Preview/remote/multi-user operation.

Foreground provider reads are independently account-authenticated routes; they
are not background jobs. Legacy GitHub sync is a separate ingestion owner and
its execution-time ConnectorRun cannot supply accepted-work authority.

## Bounded change

The existing `ChatCompletionAttempt` gains nullable `accepted_account_id`.
The authenticated ordinary `chat_complete` route explicitly passes its resolved
account scope into acceptance. No account is inferred from a queued `user_id`.
External authentication subject and canonical account ID may differ; the
existing authenticated mapping remains authoritative. Legacy local scopes
without a resolved account ID do not acquire this new custody.

Hosted-room owner and guest routes also enqueue chat, sometimes with the room
owner in task.user_id. They intentionally do not pass this ordinary-account
acceptance scope. Their attempts and historical rows remain NULL and ineligible
for this new connector prerequisite. Voice creates no accepted attempt.

The insert transaction rechecks canonical account existence and current thread
ownership. Migration `c7e4a1b9d602` extends `ab71d5ce9604`, adds no new store,
performs no backfill, and defines PostgreSQL update immutability for the snapshot
(including NULL-to-value) and the request/task/thread/turn tuple of bound rows.
Terminal and tool-checkpoint lifecycle updates remain permitted. The snapshot
has no account FK that would erase or rewrite historical identity on deletion;
the reader independently requires the canonical account to remain present.

`guardian/core/chat_account_custody.py::resolve_accepted_chat_account` is an
**unconsumed prerequisite seam**. It re-reads the persisted snapshot, compares
queue fields only as consistency evidence, checks current thread/Project owner
and legacy Project conflicts, account existence, current Preview allowlist
eligibility where applicable, durable acceptance, terminal/completed status,
original deadline, cancellation, and exact frozen tool command/argument hash.
It returns ephemeral lineage, not a bearer capability or connector permission.
It accesses no provider credentials. Database/cancellation-store errors deny
with bounded errors. No database lock spans provider network work.

The existing publication-before-acceptance race is classified explicitly: a
prepared but not acknowledged attempt returns an acceptance-pending refusal.
A fresh read after acknowledgement can succeed within the original deadline.
No scheduler, retry loop or dispatcher consumes this yet. Future integration
must reconcile/retry that pending state without premature execution or silently
losing work; this candidate does not claim that liveness requirement is closed.

## Evidence and limits

Tests cover database-backed ownership/tuple/deadline/checkpoint/cancellation and
sequential-account semantics using an isolated SQLite column projection, actual
ordinary-route scope handoff and enqueue propagation, hosted/legacy exclusion,
creation checks, migration column upgrade/downgrade and legacy preservation.
The SQLite schema deliberately does not simulate PostgreSQL constraints/locking.
PostgreSQL trigger DDL is inspected/captured, **not live PostgreSQL proof**.
No serving database, credentials, Docker service or deployment is touched.

The existing persona temperature-routing test
`guardian/tests/test_persona_profile_runtime.py::test_chat_completion_task_uses_backend_temperature_through_completion_routing`
fails with `tool_checkpoint_unavailable` both in this candidate and independently
at pre-candidate docs commit `7815f7735` (same runtime as base main). It is not
repaired by this prerequisite. Passing focused checks are not a global suite pass.

### Candidate validation

Final focused run: **242 passed**, using the existing interpreter at
`/Volumes/Dev_SSD/Codexify-main/.venv/bin/python` with `PYTHONPATH=.` from this
isolated worktree. Suites: `tests/core/test_chat_account_custody.py`,
`test_chat_account_custody_persistence.py`, `test_chat_account_custody_handoff.py`,
`test_chat_completion_service_tool_loop.py`, `test_chat_tool_exposure.py`,
`test_chat_tool_admission_deadline.py`, `test_chat_completion_enqueue_service.py`;
`tests/migration/test_chat_account_custody_migration.py`; and route suites
`test_chat_completion_enqueue_delegation.py`,
`test_chat_complete_latest_turn_integrity.py`,
`test_chat_complete_enqueue_error_tagging.py`,
`test_chat_complete_thread_config_precedence.py`, and
`test_chat_complete_task_created_event_tagging.py`.

New-file Ruff, `git diff --check`, and `make docs PYTHON=python3` passed.
Independent review found no required production correction. Three existing route
fixtures were updated to supply canonical ownership lookup results rather than
unbound MagicMock scalars. This did not weaken the production ownership checks.
The separate persona failure above remains a disclosed baseline limitation.

## Remaining boundary

Original account custody and fail-closed attempt resolution are now code/test
candidate surfaces. **The complete ADR-112 authority remains PARTIAL** until
PostgreSQL immutability/concurrency proof and actual Command Bus/provider
integration demonstrate live scope/revocation, duplicate/retry safety and
cross-account isolation. Merely returning this binding must not authorize a
provider call. Ordinary HTTP-backed commands still have their second account
authentication boundary; no general ASGI adapter or worker bearer protocol is
selected here.

The isolated GitHub credential migration is a sibling of this revision when
based on older main. Reconcile that branch's migration parent before combining
it; do not create a multi-head graph or apply either migration to serving state
as part of this task.

No imported-history permission, HistoryRecallGrant, model exposure, release
claim, supported profile, existing tool visibility or runtime policy is widened.
HOLD remains unchanged. No push/merge/deployment of this runtime candidate is
claimed by this receipt.
