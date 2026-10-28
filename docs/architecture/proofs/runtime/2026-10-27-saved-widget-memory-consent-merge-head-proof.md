# Saved Widget / Memory-Consent Alembic Merge-Head Proof

- **Date:** 2026-10-27
- **Disposition:** HOLD (inherited failure; no attributable regression)
- **Release posture:** HOLD (unchanged)

## 1. Starting main commit

`fb0b4e47aa02144b7222cbbc1049041a3896cf93`

`git rev-parse main` was verified to equal the evaluated mainline commit before
any work began. The main working tree's tracked files were inspected and were
clean; pre-existing untracked files were preserved.

Note: `main` advanced to `bf9016369127b801db13b5e85bf82203c850ba4c` during the work (`Merge remote-tracking branch 'origin/main'`).
`fb0b4e47aa02144b7222cbbc1049041a3896cf93` remains an ancestor of that tip, so the evaluated base is
still valid, but promotion of this repair would be a **merge, not a
fast-forward**. No reset or rebase was performed.

## 2. Repair worktree and commit

- **Branch:** `fix/saved-widget-memory-consent-alembic-heads-20261027`
- **Repair worktree:** `/Volumes/Dev_SSD/Codexify-main/.worktrees/feat-auto-20261020-cecd701e/repair-alembic-heads-20261027`
- **Base commit (parent of the repair commit):** `fb0b4e47aa02144b7222cbbc1049041a3896cf93`

The repair worktree was created from the exact evaluated main commit
`fb0b4e47aa02144b7222cbbc1049041a3896cf93` on a dedicated branch. It is an isolated checkout; the
pre-existing Saved Widget integration worktree was not modified, and the
pre-existing proof harness was preserved unchanged.

## 3. Original two heads

Captured from a clean pre-repair checkout of the same commit
(`/Volumes/Dev_SSD/Codexify-main/.worktrees/feat-auto-20261020-cecd701e/pre-repair-probe-20261027`), which does not contain the merge revision:

```
a6b9d2e4f701 (head)
c59e4d1a28f0 (head)
```

Two heads. The repair joins them.

## 4. Original shared parent

Both parents declared the same parent revision:

- `a6b9d2e4f701` (Saved Widget identity and revisions) -> `f0d7c4b2a198`
- `c59e4d1a28f0` (automatic memory suggestions consent) -> `f0d7c4b2a198`

`f0d7c4b2a198` was the leaf of the Saved Widget branch's base, so each migration
was individually a correct single head. origin/main independently added its own
migration on the same parent, and merging the branches produced a branched
graph.

Neither parent file was modified: both are byte-identical to their state on the
evaluated main commit.

## 5. New merge revision

- **Path:** `/Volumes/Dev_SSD/Codexify-main/.worktrees/feat-auto-20261020-cecd701e/repair-alembic-heads-20261027/guardian/db/migrations/versions/7f2c9e1a4b63_merge_saved_widget_and_memory_consent_heads.py`
- **Revision id:** `7f2c9e1a4b63`
- **down_revision:** `('a6b9d2e4f701', 'c59e4d1a28f0')`
- **upgrade / downgrade bodies:** empty (no schema operations)

Generated with Alembic's dedicated `merge` command (not `revision --merge`):

```
alembic -c backend/alembic.ini merge --rev-id 7f2c9e1a4b63 \
  -m "merge saved widget and memory consent heads" a6b9d2e4f701 c59e4d1a28f0
```

## 6. Resulting single head

```
7f2c9e1a4b63 (head)
```

Exactly one head.

## 7. Alembic history

Both former heads converge at the mergepoint:

```
a6b9d2e4f701, c59e4d1a28f0 -> 7f2c9e1a4b63 (head) (mergepoint), merge saved widget and memory consent heads
```

Recent history:

```
c6b2fdd401a9 -> 6d8d2f5c1a9b, add guardian_event_log table
c6b2fdd401a9 -> a1b2c3d4e5f6 (branchpoint), add temporal fields and personal facts tables
f2564d429cda -> c6b2fdd401a9 (branchpoint), add embedding idempotence fields to chat_messages
ef5f8a0c49a5 -> f2564d429cda (branchpoint), add metadata to chat_threads
d3b3e9f5d5ab -> ef5f8a0c49a5, add diary and identity exclusion flags to chat_threads
b5e6c55f0f0c -> d3b3e9f5d5ab, add imprint/persona/system_docs tables
9373693cc12e -> b5e6c55f0f0c, ensure chatlog and connector tables exist for Postgres-only runtime
ac973209add4 -> 9373693cc12e, add media and tts tables
2fa2ab3faac6 -> ac973209add4, create all tables from models
1eb6836bb10e -> 2fa2ab3faac6, add audit_log table
984a47e3bc2c -> 1eb6836bb10e, baseline schema
<base> -> 984a47e3bc2c, baseline schema
```

