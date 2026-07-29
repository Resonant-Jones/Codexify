# Existing User Profile Preservation Proof: Accent Migration

**Date:** 2026-07-28
**Proof class:** isolated existing-instance schema migration
**Result:** PASS
**Commit under test:** `c3289d11c94f8ea88921f68e2e5658f23f716c42`

## Claim proved

A populated pre-accent `users` and `user_profiles` row survives a normal
`alembic upgrade heads` operation. The migration adds `accent_color` and
backfills the existing profile to the canonical `default` value without
changing the existing user identity, profile metadata, or timestamps.

This proof covers database migration and durable-row preservation only. It
does not prove live `/api/user/profile` availability, an authorized runtime
profile, Chrome panel reload, or second-client rehydration.

## Revision and source gates

The repository identity gate passed:

```text
repository: /Users/resonant_jones/Keep/Resonant_Constructs/projectCodexify/Codexify
branch: main
HEAD: c3289d11c94f8ea88921f68e2e5658f23f716c42
ancestor_check: PASS
worktree at identity gate: clean (main...origin/main [ahead 1])
```

The migration under test is:

```text
revision: c8d9e0f1a2b3
down_revision: e5f6a7b8c9d0
```

The task's declared pre-upgrade heads were `b2c3d4e5f6a7` and
`e5f6a7b8c9d0`; the expected post-upgrade heads were `b2c3d4e5f6a7` and
`c8d9e0f1a2b3`.

In this checkout, `b2c3d4e5f6a7` descends through
`a1c2d3e4f5b6` from `e5f6a7b8c9d0`. Therefore the two pre-upgrade targets
were applied as sequential Alembic targets, and Alembic materialized the
pre-accent database version as `b2c3d4e5f6a7`; the `e5f6a7b8c9d0` target was
already reachable in that revision path. This is the graph-normalized form
of the requested pre-accent schema, not a stamped or manually edited state.

The requested historical proof file
`docs/architecture/proofs/2026-04-04-existing-instance-upgrade-proof.md` was
not present in this checkout and was not used as evidence.

## Isolation boundary

The proof used:

| Item | Value |
| --- | --- |
| Temporary database | `codexify_accent_upgrade_proof_20260728` |
| Temporary database container | `codexify-accent-upgrade-proof-db` |
| Database image | `postgres:15` |
| Migration image | `codexify-backend-runtime:latest` |
| Migration image digest | `sha256:4b9b22e1843c6f4914116c5dfa0c0a72288e52f86525c17f37f442ed12a5e580` |
| Migration image created | `2026-07-28T23:47:41.756120255Z` |
| Temporary database volume | none |

The temporary Postgres container was bound to host port `55432` and was
removed automatically after evidence capture. The active Codexify database
remained in `codexify-db-1` on its existing `codexify_pg_data` volume; the
proof did not connect to it. No `docker compose down -v`, `alembic stamp`,
manual `alembic_version` edit, migration edit, or application-volume change
was used.

## Procedure

1. Start the no-volume temporary Postgres database.
2. Run Alembic from the migrator image against the temporary database,
   sequentially targeting `b2c3d4e5f6a7` and `e5f6a7b8c9d0`.
3. Insert the specified user and profile with SQL into the schema produced by
   Alembic. The post-migration ORM model was not used to manufacture the
   pre-migration schema.
4. Capture the pre-upgrade row, including `created_at` and `updated_at`.
5. Run the normal command `alembic upgrade heads` from the same migrator
   image.
6. Capture the post-upgrade heads, row, schema constraint state, and an SQL
   preservation assertion.
7. Remove the temporary database container.

The seeded identity and metadata were:

```text
user_id:      accent-upgrade-proof-user
username:     accent-upgrade-proof@example.invalid
display_name: Accent Upgrade Proof
avatar_url:   https://example.invalid/accent-upgrade-proof.png
timezone:     America/New_York
```

## Captured evidence

### Pre-upgrade row

```json
{
  "user_id": "accent-upgrade-proof-user",
  "username": "accent-upgrade-proof@example.invalid",
  "display_name": "Accent Upgrade Proof",
  "avatar_url": "https://example.invalid/accent-upgrade-proof.png",
  "timezone": "America/New_York",
  "created_at": "2026-07-29T00:17:44.521556+00:00",
  "updated_at": "2026-07-29T00:17:44.521556+00:00"
}
```

### Normal upgrade result

```text
command: alembic upgrade heads
result: migration c8d9e0f1a2b3 applied successfully
```

The post-upgrade Alembic heads were:

```text
b2c3d4e5f6a7 (head)
c8d9e0f1a2b3 (head)
```

The post-upgrade row was:

```json
{
  "user_id": "accent-upgrade-proof-user",
  "username": "accent-upgrade-proof@example.invalid",
  "display_name": "Accent Upgrade Proof",
  "avatar_url": "https://example.invalid/accent-upgrade-proof.png",
  "timezone": "America/New_York",
  "accent_color": "default",
  "created_at": "2026-07-29T00:17:44.521556+00:00",
  "updated_at": "2026-07-29T00:17:44.521556+00:00"
}
```

The SQL assertion compared every seeded identity and profile field, required
`accent_color = 'default'`, and compared both timestamps to the captured
pre-upgrade values:

```text
preservation_assertion=PASS
```

The schema inspection also confirmed that `accent_color` is non-null and the
named canonical check constraint exists:

```text
schema_assertion=PASS
```

The migration performs a backfill rather than adding a database-level server
default in the migration itself; the proof claim is specifically the
backfilled value on the existing row.

## ADR and contract impact

Aligned with the existing migration-proof doctrine and the following
governing contracts:

- ADR-005 Runtime Mode and Account Boundary Invariants
- Remote Account Access and User Profile Contract
- Account Export + Restore Contract
- Data and Storage

This artifact changes no runtime behavior, schema, route, frontend, Compose
file, or supported profile. It records proof for the already-landed
account-scoped preference migration.

## Proof limits and follow-up

Proven:

- isolated temporary database use;
- populated existing profile before upgrade;
- normal `alembic upgrade heads` transition;
- post-upgrade heads `b2c3d4e5f6a7` and `c8d9e0f1a2b3`;
- preservation of user identity, profile metadata, and timestamps;
- `accent_color` backfill to `default`;
- non-null and named check-constraint presence;
- cleanup of the temporary proof database.

Deferred and not claimed here:

- live `/api/user/profile` behavior under an authorized runtime profile;
- Chrome panel reload or rehydration;
- second-client profile convergence;
- packaged or non-Compose runtime behavior.
