# 2026-09-01 Private-Preview Backup and Restore Requalification After Docker Recovery

## Conclusion

`PRIVATE_PREVIEW_BACKUP_RESTORE_REQUALIFICATION_PROVEN`

Recovery prerequisite cleared for a bounded friends-and-family private-preview
canary.

This proof does not itself execute or admit that canary. Guest traffic remains
closed until the separate canary gate is deliberately run. Previously surfaced
private-preview secrets must be rotated before external guest exposure.

## Scope and authority

- Workflow lane: `architecture-impact`
- Task kind: proof
- Evidence posture: live-runtime proven
- Execution date: 2026-09-01 local time; checkpoint timestamp:
  `20260901T091740Z`
- Source Git commit: `14929d2e6047797fdc1e803a9b4234af745a48bb`
- Source branch: local `main`
- Compose project: `codexify_private_preview`
- Supported profile: `v1-whooshd-deepseek-web`
- Source Postgres volume: `codexify_private_preview_pg_data`
- Helper Git blob identity: `ec7f6bbeab6c10b5b879b417b0eb1d400f78c2dd`

The selected authority was the committed local `main` source at the commit
above. The worktree had one pre-existing unrelated deletion,
`docs/DEV_LOG/2026-09-01/Dev Log - 2026-09-01.md`; it was preserved and was
not staged or modified by this proof. No fetch, rebase, merge, push, or
upstream-truth substitution was performed.

No users were invited, no public ingress was opened, no guest traffic was
enabled, and no provider, Modal, authentication, migration, schema, current-
state, Compose, or ADR contract was changed.

## Docker and preflight

Docker server availability was rechecked in this execution context before the
fresh checkpoint:

- `docker desktop status` — `running`.
- `docker version` — Docker Desktop `4.88.1`, Engine `29.7.2`, context
  `desktop-linux`, server `linux/arm64`.
- `docker info` — `26` running containers, `4` CPUs, `9.702GiB` total memory.
- Direct `lsof -nP -iTCP:8081 -sTCP:LISTEN` before proof — no listener.
- Exact proof-only container, labeled proof-volume, named restore-volume, and
  temporary media-restore inventories before proof — empty.

The pre-existing Buzz, Tester, watchdog, and audit workloads were observed but
not stopped, restarted, deleted, or modified. One pre-existing audit worker
was restarting during preflight; it had no 8081 conflict and was left alone.

## Fresh checkpoint and lineage

The prior 2026-08-31 failed recovery checkpoints and the earlier
Docker-unavailable attempt were not reused. A new external root was confirmed
absent before execution:

`/Volumes/Dev_SSD/Codexify-private-preview-requalification-after-docker-recovery-20260901`

The helper retained checkpoint
`private-preview-20260901T091740Z-14929d2e6047` outside the repository. The
checkpoint directory is mode `0700`; its proof artifacts are mode `0600`. It
contains the restricted Postgres dump, media archive and manifests, source and
restore revision/count artifacts, relational checks, and the helper status
receipt. No database records, media contents, media filenames, credentials, or
environment values were added to Git or this receipt.

The checkpoint manifest records:

- source and repository Alembic revision: `f41493d13761` / `f41493d13761`;
- Postgres dump: `433188` bytes,
  SHA-256 `614edc979bff2d613487d0318e054388361b3859e272785a51331fac3b7870d4`;
- source public table count: `107`, with restored table-count equality;
- durable media: `6012` files, `3805708800` bytes,
  archive SHA-256
  `f18f90e2046bdfd6f550c973733ccce587ba835d9b02ace02bceb2d4d977bf48`;
- source/restored media manifest SHA-256:
  `4458dea62c64b28747a8e94b3c6f49458fdfd46e5ee520102cd8232303b52682`;
- incomplete account-import jobs: `0`.

The source import staging count was observed as `15463`; the staging tree was
not modified.

## Live proof gates

