# Direct-message read state integrated onto the reconciled mainline

Date: 2026-10-27

Evidence class: local Git, code, and test evidence for one non-rewriting integration branch. No deployment, no push, no promotion into `main`, and no live-account or Preview qualification.

## Purpose

The reviewed recipient-local read-state series exists as ten commits ending at `1115b9263`. An earlier non-rewriting integration of that series exists at `429b8b032` (parents `fd7786400` and `1115b9263`); it is preserved as evidence only and is **not** an ancestor of this result. Local `main` and `origin/main` subsequently diverged and an interactive rebase reconciled them, so merging the earlier integration could reintroduce already-replayed history.

This record covers a single new integration that merges the **original reviewed series tip** onto the **reconciled post-rebase mainline**, preserving all ten reviewed commit identities and all current upstream architecture and runtime behavior.

## Evaluated revisions

| Role | Revision |
| --- | --- |
| Reconciled mainline (integration base) | `bf9016369127b801db13b5e85bf82203c850ba4c` |
| Reconciled mainline, first parent | `7153b69e9a9d9be58e54a4551856251e88a26a6a` |
| Reconciled mainline, second parent (`origin/main`) | `8f764549df8085eb80e72ed34a479d63d2f27f3a` |
| Read-state series tip (merged) | `1115b92632cfd13578a433216d23881d0290f3d5` |
| Series base (`merge-base`) | `fb4c74bb8ef474bf8a19e2873e02b4dacd02de5f` |
| Integration branch | `integrate/read-state-onto-reconciled-main-20261027` |
| Integration merge commit | recorded in the receipt-completion commit that follows this merge (a commit cannot embed its own hash) |
| Integration merge commit tree | recorded in the receipt-completion commit that follows this merge |
| Earlier integration (evidence only, not an ancestor) | `429b8b032` |

The merge commit that carries this record is the second parent of the branch tip; the branch tip is this merge plus a documentation-only commit that fills in the merge SHA and tree hash recorded above.

### Reconciled mainline provenance

`origin/main` advanced during this task, twice, in fast-forward steps:

- `a0d304ccb` — the tip fetched at the prerequisite gate. Reconciled into local `main` as `7153b69e9a` (conflict-free merge of `fb0b4e47a` and `a0d304ccb`).
- `8f764549d` — six further upstream commits (three merges, three test commits) that landed while the integration was being validated. Reconciled into local `main` as `bf9016369` (conflict-free merge of `7153b69e9a` and `8f764549d`), and the integration branch was re-based onto it.

The upstream delta `a0d304ccb..8f764549d` touches only `tests/core/test_completion_terminal_integrity.py`, `tests/core/test_whooshd_context_bundle_system_identity_delivery.py`, and `tests/evidence_packets/test_guardian_evidence_bounded_read.py`. No upstream file in the authorized integration set changed, so the conflict set and the conflict resolutions are identical on both reconciled bases; the two base revisions of `docs/architecture/00-current-state.md` and `docs/architecture/adr/adr-index.md` are byte-identical.

After reconciliation, `git merge-base --is-ancestor origin/main bf9016369` succeeds: the stored `origin/main` is fully contained in the local reconciled mainline. Nothing was pushed.

## Merge structure

The integration is a single normal `--no-ff` merge of `1115b9263` into `bf9016369`. No `git am`, no cherry-pick, and no rebase of the ten reviewed commits was used. The ten original commit identities are preserved as ancestors of the series tip and therefore of the merge result.

| # | Reviewed commit | Subject |
| --- | --- | --- |
| 1 | `2d91be408607e4a0dadcf3ee5351624e5acd9a5b` | docs: record private preview messaging proof |
| 2 | `2333a54899ef30f51aba7fb86546730e9e8dc5fe` | feat: persist direct message read state |
| 3 | `ce8a5fdbde164e2e5ca7e4a449df8c324610f9ba` | fix: make direct message read state explicit |
| 4 | `c90a9205bcb600a791ddd937fb3b3bee23011a45` | fix: advance direct message read state only to the read watermark |
| 5 | `e67014064c6f89864436dd4fd2806df2c2859b73` | fix: refresh direct message transcript on reopen |
| 6 | `c7d95e7b884d96a51ddebad4e981d31012e22a9d` | fix: keep a failed direct message read retryable |
| 7 | `d3044439c78d9e5f458e98c5329228258ad2312b` | fix: serialize concurrent direct message read cursor advances |
| 8 | `e2fc3f3045978c95b176d566ccbdd8b392d662a2` | feat: share the caller-local read projection across People surfaces |
| 9 | `86d569d046548babf8c1224512bd02f71f992a28` | docs: distinguish implemented read state from deployed read state |
| 10 | `1115b92632cfd13578a433216d23881d0290f3d5` | fix(people): synchronize inbox unread badges with shared read state |

