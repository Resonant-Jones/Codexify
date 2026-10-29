# Local Main ↔ origin/main Reconciliation and Publication Proof

- **Date:** 2026-10-28
- **Disposition:** **GO** — publish the reconciled mainline
- **Release posture:** HOLD (unchanged)

This receipt records the reconciliation of local `main` with `origin/main` and
the publication of the resulting tree. It closes the GitHub handoff for the
Saved Widget storage integration, which was integrated into local `main` by
earlier work and had not yet been published.

## 1. Divergence as measured

| | |
|---|---|
| Local `main` before reconciliation | `f0d2d26ea664d1e15459f5e8e2ed5522115cb45d` |
| `origin/main` before reconciliation | `bceac5b57f112a74bb7c8a4aa2dd73b05c917db1` |
| Merge base | `533542773e9dbaa4c5d35c6b1af1f6ae861cfa95` |
| Commits only on local `main` | 44 |
| Commits only on `origin/main` | 8 |

The branches had diverged long before this work. Neither side was rewritten,
reset, rebased, or force-updated.

### What upstream carried

The 8 upstream-only commits:

```
bceac5b57 Merge pull request #942 from .../test/scout-sse-bounded-reader-20261028
69a6747a7 test(scout): correct bounded task event stream fixture
494a60260 Merge pull request #940 from .../integrate/operator-route-manifest-20261027
e01db0609 test(identity): classify ADR-100 operator route additions
b1511c940 Merge pull request #937 from .../fix/ci-evidence-release-boundary-contracts
a4180890f Merge pull request #936 from .../fix/hosted-room-sqlite-orphan-check-fixture
c7ab5c95f test: reconcile evidence release checks with canonical hold boundary
89e99f081 fix(tests): isolate postgres orphan check in sqlite fixture
```

They touch **four test files only** — no migrations, no application code:

```
guardian/tests/routes/test_hosted_room_guest.py
tests/evidence_packets/test_guardian_evidence_bounded_read_contract.py
tests/identity/test_operator_route_auth_migration.py
tests/identity/test_scout_app_mount.py
```

The path overlap between upstream's delta and local main's delta is **empty**.
Neither side modified a file the other modified, which is why the merge is
conflict-free.

### What local main carried

Local main additionally carried the Saved Widget storage integration and its
Alembic repair (promoted in `144dc8355`), the read-state integration, and the
Generative UI containment work. `144dc8355` was verified to remain an ancestor
of local main, so the Saved Widget promotion had not been rewritten.

Local main also carried **four Alembic revisions that upstream does not have**
(the Saved Widget pair, the read-cursor revision, and the merge revision
joining them), giving local main 128 migration files against upstream's 124.

## 2. Reconciliation

Performed on an isolated branch `integrate/reconcile-origin-main-20261028`
created from local main, never by rewriting either remote-tracking ref:

```
git merge --no-commit --no-ff origin/main
-> Automatic merge went well; stopped before committing as requested
```

Verified at that point:

- `HEAD` remained `f0d2d26e…` — local main was not advanced by the merge
- `MERGE_HEAD` was `bceac5b57…` — the upstream tip
- **Zero unresolved conflicts** (`git diff --name-only --diff-filter=U` empty)
- Exactly the four upstream files staged; nothing else modified
- Each of the four merged files is **byte-identical to its `origin/main`
  blob**
- The remainder of local main's tree is **fully preserved**: a tree diff of
  local main against the reconciled tree, excluding the four upstream files,
  is empty

Both histories are therefore preserved as ancestors of the merge commit.
Nothing was discarded.

## 3. Integrated migration graph

```
$ python -m alembic -c backend/alembic.ini heads
3a91d7c4e8b2 (head)
```

- **Exactly one head**, unchanged by the reconciliation
- 128 migration files
- The Saved Widget merge revision `7f2c9e1a4b63` remains inside the head's
  ancestry, together with `a6b9d2e4f701`, `c59e4d1a28f0`, `f0d7c4b2a198`, and
  the read-cursor revision `b3c8d1e5f7a2`
