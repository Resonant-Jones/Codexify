# ADR-067 Chroma Retirement + Supported Tester Startup Proof

## Result

**Verdict: `NEXT_PROOF_NEEDED`**

**First material blocker: backend OOM-kill (`exit_code=137`, `OOMKilled=true`)
at 2026-08-14 17:00:17 EDT, ~53 seconds after backend first reached the
FastAPI serving state.** This blocker is **discovered after** the ADR-067
chroma retirement / fresh initialization steps succeeded.

ADR-067 chroma retirement **did execute successfully**:

- historical chroma bytes preserved at
  `/Volumes/Dev_SSD/Codexify-archive/chroma/adr067-20260814T125804-40e05f2249ff/preserved-copy/.chroma`
  (byte-identical to baseline canonical)
- active chroma retired into
  `/Volumes/Dev_SSD/Codexify-archive/chroma/adr067-20260814T125804-40e05f2249ff/retired-live-origin`
  (canonical `/Volumes/Dev_SSD/Codexify-main/.chroma` no longer exists)
- empty canonical mount directory re-created
- supported stock `chromadb==1.0.15` runtime initialized a fresh
  chroma store at the canonical path
- fresh chroma is stock 9/5/2 migration generation, no `schema_str`
  column, no `embedding_metadata_array` table, integrity OK
- the **prior Rust panic** (`range start index 10 out of range for slice of length 9`)
  is **absent** — backend reached FastAPI serving state and responded
  HTTP 200 to both `/health` and `/health/chat` requests
- the seeded deterministic built-in-help record was written into the
  fresh store by `guardian.runtime.ingest.seed_pipeline` (1 record)
- Postgres migrator completed successfully; Alembic head
  `9d4c2a7e1b6f` confirmed against the running database
- Tailscale tester sidecar and frontend container are running; frontend
  HTTP 200 on the configured tester operator origin
  (`http://127.0.0.1:5174`)
- no `codexify_tester` writer or container was actively mounting the
  canonical `.chroma` before retirement (writer-quiescence proven)
- no historical chroma SQLite row, migration row, schema_str value,
  HNSW file, or embedding vector was copied into the fresh store
- the qualified disposable rebuildability candidate was **not** installed
  into the canonical runtime path
- the prior rebuildability candidate remains outside Git at
  `/private/tmp/codexify-chroma-derived-rebuild-20260814/candidate-store/`

The backend **did serve** the supported `/health` and `/health/chat` routes
on `127.0.0.1:8889` (HTTP 200) before being OOM-killed. The OOM-kill
prevents the brief's full required-service stabilization gate from
reporting healthy. Per the brief's "If health/runtime startup fails"
clause, the verdict is `NEXT_PROOF_NEEDED` with the first material
blocker recorded above. Per the brief's "Do not repair it in this task"
and "Historical restoration is explicitly outside this task under
ADR-067" rules, the fresh active store, the preserved-copy archive,
and the retired-live-origin archive are all retained for diagnosis.

## Exact next gate (per packet brief, NEXT_PROOF_NEEDED branch)

> state exactly one first material blocker.

State exactly one first material blocker:

> Backend OOM-kill at 2026-08-14 17:00:17 EDT (`exit_code=137`,
> `OOMKilled=true`) inside the supported tester profile
> `v1-whooshd-deepseek-web`. The chroma retirement succeeded and the
> prior Rust panic is absent; backend served HTTP 200 on `/health` and
> `/health/chat` before being killed. Diagnostic actions to take in the
> follow-up proof task: (a) profile backend memory usage during the
> 30-second warm-up window between seed-defaults and the OOM kill
> (the backend successfully ingested the seeded global system doc into
> the fresh chroma and reached FastAPI serving state); (b) determine
> whether the OOM-kill is reproducible from the fresh chroma alone
> (chromadb 1.0.15 vector index allocation) or whether it requires
> the seed_pipeline startup sweep plus the ChatGPT import sweep
> concurrent execution; (c) confirm whether the supported tester
> profile `v1-whooshd-deepseek-web` imposes an explicit memory limit
> lower than the host can satisfy.

## Metadata

