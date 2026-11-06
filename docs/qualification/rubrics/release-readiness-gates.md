# Release Readiness Gates Qualification Rubric

## Qualification ID

`release-readiness-gates`

## Version

`1`

## Qualification metadata

```yaml qualification-metadata
qualification_id: release-readiness-gates
version: 1
title: Release Readiness Gates
scope: The eight release-gate behaviours of the supported local-first runtime, exercised together on one frozen evaluated tip, each judged PASS, FAIL or UNPROVEN from a named observable surface
surface_paths:
  # 1. queue / worker
  - guardian/queue/redis_queue.py
  - guardian/queue/account_import_queue.py
  - guardian/queue/document_embed_queue.py
  - guardian/workers/chat_worker.py
  - guardian/workers/document_embed_worker.py
  # 2. deadline
  - guardian/core/chat_completion_service.py
  - guardian/core/chat_postgres_deadline.py
  - guardian/tasks/chat_deadline.py
  # 3. graceful stop
  - guardian/workers/coding_worker.py
  - backend/scripts/docker/run_worker_coding.py
  # 4. lock
  - guardian/queue/turn_lock.py
  - guardian/core/db.py
  - guardian/agents/store.py
  # 5. migration deployment
  - backend/scripts/docker/run_migrator.py
  - guardian/db/migrations/versions/**
  # 6. browser
  - frontend/src/features/chat/**
  - frontend/src/components/chat/**
  # 7. import to recall
  - guardian/services/openai_account_import.py
  - guardian/services/imported_history_evidence.py
  - guardian/memoryos/**
  # 8. scope isolation
  - guardian/memoryos/**
  - guardian/core/db.py
  # the runtime the gates are exercised under
  - docker-compose.yml
  - docker-compose.private-preview.yml
  - config/supported_profiles/v1-local-core-web-mcp.yaml
  - guardian/db/models.py
evidence:
  - docs/architecture/proofs/runtime/2026-11-05-stock-compose-migration-source-proof.md
  - docs/architecture/proofs/supported-compose/2026-11-05-supported-compose-stock-844b35599ed6.md
  - docs/architecture/proofs/2026-10-09-synthetic-account-import-recall-qualification.md
  - docs/architecture/proofs/2026-09-23-natural-account-import-recall-proof-r4.md
```

## Purpose

Determine whether the eight behaviours the release definition names are **green on one evaluated
tip**. This rubric exists because bounded evidence and runtime qualification are different
things: mainline has bounded evidence for queue/worker lifecycle, locks, cancellation, deadlines
and authorization, and that is not the same claim as those gates being green on a running stack.

The eight gates are:

```text
queue/worker · deadline · graceful-stop · lock · migration-deployment · browser · import-recall · scope-isolation
```

This rubric does not replace `supported-compose` or `supported-compose-stock`. Those qualify a
runtime's startup path; this one qualifies the eight behaviours. A PASS here does not widen
Beta support and does not lift the release gate.

## Rules of judgement

These rules apply to every check and are what make "UNPROVEN" a real verdict rather than a
formality.

1. **The observable surface is named before the run.** Every check below names the exact artefact
   the operator reads. A check with no named surface cannot be PASS.
2. **UNPROVEN is not PASS.** A gate that was not exercised, or was exercised without its
   observable surface being read, is **UNPROVEN**. Unproven boundaries are not silent passes.
3. **A gate is judged at one revision.** All eight checks run against the same frozen evaluated
   commit on the same runtime instance. A check carried over from another revision is UNPROVEN,
   not PASS.
4. **Absence of a defect is not evidence.** A gate is PASS only when the named surface shows the
   required state, not when nothing went wrong.
5. **One failure is one bounded repair.** A FAIL becomes a repair task scoped to that gate. It does
   not license re-scoping the rubric.

## Qualification identity

Every run of this rubric must record:

- the exact evaluated commit SHA;
- the branch and upstream state at evaluation;
- the runtime profile and the Compose files rendered, in order;
- the startup command exercised and the backend image reference it resolved;
- the live Alembic revision, read directly from PostgreSQL;
- for each of the eight gates: its verdict, the named surface, and the value observed;
- the browser and device used for the browser gate;
- the account identifiers used for the scope-isolation gate;
- the durable artefact receipts collected.