- No migration file was added, removed, or rewritten by the reconciliation

Note on the head identifier: `3a91d7c4e8b2` is an **Alembic revision id**, not
a Git commit SHA. It names the merge revision that folds the read-cursor
branch into the unified mainline, and is recorded as the authoritative promoted
merge revision in
`2026-10-28-saved-widget-alembic-main-promotion-proof.md`.

## 4. PostgreSQL qualification of the reconciled tree

- **Instance:** host-native **PostgreSQL 16.2**, `data_directory`
  `/Volumes/Dev_SSD/Codexify-main/.scratch/pgdata_pg16` (beneath the approved
  scratch root), `listen_addresses` `127.0.0.1`, superuser proof role
- **`TEST_DATABASE_URL`:** `postgresql://postgres@127.0.0.1:55432/postgres`
- **Import origins:** `guardian`, `guardian.core.saved_widget_store`,
  `guardian.db.models` — all resolved inside the reconciliation worktree
- **Overlapping proof run:** none; the shared proof lock `127.0.0.1:59177` was
  free before the run
- **Production / Private Preview / persistent application DB:** never targeted
- **Docker:** not used, not restarted, no volumes modified

### Saved Widget contract suites

```
python -m pytest -o addopts="" -v -rs \
  tests/db/test_saved_widget_storage_migration.py \
  tests/db/test_saved_widget_revision_store.py \
  tests/core/test_saved_widget_validation.py \
  tests/db/test_saved_widget_validation_provenance.py \
  tests/db/test_automatic_memory_consent_migration.py
```

```
137 passed, 67 warnings in 484.59s (0:08:04)
```

- **Passed: 137 · Failed: 0 · Errors: 0 · Skipped: 0**

Zero skips is measured, not assumed: no `SKIPPED` line and no `N skipped`
summary appeared in the run. This matches the count recorded for the
promotion candidate, so the reconciliation introduces no regression to the
Saved Widget contract. `test_the_migration_is_the_single_head` passes on the
reconciled tree.

### Database cleanup

Residue matching `mergehead_*`, `codexify_saved_widget*`, or `codexify_consent*`
after all validation: **0**. The disposable databases created by the gate runs
were removed. Databases belonging to other Codexify sessions sharing the same
scratch cluster were left untouched.

## 5. Upstream's own touched test files

The reconciliation brings four upstream test files into a tree whose other
contents come from local main. To establish whether that combination is
sound, the same four files were executed on **three trees** and the failure
sets compared:

| Tree | Failed | Passed | Collected |
|---|---|---|---|
| `origin/main` alone (`bceac5b57`) | 4 | 99 | 103 |
| local `main` alone, pre-reconciliation (`f0d2d26e`) | 6 | 26 | 32 |
| **Reconciled tree** | **10** | **93** | **103** |

