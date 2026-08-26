# Google live-DB preservation backup / Shape D proof

## Result

**READY — a new checksum-bound preservation backup of the still-unmodified live 6e9f0a1b2c3 database was restored into a disposable database and converged through the canonical migrator to 9c66e490a42b with historical Watchdog schema and known local state preserved.**

This is a compatibility and preservation proof only. It does not authorize a live migration, OAuth, a Google API call, a Command Bus operation, or release promotion.

## Source identity

| Check | Value |
| --- | --- |
| Worktree | `/private/tmp/codexify-google-drive-main-reconcile` |
| Branch | `codex/implement-google-drive-knowledge-connection` |
| Pre-task HEAD | `f4f4c92f4c782409f9b572250b15b6deff12cba0` |
| `origin/main` | `a3d7882b8dfe826bc2f7ce3407e0677e827fcc17` |
| `origin/main...HEAD` left/right | `0 / 14` (behind / ahead) |
| `origin/main` ancestor of HEAD | yes |
| Canonical Alembic head | `9c66e490a42b` only |

The source was clean before this proof receipt. Current `origin/main` was fetched before backup and had not advanced beyond the reconciled branch.

## Migration identity

The historical Watchdog blobs remain exact:

| Revision | Blob SHA |
| --- | --- |
| `2a6b7c8d9e0f` | `1827f45ea69b392af09bfde9a798068bc23edaf3` |
| `3b7c8d9e0f1a` | `ad674e7826360fe8cc055badcc117f86a3831cf3` |
| `4c7d8e9f0a1b` | `9c5f22f48379a6c87af9a4d8ae24e9976aa05af8` |
| `5d8e9f0a1b2c` | `1666cde8b35b1918f4378ab3518f6bdb4dcfe0ba` |
| `6e9f0a1b2c3` | `041cf25e22fbf8696eb21c82be6fe58f1dcba5ef` |

`alembic history --verbose` continues to represent both historical parents of metadata-only merge `9c66e490a42b`: `6e9f0a1b2c3` and `d2e3f4a5b6c7`.

## Missing historical artifact boundary

The 2026-08-24 `/tmp/codexify-google-drive-pre-schema-reconcile-20260824.sql` artifact was not recovered. No recovery or identity-equivalence claim is made.

This task created a distinct fresh checksum-bound pre-live-migration backup from the still-unmodified qualifying database. Its digest is a new artifact identity and is not compared as though it were the missing artifact's historical digest.

## Live pre-backup state

Read-only queries against the qualifying database recorded:

| Check | Value |
| --- | --- |
| Alembic revision | `6e9f0a1b2c3` |
| Canonical users / `local` users | `1 / 1` |
| Authenticated principals | `0` |
| Projects / projects owned by `local` | `1 / 1` |
| OAuth connections | `0` |
| `notion_connection_credentials` | absent |
| Historical Watchdog tables | `5` |

## New preservation backup identity

| Check | Value |
| --- | --- |
| Backup path | `/Users/chriscastillo/.codexify/qualification-backups/2026-08-25/codexify-google-drive-pre-live-migration-20260825.sql` |
| Backup mode / size | `600` / `307135` bytes |
| SHA-256 | `58dcf970a26245ef64d489fac71db0ef9b13220e39b77bee7702d32729f5d3e7` |
| Checksum sidecar | same path with `.sha256` suffix; mode `600` |
| Evidence directory mode | `700` |
| Creation command class | read-only `pg_dump --no-owner --no-privileges` in the current Compose database service with server-owned environment |

The artifact is a regular, nonempty file outside Git and temporary storage. No database credential, credential-bearing DSN, or application secret was printed.

## Disposable restore and Shape D migration

The backup was restored into explicitly named isolated target `codexify_google_shape_d_20260825_f4f4c92`. Restore succeeded. Before migration, it exactly matched live: revision `6e9f0a1b2c3`; one `local` user and one project owned by that user; zero authenticated principals and OAuth rows; five Watchdog tables; and no Notion credential table.

The canonical Alembic environment was explicitly directed to that target and ran `upgrade heads` successfully. The final revision was `9c66e490a42b`.

## Physical schema and data preservation

After migration, all five historical Watchdog tables remained. The dispatch state index and dispatch check, foreign-key, primary, and unique constraints were present. `notion_connection_credentials` contained `id`, `user_id`, `encrypted_integration_token`, `validation_status`, `last_validated_at`, `created_at`, and `updated_at`; its validation-status check and user uniqueness constraint were present. `oauth_connections` remained present with its canonical user, provider, mode, scope, status, encrypted-token, expiry, error, and timestamp columns.

| Check | Value after migration |
| --- | --- |
| Canonical users / `local` users | `1 / 1` |
| Projects / projects owned by `local` | `1 / 1` |
| Authenticated principals | `0` |
| OAuth connections | `0` |

No account, authenticated principal, OAuth authorization, token, Google authorization, or Notion authorization was fabricated.

## Artifact-integrity recheck

After restore and migration, the persistent backup rehashed to `58dcf970a26245ef64d489fac71db0ef9b13220e39b77bee7702d32729f5d3e7`. The SHA-256 sidecar verified successfully. The before/after digests are equal. The backup and sidecar remain in their persistent owner-only location.

## Live containment

The final live read-only check remained:

| Check | Value |
| --- | --- |
| Alembic revision | `6e9f0a1b2c3` |
| Canonical users / `local` users | `1 / 1` |
| Authenticated principals | `0` |
| Projects / projects owned by `local` | `1 / 1` |
| OAuth connections | `0` |
| `notion_connection_credentials` | absent |

No live DDL, Alembic migration, stamp, reset, or data mutation occurred. Google OAuth was not initiated, and no Google API was called.

## Validation and boundaries

`pytest -v tests/migration/test_alembic_revision_uniqueness.py tests/migration/test_d6_compatibility_bridge.py` passed: **13 passed**.

ADR impact: none. Release-truth impact: none. The reconciled feature branch is not canonical `main`, and this READY preservation proof does not make it so.

The next gate is to publish and merge the zero-behind reconciled Google / Watchdog migration branch into canonical main. Only after main contains the exact repair may a separately authorized live migration window use this fresh preservation backup; that later window must reprove GuardianDB, Google Drive safe status, and actor-resolving Command Bus access before OAuth.
