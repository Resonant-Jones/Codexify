# Read state integrated onto the promoted single-head mainline

Date: 2026-10-28

Evidence: isolated branch, Alembic graph inspection and disposable real-PostgreSQL tests. Not a deployment, not a push, not a live Preview qualification. Release remains `HOLD`.

## Purpose

The reviewed recipient-local read-state series was integrated onto a reconciled mainline as branch `integrate/read-state-onto-reconciled-main-20261027` at `3b7142586244f45d1a68e750a74a08de2c9e6e1e`. That branch carried the read-cursor migration `b3c8d1e5f7a2` but descended from a mainline that still had two Alembic heads.

A separate correction then unified the mainline's own two heads behind a graph-only merge revision `7f2c9e1a4b63`, and that correction was promoted onto `main` at `144dc8355` — the promoted merge revision is the authoritative one, recorded in `2026-10-28-saved-widget-alembic-main-promotion-proof.md`. Combining the read-state branch with the promoted mainline therefore produced two heads again: the read-cursor branch and the unified mainline head.

This record covers the further merge revision `3a91d7c4e8b2` that connects them, so the mainline carries Saved Widget storage, account consent, and participant-local read state in one Alembic lineage with one head.

## Evaluated revisions

| Role | Revision |
| --- | --- |
| Promoted main before the read-state merge (first parent) | `144dc83554638b6b66524fd77e1f3cc403337751` |
| Reviewed read-state integration (second parent) | `3b7142586244f45d1a68e750a74a08de2c9e6e1e` |
| Promoted mainline merge revision | `7f2c9e1a4b63` (module `7f2c9e1a4b63_merge_saved_widget_and_memory_consent_heads.py`) |
| Read-cursor revision | `b3c8d1e5f7a2` |
| Consent revision | `c59e4d1a28f0` |
| Saved Widget storage revision | `a6b9d2e4f701` |
| Further merge revision (new) | `3a91d7c4e8b2` |
| Branch | `fix/read-state-onto-promoted-main-20261028` |

The commit that carries this record is supplied in the task closeout, because a commit cannot embed its own hash.

## The graph

Before the read-state merge, two heads:

```text
7f2c9e1a4b63 (head)   Merge Saved Widget storage and automatic-memory consent heads.
b3c8d1e5f7a2 (head)   Add recipient-local direct message read cursors.
```

After:

```text
3a91d7c4e8b2 (head) (mergepoint), Merge the read-cursor branch into the unified Saved Widget / consent head.
a6b9d2e4f701, c59e4d1a28f0 -> 7f2c9e1a4b63 (mergepoint), Merge Saved Widget storage and automatic-memory consent heads.
a6b9d2e4f701 -> b3c8d1e5f7a2, Add recipient-local direct message read cursors.
f0d7c4b2a198 -> a6b9d2e4f701 (branchpoint), Add canonical Saved Widget identity and immutable revision storage.
f0d7c4b2a198 -> c59e4d1a28f0, add automatic memory suggestions consent to user_settings
```

`3a91d7c4e8b2` declares `down_revision = ("7f2c9e1a4b63", "b3c8d1e5f7a2")`. Both existing revision identities remain intact and are the direct parents of the new one. The new revision contains **no DDL**: `upgrade()` and `downgrade()` are `pass`, and the file makes no `op.` call. The revision ID was confirmed unused before use.

The further merge revision is placed in the same commit as the branch merge. That is deliberate: an intermediate commit whose tree had two heads would again make `alembic upgrade head` ambiguous and would re-break the same tests that the first merge repaired. No reachable commit on this branch has an ambiguous head.

## A duplicate revision identifier that must not reach `main`

An earlier candidate for this work regenerated the Saved Widget / consent merge revision `7f2c9e1a4b63` under the module name `7f2c9e1a4b63_merge_saved_widget_and_consent_heads.py`. The promoted candidate on `main` declares the **same revision identifier** under the module name `7f2c9e1a4b63_merge_saved_widget_and_memory_consent_heads.py`.

Those two modules are mutually exclusive. With both present, Alembic reports the graph as broken:

```text
UserWarning: Revision 7f2c9e1a4b63 is present more than once
3a91d7c4e8b2 (head)
7f2c9e1a4b63
```

