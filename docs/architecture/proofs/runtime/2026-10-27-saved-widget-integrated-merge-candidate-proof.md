# Saved Widget / Memory-Consent Integrated Merge Candidate Proof

- **Date:** 2026-10-27
- **Disposition:** **GO** for operator approval to advance `main`
- **Release posture:** HOLD (unchanged)

This receipt qualifies an **isolated integration candidate**. The companion
historical receipt
(`2026-10-27-saved-widget-memory-consent-merge-head-proof.md`) is preserved
unchanged and remains the authoritative record of the repair branch's own
evidence, including the inherited failure it documented at the time.

## 1. Inputs

| | |
|---|---|
| Evaluated main | `df1c60296728d34f1cf740e8f6b8dfee5a0f6110` |
| Repair branch | `fix/saved-widget-memory-consent-alembic-heads-20261027` |
| Repair tip | `50ddacd97e01136ba88890b13985d8471289c93e` |
| Common ancestor | `fb0b4e47aa02144b7222cbbc1049041a3896cf93` |
| Integration branch | `integrate/saved-widget-alembic-heads-20261027` |

`git rev-parse main` was verified to equal the evaluated mainline commit before
any work began, and the main worktree's tracked files were clean. The target
integration branch did not previously exist.

### What each side carries since the common ancestor

`main` changed 11 files, all tests:

```
tests/core/test_completion_terminal_integrity.py
tests/core/test_whooshd_context_bundle_system_identity_delivery.py
tests/evidence_packets/release_truth_contract.py
tests/evidence_packets/test_guardian_evidence_bounded_read.py
tests/evidence_packets/test_guardian_evidence_bounded_read_contract.py
tests/evidence_packets/test_guardian_evidence_bounded_read_fixture.py
tests/evidence_packets/test_guardian_evidence_packet_generator.py
tests/evidence_packets/test_guardian_evidence_packet_generator_contract.py
tests/evidence_packets/test_guardian_evidence_reducer_input_bundle_dry_run_loader_contract.py
tests/evidence_packets/test_guardian_evidence_reducer_input_bundle_template.py
tests/routes/test_agent_orchestration_request_user.py
```

The repair branch changed 3 files:

```
guardian/db/migrations/versions/7f2c9e1a4b63_merge_saved_widget_and_memory_consent_heads.py
tests/db/test_saved_widget_storage_migration.py
docs/architecture/proofs/runtime/2026-10-27-saved-widget-memory-consent-merge-head-proof.md
```

**Path overlap: none.** The two deltas are disjoint, which is why the merge is
conflict-free.

## 2. Merge candidate

The candidate is the two-parent commit on `integrate/saved-widget-alembic-heads-20261027`
whose parents are, in order:

1. `df1c60296728d34f1cf740e8f6b8dfee5a0f6110` (main)
2. `50ddacd97e01136ba88890b13985d8471289c93e` (repair tip)

Its own SHA cannot appear inside this receipt, because the receipt is one of the
files the merge commit introduces; the SHA is recorded in the task closeout.

A normal history-preserving merge was performed without committing:

```
git merge --no-commit --no-ff fix/saved-widget-memory-consent-alembic-heads-20261027
-> Automatic merge went well; stopped before committing as requested
```

Verified at that point:

- `HEAD` was still `df1c6029…` (main was not advanced by the merge)
- `MERGE_HEAD` was `50ddacd97…`
- **Zero conflicts** — `git diff --name-only --diff-filter=U` was empty
- Exactly the three authorized repair paths were staged; nothing else was
  modified or staged

No reset, rebase, amend, or overwrite of any existing work occurred. Neither
input history was rewritten.

## 3. Integrated migration graph

```
$ python -m alembic -c backend/alembic.ini heads
7f2c9e1a4b63 (head)
```

