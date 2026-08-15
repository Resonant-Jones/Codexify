# Chroma store generation reconciliation proof

## Result

**NEXT_PROOF_NEEDED**

Fail-closed before any reconciliation mutation. The authorized unused-artifact
premise for `collections.schema_str` is false: the sole preserved collection
row carries a non-null, non-empty 1697-byte JSON object. The task requires
`schema_str IS NOT NULL = 0` and non-empty `schema_str = 0` before any
schema-generation transformation. That gate failed on a disposable copy whose
bytes are identical to the live store and to the prior diagnostic fingerprint.

No live-store swap was performed. No reconciled candidate was produced.

## Metadata

- date/time America/New_York: 2026-08-13 22:23 EDT (UTC-04:00)
- branch: `proof/chroma-store-generation-reconciliation`
- pre-task checkout HEAD: `791252aae54b991e2546eadd4fb72e8fd2571528`
  on `proof/chroma-startup-isolation` (one later commit after the required
  diagnostic; that branch was left untouched at this SHA)
- tested source HEAD: `653e58f61e54d09c96e78e3b3f7fd4e19f457899`
  (`git switch -c proof/chroma-store-generation-reconciliation 653e58f61...`;
  verified `HEAD` equals the diagnostic commit)
- origin/main: `53ce6f971e67fdbd008a9e02d7ee70ce3c32433d`
  (advanced from the handoff SHA `cff739d9bdf73c06a08f8095b40a256d203cd72e`;
  this task did not merge, rebase, or otherwise consume that advance)
- diagnostic prerequisite commit: `653e58f61e54d09c96e78e3b3f7fd4e19f457899`
- canonical runtime image: `codexify-backend-runtime:latest`
  `sha256:cc06585cd1acf230bad9c06d7db9d619d65c70ba6b5ad556acbae58466019384`
  (linux/arm64; rebuilt after the diagnostic image
  `sha256:c3d893be56e033b8d98382ae8feb9b7039e6ac6076fcc0bd7f05dafdc5c023b3`;
  independently re-verified as stock `chromadb==1.0.15`)

## Architecture impact

- classification: `Aligned with existing ADR(s)`
- governing contracts:
  - `docs/architecture/data-and-storage.md`
  - `docs/architecture/config-and-ops.md`
  - `guardian/runtime/embed/embedder.py` (`CODEXIFY_VECTOR_STORE=chroma`,
    `CODEXIFY_CHROMA_PATH=./.chroma`)
  - `backend/vector_store/chroma_store.py`
  - `backend/requirements.txt` pin `chromadb==1.0.15`
  - Compose bind mount `./.chroma:/app/.chroma`
- why no new ADR is required: this task proposed no architecture change and
  performed no live mutation. The accepted architecture already uses persistent
  Chroma retrieval storage. Evidence shows the authorized lossless
  transformation cannot proceed because a supposedly-unused schema artifact
  contains material persisted data. Per the packet, that is a STOP /
  `NEXT_PROOF_NEEDED` outcome, not an in-task architecture change.

## Diagnostic prerequisite

- `653e58f61e54d09c96e78e3b3f7fd4e19f457899` local availability:
  `git cat-file -e 653e58f61e54d09c96e78e3b3f7fd4e19f457899^{commit}` → exit 0
- parent/ancestry:
  `git merge-base --is-ancestor 9894437b40d38e47b5c578793e932b12692fda62 653e58f61e54d09c96e78e3b3f7fd4e19f457899`
  → PASS
- diagnostic commit vs prerequisite changes only:
  `docs/architecture/proofs/2026-08-13-chroma-backend-startup-isolation-proof.md`
- diagnostic proof path:
  `docs/architecture/proofs/2026-08-13-chroma-backend-startup-isolation-proof.md`
- root-cause classification (unchanged from diagnostic):
  `PERSISTED_STORE_COMPATIBILITY_BOUNDARY`

## Live-store precondition