A run that cannot name its evaluated commit is not a qualification run. It is an observation.

## Blocking criteria

This rubric cannot receive PASS if any of the following occur:

- the evaluated commit cannot be identified, or the eight checks were not run at one revision;
- any gate is UNPROVEN;
- the live Alembic revision was read from a container exit code rather than from PostgreSQL;
- a queue accepted work that no worker ever claimed and the backlog was not observed;
- an attempt exceeded its terminal deadline without a recorded terminal state;
- a worker stopped without releasing or terminalising what it held;
- two actors were able to take the same run;
- the migration source and the image disagreed and the migrator did not refuse;
- a browser-observed projection disagreed with the durable state it claimed to render;
- an imported record was retrievable by an account that did not own it;
- the scope-isolation gate was judged without a second, distinct account.

## Required checks

### 1. Queue and worker lifecycle

**Governing behaviour.** A durable request is queued, a worker claims it, the worker's liveness is
observable, and the queue drains.

**Observable surface.**

- Redis list lengths for the queues in play (`codexify:queue:chat-embed`,
  `codexify:queue:coding-execution`, `codexify:queue:document-embed`,
  `codexify:queue:account-import`) read directly with `LLEN`.
- The worker heartbeat key `codexify:worker:chat:heartbeat` and its age.
- The durable attempt row for the submitted request in `chat_completion_attempts`.

**PASS requires.** A submitted request observed at a non-zero queue depth and later at zero; a
worker heartbeat observed fresh at the time of the read; a durable attempt row in a terminal
state for the same request.

**FAIL.** Work left in a queue with no worker claiming it while the worker reports healthy; or an
attempt row that never reached a terminal state.

**UNPROVEN.** Only `/health/chat` was read, with no direct queue and heartbeat observation.

### 2. Deadline

**Governing behaviour.** An accepted attempt carries a terminal deadline, and an attempt that
passes it is terminalised rather than left open.

**Observable surface.**

- `chat_completion_attempts.deadline_snapshot` (JSONB), including `terminal_deadline_at`.
- The attempt's terminal state and `turn_lock_token`.

**PASS requires.** An accepted attempt observed with a non-null `deadline_snapshot` and a
`terminal_deadline_at` in the future at acceptance; and, for the deadline path itself, an attempt
driven past its terminal deadline observed in a terminal state with the deadline recorded.

**FAIL.** An attempt accepted without a deadline snapshot; or an attempt past its
`terminal_deadline_at` still carrying a live turn lock.

**UNPROVEN.** A deadline was configured but no attempt was observed carrying it.

### 3. Graceful stop

**Governing behaviour.** A worker stopped on SIGTERM releases or terminalises what it holds; it
does not leave an orphaned claim, a held lock, or a half-written attempt.

**Observable surface.**

- The worker's shutdown handler (`backend/scripts/docker/run_worker_coding.py`, SIGTERM
  registration).
- `agent_runs` rows for the worker's held run, and the ownership/heartbeat columns on them.
- The Redis queue depth immediately before and after the stop.

**PASS requires.** A worker stopped on SIGTERM while holding a claim, observed afterwards with no
claim outstanding, the run's ownership either released or terminalised, and the queue depth
unchanged.

**FAIL.** A run left owned by a stopped worker with no terminal state; or work claimed and never
returned to the queue.

**UNPROVEN.** The worker was stopped while idle, so nothing was held.

### 4. Lock

**Governing behaviour.** Mutual exclusion over a run: exactly one actor takes it, and the loser is
refused deterministically.

**Observable surface.**

- `agent_runs` ownership columns, the claim identity, and the heartbeat.
- The claim path in `guardian/agents/store.py` (`claim_run_for_acceptance`, row locks taken with
  `with_for_update`).

**PASS requires.** Two concurrent claim attempts against the same run, observed with exactly one
holding the claim and the other refused, and the refusal recorded.

