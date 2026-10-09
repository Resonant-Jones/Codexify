# Candidate runtime checkpoint and restore

## Approved campaign policy

This operator capability provides a cold-volume **candidate rollback checkpoint**,
not a user-facing backup product, off-host backup, disaster recovery, archival
storage, or high availability. PostgreSQL remains canonical domain truth; Redis
is operational state, Chroma derived/admitted state under ADR-101, and Neo4j
retains its existing feature boundary. No ADR changes. Release HOLD.

The explicitly approved campaign root is
`/Volumes/Dev_SSD/offload/codex/checkpoints/`. Current-candidate checkpoints belong
under `codexify_candidate_28c95_20261005/` below that root. The helper accepts an
explicit root; it has no global default. It generates each immutable identity
from UTC time, project identity and a random collision-resistant suffix. It
never selects “latest.” Operator-supplied IDs are accepted only as explicit
`cp-...` identities and can never be reused, including after a failed attempt.

“Independent” means operator-owned host storage outside Docker volumes, all
source/Git worktrees, candidate runtime scratch, `/private/tmp`, and candidate
read-write mounts. It survives container recreation. It does not protect against
loss of the physical host/disk; the same underlying storage device is accepted
for this bounded campaign. There is no automatic pruning, keep-latest behavior,
retention timer, or deletion on restore/success. Cleanup requires separate
operator authority. Completed and failed artifacts remain outside Git.

## Scope and primitive

[`candidate_runtime_checkpoint.py`](../../scripts/ops/candidate_runtime_checkpoint.py)
is a standard-library Python operator CLI with `plan`, `create`, `validate` and
`restore`. It never closes admission, dequeues tasks, changes deadlines, stops or
starts application/storage services, migrates a schema, admits a new Chroma
store, or reconciles Compose. Those remain explicit operator prerequisites.

Capture uses the installed runtime's Docker-managed local volumes after every
application writer and storage engine in the named project has cleanly exited.
PostgreSQL `/var/lib/postgresql/data`, Redis `/data`, Neo4j `/data` and the exact
admitted Chroma `/app/.chroma` root are archived cold, with numeric ownership,
permissions, directory structure and file bytes preserved. There are no schema
transformations or cross-version conversions. Restore/readback must use the
same recorded PostgreSQL/Redis/Neo4j/runtime image IDs. Bind-backed volumes,
ambiguous stores, extra installations sharing a protected volume and nonregular
archive members are refused. Mutable image tags and network pulls are refused.

Redis final persistence is separately checked: a clean exit alone is insufficient;
creation requires a saved-RDB record after the last shutdown request and before
the clean-exit record from that container's latest run. This captures its persisted operational state, including absolute
expiry times. Rollback does not reset elapsed time or resurrect expired locks.
An unknown/no-save/failed Redis shutdown cannot be promoted into an exact rollback
claim. Redis queues and locks are never flushed or rewritten for capture.

Chroma's archived admission marker must agree with volume name, creation identity,
project, ADR-101 and admission nonce. Same-project rollback requires the original
volume identities to remain present. Historical Chroma bytes are never selected.
A separately selected isolated clone retains original marker bytes and does not
acquire authority to start supported consumers as a new admitted installation.

The archiving/restoration helper is an already-local immutable Python runtime
image, run without network, with a read-only root filesystem, no Docker socket,
1 CPU, 512MiB RAM and a process bound. Source volume mounts are read-only. Only
explicitly confirmed restore targets are read-write. Helpers have unique names
and ownership labels; normal exit removes them, and failure/timeout cleanup
rechecks the helper label before removing that exact owned helper. No broad
container, volume or Docker cleanup occurs.

## Custody and writer closure

`plan` is observational. For the explicitly named project it lists services,
container/image IDs, four volume identities, destination, capture artifacts,
ordering and blockers as OBSERVED / PLANNED / BLOCKED. It does not claim that
planned actions were executed. Source size probes are deferred until cold capture.

The operator must serialize the entire lifecycle with other owners:

1. Establish exclusive candidate custody, including the recovery Goal's files
   and any surviving process. An empty process-pattern scan is not ownership proof.
2. Close new admission through the approved candidate operation procedure.
3. Drain queued/accepted work under its original accepted deadlines and obtain
   durable terminal disposition. Preserve unconsumed non-chat system queue work.
4. Stop application writers after proving their work released. The committed chat
   worker signal drain and 13m5s grace differ from document embedding's 10s grace,
   which does not bound active tasks. This helper does not invent abandonment.
5. Stop PostgreSQL, Redis and Neo4j cleanly and verify final Redis persistence.
6. Run create only after all project services are exited, non-OOM and exit 0;
   all protected volume attachments must belong solely to the explicit project.
7. Validate the completed checkpoint before any candidate mutation. Return the
   original service posture only through a separately approved operation.