## 8. Actual PostgreSQL instance type

- **Instance:** host-native PostgreSQL `16.2` -- **not** a container
- **data_directory:** `/Volumes/Dev_SSD/Codexify-main/.scratch/pgdata_pg16`
- **Mode:** disposable scratch cluster created for this task; the proof refuses to run against any server whose data_directory is outside the disposable scratch root, and refuses any URL naming a production or Private Preview target
- **Proof role:** `postgres` (superuser, verified from `pg_roles.rolsuper`). This mirrors the container path, where `POSTGRES_USER` in the official `postgres` image is also a superuser; the disposable-database fixtures drop their database by calling `pg_terminate_backend()`, which a lesser role cannot do.
- **Listening on:** loopback only (`127.0.0.1`)
- **Named volumes touched:** none
- **Private Preview production data targeted:** none
- **Docker reset / prune / `down -v`:** none

The Docker engine was unavailable during this proof (the engine socket accepted connections and then returned zero bytes, and a 600-second patient probe timed out), so the proof ran against this independently verified disposable PostgreSQL -- the alternative the task specification allows. The cluster is a scratch instance living under the repository's own `.scratch/` directory; it holds no production data. The scratch cluster itself was left running; only the objects the proof created were removed.

## 9. Test database isolation

- **TEST_DATABASE_URL:** `postgresql://postgres@127.0.0.1:55432/postgres`
- **Target:** `disposable scratch PostgreSQL 16.2 on 127.0.0.1:55432 (data_directory /Volumes/Dev_SSD/Codexify-main/.scratch/pgdata_pg16); superuser role postgres (mirrors POSTGRES_USER in the official postgres image, which is a superuser); loopback only; not Private Preview, not a Docker named volume`
- **Isolation:** each database-dependent test created and dropped its own
  uniquely-named disposable database inside the disposable instance; the
  Private Preview application database was never addressed.

## 10. Import origins

Every module under test resolved inside the repair worktree:

```
/Volumes/Dev_SSD/Codexify-main/.worktrees/feat-auto-20261020-cecd701e/repair-alembic-heads-20261027/guardian/__init__.py
/Volumes/Dev_SSD/Codexify-main/.worktrees/feat-auto-20261020-cecd701e/repair-alembic-heads-20261027/guardian/core/saved_widget_store.py
/Volumes/Dev_SSD/Codexify-main/.worktrees/feat-auto-20261020-cecd701e/repair-alembic-heads-20261027/guardian/db/models.py
```

Alembic configuration origin: `/Volumes/Dev_SSD/Codexify-main/.worktrees/feat-auto-20261020-cecd701e/repair-alembic-heads-20261027/backend/alembic.ini`

Alembic `script_location`: `%(here)s/../guardian/db/migrations`

Migration revision id present in the evaluated tree: `7f2c9e1a4b63`

No overlapping proof execution: the single-run proof lock was
`acquired 127.0.0.1:59177`.

## 11. Applied migration results

Three disposable databases, each upgraded from a different valid starting point
to the combined head:

### `from_shared_parent`

- Disposable database: `mergehead_from_shared_parent_5e7285d5`
- Upgraded to `f0d7c4b2a198` (rc=0), then to `head` (rc=0)
- `alembic_version` = `7f2c9e1a4b63`

### `from_saved_widget_head`

- Disposable database: `mergehead_from_saved_widget_head_633265ba`
- Upgraded to `a6b9d2e4f701` (rc=0), then to `head` (rc=0)
- `alembic_version` = `7f2c9e1a4b63`

### `from_memory_consent_head`

- Disposable database: `mergehead_from_memory_consent_head_11418920`
- Upgraded to `c59e4d1a28f0` (rc=0), then to `head` (rc=0)
- `alembic_version` = `7f2c9e1a4b63`


## 12. Saved Widget schema readback