`git merge-base main 1115b9263` resolves to `fb4c74bb8`, the exact series base, so the merge introduces no obsolete pre-rebase local-main history. `git merge-base --is-ancestor 429b8b032 HEAD` fails: the earlier integration is absent from this branch.

## Conflicts and resolutions

Two files conflicted. Both are documentation. Every conflict was inspected before resolution; no file was resolved with a blanket ours/theirs choice, and no conflict touched an authority, persistence, or schema implementation file.

### `docs/architecture/adr/adr-index.md`

Resolution: additive union. Both ADR-103 (read state, Accepted 2026-10-26, from the series) and ADR-104 (upstream, Proposed) are retained, in numeric order. The upstream ADR-104 entry text is carried verbatim; no upstream ADR entry was dropped or renumbered.

### `docs/architecture/00-current-state.md`

Resolution: a union that keeps mainline's newer operational truth while preserving the four distinctions the read-state series requires.

Retained from mainline: the saved-widget storage foundation, generated-UI containment, the UMS ORM restoration, the account-boundary and `account_session` JWT boundary, and the bounded private-preview restart/schema/health evidence. The reconciliation line now records that `origin/main` is reconciled through `8f764549d` and fully contained in local `main`.

Retained from the series: the same-node messaging live proof at serving commit `57184dfbe` with its proof-document reference; the read-state bullet, rewritten to state that read state is integrated on branch `integrate/read-state-onto-reconciled-main-20261027` on reconciled main `bf9016369`, is test-evidenced, and is **not** merged to `main`, **not** deployed, and **not** live-qualified; the "Current supported reality" Private Preview line, which now states that read state is implemented and test-evidenced on the integration branch and that no live read-state evidence exists; and the "Not yet true" branch-only bullet, reworded from "unmerged local branch" to "read-state integration branch".

Dropped as superseded by newer mainline truth: the ADR-102 "architecture only" statement, the saved-widget contract-review bullet, the share-route admission bullet, the personal-fact pipeline baseline bullet, and a duplicate "no fresh integrated-tip qualification" statement. Two series bullets were retained only after being verified true in the merged tree: the personal-fact candidate-listing fix and the `@`-sigil People-search fix (`18eb0c1d2` is an ancestor of the reconciled mainline).

Blockers and priorities: the series' messaging/read-state blocker is kept (reworded) **alongside** mainline's saved-widget blocker, and priorities item 5 combines both. No blocker, priority, or release statement was broadened.

## Migration graph reconciliation

The merged tree initially carried three Alembic heads: `a6b9d2e4f701`, `b3c8d1e5f7a2`, and `c59e4d1a28f0`. The reconciled mainline baseline has two: `a6b9d2e4f701` and `c59e4d1a28f0`. The repository's own convention in `tests/migration/test_alembic_revision_uniqueness.py` requires an additive migration to extend an existing branch rather than introduce another independent head.

Resolution: `guardian/db/migrations/versions/b3c8d1e5f7a2_add_direct_message_read_cursors.py` now declares `down_revision = "a6b9d2e4f701"` instead of the authored `f0d7c4b2a198`, with the reason recorded in the revision docstring. Only the parent pointer of this new, additive revision changes. No existing revision was rewritten, and no existing migration ancestry was altered. The schema effect of the migration is unchanged.

Resulting lineage and heads:

```
f0d7c4b2a198 -> a6b9d2e4f701 -> b3c8d1e5f7a2 (head)
a6b9d2e4f701 (head on the reconciled mainline baseline)
c59e4d1a28f0 (head on both the baseline and the integrated tree)
```

