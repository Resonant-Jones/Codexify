# Tester Chat-Message Sequence Migration Proof

Date: 2026-07-29

## Final outcome

`FAILED`

The supported tester migration command did not apply the pending Alembic revisions. It stopped at revision `7a91c4e2f6b8` because PostgreSQL reported that `chat_messages.hosted_room_participant_id` already existed. The tester database therefore remains below repository head `8c4d2e7f1a9b`, and Task 9K is not ready.

## Tested repository state

- Branch state: detached `HEAD`
- Tested repository commit: `e6f78f1292fa1dc120ad56b6f3a67e77e7c61347`
- Repository Alembic head: `8c4d2e7f1a9b`
- The sequence-repair commit is an ancestor of the tested commit.
- Worktree was clean before the proof receipt was created.

The local Alembic graph is linear through the relevant revisions:

`b2c3d4e5f6a7 -> 7a91c4e2f6b8 -> 8b02d5f3a7c9 -> 8c4d2e7f1a9b`

No duplicate-revision warning was emitted by the repository `alembic heads` check.

## Tester environment

- Compose project: `codexify_tester`
- Database service: `db`
- One-shot migration service: `migrator`
- The database was already running and healthy.
- Application and worker services were not restarted for this proof.

## Pre-migration database state

Read-only inspection before the migration attempt showed:

- `alembic_version`: `b2c3d4e5f6a7`
- `MAX(chat_messages.id)`: `112455`
- `chat_messages_id_seq.last_value`: `112455`
- `chat_messages_id_seq.is_called`: `true`
- Serial sequence: `public.chat_messages_id_seq`
- Sequence ownership: `public.chat_messages_id_seq` owns `public.chat_messages.id`
- Both Hosted Room provenance columns already existed.

## Supported migration path

The supported one-shot path was used exactly once:

```text
docker compose --env-file .env.tester -p codexify_tester \
  -f docker-compose.yml -f docker-compose.tester.yml \
  run --rm migrator
```

This uses the repository migrator service and its Alembic `upgrade heads` entrypoint. No manual migration SQL, version stamping, sequence stamping, or sequence reset was used.

## Migration result

The migrator exited non-zero while applying `7a91c4e2f6b8_add_hosted_room_message_provenance.py`. PostgreSQL rejected the attempted addition of the already-existing `hosted_room_participant_id` column with a duplicate-column error. The command stopped at that failure; no retry or repair was attempted.

## Post-failure database state

Read-only inspection after the failed attempt showed:

- `alembic_version`: `b2c3d4e5f6a7`
- `MAX(chat_messages.id)`: `112455`
- `chat_messages_id_seq.last_value`: `112455`
- `chat_messages_id_seq.is_called`: `true`
- Serial sequence: `public.chat_messages_id_seq`
- Sequence ownership: `public.chat_messages_id_seq` owns `public.chat_messages.id`
- Both Hosted Room provenance columns remain present.
- No active Alembic or sequence-reset activity remained after excluding the inspection connection.

The failed migration did not advance the database revision or alter the observed sequence state.

## Generated-ID insert proof

Not run. The task requires the migration to succeed before generated-ID inserts are used as proof. No rows were inserted, no data was deleted, and no sequence value was manually changed.

## Tester health and route observation

`make tester-status` passed after the failed migration attempt. The database, backend, Redis, Neo4j, frontend, chat workers, account-import worker, and tester Tailscale service were running; required health checks reported healthy. Backend and chat health reported normally, with chat message count `112455`.

The backend OpenAPI document was reachable and exposed the existing Hosted Room route surface, including room creation, room messages, invitations, session messages, and invocation paths. This route observation is informational only and is not a Task 9K invocation or lifecycle proof.

## Privacy review

The receipt contains no credentials, cookies, invitation values, database URLs, or session values. The migration stack trace was reduced to its bounded revision and duplicate-column error; host paths and connection details were omitted.

## Cleanup

The one-shot migrator was run with `--rm` and was removed after exit. No unrelated service was restarted. No repository source, test, configuration, ORM, migration, worker, route, task-schema, or frontend file was modified.

## Task 9K readiness decision

`NEXT-PROOF-NEEDED`

Task 9K is not ready. A separately authorized migration-reconciliation task must reconcile the tester database's pre-existing provenance columns with Alembic history before this migration can be rerun. Task 9K duplicate-identity and lifecycle gates were not run.

## Commands executed

The proof included these command classes:

- repository status, detached-HEAD, ancestry, and Alembic graph checks;
- `make tester-status`;
- the supported `docker compose ... run --rm migrator` command above;
- read-only PostgreSQL checks for Alembic version, maximum message ID, sequence synchronization, sequence ownership, provenance columns, and active migration activity;
- OpenAPI route inspection;
- `venv/bin/python -m pytest -q tests/migration/test_chat_message_sequence_migration.py`;
- documentation and diff hygiene checks.

## Proof receipt commit

This receipt is committed separately with:

`Record tester sequence migration proof`