Queue length zero alone proves none of these closure steps. Creation checks
closure and resource identity repeatedly before, between and after captures.
It fails closed on drift. A host lock serializes publication in a destination's
project directory; it does not grant custody or prevent an outside operator from
issuing Docker commands. Exclusive lifecycle ownership remains a human boundary.

## Command surface

From repository root:

```bash
python3 scripts/ops/candidate_runtime_checkpoint.py --help
python3 scripts/ops/candidate_runtime_checkpoint.py plan \
  --project codexify_candidate_28c95_20261005 \
  --destination /Volumes/Dev_SSD/offload/codex/checkpoints \
  --helper-image sha256:bcb55917283fc2d6f23b7891b11c06fcebb5ec811e82eb5d62491e09b404ccb6
```

The following create command is for a **later explicitly authorized task**, only
with the named project's fully closed writers/engines and refreshed schema
observation. It is not executed against the live candidate in this implementation
slice. The `--schema-revision` is an explicit operator read-only observation;
it is labelled as such, not falsely inferred from a stopped PostgreSQL directory.

```bash
python3 scripts/ops/candidate_runtime_checkpoint.py create \
  --project codexify_candidate_28c95_20261005 \
  --destination /Volumes/Dev_SSD/offload/codex/checkpoints \
  --helper-image sha256:bcb55917283fc2d6f23b7891b11c06fcebb5ec811e82eb5d62491e09b404ccb6 \
  --confirm checkpoint:codexify_candidate_28c95_20261005 \
  --schema-revision f8c2a91d6b40 \
  --source-revision a165a34475a20c3a1aad95c41b3d69c041d9b14e \
  --client-revision c511f154bf70175672a6a9e78e854827482a4b73
```

The client argument records a supplied prepared-client identity; it does not
claim the currently served client uses that source. Backend image provenance
`685cea098` and prepared current client `c511f154b` remain separate. The currently
running candidate still uses its pre-adoption `a165a3447` image/source posture.

Creation emits a JSON result with the exact checkpoint path/ID. `validate`
requires `--project` and `--checkpoint` explicitly; it performs file/hash/archive
checks without Docker runtime access. `restore` additionally requires
`--source-project`, `--targets` (a JSON object mapping exactly `postgres`, `redis`,
`chroma`, `neo4j` to four distinct existing named volumes) and
`--confirm restore:SOURCE_PROJECT:CHECKPOINT_ID:TARGET_PROJECT`.

Same-project restore requires the four original source volume creation/ownership
identities, stopped target services and matching recorded service images. It
refuses another project's attachments, ambiguous volumes and live/paused target
writers. Cross-project restore additionally requires `--isolated`, distinct
source/target projects, entirely different target volume identities, and explicit
Compose-project ownership labels on every target volume. It cannot silently
redirect original candidate state to another installation.

No restore infers a checkpoint, creates target volumes, stops engines or starts
services. Every required artifact and archive path is checked before the first
target write. Archive traversal, links, devices and duplicate paths are refused.
Restoration overwrites only the four selected stopped volumes, then compares
complete file/directory inventories with the archived originals. If restore fails,
keep every target stopped; the completed checkpoint remains unchanged and can be
revalidated before an explicitly selected retry. Cross-store restoration is not
an atomic transaction, and a failure must never be described as completed rollback.

## Manifest and atomic completion

Schema version 1 records checkpoint/project/time, repository and supplied source/
client identities, container/image/service sets, mounts and store creation/
admission identities, schema observation, closure evidence, queue-observation
limits, archive filenames, sizes, SHA-256 hashes and per-member byte/metadata
inventories. It contains no message bodies, credential values, API keys or tokens.
Runtime configuration needed to reconstruct the original posture is retained in
`runtime-config.json`, a separate protected artifact which can contain credentials.
Database/archive artifacts contain private data too; do not print, publish or
commit them. Source/config/cache mount identities are recorded; those externally
pinned resources are not automatically archived or rewritten.

Creation reserves `.incomplete-CHECKPOINT_ID`, retains it on failure, captures
all four stores, hashes and verifies all archives/marker identities, fsyncs the
artifacts, writes the final manifest and hashed COMPLETE record, then atomically
renames to CHECKPOINT_ID and fsyncs the parent. Completed directories are 0500;
files are 0400. Normal validation/restoration rejects incomplete directories,
missing/extra artifacts, wrong schema/project, corrupt metadata and failed hashes.
The tool never writes a completed checkpoint or reuses its identity. These are
operator filesystem/CLI protections, not protection against a malicious owner
who can alter permissions or forge an unsigned manifest.

## Validation and proof boundary

