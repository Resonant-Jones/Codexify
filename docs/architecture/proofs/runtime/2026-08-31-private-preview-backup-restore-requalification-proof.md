# 2026-08-31 Private-Preview Backup and Restore Requalification Proof

## Conclusion

`PRIVATE_PREVIEW_BACKUP_RESTORE_REQUALIFICATION_FAILED`

The recovery prerequisite remains uncleared. The existing recovery helper
reached the current-head backup boundary, then exposed a defect in its isolated
PostgreSQL restore command. Repairing that helper is a separate prerequisite;
this task did not modify it.

## Scope and authority

- Workflow lane: `architecture-impact`
- Task kind: proof
- Evidence posture: live-runtime partial, failed closed
- Execution date: 2026-08-31 local time; checkpoint timestamp:
  `20260901T002155Z`
- Source Git commit:
  `77f1acf806a1aa5481defc2dbe298b6701157da6`
- Source branch: local `main`
- Compose project: `codexify_private_preview`
- Supported profile: `v1-whooshd-deepseek-web`
- Source Postgres volume: `codexify_private_preview_pg_data`
- Migration prerequisite commit:
  `a37f3b2eb69e31fa92ed6595ad3c63a99f4182e1`

The execution used current local committed truth. Local/upstream Git
divergence was not reconciled. No users were invited, no public ingress was
opened, and no provider, Modal, authentication, or ADR posture was changed.

## Lineage

The earlier recovery attempt remains preserved at
[`2026-08-31-private-preview-backup-restore-proof.md`](2026-08-31-private-preview-backup-restore-proof.md).
It failed before backup because the source database trailed the repository
head. The intervening database migration proof remains at
[`2026-08-31-private-preview-database-migration-proof.md`](2026-08-31-private-preview-database-migration-proof.md)
and proves the source transition from `6e2b9c4a7d1f` to
`f41493d13761`.

## Live evidence

| Gate | Result | Bounded evidence |
| --- | --- | --- |
| Repository state before proof | PASS | Worktree was clean at `77f1acf806a1aa5481defc2dbe298b6701157da6`. |
| Source/current-head equality | PASS | The frozen source reported `f41493d13761`; repository Alembic head was `f41493d13761`. |
| Migration required or performed | PASS | No migration, stamp, direct ledger edit, schema change, or source-volume replacement was performed. |
| Writer freeze and source volume | PASS | The helper stopped the private-preview project, started only source `db`, and used `codexify_private_preview_pg_data` read/write. |
| Incomplete account-import gate | PASS | The helper reached and passed the zero-incomplete-job gate without printing identity-bearing rows. |
| Fresh Postgres backup | PASS | A custom-format dump was created in the external checkpoint; size `433188` bytes, mode `0600`. |
| Fresh durable-media checkpoint | PASS | A `6012`-file source manifest and media archive were created outside the repository; archive mode `0600`. |
| Retained checkpoint | PASS with failure marker | External checkpoint `private-preview-20260901T002155Z-77f1acf806a1` remains retained with `PROOF_FAILED`; checkpoint directory mode is `0700`, files are `0600`. |
| Isolated PostgreSQL 15 restore | FAILED | The helper invoked `pg_restore`, but its `docker exec` shell had no `POSTGRES_USER`; the command defaulted to the container exec user and failed with `role "root" does not exist`. |
| Restored Alembic revision | NOT RUN | Restore did not complete, so restored revision equality was not reached. |
| Table reconciliation | NOT RUN | The restore stopped before restored table counts could be captured. The frozen source contained 107 public tables; this is an observed checkpoint value, not a schema invariant. |
| Relational integrity | NOT RUN | Restore stopped before the bounded relational checks. |
| Media restore and digest equality | NOT RUN | Source media backup was captured; isolated media extraction and exact restored-file comparison were not reached. |
| Source preservation | PARTIAL | The source volume remained present with the expected identity after failure; the helper did not reach its post-restore source-integrity comparison. |
| Disposable teardown | PASS | Post-failure inspection found no proof-only restore container or labeled restore volume. The temporary media restore directory was not created. |
| Preview restart | NOT RUN | The helper stopped at the restore defect before the source preview restart. |
| Reachability | NOT RUN | The mandatory post-restart `reachability` proof was not reached. |

