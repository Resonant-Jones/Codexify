# 2026-09-03 Private-Preview Live Alembic Upgrade Proof

## Conclusion

`PRIVATE_PREVIEW_LIVE_ALEMBIC_UPGRADE_FAILED`

The live PostgreSQL schema upgrade itself completed and passed every database,
data-preservation, account-import-worker, and immediate runtime-read gate. The
live database is now at the exact target `b2c8d0e3f5a7` on the original
`codexify_private_preview_pg_data` volume, and it must not be described as
remaining at the source revision.

The overall task is nevertheless classified failed because the restored
private-preview scheduled reconciler subsequently exited 1. Its existing baked
migrator image does not contain revision `b2c8d0e3f5a7`; when the interval ran
`alembic upgrade heads`, Alembic reported that it could not locate the live
revision. Existing runtime containers remained healthy, but desired-state
reconciliation is no longer qualified for host/container recovery. That is a
required lifecycle boundary, not a cosmetic warning.

The lifecycle failure was observed after the application writers had resumed.
The task's rollback authorization therefore no longer applied, and no downgrade
or dump restore was attempted. The next repair must qualify a current migrator
artifact/lifecycle path without recreating the healthy process-preserved
application containers or changing the proven live data.

## Scope and authority

- Workflow classification: `architecture-impact`
- Task kind: live existing-instance database migration / controlled runtime
  cutover
- Branch: `main`
- Source Git commit:
  `ccd9734410f5aa3e9adfd999c6f974a84ad2f7ec`
- Qualification source commit:
  `6706fc933009cb51508611e400388cd7e35f7da2`
- Accepted qualification commit:
  `ccd9734410f5aa3e9adfd999c6f974a84ad2f7ec`
- Source revision: `f41493d13761`
- Intermediate revision: `a1b7c9d2e4f6`
- Exact target and repository head: `b2c8d0e3f5a7`
- PostgreSQL major: 15
- Database: `Codexify`
- Compose project: `codexify_private_preview`
- Source database container:
  `e3c8551104f57e0a4de602ce20bb83ca37ec51d1a5856a764c35ae1d7f450e81`
- Source volume: `codexify_private_preview_pg_data`

No source, migration, frontend, backend, account-import, ownership, Project,
thread, message, Redis, or configuration implementation was edited. This proof
receipt is the only repository change.

## Repository and migration gate

The repository was on a normal `main` checkout with no active rebase, detached
HEAD, or unexplained dirty state. No pull, merge, rebase, reset, or remote
synchronization occurred.

Repository inspection proved one head and the exact qualified lineage:

```text
f41493d13761
-> a1b7c9d2e4f6
-> b2c8d0e3f5a7
```

- `a1b7c9d2e4f6.down_revision == f41493d13761`
- `b2c8d0e3f5a7.down_revision == a1b7c9d2e4f6`
- both pending migrations declare `depends_on = None`
- no stamp or direct Alembic-ledger edit was used
- the three migration files were byte-identical to the successful
  qualification source

Migration file SHA-256 values were:

| Revision | SHA-256 |
| --- | --- |
| `f41493d13761` | `cbed56f788a8570951cb6bfedf9ff18f7f2f12837ef0f982947982d2fb670718` |
| `a1b7c9d2e4f6` | `5705c481ec8ebfae94b4212a47bf254e9ada5b35eb722e2d440656391b532184` |
| `b2c8d0e3f5a7` | `1d65bcea5a76b7c6901ed2eebb9739a7350d45fe0f6e6192c16e8324519a2489` |

The focused migration suite ran against a proof-only PostgreSQL 15 container:

```text
.venv/bin/pytest -v tests/migration/test_direct_messaging_migration.py
2 passed, 6 warnings in 3.79s
```

The test container was removed before the live cutover.

## Account-import executable-work gate

Read-only preflight found:

| Durable/queue state | Count or type |
| --- | ---: |
| `completed_with_warnings` jobs | 4 |
| `receiving` jobs | 9 |
| startup-recoverable jobs | 0 |
| retry-attempt rows | 0 |
| receiving jobs with all declared files staged | 1 |
| Redis account-import queue type | absent (`none`) |
| Redis account-import queue depth | 0 |

