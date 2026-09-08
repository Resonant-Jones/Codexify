# Persona Chroma named-volume compatibility comparison

Date: 2026-09-07

Result: **PASS — PERSISTED_CHROMA_STORE_COMPATIBILITY_BOUNDARY**.

## Authority and frozen inputs

Branch `feature/persona-studio`, starting HEAD `e9f5b7ee9528a5f2f70b9865cdccb2e26bde0c12`, clean before execution. This comparison follows the [empty-control qualification](./2026-09-06-persona-private-preview-chroma-empty-control-diagnosis.md) and [preservation receipt](./2026-09-06-persona-private-preview-chroma-diagnosis.md).

Exact failed backend image: `sha256:2fda9cb708e0c6567062a52386dd1c99aa839545474c554cee34db7d90c4881b`.
Live exact-image metadata: Python 3.11.14, Chroma 1.0.15, SQLite 3.46.1, Linux ARM64 (`aarch64`). Collection: `codexify_vault_supported`.

Existing preservation: `/Volumes/Dev_SSD/Codexify-preservation/chroma/persona-20260906T230016Z/canonical-chroma`. Files remained read-only (`0400`), directories `0500`. Before copying, its relative-path/type/size/SHA-256 manifest matched the recorded digest:
`c12d9eecacf005c983fe1d2e917f7526cd5e8c0372845d3127329930bd69b19c`.
There were five files, 458,916 bytes, and no symlinks. Canonical active `.chroma` was not a seed input and was never opened by SQLite or Chroma. Read-only byte hashing implemented the brief's explicit before/after fingerprint requirement.

## Isolated storage qualification and seed equality

Two newly created Docker local named volumes, both effectively `RW=true` at `/probe`:

- Empty control: `persona-ab-20260907093210-empty`.
- Preserved copy: `persona-ab-20260907093210-preserved`.

Each used a separate disposable container, exact image above, network disabled, Python entrypoint, `PYTHONFAULTHANDLER=1`, and `RUST_BACKTRACE=1`. No application service started.

Both volumes independently passed ordinary file create/write/append/rename/delete and stdlib SQLite create-table/insert/commit/reopen/count/second-write checks before any Chroma call. Container directory ownership was UID/GID 0/0, mode `0755`, writable, unchanged before/after; qualification SQLite files were UID/GID 0/0, mode `0644`. Qualification files were removed before seeding or probing.

A disposable helper using the same image mounted only the existing preservation read-only at `/preservation` and the preserved-copy named volume read-write at `/probe`. It copied into the named volume and made only the disposable files writable. Before Chroma, full relative-path, file-type, size, content SHA-256 and aggregate-manifest equality passed. Seeded digest: `c12d9eecacf005c983fe1d2e917f7526cd5e8c0372845d3127329930bd69b19c`. Preservation was rechecked unchanged after copying.

## Identical first-call probes

Each ran exactly once:

```python
client = chromadb.PersistentClient(path="/probe")
client.get_or_create_collection(name="codexify_vault_supported")
```

| Evidence | Empty named volume | Preserved named volume |
| --- | --- | --- |
| Process exit | 0 | 1 (caught panic reported by diagnostic wrapper) |
| First call | Success; one collection | `pyo3_runtime.PanicException` during client initialization |
| Collection creation | Succeeded | Not reached; one existing collection remains |
| SQLite size | 163840 bytes | 290816 bytes |
| Tables | 20 | 21 |
| Integrity check | ok | ok |
| Migration max/count: embeddings_queue | 2/2 | 2/2 |
| Migration max/count: metadb | 5/5 | 6/6 |
| Migration max/count: sysdb | 9/9 | 10/10 |

Exact preserved-copy discriminator:

```text
range start index 10 out of range for slice of length 9
```

Message SHA-256: `2444dd0cee224b506b5f8ac1e0c94e7139e57fc08800734ef4477981ea8f0679`. Safe Python frames include `chromadb/__init__.py:164` (`PersistentClient`), `api/client.py:65`, `api/shared_system_client.py:32`, `config.py:471`, and `api/rust.py:112` (`start`). No row content, embeddings, document text, or metadata values were output. No second calls or retries occurred.

## Disposable mutation and preservation

The failed preserved-copy initialization changed disposable bytes:

- Pre-probe aggregate: `c12d9eecacf005c983fe1d2e917f7526cd5e8c0372845d3127329930bd69b19c`.
- Post-probe aggregate: `7fc245509677cb281436b68c727755ec2ba450d5dd8a027214f8e1b9bb53bab8`.
- Original SQLite SHA-256: `6c7ec4dbb5d063c28b7293e59abb5bf387ce4a5fe039e9d13ce5e5034c436247`.
- Post-probe SQLite SHA-256: `d96ada809acacc2ef6e86e57f54cc1ee2a9721caa2a5f830f9a580de96e4ca1a`.

Schema generations and SQLite size remained as above; unchanged structure does not imply unchanged bytes. The empty control created new state as expected, aggregate `6d22c4705a3a3652066fa85284904ea45cb928e6ac46ebd9ff5bbb8d99a2d2d3`.

Canonical and preservation final manifests each matched their pre-task digest `c12d9eecacf005c983fe1d2e917f7526cd5e8c0372845d3127329930bd69b19c`. No canonical copy, retirement, replacement, or initialization occurred. The existing preservation remains retained and read-only.

## Cleanup and live boundary

Both named volumes and probe containers were removed; the seed helper used automatic removal. Temporary comparison script/result files were removed after incorporating safe evidence into this receipt; no raw logs or manifests are retained by this task.

Before and after: PostgreSQL `d4e0f2a5b7c9`; backend `exited`; stack reconciliation suspended (LaunchAgent unloaded); tunnel LaunchAgent loaded; desired-up marker present. PostgreSQL and rollback checkpoint were not changed. No backend, frontend, worker, or other application startup occurred.

ADR-067 preserves PostgreSQL canonical authority and requires separately authorized retirement/recovery; none was exercised. ADR-082 Persona ownership, manifest, revision, and binding semantics remain unchanged. No source, dependency, Compose, configuration, or runtime implementation changed.

## Validation, warnings, and next boundary

Validation commands: `python3 scripts/validate_docs.py`, `git diff --check`, and staged diff checks. Only this receipt and `docs/architecture/00-current-state.md` are changed; results are reported in the task closeout.

The preserved-copy panic is the expected discriminating diagnostic failure, not a failed empty control. Warning: the host-bind SQLite issue remains unresolved; this comparison avoids that storage class. Pi was not used, following the task's explicit non-goal. No provider/model inference occurred.

This establishes the persisted-store compatibility prerequisite for a separately authorized ADR-067 preserve → retire → fresh-initialize recovery. It does not prove that canonical host storage can initialize SQLite successfully. The next recovery brief must account for that remaining storage boundary and require writer quiescence, preservation, runtime initialization, and health evidence. No recovery, deployed Persona lineage qualification, or browser persistence is claimed here.
