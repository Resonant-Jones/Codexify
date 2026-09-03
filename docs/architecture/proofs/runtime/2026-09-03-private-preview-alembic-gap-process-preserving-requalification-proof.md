# 2026-09-03 Private-Preview Alembic Gap Process-Preserving Requalification Proof

## Conclusion

`PRIVATE_PREVIEW_ALEMBIC_GAP_QUALIFIED`

The exact private-preview migration path from `f41493d13761` through
`a1b7c9d2e4f6` to `b2c8d0e3f5a7` passed on a fresh, writer-consistent clone of
the live PostgreSQL 15 database. The target invocation was a stable no-op, and
the disposable database downgraded back to a source-equivalent
`f41493d13761` state.

The live database was not migrated. It remains at `f41493d13761` on the
unchanged `codexify_private_preview_pg_data` volume. The pre-existing
`worker-account-import` schema-mismatch restart loop also remains unchanged in
category; this qualification did not attempt to repair it.

## Scope and authority

- Workflow classification: `architecture-impact`
- Task kind: existing-instance migration requalification
- Evidence posture: live source checkpoint plus proof-only PostgreSQL 15
  restore, exact-target upgrade, no-op, and downgrade evidence
- Branch: `main`
- Source Git commit: `6706fc933009cb51508611e400388cd7e35f7da2`
- Compose project: `codexify_private_preview`
- PostgreSQL major: 15
- Live database: `Codexify`
- Live source revision: `f41493d13761`
- Intermediate revision: `a1b7c9d2e4f6`
- Repository and qualification target: `b2c8d0e3f5a7`
- Live source volume: `codexify_private_preview_pg_data`
- Live database container:
  `e3c8551104f57e0a4de602ce20bb83ca37ec51d1a5856a764c35ae1d7f450e81`

The repository was on a normal `main` checkout with no rebase, detached HEAD,
or unexplained dirty state. This receipt is the only repository change made by
the task.

## Frozen migration boundary

Repository inspection returned one Alembic head and proved the exact chain:

```text
f41493d13761
-> a1b7c9d2e4f6
-> b2c8d0e3f5a7
```

- `a1b7c9d2e4f6.down_revision == f41493d13761`
- `b2c8d0e3f5a7.down_revision == a1b7c9d2e4f6`
- both pending revisions declare `depends_on = None`
- neither pending revision stamps or directly edits `alembic_version`
- inspection found no out-of-contract Project, thread, or message mutation in
  either migration

No migration beyond `b2c8d0e3f5a7` was included.

## Focused migration test

The required migration suite ran against a short-lived, loopback-only
PostgreSQL 15 container before the live writer freeze:

```text
.venv/bin/pytest -v tests/migration/test_direct_messaging_migration.py
2 passed, 6 warnings in 4.21s
```

The test container was removed after the run. Its seeded-profile case also
proved that the first migration mints a unique required profile ID when a
pre-existing profile requires backfill. This is complementary synthetic
evidence; the live checkpoint itself contained zero `user_profiles` rows.

## Pre-task writer posture

Six running application writers were eligible for the bounded pause:

| Service | Pre-freeze posture | Restart count |
| --- | --- | ---: |
| `backend` | running, healthy | 0 |
| `worker-warmup` | running | 0 |
| `worker-chat` | running | 0 |
| `worker-chat-embed` | running | 0 |
| `worker-document-embed` | running | 0 |
| `worker-voice` | running | 0 |

Two workers were already nonoperational restart loops and were not paused:

- `worker-account-import` was classified
  `account_import_schema_mismatch_restart_loop`.
- `worker-coding` exited before queue consumption because its Pi
  authentication prerequisite was absent. This was a separate pre-existing
  baseline condition and was not part of the migration qualification.

The account-import worker identity and baseline were:

- container ID:
  `a5abdf3f643016bee5ac4992bf855a21093d66a92fbad46755440c52ea71506b`
- image ID:
  `sha256:e81c1b0a32da55f08527cb2e6d8443f177c266139a0f66f0c348f7ee3701e0d9`
- restart policy: `unless-stopped`
- first captured restart count: 29
- count immediately after unpause: 42
- final post-teardown count: 58

The count changed through Docker's pre-existing restart policy; the container
and image identities did not change.

### Account-import failure-before-write proof

Static startup ordering and a bounded read-only reproduction proved this
sequence:

```text
account_import_worker.run_forever
-> configure event-store client
-> OpenAIAccountImportService(db=GuardianDB(...))
-> GuardianDB schema-consistency validation
-> requeue incomplete jobs
-> worker-started state
-> Redis dequeue / claim / import writes
```

`GuardianDB` failed at schema-consistency validation because the current
runtime expects the five direct-messaging tables introduced by the pending
migrations. A bounded log sample contained 29 `worker boot failed` entries and
zero worker-started, dequeue, or recovered-job entries. A separate read-only
constructor attempt reproduced the same five-table validation failure.

