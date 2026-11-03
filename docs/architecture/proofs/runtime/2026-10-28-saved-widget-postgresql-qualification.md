# Saved Widget PostgreSQL 16.15 Qualification - 2026-10-28

**Result: PASS (focused database and eligibility proof only).**

- **Evaluated source commit:** `3571556894c3707069b3e0c348e8eb5049efb243`
- **Proof class:** disposable native PostgreSQL migration, storage, consent, and E5 provenance
- **Execution date:** 2026-10-28 (UTC evidence checkpoint: `2026-10-28T15:26:54Z`)
- **Host:** macOS arm64; PostgreSQL `16.15 (Postgres.app)`
- **Test outcome:** **141 passed, 0 failed, 0 skipped**, 71 nonfatal warnings, in 116.66 seconds
- **Release interpretation:** no change. This does not qualify Saved Widget product lifecycle or the supported Compose Beta profile.

## Isolation and database preflight

The proof used a newly initialized PostgreSQL 16.15 cluster, exclusively for this task, bound to `127.0.0.1:55449`. Its separate data directory was `/tmp/cfy-sw-357155-gJYyas/data`. The native binary and SQL `server_version` both identified Postgres.app 16.15. `pg_isready` confirmed the isolated server accepted connections before tests.

The only connection authority supplied to the test runner was:

```sh
export TEST_DATABASE_URL=postgresql://postgres@127.0.0.1:55449/postgres
unset DATABASE_URL GUARDIAN_DATABASE_URL
export PYTHONPATH="$PWD"
```

No serving/production PostgreSQL URL was used. The suites generated unique disposable database names from `TEST_DATABASE_URL`, applied repository Alembic migrations, and dropped their test databases afterward. SQL inventory before and after the suites showed only `postgres`, `template0`, and `template1`. Other already-running PostgreSQL test clusters on ports 55432 and 55433 were left untouched. After readback, this task's port 55449 cluster was stopped and verified unavailable.

A host-level preflight issue initially blocked `initdb`: all 32 macOS System V shared-memory IDs were occupied, producing `shmget: No space left on device`. Inspection found ten anonymous segments owned by the local account with zero attachments, zero last-attached PID, and exited creator PIDs. Only those ten verified orphan IDs were reclaimed. `initdb` and server startup then succeeded. No kernel limit, application code, or active PostgreSQL process was modified.

## Executed qualification

From the detached worktree checked out at the exact evaluated SHA, using the repository's existing Python 3.12 virtual environment:

```sh
/Volumes/Dev_SSD/Codexify-main/.venv/bin/python -m pytest -v -ra -o addopts='' \
  tests/db/test_saved_widget_storage_migration.py \
  tests/db/test_saved_widget_revision_store.py \
  tests/db/test_saved_widget_validation_provenance.py \
  tests/db/test_automatic_memory_consent_migration.py \
  tests/core/test_saved_widget_validation.py
```

| Suite | Passed | Failed | Skipped | Scope |
| --- | ---: | ---: | ---: | --- |
| `tests/db/test_saved_widget_storage_migration.py` | 13 | 0 | 0 | Alembic ancestry, single head, DDL constraints, ORM parity, upgrade/downgrade/re-upgrade, chat/consent preservation |
| `tests/db/test_saved_widget_revision_store.py` | 30 | 0 | 0 | Account-owned widget identity, immutable snapshots, revision concurrency/conflicts, rollback, tombstones, source-thread independence |
| `tests/db/test_saved_widget_validation_provenance.py` | 16 | 0 | 0 | Server-owned E5 completion-attempt evidence, rejected unaccepted/failed/cancelled provenance, cross-account isolation |
| `tests/db/test_automatic_memory_consent_migration.py` | 7 | 0 | 0 | Consent migration, defaults, constraints, durable readback, cross-account separation |
| `tests/core/test_saved_widget_validation.py` | 75 | 0 | 0 | Artifact parser/eligibility, E4 dependency rejection, shared cross-language marker corpus |
| **Total** | **141** | **0** | **0** | |

The asserted canonical migration ancestry is:

```text
f0d7c4b2a198 -> c59e4d1a28f0 -> a6b9d2e4f701
```

The structural migration tests are not gated behind a PostgreSQL fixture; the database-backed portions ran against the isolated live server. Skips were not counted as success.

### Initial attempt and corrected test environment

The initial five-suite run yielded `140 passed, 1 failed, 0 skipped`. Its sole failure was `test_shared_corpus_cases_parse_the_same_way_the_frontend_expects`: the detached worktree contained an unhydrated Git LFS pointer instead of `docs/architecture/generative-ui-marker-corpus.json`. The fixture was materialized from the local Git LFS object store with `git lfs checkout`. The resulting file was valid JSON (11,456 bytes), the isolated failing test passed, and the entire five-suite command was rerun successfully. `git status` confirmed that hydration did not alter tracked source.

The successful rerun's output was captured to a task-local log with SHA-256:

```text
9295e294cc09535415524826e93ff9ef9feab76ff40081431e05e1fb90e52d74
```

The 71 warnings consisted of Alembic's legacy `prepend_sys_path` deprecation and one existing SQLAlchemy relationship-overlap warning. There were no failed or skipped tests. These warnings were not used to justify out-of-scope application changes.

## Authority, ADR and release boundaries

**ADR impact:** aligned with accepted ADR-102; no new ADR or architecture change. This is evidence for the internal Saved Widget persistence and validation seams, not an authorization or implementation of a user-facing promotion path. It does not change `docs/architecture/00-current-state.md`, the Beta release HOLD posture, or ADR-069's supported-path evidence boundary.

**Not proven:** human save action, authoritative listing, cross-thread invocation, conversational revision editing, deletion execution behavior, account export/restore of widgets, Library Widgets filter availability, browser/Web Audio/canvas compatibility, or full local Docker Compose runtime qualification.

**Files changed:** this proof receipt only. No application source, migration, test, or configuration file was edited.
