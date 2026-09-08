# Persona private-preview SQLite host-storage diagnosis

Date: 2026-09-07

**PASS — DOCKER_HOST_BIND_SQLITE_IDENTITY_DEFECT**.
This is a diagnostic classification for the tested exact image and Docker host, not recovery or a universal SQLite claim.

## Scope and frozen identity

Branch `feature/persona-studio`; clean starting HEAD `07a176c361519a68bdcffe44e5dc58225ad46352`.
Governing authority: ADR-067; ADR-082 unchanged. The [blocked recovery gate](./2026-09-07-persona-private-preview-chroma-adr067-recovery-proof.md), [empty-control qualification](./2026-09-06-persona-private-preview-chroma-empty-control-diagnosis.md), and [named-volume comparison](./2026-09-07-persona-private-preview-chroma-named-volume-comparison.md) remain distinct evidence surfaces.

Exact image: `sha256:2fda9cb708e0c6567062a52386dd1c99aa839545474c554cee34db7d90c4881b`. Prior exact-image metadata: Python 3.11.14 / Chroma 1.0.15 / ARM64; the SQLite-only procedure reports SQLite 3.46.1. Chroma was never imported or invoked.
Docker Engine/client 29.7.2; Docker Desktop 4.89.0 (238018), Linux ARM64 engine, kernel `7.0.12-linuxkit`, context `desktop-linux`.

Deployment real path: `/Users/chriscastillo/.codex/worktrees/dda8/Codexify-main`.
Canonical real path, resolved without opening contents: `/Users/chriscastillo/.codex/worktrees/dda8/Codexify-main/.chroma`.
Stopped backend inspection confirms the existing read-write bind to `/app/.chroma`; no topology or configuration changed.

## Verified host filesystems

`df`, host `stat`, and mount metadata establish:

- Deployment root and `/private/tmp`: device `/dev/disk3s5`, mount `/System/Volumes/Data`, APFS, host device ID 16777234; local/journaled Data volume.
- `/Volumes/Dev_SSD`: device `/dev/disk5s1`, mount `/Volumes/Dev_SSD`, APFS, host device ID 16777250; external USB physical store `disk4s2`, local/journaled, ownership disabled. DiskManagement confirmed writable media/volume.

These are distinct mounted filesystems, though both use APFS. No non-APFS claim is made.

## Identical minimal procedure

Each control used a fresh disposable host directory, exact image, separate container, network disabled, Python entrypoint, identical `--mount type=bind,source=<directory>,target=/app/.chroma` flags. Docker inspection confirmed `RW=true` before and after each probe.

Before SQLite, ordinary create/write/append/rename/delete passed for all three. The database was never renamed, copied, replaced, chmodded, or otherwise manipulated while a connection was open. The procedure connected to `proof.sqlite3`, created one table and committed, then attempted the first insert/commit. On success it would close/reopen, count one row, then insert/commit a second row. All three failed before those latter steps.

The container paused at ordinary-write completion, connection creation, table commit, and failure so the supervisor could observe host stat and scoped `lsof` metadata before continuing. This is observation only; no path mutation occurred at the pauses.

| Control | Disposable source (removed) | Host device ID | Directory inode | Database inode | Result |
| --- | --- | --- | --- | --- | --- |
| same_root | `/Users/chriscastillo/.codex/worktrees/dda8/Codexify-main/.persona-sqlite-ri1szl2y` | 16777234 | 82095248 | 82095250 | FAIL: first insert, 8/1032 |
| same_fs | `/private/tmp/.persona-sqlite-62w0cy7r` | 16777234 | 82095253 | 82095255 | FAIL: first insert, 8/1032 |
| different_fs | `/Volumes/Dev_SSD/.persona-sqlite-3du8k3at` | 16777250 | 8212480 | 8212482 | FAIL: first insert, 8/1032 |

## Failure and path identity evidence

Every control successfully created and committed the table, then failed the first insert with:

```text
sqlite3.OperationalError: attempt to write a readonly database
primary code = 8 (SQLITE_READONLY)
extended code = 1032 (SQLITE_READONLY_DBMOVED)
```

