# Exact durable terminal authority in late chat workers

## Authority and scope

Level 0 EXECUTE → PROOF on `codex/chat-postgres-terminal-deadline-20261003`,
starting at `2ab3f8d183ea2d84de09b356d2e25216daabfdc5`. The previous Goal turn
made progress by committing the bounded receipt/retry controller. This Task
integrates the directly human-authorized original-deadline recovery policy into
worker terminal arbitration. ADR-087/091 and the existing durable attempt/message
contracts govern; no new ADR, schema, token or worker-generation authority.

Task Spec and raw evidence:
`/private/tmp/codexify-chat-worker-terminal-authority-2ab3f8d18-20261004/`.
Release remains **HOLD** and the full chat-reliability Goal remains active.

## Changes and evidence boundaries

`guardian/workers/chat_worker.py` reads a request-scoped packet's existing attempt
under a fixed two-second PostgreSQL maintenance scope before execution. Exact
request/task/thread/turn identity is required. Missing identity or read uncertainty
stops execution without an inferred terminal event. Durable assistant completion
wins; an existing durable failed/cancelled outcome is projected without running
provider, retrieval or rescue work. Publication failure does not change durable
truth.

When the attempt has its original immutable deadline snapshot, the worker requires
the accepted packet to carry that same valid envelope. Missing, malformed or
shifted authority is refused, never repaired or renewed. Historical snapshot-null
rows are not backfilled. The immutable UTC envelope is anchored after observation,
so preparation time consumes the original budget. A focused injected preparation
cost of three seconds leaves 717 seconds, not a refreshed 720-second work budget.
Maintenance scopes explicitly reject accepted child-work authority.

Early queued cancellation and cancellation/exception handlers now defer to exact
durable terminal truth after a rejected terminal write. If no terminal outcome can
be confirmed, a request-scoped worker suppresses the alternate inferred failure or
cancellation event; the durable write/read warnings retain uncertainty. Existing
completion projection retains provider metadata only when it belongs to the exact
persisted assistant result. Orphan projection uses the recorded canonical code and
reconciliation timestamp, without invented death time, execution/fallback truth,
provider error, execution run ID or duration.

After original task scopes close, separate bounded observation may reproject an
**already recorded** orphan. It never creates an orphan, updates the attempt,
replays the task, or executes generation. Ordinary completion is not published
again by this postflight observation. An orphan may be observed in both an error
handler and postflight; these are repeat projections of the same durable outcome.

Observed terminal publication owns PostgreSQL and Redis maintenance resource
scopes. The PostgreSQL bound includes the existing live-event outbox mirror;
closing accepted scopes must not accidentally restore an unbounded outbox write.
A real held `events_outbox` table lock expires within the two-second maintenance
bound while the lock remains held. No delayed outbox insert appears after unlock,
and the durable orphan row remains unchanged.

Changed test surfaces are the new focused/native terminal-authority cases,
`test_chat_postgres_deadline.py`, and existing worker fixture seams for streaming,
queue deadlines, tool loops, lifecycle, cancellation, turn integrity, explicit
models and first-token timing. Those orchestration fixtures now explicitly
acknowledge durable attempts/writes rather than accidentally supplying generated
request IDs with no durable repository. They are not native persistence proof.
Malformed request-scoped queue packets now expect no inferred terminal event or
cleanup; a native unacknowledged terminal write likewise retains uncertainty.

## Validation

From the repair repo using `/Volumes/Dev_SSD/Codexify-main/.venv/bin/python`:

- Twelve worker files covering terminal authority, queue and rescue deadlines,
  streaming, tool loops, lifecycle, cancellation, missing trace, turn integrity,
  explicit model selection, first-token timing and heartbeat: **100 passed**.
- Native PostgreSQL query/connect/DNS/pool/maintenance deadlines, attempt migration,
  recovery controller and worker terminal authority: **75 passed**.
- After adding the outbox resource bound, the terminal-authority focused file and
  five native worker cases were rerun. Counts overlap the broader runs; they are
  not additional independent full-runtime qualifications.
- Native cases prove pre-execution orphan priority; post-scope observation; refusal
  of altered original authority; an injected lagging worker clock with a late
  exception losing to the durable orphan; unchanged attempt/snapshot/message rows;
  rejected later failure/cancellation writes; and bounded held-outbox visibility.
  The injected-clock and publication seams are not an actual Compose crash/restart
  or network fault run.
- Ruff comparison introduced zero diagnostics. The worker retains its two existing
  duplicate-key diagnostics; the first-token fixture retains five existing lint
  diagnostics. New tests pass Ruff. Compile and `git diff --check` pass; documentation
  validation applies to this receipt, not runtime behavior.

Initial fixture-related failures and subsequent refinements remain in separate
JUnit/log files. The resource-scope validation and native outbox proof were added
before closeout rather than treating the earlier passing subset as completion.

## Custody, follow-through and remaining work

Read-only custody checks compare all 1,138 frozen source hashes in the retained
source and both application containers, migration, lifecycle/restart counters,
health, queue/lock state and prior thread 37 messages. Protected `main` remains
`0163521312ef767c0884654e70094ae7b44a5eec` with its unrelated staged Dev Log deletion.
Native tests use random disposable databases in the dedicated PostgreSQL proof
container; independent catalog inspection verifies their absence after tests.
No application source/migration refresh, service restart, main mutation, installation,
model download, push, merge or deployment is part of this Task.

The retained application is still the pre-reconciliation candidate and application
migration `d4c69e03a712`; these tests do not qualify the new changes in supported
Compose. Strict recovery-controller task/token cleanup is already implemented,
but the worker's legacy final cleanup still needs its own qualification/repair.
Receipt/UI/operator projection and explicit new-identity retry, unconfirmed-admission
ambiguity, then coherent candidate refresh and fresh ordinary success/failure,
worker-loss, restart/shutdown and persistence proofs remain required. No release
truth or full Goal completion claim is made. Recommended KB follow-through is
limited to this proof receipt; release anchors and shared memory are unchanged.