| Gate | Result | Bounded evidence |
| --- | --- | --- |
| Graph-write posture | PASS | `graph_write_gate=PASS`; the resolved proof configuration remained provider-free/noop for graph writes. |
| Private publication contract | PASS | `preview_port_contract=PASS`; the only accepted publication was `private-preview-origin` at `127.0.0.1:8081 -> 8080`. |
| Writer freeze | PASS | The helper stopped the private-preview project, started only the source database, and passed the zero-incomplete-import-job gate before capture. |
| Fresh Postgres backup | PASS | Custom-format dump retained in the new external checkpoint, mode `0600`. |
| Fresh durable-media checkpoint | PASS | Source media archive and restricted source manifest retained outside the repository. |
| Explicit restore identity | PASS | Disposable `postgres:15` restore used `codexify_restore` / `codexify_restore`, with `POSTGRES_HOST_AUTH_METHOD=trust` only inside the isolated proof container. |
| Restore isolation | PASS | Disposable restore container used `--network none`; it did not reuse the source database identity or volume. |
| Postgres restore | PASS | `postgres_restore=PASS`; `pg_restore` completed against the explicit restore user/database. |
| Alembic equality | PASS | `source_alembic_revision=f41493d13761` and `repository_alembic_revision=f41493d13761`; restored revision equality passed. |
| Public-table and row-count reconciliation | PASS | `source_public_table_count=107`; restored table-count equality passed. |
| Relational integrity | PASS | `relational_integrity=PASS`; restricted relational-check artifact retained. |
| Media restore equality | PASS | `media_file_count=6012`; exact restored-file and aggregate manifest equality passed. |
| Source Postgres preservation | PASS | `source_volume_identity=UNCHANGED`; source volume remained `codexify_private_preview_pg_data`. |
| Source media preservation | PASS | `source_media_integrity=UNCHANGED` after restore comparison. |
| Disposable cleanup | PASS | Proof-only restore container and volume, plus temporary extracted-media directory, were absent after the run. |
| Preview restart | PASS | `preview_restart_reachability=PASS`; the private-preview Compose project restarted from the preserved source state. |
| Post-restart reachability | PASS | The helper and an independent `PRIVATE_PREVIEW_BASE_URL=http://127.0.0.1:8081 bash scripts/private_preview_validate.sh reachability` both passed. |
| Retained checkpoint | PASS | `retained_checkpoint=PASS`; the fresh external checkpoint remains available for bounded inspection/recovery follow-through. |

The post-proof Compose inspection showed the expected project state: database,
backend, Neo4j, and Redis healthy; frontend, workers, and private-preview
origin up; migrator, model-prep, and graph-init one-shot jobs exited `0`. The
origin remained loopback-only at `127.0.0.1:8081`. Reachability proves the
private HTTP path and configuration contract; it does not prove provider
execution, persistence, guest isolation, or canary acceptance.

## Safety and preservation boundary

- No `docker compose down` or `down -v` was used.
- No source volume was removed, replaced, or relabeled.
- No source database migration, schema mutation, stamp, or direct
  `alembic_version` edit was performed during this proof.
- No source media or import-staging bytes were changed.
- Only exact proof-created disposable resources were removed.
- The pre-existing non-proof containers were not mutated.
- No credentials were printed, committed, rotated, or created by this proof.
- Provider execution, external guest access, Cloudflare behavior, reboot
  recovery, load capacity, and production disaster recovery remain outside
  this qualification.

## Validation results

- `.venv/bin/python -m pytest -v tests/ops/test_private_preview_backup_restore_proof.py` — PASS, 6 tests.
- `bash -n scripts/ops/private_preview_backup_restore_proof.sh` — PASS.
- `git diff --check` before and after the proof — PASS.
- `.venv/bin/python -m alembic -c backend/alembic.ini heads` — PASS,
  `f41493d13761`.
- Fresh repaired helper invocation against the new external checkpoint — PASS,
  `PRIVATE_PREVIEW_BACKUP_RESTORE_PROVEN`.
- Independent post-restart reachability invocation — PASS.
- Post-proof Compose and bounded resource inventory — PASS; no proof-only
  disposable resources remained.
- `python3 scripts/validate_docs.py` — run after this receipt is added; result
  recorded in the final closeout.

## ADR impact

Aligned with ADR-039, ADR-041, ADR-042, ADR-049, and ADR-069. No new ADR is
required. This proof clears only the recovery prerequisite for a bounded
private-preview canary; it does not widen release support or alter runtime,
persistence, identity, provider, or authentication contracts.

## Axis KB addition

Record that after Docker Desktop recovery, the repaired private-preview
backup/restore helper completed a fresh external checkpoint at local `main`
commit `14929d2e6047797fdc1e803a9b4234af745a48bb`, restoring the database with
the explicit `codexify_restore` identity, proving Alembic/table/relational
equality, proving exact 6,012-file media restore and source preservation,
cleaning exact disposable proof resources, and passing private loopback
restart/reachability. Recovery is now qualified for a bounded canary; guest
traffic remains closed and previously surfaced private-preview secrets must be
rotated before external guest exposure.
