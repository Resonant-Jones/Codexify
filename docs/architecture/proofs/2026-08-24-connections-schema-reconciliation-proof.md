# Connections Schema Reconciliation Proof

Proof date: 2026-08-24

## Outcome

**BLOCKED — the live database revision `6e9f0a1b2c3` has no forward path in
the current canonical migration graph.**

The initial migrator artifact was stale, so it was rebuilt from the qualifying
checkout before any migration was attempted. The rebuilt artifact correctly
exposes head `d2e3f4a5b6c7`, including the Notion credential-table migration.
It cannot upgrade the live database because the sole live `alembic_version`
row (`6e9f0a1b2c3`) is absent from that graph. The canonical migrator therefore
stopped before applying DDL.

This is **Class D: no supported forward path**. No revision was stamped, no
manual DDL was issued, no schema/table was dropped, and no retry using an
explicit revision, downgrade, reset, or volume deletion was attempted.

## Source and runtime identity

| Item | Result |
| --- | --- |
| Worktree | `/private/tmp/codexify-google-drive-knowledge` |
| Branch | `codex/implement-google-drive-knowledge-connection` |
| Task HEAD | `65858e825f1df748eaa0feb5762b324d10ea2bba` |
| Tracked worktree before evidence record | clean |
| Required ancestry | `c3e5c87d`, `d8eb9d3b`, and `65858e82` are reachable from `HEAD` |
| Supported profile | `v1-local-core-web-mcp` |
| Auth mode / multi-user mode | `local` / `false` |

The local `.env` remained ignored, mode `600`, untracked, and unstaged. No
credential, OAuth configuration value, connection token, or database URL was
printed or committed.

## Migration graph and artifact preflight

| Surface | Result |
| --- | --- |
| Checkout migration head | `d2e3f4a5b6c7` |
| `d2e3f4a5b6c7` parent | `1c0a2b3c4d5e` |
| Live `alembic_version` before mutation | `6e9f0a1b2c3` |
| Initial migrator artifact head | `6e9f0a1b2c3` (stale) |
| Rebuilt runtime image | `sha256:ee3f3fbecbdc20ace36b00b1ce239266a000c303fe797da13e19d0cb469c3d6a` |
| Rebuilt migrator artifact head | `d2e3f4a5b6c7` |
| Rebuilt artifact contains the d2 migration | yes |
| `6e9f0a1b2c3` resolvable in checkout graph | no |

The stale-artifact condition was initially Class B. Rebuilding the canonical
backend/migrator image from the exact checkout resolved that condition, but
exposed the independent historical-lineage mismatch: the database stamp is
not merely behind the checkout graph; it is not a revision in that graph.

## Preservation backup and writer handling

Before the migration attempt, the canonical Postgres dump was written to:

```text
/tmp/codexify-google-drive-pre-schema-reconcile-20260824.sql
```

The dump completed successfully and is nonempty (307135 bytes). It is local,
untracked, and was not committed.

Only the qualifying Compose project application writers and backend were
stopped for the migration window. Postgres, Redis, Neo4j, volumes, and
unrelated Compose projects were not torn down or removed. After the failed
attempt, the backend and the prior application-writer services were recreated
from the current Compose configuration; no orphan was removed.

## Canonical migration attempt

The sole schema-mutating command was:

```text
docker compose run --rm migrator
```

Its canonical runner invoked:

```text
python -m alembic --raiseerr -c /app/backend/alembic.ini upgrade heads
```

Alembic failed while resolving the current revision, before selecting or
running an upgrade operation:

```text
alembic.script.revision.ResolutionError: No such revision or branch '6e9f0a1b2c3'
alembic.util.exc.CommandError: Can't locate revision identified by '6e9f0a1b2c3'
```

The migrator exited nonzero. This is a migration-lineage resolution failure,
not a Notion, Google Drive, OAuth, Command Bus, credential, or provider-API
failure.

## Post-attempt state

Read-only Postgres checks after the failed migrator show:

| Surface | Result |
| --- | --- |
| Live `alembic_version` | unchanged at `6e9f0a1b2c3` |
| `notion_connection_credentials` | absent |
| `oauth_connections` rows | 0, preserved |
| `users` rows | 1, preserved |
| `projects` rows | 1, preserved |

The desired canonical schema state was not reached. In particular,
`notion_connection_credentials` was not created, the live database was not
advanced to the checkout head, and `GuardianDB` initialization/protected-read
reproof was deliberately not represented as recovered.

The backend was restored and its non-provider health surfaces returned:

| Endpoint | Result |
| --- | --- |
| `GET /health` | `200` |
| `GET /health/chat` | `200` |
| `GET /api/health/llm` | `200` |

No Google Drive OAuth action, Google API call, connection mutation, or Google
Drive Command Bus invocation occurred. No credential, OAuth state, external
content, memory, provenance record, or document was persisted by this task.

## Validation

| Command | Result |
| --- | --- |
| `/Volumes/Dev_SSD/Codexify-main/.venv/bin/python -m alembic -c backend/alembic.ini heads` | `d2e3f4a5b6c7 (head)` |
| rebuilt migrator `alembic heads` | `d2e3f4a5b6c7 (head)` |
| canonical `docker compose run --rm migrator` | failed as recorded above; no forward-path resolution |
| migration-focused pytest suite | 14 passed, 1 skipped, 1 failed |

The failed migration test is
`tests/migration/test_alembic_revision_uniqueness.py::test_alembic_revision_ids_are_unique_and_current_head_is_explicit`.
Its checked-in expected head is `9d4c2a7e1b6f`, while the checkout graph
reports `d2e3f4a5b6c7`. This task forbids source/test changes, so the stale
test expectation was recorded rather than altered. It does not provide a
supported path from the live `6e9f0a1b2c3` stamp to the current graph.

## Required next authority

Do not use `alembic stamp`, manual DDL, a synthetic migration, a downgrade,
or a database reset to bridge this gap. A separately authorized migration
lineage-recovery task must first establish the missing historical revision's
canonical ancestry (or an approved compatibility/bridge migration) and its
data-preservation contract. It must then rerun the canonical migrator from
that repaired graph, verify the physical schema and `GuardianDB` binding, and
only then resume the Google Drive safe-status and actor-control reads.

ADR impact: none. This records a runtime migration-lineage blocker; it does
not change ADR-005, ADR-069, ADR-071, ADR-072, ADR-075, release truth, or the
Google Drive qualification boundary.