Failure-path tests and the gated disposable four-store proof live in
[`test_candidate_runtime_checkpoint.py`](../../tests/ops/test_candidate_runtime_checkpoint.py).
The test uses existing local PostgreSQL 15, Redis 7, Neo4j 5 community and the
prepared backend's actual Chroma runtime. It never pulls an image, publishes a
port, uses the real candidate volumes, or starts a supported consumer against a
cloned admission identity. Fixture processes have bounded resources and private
Docker isolation. The proof deliberately mutates all four original fixture
stores, restores into four different explicit volumes, verifies actual runtime
readback plus absolute Redis expiry, revalidates unchanged checkpoint hashes and
removes only fixture-owned Docker resources. Completed checkpoint artifacts are
retained under the explicit proof destination.

Run normal narrow tests with the repository Python environment; enable the live
Docker proof only through the explicit environment variable:

```bash
/Volumes/Dev_SSD/Codexify-main/.venv/bin/python -m pytest -v tests/ops/test_candidate_runtime_checkpoint.py
CODEXIFY_CHECKPOINT_PROOF_ROOT=/Volumes/Dev_SSD/offload/codex/checkpoints/disposable-proof-20261007-01a116f7 \
  /Volumes/Dev_SSD/Codexify-main/.venv/bin/python -m pytest -v -s tests/ops/test_candidate_runtime_checkpoint.py -k disposable_four_store_round_trip
python3 -m py_compile scripts/ops/candidate_runtime_checkpoint.py tests/ops/test_candidate_runtime_checkpoint.py
```

A skipped Docker test is not round-trip proof. Final observed proof outcome,
fixture identities, checkpoint hashes and preservation receipts must be reviewed
before considering this capability qualified. Real-candidate closure, checkpoint,
restore, ordinary chat, embedding activation, adoption and restart qualification
remain unperformed. Successful disposable proof does not change release HOLD or
authorize adoption. The next eligible slice is separately authorized real-candidate
checkpoint creation/validation and return to its original running posture.

Structured pre-closure queue observations may be supplied repeatedly as
`--queue-observation queue_name=count`; only bounded queue names and numeric counts
are accepted. The manifest labels these as operator observations, never closure
authority. Missing observations are explicitly recorded as not supplied and must
be resolved by the later candidate operator; zero counts do not permit capture.

## Observed implementation receipt — 2026-10-07

Implementation source HEAD: `6dac75d443cd6b807235f91c03d11c45b16cf2ec`.
Governing contracts: ADR-101 plus existing PostgreSQL canonical-authority,
Redis operational-state, request/terminal and runtime-identity boundaries.
No new ADR or runtime semantics. Only the helper, its ops tests, this contract
and the stopped native-adoption runbook are changed.

**Proven in disposable fixture:** the final narrow command above, with the Docker
proof enabled, collected and passed **22 tests in 81.17 seconds**. Create,
validate, deliberate source mutation, isolated restore and actual readback passed
for PostgreSQL 15, Redis 7, Neo4j 5 community and the prepared backend's Chroma.
The fixture used no network, published ports or downloaded embeddings; an explicit
loopback hostname entry permits Neo4j initialization. Both projects used their
own four storage volumes plus a separately owned Neo4j log volume. Every final
fixture container/volume was removed after ownership verification; subsequent
project-scoped lists were empty. Completed checkpoint bytes remain retained.

Source project: `cfy-checkpoint-proof-0d16836cf960`. Target project:
`cfy-checkpoint-restore-0d16836cf960`. Checkpoint:
`/Volumes/Dev_SSD/offload/codex/checkpoints/disposable-proof-20261007-01a116f7/cfy-checkpoint-proof-0d16836cf960/cp-20261007T182657456059Z-e0e1d1e3-78e9bd44`.
Create/validate/restore/readback: **PASS**.
Manifest SHA-256 before and after restore:
`6820a7991e4676eee66b5b0602340f4ed07096931fa991e862eeb0aac6995902`.
All seven artifact hashes matched before/after, including the four store archives,
protected runtime config, manifest and COMPLETE. The full hash/image receipt is
`/Volumes/Dev_SSD/offload/codex/checkpoints/disposable-proof-20261007-01a116f7/fixture-proof.json`.
Redis absolute expiry `1791401209410` was preserved;
rollback does not extend TTLs.

Earlier attempts are negative evidence: two fixture Neo4j startups exited 3
before initialization; the explicit loopback hostname mapping fixed that fixture
condition. A later attempt captured/validated all stores but Chroma's document
update attempted an unavailable embedding download. Explicit fixture embeddings
removed that dependency; the subsequent two complete round trips passed. These
failures were not counted as successful restore proof. No candidate repair or
production configuration change was made.

**Implemented refusal coverage:** absent/unsafe/worktree/source/symlink destinations;
wrong project, missing volume and unrelated attachments; running/OOM/unclean
writers; missing final Redis save or a save before shutdown; incomplete/corrupt/
wrong-schema/missing-store/hash-invalid checkpoints; target project mismatch and
active writers; partial create; repeated partial/completed checkpoint IDs;
inferred latest; unsafe archive members; mutable helper image and invalid queue
observations. Refusal paths did not issue unrelated Docker mutations.