| Tree | Alembic heads | Count |
| --- | --- | --- |
| Reconciled mainline baseline `bf9016369` | `a6b9d2e4f701`, `c59e4d1a28f0` | 2 |
| Integrated tree `6059a9caa` | `b3c8d1e5f7a2`, `c59e4d1a28f0` | 2 |

The integrated tree replaces the `a6b9d2e4f701` head with its own head rather than adding a third, so the head count of the reconciled mainline is preserved.

**Known limitation, reported not repaired.** The reconciled mainline itself carries an inherited two-head Alembic state (`a6b9d2e4f701` and `c59e4d1a28f0`). Unifying those two heads into one requires a new merge revision file, which is outside the authorized integration file set. This is therefore reported rather than created. The repository's canonical-head constant `2e865c4a9b10` is likewise not reconciled by this integration.

## Validation

All commands were run from the isolated integration worktree `.scratch/integrate-reconciled` (merged tree) and `.scratch/baseline-main` (reconciled mainline baseline), each against its own disposable PostgreSQL instance.

### Environment

- Python 3.12.13, pytest 8.4.2, `pytest-asyncio` 1.2.0 in strict mode.
- PostgreSQL **16.2, a locally patched build** (`PG_FILE_INTERLOCK`, named-POSIX semaphores, `dynamic_shared_memory_type=mmap`, trust authentication), built under `.scratch/pg162install/bin`. This is **not** the stock container image and must not be presented as stock-image proof.
- Merged tree: `127.0.0.1:55432`. Baseline: `127.0.0.1:55433`. `pgcrypto` installed for the Guardian event-log migrations.
- Frontend: Vitest via `frontend/node_modules/.bin/vitest` run from `frontend/src` with `--config vitest.config.ts`; `pnpm --dir src exec vitest` is broken in this checkout.
- `DATABASE_URL` and `GUARDIAN_DATABASE_URL` were unset for every backend run; `TEST_DATABASE_URL` was set explicitly per instance. Trust authentication was used throughout; no password was supplied.

### Focused PostgreSQL proof (merged tree)

```sh
cd .scratch/integrate-reconciled
export TEST_DATABASE_URL="postgresql://postgres@127.0.0.1:55432/postgres"
env -u DATABASE_URL -u GUARDIAN_DATABASE_URL PYTHONPATH="$PWD" \
  .venv/bin/python -m pytest -o addopts="" -v -p no:warnings --basetemp=<stable tmp> \
  tests/routes/test_direct_message_read_state.py tests/routes/test_direct_messages.py \
  tests/migration/test_direct_message_read_cursor_migration.py \
  tests/routes/test_direct_message_read_concurrency.py
```

Result: **62 passed, 0 skipped** in 36.36s. All four PostgreSQL-dependent modules were collected and executed; there were zero skips, so the database proof is real rather than skipped.

This run was executed **after** the `down_revision` re-point, and it includes `test_read_cursor_migration_round_trip`, which exercises the read-cursor migration round trip against the reconciled lineage.

### Focused frontend proof (merged tree)

```sh
cd .scratch/integrate-reconciled/frontend/src
../node_modules/.bin/vitest run --config vitest.config.ts \
  components/direct-messages/__tests__/DirectMessageInbox.integration.test.tsx \
  components/direct-messages/__tests__/DirectMessageInbox.test.tsx \
  features/contacts/ContactsLauncher.test.tsx features/contacts/FloatingConversation.test.tsx \
  features/contacts/ContactsWindow.test.tsx components/share/ShareSheet.test.tsx
```

Result: **6 test files passed, 89 tests passed**, 0 failed.

### Full frontend suite

```sh
cd .scratch/integrate-reconciled/frontend && pnpm test
cd .scratch/baseline-main/frontend     && pnpm test
```

| Tree | Test files | Tests |
| --- | --- | --- |
| Integrated tree | 4 failed, 225 passed, 1 skipped (230) | 1 failed, 2276 passed, 1 skipped (2278) |
| Reconciled mainline baseline | 4 failed, 223 passed, 1 skipped (228) | 1 failed, 2242 passed, 1 skipped (2244) |

The failed set is **identical** on both trees, file for file:

- `features/chat/components/__tests__/GenerativeUI.test.tsx`
- `features/chat/components/generativeUi/openuiFoundationLibrary.test.tsx`
- `features/chat/components/generativeUi/openuiNative.test.tsx`
- `features/chat/components/generativeUi/openuiProgramAdmission.test.ts`

