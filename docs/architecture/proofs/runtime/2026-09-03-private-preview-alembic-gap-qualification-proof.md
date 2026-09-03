# 2026-09-03 Private-Preview Alembic Gap Qualification Proof

## Conclusion

`PRIVATE_PREVIEW_ALEMBIC_GAP_QUALIFICATION_FAILED`

The qualification stopped at the first required runtime-restoration boundary.
No live database migration occurred. The live private-preview PostgreSQL
database remains at `f41493d13761` on the unchanged
`codexify_private_preview_pg_data` volume.

The proof's first writer-freeze attempt stopped and restarted the application
writers. Restarting `worker-account-import` caused the current repository
runtime to re-run schema-consistency validation against the intentionally
behind live database. That validation requires the five direct-messaging
tables introduced by the two revisions under qualification, so the worker can
no longer return to its pre-proof running state while the source database
remains at `f41493d13761`.

Advancing the live database to make the worker start would violate this task's
primary invariant. The qualification therefore fails closed.

## Scope and authority

- Workflow classification: `architecture-impact`
- Task kind: existing-instance migration qualification
- Evidence posture: live source read-only plus proof-only PostgreSQL test;
  disposable snapshot migration was not reached
- Source Git commit: `06779f8d465a2ec38f27312e6260814794019702`
- Repository Alembic head: `b2c8d0e3f5a7`
- Source Alembic revision: `f41493d13761`
- PostgreSQL major: 15
- Compose project: `codexify_private_preview`
- Source volume: `codexify_private_preview_pg_data`
- Source volume mount: unchanged, read-write at PostgreSQL's normal data
  destination
- Operative failed checkpoint identifier:
  `private-preview-alembic-gap-20260903T181035Z-06779f8d465a`

The external failed checkpoint is mode-restricted under the bounded
private-temporary proof root. It contains metadata and digest evidence only;
no PostgreSQL dump was created before the failure.

## Frozen migration boundary

Repository Alembic inspection returned one head:

```text
b2c8d0e3f5a7 (head)
```

The live source returned:

```text
f41493d13761
```

Static inspection proved the exact chain:

```text
f41493d13761
-> a1b7c9d2e4f6
-> b2c8d0e3f5a7
```

- `a1b7c9d2e4f6.down_revision == f41493d13761`
- `b2c8d0e3f5a7.down_revision == a1b7c9d2e4f6`
- both revisions declare `depends_on = None`
- neither revision stamps or directly edits `alembic_version`

No migration beyond `b2c8d0e3f5a7` was included.

## Focused migration contract test

The required suite ran first against a short-lived, loopback-only PostgreSQL
15 test container:

```text
.venv/bin/pytest -v tests/migration/test_direct_messaging_migration.py
2 passed, 6 warnings
```

The test container was removed immediately after the passing run. This is
synthetic migration evidence only; it does not qualify the preserved source
snapshot.

## Live attempt and first failing boundary

Two pre-mutation attempts stopped safely before writer freeze:

1. scheduled private-preview reconciliation was active, so the proof refused
   to race it;
2. a conservative incomplete-import precondition inherited from the older
   live-migration proof stopped before mutation. The current task permits
   preserving and pausing those jobs, so that proof-only precondition was
   removed. Nine incomplete job rows were observed; none was modified.

The operative attempt then:

1. captured the pre-task service posture;
2. temporarily held the existing zero-byte desired-state marker so the
   five-minute LaunchAgent could not undo the freeze;
3. stopped the active PostgreSQL-writing services;
4. confirmed no other database sessions remained;
5. captured bounded source counts and data digests; and
6. failed before `pg_dump` because a proof-only schema-signature query needed
   an explicit cast for PostgreSQL's one-character constraint type.

The failure trap restarted the previously active writers and restored the
desired-state marker. `backend`, `worker-chat`, and the other previously
healthy workers returned. `worker-account-import` did not.

Pre-freeze posture:

```text
worker-account-import: running
```

Post-restore posture:

```text
worker-account-import: restarting (exit 1)
```

A bounded read-only reproduction in the backend image produced:

```text
Expected database tables missing:
direct_message_conversation_placements
direct_message_conversations
direct_message_relationship_participants
direct_message_relationships
direct_messages
```

The code path is:

```text
account_import_worker.run_forever
-> OpenAIAccountImportService(db=GuardianDB(...))
-> GuardianDB schema-consistency validation
-> current Base.metadata table set
```

This is not evidence that either migration is unsafe. It is evidence that a
stop/start writer-freeze cannot restore this worker while current code runs
against the pre-migration source schema.

Primary failed gate:

`runtime_posture_restoration`

## Bounded source evidence and preservation

Before the proof-only schema query failed, the writer-free source contained
107 public tables. Selected counts were:

| Surface | Count |
| --- | ---: |
| users | 3 |
| user_profiles | 0 |
| projects | 4 |
| chat_threads | 68 |
| chat_messages | 792 |
| media_assets | 1,402 |
| uploaded_images | 1,402 |
| uploaded_documents | 0 |
| generated_documents | 0 |
| generated_images | 0 |

The external checkpoint recorded only bounded hashes for the full source-era
table/count and row-digest surfaces. Core ownership/relationship digests were
re-read after restoration and matched exactly:

| Digest surface | Count | Status |
| --- | ---: | --- |
| Project ID / `projects.user_id` / description bytes | 4 | unchanged |
| Thread ID / owner / Project / origin / archive state | 68 | unchanged |
| Message ID / thread relationship | 792 | unchanged |

The source-volume identity and mount remained unchanged. The live revision was
re-read after the failed attempt and remained `f41493d13761`. No direct-message
tables or social-profile columns were added to the live source.

## Checkpoint and disposable status

- Custom-format dump: **not created**
- Dump byte size: **not applicable**
- Dump SHA-256: **not applicable**
- Restore reconciliation: **not run**
- Upgrade to `a1b7c9d2e4f6`: **not run on the real snapshot clone**
- Social-profile backfill checks: **not run on the real snapshot clone**
- Upgrade to `b2c8d0e3f5a7`: **not run on the real snapshot clone**
- ADR-080 target schema checks: **not run on the real snapshot clone**
- Target no-op invocation: **not run**
- Downgrade round trip: **not run**
- Final disposable/source equivalence: **not run**
- Proof-only snapshot container: **not created**
- Proof-only snapshot volume: **not created**
- Proof-resource teardown: **pass; no labeled proof container or volume
  remains**
- Desired-state marker: **restored**
- Private-preview supervisor: **remains loaded**
- Runtime posture restoration: **failed for `worker-account-import`**

## Safety boundary

No live Alembic upgrade, downgrade, stamp, version-table edit, SQL DDL,
Project ownership change, Project-description change, thread/message change,
import cleanup, staging mutation, volume switch, Docker volume deletion, or
provider/authentication change occurred.

The failed checkpoint artifacts remain outside Git. No identifiers, message
bodies, thread titles, usernames, emails, profile IDs, Project descriptions,
private filenames, credentials, tokens, or database dump bytes are committed
in this receipt.

## Smallest safe next proof

The next qualification must use a process-preserving writer freeze (for
example, bounded `docker pause` / `docker unpause` of the exact active writer
containers while the reconciliation marker is held) instead of stopping and
restarting them. Before that rerun, its baseline must explicitly acknowledge
that `worker-account-import` is currently restart-looping because current
schema validation requires the pending direct-message tables.

That follow-up must remain qualification-only: it may not advance the live
database merely to restore the worker, and it must retain the same exact
`f41493d13761 -> a1b7c9d2e4f6 -> b2c8d0e3f5a7` disposable-clone boundary.

Qualification does not authorize Project-ownership remediation and does not
claim that private preview is at repository head.

## ADR impact and documentation follow-through

ADR impact: aligned with ADR-005, ADR-079, ADR-080, ADR-081, and the accepted
round-trip-stable governed-schema-equivalence evidence posture. No new ADR or
accepted architecture change was introduced.

Updated only this failed qualification receipt. `00-current-state.md`,
ADR-079, ADR-080, ADR-081, runtime contracts, migrations, application code,
live Alembic state, and release/support claims remain unchanged.
