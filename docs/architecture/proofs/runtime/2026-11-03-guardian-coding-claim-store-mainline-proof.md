# Guardian coding claim persistence — mainline reconciliation

Date: 2026-11-03. Disposition: **GO for independent reconciliation of this
persistence slice. Release: HOLD.** This is disposable PostgreSQL persistence
proof, not successful coding-worker execution or supported-runtime qualification.

## Revision custody and scope

| Source | Verified revision |
| --- | --- |
| Evaluated main | `00c3a4163cfce8e84b7c92009bb31209276df45a` |
| Freshly fetched actual `origin/main`, integration parent, and pristine baseline | `00c3a4163cfce8e84b7c92009bb31209276df45a` |
| Frozen published candidate | `94049db8d771daccb8eefc6cb9c9c256978b4a12` |
| Verified admission implementation, ancestor of the frozen candidate | `e7d3ccde69ba6d7313e666340d12d99a1775f162` |
| Remote dispatch branch observed during fetch | `802c3c3589f3a7b58c8b5c4c6cccd4492c66d082` |

`git ls-remote` and `git fetch origin main
integrate/guardian-coding-authorized-dispatch-20261031` established the remote
revisions. The frozen candidate is an ancestor of the observed remote dispatch
tip; the later remote tip was not used as implementation input. Main had not
advanced beyond the evaluated SHA.

No existing local/remote branch, registered worktree, or visible active Codex
executor owned the requested integration name. Git worktree creation reserved
`integrate/guardian-coding-claim-store-mainline-20261103` from `origin/main` at
`/private/tmp/codexify-claim-store-mainline-20261103`. The supplied checkout's
untracked probe files were preserved. The frozen dispatch worktree was read
only. Its local branch remained at `94049db8d771daccb8eefc6cb9c9c256978b4a12`;
the historical feature branch remained at
`7b4b0bab44bf2fd3894eb310d8c2ef48d406325f`.

Exactly these files belong to the change:

- `guardian/agents/store.py`
- `tests/contracts/test_guardian_coding_claim_store_contract.py`
- This receipt.

No push, PR, merge, deployment, schema edit, or migration revision was performed.

## Implementation and authority

Adapted the candidate's `claim_run_for_acceptance`,
`renew_coding_run_heartbeat`, and `claim_coding_run_terminal` into the current
mainline store. Added only `sqlalchemy.func`, the ten candidate acceptance,
heartbeat, and terminal outcome constants, the 64-character ownership bound,
`_valid_coding_claim_identity`, and an adapted `_coding_run_lineage_matches`.
The latter consolidates acceptance/terminal identity checks without the
candidate's contradictory-identity sentinel or feature-only imports.

- Acceptance requires a PostgreSQL session, an existing matching deployment
  and canonical run, canonical account/thread lineage, and agreement among
  persisted spec, execution binding, deployment thread, run account/thread,
  and claiming-task assertions. Contradictory or malformed persisted lineage
  is refused. A conditional `UPDATE` requires `queued` and null ownership;
  exactly one winner persists worker, claim, database-clock heartbeat, and
  `COALESCE(started_at, now())`.
- Acceptance and terminal decisions lock deployment then run in the same
  transaction to keep checked lineage stable. The database conditional update,
  ownership-pair constraints, and unique claim constraint are authoritative;
  no process-local ownership lock or parallel registry exists.
- Heartbeat is one conditional PostgreSQL update matching `running`, worker,
  and claim, using `now()`. It changes only heartbeat evidence.
- Terminal decisions re-read locked canonical state, including a caller's
  cached run, and validate every persisted identity assertion. Only the
  recorded running worker/claim may transition to `succeeded`, `failed`, or
  `canceled` using existing normalization aliases. Unknown/nonterminal targets
  are refused. Escalated runs refuse late completion. Other terminal runs
  return already-terminal only to their recorded owner, without mutation.
- The terminal method neither commits nor rolls back the supplied session.
  SQLAlchemy session synchronization keeps cached state consistent. The caller
  owns the result transaction and must abort on unavailable persistence or a
  failed result write, and produce results only after `terminal_accepted`.

Canonical account/thread absence is refused by the new operations. Historical
null worker/claim/heartbeat metadata remains readable through existing APIs;
an unowned queued row with valid lineage can be accepted, while an unowned
running/terminal row cannot be taken over. As in the candidate, absent optional
message/task/attempt assertions on older deployment specs are not manufactured;
every assertion that is present must agree, including binding aliases.

AgentRun remains execution-state authority; deployment remains authoritative
for its persisted lineage. Worker and claim IDs never become account
principals, credentials, retry grants, or liveness guarantees. There is no
adapter restart, enqueue, automatic recovery, or authority derived from a
heartbeat.

## Schema and PostgreSQL isolation

