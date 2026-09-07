# Persona private-preview ADR-067 recovery gate

Date: 2026-09-07

**BLOCKED — HOST_STORAGE_BOUNDARY_BLOCKS_ADR067_RECOVERY**.
Recovery stopped at the mandatory same-root host-bind preflight, before retirement.

## Scope and identity

Branch `feature/persona-studio`; clean starting HEAD `4aad85f7420a59d951f315043721cb2612298bab`. The [named-volume comparison](./2026-09-07-persona-private-preview-chroma-named-volume-comparison.md) was not repeated. ADR-067 retirement was conditional on this new gate; ADR-082 remains unchanged.

Deployment root: `/Users/chriscastillo/.codex/worktrees/dda8/Codexify-main`.
Active non-symlink path: `/Users/chriscastillo/.codex/worktrees/dda8/Codexify-main/.chroma`.
Existing read-only preservation: `/Volumes/Dev_SSD/Codexify-preservation/chroma/persona-20260906T230016Z/canonical-chroma`.
Secure env path resolved from the committed lineage receipt: `/Volumes/Dev_SSD/Codexify-main/.env.private-preview`; not read or used by this preflight.
Exact failed/recovery image: `sha256:2fda9cb708e0c6567062a52386dd1c99aa839545474c554cee34db7d90c4881b`. Prior exact-image proof records Linux ARM64, Python 3.11.14, Chroma 1.0.15, SQLite 3.46.1. Canonical collection: `codexify_vault_supported`.

## Preservation and writer quiescence

Read-only relative-path/type/size/content-SHA-256 manifests of active and preserved state matched the recorded aggregate before and after the gate:
`c12d9eecacf005c983fe1d2e917f7526cd5e8c0372845d3127329930bd69b19c`.
Preservation root and descendants had no write permission bits. Canonical `.chroma` was not opened by SQLite or Chroma and was not modified, copied, retired, renamed, or deleted.

Every running container's mounts were checked for read-write sources equal to, above, or below the canonical path, accounting for Docker Desktop's `/host_mnt` prefix. Zero overlapping writers were found. The backend was exited and periodic reconciliation was suspended before the probe.

## Same-root preflight

Disposable adjacent directory: `/Users/chriscastillo/.codex/worktrees/dda8/Codexify-main/.persona-chroma-preflight-l02bfkqv`.
A disposable container ran the exact image, network disabled, Python entrypoint, `PYTHONFAULTHANDLER=1`, and `RUST_BACKTRACE=1`. Docker inspection confirmed type `bind`, destination `/app/.chroma`, `RW=true`, propagation `rprivate`. No mount override to the deployment was made.

Container-visible directory UID/GID was 0/0, mode `0700`, and reported writable.

- Ordinary create/write/append/rename/delete: PASS.
- Stdlib SQLite database and table creation: succeeded.
- First SQLite insert: FAIL, `sqlite3.OperationalError: attempt to write a readonly database`.
- Extended code: `1032`, `SQLITE_READONLY_DBMOVED`.
- Commit/reopen/second insert: not reached.
- Chroma import/client/collection initialization: not attempted because SQLite qualification failed.

The diagnostic wrapper caught and reported the exception; its process completion is not a passing preflight. This reproduces the SQLite boundary on the actual deployment root/filesystem. It does not establish an incorrect UNIX mode or resolve the underlying host-storage cause. No named-volume fallback or storage repair was attempted.

The disposable container and adjacent directory were removed after capture. No application service started.

## Recovery state and final handoff

- `HISTORICAL_CHROMA_PRESERVATION_RETAINED=PASS`.
- `ACTIVE_CHROMA_INDEX_RETIRED=NOT_ATTEMPTED`.
- `FRESH_CHROMA_INITIALIZED=NOT_ATTEMPTED`.

There is no fresh canonical schema/migration result and no new historical-panic absence proof. Queue inspection and worker safe-start gates were not reached. `/health` and `/health/chat` were not tested; no healthy runtime claim follows.

Before and after: PostgreSQL `d4e0f2a5b7c9`; backend exited; stack LaunchAgent unloaded; tunnel LaunchAgent loaded; desired-up marker present. No worker or unrelated application service was started by this task. No historical Chroma records were restored or copied into a fresh active store.

The migration checkpoint remains retained at `/var/folders/j7/l5mjdtxn2fj_2sggfbl0407c0000gn/T/codexify-persona-migration-rehearsal.08qzdrlb/live-20260906T222805Z`; its `private-preview-source.dump` SHA-256 verified `510fd0a781febbd4a3e33d6b52405ddac46b533164cec5ba08e391e90a9dd04f`. No database/checkpoint mutation was performed.

ADR-067 conditional authority was respected by stopping before retirement. ADR-082 Persona ownership, revisions, manifests, and bindings remain unchanged. Source, Compose, dependencies, configuration, and storage topology remain unchanged.

## Validation, warnings, and next prerequisite

Only this proof receipt changes. `00-current-state.md` is unchanged because the task authorizes its recovery update on PASS only. Documentation/diff checks: `python3 scripts/validate_docs.py`, `git diff --check`, and staged diff check; results reported in closeout.

Failure: mandatory same-root SQLite qualification returned `SQLITE_READONLY_DBMOVED`.
Warning: Pi catalog returned zero available model entries; no review delegation or inference occurred. No Pi repair was attempted. Periodic reconciliation remains intentionally suspended and the application remains unavailable.

Smallest prerequisite: separately authorize diagnosis of the same-root host-bind SQLite boundary and qualify writable storage under the approved topology before retrying ADR-067 recovery. No topology substitution is authorized here. After recovery, qualify matching Persona lineage and the live `/api/persona-profiles` route, then authenticated browser save/readback before restoring periodic reconciliation.