- `saved_widgets` columns: `widget_id`, `owner_user_id`, `name`, `lifecycle_state`, `current_revision`, `created_at`, `updated_at`
- `saved_widget_revisions` columns: `widget_id`, `revision`, `artifact_snapshot`, `provenance_snapshot`, `creation_context`, `edit_base_revision`, `created_at`
- Primary keys: `pk_saved_widgets`, `pk_saved_widget_revisions`
- Referential integrity: `fk_saved_widgets_owner_user_id` -> `users.id` ON DELETE CASCADE; `fk_saved_widget_revisions_widget` -> `saved_widgets.widget_id` ON DELETE CASCADE
- Forward-only current-revision pointer: `fk_saved_widgets_current_revision` -> `saved_widget_revisions(widget_id, revision)`, DEFERRABLE INITIALLY DEFERRED, with `saved_widgets_current_revision_check` enforcing `current_revision > 0`
- Immutable numbered revisions: `trg_saved_widget_revisions_immutable` BEFORE UPDATE trigger over `codexify_saved_widget_revisions_immutable`; a direct UPDATE of a stored revision was refused by the database
- Snapshot provenance: `artifact_snapshot`, `provenance_snapshot`, `creation_context` are present and NOT NULL
- Account ownership: a widget row with a non-existent owner was rejected by the foreign key
- Existing expected deletion behaviour: deleting the widget removed its revision rows (0 left)

## 13. Memory-consent schema readback

- `user_settings` consent columns: `automatic_memory_suggestions`, `consent_policy_version`, `consent_recorded_by_user_id`, `consent_recorded_at`, `consent_updated_at`
- Server defaults: `automatic_memory_suggestions` default 'unset'::character varying (nullable=NO); `consent_policy_version` default '1'::character varying (nullable=NO)
- Consent preference column: `automatic_memory_suggestions`
- Default unset/denied posture: a settings row written without the consent column read back as `['unset', '1']`
- Consent metadata columns: `consent_recorded_by_user_id`, `consent_recorded_at`, `consent_updated_at`
- Check constraint: `user_settings_automatic_memory_suggestions_check` allows only unset / enabled / paused / declined; a bogus value was rejected
- Existing account scope: the preference lives on the account's own `user_settings` row, keyed by `user_id`
- Existing settings readback behaviour: the stored preference was read back unchanged from the account's settings row

## 14. Focused test counts

### `saved_widget_storage_and_revision`

- Files: `tests/db/test_saved_widget_storage_migration.py`, `tests/db/test_saved_widget_revision_store.py`
- Summary: `============ 1 failed, 38 passed, 42 warnings in 321.81s (0:05:21) =============`
- Skipped: **0**

- Failed cases: `tests/db/test_saved_widget_storage_migration.py::test_the_migration_is_the_single_head`
- Log: `/Volumes/Dev_SSD/Codexify-main/.scratch/saved-widget/logs/merge-head-1793154645/saved_widget_storage_and_revision.log`

### `saved_widget_validation_and_provenance`

- Files: `tests/core/test_saved_widget_validation.py`, `tests/db/test_saved_widget_validation_provenance.py`
- Summary: `======================= 91 passed, 17 warnings in 54.18s =======================`
- Skipped: **0**

- Failed cases: none
- Log: `/Volumes/Dev_SSD/Codexify-main/.scratch/saved-widget/logs/merge-head-1793154645/saved_widget_validation_and_provenance.log`

### `automatic_memory_consent_migration`

- Files: `tests/db/test_automatic_memory_consent_migration.py`
- Summary: `======================= 7 passed, 10 warnings in 33.56s ========================`
- Skipped: **0**

- Failed cases: none
- Log: `/Volumes/Dev_SSD/Codexify-main/.scratch/saved-widget/logs/merge-head-1793154645/automatic_memory_consent_migration.log`

### `combined_sweep`

- Files: `tests/db/test_saved_widget_storage_migration.py`, `tests/db/test_saved_widget_revision_store.py`, `tests/core/test_saved_widget_validation.py`, `tests/db/test_saved_widget_validation_provenance.py`, `tests/db/test_automatic_memory_consent_migration.py`
- Summary: `1 failed, 136 passed, 67 warnings in 187.64s (0:03:07)`
- Skipped: **0**

- Failed cases: `tests/db/test_saved_widget_storage_migration.py::test_the_migration_is_the_single_head`
- Log: `/Volumes/Dev_SSD/Codexify-main/.scratch/saved-widget/logs/merge-head-1793154645/combined_sweep.log`


## 15. Exact skipped count

**0 skipped** across every executed suite.

Zero database tests were skipped: every database-dependent case in the five
targeted suites executed against disposable PostgreSQL.

## 16. Database cleanup results

