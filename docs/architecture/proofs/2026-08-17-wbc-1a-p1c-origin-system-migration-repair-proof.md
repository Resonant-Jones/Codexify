# WBC-1A-P1C — Psycopg3 conversation-origin migration repair proof

## Purpose

WBC-1A-P1B stopped at its first required startup boundary: the audit
project's `migrator` exited `1` while applying revision `1c0a2b3c4d5e`.
PostgreSQL via psycopg rejected the backfill query at `IN $1` with
`psycopg.errors.SyntaxError: syntax error at or near "$1"`. P1B correctly
did not repair its database, stamp a revision, or proceed to chat/runtime
qualification.

This proof repairs that one not-yet-applied migration body and proves the
normal Alembic upgrade on a real disposable PostgreSQL database using psycopg
v3. It is not a WBC-1A rerun and does not qualify chat, provider, worker, or
canonical live-proof behavior.

## Authority, lineage, and migration-history posture

| Item | Observation |
| --- | --- |
| Proof checkout | `/Users/chriscastillo/.codex/worktrees/dda8/Codexify-main` |
| Branch / pre-edit HEAD | `codex/freeze-workspace-baseline-truth` / `a955fc90b159d57032d9afb8af278e162164148b` |
| `origin/main` after `git fetch origin` | `eb6bdc530245fdffeff23589c98389be4102b564` |
| Merge base with `origin/main` | `eb6bdc530245fdffeff23589c98389be4102b564` |
| Frozen WBC target baseline | `eb6bdc530245fdffeff23589c98389be4102b564` |
| G0 truth-freeze workspace commit | `08c9e8ae64bb4239a600e00beb5db041da1025b0` |
| G0 truth-freeze ancestry | `git merge-base --is-ancestor 08c9e8 HEAD` exited `0` |
| Pre-edit checkout state | clean |
| Migration revision / parent | `1c0a2b3c4d5e` / `9d4c2a7e1b6f` |
| Migration-history search | `git log --all -- <migration>` found only `f4fece599 Establish canonical conversation origin system` |

The storage contract requires schema/history reconciliation through normal
Alembic execution and version advancement; stamping, direct
`alembic_version` edits, and manual schema repair are not substitutes. That
governs this repair.

Read-only inspection of the P1B audit database returned
`alembic_version=absent` and `chat_threads=absent` both before and after this
task. This is consistent with transactional rollback of the failed clean-start
upgrade. Repository evidence search located only the P1B failure receipt, not
a successful durable application of this revision. No claim is made about
unobserved environments outside the authorized evidence scope.

Accordingly, the task's narrow correction of the failed, unrecorded revision
body is authorized by its migration-history rule. It preserves the revision
identifier, parent, upgrade intent, canonical token registry, provenance
semantics, and fail-closed downgrade; it does not add a replacement or merge
revision.

## P1B audit-environment preservation

The `codexify-audit` project remained an observation endpoint only:

- no direct audit-database SQL repair, Alembic stamp, schema alteration, or
  corrected migration application was performed;
- no Compose/profile/environment/provider change was made;
- no cloud-provider credentials or provider activation was added; and
- no WBC chat request, turn-lock exercise, queue task, worker proof, or
  canonical collector rerun occurred.

The prior P1B receipt remains the evidence for the migration/init first
boundary and its exact failure signature. This task uses an isolated database
on the audit project's local PostgreSQL network solely because that server was
available for a disposable proof.

## Repair

The former statement passed each legacy token tuple as one normal bind value:

```python
WHEN metadata->>'import_source' IN :openai_tokens THEN 'openai'
```

With psycopg3/PostgreSQL that reached the server as the invalid `IN $1`
shape. The corrected statement declares both token binds with
`sa.bindparam(..., expanding=True)` and passes the existing bounded tuples as
execution values. SQLAlchemy now expands the values into the `IN (...)`
expression before psycopg3 executes the query.

No mapping changed:

| Historical `metadata.import_source` | Canonical `origin_system` |
| --- | --- |
| `chatgpt`, `openai` | `openai` |
| `claude`, `anthropic` | `anthropic` |
| absent, `NULL`, unrelated value | `codexify` |

The migration continues to preserve `metadata` without rewrite; the column
remains `VARCHAR(32) NOT NULL DEFAULT 'codexify'`, with
`ck_chat_threads_origin_system_canonical`, index
`ix_chat_threads_user_origin` on `(user_id, origin_system)`, and its original
fail-closed downgrade.