and the single failed test is the same in both: `renders the version-2 OpenUI foundation pack through the ordinary transcript`.

These four files are untouched by the read-state series, which modifies only the direct-message, contacts, and share surfaces. The integration adds 2 passing test files and 34 passing tests and introduces **no new frontend failure**.

### Typecheck

```sh
cd .scratch/integrate-reconciled/frontend && pnpm typecheck
cd .scratch/baseline-main/frontend     && pnpm typecheck
```

Both trees report **160** TypeScript errors, and the normalized error sets are identical. The only difference is the position of one pre-existing error: `frontend/src/components/direct-messages/DirectMessageInbox.tsx(251,7): error TS2322: Type 'number' is not assignable to type 'Timeout'` on the baseline moves to line `359` on the integrated tree because the series added lines above it. Same file, same error code, same count. **No new type error is introduced.**

### Full backend suite

```sh
cd .scratch/integrate-reconciled
env -u DATABASE_URL -u GUARDIAN_DATABASE_URL PYTHONPATH="$PWD" TMPDIR=<stable tmp> \
  TEST_DATABASE_URL="postgresql://postgres@127.0.0.1:55432/postgres" \
  .venv/bin/python -m pytest -o addopts="" -q -p no:warnings --continue-on-collection-errors \
  --basetemp=<stable tmp>
```

The two runs were executed concurrently, each against its own disposable PostgreSQL instance, so neither run could perturb the other's database. The final integrated tree was validated against a reconciled-mainline baseline built from the identical reconciled main SHA `bf9016369`, so the only difference between the two trees is the read-state integration itself.

| Tree | Result |
| --- | --- |
| Integrated tree | 282 failed, 8441 passed, 114 skipped, 35 xfailed, 11 xpassed, 587 errors in 3275.88s (0:54:35) |
| Reconciled mainline baseline `bf9016369` | 284 failed, 8418 passed, 114 skipped, 35 xfailed, 11 xpassed, 587 errors in 3219.71s (0:53:39) |

The integration has **two fewer failures, 23 more passing tests, and an identical error count** against the baseline.

The comparison was made by set identity, not by counting. The `FAILED`/`ERROR` node-id sets are 869 entries on the integrated tree and 871 on the baseline, and the symmetric difference is four entries, none of which is a read-state test:

| Node id | Integrated tree | Baseline | Interpretation |
| --- | --- | --- | --- |
| `tests/command_bus/test_chat_loopback_accepted_deadline.py::test_parent_total_deadline_closes_real_http` | failed in the full run | passed in the full run | timing-sensitive, unrelated to read state |
| `tests/vector/test_vector_physical_deadline.py::test_accepted_constructor_retains_parent_add_authority` | passed in the full run | failed in the full run | timing-sensitive, unrelated to read state |
| `tests/vector/test_vector_physical_deadline.py::test_chroma_bound_search_preserves_results_and_deferred_parent_handle` | passed in the full run | failed in the full run | timing-sensitive, unrelated to read state |
| `tests/vector/test_vector_physical_deadline.py::test_snapshot_is_coherent_and_next_search_observes_acknowledged_add` | passed in the full run | failed in the full run | timing-sensitive, unrelated to read state |

All four were re-run directly on **both** trees after the comparison, and all four pass on both trees (`7 passed` on the integrated tree, `7 passed` on the baseline). They are full-suite timing sensitivities, not integration regressions. No read-state test appears in the symmetric difference on either side.

No new unexplained baseline failure is introduced by this integration.

### Git verification

```sh
git status
git rev-parse HEAD
git merge-base --is-ancestor origin/main bf9016369      # succeeds
git merge-base --is-ancestor 1115b9263 HEAD              # succeeds
git merge-base --is-ancestor 429b8b032 HEAD              # fails, as required
git diff --check                                          # clean
git show -s --format="%H %P %T" HEAD
```

## Preserved semantics and invariants

Verified on the integrated tree:

