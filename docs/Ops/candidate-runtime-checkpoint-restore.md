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