(The `main`-alone row collects fewer tests because the merge base predates
one of the upstream files' own additions on that side.)

Exact failure sets:

- `origin/main` alone — 4 × `test_scout_app_mount.py::test_hosted_transport_retains_mainline_durable_task_authorization[...]`
- local `main` alone — the same 4 × `test_scout_app_mount.py[...]`, plus
  `test_guardian_evidence_bounded_read_contract.py::test_cross_links_and_existing_tools_remain_green`,
  plus `test_operator_route_auth_migration.py::test_frozen_operator_manifest_has_exactly_58_registrations_in_13_files`
- reconciled tree — the same 4 × `test_scout_app_mount.py[...]`, plus
  `test_cross_links_and_existing_tools_remain_green`, plus 5 further cases in
  the same upstream file:
  `test_release_boundary_helper_accepts_the_canonical_document`,
  `test_release_boundary_helper_ignores_case_and_wrapping`,
  `test_release_boundary_helper_rejects_a_contradicted_hold`,
  `test_release_boundary_helper_rejects_a_document_without_default_beta_non_promotion`,
  `test_release_boundary_helper_rejects_a_document_without_hold`

**The reconciliation fixed one upstream failure** — upstream's PR #940
reclassified the operator-route manifest, so
`test_frozen_operator_manifest_has_exactly_58_registrations_in_13_files` now
passes on the reconciled tree.

**The reconciliation introduced no new defect.** The 5 additional cases are
additional *detectors* of one pre-existing condition that local main already
carried: local main's `docs/architecture/00-current-state.md` has drifted out
of compliance with the canonical release-truth contract in
`tests/evidence_packets/release_truth_contract.py`.

The drift is precise. The contract requires six canonical phrases; local
main's current-state document is missing two of them:

| Required phrase | `origin/main` | local `main` |
|---|---|---|
| ``the release gate remains `HOLD` `` | present (mid-sentence) | **missing** (main writes `The release gate remains \`HOLD\`` with a capitalised sentence start) |
| `not default Beta support` | present | **missing** |
| `bounded evidence` | present | present |
| `qualification is a separate gate` | present | present |
| `without current-main qualification` | present | present |
| `release readiness` | present | present |

Because local main's document was already non-compliant, local main **already
failed** `test_cross_links_and_existing_tools_remain_green` before this
reconciliation — with the assertion
`assert "release gate remains \`hold\`" in phase`. Upstream's newer test file
adds five further cases that detect the same drift, because its string-surgery
helpers (`_drop`, `_swap`) perform case-sensitive matching against the
canonical document. The underlying condition is identical; only the number of
detectors changed.

Neither side was green before this work, and the reconciled tree is no worse
than either side: it carries the same shared pre-existing failures, the same
main-side documentation drift, and one upstream failure repaired.

## 6. Publication

The reconciliation commit was created on its own isolated branch and local
`main` was fast-forwarded onto it through a normal Git fast-forward — no
history rewrite, no raw ref update. Publication to `origin/main` is a
fast-forward for the remote, because the upstream tip `bceac5b57…` is a parent
of the reconciliation commit. No force was used.

Both histories are reachable from the published tip: the 8 upstream commits and
all 44 local-main commits are ancestors of it.

## 7. Remaining release gaps

- **Release-truth document drift.** Local main's `00-current-state.md` remains
  non-compliant with `tests/evidence_packets/release_truth_contract.py` in the
  two phrases identified in §5. The remedy is a bounded documentation
  correction to that file — restoring the lowercase
  ``the release gate remains `HOLD` `` form and the `not default Beta support`
  phrase in their owning sections. That file is owned by the weekly
  current-state refresh cadence and was not modified by this reconciliation.
- **Four inherited `test_scout_app_mount.py` failures** are present on both
  sides and are unrelated to this work.
- **Three inherited migration-head assertions** (expecting the historical
  revision `2e865c4a9b10`) remain deferred as a separate bounded correction.
- **Docker engine unavailable.** The engine socket accepts connections and
  then returns zero bytes; no container-path PostgreSQL proof exists. All
  database evidence here comes from the native scratch cluster.
- **No supported-Compose qualification, no browser qualification.**
- **Full backend qualification is not claimed.** Only the five Saved Widget
  contract suites and the four upstream-touched files were executed here.
- **Saved Widget remains storage only.** The `00-current-state.md` declaration
  that the storage foundation is implemented while its user-facing lifecycle
  remains unimplemented is unchanged and still accurate. No human-promotion
  authority was added.

## 8. Disposition

**GO** — publish.

Every publication gate passed: divergence measured, both histories preserved
without rewrite, the merged tree conflict-free with upstream's files
byte-identical and local main's tree fully preserved, exactly one Alembic head
intact, the five Saved Widget contract suites green with zero skips, and
disposable database isolation and cleanup proven.

The reconciled tree introduces no new defect; it repairs one upstream failure
and makes one pre-existing main-side documentation drift visible through
additional detectors. That drift is recorded above as a bounded follow-up and
does not bear on the Saved Widget handoff.

`main` was not force-updated, no history was rewritten, and the release gate
remains `HOLD`.