- `guardian/db/models.py` carries **both** upstream `DirectMessageConsent` (`direct_message_consents`) and the series' `DirectMessageReadCursor` (`direct_message_read_cursors`). Upstream consent authority is intact.
- The read cursor is keyed by `(conversation_id, user_profiles.profile_id)`: it is participant-local, and the other participant can neither observe nor advance it.
- `guardian/messaging/service.py` retains `_lock_read_cursor_authority`, `with_for_update(key_share=True)`, and `execution_options(populate_existing=True)`, so concurrent advances are serialized against the participant authority row and a cursor cannot regress.
- The caller-asserted watermark bounds cursor advancement; a stale watermark after a newer read never regresses the cursor.
- Unread counts remain derived from the durable message store and the cursor. No counters or second message store were introduced.
- `POST /api/direct-messages/conversations/{conversation_id}/read` is present in `guardian/routes/direct_messages.py`.
- No sender-visible read-receipt surface exists anywhere in `guardian/` or `frontend/src/` (no `read_receipt`, `readReceipt`, `seen_by`, or `seenBy`).
- `docs/architecture/direct-messaging-contract.md` carries both the read-state contract (12 references) and the existing direct-message consent contract (12 references).
- ADR-103 is present and ADR-104 is preserved verbatim in the ADR index.
- The shared frontend projection is a read-through projection of the caller's own cursor, not authoritative persistence.

## Known limitations and inherited failures

These are reported, not hidden, and are not attributable to this integration.

**Inherited environment and dependency failures, identical on both trees:**

- 3 collection errors: `tests/identity/test_scout_handoff_routes.py` and `tests/identity/test_scout_qualification.py` fail with `ModuleNotFoundError: No module named 'fakeredis'`, and `tests/mcp/test_stdio.py` fails with `ImportError: cannot import name 'Client' from 'mcp'` (installed `mcp` package API drift). `--continue-on-collection-errors` is required to run the suite.
- The repository's backend suite is in a degraded state on the reconciled mainline: 284 failures and 587 errors on the baseline, and the integrated tree is slightly better (282 failures, 587 errors). The failing and erroring sets are the same to within four timing-sensitive entries, none of them in the read-state area. These are inherited conditions of the mainline, not consequences of this integration.
- 4 generative-UI frontend files fail as listed above.
- 160 typecheck errors on both trees.

**Sandbox artifact corrected during validation.** An earlier full-backend comparison (on the pre-reconciliation base `7153b69e9a`) reported two additional errors in the merged tree, in `tests/migration/test_direct_message_read_cursor_migration.py::test_read_cursor_migration_round_trip` and `tests/routes/test_direct_message_read_state.py::test_cleared_state_survives_a_new_session`. Both were `ERROR at setup` with `FileNotFoundError` on the pytest `tmp_path` base directory: the sandbox evicted the session temp root mid-run. The same cause produced 1033 such errors on the baseline tree and 1035 on the merged tree, which is why that first comparison reported 1666 and 1668 errors respectively.

Both read-state tests pass in isolation with a stable `--basetemp` (see the focused PostgreSQL proof). The full-suite comparison was therefore re-run on both final trees with a stable temp directory. The final logs contain **zero** `tmp_path` eviction errors, and the error count dropped from 1666/1668 to 587 on both trees, with the passing count rising from 7347/7366 to 8418/8441. The first-round comparison is retained here as an environmental artifact, not as evidence.

**Migration limitation.** The reconciled mainline's inherited two-head Alembic state is reported above and not unified; unifying it requires a new file outside the authorized set.

## Release posture and remaining gaps

Release posture is unchanged: **HOLD**. The default Beta remains unqualified.

- Read state is **not** merged into `main`, **not** deployed, and **not** live-qualified. The running Private Preview still serves `57184dfbe`, which predates read state.
- Same-node messaging retains its existing live proof at `57184dfbe`; that proof qualifies same-node messaging only.
- Private Preview deployment, browser qualification, live read-state qualification on a running preview, and any default Beta promotion are separate, separately authorized phases.
- No push, no deploy, and no `main`-branch promotion was performed by this task.

## Documentation follow-through

`docs/architecture/00-current-state.md` was reconciled to the actual integration status without broadening any release claim: it records the integration branch and its reconciled base, keeps the same-node messaging proof separate from the read-state implementation evidence, states that read state is neither deployed nor live-qualified, and leaves the release posture at HOLD. This proof record is the only added file outside the series' own twenty-six authorized paths.
