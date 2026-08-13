# Chroma persistent-store backend startup panic isolation proof

## Result

**ROOT_CAUSE_BOUNDED**

The reproducible backend startup panic is classified as:

`PERSISTED_STORE_COMPATIBILITY_BOUNDARY`

The preserved `.chroma` persistent store was written by a **non-stock chromadb
build** that applied two migrations the canonical runtime does not ship:

- sysdb `00010-collection-schema.sqlite.sql`
- metadb `00006-metadata-array-support.sqlite.sql`

The canonical pinned runtime (`chromadb==1.0.15`, stock PyPI wheel) ships only
9 sysdb and 5 metadb migrations. On `PersistentClient` construction the
Rust sysdb migration validator slices its 9-entry migration list at index 10
(derived from the store's applied migration count) and panics:

```text
thread '<unnamed>' panicked at rust/sqlite/src/db.rs:157:42:
range start index 10 out of range for slice of length 9
```

This is not a corruption defect and not a backend integration defect: the
store is SQLite-integrity-clean, a clean/empty store initializes perfectly
under the same runtime, and the panic is fully reproduced by a 9-line direct
`PersistentClient` probe inside the canonical image.

## Metadata

- timestamp America/New_York: 2026-08-13 19:58 EDT (UTC-04:00)
- branch: `proof/chroma-startup-isolation`
- pre-task HEAD: `9894437b40d38e47b5c578793e932b12692fda62`
  (published prerequisite: `proof/preserved-tester-startup-auth`)
- tested source HEAD: `9894437b40d38e47b5c578793e932b12692fda62`
- origin/main: `cff739d9bdf73c06a08f8095b40a256d203cd72e`
- prerequisite proof commit: `9894437b40d38e47b5c578793e932b12692fda62`
  (verified: `origin/proof/preserved-tester-startup-auth` resolves to it)
- runtime image: `codexify-backend-runtime:latest`
  `sha256:c3d893be56e033b8d98382ae8feb9b7039e6ac6076fcc0bd7f05dafdc5c023b3`
- platform: `linux/arm64`
- runtime drift vs origin/main: NONE
  (`git diff --name-only origin/main..HEAD` = 2 proof receipts only;
  no runtime/config/dependency/vector-store file differs)

## Architecture impact

- classification: `Aligned with existing ADR(s)`
- governing contracts: existing storage/vector-store contracts
  (`docs/architecture/data-and-storage.md`, `guardian/vector/store.py`,
  `backend/rag/embedder.py`, `guardian/core/config.py`);
  no ADR, migration, model, runtime, Compose, or dependency file changed.
- confirmation no architecture was changed: CONFIRMED — `git status --short`
  empty before the receipt commit; the only repository change is this file.

## Existing blocker

Recorded exactly once:

```text
thread '<unnamed>' panicked at rust/sqlite/src/db.rs:157:42:
range start index 10 out of range for slice of length 9
```

## Runtime identity

- Python: 3.11.14
- Chroma: 1.0.15 (stock PyPI wheel; `chromadb_rust_bindings.abi3.so` present;
  `dist-info` has no `direct_url.json`)
- SQLite: 3.46.1 (system SQLite linked into Python 3.11)
- relevant package identity: `chromadb==1.0.15` with compiled
  `chromadb_rust_bindings` extension; image migration directories:
  sysdb 00001–00009, metadb 00001–00005, embeddings_queue 00001–00002.
- No vendored/alternate chromadb exists at `/app`; `PYTHONPATH=/app` resolves
  to the same site-packages module (verified by `chromadb.__file__`).

## Effective Chroma configuration

- vector-store type: `chroma` (compose default
  `${CODEXIFY_VECTOR_STORE:-chroma}`; `.env.tester` overrides nothing)
- effective container Chroma path: `/app/.chroma`
  (`CODEXIFY_CHROMA_PATH=./.chroma` resolved via
  `Path(expanduser()).resolve()` under backend `working_dir=/app`)
- host mount source: `/Volumes/Dev_SSD/Codexify-main/.chroma`
  (compose `./.chroma:/app/.chroma`)
- container destination: `/app/.chroma`
- collection identifier (canonical config): `codexify_vault_supported`
  (compose default; matches the single collection row in the preserved store)
- `.env.tester` contains NO `CODEXIFY_VECTOR_STORE` / `CODEXIFY_CHROMA_PATH`
  / `CODEXIFY_COLLECTION` / `CHROMA_*` / `ALLOW_RESET` / `MIGRATIONS` values.

## Real-store fingerprint

Fingerprint procedure: deterministic walk (sorted relative path, byte size,
SHA-256) — no application-level contents read.

| Metric | Pre-test | Post-test |
| --- | --- | --- |
| file count | 5 | 5 |
| total bytes | 376,996 | 376,996 |
| manifest SHA-256 | `8cc745602fd9acafb4103bdec3102d048391e930d2423d3d78187d7decd44a91` | `8cc745602fd9acafb4103bdec3102d048391e930d2423d3d78187d7decd44a91` |
| `chroma.sqlite3` SHA-256 | `fb156e9a7f0d3a1c695df339b66987ebc17c1822dd109d4582e611f9cf29fa88` | `fb156e9a7f0d3a1c695df339b66987ebc17c1822dd109d4582e611f9cf29fa88` |

**Before/after equality: PASS — the real store was not modified.**

## SQLite structural inspection

Performed on a disposable copy only (`preserved-copy`), read-only URI mode:

- `PRAGMA integrity_check`: `ok`
- `PRAGMA quick_check`: `ok`
- `PRAGMA user_version`: `0`
- `PRAGMA journal_mode`: `delete`
- table count: 21 (incl. `embedding_metadata_array` — non-canonical)
- index count: 20 (incl. `embedding_metadata_array_*` indexes — non-canonical)
- migration metadata (bounded):
  - sysdb: 1..10 — includes `00010-collection-schema.sqlite.sql` (non-canonical)
  - metadb: 1..6 — includes `00006-metadata-array-support.sqlite.sql` (non-canonical)
  - embeddings_queue: 1..2 (canonical)
- bounded row counts: `embeddings=10`, `collections=1`,
  `databases=1`, `tenants=1`, `segments=2`, `max_seq_id=1`
- no document text, embeddings, metadata values, or user identifiers emitted.

Classification: `SQLITE_INTEGRITY_PASS`.

Comparative evidence: a store freshly created by the canonical runtime
(Experiment B) contains sysdb 1..9, metadb 1..5, embeddings_queue 1..2,
20 tables, no `embedding_metadata_array`. The preserved store is exactly
one sysdb and one metadb migration AHEAD of the canonical generation.

## Direct Chroma experiment

Probe (run inside the canonical image, `RUST_BACKTRACE=full`): import
`chromadb`, print version, `PersistentClient(path=/diag/chroma)`,
`list_collections()`; print `persistent_client=ok` + collection count only.

| Store | Exit | PersistentClient | list_collections | Panic |
| --- | --- | --- | --- | --- |
| preserved-copy | 1 | NO | NOT REACHED | YES — `rust/sqlite/src/db.rs:157:42: range start index 10 out of range for slice of length 9` |
| empty-store | 0 | ok | ok (0 collections) | NO |

## Rust backtrace boundary

- Nearest Python-facing call (from the preserved-copy probe traceback):
  `chromadb/__init__.py:164 PersistentClient` →
  `chromadb/api/client.py:65` →
  `chromadb/api/shared_system_client.py:32 _create_system_if_not_exists` →
  `chromadb/config.py:471 start` →
  `chromadb/api/rust.py:112 start` →
  `self.bindings = chromadb_rust_bindings.Bindings(...)` →
  `pyo3_runtime.PanicException: range start index 10 out of range for slice of length 9`
- Rust panic site: `rust/sqlite/src/db.rs:157:42`. Upstream source for the
  pinned version confirms line 157 is inside
  `validate_migrations_and_get_unapplied`:

  ```rust
  let unapplied = source_migrations[applied_migrations.len()..].to_vec();
  ```

  With `applied_migrations.len() == 10` (from the store's sysdb rows) and
  `source_migrations` = the runtime's 9 sysdb migrations, the slice range
  start 10 exceeds length 9 → panic. The Rust symbols are stripped in the
  wheel, so frames show `<unknown>`; the panic location line identifies the
  site unambiguously.
- complete raw logs retained outside Git (see below); durable receipt
  records only the bounded summary above.

## Backend-equivalent experiment

Started only `db neo4j redis` (healthy), then ran disposable containers from
the canonical `backend` service definition with ONLY `RUST_BACKTRACE=full`
and `CODEXIFY_CHROMA_PATH=/diag/chroma` overridden; no ports published.

| Store | Backend startup result | First failure/success boundary |
| --- | --- | --- |
| preserved-copy | PANIC, exit 3 | `[embedder] backend=sentence_transformer model=/models/bge-large-en-v1.5` → immediate Rust panic in `PersistentClient` (exact same panic) |
| empty-store | SUCCESS | full startup: embedder init → seed `count=1` into fresh store → uvicorn serving HTTP 200 for a bounded 10-minute observation window, then terminated |

Note on provenance: the empty-store backend run mounted an empty directory
that Docker created for the bind source; it is functionally identical to
step 25's prescribed empty-store run (canonical service definition, empty
store at the effective path) and is recorded as such.

## Root-cause classification

`PERSISTED_STORE_COMPATIBILITY_BOUNDARY`

Primary matrix: preserved-copy = PANIC, empty-store = PASS (case A).

Supporting evidence:

1. SQLite integrity of the preserved store: PASS — the store is healthy,
   not corrupted.
2. The preserved store's migration metadata is one sysdb and one metadb
   migration ahead of the canonical runtime's migration set.
3. No upstream chromadb release ships those two migrations — verified
   against PyPI wheel contents for 1.0.15, 1.0.16, 1.0.17, and current
   releases up to 1.5.9. The store was therefore written by a non-stock
   chromadb build (fork/dev build), i.e. a newer-generation store.
4. The panic index (10) and slice length (9) exactly match the
   store's sysdb applied-migration count (10) vs the runtime's sysdb
   migration count (9), at the source line identified above.
5. A clean store under the same runtime initializes and persists correctly;
   the backend fully starts against an empty store, proving no backend
   integration seam (other than the store itself) is at fault.
6. The panic occurs inside the Rust bindings constructor, before any
   application-level Chroma operation; it is independent of embedding
   model state.

## What is proven

- The panic is caused by the persisted Chroma store generation, not by the
  canonical runtime in isolation and not by a later backend integration seam.
- The exact failing Rust statement is identified:
  `source_migrations[applied_migrations.len()..]` with applied=10 vs
  source length 9 (chromadb 1.0.15, `rust/sqlite/src/db.rs:157`).
- The preserved store was written by a non-stock chromadb build whose
  migration set (sysdb 1..10, metadb 1..6) exceeds every upstream release.
- The preserved store is SQLite-integrity-clean with 10 embeddings in
  collection `codexify_vault_supported`.
- The canonical runtime initializes clean stores; the backend-equivalent
  empty-store run reached uvicorn serving and seeded the vector store.
- The real `.chroma` directory is byte-identical before and after this task.

## What is not proven

- no repair was applied (diagnostic only; real store untouched);
- the supported Tester remains unqualified (`/health`, `/health/chat`,
  authenticated `/api/dashboard/snapshot` remain unproven);
- Hosted Room replay remains unperformed;
- no release widening;
- the actor/time that wrote the non-canonical store generation was not
  identified (out of scope for this diagnostic).

## Persistent-state safety

- real `.chroma` store NOT modified (fingerprint equality PASS);
- all Chroma mutation/testing occurred only on disposable copies
  (`preserved-copy`, `probe-c1`, `probe-c2`, `backend-copy`, `empty-store`
  under the private diagnostic directory);
- Postgres was touched only by normal service startup (`seed_defaults.py`
  idempotent seeding during the two backend-equivalent runs); no schema or
  migration changes, no manual SQL;
- no user data, document text, embeddings, metadata values, API keys,
  session material, or secrets were dumped or recorded.

## Exact repair recommendation

Authorize ONE atomic repair task:

**Chroma store generation reconciliation (copy-first) for the preserved
Tester.**

Goal: produce a canonical-compatible copy of the preserved `.chroma` store
that opens cleanly under the pinned `chromadb==1.0.15` runtime, and replace
the live store only after operator approval.

Required contents of that task:

1. Work exclusively on fresh copies; the live `/Volumes/Dev_SSD/Codexify-main/.chroma`
   remains read-only until the operator approves replacement.
2. Reconcile the two non-canonical migration artifacts on the copy:
   - sysdb `00010-collection-schema.sqlite.sql` — added
     `collections.schema_str TEXT` (prove the column is NULL/empty for all
     rows and the migration row is removable);
   - metadb `00006-metadata-array-support.sqlite.sql` — added the
     `embedding_metadata_array` table + its 4 indexes (preserved store shows
     `embedding_metadata_array` row count 0; prove no writer depends on it).
3. On the copy only: drop the empty `embedding_metadata_array` table and its
   indexes, drop the `collections.schema_str` column (SQLite `DROP COLUMN`
   or table-rebuild), and delete the two non-canonical rows from the
   `migrations` table so the store's applied set matches the canonical
   9/5/2 generation.
4. Validate the reconciled copy with the canonical image:
   `chromadb.PersistentClient(path=...)` must construct without panic,
   `list_collections()` must return the existing collection
   (`codexify_vault_supported`), and a bounded count query must show the
   10 preserved embeddings intact. Add a clean-store regression test
   (`PersistentClient` on empty path) to the task's validation surface.
5. Commit proof artifacts; then request operator approval to swap the
   reconciled store into the live path (physical + logical backups retained
   first, matching prior task practice).
6. After the swap, rerun the canonical preserved Tester startup/auth proof
   from lifecycle startup through authenticated `GET /api/dashboard/snapshot`
   to reach GO. Stage 2K.6 Hosted Room owner/guest replay resumes only after
   that GO.

Forbidden in that task: changing the pinned Chroma version, editing
`backend/requirements.txt`, switching to FAISS, changing vector-store
authority/durability semantics, editing runtime/Compose/config code, or
treating the preserved retrieval state as disposable without the
copy-first proof above.

Note: no upstream Chroma-provided migration/repair CLI exists that can fix
this generation mismatch (verified: stock wheels up to 1.5.9 do not contain
the store's migrations); a schema-level reconciliation on a copy is the
only viable repair path consistent with the pinned dependency.

## Proof surface / validation

- Real-store fingerprint equality: PASS (identical manifest + sqlite SHA-256)
- Direct preserved-copy probe: PANIC (exit 1) — recorded
- Direct empty-store probe: PASS (exit 0) — recorded
- Full Rust backtrace: captured; raw log SHA-256:
  `45f7f93661285ff2f656282eb5207a0f77ec341d511193a7a8552b6449029d8c`
  (`experiment-A.stderr`, complete frames)
- Backend-equivalent experiment: preserved-copy PANIC (exit 3),
  empty-store SUCCESS — recorded
- Relevant existing tests (files referencing
  `CodexifyEmbedder|PersistentClient|CODEXIFY_CHROMA_PATH|chromadb`):
  - `tests/vector/test_vector_store_resolution.py`: 2 passed
  - `tests/obsidian/test_file_lifecycle.py`,
    `tests/obsidian/test_ingest_idempotency.py`: passed (Chroma
    `PersistentClient` open/write paths)
  - `tests/obsidian/test_live_runtime_proof.py`: 1 failed —
    `ValueError: MemoryOSRetriever requires user_id` (test-harness
    pre-existing condition unrelated to Chroma store opening; the test
    uses the mock embedder; no repository code was changed by this task)
- DLG validation: PASS
  (result `pass`, repository_revision `9894437b40d38e47b5c578793e932b12692fda62`)
- Documentation validation: PASS
  (`validate_docs.py` and `check_diagram_freshness.py` both passed)
- `git diff --check`: PASS (empty)
- Scope: only this receipt; no runtime/config/dependency file changed.

## Raw diagnostic artifacts (outside Git)

Directory: `/private/tmp/codexify-chroma-isolation.01ecKb` (mode 0700)

| Artifact | SHA-256 |
| --- | --- |
| experiment-A.stderr (preserved-copy direct probe, full backtrace) | `45f7f93661285ff2f656282eb5207a0f77ec341d511193a7a8552b6449029d8c` |
| experiment-A.stdout | `482afebd7d4b4eb8d1a84887bef41288c4b9c758d9474595ece952f5f3f7037d` |
| experiment-B.stderr (empty store, empty) | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| experiment-B.stdout | `513ed26bad8de9303927668a8f3d256ee1fcb7a985817c295194aaa7f5578d22` |
| backend-c2.stderr (backend-equivalent preserved-copy panic) | `8c417dd03a303b756566969a32ff3038ad377c5bac6dfa0ddead70a670df5507` |
| backend-c2.stdout | `b5bf5d4d7d04244a7384dc7bde0da89aad672dfcf471660bc6a81ad9a5ae308e` |
| backend-preserved.stderr (backend-equivalent empty-store success) | `f05bae4cfc117793fa8e20d01d93ac65b660d1893af0b285427c5080c2f25485` |
| backend-preserved.stdout | `4a7e2b0fadb3280db582958bb14e6a94991ade881b0d83531c986cb34deae426` |
| real-store-pre.manifest | (see fingerprint table) |

Disposable copies `preserved-copy`, `probe-c1`, `probe-c2`, `backend-copy`,
`empty-store` are retained under the same directory.

## Cleanup state

- disposable diagnostic containers: removed (all `--rm` runs exited;
  no `*backend-run*` containers remain)
- db/neo4j/redis diagnostic services: stopped via Compose (`stop`, not
  `down -v`; named volumes preserved)
- Tester desired_state: `disabled` (marker cleared by the task's opening
  quiesce; no re-enable performed)
- `$CHROMA_DIAG` retained (required until receipt committed)

## What Axis should add to his KB

1. The Chroma panic is a persisted-store generation mismatch: the preserved
   `.chroma` was written by a non-stock chromadb build carrying sysdb
   `00010-collection-schema` and metadb `00006-metadata-array-support`
   migrations. No upstream chromadb release (through 1.5.9) ships them.
2. Stock `chromadb==1.0.15` panics (not errors) on a newer-generation store:
   `rust/sqlite/src/db.rs:157` slices `source_migrations[applied..]` with
   applied=10 vs 9 available → `range start index 10 out of range for slice
   of length 9`. It is an upstream robustness bug triggered by the
   store/runtime generation gap; the store itself is SQLite-healthy with
   10 embeddings in `codexify_vault_supported`.
3. The canonical runtime and backend work fine against an empty store
   (backend-equivalent run served HTTP 200 and seeded the vector store),
   so no Codexify runtime, config, or integration seam needs repair.
4. The real store was fingerprint-verified byte-identical before/after the
   diagnostic; all experiments ran on disposable copies.
5. Next: one atomic copy-first reconciliation task (remove the two
   non-canonical migration rows + their provably-empty schema artifacts on
   a copy, validate with the canonical image, operator-approved swap), then
   rerun the preserved Tester startup/auth proof to GO.