- **Exactly one head.** Head count from `heads` output: 1.
- Migration files in the merged tree: **126** (main's 125 plus the merge revision).
- Convergence: `a6b9d2e4f701, c59e4d1a28f0 -> 7f2c9e1a4b63 (head) (mergepoint)`.
- Lineage contains 126 revisions with **no missing revisions and no duplicate
  revision identifiers**; both predecessor revisions (`a6b9d2e4f701`,
  `c59e4d1a28f0`) and the shared parent (`f0d7c4b2a198`) are all reachable.
- Both original parent migrations are **byte-identical to main**
  (`a6b9d2e4f701_add_saved_widget_identity_and_revisions.py`,
  `c59e4d1a28f0_add_automatic_memory_suggestions_consent.py`).
- The merge revision still declares `down_revision = ('a6b9d2e4f701', 'c59e4d1a28f0')`
  with empty `upgrade()` / `downgrade()` bodies — **no new schema operations**,
  no new product semantics.

## 4. PostgreSQL instance and isolation

- **Instance:** host-native **PostgreSQL 16.2** — not a container
- **data_directory:** `/Volumes/Dev_SSD/Codexify-main/.scratch/pgdata_pg16`,
  verified to sit beneath the approved scratch root before any database was created
- **`listen_addresses`:** `127.0.0.1` (loopback only)
- **Proof role:** `postgres`, superuser (`rolsuper = t`), mirroring `POSTGRES_USER`
  in the official `postgres` image; the disposable fixtures drop their databases
  with `pg_terminate_backend()`, which a lesser role cannot perform
- **`TEST_DATABASE_URL`:** `postgresql://postgres@127.0.0.1:55432/postgres`
- **Concurrent proof run:** none — the shared proof lock `127.0.0.1:59177` was free
  before the run
- **Import origins:** `guardian`, `guardian.core.saved_widget_store`, and
  `guardian.db.models` all resolved inside the integration candidate worktree
- **Production / Private Preview / persistent application DB:** never targeted
- **Docker:** not used, not restarted, no volumes touched

## 5. Targeted suite results

Executed against the merged source tree:

```
python -m pytest -o addopts="" -v -rs \
  tests/db/test_saved_widget_storage_migration.py \
  tests/db/test_saved_widget_revision_store.py \
  tests/core/test_saved_widget_validation.py \
  tests/db/test_saved_widget_validation_provenance.py \
  tests/db/test_automatic_memory_consent_migration.py
```

```
137 passed, 67 warnings in 305.91s (0:05:05)
```

- **Passed: 137**
- **Failed: 0**
- **Errors: 0**
- **Skipped: 0**

The skip count is zero as measured, not assumed: no `SKIPPED` line and no
`N skipped` summary appeared anywhere in the run. Every database-dependent case
executed against disposable PostgreSQL.

This matches the repair branch's own count exactly (137 passed). The merged
candidate therefore introduces **no attributable integrated regression** — the
eleven main-side files are unrelated test modules outside these five suites, and
no path is shared.

Log: `/Volumes/Dev_SSD/Codexify-main/.scratch/saved-widget/logs/integration-candidate/all_five.log`

## 6. Migration path proofs on the merged tree

Three disposable databases, each upgraded from a different valid starting point
to the combined head:

| Starting point | Path | Result |
|---|---|---|
| `f0d7c4b2a198` (shared parent) | -> `head` | **PASS**, `alembic_version = 7f2c9e1a4b63` |
| `a6b9d2e4f701` (saved-widget head) | -> `head` | **PASS**, `alembic_version = 7f2c9e1a4b63` |
| `c59e4d1a28f0` (memory-consent head) | -> `head` | **PASS**, `alembic_version = 7f2c9e1a4b63` |

Both schema families verified present on the migrated database: `saved_widgets`,
`saved_widget_revisions`, the `trg_saved_widget_revisions_immutable` trigger, the
`automatic_memory_suggestions` consent column, the
`user_settings_automatic_memory_suggestions_check` constraint, and the `'unset'`
fail-closed consent default.

This reuses the technique already proven on the repair branch; no additional
migration-testing subsystem was introduced.

### Method note — a harness defect, not a candidate defect

The first invocation of this path prover reported three path failures. The cause
was a defect in the prover itself: it invoked Alembic with the relative path
`-c backend/alembic.ini` but without setting the working directory to the
candidate, so Alembic resolved **main's** `alembic.ini` and loaded main's
two-head graph; `upgrade head` then failed with a multiple-heads error. The
candidate was never implicated, and no candidate file was modified. The prover
was corrected to set `cwd` to the candidate and now refuses to run unless the
resolved `script_location` lies inside the candidate worktree and `heads` is
exactly `('7f2c9e1a4b63',)`. The PASS results above are from the corrected
invocation, whose preflight printed:

```
alembic dir: .../integrate-alembic-heads-20261027/guardian/db/migrations
alembic heads: ('7f2c9e1a4b63',)
```

## 7. Cleanup

- All three path-proof disposable databases dropped: **3 of 3**
- Databases remaining on the disposable server after the run:
  `postgres`, `template0`, `template1`
- Residue matching `mergehead_*`, `codexify_saved_widget*`, or `codexify_consent*`:
  **0**

No named volume, Docker resource, or non-disposable database was modified. No
disk reclamation was performed.

## 8. Evidence boundary

The repair branch's own receipt
(`2026-10-27-saved-widget-memory-consent-merge-head-proof.md`) is committed into
this candidate **byte-unchanged**. Its recorded inherited failure — the stale
hardcoded single-head assertion, reproduced on the pre-repair two-head baseline —
stands as written. It was not edited to present that history as an unbroken pass.

This receipt records only what was observed on the merged candidate, after the
ancestry correction had landed on the repair branch. Nothing here revises the
earlier record.

## 9. Remaining unproven surfaces

A green database-contract proof is not release qualification. Still outstanding:

- **Docker engine unavailable.** The engine socket accepts connections and then
  returns zero bytes; no container-path PostgreSQL proof has been run. All
  database evidence in this receipt comes from the native scratch cluster.
- **No supported-Compose qualification.** The Compose supported path has not been
  exercised for this candidate.
- **No browser or cross-browser qualification.**
- **Saved Widget remains storage only.** The `00-current-state.md` declaration
  that the storage foundation is implemented while its user-facing lifecycle
  remains unimplemented is untouched and still accurate.
- **Inherited DLG validation errors and warnings** are unchanged by this work.
- **No human-promotion authority** was added; none is claimed.

## 10. Disposition

**GO** for explicit operator approval to advance `main`.

Every acceptance gate for this candidate passed: identities verified, no
unauthorized changes, exactly one integrated head, both original migrations
unchanged, all five suites green with zero skips, disposable isolation and
cleanup proven, and a durable receipt committed alongside.

`main` is **not** advanced by this work. The candidate exists only on
`integrate/saved-widget-alembic-heads-20261027`, unpushed. Advancing `main` is a
separate, explicit operator decision.

**Release posture remains HOLD.**