Database size progressed from 0 at connection to 8192 bytes after table commit and remained 8192 at failure. At each observation, the only database-related file was `proof.sqlite3`; no journal/WAL/SHM file remained at those boundaries. Transient journal creation between observations is not excluded.

Host directory and database inodes remained stable within each run; container inodes matched the host values. Real paths did not change. Host directory modes were `0700`, UID 501; container modes `0700`, UID/GID 0/0. Database modes were `0644` on both sides. Container stat reported device 43 across the three binds, filesystem block size 1048576, fsid 0, flags 4102. A shared container device identifier does not negate the separately verified host mount identities.

Docker mount inspection was unchanged before/after. No bind source recreation or remount was observed. Scoped host `lsof` found only PID 1164, `com.docker.sailor`, holding the disposable database through Docker file sharing; no independent host process was observed. This does not prove absence of every transient opener between samples. No specific external replacement mechanism was established, and SQLite's error name alone is not proof that the path was physically replaced.

## Classification and boundary

All three host-bind locations fail at the same SQLite boundary, spanning the deployment worktree, outside-worktree same filesystem, and a different local APFS mount. Previously qualified named-volume and container-internal storage succeed with the same exact image. The task's classification is therefore `DOCKER_HOST_BIND_SQLITE_IDENTITY_DEFECT`.

The explicit table commit and removal of unrelated harness actions did not make the same-root probe pass. Evidence does not isolate a worktree-only problem or one host volume. The deeper Docker/SQLite identity mechanism is not established by these stat samples. No additional diagnosis or repair was performed after reaching the storage-topology decision boundary.

## Preservation, cleanup, and final operator state

Zero running-container read-write mounts overlapped canonical `.chroma`, including parent/child sources and Docker Desktop path-prefix normalization. Canonical contents were never opened, copied, or mutated; only path/stat metadata was read. Canonical root real path/device/inode/mode/size/mtime metadata matched before/after. A new canonical byte hash was intentionally not computed because this task forbids opening it; byte equality from prior proof is not presented as freshly reverified.

Historical preservation remained read-only, with recorded content-manifest digest reverified `c12d9eecacf005c983fe1d2e917f7526cd5e8c0372845d3127329930bd69b19c`.
Rollback dump remained retained with SHA-256 `510fd0a781febbd4a3e33d6b52405ddac46b533164cec5ba08e391e90a9dd04f`. Neither was modified.

All three diagnostic containers and disposable directories/databases were removed. Temporary diagnostic script/results were removed after transferring safe evidence into this receipt. No application services started; no Chroma or model/provider inference ran.

Before and after: PostgreSQL `d4e0f2a5b7c9`; backend exited; stack reconciliation unloaded/suspended; tunnel LaunchAgent loaded; desired-up present. No live persistence, Compose, dependency, runtime, or Docker setting changed. ADR-067 retirement/restoration authority was not exercised; ADR-082 Persona semantics remain unchanged.

## Validation and next prerequisite

Validation: `python3 scripts/validate_docs.py`, `git diff --check`, and staged diff checks. Only this receipt and the narrow current-state classification change are task-owned. Results are reported in closeout.

Diagnostic failures: all three expected SQLite comparisons returned primary 8 / extended 1032. No unrelated runtime failure was investigated.
Warnings: the first sandboxed `diskutil` read lacked DiskManagement access; the approved read succeeded. Sampling cannot exclude an unobserved transient opener/replacement, and the underlying Docker implementation cause remains unproven.

Next prerequisite: an architecture-impact decision for supported Chroma storage topology, followed by its separately authorized implementation/qualification. Do not retry ADR-067 on the current unqualified host bind. No Chroma recovery, Persona runtime qualification, browser persistence, or release closure is claimed.

Single current-truth fact: the exact private-preview runtime fails SQLite writes across all three tested Docker host binds on two APFS mounts, while prior named-volume/internal controls succeed; host-bind storage blocks ADR-067 recovery.