- actual live host path: `/Volumes/Dev_SSD/Codexify-main/.chroma`
  (resolved from Compose `./.chroma:/app/.chroma` +
  `CODEXIFY_CHROMA_PATH=./.chroma` under Tester root
  `CODEXIFY_TESTER_REPO_ROOT=/Volumes/Dev_SSD/Codexify-main`)
- file count: 5
- bytes: 376996
- manifest SHA-256:
  `8cc745602fd9acafb4103bdec3102d048391e930d2423d3d78187d7decd44a91`
- `chroma.sqlite3` SHA-256:
  `fb156e9a7f0d3a1c695df339b66987ebc17c1822dd109d4582e611f9cf29fa88`
- equality with diagnostic baseline: **PASS** (exact match)

Fingerprint method: the same deterministic walk used by the diagnostic
(`/tmp/chroma_diag_tools/fingerprint.py`): sorted relative path, byte size,
SHA-256 only.

Tester state at the fingerprint/copy boundary: `desired_state=disabled`;
`scripts/ops/codexify_tester.sh down` completed; `codexify_tester` `ps --all`
empty. No running container mounted `.chroma`. An unrelated default-project
`codexify-backend-1` existed in `exited (3)` state with a read/write bind
definition but was not running. Docker Desktop held directory-level read
handles only.

## Canonical Chroma generation

Independently inspected inside `codexify-backend-runtime:latest`
(`chromadb==1.0.15`,
`/usr/local/lib/python3.11/site-packages/chromadb/migrations/`):

- sysdb 1..9
  - `00001-collections.sqlite.sql`
  - `00002-segments.sqlite.sql`
  - `00003-collection-dimension.sqlite.sql`
  - `00004-tenants-databases.sqlite.sql`
  - `00005-remove-topic.sqlite.sql`
  - `00006-collection-segment-metadata.sqlite.sql`
  - `00007-collection-config.sqlite.sql`
  - `00008-maintenance-log.sqlite.sql`
  - `00009-segment-collection-not-null.sqlite.sql`
- metadb 1..5
  - `00001-embedding-metadata.sqlite.sql`
  - `00002-embedding-metadata.sqlite.sql`
  - `00003-full-text-tokenize.sqlite.sql`
  - `00004-metadata-indices.sqlite.sql`
  - `00005-max-seq-id-int.sqlite.sql`
- embeddings_queue 1..2
  - `00001-embeddings.sqlite.sql`
  - `00002-embeddings-queue-config.sqlite.sql`

No sysdb `00010-*` and no metadb `00006-*` exist in the stock runtime.

## Preserved generation

Inspected on `reconciled-copy/chroma.sqlite3` in read-only URI mode.
Migration table columns: `dir`, `version`, `filename`, `sql`, `hash`.

- sysdb 1..10
- metadb 1..6
- embeddings_queue 1..2

Exact extra migration records:

- sysdb `00010-collection-schema.sqlite.sql`
- metadb `00006-metadata-array-support.sqlite.sql`

## Pre-reconciliation data/integrity

Read-only inspection of the disposable `reconciled-copy` only.

- `PRAGMA integrity_check`: `ok`
- `PRAGMA quick_check`: `ok`
- canonical collection: `codexify_vault_supported`
- collection count: 1
- embedding/record count: 10
- segment count: 2
- database count: 1
- tenant count: 1

No stored document text, embeddings, IDs, or user metadata values were
emitted.

## Extra-artifact proof

### `collections.schema_str`

- column exists: YES (`collections` columns:
  `id`, `name`, `dimension`, `database_id`, `config_json_str`, `schema_str`)
- non-null rows: **1** (required: 0)
- non-empty rows: **1** (required: 0)
- structural characterization of the single non-null value (payload not
  recorded):
  - SQLite `typeof`: `text`
  - length: 1697
  - non-whitespace length: 1697
  - first codepoint: 123 (`{`)
  - looks like JSON object: YES
  - looks like JSON array: NO
  - looks like JSON `null` token: NO
  - SHA-256 of payload only:
    `66728296c3a1852fb7d1dfe52fdcf4588ddd5fd29244d9babfb04711f27d4777`

Classification: **MATERIAL_PERSISTED_DATA**.

