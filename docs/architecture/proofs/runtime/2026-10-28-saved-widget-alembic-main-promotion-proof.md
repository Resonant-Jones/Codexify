# Saved Widget / Memory-Consent Alembic Repair — Mainline Promotion Proof

- **Date:** 2026-10-28
- **Disposition:** **GO**
- **Release posture:** HOLD (unchanged)

This receipt records the promotion of the verified Saved Widget /
memory-consent Alembic repair onto current `main`. The two historical receipts
it builds on are preserved unchanged and remain the authoritative records for
the repair branch and the integration candidate respectively:

- `2026-10-27-saved-widget-memory-consent-merge-head-proof.md`
- `2026-10-27-saved-widget-integrated-merge-candidate-proof.md`

## 1. Evaluated identities

| | |
|---|---|
| Main before promotion | `cd47fd826cdc8788e75c98bc3c62b36822db71ea` |
| Proven candidate | `327744d294d22d1da4ed94549227fb734ac09f6a` |
| Merge base | `df1c60296728d34f1cf740e8f6b8dfee5a0f6110` |
| Promotion branch | `integrate/saved-widget-alembic-main-20261028` |

Both references were re-verified with `git rev-parse` immediately before any
work began, and matched their expected values exactly. The `main` worktree had
no tracked modifications. No reference was reset, rebased, cherry-picked, or
force-updated.

The candidate's own two-parent history was confirmed unchanged:

```
327744d29  parents: df1c60296728d34f1cf740e8f6b8dfee5a0f6110  50ddacd97e01136ba88890b13985d8471289c93e
```

The merge base of current `main` and the candidate is `df1c60296…`, the
candidate's first parent.

## 2. Changed-file scope

`main` advanced from `df1c60296…` to `cd47fd826…` while the candidate was
under qualification. The intervening changes were verified independently:

```
git diff --name-only df1c60296728d34f1cf740e8f6b8dfee5a0f6110 cd47fd826cdc8788e75c98bc3c62b36822db71ea
docs/architecture/00-current-state.md
docs/architecture/README.md
```

Documentation only — no migrations, no application code, no targeted tests.
The path overlap between that delta and the candidate's delta is **empty**.

The promotion merge itself introduced exactly the four authorized merge inputs
plus this receipt:

```
guardian/db/migrations/versions/7f2c9e1a4b63_merge_saved_widget_and_memory_consent_heads.py
tests/db/test_saved_widget_storage_migration.py
docs/architecture/proofs/runtime/2026-10-27-saved-widget-memory-consent-merge-head-proof.md
docs/architecture/proofs/runtime/2026-10-27-saved-widget-integrated-merge-candidate-proof.md
docs/architecture/proofs/runtime/2026-10-28-saved-widget-alembic-main-promotion-proof.md
```

**Both newer mainline documentation files survive intact.** After the merge,
`docs/architecture/00-current-state.md` and `docs/architecture/README.md` were
hash-verified byte-identical to their state at `cd47fd826…`. Neither was
edited.

All four merge inputs were hash-verified **byte-identical to candidate
`327744d29…`** — the repair was carried forward without re-authoring.

## 3. Merge construction

Performed in a dedicated isolated worktree created from `cd47fd826…`, never
in the source `main` worktree:

```
git merge --no-commit --no-ff integrate/saved-widget-alembic-heads-20261027
-> Automatic merge went well; stopped before committing as requested
```

At that point:

- `HEAD` was still `cd47fd826cdc8788e75c98bc3c62b36822db71ea`
- `MERGE_HEAD` was `327744d294d22d1da4ed94549227fb734ac09f6a`
- **Zero unresolved conflicts** (`git diff --name-only --diff-filter=U` empty)
- Exactly four authorized existing paths staged

## 4. Integrated migration graph

```
$ python -m alembic -c backend/alembic.ini heads
7f2c9e1a4b63 (head)
```

- **Exactly one head** (head count: 1)
- Migration files: **126**
- Lineage: 126 revisions, **no duplicate revision identifiers**, no missing parents
- Reachable from the single head: `7f2c9e1a4b63` (merge head), `a6b9d2e4f701`
  (saved widget), `c59e4d1a28f0` (memory consent), `f0d7c4b2a198` (shared
  parent), and the historical `2e865c4a9b10`
- Both original parent migrations remain **byte-identical to `main`**
- The merge revision still declares
  `down_revision = ('a6b9d2e4f701', 'c59e4d1a28f0')` with **zero schema
  operations** — no new tables, no new columns, no duplicated DDL

### The defect this removes from mainline

Before this promotion, `main` at `cd47fd826…` still carried **two** Alembic
heads — `a6b9d2e4f701` and `c59e4d1a28f0` — and did not contain the merge
revision. Verified directly against `main`'s own tree. The promotion replaces
that branched graph with a single canonical head.

## 5. PostgreSQL isolation

- **Instance:** host-native **PostgreSQL 16.2** — not a container
- **data_directory:** `/Volumes/Dev_SSD/Codexify-main/.scratch/pgdata_pg16`,
  beneath the approved scratch root
- **`listen_addresses`:** `127.0.0.1` — loopback only
- **Proof role:** `postgres`, superuser, mirroring `POSTGRES_USER` in the
  official `postgres` image (the disposable fixtures drop their databases via
  `pg_terminate_backend()`, which a lesser role cannot perform)