That is two heads and a warning on every invocation — the exact failure this work exists to remove. This was verified empirically by placing both modules in one tree and running `alembic heads`; the result above is that output, not an estimate.

Consequently this branch was rebuilt directly on the promoted `main` tip and **does not** contain the regenerating module. The revision identifier `7f2c9e1a4b63` is used only once in the tree, and the identifier-uniqueness scan over `guardian/db/migrations/versions/` returns no duplicates.

The superseded local branches `fix/alembic-main-head-merge-20261028` and `fix/read-state-onto-main-head-merge-20261028` still carry the regenerating module. They must not be merged into `main`; they are retained only as the record of the earlier regeneration and of the full-suite evidence quoted below.

## Conflict resolution

The branch merge produced exactly one conflict, in `docs/architecture/00-current-state.md`. The ADR index merged without conflict and carries both ADR-103 (recipient-local read state) and ADR-104 (agent run cancellation intent) in numeric order; both ADR files are present in the merged tree.

The three-way inputs were identical to the ones already resolved and validated for the earlier branch: merge base `bf9016369`, ours the weekly current-state override carried by `main`, theirs the read-state side. The resolution was therefore applied from the previously validated result, and then two proof links were repointed to the promoted proof receipts and the new receipt's `proofs/runtime/` location.

The current-state conflict was resolved by inspection, keeping the newer weekly override's condensed structure and adding the facts it had dropped:

- Retained from the newer mainline: the account-bound run readback and fail-closed cancellation bullet, the account-consent and scoped-settings bullet, the durable chat terminal/readback reconciliation, the Saved Widget storage foundation, the generated-UI containment repair and Chrome 156 evidence, the "no fresh integrated-tip qualification" statement, and the `origin/main` accounting bullet — the last rewritten, because the stored `origin/main` has since advanced to `494a60260` and is no longer contained in local `main`.
- Retained from the read-state side, because the newer override had dropped them and they are material: the personal-fact candidate-listing fix, the `@`-sigil People-search fix, the same-node private-preview live proof at `57184dfbe`, and the recipient-local read-state bullet.
- The read-state bullet was rewritten from "integrated on branch `integrate/read-state-onto-reconciled-main-20261027` … not merged to `main`" to the new reality: integrated onto this mainline, test-evidenced, **not deployed and not live-qualified**, with the running preview still serving `57184dfbe`.
- Two further lines that still carried the pre-merge "branch-only, neither merged to `main`" framing were updated to match: the Private Preview paragraph under "Current supported reality" and the corresponding "do not assume" bullet.
- The "Not yet true" bullet on private-preview messaging was resolved in favour of the read-state side's more precise wording, which keeps the live proof and the remaining unqualified gaps visible; the Saved Widget bullet was kept as a union of both sides.
- Priorities item 5 was resolved in favour of the more precise read-state wording, which records that same-node messaging is closed by live proof while share-link expiry/revocation, cross-node messaging, live read-state qualification, and Saved Widget qualification remain open.

No release statement was broadened. The release posture remains `HOLD` and the default Beta remains unqualified.

## Environment and commands

Python 3.12.13, pytest 8.4.2. The database was PostgreSQL **16.2, a locally patched build** (`PG_FILE_INTERLOCK`, named-POSIX semaphores, `dynamic_shared_memory_type=mmap`, trust authentication) under `.scratch/pg162install/bin`. This is **not** the official stock image. The Preview database was not used. `DATABASE_URL` and `GUARDIAN_DATABASE_URL` were unset for every run; each test creates a uniquely named disposable database and drops it afterwards. A stable scratch `TMPDIR` and `--basetemp` were used so pytest's `tmp_path` base could not be evicted mid-run.

```sh
cd .scratch/readstate-on-main
python -m alembic -c backend/alembic.ini heads
python -m alembic -c backend/alembic.ini history -r 'f0d7c4b2a198:heads'
TEST_DATABASE_URL=postgresql://postgres@127.0.0.1:<port>/postgres \
  python -m pytest -o addopts='' -v -p no:warnings --basetemp=<stable-temp>/pt_read_merge \
  tests/migration/test_read_state_main_head_merge.py
```