This contradicts the diagnostic receipt's prose claim that `schema_str` was
NULL for every collection row. The live `chroma.sqlite3` SHA-256 is identical
to that diagnostic's fingerprint, so the prior NULL observation was incorrect;
the bytes have not changed since the diagnostic.

### `embedding_metadata_array`

- table exists: YES
- row count: **0** (required: 0) — unused-artifact premise HOLDS for this table
- exact index names (all reference only `embedding_metadata_array`):
  1. `embedding_metadata_array_id_key`
     — `ON embedding_metadata_array (id, key)`
  2. `embedding_metadata_array_key_float`
     — `ON embedding_metadata_array (key, float_value) WHERE float_value IS NOT NULL`
  3. `embedding_metadata_array_key_int`
     — `ON embedding_metadata_array (key, int_value) WHERE int_value IS NOT NULL`
  4. `embedding_metadata_array_key_string`
     — `ON embedding_metadata_array (key, string_value) WHERE string_value IS NOT NULL`
- dependent-object result:
  - expected hits only: the `embedding_metadata_array` table itself, its four
    indexes, and the `collections` table definition (because it declares
    `schema_str`)
  - unexpected views / triggers / foreign-key references / other SQL
    definitions: **NONE**
  - `PRAGMA foreign_key_list` hits on extra artifacts: **NONE**

The metadb extra table is still a proven-empty compatibility artifact. The
sysdb extra column is not.

## Reconciliation transaction

**NOT ATTEMPTED.**

Fail-closed at extra-artifact proof step 20 before `BEGIN IMMEDIATE`.

- exact sysdb migration row removed: N/A
- exact metadb migration row removed: N/A
- exact indexes removed: N/A
- `embedding_metadata_array` removed: N/A
- `collections.schema_str` removed: N/A
- transaction result: **NOT STARTED**

No alternative repair was introduced.

## Post-reconciliation integrity

**NOT APPLICABLE** — no mutation was performed.

- integrity_check: not re-run as a post-mutation check (pre-check remains `ok`)
- quick_check: not re-run as a post-mutation check (pre-check remains `ok`)
- canonical 9/5/2 migration generation: NOT PRODUCED (store remains 10/6/2)
- expected artifact absence: NOT PRODUCED
- unexpected schema delta result: NONE (no schema change)

## Retrieval preservation

Pre-reconciliation bounded counts (disposable copy, unchanged):

- collection `codexify_vault_supported`: present
- collection count: 1
- embeddings/records: 10
- segments: 2
- databases: 1
- tenants: 1

Post-reconciliation counts: N/A (no mutation).

All 10 existing records remain on the unmutated copies and on the live store.
No record was rebuilt. No document was re-embedded.

## Direct canonical Chroma proof

**NOT RUN.** No golden reconciled candidate exists. The packet forbids opening
`reconciled-copy` with Chroma after reconciliation and requires a clone of a
successful candidate; that candidate was never produced.

- runtime image: `codexify-backend-runtime:latest`
  `sha256:cc06585cd1acf230bad9c06d7db9d619d65c70ba6b5ad556acbae58466019384`
- Chroma version (image, independently verified): `1.0.15`
- PersistentClient result: NOT RUN
- list_collections result: NOT RUN
- canonical collection: NOT RE-PROBED via Chroma
- `count()` result: NOT RUN
- panic status: NOT RE-EXERCISED in this task
  (prior diagnostic still stands: stock 1.0.15 panics on the unrepaired
  10/6/2 generation)

## Backend-equivalent proof

**NOT RUN.** Fail-closed before mutation; no backend-probe copy of a
reconciled candidate was created.

- backend startup result: NOT RUN
- HTTP serving result: NOT RUN
- bounded stability window: NOT RUN
- panic status: NOT RE-EXERCISED

Diagnostic `db` / `neo4j` / `redis` services were not started.

## Clean-store regression

**NOT RUN.** The fail-closed stop occurred before optional independent
runtime probes. The prior diagnostic already proved a clean empty store
opens under stock `chromadb==1.0.15`.

