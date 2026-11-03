# Saved Widget Current-Upstream PostgreSQL 16.15 Qualification - 2026-10-28

**Result: PASS (database migration topology, storage, consent, and E5 provenance only).**

- **Evaluated source commit:** `766ddf2075a1e277f0c780792290736a9cc13198` (`origin/main` at evaluation)
- **Proof class:** disposable native PostgreSQL migration, storage, consent, and E5 provenance
- **Execution date:** 2026-10-28
- **Server:** PostgreSQL `16.15 (Debian 16.15-1.pgdg13+2)`, `aarch64-unknown-linux-gnu`, official `postgres:16.15` image
- **Test outcome:** **149 passed, 0 failed, 0 skipped**, 112 nonfatal warnings, in 126.37 seconds
- **Alembic heads at the evaluated commit:** exactly one — `3a91d7c4e8b2`
- **Release interpretation:** no change. This qualifies the current upstream migration topology for the Saved Widget persistence and validation seams. It does not qualify the Saved Widget product lifecycle, browser behavior, or the supported Compose Beta profile.

## Scope and relationship to the earlier qualification

This receipt qualifies the **current upstream** migration topology. It is a distinct proof from `docs/architecture/proofs/runtime/2026-10-28-saved-widget-postgresql-qualification.md`, which qualified a **different** topology at a **different** evaluated SHA, and both stand independently.