Syntax compilation, CLI help, scoped Ruff lint and `git diff --check` passed.
The real-candidate `plan` passed observationally and reported **BLOCKED** because
its application/storage writers are still running; that is the required refusal
posture. Existing Ruff configuration deprecation warnings were left unchanged.

**Observed preservation:** pre/post read-only receipts show all seven real
candidate container IDs, image IDs, start times, restart counts and mounts equal;
all eleven attached volume metadata records equal. The recovery checkout HEAD,
status, four file hashes, diff and index are equal; the ten unrelated assigned
checkout files, their diff and index also remain equal. No recovery process was
signalled, restarted or terminated. Evidence baseline/plan/preservation receipts
are under `/private/tmp/codexify-checkpoint-implementation-20261007-01a116f7/`;
that scratch is evidence only, never a checkpoint destination.

**Still unproven on the real candidate:** admission closure, durable accepted-work
drain, storage closure, candidate checkpoint creation/validation, rollback,
posture recreation, adoption, ordinary chat, embeddings and restart qualification.
Disposable proof establishes the operator capability; it does not qualify those
candidate behaviors. Release remains **HOLD**. No merge, push or deployment.
The next authority frontier is the separately authorized real-candidate checkpoint
slice and return to original running posture, without adoption. It was not begun.

## Candidate closure evaluation — 2026-10-08

Historical live-candidate finding. The source repair and disposable proof below
supersede the source-level blocker; the unchanged live candidate still lacks
the repair. This evaluation does not authorize candidate mutation.

**HUMAN_DECISION_REQUIRED — RUNTIME CONTROL PRIMITIVE MISSING.**
Outcome B: a **bounded active-document-worker drain with durable terminal
acknowledgement** is the strongest missing primitive. The existing worker has
cooperative signal handling; this finding is specifically about active work,
not an absent SIGTERM handler. No complete executable admission/closure/return
procedure is approved by this evaluation. Do not signal the candidate or invoke
create using this section. The running-writer override remains accepted; it does
not supply a missing active-work bound or permit forced abandonment.

Authoring HEAD: `636cdc7da4f7413bf0a248b514148a677c799ebb`.
Candidate: `codexify_candidate_28c95_20261005`. Its exact seven services remain
backend, frontend, worker-chat, worker-document-embed, db, redis and neo4j.
No worker-chat-embed runs. The backend/chat/document image remains
`sha256:910b5acd39be578be8da6fd5c773314bccc4a3bdc516226210fb53ecc746e341`;
no prepared backend or c511f154b client is adopted. Release HOLD.

### Evidence ownership and source identities

Docker labels identify the existing Compose inputs under
`/private/tmp/codexify-mainline-proof-28c95/`: `source/docker-compose.yml`,
`source/docker-compose.whooshd-smoke.yml`, `candidate.override.yml` and
`receipt-candidate-adoption/integrated.override.json`. Backend/chat/document
mount `receipt-candidate-adoption/runtime-source/guardian` at `/app/guardian`.
Source analysis uses those actual host bytes and immutable Git objects, not the
uncommitted recovery checkout. Missing governing source was read from immutable
`c511f154bf70175672a6a9e78e854827482a4b73` without checkout/reset/merge.

Actual worker, API lifespan, queue, model and vector-operation files match that
immutable revision. `routes/chat.py` and `workers/chat_embedding_worker.py` differ;
neither is silently substituted. The latter consumer is absent. The document
worker SHA-256 is
`3bbf52c10445f77cc987f08280a84e6c9b661045cb7ea26b6a26c76d877862e3`.
Its vector facade is `guardian/vector/store.py`, not the unrelated in-memory
stub `guardian/vector_store.py`. Full byte comparison/fingerprints and runtime
baseline are retained in
`/private/tmp/codexify-candidate-closure-source-20261008-01a116f7/`.
That location is evidence only, never a checkpoint destination.

Governing boundaries remain ADR-101, existing Postgres canonical authority,
Redis operational transport, admitted Chroma and feature-bounded Neo4j. ADR-087's
accepted chat deadline is not a document-task deadline. No ADR or runtime
semantics change is made. The dirty current-state conflict markers are preserved;
neither side supplies release readiness or missing operational authority.

### Candidate writer map

Line references below describe the actual mounted runtime-source bytes unless
an immutable revision or Compose source is named explicitly. Startup, imports,
non-chat routes and background operations remain writers even when ordinary
chat queues are empty.

