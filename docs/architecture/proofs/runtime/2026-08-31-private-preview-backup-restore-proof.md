# 2026-08-31 Private-Preview Backup and Restore Proof

## Conclusion

`PRIVATE_PREVIEW_BACKUP_RESTORE_FAILED`

The private-preview recovery prerequisite is not cleared for real
friends-and-family traffic.

## Scope

This proof attempted the bounded deployment-level recovery checkpoint required
by [`docs/Ops/private-browser-preview.md`](../../../Ops/private-browser-preview.md):

- canonical Postgres application state in the private-preview `pg_data`
  volume;
- durable media bytes under `data/media`;
- no Redis backup because Redis is transient transport;
- no Chroma backup because vector state is derived;
- no Neo4j backup because resolved graph-write posture was disabled/noop; and
- no private import staging because no receiving, queued, or running account
  import depended on it.

No application-level `Codexify-Export.zip` behavior was exercised. No public
preview, Cloudflare, Modal, provider-inference, guest-account, or release claim
was changed.

## Source identity

- Execution date: 2026-08-31
- Checkpoint attempt timestamp: `2026-08-31T22:07:21Z`
- Source Git commit:
  `f351585e8b71908a0b173b9fd2d4e5a87ce99994`
- Source branch: local `main`
- Source Compose project: `codexify_private_preview`
- Intended profile: `v1-whooshd-deepseek-web`
- Source Postgres volume: `codexify_private_preview_pg_data`
- Source Alembic revision: `6e2b9c4a7d1f`
- Repository Alembic head: `f41493d13761`

The local branch was ahead of and behind `origin/main`; this task did not
fetch, rebase, merge, or substitute public branch state for the selected local
execution authority.

## Pre-maintenance inspection

| Gate | Result | Bounded evidence |
| --- | --- | --- |
| Repository state | PASS | Clean before implementation; only the authorized proof helper became untracked during the attempt. |
| Private-preview Compose identity | WARNING | Only the project Redis container was running. Its labels referred to an older local worktree rather than the current repository root. |
| Postgres volume identity | PASS | The expected `codexify_private_preview_pg_data` volume existed before and after the attempt. |
| Postgres health before maintenance | UNAVAILABLE | No source Postgres container was running before the proof. |
| Media root | PASS | The current canonical `data/media` root existed and contained `0` regular files. |
| Import staging | PASS | `data/imports` contained `0` regular files. |
| Graph-write posture | PASS | Resolved backend/worker configuration kept graph writes disabled with the noop graph backend. |
| Incomplete account-import gate | PASS | After DB-only startup, the bounded count of `receiving`, `queued`, or `running` import jobs was `0`. No identity-bearing rows were printed. |
| Existing origin health | FAIL | Static preview validation passed, but the pre-maintenance reachability run returned HTTP `404`; the private-preview origin was absent. |

An unrelated local Buzz relay initially occupied TCP 8081. The operator
authorized its termination; by the time termination was attempted the verified
process had already exited, and TCP 8081 was confirmed free before the backup
proof began. No broad process signal was issued.

## Helper safety checks

The new helper is
[`scripts/ops/private_preview_backup_restore_proof.sh`](../../../../scripts/ops/private_preview_backup_restore_proof.sh).

Before live execution it passed:

- Bash syntax validation;
- unset backup-destination rejection;
- relative backup-destination rejection;
- direct inside-repository destination rejection;
- symlink-resolved inside-repository destination rejection;
- unsafe broad-root destination rejection before directory mode changes;
- repository-directory mode preservation during rejected destination checks;
- resolved graph-write fail-closed inspection;
- exact loopback-publication contract inspection; and
- `git diff --check`.

The destination-validation ordering was corrected before live execution so an
unsafe repository path is rejected before directory creation or permission
changes. The helper also removes a proof-created source DB container and an
empty pre-backup checkpoint automatically when a pre-backup gate fails.

## Live attempt

The helper used an operator-selected absolute backup root outside the
repository. The exact machine path is intentionally omitted from this receipt.

The live sequence reached these steps:

1. validated provider-free graph and port posture;
2. created a mode-`0700` timestamped checkpoint directory outside Git;
3. recorded one initially running source service;
4. stopped the private-preview project with `docker compose stop`;
5. started only the existing source `db` service;
6. waited for Postgres readiness;
7. confirmed no application writer remained active;
8. confirmed zero incomplete account-import jobs; and
9. compared source and repository Alembic identity.

The helper then failed closed because source revision `6e2b9c4a7d1f` does not
equal repository head `f41493d13761`.

Allowing the normal current-Compose startup to continue would invoke the
migrator and change the source schema. Schema migration is explicitly outside
this proof task. Starting current application code while bypassing the
migrator would provide a misleading health result against an older schema.
Starting the older worktree would contradict the task's local-current-truth
authority. None of those paths was taken.

## Backup and restore results