The failure therefore occurs before recovery, Redis account-import queue
consumption, job claim, or canonical import writes. It was safe to preserve
that natural restart-loop baseline rather than restarting or forcing it
healthy.

## Process-preserving source checkpoint

The existing desired-state marker was held only while the freeze was acquired
so the scheduled private-preview reconciliation could not race the checkpoint.
The exact active writer pause set was:

| Service | Paused container ID |
| --- | --- |
| `backend` | `c1bb3ad0eb896c2e6b8908bfe97f08302c5e05577f1f0747b58b69ec5d6a805c` |
| `worker-warmup` | `9c2cb10f9428a2a6c7c7523400e9b76c9541493ed8e84f00830d4f78cd567ea7` |
| `worker-chat` | `91b32032251d1477223033ef15ad05ad8cf95ab54375e6df296e62be11fc69d1` |
| `worker-chat-embed` | `e44a3be96cf7cb8e3829244485dc0f01d937b72ecc1bf056cc7584590eca0796` |
| `worker-document-embed` | `0b2d3e597e690bc5c2d6b56559b9c323929cb0aed64467689a1860e8bdcc6712` |
| `worker-voice` | `04b20506fe0335784a6f3407bd72cc1a141e1e6c3e09ee3c7198ae3ec9fd9f7e` |

All six exact containers entered Docker's paused state. PostgreSQL remained
running. Its freeze-window activity snapshot found four client backends, zero
open transactions, and zero non-idle client backends. No unexpected active
application writer remained.

The freeze ran from `2026-09-03T18:44:59Z` through
`2026-09-03T18:45:01Z`. During it, the task captured the bounded snapshot and
created a custom-format PostgreSQL dump:

- checkpoint identifier:
  `private-preview-alembic-gap-process-preserving-20260903T183104Z-6706fc933009`
- dump filename: `private-preview-source.pgcustom`
- dump size: 3,293,763 bytes
- dump SHA-256:
  `3f5d2c19aa0b2fb7e79351cb1dc233b2dad7158612766f6255bd3899856a7201`
- external checkpoint root mode: `0700`
- dump and bounded evidence mode: `0600`

The live checkpoint contained 107 public tables, no pending direct-message
tables, and none of the four pending social-profile columns. Selected bounded
counts were:

| Surface | Count |
| --- | ---: |
| users | 3 |
| user_profiles | 0 |
| Projects | 4 |
| chat_threads | 68 |
| chat_messages | 792 |
| media_assets | 1,402 |
| uploaded_images | 1,402 |

The full 107-table count/digest surface was retained outside Git. Core bounded
authority digests covered Project IDs, `projects.user_id`, Project-description
bytes, thread IDs/owners/Project relationships/provenance/archive state, and
message IDs/thread relationships:

| Digest surface | Count | Digest |
| --- | ---: | --- |
| Project authority | 4 | `04a642aeebfe134c38fe329a4efc0f9c` |
| Thread authority | 68 | `34102f912622380d9a65d6258d6a1be7` |
| Message relationships | 792 | `a5154a518420cab5ca36c825d91bb265` |

There were zero orphan threads and zero orphan messages. The 67
Project/thread owner mismatches were pre-existing evidence from the source and
remained unchanged; this task did not treat them as migration output or repair
them.

Immediately after dump completion, the task unpaused only those six exact
container IDs. Every container retained the same ID, image ID, restart policy,
and `StartedAt` timestamp; each resumed its prior running role with restart
count zero. The desired-state marker was restored to its exact original path.
The immediate post-unpause live snapshot was byte-identical to the checkpoint.

## Disposable restore reconciliation

The dump was restored with no-owner/no-ACL posture into an internal-only
PostgreSQL 15 container on a proof-labeled volume and network. It had no host
ports, application workers, provider credentials, or live-volume mount.

Before migration, the clone reconciled as follows:

- revision: `f41493d13761`
- public tables: 107
- all table counts and row digests: equal to source
- all three core authority digests: equal to source
- orphan and owner-mismatch integrity counts: equal to source

The raw source and first-restore schema descriptor streams each contained
2,103 descriptors but had different hashes. The exact 97 differences were all
PostgreSQL CHECK-expression rendering of equivalent array casts, for example
an explicit `character varying` array cast versus the restored equivalent text
cast. There were zero non-CHECK descriptor differences.

Following the accepted round-trip schema-equivalence posture, the restored
schema was dumped and restored once more into a second disposable database.
The first-restore and second-restore canonical descriptor streams were
byte-identical at 2,103 descriptors, with SHA-256
`f5f6212ff79c1a1e94f970243507003b8d2a74e3178231d19301cf763f5b9aa0`.
The source-to-clone schema was therefore reconciled semantically rather than by
silently ignoring serialization drift.

## Intermediate upgrade: `a1b7c9d2e4f6`

The canonical Alembic path upgraded the disposable clone to the exact
intermediate revision successfully.

- revision: `a1b7c9d2e4f6`
- public tables: 110
- initial direct-message tables: 3
- social-profile columns added: 4
- expected migration-owned constraints: 16
- expected migration-owned indexes: 5
- direct-message conversations, participants, and messages: all 0