## Exact helper defect

The live failure is in the existing read-only dependency at
[`private_preview_backup_restore_proof.sh`](../../../../scripts/ops/private_preview_backup_restore_proof.sh),
lines 453–475. The isolated `postgres:15` container is started without an
explicit `POSTGRES_USER`, while the subsequent `docker exec` invokes:

```bash
pg_restore ... -U "$POSTGRES_USER" -d "$POSTGRES_DB"
```

Because the variable is unset in that exec environment, `pg_restore` attempted
to connect as `root` and failed. The error was captured in the retained
checkpoint's restricted `pg-restore.stderr.log`. The same environment contract
must be repaired or replaced in a separately authorized helper-repair task
before this requalification can continue. No helper edit was made here.

## Source preservation and safety boundary

- The source Alembic revision was read as `f41493d13761` before backup.
- The source Postgres volume remained present after the helper failure.
- No `docker compose down`, `down -v`, source volume removal, source media
  replacement, migration, or schema mutation was performed.
- The helper's failure trap removed the exact proof-only PostgreSQL container
  and volume; no labeled proof resources remain.
- The source media tree was read to create a manifest and archive only. The
  helper did not reach its after-proof media comparison, so the formal source
  integrity gate remains unproven in this run.
- The repository remained clean after the live attempt; no backup bytes,
  account data, media contents, credentials, or environment values entered
  Git.

## Validation results

- `bash -n scripts/ops/private_preview_backup_restore_proof.sh` — PASS
- `.venv/bin/python -m alembic -c backend/alembic.ini heads` — PASS,
  `f41493d13761`
- `CODEXIFY_PRIVATE_PREVIEW_BACKUP_DIR=... PRIVATE_PREVIEW_ENV_FILE=... bash scripts/ops/private_preview_backup_restore_proof.sh` — FAIL,
  isolated restore `pg_restore` attempted role `root`
- Post-failure Docker inspection — PASS, no proof-only container or volume
  remained; source volume remained present
- `git status --short --branch --untracked-files=all` after live proof — PASS,
  no repository changes before this receipt
- `python3 scripts/validate_docs.py` — pending until this receipt is added
- `git diff --check` — pending until this receipt is added

The earlier failed recovery receipt remains unchanged. The private-preview
runbook was not updated because its recovery-prerequisite statement is
success-gated.

## Limitations and next gate

This result does not clear the private-preview recovery prerequisite. It does
not prove isolated database restore, restored schema equality, relational
integrity, media restore equality, source-after integrity, preview restart,
service health, or reachability. It also does not prove guest isolation,
reboot recovery, load capacity, provider capacity, Cloudflare behavior, or
production-grade disaster recovery.

The next prerequisite is a separately scoped repair of the existing helper's
isolated PostgreSQL restore-user contract, followed by a fresh rerun of this
requalification task. No guest canary or external tester admission should
begin before that rerun passes. Credential rotation remains a separate
pre-exposure safety action because prior diagnostic output surfaced
secret-bearing private-preview configuration.

## ADR impact

Aligned with ADR-039, ADR-041, ADR-042, ADR-049, and ADR-069. No new ADR is
required. This failed proof does not widen release support or alter any
runtime, persistence, identity, provider, or authentication contract.

## Axis KB addition

Record that the post-migration private-preview recovery rerun reached current
Alembic head and retained a fresh external Postgres/media checkpoint, but the
existing isolated restore helper failed because `POSTGRES_USER` was not
available to its `docker exec` shell and `pg_restore` attempted the `root`
role. The helper repair is the next prerequisite; recovery remains
qualification-pending and the bounded friends-and-family canary remains
closed.