| Proof surface | Result | Reason |
| --- | --- | --- |
| Postgres custom-format dump | NOT RUN | Alembic source/current-head gate failed before `pg_dump`. |
| Postgres dump hash and size | NOT AVAILABLE | No dump was created. |
| Isolated Postgres 15 restore | NOT RUN | No dump existed to restore. |
| Source/restored Alembic equality | NOT RUN | Restore was not started. |
| Public-table-set comparison | NOT RUN | Restore was not started. |
| Per-table row-count comparison | NOT RUN | Restore was not started. |
| Core relational checks | NOT RUN | Restore was not started. |
| Durable-media archive | NOT RUN | The cross-store checkpoint did not proceed after the database gate. |
| Media file-count equality | NOT RUN | No archive was restored. |
| Individual media-hash equality | NOT RUN | No archive was restored. |
| Aggregate media-manifest equality | NOT RUN | No archive was restored. |
| Retained outside-repository checkpoint | NO | The empty pre-backup checkpoint was removed after confirming it held no dump or media archive. |

No database rows, table contents, password hashes, tokens, credentials,
messages, document contents, media contents, account identifiers, or filenames
were added to this receipt.

## Source preservation and cleanup

| Invariant | Result |
| --- | --- |
| No `docker compose down` or `down -v` | PASS |
| Source `pg_data` volume retained | PASS |
| Source volume identity unchanged | PASS |
| Source media untouched | PASS |
| Source schema untouched | PASS |
| Source repository scope preserved | PASS |
| Proof-created source DB container removed | PASS |
| Original Redis-only running state restored | PASS |
| Disposable restore container | NOT CREATED |
| Disposable restore volume | NOT CREATED |
| Disposable extracted-media directory | NOT CREATED |
| Empty pre-backup checkpoint removed | PASS |

The only removed material was the proof-created stopped source DB container and
the empty two-file pre-backup checkpoint. The source Postgres volume and all
source media remained intact.

## Preview restart and health

Full private-preview restart was not attempted because current Compose would
run a schema migration outside the authorized task. The helper restored the
pre-attempt Redis-only service state instead.

Consequently these mandatory acceptance gates remain failed or unproven:

- source Postgres healthy after full restart;
- backend healthy;
- chat-worker heartbeat healthy;
- loopback private-preview origin healthy; and
- `scripts/private_preview_validate.sh reachability` passing after restart.

No authenticated provider check was attempted and no credential was created or
exposed.

## Validation results

- `bash -n scripts/ops/private_preview_backup_restore_proof.sh` — PASS
- unset backup-destination refusal — PASS, exit `1`
- relative, inside-repository, symlink-resolved inside-repository, and unsafe
  broad-root destination refusals — PASS
- `git diff --check` before live execution — PASS
- private-preview static validation — PASS, `39` focused tests passed
- pre-maintenance private-preview reachability — FAIL, HTTP `404`
- graph-write posture gate — PASS
- DB-only Postgres readiness — PASS
- incomplete account-import job gate — PASS, count `0`
- Alembic source/current-head gate — FAIL,
  `6e2b9c4a7d1f != f41493d13761`
- post-failure source-volume existence check — PASS
- post-failure original service-state restoration — PASS
- `python3 scripts/validate_docs.py` after receipt/runbook updates — PASS
- final `git diff --check` — PASS
- final changed-file scope — PASS, limited to the three task-authorized files

`shellcheck` was not installed on the host and was not classified as passed.

## Warnings versus failure

Warnings:

- the private-preview project was already degraded before maintenance: only
  Redis was running;
- the remaining Redis container carried labels from an older local worktree;
- the current media and import-staging trees were empty; successful empty-media
  restore semantics therefore remain unproven because backup did not proceed;
- this is local live evidence, not canonical `latest` promotion under
  ADR-041/ADR-042.

Mandatory failure:

- the source Postgres migration revision is behind current local `main`, and
  this proof was not authorized to migrate it.

## Required next boundary

Do not invite real users yet.

A separately authorized migration/recovery task must govern the stale source
database before this proof can pass. It should first establish a retained,
isolated restore of the existing `6e2b9c4a7d1f` Postgres state and media, then
prove the supported migration to `f41493d13761`, restart current private-preview
services, and rerun this recovery checkpoint. That task must not treat the
failed attempt or the presence of a source volume as migration approval.

The existing private-preview runbook warning remains authoritative and is not
weakened by this receipt.

## Axis KB addition

Record that the 2026-08-31 private-preview recovery attempt stopped before
backup at a fail-closed migration gate: the preserved Postgres volume is at
`6e2b9c4a7d1f`, while local `main` expects `f41493d13761`. No dump, media archive,
restore runtime, retained checkpoint, schema mutation, user invitation, or
release promotion occurred. Exact conclusion:
`PRIVATE_PREVIEW_BACKUP_RESTORE_FAILED`.
