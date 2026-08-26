# Tester migrator runtime/source coherence proof

## Result

`TESTER_MIGRATOR_RUNTIME_COHERENCE_PASS`

The Tester migrator's failed runtime image was stale. Rebuilding the existing
canonical `migrator` image from the current checkout restored source/runtime
Alembic coherence. No tracked Compose, Dockerfile, migration, or application
source change was needed, and PostgreSQL was not changed.

This is a branch-local packaging/runtime receipt. It does not establish Tester
backend health, worker health, model availability, Watchdog execution, or
current-`main` release truth.

## Source and migration identity

- Source HEAD: `994964a125d2413e127779371488352618c19219`.
- Branch: `codex/diagnose-tester-fresh-chroma-failure`.
- Required predecessor commits `994964a125d2413e127779371488352618c19219`
  and `0ff80e332fa19edea85abc977275bd37fc8d409a` were verified ancestors.
- `.env.tester` is ignored and was not modified.
- Canonical source Alembic head: `6e9f0a1b2c3`.
- Authoritative source migration path, as resolved by
  `backend/alembic.ini`:
  `guardian/db/migrations/versions/6e9f0a1b2c3_add_github_watchdog_review_dispatches.py`.
- Source migration SHA-256:
  `3820e65ae666fc26bb07775bdbe008759c75558cf61fb866b5a36f6b53047207`.
- Migration node: `revision = 6e9f0a1b2c3`,
  `down_revision = 5d8e9f0a1b2c`.

Source Alembic `heads` returned exactly `6e9f0a1b2c3`. Its bounded history
confirmed the relevant chain:

```text
3b7c8d9e0f1a -> 4c7d8e9f0a1b -> 5d8e9f0a1b2c -> 6e9f0a1b2c3 (head)
```

`backend/alembic.ini` sets
`script_location = %(here)s/../guardian/db/migrations`. The migrator binds
only `/app/backend`; it deliberately consumes the baked `/app/guardian` tree.
The shared backend/migrator Dockerfile already copies `guardian` into that
location, and the canonical Compose definition already gives both services the
same `codexify-backend-runtime:latest` build. There was therefore no source
packaging defect to edit.

## Failed runtime inspection and root cause

- Failed migrator container:
  `4dc7b6ff2a70e8821d3b14071f7a6a322488a9163803cbfea0c9d4b2e3576145`.
- State: exited `1`; effective entrypoint `python`; command
  `/app/backend/scripts/docker/run_migrator.py`; working directory `/app`.
- Its sole mount was the backend bind path at `/app/backend`; it had no
  `/app/guardian` mount.
- Failed image ID:
  `sha256:ee3f3fbecbdc20ace36b00b1ce239266a000c303fe797da13e19d0cb469c3d6a`.
- Failed image creation timestamp: `2026-08-24T21:51:22.703052757Z`.
- Failed runtime `backend/alembic.ini` and its resolved Guardian migration
  directory were present, but the `6e9f0a1b2c3` file was absent.
- Failed runtime Alembic head: `d2e3f4a5b6c7`; resolving `6e9f0a1b2c3`
  raised `Can't locate revision identified by '6e9f0a1b2c3'`.

Classification: `STALE_MIGRATOR_IMAGE`.

The image history proves that the runtime bakes `COPY guardian /app/guardian`.
The failed image therefore carried an older baked Guardian migration graph than
the current checkout, while the live database and source had already advanced
to `6e9f0a1b2c3`. The Compose build context, Dockerfile copy path,
`.dockerignore`, image reference, working directory, and Alembic script
location were all coherent.

## Bounded repair and repaired-runtime proof

The only repair was the canonical shared-image rebuild; it did not start,
recreate, or run the backend, `worker-chat`, or a stateful migrator entrypoint:

```text
docker compose --env-file .env.tester -p codexify_tester \
  -f docker-compose.yml -f docker-compose.tester.yml \
  -f docker-compose.whooshd-deepseek.yml build migrator
```

- Repaired image ID:
  `sha256:2508fe43e87e883caea01fe36b5ab5eff3a1d9616d395d7e7903b03204a584cf`.
- Repaired image creation timestamp: `2026-08-25T14:05:41.611173001Z`.
- In an ephemeral canonical Compose `migrator` container with `--no-deps` and
  `--entrypoint python`, the migration file existed and its SHA-256 exactly
  matched source:
  `3820e65ae666fc26bb07775bdbe008759c75558cf61fb866b5a36f6b53047207`.
- That container's resolved script location was
  `/app/backend/../guardian/db/migrations`, its Alembic head was
  `6e9f0a1b2c3`, and its bounded history matched the source chain above.
- `alembic current` in the same read-only command shape reported
  `6e9f0a1b2c3 (head)`.

The normal migrator entrypoint was **not** run. Its current implementation
runs `alembic upgrade heads` and then `seed_defaults.py`; even though the
database was already current, that seed step is stateful. The bounded
`heads`/`history`/`current` proofs were sufficient and performed no migration
or seed operation.

## Durable-state and execution boundaries

The live Tester `alembic_version` was `6e9f0a1b2c3` before and after the image
rebuild and read-only runtime proofs. There was no stamp, manual database
mutation, schema migration, or migration-history rewrite.

The normal chat queue remained depth `0`; durable counts remained `5137` chat
threads, `113328` chat messages, and zero Watchdog attempts, dispatches, and
results. The Chroma fingerprint remained unchanged: `42,588,516` bytes and
`chroma.sqlite3` SHA-256
`602eca12546c7bc177e801f065df87afa6713c3b1a61693450a455fc464a5e46`.

The pre-existing backend container remained `Created` on the failed image and
was not started or recreated. `worker-chat` remained `Created` and was not
started. No chat, local-model, DeepSeek, Watchdog, GitHub, Command Bus, or
Build Loop operation occurred.

## ADR impact and validation

**No ADR change — existing migration/persistence authority restored.**

- Mandatory ancestry, clean-worktree, and `.env.tester` ignore checks passed.
- Source `alembic heads` and bounded `history` passed.
- Failed container/image and read-only failed-image Alembic inspection passed
  and established the stale-image classification before repair.
- The canonical `build migrator` command passed. It emitted only the existing
  optional-unset `LOCAL_VISION_MODEL` and `LOCAL_GGUF_MODEL` warnings.
- Repaired runtime file identity, `heads`, bounded `history`, and read-only
  `current` checks passed.
- Live PostgreSQL revision, queue depth, durable counts, container states, and
  Chroma fingerprint were read back after proof and remained unchanged.
- Canonical Tester Compose render passed with the same optional-model warnings.

No source packaging file changed, so a packaging regression test was not
applicable. `docs/architecture/00-current-state.md` remains untouched.

## Deferred next slice

Rerun the ordinary Tester runtime restoration from the existing durable state:
one canonical backend start, then one normal chat-worker start only if backend
health succeeds, followed by exact configured-model availability
classification. Do not change model authority or resume Watchdog in that
slice.
