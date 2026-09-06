# Persona private-preview Chroma diagnosis

Date: 2026-09-06
Result: **BLOCKED — INSUFFICIENT_DIAGNOSTIC_EVIDENCE**.

The preserved-copy probe reproduces a persisted-state panic, but the empty
control also fails with a different SQLite error. Neither a successful empty
control nor the same failure in both controls was established. No repair class
A, B, or C can therefore be selected under the task's decision table.

## Scope and runtime identity

Source: clean `feature/persona-studio` at
`8a3e30a0c543d0af6c0a6a0d7ab6a55d5a2e764a`.
Failed backend container: `a120cb2113232c3dbcbcc2caea2bee4bfc0d521113254358a1e5e4411d4a060e`.
Exact probe image: `sha256:2fda9cb708e0c6567062a52386dd1c99aa839545474c554cee34db7d90c4881b`.
Runtime: Linux ARM64 (`aarch64`), Python 3.11.14, chromadb 1.0.15,
SQLite 3.46.1; `chromadb_rust_bindings` present.

The stopped backend log shows `pyo3_runtime.PanicException` through Guardian
service initialization, vector store construction, backend embedder
`_create_chroma_client`, `PersistentClient`, and `chromadb.api.rust.start`.
Raw bounded logs are retained outside Git with mode 0600. No general
environment or user-content output was retained in this document.

## Active path and preservation

Container metadata explicitly supplied:

- `CODEXIFY_VECTOR_STORE=chroma`;
- `CODEXIFY_CHROMA_PATH=./.chroma`;
- `CODEXIFY_COLLECTION=codexify_vault_supported`;
- working-directory resolution to `/app/.chroma`;
- read-write bind mount from `/Users/chriscastillo/.codex/worktrees/dda8/Codexify-main/.chroma` to `/app/.chroma`.

Before preservation, all running-container mounts were checked for this path
or an overlapping parent/child read-write source: none matched. The backend
remained stopped. The canonical path was never opened through Chroma.

Preservation:
`/Volumes/Dev_SSD/Codexify-preservation/chroma/persona-20260906T230016Z/canonical-chroma`.

It was copied byte-for-byte under the pre-existing ADR-067 preservation root,
verified against a relative-path/type/size/SHA-256 manifest, then made read-only
(files 0400, directories 0500, enclosing evidence directory 0700).

- Files: 5; aggregate bytes: 458916; symlinks: 0.
- Aggregate manifest SHA-256: `c12d9eecacf005c983fe1d2e917f7526cd5e8c0372845d3127329930bd69b19c`.
- SQLite size: 290816 bytes.
- SQLite SHA-256: `6c7ec4dbb5d063c28b7293e59abb5bf387ce4a5fe039e9d13ce5e5034c436247`.
- Four binary index files; no WAL, SHM, or journal files observed.
- Source and preservation manifests were equal before probing and rechecked
  equal afterward. Canonical bytes were unchanged.

## Query-only structural inspection

Only the preservation's SQLite file was opened, with `mode=ro`, `immutable=1`,
and `PRAGMA query_only=ON`. Absence of WAL/journal files was established.

- `quick_check=ok`; `integrity_check=ok`.
- Tables: 21; indexes: 20.
- Collections: 1; segments: 2; embeddings: 32.
- Migration directory maximum/count: `embeddings_queue=2/2`, `metadb=6/6`,
  `sysdb=10/10`.
- Collections columns include `config_json_str` and `schema_str`.
- Table names: `acquire_write`, `collection_metadata`, `collections`, `databases`, `embedding_fulltext_search`, `embedding_fulltext_search_config`, `embedding_fulltext_search_content`, `embedding_fulltext_search_data`, `embedding_fulltext_search_docsize`, `embedding_fulltext_search_idx`, `embedding_metadata`, `embedding_metadata_array`, `embeddings`, `embeddings_queue`, `embeddings_queue_config`, `maintenance_log`, `max_seq_id`, `migrations`, `segment_metadata`, `segments`, `tenants`.

No row content, embedding payload, document text, or metadata value was read
for this structural report. The sysdb generation and preserved-copy panic
resemble the ADR-067-era compatibility boundary; this resemblance does not
substitute for the failed control comparison.

## Exact-image probes

Exactly one empty-state probe and one writable-preservation-copy probe ran.
Each used the exact failed image, a separate temporary host directory mounted
at `/probe`, `--network none`, `--entrypoint python`, `PYTHONFAULTHANDLER=1`, and
`RUST_BACKTRACE=1`. The only Chroma operations were:

```python
client = chromadb.PersistentClient(path="/probe")
client.get_or_create_collection(name="codexify_vault_supported")
```

No application startup, model, embedding, chat, or provider inference ran.
Both disposable directories were removed afterward; probe containers used
`--rm`. Logs and structural summaries remain outside Git in the preservation
parent directory.

### Empty control

Exit **1**; collection creation did not complete. Failure at
`chromadb.api.rust.start`:

```text
chromadb.errors.InternalError: error returned from database:
(code: 1032) attempt to write a readonly database
```

Initialization created partial SQLite state: integrity/quick checks `ok`,
`acquire_write` and `migrations` tables, one index, zero migration rows, and no
collection/segment/embedding tables. The temporary directory was created
writable (0700), but that alone does not prove Docker/SQLite write semantics.
The causal filesystem/runtime reason for error 1032 is unresolved.

### Writable preserved-copy reproduction

Exit **1**; collection creation did not complete. Exact sanitized signature:

```text
thread '<unnamed>' panicked at rust/sqlite/src/db.rs:157:42:
range start index 10 out of range for slice of length 9
pyo3_runtime.PanicException
```

Python failure again terminates at `chromadb/api/rust.py:112`, `start`.
The original 21 tables, migration generations, counts, and integrity results
remained structurally unchanged. Initialization nevertheless changed the copy's
byte manifest:

- Before: `c12d9eecacf005c983fe1d2e917f7526cd5e8c0372845d3127329930bd69b19c`.
- After: `7fc245509677cb281436b68c727755ec2ba450d5dd8a027214f8e1b9bb53bab8`.

That mutation occurred only on the disposable copy; it was not normalized or
applied to canonical state. No retry or schema surgery was performed.

## Classification and next prerequisite

**INSUFFICIENT_DIAGNOSTIC_EVIDENCE**: the control failed differently from the
preserved-copy reproduction. This does not qualify store retirement and does
not prove that both stores suffer one current runtime defect.

The smallest next slice is a bounded diagnosis of the empty-control SQLite
1032 write failure on disposable state, including Docker bind-mount/SQLite
write behavior. Obtain a valid empty-store control before selecting a
persisted-store repair, or prove a common causal initialization defect before
selecting runtime repair. Do not retire or initialize the canonical index.

## Preserved operator state and validation

PostgreSQL remains `d4e0f2a5b7c9`. Backend remains exited; no application service
was restarted. Stack reconciliation remains unloaded; tunnel LaunchAgent
loaded; desired-up present. The retained PostgreSQL checkpoint was not modified.
No source, dependencies, Compose, profiles, migrations, or canonical Chroma
files changed. ADR-067 retirement authority was not executed, and ADR-082
Persona/account authority remains unchanged.

Warnings: Pi catalog returned no available models, so no delegation occurred.
Probe failures are recorded above; backend recovery is not claimed.
`python3 scripts/validate_docs.py`, working/staged diff checks passed.
Only this authorized receipt changed. Current-state remains unchanged because
no concrete causal repair classification was established. No push or merge.
