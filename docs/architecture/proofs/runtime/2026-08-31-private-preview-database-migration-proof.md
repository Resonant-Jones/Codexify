# Private-preview database migration proof

Date: 2026-08-31 (operator-local time)

Conclusion: `PRIVATE_PREVIEW_DATABASE_MIGRATION_PROVEN`

This receipt records the live migration qualification for the preserved
private-preview PostgreSQL database. It contains no database contents,
identifiers, credentials, tokens, message text, document contents, or media
filenames.

## Scope and authority

- Source Git commit: `f945632bf847ff30bbafe0090bad613693307dfb`
- Compose project: `codexify_private_preview`
- Source volume: `codexify_private_preview_pg_data`
- Source Alembic revision: `6e2b9c4a7d1f`
- Target Alembic revision: `f41493d13761`
- Private-preview traffic gate: closed
- No users were invited and no public preview surface was exposed.

The proof ran the current local repository state. The known local/upstream Git
divergence was not reconciled.

## Migration lineage

The static graph validator found 95 parseable revision files, no duplicate
revision identities, no missing parent revisions, and one repository head.
The required merge and both understood source-to-head paths were:

```text
6e2b9c4a7d1f -> 8f3c1a7d2e6b -> 9d4c2a7e1b6f -> 1c0a2b3c4d5e -> d2e3f4a5b6c7 -> 9c66e490a42b -> f41493d13761
6e2b9c4a7d1f -> 8f3c1a7d2e6b -> 9d4c2a7e1b6f -> 1c0a2b3c4d5e -> 2a6b7c8d9e0f -> 3b7c8d9e0f1a -> 4c7d8e9f0a1b -> 5d8e9f0a1b2c -> 6e9f0a1b2c3 -> 9c66e490a42b -> f41493d13761
```

No required migration declared an unsupported dependency, modified the
Alembic ledger directly, or used stamping as a substitute for upgrade.

## Evidence gates

| Gate | Result | Bounded evidence |
| --- | --- | --- |
| Source runtime and writer freeze | PASS | PostgreSQL 15; source revision exact; one pre-task running service; no application writer remained during the migration window |
| Pre-migration backup | PASS | PostgreSQL custom-format dump; `--no-owner --no-acl`; mode `0600`; 379,879 bytes; SHA-256 recorded in the external checkpoint |
| Backup restore verification | PASS | Disposable PostgreSQL 15 container and volume; no host port; network isolated; restored revision `6e2b9c4a7d1f`; bounded table counts and integrity checks matched |
| Disposable migration rehearsal | PASS | Canonical `/app/backend/scripts/docker/run_migrator.py`; exact target revision `f41493d13761`; expected schema objects, deterministic backfill invariants, and relationship checks passed |
| Source migration | PASS | Same canonical migrator path; starting revision rechecked immediately before mutation; source reached `f41493d13761` |
| Post-migration reconciliation | PASS | 98 public table counts reconciled; no unexpected canonical row loss; ownership, transcript, document/media, Hosted Room, ThreadSpace, and account-observability relationship checks passed where present |
| Durable media | PASS | 6,012-file aggregate manifest count and digest unchanged; no media bytes were modified by the migration |
| Source volume | PASS | `codexify_private_preview_pg_data` identity unchanged |
| Second migrator invocation | PASS | Canonical migrator completed at head; revision remained `f41493d13761`; table counts, schema signature, integrity, and media checks remained stable |
| Disposable teardown | PASS | Proof-only container and volume removed by exact name; no source volume removal was attempted |
| Runtime restoration | PASS | Previously observed posture restored; the only pre-task running service was Redis, and the proof-created database container was removed after verification |
| Backup retention | PASS | Pre-migration dump and bounded checkpoint retained outside the repository |

The internal gate `DISPOSABLE_MIGRATION_REHEARSAL=PASS` was written only after
backup restore, exact pre-migration reconciliation, disposable migration to
the target head, schema checks, deterministic invariants, and integrity checks
all passed.

## Retained checkpoint

The external checkpoint identifier is:

`private-preview-database-migration-20260901T000136Z-f945632bf847`

The backup path and database dump remain outside Git. The checkpoint records
the dump size, SHA-256, restrictive permissions, table-count digests,
relationship/integrity digests, schema digests, media-manifest digest, and
proof-script digest. The committed receipt records only the presence of those
artifacts, not their sensitive paths or contents.

## Limitations and next gate

This proof clears only the database-migration prerequisite. It does not prove
private-preview backup/restore qualification, guest readiness, authentication
readiness, provider execution, queue completion, reboot recovery, Cloudflare
Tunnel/Access behavior, public-host behavior, or general Beta support.

The next separate task is to rerun the already-committed private-preview
backup/restore proof against the now-current database. Do not invite users or
open guest traffic before that recovery proof and the subsequent bounded
guest-canary gate pass.

ADR impact: aligned with ADR-039, ADR-041, ADR-042, ADR-049, and ADR-069; no
new ADR or migration was required.