- **`TEST_DATABASE_URL`:** `postgresql://postgres@127.0.0.1:55432/postgres`
- **Import origins:** `guardian`, `guardian.core.saved_widget_store`, and
  `guardian.db.models` all resolved inside the promotion worktree
- **Overlapping proof execution:** none — the shared proof lock
  `127.0.0.1:59177` was free before the run
- **Production / Private Preview / persistent application DB:** never targeted
- **Docker:** not used, not restarted, no volumes modified

## 6. Targeted suite results

```
python -m pytest -o addopts="" -v -rs \
  tests/db/test_saved_widget_storage_migration.py \
  tests/db/test_saved_widget_revision_store.py \
  tests/core/test_saved_widget_validation.py \
  tests/db/test_saved_widget_validation_provenance.py \
  tests/db/test_automatic_memory_consent_migration.py
```

```
137 passed, 67 warnings in 111.60s (0:01:51)
```

- **Passed: 137**
- **Failed: 0**
- **Errors: 0**
- **Skipped: 0**

Zero skips is measured, not assumed: no `SKIPPED` line and no `N skipped`
summary appeared anywhere in the run. Every database-dependent case executed
against disposable PostgreSQL.

The count matches the candidate's own qualification exactly (137 passed), so
promotion introduces **no attributable regression**. The saved-widget
single-head case passes:

```
tests/db/test_saved_widget_storage_migration.py::test_the_migration_is_the_single_head PASSED
```

Log: `/Volumes/Dev_SSD/Codexify-main/.scratch/saved-widget/logs/main-promotion/all_five.log`

## 7. Database cleanup

- Databases remaining on the disposable server after validation:
  `postgres`, `template0`, `template1`
- Residue matching `mergehead_*`, `codexify_saved_widget*`, `codexify_consent*`:
  **0**

No named volume, Docker resource, or non-disposable database was modified. No
disk reclamation was performed. A throwaway baseline worktree used for the
inherited-failure comparison in §8 was removed.

## 8. Inherited migration-test failures

Three historical migration tests assert that the graph's head is the
pre-existing canonical revision `2e865c4a9b10`. They were executed against
**both** `main` at `cd47fd826…` (in a throwaway detached worktree) and the
promotion candidate, and the failure sets are **identical**:

| Failing test | Assertion |
|---|---|
| `tests/migration/test_d6_compatibility_bridge.py::test_final_graph_has_exactly_one_head` | `assert _script().get_heads() == [CANONICAL_HEAD]` |
| `tests/migration/test_alembic_revision_uniqueness.py::test_alembic_revision_ids_are_unique_and_hosted_room_lineage_is_preserved` | `assert heads == [CANONICAL_HEAD]` |
| `tests/migration/test_agent_extension_schema_consistency.py::test_agent_extension_schema_chain_merges_and_tables_exist` | `assert set(script.get_heads()) == {CANONICAL_HEAD_REVISION}` |

Baseline `main`: **3 failed, 12 passed**. Promotion candidate: **3 failed,
12 passed**. The failure sets were diffed and are byte-for-byte the same three
test ids.

On the candidate the assertion reads:

```
AssertionError: assert ['7f2c9e1a4b63'] == ['2e865c4a9b10']
```

These are **inherited failures, not regressions introduced by this repair.**
They assert a hardcoded head identifier rather than a graph property, so they
were already stale before this work: `main` carried two heads
(`a6b9d2e4f701`, `c59e4d1a28f0`), and the repair replaces that with one head
that is the mergepoint. Either way the literal `2e865c4a9b10` is not the head.

They were **not** repaired here. Repairing unrelated historical tests is
explicitly out of scope for this promotion, and correcting them is deferred to
a separate bounded change. Their presence does **not** constitute full backend
qualification, and this receipt does not claim it.

## 9. Release qualification limitations

A green focused database-contract suite is not release readiness. Still
outstanding:

- **Docker engine unavailable.** The engine socket accepts connections and then
  returns zero bytes; no container-path PostgreSQL proof has been run. All
  database evidence here comes from the native scratch cluster.
- **No supported-Compose qualification** for this promotion.
- **No browser or cross-browser qualification.**
- **Full backend qualification is not claimed.** The repository carries
  long-standing pre-existing failures outside these five suites, and the three
  inherited migration-head failures in §8 remain open.
- **Saved Widget remains storage only.** The `00-current-state.md` declaration
  that the storage foundation is implemented while its user-facing lifecycle
  remains unimplemented is untouched and still accurate. Promotion, listing,
  invocation, editing, deletion, export/restore, Library Widgets filtering, and
  canvas qualification remain open.
- **Inherited DLG validation errors and warnings** are unchanged.
- **No human-promotion authority** was added; none is claimed.

The current-state release gate remains `HOLD`, and it was not modified by this
work.

## 10. Disposition

**GO.**

Every acceptance gate passed: the merge preserves the latest mainline
documentation, the existing repair files remain byte-identical, exactly one
Alembic head exists, all five targeted suites pass with zero skips, disposable
isolation and cleanup are proven, a durable receipt accompanies the change, and
the integration commit carries exactly two parents with `main` first.

`main` is advanced only by a normal `git merge --ff-only` onto the already
verified two-parent commit — no history is rewritten, no raw ref update is
used, and no remote push is performed.

**Release posture remains HOLD.**
