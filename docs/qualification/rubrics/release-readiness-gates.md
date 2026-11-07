# Release Readiness Gates Qualification Rubric

## Qualification ID

`release-readiness-gates`

## Version

`3`

Version 3 corrects three defects found while building the evidence harness against this rubric.
**No required check was added, removed, or re-scoped.**

Version 2 applied the independent review of version 1: it replaced an inert surface path with the
files that exist, closed the gate-7 implementation blind spot, narrowed the frontend surface to the
projection the browser gate renders, and named the schema constraints that are stronger
observables than the prose checks they replace.

Version 3 corrects three things version 2 got wrong:

- **Gate 1 named the wrong queue.** It listed `chat-embed`, `coding-execution`,
  `document-embed` and `account-import`. A chat completion actually lands on
  `codexify:queue:chat` (`guardian/core/chat_completion_service.py:248`), and
  without that queue the gate's own PASS condition — a submitted request
  observed at a non-zero depth — is not exercisable.
- **Gate 2 implied a configurable deadline.** The budgets are hardcoded constants with no
  environment knob, so the gate must be driven by an attempt that has actually lived past the
  budget rather than by shortening one.
- **Gate 3's PASS bar was unsatisfiable.** It required both ownership columns to be NULL after a
  stop, and **no code path NULLs them**: the claim writes both columns and the terminal paths
  write only `status`, `ended_at` and `error`. The claim is durable correlation material for
  fencing, so a populated ownership pair after a stop is expected rather than a failure. The
  release signal is the run's terminal status.

## Qualification metadata