| Process / path | Triggers and stores | Intake / in-flight ownership and stop behavior | Grace / completion evidence |
| --- | --- | --- | --- |
| Backend HTTP | Chat thread/message/attempt writes to Postgres; completion acceptance enqueues Redis and publishes events. Upload/document, account/Project/config and enabled knowledge routes also write Postgres and may initialize/index Chroma. | `routes/chat.py` calls shared completion acceptance; workers execute queued completions independently. PID 1 guard execs Python, `run_backend.py` execs Uvicorn. Stopping frontend or workers does not close this listener. HTTP stop must let accepted handlers finish while DB/Redis/Neo4j remain available. | Actual backend stop timeout 30s. No new maintenance route exists. Backend stop is a candidate operation to qualify, not an approved full-stack closure proof here. |
| Backend startup/background | `guardian_api.py:322–371,569–833`: seeds, built-in ingestion, provider/default rows, ChatGPT import embedding sweep, system warmup enqueue, optional connector scheduler; Postgres/Redis/Chroma. Graph connection/writes are conditional on existing graph settings. | Startup import uses `asyncio.to_thread` and a tracked async task; lifespan cancels tracked startup wrappers. Cancellation of that wrapper is not evidence that its synchronous child finished. Optional connector worker is cancelled on shutdown. Request listener closure alone is not whole-process writer closure. | Require clean process exit plus applicable durable import/job dispositions and child completion. Candidate `ENABLE_CONNECTOR_WORKER=false`; supported profile quarantines connector routes, so manual detached connector sync is not asserted active here. |
| Domain events / SSE | Producers append durable outbox through `event_bus`/Postgres; task events use Redis. Graph/event hooks retain their own existing policy. | Backend SSE `guardian_api.py:1546–1642` polls/streams; it retains outbox rows despite an older deletion comment. Consumers' receipt/transport state is not domain completion. Outbox producers remain part of their owning processes. | Outbox/event absence is not drain proof; preserve rows. No deletion or publication-as-completion shortcut. |
| worker-chat | Redis BRPOP, provider/retrieval work, assistant/terminal writes to Postgres, task events/lock cleanup and derived embedding enqueue in Redis; Chroma initialization/retrieval. Graph-write candidates/inspection are conditional; no new direct Neo4j authority is inferred. | `chat_worker.py:3283–3401`: SIGTERM/SIGINT sets intake flag, executor context waits for already-submitted tasks, heartbeat remains through drain. A task popped while stopping still enters existing handling. Uses original accepted finite deadline, never user-cancellation semantics. | Actual grace 785s. Existing `accepted work drained` log + clean exit must agree with each accepted attempt's completed-message/terminal evidence and lock disposition. The log alone is insufficient. |
| worker-document-embed | Redis BRPOP removes payload; Postgres UploadedDocument status/timestamps; chunking/model embedding/Chroma writes, then terminal status persistence. No direct Neo4j call in this worker path. | `document_embed_worker.py:127–213,216–287`: signal sets flag, synchronous current task runs before loop can observe it. The handler does not interrupt or bound current encoding/storage/status I/O. `finally` attempts durable status; outer loop catches failures, so exit/log alone does not prove the status committed. | Actual grace 10s. Durable ready/failed + completed timestamp for every owned task and clean process exit are necessary. No finite active-drain envelope or acknowledged abort exists. This is the deciding seam. |
| worker-chat-embed | Absent now; its ordinary/import queues may retain operational work. Source handles Postgres/Chroma status/indexing and consumes Redis. | Actual source `chat_embedding_worker.py:216–270` loops without graceful signal/drain handling. Do not activate it. A future topology with this worker requires separate requalification, not this candidate procedure. | Absence is not proof its queues are empty; checkpoint retained queues, never flush or replay them. No generic future-worker closure claim. |
| Frontend | Vite/pnpm/cache filesystem activity and HTTP client initiation; no direct protected-store writer. | Frontend shutdown changes user availability but direct backend clients remain. It cannot establish admission closure. | Require stopped state under helper's all-project-services rule, not a durable-work receipt. |
| PostgreSQL / Redis / Neo4j | Engine-internal WAL/checkpoints, RDB/AOF/expiry state, graph transaction/log/page persistence. Chroma has no separate engine service; its application processes own SQLite/index writes. | Keep engines available through every application drain; never stop them while a writer might still use them. | PostgreSQL configured image stop signal SIGINT; Redis requires final persisted RDB proof; Neo4j clean exit. Actual Redis command disables periodic save and AOF, so ordinary signal exit must not be assumed to persist keys. |

Queue implementations `redis_queue.py:629–642` and `document_embed_queue.py:41–44`
use destructive BRPOP/RPOP, without a separate in-flight acknowledgement list.
Queue length can fall to zero before a worker has marked the row processing.
For chat, `ChatCompletionAttempt` completed-message link and terminal kind are
canonical evidence, not an invented status enum. For documents, UploadedDocument
embedding status/start/completion timestamps are evidence, not a queue receipt.
No manual row, lock, deadline, event or queue edit is permitted to manufacture
completion.

### Why the active document drain is not established