**FAIL.** Both actors observed holding the same run; or the refused attempt left a partial write.

**UNPROVEN.** A single claim was exercised without a concurrent competitor.

### 5. Migration deployment

**Governing behaviour.** The migrator applies the evaluated source's migration head to the live
database, and refuses to migrate when the image's migration source does not describe the served
checkout.

**Observable surface.**

- `alembic_version` read directly from PostgreSQL — row count and value — never from a container
  exit code.
- The migrator's coherence comparison against `/source-migrations`.
- The refusal case: a stale image, a same-head image with different revision content, and a
  same-head source with a different migration environment.

**PASS requires.** The live `alembic_version` equals the evaluated checkout's single head with
exactly one row; the coherence comparison reports the source as coherent; and each of the three
refusal cases fails closed **before** any migration is applied.

**FAIL.** The live revision is not the evaluated head; or a mismatch was detected and the migrator
proceeded anyway.

**UNPROVEN.** Only the successful path was exercised and no refusal case was run.

### 6. Browser

**Governing behaviour.** What the interface renders agrees with the durable state it claims to
render, and survives a reload.

**Observable surface.**

- A real browser, with its version, viewport and device pixel ratio recorded.
- The DOM's own text and attributes for the projected element, read directly rather than inferred
  from a screenshot.
- The durable rows the projection claims to render, read from the database.

**PASS requires.** The projected element read from the DOM matching the durable value; the
terminal state converging in the UI; and a reload preserving the projected state.

**FAIL.** The DOM disagrees with the durable state; or a reload loses the projected state.

**UNPROVEN.** The surface was observed by description or screenshot only, with no DOM read and no
durable comparison.

### 7. Import to recall

**Governing behaviour.** A record imported from an external export becomes retrievable through the
account's own recall path, under the account that owns it.

**Observable surface.** The imported record's canonical PostgreSQL row, the materialization
job's durable checkpoint, and the recall result that returns it.

**PASS requires.** An imported record materialised canonically and then returned by recall for
the owning account, with the durable materialisation row and the recall result observed together.

**FAIL.** The record materialised but is not retrievable; or it is retrievable by an account that
does not own it.

**UNPROVEN.** Only the materialisation stage was exercised, or only the retrieval stage, without
both observed for the same record.

**Standing evidence.** The synthetic import-to-recall qualification of 2026-10-09 recorded
canonical PostgreSQL materialisation as PASS and **natural recall as BLOCKED**, with VaultNode
qualification BLOCKED. This rubric does not inherit that verdict; it requires the import and the
recall to be observed together for one record.

### 8. Scope isolation

**Governing behaviour.** An account's data is visible to that account and not to another.

**Observable surface.**

- The same read issued under two distinct account identities, with the owning account's record
  visible and the other account's view of it absent.
- The retrieval path's account scoping, and the account-scoping rules of ADR-005 and ADR-071.

**PASS requires.** Two distinct accounts on the running stack; the owning account's record observed
for its owner and **not** observed for the other account, with both reads made against the same
record identifier.

**FAIL.** A record owned by one account is observable by another; or the isolation boundary is
judged from configuration rather than from two accounts' observations.

**UNPROVEN.** Only one account was used; or isolation was asserted from the profile's route
posture rather than observed.

## Freshness

This surface is commit-bound. A run's evidence becomes stale when meaningful changes touch the
eight gates' implementation — the Compose files, the supported profile manifest, the queue, the
workers, the deadline and lock paths, the models and migrations, the migration entrypoint, the
frontend projection, or the import path.

The registry computes this from repository history rather than by hand. See
`scripts/qualification/lib/freshness.py`.

## Evidence

Cite the detailed proof artifacts under `docs/architecture/proofs/`. The receipt links to the
exact proof rather than duplicating it. A proof artifact the registry cannot read does not
qualify this surface.

## Relationship to release authority

`docs/architecture/00-current-state.md` remains release authority. A PASS here qualifies the eight
gates for the tested revision and runtime profile. It does not by itself lift the release gate,
and nothing in this directory independently widens Beta or production support.