The current Alembic graph has exactly one head: `d91e4fa6702b`.
The existing ownership revision `e42c7d0b9135`, heartbeat revision
`d86f2a4b1c90`, and mergepoint `c8e42a91d307` are retained.
`guardian/db/models.py` and all migrations are unchanged from the parent.
The unchanged model SHA-256 is
`f2ee6c3a8a657daeb2ed3ef2b19219a6b16a4b4e018210871bebd04cc92cac73`.

Proof used existing `postgres:15`, reporting **PostgreSQL 15.19**, aarch64
Debian, with default **READ COMMITTED** isolation. The uniquely named container
`codexify-claim-store-proof-20261103` carried this task's ownership label,
published only `127.0.0.1:51493`, and used a 512 MB tmpfs data directory,
512 MB container memory limit, one CPU, 30 connections, and 32 MB shared buffers.
Only synthetic accounts/messages/results were used. No provider was invoked by
the new contract. No production or Private Preview database was accessed.

The new module creates a UUID-named `codexify_claim_store_*` database, applies
the actual repository Alembic chain to head, and drops it in `finally`.
The existing migration contracts similarly create/drop their own databases.
Missing PostgreSQL or its driver fails the new module; it never silently skips.
The non-PostgreSQL refusal test uses a dialect stub, not SQLite authority proof.

## Validation

Commands ran from the integration repository root using the existing host
virtualenv's Python 3.12.13 and pytest 8.4.2. Common environment:

```sh
export PATH=/Volumes/Dev_SSD/Codexify-main/.venv/bin:$PATH
export CODEXIFY_DISABLE_DOTENV=1 CODEXIFY_CONFIG_SOURCE=core
export CODEXIFY_EMBEDDINGS_BACKEND=mock
export TEST_DATABASE_URL=postgresql+psycopg://postgres@127.0.0.1:51493/postgres
```

### Focused persistence contract — PASS

```sh
python -m pytest -o addopts="" -v -rs \
  tests/contracts/test_guardian_coding_claim_store_contract.py
```

Final result: **69 passed, 0 failed, 0 errors, 0 skipped**, exit 0 (8.36s).
An earlier 63-case run also passed before adding concurrency/cache/refusal cases.
Coverage includes eight concurrent acceptance claimants with exactly one
durable winner; duplicate/unique-claim refusal; write-once start time; durable
ownership/initial heartbeat; database-clock writes despite an incorrect host
clock; owner/claim fencing; terminal/escalated refusal; account and all five
identity assertions; malformed/missing lineage and persistence; historical null
ownership; and refusal to replace pre-existing ownership on a queued row.

Two competing terminal transactions produce exactly one accepted decision and
one canonical result artifact. A separate session observes no premature commit.
A real result-artifact foreign-key violation after a flushed message and
artifact rolls back all result writes and the terminal transition; the owner
can claim again after rollback. Explicit caller rollback is also proven.
Cached-session escalation cannot be overwritten by late completion.

### Migration contracts — PASS

```sh
python -m pytest -o addopts="" -v -rs \
  tests/migration/test_guardian_coding_claim_schema_merge.py \
  tests/migration/test_read_state_main_head_merge.py
```

Result: **17 passed, 0 failed, 0 errors, 0 skipped**, exit 0 (21.41s).
This includes real PostgreSQL constraints, preserved migration identities and
ancestry, historical rows, and existing read-state/Saved Widget/consent state.

### Required mainline regressions and pristine comparison

```sh
python -m pytest -o addopts="" -v -rs \
  tests/agents/test_coding_agent_contracts.py \
  tests/agents/test_coding_worker.py \
  guardian/tests/workers/test_coding_worker.py \
  guardian/tests/workers/test_coding_worker_adapter_selection.py \
  guardian/tests/workers/test_coding_worker_regression_guard.py
```

The exact command exits **2**, with an import-file-mismatch collection error
between the two `test_coding_worker.py` modules. The same command reproduced
the same collection error on a clean detached worktree at evaluated main
`00c3a4163cfce8e84b7c92009bb31209276df45a`.

A supplemental execution of that exact file selection with
`--import-mode=importlib` collected all 95 tests:

| Tree | Passed | Failed | Errors | Skipped | Exit |
| --- | ---: | ---: | ---: | ---: | ---: |
| Integration | 81 | 14 | 0 | 0 | 1 |
| Pristine evaluated main | 81 | 14 | 0 | 0 | 1 |

The **full 95-node identity/status maps are equal**, including parametrized
identities containing spaces. Every failure reproduces at the same assertion
or exception location with the same observed cause below. Candidate-only
failures: **0**. These are inherited test/worker failures; the suites are not
reported as green. Underlying worker remediation is outside this task.

All identifiers below are under `guardian/tests/workers/`:

| Test identity | Reproduced observed cause on both trees |
| --- | --- |
| `test_coding_worker.py::test_one_worker_runs_two_pi_bindings_against_local_provider_mocks` | One `task.completed` event instead of two (line 1464). |
| `test_coding_worker.py::test_worker_records_campaign_attempt_ledger_and_work_order_markers` | Undefined test helper `_fetch_work_order`, `NameError` (line 1677). |
| `test_coding_worker.py::test_worktree_isolation_enabled_runs_adapter_and_validation_in_isolated_cwd` | Terminal status `failed` instead of `completed` (line 3114). |
| `test_coding_worker.py::test_worktree_isolation_preserves_relative_subdirectory_cwd` | Isolated cwd loses expected `packages/alpha` suffix (line 3181). |
| `test_coding_worker.py::test_isolated_success_captures_patch_manifest_and_terminal_metadata` | Terminal status `failed` instead of `completed` (line 3237). |
| `test_coding_worker.py::test_isolated_success_patch_capture_includes_untracked_file` | Terminal status `failed` instead of `completed` (line 3333). |
| `test_coding_worker.py::test_patch_artifact_root_can_stay_clean_with_gitignore_rule` | Checkout has untracked `.codexify/` (line 3397). |
| `test_coding_worker.py::test_dirty_original_checkout_does_not_block_isolated_execution` | `task.failed` instead of `task.completed` (line 3439). |
| `test_coding_worker.py::test_isolated_success_cleans_up_by_default_without_promoting_changes` | Terminal status `failed` instead of `completed` (line 3660). |
| `test_coding_worker.py::test_oversized_patch_writes_manifest_without_partial_patch` | Terminal status `failed` instead of `completed` (line 3919). |
| `test_coding_worker.py::test_keep_on_success_flag_preserves_isolated_worktree` | Terminal status `failed` instead of `completed` (line 4045). |
| `test_coding_worker.py::test_cleanup_failure_is_reported_without_overwriting_success` | Terminal status `failed` instead of `completed` (line 4107). |
| `test_coding_worker.py::test_dirty_preflight_fails_before_adapter_execution` | Adapter invoked when test expects zero calls (line 5222). |
| `test_coding_worker_regression_guard.py::test_no_name_error_in_guard_path` | Mock store's result method never called (line 86). |

Warnings were Alembic configuration deprecation, the existing overlapping
MemoryRecord ORM relationship, jsonschema deprecation, and Pydantic deprecation.
No warning was counted as a test pass or used to conceal a failure.

Local evidence logs remain under `/private/tmp/codexify-claim-store-` with
suffixes `focused-final.log`, `migrations.log`, `regressions.log`,
`regressions-importlib.log`, `baseline-exact.log`, and `baseline-importlib.log`.
No full backend run was launched. The SSD had approximately 9.7 GiB free;
task worktrees used the host temporary volume with over 30 GiB available.

## Compatibility, cleanup, ADR impact, and limits

- An AST comparison against the parent confirms every pre-existing module
  function and AgentStore member is unchanged, including existing API
  signatures, source-thread result delivery, and readback. Existing model and
  migration diffs are empty. `git diff --check` passes.
- The terminal transaction proof uses canonical message/artifact writes in the
  caller's session. Existing committing `store_coding_result` delivery helpers
  were intentionally not rewired. Future worker integration must arrange a
  shared result transaction; calling independently committing legacy helpers
  is not made atomic by merely adding this method.
- After all database tests, querying the task container found zero
  `codexify_*` databases. The container was removed; its tmpfs data was
  destroyed and no task-labelled container remains. The clean detached
  baseline worktree was removed. The integration worktree and local evidence
  logs remain for review. No shared image, volume, database, or checkout was
  deleted or pruned.
- ADR impact: aligned with accepted ADR-020, ADR-077, ADR-081, ADR-092, and
  ADR-094 and the Guardian Delegation Loop Contract. Main's ADR-022 is actually
  **Proposed**, despite the task's accepted-status description; it is context,
  not acceptance authority here. ADR-104 remains Proposed and is not used as
  implementation authority. No ADR or governing contract was changed.
- No worker, dispatch, route, provider, credential, approval, profile,
  executable-plan, retry, startup-recovery, or release behavior was integrated.
  All source identity/credential boundaries remain separate from executor
  metadata. Conditional decisions cannot reopen terminal runs or transfer
  ownership. Missing persistence does not authorize execution.
- Only this proof receipt changes documentation. Current-state and release
  claims remain untouched. The source-matched migrator work newly merged on
  main is not qualified by this task. The frozen candidate retains its own
  original evidence.
- Deferred: mainline worker use of these methods and shared result
  transactions; authorized dispatch integration/promotion; independent review;
  supported-profile/live execution qualification. There is no exactly-once,
  recovery, successful coding-worker, Preview, or release claim.

**Publication: local commit only; no push or PR. Release remains HOLD.**