```yaml qualification-metadata
qualification_id: release-readiness-gates
version: 3
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
  - frontend/src/features/chat/GuardianChat.tsx
  - frontend/src/features/chat/ChatView.tsx
  - frontend/src/features/chat/components/**
  - frontend/src/components/chat/**
  # 7. import to recall
  - guardian/core/account_history_recall.py
  - guardian/core/message_origin_classification.py
  - guardian/core/repository_import.py
  - guardian/services/openai_account_import.py
  - guardian/services/imported_history_evidence.py
  - guardian/queue/account_import_queue.py
  - guardian/workers/account_import_worker.py
  # 8. scope isolation
  - guardian/memoryos/**
  - guardian/core/db.py
  - guardian/core/message_origin_classification.py
  # the runtime the gates are exercised under
  - docker-compose.yml
  - docker-compose.private-preview.yml
  - config/supported_profiles/v1-local-core-web-mcp.yaml
  - guardian/db/models.py
evidence:
  # The operator procedure that executes this rubric's checks. It is listed
  # here so the registry pins the pairing: the rubric states the criteria, the
  # runbook states how they are exercised, and a future edit to either one
  # cannot quietly change what the other claims.
  - docs/Ops/private-preview-human-qualification-sessions.md
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
6. **A schema constraint is the strongest observable available.** Where the database already
   enforces the property, the constraint is the observation and the prose check explains what the
   constraint guarantees.

## Qualification identity

Every run of this rubric must record:

- the exact evaluated commit SHA;
- the branch and upstream state at evaluation;
- the runtime profile and the Compose files rendered, in order;
- the startup command exercised and the backend image reference it resolved;
- the live Alembic revision, read directly from PostgreSQL;
- for each of the eight gates: its verdict, the named surface, and the value observed;
- the browser and device used for the browser gate;
- the account identifiers used for the scope-isolation gate, and whether each is a human tester or
  an agent-created account;
- for the import-to-recall gate: whether the import was **natural** or synthetic, and the evidence
  for that classification;
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
- the scope-isolation gate was judged without a second, distinct account;
- the import-to-recall gate was judged on a synthetic import rather than a natural one.

## Required checks

### 1. Queue and worker lifecycle

**Governing behaviour.** A durable request is queued, a worker claims it, the worker's liveness is
observable, and the queue drains.

**Observable surface.**

- Redis list lengths for the queues in play, read directly with `LLEN`. **`codexify:queue:chat`
  is the queue a chat completion actually lands on** (`guardian/core/chat_completion_service.py:248`)
  and is the one this gate's PASS condition depends on; `codexify:queue:chat-embed`,
  `codexify:queue:coding-execution`, `codexify:queue:document-embed` and
  `codexify:queue:account-import` are the other queues in play.
- The worker heartbeat key and its age.
- The durable attempt row for the submitted request in `chat_completion_attempts`.

**PASS requires.** A submitted request observed at a non-zero queue depth and later at zero; a
worker heartbeat observed fresh at the time of the read; a durable attempt row in a terminal
state for the same request.

**Liveness coverage limit.** The codebase defines exactly two worker heartbeat keys —
`codexify:worker:chat:heartbeat` and `codexify:worker:voice:heartbeat`. **Three of the four
queues named above have no heartbeat key at all.** A PASS on this gate therefore asserts liveness
for the chat queue only. The document-embed, account-import and coding-execution queues can be
judged on depth and durable outcome, but **not** on worker liveness, and a run must not report
liveness for them.

**FAIL.** Work left in a queue with no worker claiming it while the worker reports healthy; or an
attempt row that never reached a terminal state.

**UNPROVEN.** Only `/health/chat` was read, with no direct queue and heartbeat observation.

### 2. Deadline

**Governing behaviour.** An accepted attempt carries a terminal deadline, and an attempt that
passes it is terminalised rather than left open.

**Primary observable — the database enforces the pairing.**
`chat_completion_attempts` carries a CHECK constraint requiring
`(deadline_snapshot IS NULL AND turn_lock_token IS NULL) OR (deadline_snapshot IS NOT NULL AND
turn_lock_token IS NOT NULL AND length(trim(turn_lock_token)) > 0)`, and requiring
`(deadline_snapshot->>'terminal_deadline_at')::timestamptz` to be non-null wherever a snapshot
exists. **A live attempt with a NULL `deadline_snapshot` is a writer bug, not a missing row.**

**PASS requires.**

1. An accepted attempt observed carrying a non-null `deadline_snapshot` with a
   `terminal_deadline_at` in the future at acceptance, and a non-null `turn_lock_token`.
2. **An attempt observed past its own `terminal_deadline_at` and in a terminal state**, with the
   deadline recorded. A snapshot alone proves the shape; only the second observation proves the
   deadline was *enforced*.

**The budget is not configurable.** The budgets are module constants with no environment knob:
`ACCEPTED_CHAT_TASK_WORK_BUDGET_SECONDS = 720`,
`ACCEPTED_CHAT_TASK_TERMINAL_BUDGET_SECONDS = 60`,
`ACCEPTED_CHAT_TASK_TOTAL_BUDGET_SECONDS = 780`, and a turn-lock lease of 840s. Neither deadline
module reads the environment. The second PASS observation therefore has to come from an attempt that
has actually lived past the budget — a run must not shorten the deadline by configuration and must
not report PASS without one.

**FAIL.** An accepted attempt without a deadline snapshot; or an attempt past its
`terminal_deadline_at` still carrying a live turn lock; or an attempt whose snapshot has no
non-null `terminal_deadline_at`.

**UNPROVEN.** A deadline was configured but no attempt was observed carrying it; or a snapshot was
observed but no attempt was driven past its deadline.

### 3. Graceful stop

**Governing behaviour.** A worker stopped on SIGTERM releases or terminalises what it holds; it
does not leave an orphaned claim, a held lock, or a half-written attempt.

**Observable surface.**

- The worker's shutdown handler: `backend/scripts/docker/run_worker_coding.py` registers SIGTERM
  and SIGINT.
- `agent_runs.status`, constrained to
  `('queued','running','escalated','canceled','failed','succeeded')`.
- The ownership pair `coding_worker_instance_id` / `coding_worker_claim_id`, which a CHECK
  constraint requires to be both NULL or both NOT NULL.
- The Redis queue depth immediately before and after the stop.

**PASS requires.** A worker stopped on SIGTERM **while holding a claim**, observed afterwards with
`agent_runs.status` in the store's own terminal set `{succeeded, failed, escalated, canceled}` —
reached either by the worker's own terminalisation or by the recovery path that escalates a stale
run — and the queue depth unchanged.

**The ownership pair is expected to persist, and a cleared pair is not achievable.** The claim is
durable correlation material for fencing. **No code path NULLs the ownership columns**: the claim
writes both columns (`guardian/agents/store.py`), and the terminal paths write only `status`,
`ended_at` and `error`. A run carrying its ownership pair after a stop is therefore the expected
shape, not a defect, and it is not a FAIL.

**A persisting heartbeat is not a failure either.** `coding_worker_last_heartbeat_at` is tied by its
own constraint to the presence of the ownership pair, **not** to liveness, and the schema states
plainly that a persisted owner "is not proof that the worker is still alive -- it records that
this instance took the claim, not that it still holds it". A reader seeing a stale
`coding_worker_last_heartbeat_at` on a terminalised run must not call that a FAIL.

**FAIL.** The run is still non-terminal and still claimed by the stopped worker **after the
recovery path has run** — a stranded run, not a slow one; or work claimed and never returned to
the queue.

**UNPROVEN.** The worker was stopped while idle, so nothing was held.

### 4. Lock

**Governing behaviour.** Mutual exclusion over a run: exactly one actor takes it, and the loser is
refused deterministically.

**Primary observable — the database forbids the double-claim.**
`uq_agent_runs_coding_worker_claim_id` is UNIQUE on `coding_worker_claim_id`, and
`claim_run_for_acceptance` takes row locks with `with_for_update()`. The schema therefore
already prevents two rows holding the same claim id.

**PASS requires.** Two concurrent claim attempts against the same run, observed with exactly one
holding the claim and the other refused, and the refusal recorded.

**What the FAIL clause means.** "Both actors observed holding the same run" is only reachable if
the unique constraint is **absent**, not if the refusal path has a bug. A run that observes the
constraint missing is a schema defect and must say so.

**FAIL.** The unique constraint is absent; or both actors were observed holding the same run; or
the refused attempt left a partial write.

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

**Session requirement.** The browser session must be an **authenticated account session**. An
unauthenticated surface is not evidence for this gate, and it is not evidence for the
scope-isolation gate either — that is gate 8's requirement, and it is a different check.

**FAIL.** The DOM disagrees with the durable state; or a reload loses the projected state.

**UNPROVEN.** The surface was observed by description or screenshot only, with no DOM read and no
durable comparison.

### 7. Import to recall

**Governing behaviour.** A record imported through the product's **natural** import path becomes
retrievable through the account's own recall path, under the account that owns it.

**Observable surface.** The imported record's canonical PostgreSQL row, the materialisation job's
durable checkpoint, the reader-side exclusion that decides the record's retrievability, and the
recall result that returns it.

**PASS requires.**

1. An import performed through the **natural** import path — a real export produced by the
   provider being imported, not a synthetic fixture — with the classification recorded and its
   evidence cited.
2. That record materialised canonically, with the durable materialisation row observed.
3. The same record returned by recall for the owning account, with the recall result observed.

**The 2026-10-09 synthetic proof cannot satisfy this gate.** That proof recorded canonical
PostgreSQL materialisation as PASS and **natural recall as BLOCKED**, with VaultNode
qualification BLOCKED. A run that imports through a synthetic fixture and recalls that fixture
would be green while the product's natural import path remained exactly as broken as the standing
proof found it. The gate therefore requires the natural path, and the synthetic proof is cited as
standing evidence of what remains open — not as evidence this gate passed.

**FAIL.** The natural import materialised but is not retrievable; or it is retrievable by an
account that does not own it; or the import was synthetic and recorded as such.

**UNPROVEN.** Only the materialisation stage was exercised, or only the retrieval stage, without
both observed for the same record; or the import's natural/synthetic classification is unevidenced.

### 8. Scope isolation

**Governing behaviour.** An account's data is visible to that account and not to another.

**Observable surface.**

- The same read issued under two distinct account identities, with the owning account's record
  visible and the other account's view of it absent.
- The retrieval path's account scoping, and the account-scoping rules of ADR-005 and ADR-071.

**PASS requires.** Two distinct accounts on the running stack; the owning account's record observed
for its owner and **not** observed for the other account, with both reads made against the same
record identifier.

**This gate does not satisfy the human qualification.** The accounts used here may be
agent-created. The `onboarding-and-people` rubric requires **2 distinct non-developer human
tester accounts**, each on its own authenticated session, at least one completing the critical path
unguided. A PASS on this gate contributes **nothing** to that requirement, and
`onboarding-and-people` remains HOLD on absent evidence regardless of this gate's verdict.

**FAIL.** A record owned by one account is observable by another; or the isolation boundary is
judged from configuration rather than from two accounts' observations.

**UNPROVEN.** Only one account was used; or isolation was asserted from the profile's route
posture rather than observed.

## Freshness

This surface is commit-bound. A run's evidence becomes stale when meaningful changes touch the
eight gates' implementation — the queue and worker modules, the deadline, lock and ownership paths,
the models and migrations, the migration entrypoint, the chat projection, and the import and
recall paths.

The surface is deliberately narrow: it lists the files that decide each gate's observable, rather
than whole trees. A tree-wide surface would make the freshness field a measure of churn instead
of of whether the evidence still describes the gates — the reason `supported-compose` sits
permanently stale. **The test for narrowing is not "how few paths can be listed" but "does every
one of the eight gates' implementation files appear"**; a gate whose implementation is outside the
surface can move while this rubric still projects `current`.

The registry computes freshness from repository history rather than by hand. See
`scripts/qualification/lib/freshness.py`.

## Evidence

Cite the detailed proof artifacts under `docs/architecture/proofs/`. The receipt links to the
exact proof rather than duplicating it. A proof artifact the registry cannot read does not
qualify this surface.

## Relationship to release authority

`docs/architecture/00-current-state.md` remains release authority. A PASS here qualifies the eight
gates for the tested revision and runtime profile. It does not by itself lift the release gate,
and nothing in this directory independently widens Beta or production support.