- Disposable path databases dropped: 3 of 3 (mergehead_from_shared_parent_5e7285d5, mergehead_from_saved_widget_head_633265ba, mergehead_from_memory_consent_head_11418920)
- Databases the proof dropped are exactly the ones it created: **True**
- Leftover proof databases on the disposable server: none
- Proof-owned disposable databases swept at cleanup: ['mergehead_from_shared_parent_1198c65f']
- Databases remaining on the disposable server: none
- Note: swept 1 proof-owned disposable database(s) (the `mergehead_*` prefix is unique to this proof) left on the server by an earlier run of this proof: `mergehead_from_shared_parent_1198c65f`

## 17. Inherited failures

One case in the five targeted suites fails: `tests/db/test_saved_widget_storage_migration.py::test_the_migration_is_the_single_head`.

```
assert tuple(script.get_heads()) == (SAVED_WIDGET_REVISION,)  # SAVED_WIDGET_REVISION = 'a6b9d2e4f701'
```

**This failure is inherited, not introduced by this correction.** It was reproduced on a clean pre-repair checkout of the same commit (`fb0b4e47aa02144b7222cbbc1049041a3896cf93`, worktree `/Volumes/Dev_SSD/Codexify-main/.worktrees/feat-auto-20261020-cecd701e/pre-repair-probe-20261027`) where the merge revision does not exist:

```
assert ('a6b9d2e4f701', 'c59e4d1a28f0') == ('a6b9d2e4f701',)
# Left contains one more item: 'c59e4d1a28f0'
```

Baseline log: `/Volumes/Dev_SSD/Codexify-main/.scratch/saved-widget/logs/pre_repair_baseline_single_head.log`

Before the repair the test failed because the tree had **two** heads. After the repair it fails because the tree has **one** head and that head is the mergepoint `7f2c9e1a4b63` rather than `a6b9d2e4f701`. The test's stated intent -- *exactly one head* -- is what this correction delivers; the hardcoded revision id cannot survive any correct merge revision. No other case in any of the five targeted suites fails.

A repository-wide `pytest -v` sweep was not treated as part of this gate; unrelated pre-existing failures elsewhere in the repository (including the inherited DLG validation errors and warnings and the `NameError: _fetch_work_order` defect in `guardian/workers/coding_worker.py`) are unchanged by this correction and are reported separately from this proof.

## 18. Remaining release gaps

- Saved Widget remains **storage only**. The `00-current-state.md` declaration
  that the Saved Widget storage foundation is implemented while its user-facing
  lifecycle remains unimplemented is unchanged and intact.
- Browser qualification, cross-browser coverage, and the inherited DLG
  validation errors and warnings are untouched by this correction.
- Docker Compose / supported-path qualification is not established by this
  proof.
- The stale single-head assertion in `tests/db/test_saved_widget_storage_migration.py`
  still fails and still must be corrected. That file was read-only for this
  task, so the correction could not be made here.

## 19. Disposition

**HOLD** - every mandatory gate passed and the correction is sound, but one targeted test case fails: saved_widget_storage_and_revision: suite passed

That failure is **inherited, not attributable to this correction**. The assertion `test_the_migration_is_the_single_head` hardcodes `a6b9d2e4f701` as *the* Alembic head. It fails on the pre-repair tree at `fb0b4e47aa02` as well, because that tree had two heads:

```
a6b9d2e4f701 (head)
c59e4d1a28f0 (head)
```

Any correct merge revision necessarily makes it fail, because the head becomes the mergepoint `7f2c9e1a4b63` rather than `a6b9d2e4f701`. The test's stated intent -- *exactly one head* -- is now satisfied by this correction; its hardcoded revision id is not.

`tests/db/test_saved_widget_storage_migration.py` was listed read-only for this task, so the stale assertion could not be corrected here. Closing it requires a separate, explicitly authorized change to that file (assert the merge revision as head, or assert that `a6b9d2e4f701` is an ancestor of the single head).

**Release posture remains HOLD.** The repair is committed on the isolated branch `fix/saved-widget-memory-consent-alembic-heads-20261027` and is **not** promoted to `main`; promotion remains a separate, explicit operator decision.

### Note on evidence scope

The earlier Saved Widget PostgreSQL proof was performed against the
**pre-origin/main** integration tree, where `a6b9d2e4f701` was the single head.
It was **not** reused as integrated-tip qualification for this correction. Every
result recorded above was produced against the repaired integrated tree
`fb0b4e47aa02144b7222cbbc1049041a3896cf93` plus `7f2c9e1a4b63`, using a proof harness written for this
repair; the pre-existing Saved Widget harness (hardcoded to the older
integration worktree) was preserved and not reused.

This correction joins two already-accepted, independent schema branches without
changing either contract, so no new ADR is required.