The signal handler at `document_embed_worker.py:223–230` sets a flag. That flag
is checked only at the outer loop boundary, after
`process_document_embed_task` returns. Native work follows
`_write_document_chunks` → `guardian/vector/store.py:148–157` →
`backend/rag/embedder.py:447–470,490+`: synchronous model encode and index writes.
The document dispatch installs no accepted-work deadline. The vector facade's
chat budget check does not supply one: `chat_postgres_deadline.py:131–139`
returns None when no chat budget exists. A timeout measured by an observer does
not interrupt these native writes or make them terminal.

Thus an active embedding/storage call can remain owned beyond Compose's 10s.
Ordinary Compose stop may escalate to SIGKILL; SIGKILL cannot run the terminal
status `finally`. Increasing a guessed grace cannot establish a missing bound.
An unlimited wait avoids forced loss but cannot provide the required finite
abort/return transition if the call never returns; its intake flag cannot be
undone by an existing resume operation. This evaluation does not redefine that
incomplete state as quiescence. Missing primitive: **bounded active-document
worker drain with durable terminal acknowledgement**. No design, deadline,
cancellation token or implementation is introduced here.

The historical private-preview shutdown classification demonstrated forced
exit-137 behavior and explicitly limits its scope; the idle chat-worker restart
proof covers queue handoff only. Neither qualifies active document drain for
this candidate. The worker's existing cooperative handler and possible eventual
successful completion remain real capabilities, but do not establish the full
requested safe drain/abort procedure under partial failure.

### Gate and abort dispositions — no executable mutating procedure

| Requested gate / phase | Outcome B disposition |
| --- | --- |
| Exact admission-close operation | Not approved as a complete candidate procedure. Native graceful backend listener/process shutdown is the candidate primitive to evaluate after the missing drain boundary is resolved; no new flag, proxy, route or firewall rule is selected. |
| NEW ADMISSION CLOSED | Must eventually require the owned backend listener unavailable, accepted handlers released and backend process/children stopped, with workers/storage still available. A failed health request or elapsed time alone cannot prove those conditions. Gate not asserted here. |
| Chat accepted-work drain | Preserve original attempts/deadlines; leave DB/Redis available, account for queued and executor-held attempts, correlate durable terminal/message/lock disposition with the existing drained log and clean exit. Do not signal intake shutdown while treating remaining queued work as completed. |
| Document accepted-work drain | Gate unavailable for an active native call without the missing primitive. Empty queue, idle-looking DB snapshot or worker absence cannot substitute for ownership and terminal commit evidence. |
| APPLICATION WRITERS QUIESCENT | Must cover backend/background children, chat/document writers, absent chat-embed classification, every protected-volume attachment and durable receipts. Not established by this evaluation. |
| Storage ordering | Only after the previous gate, engines may close with their storage-specific clean persistence evidence; Chroma remains the same unmounted-by-writers admitted filesystem. No engine stop command is approved before that gate. Engine-to-engine order cannot compensate for a live application writer. |
| CHECKPOINT CREATE ELIGIBLE | Withheld. Helper must prove all project services exited 0/non-OOM, exclusive volume custody, final Redis RDB and unchanged identity. No create invocation occurs in this task. |
| Before any admission closure | Abort with the original runtime unchanged; this is the only phase exercised here (read-only). |
| After admission closure / partial application shutdown | Keep storage available. Do not destroy/restart a still-owning document process to recover intake. No bounded return-to-original-worker-posture can be certified while its native call is hung; this is why Outcome A is withheld. |
| After engines stopped before capture | Only an independently established writer-quiescent state could permit storage readiness first, then original backend, workers and frontend using preserved inputs. This unreachable branch is not supplied as a pretend executable recovery path. No data restore/repair without a checkpoint. |
| Return to original service | Must reuse exact original images/config/source/volumes/network/worker set and gated storage/backend health; backend startup may seed or enqueue warmup. Generic Makefile restart/Compose up cannot prove equivalence. Exact operational sequence remains unapproved, rather than hiding placeholders in executable commands. |

The checkpoint helper remains unchanged and its proven four-store capture is not
rejected as a storage-format capability. The earlier missing-documentation
frontier is now classified as an active document-drain runtime control frontier.
The adoption runbook references this evaluation; it does not mark closure as
resolved or authorize live execution. No checkpoint, signals, stop/start,
recreation, adoption or native chat qualification occurred. No live checkpoint
exists. Release remains HOLD.

### Evaluation validation and preservation receipt

Source-only validation passed: both documents' shell blocks were parsed with
`bash -n` without execution; the four label-derived Compose files rendered with
`config --no-interpolate --no-env-resolution -q` and the existing empty-env
syntax input. This does not prove activation environment, credentials or live
shutdown. Scoped `git diff --check` passed. No runtime tests apply to this
non-mutating Outcome B; no live signal/drain/checkpoint proof is claimed.