## Disposable PostgreSQL / psycopg3 proof

The regression test is
`tests/db/test_chat_thread_origin_system_migration.py`. It requires
`TEST_DATABASE_URL` or `DATABASE_URL`, creates a UUID-suffixed
`codexify_origin_system_*` database through psycopg, and terminates remaining
connections before dropping that database in `finally`.

The executed runner was a transient container from
`codexify-backend-runtime:latest`, with the proof checkout mounted read-only
at `/workspace`, attached to `codexify-audit_default`, and with the service
entrypoint disabled. Its non-secret dependency probe reported:

```text
alembic=1.17.0 psycopg=3.3.4
```

The effective test command was:

```text
TEST_DATABASE_URL=<derived non-secret-redacted local Postgres URL> \
docker run --rm --entrypoint python --network codexify-audit_default \
  -v "$PWD:/workspace:ro" -w /workspace \
  codexify-backend-runtime:latest \
  -m pytest -q tests/db/test_chat_thread_origin_system_migration.py
```

Result: `1 passed`.

The test performed these real PostgreSQL operations through Alembic and the
psycopg3 SQLAlchemy dialect:

1. upgraded an empty disposable database to parent `9d4c2a7e1b6f`;
2. inserted a valid parent `users` row and representative pre-migration
   `chat_threads` rows for `chatgpt`, `openai`, `claude`, `anthropic`, absent
   provenance, and unrelated provenance;
3. upgraded exactly to `1c0a2b3c4d5e`;
4. asserted exact `alembic_version = 1c0a2b3c4d5e`;
5. asserted all six backfill mappings and byte-equivalent JSON meaning for
   each original metadata object;
6. asserted the non-null `VARCHAR(32)` column, effective `codexify` default,
   named CHECK constraint and values, and composite index columns;
7. asserted that the CHECK rejects `origin_system='unsupported'`; and
8. terminated disposable connections and dropped the proof database.

Read-only teardown verification against the audit server returned
`alembic_version=absent|chat_threads=absent` for the untouched audit database
and no remaining `codexify_origin_system_*` database.

## Focused regression and graph checks

| Command | Result |
| --- | --- |
| `.venv/bin/python -m pytest -q tests/db/test_chat_thread_origin_system.py` | `23 passed` |
| disposable psycopg3 test above | `1 passed` |
| `python -m alembic -c backend/alembic.ini heads` in the read-only runner | `1c0a2b3c4d5e (head)` |
| Black check for the new regression test | pass; one file unchanged |
| `.venv/bin/ruff check tests/db/test_chat_thread_origin_system_migration.py` | pass (repository config deprecation warning only) |

The repository-wide Black check still proposes formatting in the existing
migration file because that historical file predates current formatter output.
Its only semantic change in this task is the psycopg3-safe expanding bind;
unrelated formatter and typing modernization was deliberately not mixed into
the migration repair.

## ADR impact

**Aligned with existing ADRs and storage contracts. No architectural decision
changed.**

- ADR-031, Continuity Phase A Storage Migration Gate: real database migration
  proof and provenance/constraint preservation;
- ADR-005, Runtime Mode and Account Boundary Invariants: owner-scoped
  persistence remains intact; and
- ADR-069, Beta Support Boundary: no supported profile, provider, or release
  posture changed.

The governing implementation contracts were
`docs/architecture/data-and-storage.md` (normal Alembic advancement and the
canonical conversation-origin surface),
`docs/architecture/account-export-restore-contract.md` (preserved provenance),
and `docs/architecture/config-and-ops.md` (Postgres migration DSN posture).

## Limits and handoff

- This proof does not apply the corrected revision to `codexify-audit`; that
  must wait until this committed source is landed on canonical `main`.
- It does not rerun WBC-1A-P1B, invoke the canonical live-proof collector, or
  make any runtime eligibility claim.
- It does not run the turn-lock test, repair turn-lock behavior, or start a
  chat lifecycle.
- It does not create another migration revision or alter migration history.
- No secret values appear in this proof.

## Result

`MIGRATION_REPAIR_PROVEN`

WBC-1A-P1C PROVEN — land migration repair on canonical main, then rerun WBC-1A-P1B.