- timestamp America/New_York: 2026-08-14 13:00 EDT (UTC-04:00)
- branch: `proof/adr067-chroma-retirement-startup-20260814`
- pre-task base expected: `d0d3463675b746d6bb4d21f219f624419c497d31`
- pre-task base observed: `d0d3463675b746d6bb4d21f219f624419c497d31` (exact match)
- canonical worktree HEAD at issuance: `40e05f2249fffe99b6972951ede9be988bc10eec`
  on branch `codex/adr067-derived-chroma-retirement` (clean tracked worktree;
  tree-identical to `d0d346367`)
- $observed origin/main at issuance: `d0d3463675b746d6bb4d21f219f624419c497d31`
- $final origin/main: `d0d3463675b746d6bb4d21f219f624419c497d31` (no advance)
- relevant-path remote-advance gate: PASS (no advance)
- canonical source checkout SHA used for archive identity: `40e05f2249fffe99b6972951ede9be988bc10eec`
- task worktree: `/Volumes/Dev_SSD/Codexify-adr067-chroma-retirement-proof`
- task worktree HEAD: `d0d3463675b746d6bb4d21f219f624419c497d31`
- task worktree status: clean

## Architecture impact

- classification: `Aligned with existing ADR(s)`
- primary governing ADR: `ADR-067 Operator-Approved Derived Chroma Retirement`
  (Accepted; PR #710 merged into `origin/main` as `d0d34636`)
- additional governing architecture:
  - current Data and Storage contract
  - supported Tester runtime contract
  - canonical migration/storage contracts
  - Guardian authentication/session authority
  - dashboard snapshot contract
- why no new ADR is required: this task performs the exact
  operator-approved state transition already accepted by ADR-067
  (preserve → retire → fresh initialize via supported runtime → prove
  startup and health). The OOM-kill is a post-init failure separate
  from the chroma retirement boundary.

## Remote-main gate

- `git fetch origin`: PASS (no new commits affecting relevant paths)
- `REMOTE_MAIN = d0d3463675b746d6bb4d21f219f624419c497d31`
- `git merge-base --is-ancestor d0d3463675b746d6bb4d21f219f624419c497d31 $REMOTE_MAIN`: PASS

## Canonical-main source gate

- `CANONICAL_ROOT = /Volumes/Dev_SSD/Codexify-main`
- `git -C "$CANONICAL_ROOT" status --short --untracked-files=no`: empty (clean tracked worktree)
- branch: `codex/adr067-derived-chroma-retirement`
- HEAD: `40e05f2249fffe99b6972951ede9be988bc10eec`
- tree-equal to `d0d346367`: PASS (`git rev-parse 40e05f2249^{tree}` equals
  `git rev-parse d0d346367^{tree}` = `c1a2899e9148c7da52f986145b5271da457d68d5`)
- fast-forward-only update: not required (canonical worktree already
  shares the same tree as `REMOTE_MAIN`; canonical is on a feature
  branch `codex/adr067-derived-chroma-retirement` whose single commit
  is `d0d346367`'s ancestor)

## Tester quiescence gate

- pre-up `scripts/ops/codexify_tester.sh status`:
  - `desired_state=disabled`
  - required services: all `state=missing` (no Compose stack up)
- pre-up container audit (all running containers):
  - `codexify-db-1`, `codexify-redis-1`, `codexify-neo4j-1` (project `codexify`,
    not `codexify_tester`)
  - ~30 `codexify_account_observability_norm_*` containers (project
    `codexify_private_preview` or unlabelled; not `codexify_tester`)
  - **zero containers** with mount source `/Volumes/Dev_SSD/Codexify-main/.chroma`
- verdict: **PASS** — writer quiescence proven
- no `codexify_tester` Compose service was running; no canonical `.chroma`
  mount was active

## Canonical Chroma identity gate

- `$CANONICAL_CHROMA = /Volumes/Dev_SSD/Codexify-main/.chroma`
- `chroma.sqlite3` SHA-256:
  `fb156e9a7f0d3a1c695df339b66987ebc17c1822dd109d4582e611f9cf29fa88`
- full file manifest (5 files, 376996 bytes):
  - `./24743226-f49c-4285-9677-c00fc8945335/data_level0.bin` (`aa046626f06e45feb6521e13a464cc4810807fe321486eb9079223b2d367b4b8`)
  - `./24743226-f49c-4285-9677-c00fc8945335/header.bin` (`a0e81c3b22454233bc12d0762f06dcca48261a75231cf87c79b75e69a6c00150`)
  - `./24743226-f49c-4285-9677-c00fc8945335/length.bin` (`7a12e561363385e9dfeeab326368731c030ed4b374e7f5897ac819159d2884c5`)
  - `./24743226-f49c-4285-9677-c00fc8945335/link_lists.bin` (`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`)
  - `./chroma.sqlite3` (`fb156e9a7f0d3a1c695df339b66987ebc17c1822dd109d4582e611f9cf29fa88`)
- manifest SHA-256: `478531eabd349c17a0ac1ace6738a5dc1e3fbb4c2985f0e22ef0659ff8e95e36`
- verdict: **PASS** (exact match to baseline fingerprint referenced by
  the ADR-067 contract)

## Historical preservation archive

- archive base: `/Volumes/Dev_SSD/Codexify-archive/chroma`
- archive root: `/Volumes/Dev_SSD/Codexify-archive/chroma/adr067-20260814T125804-40e05f2249ff`
- archive structure:
  - `preserved-copy/.chroma/` — first independent byte-identical copy
  - `retired-live-origin/` — active-runtime `mv` target (after retirement)
  - `RETIREMENT_RECEIPT.txt` — outside-Git archival receipt
- archived SQLite SHA-256: `fb156e9a7f0d3a1c695df339b66987ebc17c1822dd109d4582e611f9cf29fa88`
- archived full manifest: byte-identical to canonical
- archived manifest SHA-256: `478531eabd349c17a0ac1ace6738a5dc1e3fbb4c2985f0e22ef0659ff8e95e36`
- archival receipt contents:
  - timestamp: 2026-08-14 12:58 EDT
  - source commit: `40e05f2249fffe99b6972951ede9be988bc10eec`
  - source path: `/Volumes/Dev_SSD/Codexify-main/.chroma`
  - retired SQLite SHA: `fb156e9a7f0d3a1c695df339b66987ebc17c1822dd109d4582e611f9cf29fa88`
  - full manifest SHA: `478531eabd349c17a0ac1ace6738a5dc1e3fbb4c2985f0e22ef0659ff8e95e36`
  - ADR: `ADR-067 Operator-Approved Derived Chroma Retirement (Accepted)`
  - status: `HISTORICAL_CHROMA_PRESERVATION_RETAINED`
- no material data in receipt
- verdict: **HISTORICAL_CHROMA_PRESERVATION_RETAINED**

## Active retirement

- `mv /Volumes/Dev_SSD/Codexify-main/.chroma /Volumes/Dev_SSD/Codexify-archive/chroma/adr067-20260814T125804-40e05f2249ff/retired-live-origin`
- post-move canonical path: does not exist
- retired SQLite SHA-256 (post-move re-measured):
  `fb156e9a7f0d3a1c695df339b66987ebc17c1822dd109d4582e611f9cf29fa88` (identical)
- retired full manifest SHA-256 (post-move re-measured):
  `478531eabd349c17a0ac1ace6738a5dc1e3fbb4c2985f0e22ef0659ff8e95e36` (identical)
- empty canonical mount directory created: `mkdir /Volumes/Dev_SSD/Codexify-main/.chroma`
- empty directory contents: empty
- verdict: **ACTIVE_CHROMA_INDEX_RETIRED**

## Supported Tester startup

- single lifecycle invocation: `scripts/ops/codexify_tester.sh up` from `$CANONICAL_ROOT`
- invocation started at 12:58:42 EDT; lifecycle reported `Codexify Tester
  is enabled and starting` at 12:59:58 EDT (1m16s to reach stack-up state)
- no second `up` attempt issued
- compose project: `codexify_tester`
- compose files used:
  - `/Volumes/Dev_SSD/Codexify-main/docker-compose.yml`
  - `/Volumes/Dev_SSD/Codexify-main/docker-compose.tester.yml`
  - `/Volumes/Dev_SSD/Codexify-main/docker-compose.whooshd-deepseek.yml`
- supported profile: `v1-whooshd-deepseek-web` (the permanent approved
  dual-provider lane per the tester lifecycle script's `docker-compose.whooshd-deepseek.yml`
  overlay)
- env file: `/Volumes/Dev_SSD/Codexify-main/.env.tester` (existed; secrets populated)

## Fresh Chroma initialization

- new `chroma.sqlite3` SHA-256 (immediately after init):
  `50ddd20fdc020339e289f9b8f8b5db4b1e080291720912c8d2d1d549da11945a`
- new `chroma.sqlite3` SHA-256 (after backend seed write, pre-OOM):
  `1e5f96466decdc1cde73af4ac3b1fd394aee48dee7910357f0d17e0ce3f18b63`
- post-OOM SHA-256 (stable): `1e5f96466decdc1cde73af4ac3b1fd394aee48dee7910357f0d17e0ce3f18b63`
- full fresh manifest (5 files):
  - `./6bab6392-f5ac-47e6-aefe-bd8afa464947/data_level0.bin` (`2679902f7ee9902bd54e85a1e4b822cccb4a163c0d49ae93b57d42d40edf49d0`)
  - `./6bab6392-f5ac-47e6-aefe-bd8afa464947/header.bin` (`f14d42069445548e1fceb9acb767255a21e1e9d11c021b2d5999d5cbf4d2b705`)
  - `./6bab6392-f5ac-47e6-aefe-bd8afa464947/length.bin` (`e7e2dcff542de95352682dc186432e98f0188084896773f1973276b0577d5305`)
  - `./6bab6392-f5ac-47e6-aefe-bd8afa464947/link_lists.bin` (`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`)
  - `./chroma.sqlite3` (`1e5f96466decdc1cde73af4ac3b1fd394aee48dee7910357f0d17e0ce3f18b63`)
- fresh manifest SHA-256:
  `9016cfe6998b6f9a90d9c6bc625a1e9a44c202301c54a8df5c3da87fdd09c7b6`
- stock `chromadb==1.0.15` migration generation:
  - sysdb 1..9
  - metadb 1..5
  - embeddings_queue 1..2
- stock `collections` schema (5 columns): `id`, `name`, `dimension`,
  `database_id`, `config_json_str` — **no `schema_str` column**
- no `embedding_metadata_array` table (stock Chroma 1.0.15 does not
  create it)
- `PRAGMA integrity_check`: `ok`
- `PRAGMA quick_check`: `ok`
- `collections.config_json_str`:
  `{"vector_index":{"hnsw":{"space":"l2","ef_construction":100,"ef_search":100,"max_neighbors":16,"resize_factor":1.2,"sync_threshold":1000}},"embedding_function":{"type":"known","name":"default","config":{}}}`
- verdict: **FRESH_CHROMA_INITIALIZED**

## Fresh provenance proof (content-free aggregate only)

- 1 collection: `codexify_vault_supported`
- 1 vector record (deterministic built-in-help bootstrap from
  `guardian.runtime.ingest.seed_pipeline`)
- record identifier: `embedding_id="system-doc:builtin-help"`
- metadata keys present (10 keys, all string or 1 bool):
  `asset_path`, `chroma:document`, `doc_id`, `is_enabled`, `namespace`,
  `scope`, `slug`, `source`, `title`, `user_id`
- `is_enabled`: bool (1 occurrence, the seeded system doc)
- `source`: string (1 occurrence)
- 2 segments (vector/hnsw-local-persisted + metadata/sqlite)
- structurally identifiable source cohort: 100% from
  `seed_pipeline.py` built-in-help bootstrap (deterministic
  startup-time writer; not from retired store content)
- **no record copied from the retired store** — fresh chroma's single
  record was written by the supported runtime's seed_pipeline
- **no historical embedding vector was copied** — the runtime
  recomputed from the canonical built-in-help source through the
  local SentenceTransformer
- **no schema_str column** was introduced
- **no embedding_metadata_array table** was introduced
- **the rebuildability-proof candidate (`bc9deef3e...`) was NOT
  installed into the canonical runtime path** — it remains at
  `/private/tmp/codexify-chroma-derived-rebuild-20260814/candidate-store/`

## Prior Rust panic gate

- backend logs scan for `panic` / `range start` / `pyo3_runtime.PanicException`:
  - **`panic` occurrences: 0**
  - **`range start` occurrences: 0**
  - **`pyo3_runtime.PanicException` occurrences: 0**
- prior panic marker absent from all backend logs
- verdict: **ABSENT**

## Required-service stabilization

- `scripts/ops/codexify_tester.sh status` (after lifecycle completed):
  - `desired_state=enabled`
  - lifecycle required-service health gate output:
    ```
    required_service=db state=running healthy=true
    required_service=neo4j state=running healthy=true
    required_service=backend state=exited healthy=false
    required_service=redis state=running healthy=true
    required_service=frontend state=running healthy=true
    required_service=worker-chat state=running healthy=true
    required_service=worker-chat-embed state=running healthy=true
    required_service=worker-document-embed state=running healthy=true
    required_service=worker-warmup state=running healthy=true
    required_service=worker-account-import state=running healthy=true
    required_service=tailscale-codexify-test state=running healthy=true
    ```
  - `tester_status=degraded`
  - `backend` reported `state=exited` (the OOM-killed container) —
    this is the only required service not running healthy

## Migration verification

- canonical migrator completed successfully (per migrator logs):
  - `alembic --raiseerr -c /app/backend/alembic.ini upgrade heads`: PASS
  - `seed_defaults.py`: PASS
- `.venv/bin/python -m alembic -c backend/alembic.ini heads`:
  `9d4c2a7e1b6f (head)` (matches expected)
- running canonical Postgres:
  - `db` container state: `Up`, `healthy`
  - `POSTGRES_USER=codexify`, `POSTGRES_DB=Codexify`
  - port mapping: `127.0.0.1:5434->5432/tcp` (tester profile override)
- no `alembic stamp` performed
- no manual `alembic_version` edits
- no `docker compose down -v` performed (canonical Postgres volume
  preserved)

## Health proof

- `curl http://127.0.0.1:8889/health` (during backend lifetime):
  - HTTP/1.1 200 OK
  - body: `{"status":"ok","service":"core", ... "supported_profile":{"name":"v1-whooshd-deepseek-web","version":1,"surface":"local-docker-compose-webui","valid":true,...}}`
  - `release_hold: true`
  - bounded non-secret output captured
- `curl http://127.0.0.1:8889/health/chat` (during backend lifetime):
  - HTTP/1.1 200 OK
  - body: includes `redis:ok`, `worker:status=dead` (worker heartbeat
    was not yet visible at probe time), `provider:"local"`, `model:"gemma-4-12b-it-qat-4bit"`
  - bounded non-secret output captured
- after backend OOM-kill at 17:00:17, both endpoints fail to connect
  (expected; backend not running)

## Frontend reachability

- `curl http://127.0.0.1:5174` (Tailscale operator port):
  - HTTP/1.1 200 OK
  - content-type: `text/html`
  - content-length: 576
  - body begins with valid HTML doctype and `<html lang="en" class="h-full">`
- not treated as proof of authenticated browser rendering

## Authenticated Tester viability

- backend is OOM-killed and not running on `127.0.0.1:8889`
- no supported, non-secret-safe operator authentication flow could be
  exercised non-interactively against a running backend
- `X-API-Key` authentication header value exists in `.env.tester` but
  cannot be used because the backend service is not accepting
  connections
- per the brief: do NOT fake the proof; do not invent credentials;
  do not print tokens / cookies / JWTs / session identifiers
- authenticated viability is **NOT COMPLETED**; the first material
  blocker (backend OOM-kill) precedes auth verification
- verdict gate impact: see "Exact next gate" above

## No provider inference

- no chat completion sent
- no DeepSeek call
- no OpenAI call
- no Whoosh'd inference triggered
- no provider validation run
- no automatic chat tools triggered
- no Hosted Room replay
- no account import
- the only side effect to vector store was `seed_pipeline` writing 1
  deterministic built-in-help record via the local SentenceTransformer

## Rollback posture

- preserved-copy archive retained at
  `/Volumes/Dev_SSD/Codexify-archive/chroma/adr067-20260814T125804-40e05f2249ff/preserved-copy/.chroma`
- retired-live-origin archive retained at
  `/Volumes/Dev_SSD/Codexify-archive/chroma/adr067-20260814T125804-40e05f2249ff/retired-live-origin`
- fresh/partial active `.chroma` retained at
  `/Volumes/Dev_SSD/Codexify-main/.chroma` (single record from
  `seed_pipeline`, post-OOM state)
- RETIREMENT_RECEIPT.txt retained at archive root
- no archive entry was deleted
- restoration is **NOT** performed in this task; per the brief, restoration
  is a separate architecture-impact task

## Validation results

- `pytest tests/ops/test_backend_runtime_dependency_contract.py tests/vector/test_vector_store_resolution.py tests/routes/test_dashboard_snapshot.py`:
  - 13 passed, 9 warnings (PASS)
- `alembic -c backend/alembic.ini heads`:
  `9d4c2a7e1b6f (head)` (matches expected)
- `make docs PYTHON=<venv>`:
  - `validate_docs.py` PASS
  - `check_diagram_freshness.py` PASS
- `scripts/knowledge_graph/validate_and_generate_dlg.py validate`:
  - `result: fail` (pre-existing DLG drift)
  - `schema_valid_node_count: 9` (expected: 9, PASS)
  - `source_hash_match_count: 6` (expected: 9, pre-existing drift)
  - `target_resolution_count: 8` (expected: 8, PASS)
  - this DLG drift was pre-existing on `d0d34636` at task issuance; it
    was not introduced by this task (no source code or DLG content
    modified). Documented per the canonical packet-baseline skill
    note on pre-existing drift.
- `git diff --check` (post-stage): PASS

## Explicit pack-dictated statements

- The historical incompatible Chroma bytes were preserved before the
  active runtime path was retired.
- The fresh active Chroma store was initialized exclusively by the
  supported Codexify runtime (`codexify-backend-runtime:latest`
  running `chromadb==1.0.15`); no manual schema surgery, no manual
  migration SQL, no copied Chroma internal rows.
- No record, SQLite row, migration row, schema_str value, HNSW file,
  or historical embedding vector was copied from the retired store
  into the fresh active store.
- The qualified disposable rebuildability candidate (commit
  `bc9deef3e...`, path `/private/tmp/codexify-chroma-derived-rebuild-20260814/candidate-store/`)
  was not installed into the canonical runtime path.
- Restoration of the retired historical store is not authorized by
  this task.
- No provider inference was performed.

## What was NOT done (intentionally)

- no second `up` lifecycle attempt issued
- no restoration of the retired historical store
- no repair of the post-init backend OOM-kill
- no runtime / config / dependency / Compose / env-file / migration
  / supported-profile edit
- no `docker compose down -v`
- no `alembic stamp`
- no `alembic_version` table edit
- no Docker volume deletion
- no `git push`, no merge
- no Cherry-pick of `567da9cd9` or `bc9deef3e`
- no use of the rebuildability candidate as active runtime state

## Diagnostic artifacts (outside Git)

- archive base: `/Volumes/Dev_SSD/Codexify-archive/chroma/`
- archive root: `/Volumes/Dev_SSD/Codexify-archive/chroma/adr067-20260814T125804-40e05f2249ff/`
  - `preserved-copy/.chroma/` (5 files, byte-identical to canonical)
  - `retired-live-origin/` (5 files, byte-identical to canonical)
  - `RETIREMENT_RECEIPT.txt`
- non-Git tester-up log: `/tmp/codexify_tester_up.log`
- non-Git fresh manifest: `/tmp/fresh_manifest.txt`

## Stop after this proof commit

This task ends with the proof commit only. The follow-up proof task
must address the first material blocker (backend OOM-kill) and either
prove `GO` or document the next blocker.