The fully received declaration was not committed, queued, or eligible for
startup recovery. No executable account-import work would run when the worker
became schema-compatible. No job or queue state was mutated.

## Fresh source truth and recovery checkpoint

Immediately before the freeze, the live source was PostgreSQL 15 at
`f41493d13761`, with 107 public tables, zero pending DM tables, and zero pending
social-profile columns. Fresh bounded counts were:

| Surface | Count |
| --- | ---: |
| users | 3 |
| user profiles | 0 |
| Projects | 4 |
| chat threads | 68 |
| chat messages | 792 |
| media assets | 1,402 |
| uploaded images | 1,402 |

The full-table digest surface included all 106 pre-existing application tables
other than the Alembic ledger, including Project lifecycle state, users,
document metadata, media metadata, and import persistence. Core authority
digests were:

| Surface | Count | Digest |
| --- | ---: | --- |
| Project ID / owner / description authority | 4 | `04a642aeebfe134c38fe329a4efc0f9c` |
| thread ID / owner / Project / origin / archive authority | 68 | `34102f912622380d9a65d6258d6a1be7` |
| message ID / thread / owner relationships | 792 | `a5154a518420cab5ca36c825d91bb265` |

Zero orphan threads and zero orphan messages were present. The 67 pre-existing
Project/thread owner mismatches were recorded as source truth and were not
reconciled.

The existing desired-state marker was held using the previously proven marker
mechanism before the freeze. Six healthy PostgreSQL-writing containers were
paused without recreation:

| Service | Container ID |
| --- | --- |
| backend | `c1bb3ad0eb896c2e6b8908bfe97f08302c5e05577f1f0747b58b69ec5d6a805c` |
| warmup worker | `9c2cb10f9428a2a6c7c7523400e9b76c9541493ed8e84f00830d4f78cd567ea7` |
| chat worker | `91b32032251d1477223033ef15ad05ad8cf95ab54375e6df296e62be11fc69d1` |
| chat-embed worker | `e44a3be96cf7cb8e3829244485dc0f01d937b72ecc1bf056cc7584590eca0796` |
| document-embed worker | `0b2d3e597e690bc5c2d6b56559b9c323929cb0aed64467689a1860e8bdcc6712` |
| voice worker | `04b20506fe0335784a6f3407bd72cc1a141e1e6c3e09ee3c7198ae3ec9fd9f7e` |

The pre-existing account-import restart-loop container was stopped by exact
container ID before mutation. The coding worker's unrelated Pi-authentication
restart loop remained outside the writer set and was not changed.

After the pause, PostgreSQL reported four idle client backends, zero open
transactions, and zero non-idle client backends. PostgreSQL remained healthy.
No unexpected active writer remained.

The cutover checkpoint was created under the mode-`0700` external root:

```text
/private/tmp/codexify-private-preview-live-upgrade/
private-preview-live-upgrade-20260903T192006Z-ccd9734410f5-f41493d13761
```

- dump: `private-preview-pre-migration.pgcustom`
- dump format: PostgreSQL custom, no owner, no ACL
- dump size: 3,293,763 bytes
- dump SHA-256:
  `30b8625204ad2789824f8710f597f40a5c0dc3836431c27e6c2052f3c8776a05`
- source schema descriptors: 2,103
- source schema digest: `159cfca18ae5c1d9988c51eae2ea2ce7`
- dump and bounded evidence mode: `0600`

The freeze checkpoint was byte-identical to the immediately preceding live
snapshot. The live source was read again immediately before mutation and was
still byte-identical to that checkpoint. Database container and volume
identities were unchanged.

## Disposable restore and current-snapshot forward rehearsal

The fresh dump restored successfully into an internal proof-only PostgreSQL 15
container with a proof-labeled volume and network and no host port. The restored
source had revision `f41493d13761`; every table count, row digest, core authority
digest, and integrity count matched the live checkpoint.

The live and restored schema streams each had 2,103 descriptors. Their 194
changed diff lines were exactly 97 paired CHECK-expression rendering
differences and contained zero non-CHECK differences. A second restore of the
first restored schema was byte-identical to the first restore, with canonical
descriptor SHA-256
`f5f6212ff79c1a1e94f970243507003b8d2a74e3178231d19301cf763f5b9aa0`.
This matches the accepted schema-equivalence method from qualification.

