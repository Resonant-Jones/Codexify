# Accepted chat source custody prerequisite

**CX-RECALL-01A · 2026-11-27 · Isolated implementation receipt.** The accepted
architecture is on main at
`0a447d937a65e4d9c1fe9d0ac4c99e78f9e62879`. Guardian CI finished successfully
on that base before implementation, including its container migration contract.
The candidate branch is `codex/recall-01a-accepted-source-custody`. Its evaluated
runtime and test tree before adding this receipt is
`5f03c1340ae36d070ca2bccac66daa2ddb11aaab`. The branch is an isolated
prerequisite candidate. Release remains **HOLD**.

## Identity boundary

The existing authenticated ordinary-chat route selects the user message and
hands it to enqueue with its resolved account scope. Enqueue captures that
message ID before queue preparation. Attempt creation rechecks and locks the
canonical thread and account, then checks the exact source row under a
PostgreSQL share lock before inserting the attempt. An eligible source is
owned by that account, belongs to that thread, is an ordinary user-authored
chat row, and passes the existing message-origin classification. The source
check selects metadata and excludes the message body. Missing, imported,
ambiguous, and other ineligible sources leave source custody NULL. A legacy
scope without a canonical account and a hosted-room invocation acquire no new
custody. Database failure retains the existing pre-publication failure path.

Migration `e4b7c2d9a601` extends `a64c358e2241` and is the single Alembic
head in the candidate. The nullable bigint mirrors the canonical message ID.
A database check requires original account custody for a populated source ID.
The PostgreSQL trigger refuses reassignment, erasure, and NULL-to-value
updates. The source snapshot has no foreign key, and existing message, thread,
and account deletion behavior is preserved. A deleted source makes subsequent
resolution refuse the original ID. Upgrade does not backfill any attempt.

`resolve_accepted_chat_work_identity()` re-reads accepted identity without a
tool checkpoint. It verifies the request, task, thread, turn and accepting
account, exact source, current account eligibility, thread ownership, current
Project ownership and absence of conflict, durable acceptance, nonterminal
status, deadline, and cancellation. Queue values only check consistency.
During the enqueue acknowledgement race it refuses execution with the existing
typed pending disposition. A fresh retry repeats these checks. The returned
identity contains IDs and current placement. Existing post-selection
`resolve_accepted_chat_account()` continues to require its original tool
command, argument hash and checkpoint checks. Existing consumers can still
resolve post-selection custody for eligible attempts with NULL source custody.

The change implements an existing requirement under
[ADR-005](../adr/005-runtime-mode-and-account-boundary-invariants.md),
[ADR-081](../adr/081-project-ownership-authority.md),
[ADR-084](../adr/084-unified-account-owned-memory-store.md), and
[ADR-112](../adr/112-trusted-worker-account-bound-dispatch.md).
[ADR-016](../adr/016-continuity-governance-surface-contract.md) independently
governs durable source provenance.

## Executed proof

- **Focused suites:** 285 passed, zero failures, errors or skips on Python
  3.11.15. The authenticated route test passes a distinct external subject
  and persists its exact selected canonical message before enqueue. Tests
  cover owner, thread, role and kind mismatches, hosted and legacy exclusions,
  and persistence failure without queue publication. Resolver tests exercise
  A → B → A with one resolver and no checkpoints, substituted IDs from the
  same thread, another thread, and another account, and fresh reads after
  pending acknowledgement, source deletion, revocation, Project conflict,
  changed thread ownership, cancellation, expiry, terminal state or store
  failure. The existing post-selection, enqueue, tool-loop, exposure and
  deadline regressions ran in the same suite.
- **PostgreSQL:** PostgreSQL 17.6 in a disposable, Unix-socket-only cluster.
  The real migration test passed without skipping. It replayed the actual
  Alembic ancestry to `a64c358e2241`, inserted a legacy attempt, upgraded to
  `e4b7c2d9a601`, exercised the ORM and independent SQL transactions, then
  downgraded and re-upgraded. The old row retained NULL source custody.
  Attempts accepted a valid binding and refused ownerless inserts, source
  rewrites or erasure, NULL backfills, and original account reassignment.
  Acceptance, checkpoint and terminal updates succeeded. Source deletion
  left the snapshot intact and caused resolution to refuse. Thread and
  account deletion cascaded normally. Downgrade preserved unrelated attempt
  data and re-upgrade granted no history retroactively.
- **Architecture and evidence packets:** 889 passed and one failed on the
  candidate, with zero skips. The same suite passed all 890 on the base.
  `test_current_phase_publishes_the_resolved_migration_head_and_count` compares
  this branch's migration graph with the source-head claim in
  `00-current-state.md`. The unchanged mainline claim names `a64c358e2241`
  and 143 revisions. The candidate graph has `e4b7c2d9a601` and 144 revisions.
  Changing that file requires an explicit scope amendment. The test was
  neither changed nor bypassed.
- **Static checks:** `alembic heads`, Git diff checks, tracked paths and
  generated-artifact verification passed. Ruff found zero new violations
  compared with the base. The affected files retain 398 pre-existing Ruff
  findings, compared with 399 on the base. The initial commit hooks passed
  mypy, Bandit and tracked-path validation. Black, isort, and pyupgrade
  rewrote existing source outside the changed sections. Those rewrites were
  discarded and the local candidate commit excludes those three hooks to
  preserve the scoped, evaluated tree.