The source contained zero profile rows, so the real-snapshot profile backfill
set was empty: zero null required IDs and zero generated IDs. No username or
node identity was fabricated. The focused seeded-profile migration test
separately covered the non-empty backfill branch and proved unique ID minting.

All 106 pre-existing application tables other than the Alembic ledger retained
identical counts and row digests. Project, thread, message, user,
document-metadata, and media-metadata surfaces were unchanged. The first
canonical-preservation gate passed.

## Target upgrade: `b2c8d0e3f5a7`

The canonical Alembic path then upgraded the same disposable clone to the exact
target successfully.

- revision: `b2c8d0e3f5a7`
- public tables: 112
- target direct-message tables: 5
- relationship and relationship-participant tables: present, 0 rows
- conversation-placement table: present, 0 rows
- obsolete conversation-participant table: absent
- expected relationship/provenance conversation columns: 4
- obsolete conversation pair-key column: absent
- expected migration-owned target constraints: 12
- direct-message conversations and messages: 0

No historical direct-message conversation, message, relationship, placement,
or origin provenance was fabricated. All 106 pre-existing application tables
again retained identical counts and row digests, including the Project,
thread, message, user, document, and media authority surfaces. The second
canonical-preservation gate passed.

## Target no-op and downgrade round trip

Invoking the canonical migrator again with exact target `b2c8d0e3f5a7`
succeeded. The complete target snapshot before and after that invocation was
byte-identical: revision, 112-table surface, schema signature, all table
counts, and all canonical digests were unchanged.

Result: `TARGET_NOOP_STABLE`.

The proof then downgraded only the disposable database:

1. `b2c8d0e3f5a7 -> a1b7c9d2e4f6` succeeded. The 110-table ADR-079 shape,
   three initial direct-message tables, four social columns, restored
   conversation-participant table, pair-key authority, empty direct-message
   domain, and source canonical digests all reconciled.
2. The intermediate raw schema hash differed from the forward intermediate
   hash only because downgrade re-added the pair-key column after existing
   columns, changing its ordinal position. The required columns, constraints,
   indexes, authority semantics, and data state matched the ADR-079 shape.
3. `a1b7c9d2e4f6 -> f41493d13761` succeeded. The final 107-table disposable
   snapshot was byte-identical to the initially restored source snapshot,
   including its canonical restored schema representation, every table count
   and row digest, all core authority digests, and integrity counts.

Result: `ROUNDTRIP_SOURCE_EQUIVALENT`.

## Final live-source and runtime preservation

After all disposable migration work and again after teardown, the live source
snapshot was byte-identical to the writer-free checkpoint:

- Alembic revision: `f41493d13761`
- PostgreSQL database container ID: unchanged
- source volume: `codexify_private_preview_pg_data`, unchanged
- public tables: 107
- pending direct-message tables: absent
- pending social-profile columns: absent
- Projects: 4, unchanged digest
- chat threads: 68, unchanged digest
- chat messages: 792, unchanged digest
- orphan threads/messages: 0 / 0
- pre-existing Project/thread owner mismatches: 67, unchanged

The six paused writers retained their original containers, images, restart
policies, start times, and zero restart counts. The account-import worker
retained its original container ID, image ID, `unless-stopped` policy, and
`account_import_schema_mismatch_restart_loop` category. Its final restart count
was 58; this is continuation of the pre-task loop, not a task-created runtime
restoration failure.

No live Alembic upgrade, downgrade, stamp, version-table edit, SQL DDL,
Project-ownership change, thread/message mutation, import cleanup, staging
mutation, source-container recreation, or source-volume switch occurred.

## Disposable teardown and retained evidence

The exact proof-only PostgreSQL container, volume
`codexify_alembic_gap_requalify_pgdata`, and internal network
`codexify_alembic_gap_requalify_net` were removed. A final inventory found none
of those disposable resources and confirmed the source volume still exists.

The checkpoint and its bounded evidence remain outside Git under the
mode-restricted private-temporary proof root. No dump bytes, raw IDs, Project
descriptions, messages, credentials, private filenames, tokens, or raw
manifests are committed in this receipt.

## Qualification boundary and next slice

This proof qualifies only the exact source-to-target migration path on a
consistent clone. It does not claim that private preview is already at
repository head, and it does not authorize Project-ownership remediation.

The next eligible slice is a separately specified live private-preview upgrade
from `f41493d13761` to `b2c8d0e3f5a7`. That live upgrade must not be combined
with Project-ownership reconciliation.

## ADR impact and documentation follow-through

ADR impact: no new ADR. The result aligns with ADR-005, ADR-079, ADR-080,
ADR-081, and the accepted governed-schema round-trip equivalence posture.

Updated only this new requalification receipt. The prior failed receipt,
`00-current-state.md`, ADR-079, ADR-080, ADR-081, migration files, runtime
implementation, account-import worker, live schema, and release/support claims
remain unchanged.