The repository Alembic path then advanced the freshly restored current
snapshot directly to the exact target. Alembic executed both qualified
revisions and produced:

- revision `b2c8d0e3f5a7`
- 112 public tables
- four social-profile columns
- five final direct-message tables
- obsolete conversation-participant table absent
- relationship/provenance Conversation columns present
- obsolete Conversation pair-key authority absent
- zero usernames or node IDs fabricated
- zero Relationships, Conversations, placements, or Messages fabricated
- zero origin-Project, origin-thread, or created-by provenance fabricated
- zero differences across all 106 pre-existing application tables
- unchanged Project, thread, and message authority digests

Result: `FRESH_SNAPSHOT_FORWARD_REHEARSAL_PROVEN`.

The disposable container, volume, and network were removed after the live
proof. The source volume was never attached to a proof container and remains
present.

## Exact live migration and frozen target validation

The exact live migration ran from `2026-09-03T19:46:01Z` through
`2026-09-03T19:46:02Z` while all application writers were still frozen. It used
the repository Alembic configuration and repository migration tree mounted
read-only into a one-off instance of the current backend runtime image:

```text
python -m alembic --raiseerr \
  -c /app/backend/alembic.ini \
  upgrade b2c8d0e3f5a7
```

No `upgrade head`, stamp, ad-hoc DDL, manual ledger edit, or target widening was
used.

The live target validation returned:

| Target invariant | Result |
| --- | ---: |
| Alembic revision | `b2c8d0e3f5a7` |
| public tables | 112 |
| social-profile columns | 4 |
| profile rows missing required profile ID | 0 |
| fabricated usernames | 0 |
| fabricated node IDs | 0 |
| final DM tables | 5 |
| obsolete participant table | 0 |
| required Conversation relationship/provenance columns | 4 |
| obsolete pair-key column | 0 |
| Relationships / participants | 0 / 0 |
| Conversations / placements / Messages | 0 / 0 / 0 |
| origin-Project / origin-thread / created-by provenance | 0 / 0 / 0 |

All 106 pre-existing application-table counts and row digests matched the
checkpoint. Project IDs, `projects.user_id`, description bytes, Project
lifecycle state, thread IDs/owners/Project relationships/origin/archive state,
message IDs/thread relationships, users, documents, media, and import state
were unchanged.

An exact second invocation targeting `b2c8d0e3f5a7` succeeded. The complete
target snapshot before and after it was byte-identical, including the
2,189-descriptor live target schema signature, every table digest, and every
core authority digest.

Result: `LIVE_TARGET_NOOP_STABLE`.

## Account-import worker recovery

Before cutover, the account-import worker had the following identity and
posture:

- container ID:
  `a5abdf3f643016bee5ac4992bf855a21093d66a92fbad46755440c52ea71506b`
- image ID:
  `sha256:e81c1b0a32da55f08527cb2e6d8443f177c266139a0f66f0c348f7ee3701e0d9`
- restart policy: `unless-stopped`
- sampled restart count: 100
- category: `account_import_schema_mismatch_restart_loop`

After frozen database validation, the same stopped container was started. It
retained the same ID, image, and restart policy, reached normal startup, and
logged:

```text
[account-import] worker started queue=codexify:queue:account-import recovered=0
```

The previous missing-DM-schema boot failure did not recur. The Redis queue
remained zero, recoverable-job count remained zero, durable job-status counts
were unchanged, and a complete table-digest comparison before and after worker
startup found zero changed tables. No import executed.

At final capture the worker was running, not restarting, with restart count
zero. A non-fatal warning about untracked schema objects remains a separate
schema-registry observation; it did not block worker startup and is not the
prior missing-table failure.

## Process restoration and live reads

Only the six exact paused containers were unpaused. Each retained its original
container ID, image ID, restart policy, process PID, and `StartedAt` timestamp;
each returned to its prior role with restart count zero. The database container
and source volume remained unchanged. The desired-state marker was restored to
its exact pre-task path.

