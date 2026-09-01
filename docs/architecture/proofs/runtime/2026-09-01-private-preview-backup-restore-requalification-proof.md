# 2026-09-01 Private-Preview Backup and Restore Requalification Proof

## Conclusion

`PRIVATE_PREVIEW_BACKUP_RESTORE_REQUALIFICATION_PARTIAL`

The live recovery proof did not start because the local Docker Desktop engine
was unavailable. No checkpoint was created, no source persistence was touched,
and no helper invocation was made. Recovery remains uncleared for guest
traffic.

## Scope and authority

- Workflow lane: `architecture-impact`
- Task kind: proof
- Evidence posture: pre-runtime blocked; partial
- Source Git commit at preflight:
  `fe52cdd006fc9ad4e8ad88e541b349d35948359f`
- Helper repair commit:
  `fe52cdd006fc9ad4e8ad88e541b349d35948359f`
- Source branch: local `main`
- Repository Alembic head: `f41493d13761`
- Supported profile: `v1-whooshd-deepseek-web`

The execution used current local committed truth. The unrelated unstaged
deletion at `docs/DEV_LOG/2026-09-01/Dev Log - 2026-09-01.md` was preserved and
not staged. No users were invited, no public ingress was enabled, and no
provider, authentication, persistence, or release posture was changed.

## Required lineage

The proof lineage remains:

```text
initial recovery failure
→ stale Alembic state discovered

database migration proof
→ migration rehearsal and source migration proven

second recovery failure
→ missing restore POSTGRES_USER discovered

restore-helper repair
→ explicit proof identity regression-tested

fresh recovery requalification
→ blocked before live execution by Docker Desktop availability
```

The earlier failed receipts remain immutable:

- [`2026-08-31-private-preview-backup-restore-proof.md`](2026-08-31-private-preview-backup-restore-proof.md)
- [`2026-08-31-private-preview-backup-restore-requalification-proof.md`](2026-08-31-private-preview-backup-restore-requalification-proof.md)
- [`2026-08-31-private-preview-database-migration-proof.md`](2026-08-31-private-preview-database-migration-proof.md)

## Preflight evidence

| Gate | Result | Bounded evidence |
| --- | --- | --- |
| Repository state | PASS with preserved unrelated change | `main` was at `fe52cdd006fc9ad4e8ad88e541b349d35948359f`; only the pre-existing unstaged Dev Log deletion was present. |
| Focused helper regression tests | PASS | `.venv/bin/python -m pytest -v tests/ops/test_private_preview_backup_restore_proof.py` — 6 passed. |
| Helper shell syntax | PASS | `bash -n scripts/ops/private_preview_backup_restore_proof.sh`. |
| Repository Alembic head | PASS | `.venv/bin/python -m alembic -c backend/alembic.ini heads` — `f41493d13761`. |
| New checkpoint root | PASS | The selected external checkpoint root did not exist before the blocked attempt; no checkpoint was created. |
| Docker Desktop status | BLOCKED | `docker desktop status` reported `stopped`; `docker info` reported that Docker Desktop was unable to start. |
| Stale proof-resource inspection | NOT RUN | Docker was unavailable, so no container or volume inventory could be obtained and no cleanup was attempted. |
| Source database health/current revision | NOT RUN | The helper was not invoked and the source volume was not inspected or mounted. |
| Full recovery helper | NOT RUN | No backup, restore, migration, source stop, source restart, or runtime operation occurred. |

## Exact environment blocker

The bounded Docker checks returned:

- `docker desktop status` — `Status stopped`;
- `docker info` — `Error response from daemon: Docker Desktop is unable to
  start`;
- `docker desktop start` — `Docker Desktop is already running`, while the
  subsequent status remained `stopped`.

The Docker Desktop process was present, but its `desktop-linux` server was not
available. A restart or repair of the shared Docker Desktop runtime could
affect unrelated Compose projects and was not authorized as part of this
proof. No stale proof resource was assumed absent from the unavailable
inventory.

## Recovery proof surfaces

The following mandatory surfaces were not reached:

- source writer freeze and live source Alembic equality;
- fresh Postgres custom-format backup and retention;
- fresh durable-media manifest/archive;
- disposable `postgres:15` identity proof using `codexify_restore`;
- isolated `pg_restore`, restored revision, table reconciliation, and
  relational integrity;
- isolated media extraction and exact hash equality;
- source volume/media preservation after restore;
- disposable teardown confirmation;
- private-preview restart, service health, and loopback reachability.

No failed checkpoint was reused, mutated, relabeled, or promoted. No backup
bytes, database records, media filenames, credentials, environment values, or
user content entered Git.

## Documentation and safety boundary

The private-preview runbook was not updated because recovery status is
success-gated. The helper and its regression tests were not modified. The
source database, source Postgres volume, source media, Compose files,
migrations, models, and authentication configuration were not touched.

Previously surfaced private-preview secrets still require rotation before
external guest exposure. Guest traffic remains closed.

## Validation results

- `.venv/bin/python -m pytest -v tests/ops/test_private_preview_backup_restore_proof.py` — PASS, 6 tests.
- `bash -n scripts/ops/private_preview_backup_restore_proof.sh` — PASS.
- `.venv/bin/python -m alembic -c backend/alembic.ini heads` — PASS,
  `f41493d13761`.
- `git diff --check` — PASS before receipt creation.
- Docker Desktop read-only preflight — BLOCKED, daemon unavailable.
- Synthetic Docker smoke test — NOT RUN; Docker Desktop was unavailable.
- Full private-preview recovery qualification — NOT RUN.

## ADR impact

Aligned with ADR-039, ADR-041, ADR-042, ADR-049, and ADR-069, plus the Data
and Storage and Account Export + Restore contracts. No new ADR is required.
This partial proof changes no architecture or release-support claim.

## Next prerequisite

Restore the local Docker Desktop `desktop-linux` engine, then re-run the exact
preflight resource inventory and execute the helper with a completely new
external checkpoint. Do not use either failed recovery checkpoint or the
pre-migration backup as successful evidence. No guest canary or external
tester admission should begin until the fresh recovery proof passes.

## Axis KB addition

Record that the repaired private-preview recovery helper was regression-tested
but the next live requalification was blocked before execution because Docker
Desktop remained stopped and unable to start. No checkpoint or source runtime
operation occurred; recovery remains qualification-pending and guest traffic
remains closed.