| | Earlier qualification | This qualification |
| --- | --- | --- |
| Evaluated SHA | `3571556894c3707069b3e0c348e8eb5049efb243` | `766ddf2075a1e277f0c780792290736a9cc13198` |
| Topology | linear `f0d7c4b2a198 -> c59e4d1a28f0 -> a6b9d2e4f701` | merge-head, single head `3a91d7c4e8b2` |
| `a6b9d2e4f701` blob | `4ba8fb09226c1e7633d0cf8b197bd66e6f89b425`, `down_revision = "c59e4d1a28f0"` | `adcd6e4529324118206cd691a52db0b9e343f1b3`, `down_revision = "f0d7c4b2a198"` |
| Head resolution | chain linearized by the integration branch | saved-widget/consent heads merged by revision `7f2c9e1a4b63`, then unified with the read-cursor branch by `3a91d7c4e8b2` |
| Suites | 5 | 7 (the earlier 5 plus upstream's two merge-head suites) |
| Outcome | 141 passed, 0 failed, 0 skipped | **149 passed, 0 failed, 0 skipped** |

The earlier receipt's claim remains scoped to the SHA it names. It is **not** evidence for this topology, and this receipt is **not** a re-run of that work.

## Verified merge-head ancestry

The asserted ancestry at the evaluated commit, read from Alembic itself:

```text
2e865c4a9b10, a7b9c4d2e6f1, c7f4a9b2e6d1 -> f0d7c4b2a198 (mergepoint)
f0d7c4b2a198 -> a6b9d2e4f701 (branchpoint)   Add canonical Saved Widget identity and immutable revision storage.
f0d7c4b2a198 -> c59e4d1a28f0                add automatic memory suggestions consent to user_settings
a6b9d2e4f701 -> b3c8d1e5f7a2                Add recipient-local direct message read cursors.
a6b9d2e4f701, c59e4d1a28f0 -> 7f2c9e1a4b63 (mergepoint)   merge saved widget and memory consent heads
7f2c9e1a4b63, b3c8d1e5f7a2 -> 3a91d7c4e8b2 (head) (mergepoint)   Merge the read-cursor branch into the unified Saved Widget / consent head.
```

```sh
/Volumes/Dev_SSD/Codexify-main/.venv/bin/python -m alembic -c backend/alembic.ini heads
# 3a91d7c4e8b2 (head)
```

**Exactly one head.** No second head and no dangling branch point. The saved-widget and automatic-memory-consent revisions are joined by an explicit merge revision rather than by a rewritten linear chain, and the read-cursor branch is merged into the same unified head.

## Evaluated tree identity

The qualification ran against a tree exported directly from the evaluated commit:

```sh
git archive 766ddf2075a1e277f0c780792290736a9cc13198 | tar -x -C <export>
```

Every tracked file present in the export matches the commit's blob, except three files that this environment cannot materialise:

```text
.claude/commands/repo-map.md
.claude/commands/runtime-check.md
.claude/commands/task-report.md
```

Those three are agent tooling files. They are not imported by any qualified suite, and no qualified suite reads them. Blob identity was confirmed for every file the proof depends on, including `a6b9d2e4f701`, `7f2c9e1a4b63`, `3a91d7c4e8b2`, `guardian/db/models.py`, `tests/db/conftest.py`, and `tests/db/test_saved_widget_consent_head_merge.py`.

The shared marker corpus `docs/architecture/generative-ui-marker-corpus.json` was materialised at **11,456 bytes**, matching the size asserted by the earlier qualification receipt. The only other files present in the export beyond the commit's tracked set are `.pytest_cache` and `__pycache__` artifacts produced by the test run itself.

## Database isolation

The proof used a **dedicated, disposable** PostgreSQL instance, created for this task alone and removed afterwards.

| Property | Value |
| --- | --- |
| Image | `postgres:16.15`, digest `sha256:1beaa3084eee2676f20a9cd9928f0bf2c5bf674f8e49f81017912183d377c61c` |
| Container | `cfy-pg-qual-16-15` |
| Bind | `127.0.0.1:55449` (loopback only) |
| Lifecycle | started for the run, `docker rm -f` afterwards, port verified closed |

The only connection authority supplied to the test runner was:

```sh
export TEST_DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:55449/postgres
unset DATABASE_URL GUARDIAN_DATABASE_URL
export PYTHONPATH="<export>"
```

No serving or production PostgreSQL URL was used. The suites generated unique disposable database names from `TEST_DATABASE_URL`, applied repository Alembic migrations, and dropped their test databases afterwards. The SQL inventory after the suites showed only `postgres`, `template0`, and `template1`.

The two pre-existing PostgreSQL clusters on ports `55432` and `55433` were never connected to by this proof, and were verified still up and serving their own databases after the run. The host's running Codexify worker containers were not affected.

### Why a container rather than a native cluster

A native cluster could not be created in the execution sandbox. The sandbox denies `shmget` with `IPC_EXCL` — the flag PostgreSQL's shared-memory path requires — and denies `shm_open` for POSIX shared memory, so `initdb` fails during bootstrap with `could not create shared memory segment`. A container receives its own IPC namespace, in which the shared-memory allocation succeeds. This is an environment constraint, not a property of the repository, and it changes only where the server runs — not the server version, the schema, or any assertion.

## Executed qualification

From the exported tree at the exact evaluated SHA, using the repository's existing Python 3.12 virtual environment:

```sh
env -u DATABASE_URL -u GUARDIAN_DATABASE_URL \
  TEST_DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:55449/postgres \
  PYTHONPATH="<export>" \
  /Volumes/Dev_SSD/Codexify-main/.venv/bin/python -m pytest -v -ra -o addopts='' \
  tests/db/test_saved_widget_storage_migration.py \
  tests/db/test_saved_widget_revision_store.py \
  tests/db/test_saved_widget_validation_provenance.py \
  tests/db/test_automatic_memory_consent_migration.py \
  tests/db/test_saved_widget_consent_head_merge.py \
  tests/migration/test_read_state_main_head_merge.py \
  tests/core/test_saved_widget_validation.py
```

| Suite | Passed | Failed | Skipped | Scope |
| --- | ---: | ---: | ---: | --- |
| `tests/db/test_saved_widget_storage_migration.py` | 9 | 0 | 0 | Alembic ancestry against the merge-head topology, DDL constraints, ORM parity, upgrade/downgrade/re-upgrade |
| `tests/db/test_saved_widget_revision_store.py` | 30 | 0 | 0 | Account-owned widget identity, immutable snapshots, revision concurrency/conflicts, rollback, tombstones, source-thread independence |
| `tests/db/test_saved_widget_validation_provenance.py` | 16 | 0 | 0 | Server-owned E5 completion-attempt evidence, rejected unaccepted/failed/cancelled provenance, cross-account isolation |
| `tests/db/test_automatic_memory_consent_migration.py` | 7 | 0 | 0 | Consent migration, defaults, constraints, durable readback, cross-account separation |
| `tests/db/test_saved_widget_consent_head_merge.py` | 6 | 0 | 0 | Saved-widget / consent head merge revision `7f2c9e1a4b63` |
| `tests/migration/test_read_state_main_head_merge.py` | 6 | 0 | 0 | Unified head merge revision `3a91d7c4e8b2` |
| `tests/core/test_saved_widget_validation.py` | 75 | 0 | 0 | Artifact parser/eligibility, E4 dependency rejection, shared cross-language marker corpus |
| **Total** | **149** | **0** | **0** | |

The run's output log, 20,657 bytes, has SHA-256:

```text
aef69d8571ea9cb73809367c788feae4d62f0561f496285becc6f529105f7fab
```

No test was skipped, and no skip was counted as success.

### Corroborating run

Before the evaluated commit, the same seven suites were run against `4791f219d1b872a7d55384767f5c8ba2df5f3060`, the immediately preceding `origin/main`. That commit changed neither the migration topology nor any of the seven suites, and the run produced the identical outcome: **149 passed, 0 failed, 0 skipped** in 146.64 seconds. The evaluated commit was chosen because it additionally introduces `tests/db/conftest.py`, a logging-isolation fixture that is autouse for the `tests/db` suites; the run was repeated at that commit rather than carried over.

### Warnings

112 nonfatal warnings were emitted. They comprise Alembic's `prepend_sys_path` deprecation notice, raised once per Alembic configuration load across the six database-backed suites, and one pre-existing SQLAlchemy relationship-overlap warning on `MemoryRecord.project` that is unrelated to Saved Widget. No warning was used to justify an out-of-scope application change.

## Authority, ADR and release boundaries

**ADR impact:** aligned with accepted ADR-102; no new ADR and no architecture change. This is evidence for the internal Saved Widget persistence and validation seams against the topology that is actually published. It does not change `docs/architecture/00-current-state.md`, the Beta release HOLD posture, or ADR-069's supported-path evidence boundary.

**Not proven:** human save action, authoritative listing, cross-thread invocation, conversational revision editing, deletion execution behavior, account export/restore of widgets, Library Widgets filter availability, browser/Web Audio/canvas compatibility, or full local Docker Compose runtime qualification.

**Files changed:** this proof receipt only. No application source, migration, test, or configuration file was edited.

## Remaining open gates

This receipt closes the current-upstream PostgreSQL proof gate. The following remain open and are **not** closed by it:

- **Browser qualification.** The Playwright navigation-containment spec was not executed here; Chromium cannot launch in the execution sandbox. The existing receipt `docs/architecture/proofs/runtime/2026-10-26-generative-ui-navigation-containment-proof.md` remains the browser evidence for the containment boundary.
- **User-facing Saved Widget lifecycle.** Not implemented. The foundation is ready for code review; the product is not finished. The meaningful next capability is an explicit, account-authorized promotion path that lets a person actually save a generated widget.