- **Environment:** All 723 Git LFS JSON files were hydrated. An early
  environment check lacked the project dependencies, and the initial
  disposable database used SQL_ASCII. Installing the project dependencies
  and using a fresh UTF-8 database resolved both issues. The final focused
  suite reported 14 warnings from existing pytest-asyncio, Starlette/AnyIO,
  SQLAlchemy relationship configuration, jsonschema, Pydantic and Alembic
  configuration behavior. The architecture suite reported one
  pytest-asyncio warning.

## Deferred proof

The source ID does not bind the accepted content revision. The ordinary route
has a message deletion path, and canonical enrichment can change metadata
after insertion. No ordinary body-edit path was identified in the inspected
route and repository writers. Before Stage 2 derives intent, establish or
prove revision custody for the intent-bearing inputs at acceptance and
revalidate it when consuming the source. A deleted or changed source cannot
be replaced by a nearby message. Current Project placement does not carry
original scope, exclusions, or policy revisions across a move.

Durable native-origin custody, complete accepted-worker dispatch and retry
qualification, retrieval coverage, Recall grants, model exposure, and memory
mutation remain separate work. Historical reads stay disabled in ordinary
chat. No serving database was contacted. This receipt proves only the
isolated prerequisite and does not establish Stage 1 or Private Preview
qualification.

## Integration reconciliation · 2026-11-27

PR [#1106](https://github.com/Resonant-Jones/Codexify/pull/1106) originally
published `700c9b318572088ac080cddeec60705bc057465d`. The branch integrates
verified mainline `75e65582b4b3b435322747aaf003ea72eaeafde3` through the
two-parent merge `1c197d684f1c98fafb6b34005d6cfd4c0f3672cd`.
The reconciled runtime and tests were evaluated at
`16fe99495dbdd492622366e3d8e14993897b559c`. The isolated evaluations
and their earlier validation failures above retain their original scope.

- **Authored-turn authority.** Attempt creation preserves mainline thread
  locking and rechecks the selected authored turn inside the acceptance
  transaction. The enqueue handoff takes the custody ID from that same
  selection. Disagreement produces the existing stale-turn refusal. A
  stale submission returns HTTP 409 before attempt creation or queue
  publication. A receipt-less legacy turn can complete with NULL source
  custody. Once accepted, newer messages cannot replace the bound source.
- **Ordinary embedding.** Authored-turn admission and source custody share
  the existing ordinary-only interpretation of `embedding_status`. The
  historical classifier still receives full metadata. An origin assertion
  remains required, and actual import evidence, malformed assertions and
  conflicting or ambiguous origins remain ineligible. The route proof used
  ordinary message creation, real PostgreSQL writes through the embedding
  worker metadata seam, and real source resolution before and after
  enrichment. It used canonical numeric IDs with psycopg 3. An additional
  disposable run verified the same write seam with string IDs through
  psycopg2. The initial psycopg 3 string-ID attempt failed on PostgreSQL's
  bigint/VARCHAR comparison. That worker address-binding path is outside
  the custody correction.
- **Executed local validation.** Python 3.11.15 ran 451 focused tests
  (15 warnings), 890 architecture and evidence-packet tests (one warning),
  and 42 qualification tests (one warning), with zero failures, errors or
  skips in the final runs. The focused suite includes exact PostgreSQL
  source readback, concurrent and duplicate request checks, stale-turn
  rejection, three embedding-state transitions, sequential A → B → A
  resolution, substituted-source denial, lifecycle denial and the existing
  post-selection checkpoint checks.
- **Disposable PostgreSQL 17.6.** The dedicated migration test executed
  upgrade, downgrade and re-upgrade, legacy NULL preservation, immutable
  source and account custody, normal checkpoint and terminal writes, and
  denial after source deletion. Alembic resolved 144 revisions and the
  single head `e4b7c2d9a601` with parent `a64c358e2241`. The dated
  `ab71d5ce9604` Preview checkpoint is six revisions behind in the source
  graph. The serving database was not contacted.
- **Qualification and formatting.** The previously published head's
  Guardian CI stopped at `test_committed_registry_is_current` and skipped
  the container migration job. The repository generator refreshed the
  committed projection after the runtime commit. The generated diff changes
  only the two stale path counts, and local qualification, generated-artifact,
  tracked-path and diff checks passed. Against the integrated mainline,
  Black 26.5.1, isort 5.12.0 and pyupgrade 3.4.0 showed only pre-existing
  whole-file differences. Ruff found zero new diagnostics. Local merge and
  runtime commits bypassed only Black and isort after checking the baseline
  differences. Hook configuration remains intact.
- **Boundary.** This proof establishes the reconciled Stage 1A prerequisite
  in disposable PostgreSQL. It grants no historical-read authority and
  activates no resolver consumer. Accepted content-revision custody and
  durable native-origin custody remain separate. The corrected branch still
  requires authorized publication, fresh CI including the container migration
  job, review on the corrected head, and separate human merge approval.
  Release remains **HOLD**.