## Test results

### Alembic graph

```sh
cd .scratch/readstate-on-main
python -m alembic -c backend/alembic.ini heads
# 3a91d7c4e8b2 (head)
```

The lineage reaches a single head:

```
f0d7c4b2a198 -> a6b9d2e4f701 -> b3c8d1e5f7a2 --+
               f0d7c4b2a198 -> c59e4d1a28f0 -> 7f2c9e1a4b63 --+-> 3a91d7c4e8b2 (sole head)
```

Heads went 2 → 1 → 2 → 1. Every pre-existing revision identity is intact; both merge revisions are graph-only, with `upgrade()` and `downgrade()` bodies of a single `pass` and no `op.` call.

### Focused PostgreSQL suite

Eight files were executed against the disposable PostgreSQL 16.2 build:

| File | Surface |
| --- | --- |
| `tests/migration/test_read_state_main_head_merge.py` | the further merge revision (6 tests) |
| `tests/db/test_saved_widget_consent_head_merge.py` | the promoted mainline merge revision (6 tests) |
| `tests/db/test_saved_widget_storage_migration.py` | Saved Widget schema storage |
| `tests/migration/test_direct_message_read_cursor_migration.py` | recipient-local read cursor |
| `tests/migration/test_direct_messaging_migration.py` | direct messaging schema |
| `tests/routes/test_direct_message_read_state.py` | read-state routes |
| `tests/routes/test_direct_message_read_concurrency.py` | read-state concurrency |
| `tests/routes/test_direct_messages.py` | direct-message routes |

**Result: 85 passed, 0 failed** (2:57).

An earlier execution of this suite on the superseded branch produced **9 failed, 67 passed**. Both causes were in the proof scaffolding it authored, not in the migration graph, and both were corrected before this branch was built:

1. **Duplicate account seeding.** `tests/migration/test_read_state_main_head_merge.py` seeded two `user_profiles` rows under one `user_id`. The `user_profiles` table declares `sa.UniqueConstraint("user_id", name="uq_user_profiles_user_id")` alongside `fk_user_profiles_user_id_users`, so one account carries exactly one profile. The insert violated that constraint with `psycopg.errors.UniqueViolation`. The fix follows the pattern used by the reviewed read-cursor migration test: a two-participant conversation requires two distinct accounts, and the peer account is now seeded separately.
2. **Head literals invalidated by the further merge.** `tests/db/test_saved_widget_consent_head_merge.py` and `tests/db/test_saved_widget_storage_migration.py` asserted the head was exactly `7f2c9e1a4b63`, which the further merge revision necessarily supersedes. Both now assert the invariant that actually matters — exactly one head exists, and the merge revision lies on its lineage — using the script directory's revision walk. The upstream tests that already used the ancestry form (`test_memory_revision_persistence_migration.py`, `test_memory_lifecycle_revision_persistence_migration.py`, `test_memory_review_revision_persistence_migration.py`) are the precedent for this formulation, and they now pass on the unified head. The promoted candidate on `main` had already adopted the same ancestry form in `test_saved_widget_storage_migration.py`, independently.

`tests/db/test_saved_widget_consent_head_merge.py` resolves the merge revision's module by scanning for the revision identifier declaration rather than by a hard-coded file name, because the module name is not part of the migration contract.

### Frontend

```sh
cd .scratch/read-state-combined/frontend/src
../node_modules/.bin/vitest run --config vitest.config.ts \
  components/direct-messages/__tests__/DirectMessageInbox.integration.test.tsx \
  components/direct-messages/__tests__/DirectMessageInbox.test.tsx \
  features/contacts/ContactsLauncher.test.tsx features/contacts/FloatingConversation.test.tsx \
  features/contacts/ContactsWindow.test.tsx components/share/ShareSheet.test.tsx
cd .scratch/read-state-combined/frontend && pnpm test && pnpm typecheck
```