Final read-only comparison found the seven candidate IDs/images/start timestamps/
restart counts/mounts/networks unchanged and all eleven mounted-volume metadata
records equal. Recovery local HEAD, four file hashes and diff/index are preserved;
the assigned checkout's ten unrelated dirty files and diff/index are preserved.
No recovery process was signalled, no unrelated project was operated, no source
or proof file was edited. Only this operator contract and the adoption runbook
are staged for `docs: record candidate closure authority frontier`. No push.
The next task requires explicit authority for the missing runtime primitive;
this task neither designs it nor proceeds to live checkpointing.


## Document-worker closure repair — source and disposable proof, 2026-10-08

**Implemented and proven in tests/disposable runtime; unproven on the live
candidate.** Source baseline: `5526ebf5ce782685a89fb9abc38077ed76938d21`.
The governing lifecycle remains `processing → ready|failed`, with PostgreSQL
canonical and Chroma derived. No schema, queue acknowledgement, retry policy,
job entity, or ADR changes. This repair is aligned with the existing lifecycle.

### Execution and terminal contract

`guardian/workers/document_embed_worker.py` owns one private spawned writer.
The blocking seam is `VectorStore.add_texts → LocalSemanticEmbedder.embed_and_index
→ _embed_np → SentenceTransformer.encode`, followed by local Chroma add/upsert
or synchronous in-memory FAISS insertion. Model initialization, chunking, encoding
and vector mutation execute in that child; terminal ORM writes execute only in
the parent. Native encode previously had no cancellation/deadline, and the
candidate's 10s grace could kill its parent before terminal persistence.

Canonical configuration is
`guardian.core.config.Settings.DOCUMENT_EMBED_EXECUTION_TIMEOUT_SECONDS`:
default **120s**, finite **0 < value ≤ 600s**, validated on startup and logged
without credentials. The monotonic execution deadline includes child/model
startup and IPC waits; signals do not reset it. Socket waits, including sending
the document, are physically bounded. There is no timeout thread left running.

On SIGTERM/SIGINT, intake stops. An already-owned job completes within its
remaining bound. Expiry kills and reaps its entire local writer before committing
`failed`, with `embedding_error=document_embed_execution_bound_exceeded`.
Ordinary failures remain `failed`; success remains `ready`. A dequeue already in flight when
shutdown arrives remains owned and drains as the current job; no subsequent
dequeue starts. Repeated
signals set the same shutdown flag and do not duplicate finalization.

Chroma's child is reaped after every job, including success, before the parent
terminal commit. FAISS preserves its existing process-local in-memory index
between successful jobs; its completed synchronous insertion has returned and
the child waits for the next document. On shutdown, failure or timeout that child
is also reaped before terminal persistence. No active execution survives clean
worker exit. Interruption prevents later writes; it does not roll back vectors already
committed before expiry. The hung fixture deliberately blocks before native
add, so its zero count proves no late writes rather than general rollback.
No deletion/cleanup policy is introduced. No automatic retry/requeue is introduced; an already-ready queue
item is skipped. Reaping a failed FAISS writer discards its process-local index,
as worker restart already does; no new durable FAISS authority is introduced.

Worker-local ORM sessions reuse the existing physical PostgreSQL deadline driver.
Document read, processing commit and terminal commit each have at most **10s**;
child reap has **5s**, idle Redis transport **2s**. The explicit **40s** margin
covers these 37s of preparation/finalization/transport, with 3s additional margin.
Compose's `worker-document-embed.stop_grace_period` is **10m45s (645s)**:
`645 > 600 + 40`. The focused test checks the setting's validated maximum
against the actual service stanza. The old candidate's configuration is unchanged.

`document_embed_writer_reaped` precedes `document_embed_terminal_ack`, which is
emitted only after the terminal transaction commits and its session closes.
`document_embed_worker_drained` follows cleanup. These logs support correlation;
PostgreSQL readback is acknowledgement authority. If reaping or terminal commit
cannot be confirmed, the worker raises, reports no clean drain/terminal ack,
and does not authorize checkpointing. In particular, database unavailability
cannot be converted into a promised durable terminal state; do not infer
quiescence from a nonzero exit or treat a remaining `processing` row as terminal.

### Focused and disposable evidence

`tests/workers/test_document_worker_shutdown.py` exercises real process signals
and committed model-backed SQLite readback for idle, active success, ordinary
failure, hung execution, repeated signals, ready replay, configuration bounds,
and rejection of an unconfirmed terminal commit. The hung test releases its
abandoned operation only after exit and observes beyond its polling interval:
no late vector file, ready state, transaction/update or overwritten failed state.
A native FAISS test verifies that two successful jobs retain the same child and
both indexed texts. Existing document-worker lifecycle/store tests also pass.