## Candidate identity

No proposed live-swap candidate was produced.

- candidate directory: NONE
- files / bytes / candidate manifest SHA-256 / candidate `chroma.sqlite3`
  SHA-256: N/A

Retained outside Git (unmodified; not a swap candidate):

- `/private/tmp/codexify-chroma-reconcile.cH3CIM/source-copy`
- `/private/tmp/codexify-chroma-reconcile.cH3CIM/reference-copy`
- `/private/tmp/codexify-chroma-reconcile.cH3CIM/reconciled-copy`
  (byte-identical to source; never mutated)
- prior diagnostic directory `/private/tmp/codexify-chroma-isolation.01ecKb`
  (not deleted)

## Live-store postcondition

- final real-store fingerprint (same deterministic manifest):
  - files = 5
  - bytes = 376996
  - manifest SHA-256 =
    `8cc745602fd9acafb4103bdec3102d048391e930d2423d3d78187d7decd44a91`
  - `chroma.sqlite3` SHA-256 =
    `fb156e9a7f0d3a1c695df339b66987ebc17c1822dd109d4582e611f9cf29fa88`
- exact before/after equality result: **PASS — identical**

## Persistent-state safety

- live `.chroma` was never modified
- all inspection occurred on disposable copies in read-only SQLite URI mode
- no retrieval record was rebuilt
- no document was re-embedded
- Postgres was not modified; Alembic was not run
- no model/provider inference occurred
- no Hosted Room owner/guest replay occurred
- `chromadb==1.0.15` was not changed
- `backend/requirements.txt` was not changed
- Compose was not changed
- `CODEXIFY_VECTOR_STORE` was not changed
- FAISS was not selected
- the live store was not swapped

## Release impact

No beta/release widening.

## Live swap status

`LIVE STORE SWAP NOT PERFORMED`

## Exact next task

`Copy-first collections.schema_str material-data classification against stock chromadb==1.0.15. Determine whether the 1697-byte JSON object on the sole canonical collection is a default/empty schema envelope that the pinned runtime neither reads nor requires, or a material persisted collection schema whose removal would change retrieval semantics. Do not drop schema_str, do not delete migration rows, and do not swap the live store until that classification is proven. If unused-by-runtime is proven, re-authorize a copy-first reconciliation task with an explicit schema_str exception. If material, lossless generation reconciliation under the current authorized transformation is not possible.`

After that classification reaches GO **and** a later copy-first reconciliation
reaches GO:

`Operator-gated live Chroma store swap using the proven reconciled candidate, with atomic rollback preparation and immediate canonical PersistentClient verification. Do not start the full Tester inside that swap task.`

After that swap reaches GO:

`Rerun the preserved Tester startup/auth proof through /health, /health/chat, and authenticated GET /api/dashboard/snapshot.`

Only after startup/auth reaches GO:

`Resume Stage 2K.6 Hosted Room owner/guest live replay.`

## Proof surface / validation

- Relevant existing tests searched with
  `rg -n "Chroma|chromadb|PersistentClient|VectorStore|CODEXIFY_CHROMA_PATH" tests`.
  Hits are unit/integration files that mock Chroma, use temporary empty
  paths, or exercise VectorStore abstractions. None cover persisted
  non-stock Chroma generation compatibility.
- Governing statement:
  `No existing automated test covers this persisted non-stock Chroma generation; copy-level operational proof is the governing validation surface.`
- Those files were not executed in this task: they cannot decide the
  fail-closed `schema_str` gate, and several construct PersistentClient
  against temporary stores.
- DLG:
  `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/knowledge_graph/validate_and_generate_dlg.py validate`
  → **PASS** (`result=pass`,
  `repository_revision=653e58f61e54d09c96e78e3b3f7fd4e19f457899`)
- Docs:
  `make docs PYTHON=.venv/bin/python`
  → **PASS** (`validate_docs.py` passed;
  `check_diagram_freshness.py` passed; pre-existing Makefile duplicate-target
  warning unchanged)
- `git diff --check`: **PASS**
- Scope after receipt commit: only this file
