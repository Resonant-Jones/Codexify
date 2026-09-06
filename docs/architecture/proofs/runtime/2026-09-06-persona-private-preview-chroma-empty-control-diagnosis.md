# Persona private-preview Chroma empty-control diagnosis

Date: 2026-09-06

Result: **PASS — EMPTY_CONTROL_HARNESS_PERMISSION_DEFECT** (task classification A).
This qualifies the diagnostic harness; it does not establish canonical-store compatibility or authorize recovery.

## Scope and lineage

Branch: `feature/persona-studio`. Starting HEAD: `b5242d647fba653339775e339728c245ffe6b907`; worktree clean before diagnosis.

Every disposable probe used the exact failed backend image:
`sha256:2fda9cb708e0c6567062a52386dd1c99aa839545474c554cee34db7d90c4881b`.
The prior exact-image receipt established Linux ARM64/aarch64, Python 3.11.14, Chroma 1.0.15, SQLite 3.46.1, and Rust bindings. No dependencies changed.

Governing comparison receipts: [prior diagnosis](./2026-09-06-persona-private-preview-chroma-diagnosis.md), [August fresh-state diagnosis](./2026-08-24-tester-fresh-chroma-failure-diagnosis.md), and [August recovery proof](./2026-08-24-tester-chroma-compatibility-recovery-proof.md). ADR-067 retirement authority was not exercised; ADR-082 Persona ownership, revisions, manifests, and bindings remain unchanged.

## Recovered and reconstructed control conditions

The retained prior driver establishes a fresh host temporary child directory, mode `0700`, mounted with `--mount type=bind,source=<child>,target=/probe`, using `--network none` and the exact image above. The original container and disposable directory were already removed; original effective Docker inspection and container ownership were not retained. Those historical values cannot be recovered and are not claimed as observed.

The same mechanism was reconstructed and inspected before probing. Host ownership was UID 501/GID 20, mode `0700`; Docker reported destination `/probe`, type `bind`, `RW=true`, empty mode string, propagation `rprivate`. Container-visible directory ownership was UID 0/GID 0, mode `0700`, unchanged before/after, with writability reported true. Thus effective read-write evidence is from the reproduced mechanism, not merely its intended configuration.

## Filesystem and SQLite ladder

Ordinary qualification created, appended, renamed, and deleted a file. SQLite qualification created a database/table, inserted and committed, reopened and checked the row count, then performed a second write transaction. Qualification files were removed before Chroma on passing locations.

| Location | Effective storage / container directory | Ordinary operations | Stdlib SQLite | Chroma |
| --- | --- | --- | --- | --- |
| Host temporary bind | Docker `RW=true`; UID/GID 0/0, `0700` | PASS | FAIL at first insert after table creation | Not run |
| Container-internal `/probe` | Disposable writable container layer; no mount; UID/GID 0/0, `0755` | PASS | PASS, including reopen/read and second transaction | First call PASS |
| Fresh named volume | Docker local volume, `RW=true`, mode `z`; UID/GID 0/0, `0755` | PASS | PASS, including reopen/read and second transaction | First call PASS |

Directory ownership/modes stayed unchanged. SQLite files were UID/GID 0/0, mode `0644`. The detailed failing bind database was 8,192 bytes. Its exception was:

```text
sqlite3.OperationalError: attempt to write a readonly database
sqlite_errorcode = 1032
sqlite_errorname = SQLITE_READONLY_DBMOVED
step = insert
```

Three fresh bind-only qualifications occurred: the initial driver aborted after the expected SQLite failure; the next run recorded that failure and continued to the independent controls; a final bind-only run captured the exact failing step and extended error code. No bind Chroma call occurred. Each independent storage mechanism was qualified once.

This establishes a SQLite write failure specific to the reproduced host-bind harness despite ordinary filesystem writes and an effective read-write mount. The mandated classification token includes “permission defect,” but the evidence does not establish incorrect UNIX permissions. The deeper host filesystem/file-identity cause of `SQLITE_READONLY_DBMOVED` remains unresolved. The previous empty Chroma result is invalid as a compatibility control.

## Qualified Chroma results

Each qualified location independently ran `PersistentClient(path="/probe")` followed by `get_or_create_collection(name="codexify_vault_supported")`, with `PYTHONFAULTHANDLER=1` and `RUST_BACKTRACE=1`, without network access. Both first calls exited 0 and reported one collection. No second calls were warranted or run.

Both resulting databases were 163,840 bytes, integrity `ok`, with 20 tables. Migration maximum/count pairs were `embeddings_queue=2/2`, `metadb=5/5`, and `sysdb=9/9`.

- Internal database SHA-256: `1f5599d6aac712b29c6327964d8b562589bd547df4255ec8c5e7aad69c2b96fe`.
- Named-volume database SHA-256: `b1492717c8d5b85ae781e4f9993549ef1590160e8f67b55aaa0439574e7a3c96`.

The August first-call partial state (16,384 bytes, only `acquire_write` and `migrations`, no migration rows, second call succeeding) was not reproduced. Current writable controls succeeded on their first calls; there is no current failed-Chroma partial-state fingerprint.

## Preservation and operator state

All task-created containers, host disposable directories, and the fresh named volume were removed after evidence capture. Restricted diagnostic receipts remain outside the repository at `/var/folders/j7/l5mjdtxn2fj_2sggfbl0407c0000gn/T/persona-empty-controls-0b_alpwf`; the driver is `/tmp/persona_empty_controls.py`. These contain empty-control evidence only.

Canonical Chroma was never opened by SQLite/Chroma, copied again, modified, renamed, retired, or deleted. The required read-only byte-manifest verification remained unchanged: `c12d9eecacf005c983fe1d2e917f7526cd5e8c0372845d3127329930bd69b19c`. The preserved-store probe was not rerun.

Final operator verification: PostgreSQL `d4e0f2a5b7c9`; backend stopped/exited; stack reconciliation suspended; tunnel LaunchAgent loaded; desired-up marker present. No application service started. PostgreSQL data and the rollback checkpoint were not changed. Source, Compose, configuration, provider, and runtime implementation remained unchanged.

## Validation and limits

Validation: `python3 scripts/validate_docs.py` and `git diff --check`; only this receipt and `docs/architecture/00-current-state.md` are task-owned changes. Their execution results are recorded in the task closeout.

Warning: Pi's non-inference catalog returned zero available model entries. No provider/model was invented, no delegation/inference occurred, and Pi was not repaired. Historical original effective mount metadata was unavailable; current reconstructed effective metadata is recorded above.

The expected bind qualification failure is diagnostic evidence, not a repaired runtime. Deployment lineage, live Persona routes, browser persistence, and canonical Chroma recovery remain pending.

Smallest next slice: separately authorize a corrected preserved-store-copy versus empty-store comparison using proven-writable disposable named-volume storage, then decide whether an ADR-067 recovery action is justified. No comparison or retirement was performed here.