Disposable project **`codexify_doc_shutdown_01929499`** used real PostgreSQL 15,
Redis 7 and persistent local Chroma on a project-owned Docker volume. The pinned dependency image was
`sha256:bcb55917283fc2d6f23b7891b11c06fcebb5ec811e82eb5d62491e09b404ccb6`;
read-only guardian/backend/config mounts supplied the repaired source. This
proves source execution, not an image build containing the repair. The worker
read the real Redis queue and used the repaired PostgreSQL driver/ORM path.
Its synthetic writer initialized the canonical Chroma store with an explicitly
mock embedding backend, then blocked before native `add_texts`; this exercises
termination of the compute/write context without loading a production model.
The first host-bind fixture hit Chroma `SQLITE_READONLY_DBMOVED` before the intended
job reached its blocking gate; it was retained as a failed fixture attempt and
is not claimed as shutdown proof. The successful fixture used a Docker volume.

| Observation | Hung job proof | Normal success proof |
| --- | --- | --- |
| Execution bound / Compose grace | 12s / 645s | 12s / 645s |
| SIGTERM UTC | 2026-10-08T13:43:07.303307Z | 2026-10-08T13:47:14.029013Z |
| Writer reaped, Docker log UTC | 13:43:16.256842881Z | 13:47:14.154526172Z |
| Post-commit acknowledgement log UTC | 13:43:16.345064881Z | 13:47:14.308536130Z |
| Hung container finished UTC | 2026-10-08T13:43:17.025545381Z | Clean exit observed |
| Signal-to-exit observation | **9.7862s**, exit 0 | **1.2393s**, exit 0 |
| Canonical row | `failed`, bound-exceeded error | `ready` |
| Native Chroma readback | 0 records before/after releasing abandoned gate | 1 matching document/chunk |
| Queue after shutdown | Next document remains queued | Next document remains queued |

Hung-job committed readback occurred at **13:43:17.146422Z**. The document's
`embedding_completed_at` is a lifecycle timestamp, not an exact commit timestamp;
the post-commit log and independent PostgreSQL query establish ordering/readback.
Repeated native Chroma readers after gate release found the same zero records.
The success fixture then explicitly replayed the ready item after restart:
PostgreSQL `xmin`/terminal timestamp and Chroma records remained unchanged,
and no embedding child started. This proves scoped document restart behavior,
not general candidate restart/recreation or native chat qualification.

Private evidence receipts/scripts/logs are retained under
`/private/tmp/codexify-document-shutdown-01929499/` (`native-hung-receipt.json`,
`native-success-receipt.json`, corresponding worker logs). These are disposable
proof evidence, not candidate checkpoints or a maintained runtime config surface.
No live candidate signal, build, checkpoint, adoption or qualification occurred.

### Remaining live frontier

The unchanged `codexify_candidate_28c95_20261005` still runs older image/source
`sha256:910b5acd39be578be8da6fd5c773314bccc4a3bdc516226210fb53ecc746e341`
with its existing 10s document-worker grace. Source/disposable proof cannot
qualify that live worker. The next separately authorized task must prepare a
runtime containing this exact repair and its grace configuration, establish
custody/source fidelity, and rerun the protected checkpoint prerequisite chain.
Do not signal or checkpoint the old candidate using this source proof.
Backend/client adoption, full supported-path proof and release remain deferred.
**Release HOLD.**


### Repair validation and preservation

- `/Volumes/Dev_SSD/Codexify-main/.venv/bin/python -m pytest -v tests/workers/test_document_worker_shutdown.py tests/workers/test_document_embed_worker.py guardian/tests/test_document_embed_worker.py`: **22 passed** (17 focused, 5 existing). Existing SQLAlchemy relationship warnings remain outside this repair.
- `python3 -m py_compile guardian/workers/document_embed_worker.py guardian/core/config.py`: passed.
- `/Volumes/Dev_SSD/Codexify-main/.venv/bin/python -m ruff check guardian/workers/document_embed_worker.py guardian/core/config.py tests/workers/test_document_worker_shutdown.py`: passed; existing Ruff configuration deprecation notice remains.
- Read-only `docker compose --env-file /private/tmp/codexify-document-shutdown-01929499/empty.env -f docker-compose.yml config --no-interpolate --no-env-resolution --format json`: passed; rendered document-worker grace `10m45s`.
- Scoped six-file `git diff --check`: passed. No schema migration, retry or queue contract changes.

The seven live candidate container IDs, image IDs, mounts, start times and restart
counts matched the pre-proof baseline. All four recovery-owned file hashes and
all ten unrelated dirty-file hashes were unchanged. No signal or termination
was sent to recovery-owned activity. Disposable cleanup is restricted to the
verified three-container proof project, its network and its private Chroma volume;
receipts/logs remain in evidence scratch. No merge, push, deployment, live
checkpoint, prepared input adoption or release claim expansion occurred.