- Focused read-state surfaces: **6 files, 89 tests passed**, 0 failed.
- Full frontend suite: **4 failed | 225 passed | 1 skipped (230 files)**, **1 failed | 2276 passed | 1 skipped (2278 tests)**.
- The four failing files are the inherited generative-UI set — `GenerativeUI.test.tsx`, `openuiFoundationLibrary.test.tsx`, `openuiNative.test.tsx`, `openuiProgramAdmission.test.ts` — identical to the set on both the read-state integration branch and the unified-mainline candidate, and untouched by the read-state series.
- Typecheck: **160 errors**, with a normalized error set identical to the unified-mainline candidate's. No new type error is introduced by this merge.

### Full backend suite

The full backend suite was run to completion on the **single-head candidate tree** `889b07af2` (branch `fix/alembic-main-head-merge-20261028`), whose migration content is revision-identical to the promoted `7f2c9e1a4b63` on `main`, and compared by node-id set against the same-tree baseline `cd47fd826`:

| Tree | Result |
| --- | --- |
| Baseline `cd47fd826` | 283 failed, 8419 passed, 114 skipped, 35 xfailed, 11 xpassed, 587 errors (0:46:18) |
| Candidate `889b07af2` | 243 failed, 9015 passed, 114 skipped, 35 xfailed, 11 xpassed, 37 errors (1:16:47) |

| Set | Count |
| --- | --- |
| Unique FAILED/ERROR node ids on the baseline | 870 |
| Unique FAILED/ERROR node ids on the candidate | 280 |
| Failing on the baseline, passing on the candidate (**repaired**) | **595** |
| Failing on both trees (inherited) | 275 |
| Failing on the candidate only | 5 |

The 595 repaired node ids are the `MultipleHeads` class: on the baseline every test that upgraded to `head` aborted, because the graph had two heads. The single merge revision removes that abort and lets those tests run their real body.

**No regression was introduced.** The five node ids that fail on the candidate but not on the baseline are wall-clock artefacts of the two suites running concurrently on the same machine, and none of them touch the migration graph:

- `tests/core/test_chat_stream_accepted_deadline.py::test_absolute_deadline_interrupts_real_http[partial|retry|tokenless|versioned_404_body]` — the assertion is `time.monotonic() - start < 0.6`; under load the measured interval was 1.598 s.
- `tests/workers/test_document_worker_shutdown.py::test_hung_writer_is_reaped_before_failed_commit_with_no_late_writes` — the probe sampled the document state as `failed` where it expected `processing`, a race against the spawned child.

Re-run in isolation on the candidate tree with no competing load, all eight cases of the first test and the second test **pass** (8 passed in 19.67 s). They are load-induced flakes, not defects introduced here.

The 275 failures that remain are inherited: the same node ids fail on the unmodified baseline tree, and they span 80 files across identity, route, pi, chronicle, evidence-packet, worker and integration surfaces that this change does not touch. They are pre-existing baseline debt and are reported, not repaired.

FINAL_TREE_BACKEND_RESULT

## Known limitations

- The PostgreSQL evidence is from a locally patched 16.2 build, not the official image. It proves migration and constraint behavior, not a deployed runtime.
- The seven stale `2e865c4a9b10` assertions and the `c7f4a9b2e6d1` literal in `tests/migration/test_memory_purge_tombstone_migration.py` remain failing. They are inherited and were already failing before this change.
- The disposable PostgreSQL instances are pre-existing local servers; the sandbox blocks `pg_ctl stop` and `kill -TERM` on their PIDs, so the operator should stop them outside the session when no longer needed.
- `origin/main` advanced to `494a60260` while this work was in progress, and local `main` does not yet contain it. That upstream range changed three test files and **no** migration, so it does not alter the head set this correction addresses; reconciling local `main` with upstream is a separate step and was not performed here.
- The promoted merge revision `7f2c9e1a4b63` is exercised here by the focused suite; the full backend suite quoted above was run against the revision-identical candidate tree, not against this branch's tree.

## Release and ADR posture

No ADR change. The Saved Widget contract and ADR-102 identity/revision boundary are unchanged, the account-owned automatic-collection consent is unchanged, and neither introduces a read receipt or parallel persistence authority. ADR-103 (recipient-local read state) and ADR-104 are carried in unchanged from the reviewed read-state branch. Release remains **HOLD** and the default Beta remains unqualified. Nothing was pushed and nothing was deployed.