Immediate runtime checks passed:

- PostgreSQL: healthy
- backend: same container, healthy
- private-preview origin `/health`: HTTP 200
- private-preview origin `/health/chat`: HTTP 200
- authenticated `GET /api/chat/threads?limit=200`: HTTP 200, 66 threads
- thread query: offset 0, no Project filter, no origin filter
- authenticated `GET /api/projects`: HTTP 200, one visible Project
- final canonical database counts: 4 Projects, 68 threads, 792 messages
- final Project/thread/message authority digests: checkpoint-identical
- final common pre-existing table differences: zero
- final live revision: `b2c8d0e3f5a7`
- final source volume: `codexify_private_preview_pg_data`

The API proof used an already-live approved Redis-backed session without
printing or persisting the token, email address, thread titles, Project names,
or message content. The response body was reduced in-process to HTTP status and
counts only.

The known stale sidebar Project filter remains deferred and was not used as the
history-preservation proof.

## Lifecycle reconciliation failure

After the desired-state marker was restored, the existing scheduled
`com.resonant.codexify-private-preview` LaunchAgent ran its normal
`auto-start -> docker compose up -d` reconciliation. The run exited 1.

The Compose migrator container was unchanged:

- container ID:
  `41eddfc197e5a8f7a940687cb4a68caa361b926d049a67771be7852bddf6621b`
- image ID:
  `sha256:e81c1b0a32da55f08527cb2e6d8443f177c266139a0f66f0c348f7ee3701e0d9`
- exit code: 1

Its baked migration tree ends before the now-live target. The canonical
`run_migrator.py` invocation inside that container attempted `alembic upgrade
heads` and failed with:

```text
Can't locate revision identified by 'b2c8d0e3f5a7'
```

The scheduled agent's final bounded state showed `last exit code = 1`.
Existing database, backend, worker, frontend, Redis, Neo4j, and origin
containers remained running because the failure occurred in the one-shot
migrator dependency; the immediate runtime health and authenticated reads above
therefore still pass. This does not qualify future desired-state recovery.

This is a deployment-artifact/runtime-target mismatch, not a live data or
Alembic-migration failure. Correcting it requires a separate scoped task that
brings the private-preview migrator artifact to the already-live repository
revision while preserving the healthy application containers. No container
filesystem patch, image rebuild, Compose edit, or runtime recreation was
smuggled into this database-only task.

## Final state and rollback boundary

The application writers had already resumed before the scheduled reconciliation
failure was observed. Invariant 35 therefore prohibited automatic downgrade.
The qualified recovery dump was retained rather than restored, and no ad-hoc
repair was attempted.

Final authoritative state:

- live PostgreSQL revision: `b2c8d0e3f5a7`
- live PostgreSQL major: 15
- live database container: unchanged
- live source volume: `codexify_private_preview_pg_data`, unchanged
- canonical Projects/threads/messages: unchanged
- account-import worker: running and idle in the same container
- ordinary application writers: unpaused in the same containers
- desired-state marker: restored
- scheduled stack reconciler: failing on stale baked migration lineage
- proof-only container/volume/network: removed
- pre-migration recovery dump and bounded evidence: retained outside Git under
  restrictive permissions
- temporary live database credential artifact: removed

No canonical rows are proven lost or altered by the cutover. No Project
ownership reconciliation occurred.

## ADR impact and documentation follow-through

ADR impact: aligned with ADR-005, ADR-079, ADR-080, ADR-081, and the governed
schema-equivalence posture in
`076-round-trip-stable-governed-schema-equivalence.md`. No new ADR is required.

This receipt is the only documentation update. `00-current-state.md` contains
no exact `f41493d13761` private-preview assertion and remains unchanged. The
qualification receipts, ADRs, migration files, runtime implementation,
Project-ownership behavior, frontend behavior, and release/support claims also
remain unchanged.

## Smallest safe next task

Qualify and install a private-preview migrator artifact that contains the exact
live lineage through `b2c8d0e3f5a7`, then prove one scheduled `auto-start`
reconciliation succeeds without recreating the current healthy application
containers or changing the database. Project runtime ownership convergence is
not eligible until that lifecycle boundary is restored.
