# Native candidate adoption runbook — human decision required

## Status and boundary

**HUMAN_DECISION_REQUIRED — an accepted candidate-wide protected checkpoint and
restore procedure, with an explicitly approved independent destination, is
missing. STOP before admission closure, drain, backup, adoption or restart.**

This document is the preparation task's stopped result. It provides executable
read-only inventory and independently pinned inputs; it is **not** an
execution-ready mutating runbook. Mutating phases are withheld at the task's
explicit authority gate rather than supplied as guessed commands. No new
backup location, retention rule, control plane or runtime policy is selected.
No ADR impact. Release remains **HOLD**.

Preparation task requirements 4/5 and its final stop rule require
`HUMAN_DECISION_REQUIRED` when safe supported quiescence/preservation cannot be
derived or no accepted backup destination/mechanism exists. The single missing
prerequisite is the candidate protected-checkpoint/restore procedure. It must
cover the stores below and specify the approved destination, writer closure,
verification and return-to-original-state steps. Choosing it is a human
operational decision, not documentation authority.

ADR-101 at the immutable prepared source states that backup remains separately
authorized (lines 81–85). Its operations document lines 59–64 repeats that
boundary. That contract permits admitted-volume reattachment; it does not
provide a candidate backup/restore protocol.

## Source truth and independently pinned inputs

Assigned physical checkout:
`/Volumes/Dev_SSD/offload/codex/worktrees/7d94/Codexify-main`.
Authoring HEAD: `0ba8674cec156ff587062e99b21b0b95de7a5e65`.
Branch: `codex/chat-postgres-terminal-deadline-20261003`.
[Blocked qualification](proofs/runtime/2026-10-07-native-candidate-adoption-qualification.md)
is the one-file commit at that HEAD and was read.

Prepared source revision:
`c511f154bf70175672a6a9e78e854827482a4b73` (**current client**).
Prepared backend image:
`sha256:bcb55917283fc2d6f23b7891b11c06fcebb5ec811e82eb5d62491e09b404ccb6`.
Tag: `codexify-backend-runtime:goal-current-685cea098`.
Actual backend image revision label:
`685cea098a4a6c14e1bf3f679c94e0633dfe590a`.
**685cea098 is only the backend image provenance; it is not the desired client.**

Client production output and manifests:
`/private/tmp/codexify-chat-client-build-c511f154b-20261007/`.
The retained `artifacts.json` has SHA-256
`766a3b93e814ff09d6c37f6259575c0fdc0988ad5ec4a9c0b3e41dded48a322f`.
All 16 output hashes/sizes were freshly rechecked, totaling 11,088,871 bytes.
The earlier build's 716-input/backend-tree-equivalence attestation is prior
build evidence, not source/image/runtime equivalence independently requalified
by this task. Presence of the image and bundle does not prove adoption safe.

Required current-state, ADR index, architecture README, Development Operator
Goal and chat/runtime contracts were read in the supplied checkout. The required
current-client build, controlled-browser admission and gap-audit proofs reside
in the separate read-only checkout:
`/Volumes/Dev_SSD/offload/codex/worktrees/chat-postgres-deadline/Codexify-main/docs/architecture/proofs/runtime/`.
Its HEAD is `3c5d5538f8758f96dbc7d07f056af11a41da7ff6`. It was not switched to,
edited, staged, reset or committed. The prior scratch handoff remains a
read-only historical input; it is not a second maintained runbook.

### Immutable command/service derivation sources

Line references in this table are at **c511f154b**, not the older authoring
checkout. Exact blobs can be inspected without checkout using
`git show c511f154b:PATH` with the literal paths listed below.

| Source | Verified operational primitive and limit |
| --- | --- |
| `docker-compose.yml:483–551` | Canonical `worker-chat`; signal grace period 13m5s. |
| `guardian/workers/chat_worker.py:3283–3401` | SIGTERM/SIGINT stops intake; executor drains accepted work under existing deadlines and logs `accepted work drained`. Does not close backend admission. |
| `docker-compose.yml:742–803` and `guardian/workers/document_embed_worker.py:216–287` | `worker-document-embed`; shutdown flag stops intake after current work; 10s Compose grace explicitly does not bound active embedding. |
| `docker-compose.yml:805–863` and `guardian/workers/chat_embedding_worker.py:228–270` | Committed canonical `worker-chat-embed`; consumes ordinary/import embed queues. No new worker is needed. |
| `guardian/queue/redis_queue.py:41–50`, `guardian/queue/document_embed_queue.py:12–14`, chat worker `QUEUE_NAME` | Actual default queue names; source and live environment must agree before treating LLEN as evidence. |
| `guardian/db/models.py`, `ChatCompletionAttempt` | Durable `completed_message_id`, `terminal_event_type`, accepted deadline snapshot and distinct request/task/turn identity; no invented status field. |
| `Makefile:585–589,640–655` | Compose/environment conventions and `cfg`'s `config --no-interpolate`; bare `restart` targets the full selected stack and is not a candidate-scoped drain/adoption command. |
| `scripts/ops/default_local_chroma.py:49–60,62–75,108–130` | Admission attachment checks and initialized reattachment; helper preflight creates a transient probe container. It is not run in this read-only preparation task and is not a backup helper. |
| `docs/architecture/adr/101-default-local-chroma-persistence-contract.md:68–85` | Preserve historical state; backup/restoration remain separately authorized. |
| `docs/Ops/default-local-chroma-storage.md:34–78` | Guarded activation/reattachment and separate backup authorization; no current-store checkpoint/restore recipe. |
| `scripts/ops/private_preview_backup_restore_proof.sh:8–14,303–329,394–479` | Hard-coded `codexify_private_preview`, operator-selected `CODEXIFY_PRIVATE_PREVIEW_BACKUP_DIR`, PostgreSQL/media checkpoint and isolated restore proof. Cannot be redirected to this candidate by setting the project variable. |
| `scripts/ops/private_preview_database_migration_proof.sh:9–17,240–290` | Hard-coded preview project, migration revisions and separate destination; migration/restore behavior outside this task and candidate. |

Docker `ps`, `inspect`, `image inspect`, `volume inspect`, and Compose `config`
are observational CLI primitives. The installed `docker compose config --help`
confirms `--no-env-resolution`, `--no-interpolate` and `-q` syntax. SQL inspection
uses the versioned preview helper's `container_query`/Alembic-reading primitive
with a read-only transaction; queue commands use only Redis `LLEN`.

## Observed candidate inventory

Fresh observation: 2026-10-07T16:56:46.459719+00:00.
Compose project: `codexify_candidate_28c95_20261005`.
Network: `codexify_candidate_28c95_20261005_default`.
Active service set: `backend`, `frontend`, `worker-chat`,
`worker-document-embed`, `db`, `redis`, `neo4j`.
No candidate `worker-chat-embed` exists.

Backend/chat/document consumers run
`codexify-backend-runtime:goal-integrated-a165a3447`, image ID
`sha256:910b5acd39be578be8da6fd5c773314bccc4a3bdc516226210fb53ecc746e341`.
Their actual source bind roots remain the previous
`/private/tmp/codexify-mainline-proof-28c95/receipt-candidate-adoption/runtime-source/`.
Frontend uses Node image ID
`sha256:fb4cd12c85ee03686f6af5362a0b0d56d50c58a04632e6c0fb8363f609372293`
and the previous frontend bind, not proof of the prepared c511f154b artifacts
being served. Full filtered container identity/mount receipts are in authoring
scratch, not a new config source.

Live Compose labels identify this exact ordered file set:

1. `/private/tmp/codexify-mainline-proof-28c95/source/docker-compose.yml`
2. `/private/tmp/codexify-mainline-proof-28c95/source/docker-compose.whooshd-smoke.yml`
3. `/private/tmp/codexify-mainline-proof-28c95/candidate.override.yml`
4. `/private/tmp/codexify-mainline-proof-28c95/receipt-candidate-adoption/integrated.override.json`

These scratch files describe the pre-adoption candidate. They must not be
confused with the committed c511f154b topology or silently rewritten. Resolved
runtime environment/configuration fidelity has not been proved.

| Candidate service | Actual volume identity | Mount |
| --- | --- | --- |
| `worker-chat` | `codexify_default_local_chroma` | `/app/.chroma` |
| `worker-chat` | `codexify_candidate_28c95_20261005_codexify_cli_home` | `/home/codexify` |
| `worker-chat` | `codexify_candidate_28c95_20261005_hf_cache` | `/root/.cache/huggingface` |
| `worker-document-embed` | `codexify_default_local_chroma` | `/app/.chroma` |
| `worker-document-embed` | `codexify_candidate_28c95_20261005_hf_cache` | `/root/.cache/huggingface` |
| `frontend` | `0382900c2a77f08fd477da25b89fa9e2d7c9efb4cf19e39d18e24a716b20da65` | `/app/node_modules` |
| `frontend` | `codexify_candidate_28c95_20261005_frontend_pnpm_store` | `/pnpm/store` |
| `frontend` | `f91157e84c1d3e5d54402fd70f845fe20a675c57b4e99ded61ae1c3d58cea2a5` | `/app/src/node_modules` |
| `frontend` | `codexify_candidate_28c95_20261005_corepack_cache` | `/root/.cache/node/corepack` |
| `backend` | `codexify_default_local_chroma` | `/app/.chroma` |
| `backend` | `codexify_candidate_28c95_20261005_codexify_cli_home` | `/home/codexify` |
| `backend` | `codexify_candidate_28c95_20261005_hf_cache` | `/root/.cache/huggingface` |
| `db` | `codexify_candidate_28c95_20261005_pg_data` | `/var/lib/postgresql/data` |
| `redis` | `5fc24591f254f73d3c44a0a1e0c7b00c577c6bd3113466e4bb1247747c470fb7` | `/data` |
| `neo4j` | `codexify_candidate_28c95_20261005_neo4j_data` | `/data` |
| `neo4j` | `25830adbcea5a2a5636e75b9bd4db4d8f74f0979ae86c36ca5d17e093c5f4b1f` | `/logs` |

Protected Chroma labels: contract ADR-101, project
`codexify_candidate_28c95_20261005`, admission ID
`ef0c3312bdb640e4a35e2783ecfcd687`. Only candidate backend/chat/document
containers currently mount it. That is a Docker attachment observation, not
proof that all writers are quiescent or all non-container writers are absent.

Postgres read-only observations: Alembic `f8c2a91d6b40`; 14 threads,
27 messages, 15 attempts; no attempt with both `completed_message_id` and
`terminal_event_type` NULL; terminal event counts 12 `task.completed`,
2 `task.cancelled`, 1 `task.failed`. All 27 message embedding statuses are unset.
Counts/flags alone do not establish successful content, deadline custody,
consistent backups or durable completion validity for a newly submitted turn.

The four inspected queue lengths are zero: chat, document-embed, chat-embed,
chat-import-embed. Live backend/chat/document container environments contain no
queue-name overrides. Their actual mounted queue code still needs fidelity
qualification before any future drain relies on those defaults.

## Executable read-only preflight — no mutation permitted

Run from the supplied physical repo root in Bash. Every failed command or
assertion means **STOP**. These commands establish observations only. No later
mutating phase is authorized or executable by this document.

### Repository, prepared image and client

Expected: blocked proof and prepared source commits exist; backend ID and label
match separately; manifest SHA and all 16 output hashes/sizes match. Any input
missing from scratch is STOP, not permission to rebuild/substitute it.

```bash
set -euo pipefail
cd /Volumes/Dev_SSD/offload/codex/worktrees/7d94/Codexify-main
git status --short --branch --untracked-files=all
git rev-parse HEAD
git show --stat --oneline 0ba8674cec156ff587062e99b21b0b95de7a5e65
git cat-file -e 'c511f154b^{commit}'
git merge-base --is-ancestor 0ba8674cec156ff587062e99b21b0b95de7a5e65 HEAD
python3 - <<'PY'
import hashlib, json, pathlib, subprocess
expected = 'sha256:bcb55917283fc2d6f23b7891b11c06fcebb5ec811e82eb5d62491e09b404ccb6'
image = json.loads(subprocess.check_output(['docker','image','inspect',expected]))[0]
assert image['Id'] == expected
assert image['Config']['Labels']['org.opencontainers.image.revision'] == '685cea098a4a6c14e1bf3f679c94e0633dfe590a'
root = pathlib.Path('/private/tmp/codexify-chat-client-build-c511f154b-20261007')
raw = (root/'artifacts.json').read_bytes()
assert hashlib.sha256(raw).hexdigest() == '766a3b93e814ff09d6c37f6259575c0fdc0988ad5ec4a9c0b3e41dded48a322f'
manifest = json.loads(raw)
assert len(manifest) == 16
assert json.loads((root/'verification.json').read_text())['source_revision'] == 'c511f154bf70175672a6a9e78e854827482a4b73'
for name, entry in manifest.items():
    path = root/'output'/name
    assert path.stat().st_size == entry['bytes'], name
    assert hashlib.sha256(path.read_bytes()).hexdigest() == entry['sha256'], name
print('Prepared backend label verified; current c511f154b client: 16 outputs match')
PY
```

### Candidate/project/container identity, attachments and recovery exclusion

Expected: the exact seven baseline candidate containers/images below, one
candidate network, no extra Chroma installation, no queue environment override,
and unchanged four recovery-file hashes. The Python check intentionally fails
if container custody drifts; do not update expectations merely to pass it.
A live test-process match causes STOP. A negative pattern scan is not proof of
exclusive ownership: a future operator also needs the recovery owner's
current explicit custody receipt identifying any surviving process. No receipt
was supplied here, so conflicting activity is **unproven**, not cleared.

```bash
docker ps --format '{{.Names}}\t{{.Image}}\t{{.Status}}'
docker volume inspect codexify_default_local_chroma
python3 - <<'PY'
import hashlib, json, pathlib, subprocess
project = 'codexify_candidate_28c95_20261005'
expected = {'worker-chat': {'id': '42f5f9a660d5a53b1b42edaed3905364a3af72e3d503d81f76d2290eae7430c5', 'image_id': 'sha256:910b5acd39be578be8da6fd5c773314bccc4a3bdc516226210fb53ecc746e341'}, 'worker-document-embed': {'id': '9e468f5c35c7ad90874f06cad586f6b9007109393b5bbf33673391c8fab0d061', 'image_id': 'sha256:910b5acd39be578be8da6fd5c773314bccc4a3bdc516226210fb53ecc746e341'}, 'frontend': {'id': '8b25fa82b0315707981b3609fabda91b4d664b1fe2ba41a777f798c6202f39a6', 'image_id': 'sha256:fb4cd12c85ee03686f6af5362a0b0d56d50c58a04632e6c0fb8363f609372293'}, 'backend': {'id': '60d99ff5416b4c03326ab5594ec4e15cf962ca16e3943f307e92cf14d93070ac', 'image_id': 'sha256:910b5acd39be578be8da6fd5c773314bccc4a3bdc516226210fb53ecc746e341'}, 'db': {'id': '8d7e69dee6949a3a165422a655e7e4d061c9c5182fa5e89bca626323f1a8ce4f', 'image_id': 'sha256:724292da1f2e50bdccfc3302ce75bbba7f4a6076701b588cc795fcac65683550'}, 'redis': {'id': '93c3a036abad77999bcb012e614c2bca04e6f9a859f3937ea29dc9a34a87a6c8', 'image_id': 'sha256:858f009f9709ce576febc734aa78b8f6d624b82571f9ddb6bda4377c833b3499'}, 'neo4j': {'id': '897d8610221e90eabbe40bd4c82cc2cf99c5ee8baa3d69f7b05391d388780af5', 'image_id': 'sha256:d9cfe82983d27f5a75b3aaae8f316d04f9a698a3b7f6103a508f7caf8362f255'}}
ids = subprocess.check_output(['docker','ps','-aq']).decode().split()
assert ids
containers = json.loads(subprocess.check_output(['docker','inspect',*ids]))
candidate = {c['Config']['Labels']['com.docker.compose.service']: c for c in containers
             if (c['Config'].get('Labels') or {}).get('com.docker.compose.project') == project}
assert set(candidate) == set(expected)
for service, pin in expected.items():
    c = candidate[service]
    assert c['Id'] == pin['id'] and c['Image'] == pin['image_id'], service
    assert c['State']['Running'], service
    assert set(c['NetworkSettings']['Networks']) == {project+'_default'}, service
    queues = [v.split('=',1)[0] for v in c['Config'].get('Env',[]) if v.split('=',1)[0].endswith('QUEUE_NAME')]
    assert not queues, (service, 'unexpected queue override')
    mounts = [{k: m.get(k) for k in ('Type','Name','Source','Destination','RW')} for m in c['Mounts']]
    print(json.dumps({'service':service,'image_id':c['Image'],'mounts':mounts}))
for c in containers:
    if any(m.get('Name') == 'codexify_default_local_chroma' for m in c['Mounts']):
        assert (c['Config'].get('Labels') or {}).get('com.docker.compose.project') == project
recovery = pathlib.Path('/Volumes/Dev_SSD/offload/codex/worktrees/chat-postgres-deadline/Codexify-main')
assert subprocess.check_output(['git','-C',str(recovery),'rev-parse','HEAD']).decode().strip() == '3c5d5538f8758f96dbc7d07f056af11a41da7ff6'
protected = {'guardian/tests/migration/test_chatgpt_ingest.py': 'd904f467edb65211c40cb19e5d350af59938c10db8fbdd465b72383c3bf0eb1f', 'guardian/workers/chat_embedding_worker.py': 'c159df0aa8a7eef57d6f74104930e65c549f51feb454752b8f11bd77a319004b', 'tests/workers/test_chat_embedding_canonical_handoff.py': 'f7782be3da76b813e0713132c97af3ce83761985ea8ee2ccdac23e55b1ef4b13', 'tests/workers/test_chat_embedding_worker_import_replay.py': 'd1579a86d93dc97209609235fd4b1ef31c358bb2f7d1b51cc3d1233307e8c627'}
for name, expected_hash in protected.items():
    assert hashlib.sha256((recovery/name).read_bytes()).hexdigest() == expected_hash, name
rows = subprocess.check_output(['ps','-axo','pid=,ppid=,comm=,args=']).decode().splitlines()
hits = []
for line in rows:
    fields = line.strip().split(maxsplit=3)
    if len(fields) != 4:
        continue
    executable = pathlib.Path(fields[2]).name.lower()
    args = fields[3]
    is_test_runtime = executable.startswith(('python','pytest')) or executable == 'node'
    if is_test_runtime and ('pytest' in args or 'vitest' in args) and any(
        term in args for term in ('test_chatgpt_ingest','chat_embedding','test_document_worker_shutdown')
    ):
        hits.append(fields[0])
print('matching recovery test process count:', len(hits))
assert not hits, 'STOP: recovery activity needs owner classification; send no signals'
print('STOP: obtain current custody receipt; negative process scan is not clearance')
PY
```

### PostgreSQL terminality and Redis queue observations

Expected at authoring: schema `f8c2a91d6b40`, counts 14/27/15, zero unresolved
attempts by the explicit two-NULL diagnostic, and zero queue depths. Compare
fresh output with that baseline; drift is STOP for classification. No rows,
keys, locks, attempt states, deadlines or TTLs are changed by these commands.
The query does not invent an attempt status or mark ambiguous legacy custody
terminal. Queue emptiness does not prove an absent worker-held task.

```bash
docker exec -i codexify_candidate_28c95_20261005-db-1 sh -lc \
  'exec psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -AtX' <<'SQL'
BEGIN TRANSACTION READ ONLY;
SET LOCAL statement_timeout='5s';
SELECT version_num FROM alembic_version ORDER BY version_num;
SELECT 'threads',count(*) FROM chat_threads
UNION ALL SELECT 'messages',count(*) FROM chat_messages
UNION ALL SELECT 'attempts',count(*) FROM chat_completion_attempts;
SELECT 'unresolved_attempts',count(*) FROM chat_completion_attempts
WHERE completed_message_id IS NULL AND terminal_event_type IS NULL;
SELECT COALESCE(terminal_event_type,'NULL'),count(*)
FROM chat_completion_attempts GROUP BY terminal_event_type ORDER BY 1;
COMMIT;
SQL
for queue in codexify:queue:chat codexify:queue:document-embed \
             codexify:queue:chat-embed codexify:queue:chat-import-embed; do
  printf '%s: ' "$queue"
  docker exec codexify_candidate_28c95_20261005-redis-1 redis-cli --raw LLEN "$queue"
done
```

### Current candidate Compose structural validation

Expected: exit 0 for this **syntax/structure-only** check. It intentionally
omits interpolation and service env resolution, so it is not credential,
environment, profile, provider or activation fidelity proof. The existing
`empty.env` is a syntax-check input, not an adopted runtime environment.
The four filenames are from actual container labels. Do not use this command
prefix for activation: no verified current runtime env input has been derived.

```bash
docker compose \
  --project-directory /private/tmp/codexify-mainline-proof-28c95/source \
  --env-file /private/tmp/codexify-mainline-proof-28c95/empty.env \
  -p codexify_candidate_28c95_20261005 \
  -f /private/tmp/codexify-mainline-proof-28c95/source/docker-compose.yml \
  -f /private/tmp/codexify-mainline-proof-28c95/source/docker-compose.whooshd-smoke.yml \
  -f /private/tmp/codexify-mainline-proof-28c95/candidate.override.yml \
  -f /private/tmp/codexify-mainline-proof-28c95/receipt-candidate-adoption/integrated.override.json \
  config --no-interpolate --no-env-resolution -q
```

The first attempted structural check used
`/private/tmp/codexify-mainline-proof-28c95/source/.env`, which does not exist;
it failed before rendering. The corrected syntax-only check above passed.
That correction does not establish a future mutation environment; existing
resolved container environment was not printed or adopted as policy.

## Drain, quiescence, backups and rollback — withheld at the frontier

Each row below is an explicit STOP gate, not an implied executable step.
The authoring task cannot finish an authorized procedure by supplying generic
Docker primitives where the accepted candidate checkpoint contract is missing.

| Phase | Source-derived finding and precondition before a future procedure can be approved |
| --- | --- |
| Admission stop | Backend is a writer and may still admit work. Chat-worker signal handling does not close backend admission. A future checkpoint procedure must define safe closure without losing admitted work. No invented maintenance env flag or route is supplied. |
| Queued work drain | Existing chat accepted-deadline/terminal semantics apply; retained non-chat system queues cannot be silently discarded. Empty LLEN is only observation. No dequeue/delete/replay command is allowed. |
| In-flight completion | c511f154b chat SIGTERM/SIGINT waits for executor work and logs `accepted work drained`; its 13m5s grace is versioned. Active document embedding is explicitly not bounded by the 10s grace. Chat-embed has no graceful-drain signal implementation at that revision. No timeout escalation or forced task abandonment is defined here. |
| Durable terminal disposition | Canonical completed-message link/terminal event and original accepted envelope must agree. Neither queue emptiness nor heartbeat/process absence substitutes for this evidence. No attempt state or deadline repair is authorized. |
| Storage writer quiescence | Relevant backend/worker application writers and database/Redis/Neo4j engine persistence must be distinguished. Chroma attachment scans cannot certify all those stores. A consistent checkpoint requires the candidate-wide procedure, not copying active data directories or calling ordinary admission preflight. |
| Protected backups | No accepted exact candidate destination or complete PostgreSQL/Redis/Chroma/Neo4j capture-and-restore procedure was found in the inspected versioned machinery. Do not retarget preview-only helpers, choose a path, impose retention, or treat retained scratch dumps as current safe backups. |
| Scoped adoption | Backend image and c511f154b client are independently known, but activation environment, preserved-source overlay, exact mount parity and protected rollback checkpoint are not authorized by this stopped document. No adoption override is generated. |
| Chat-embed activation | Committed consumer exists, but adding it can immediately consume ordinary/import queues and write Postgres/Chroma. STOP until checkpoint/isolation/readiness and its exact candidate source/env/mount config are approved. |
| Restart/recreation | ADR-101 requires guarded same-store reattachment. Bare Makefile restart and broad Compose up/down do not establish bounded candidate continuity. No restart command is supplied before checkpoint and adoption fidelity pass. |
| Rollback | Pre-adoption image/container/mount pins were captured. A consistent data/client/config/worker-set restore with verified independent backups is not derivable from those pins alone. Do not restore historical Chroma, destroy backups, remove volumes or assume image reversal undoes durable writes. |

The available preview helper freezes its entire hard-coded preview project and
restarts selected preview services; its PostgreSQL/media restoration proof
cannot be promoted to this candidate's Redis/Chroma/Neo4j rollback. The tester
Postgres documentation likewise concerns a different project and does not
provide the required candidate-wide checkpoint. Historical candidate scratch
backup files are evidence from earlier operations, not a maintained versioned
procedure or freshly usable backup for this adoption.

## Canonical chat-embed status

**Committed implementation exists; no source implementation task is required to
name the consumer.** Service `worker-chat-embed` is defined at c511f154b in
`docker-compose.yml:805–863`; command is
`-m guardian.workers.chat_embedding_worker` through the admitted-storage guard.
Its image must use the prepared backend digest, not the prior running tag or
mutable latest. The prepared image contains this committed backend tree per
the earlier source-equivalence attestation; fresh in-runtime fidelity remains
unproven.

Queues are `codexify:queue:chat-embed` and
`codexify:queue:chat-import-embed`; the latter is polled first. Dependencies
include candidate Postgres, Redis, admitted `/app/.chroma`, local embedding model
`/models/bge-large-en-v1.5`, HF cache, committed config and mounted admission
receipt. Required posture includes `CODEXIFY_VECTOR_STORE=chroma`,
`CODEXIFY_CHROMA_PATH=/app/.chroma`,
`CODEXIFY_COLLECTION=codexify_vault_supported`; the Whoosh'd smoke overlay's
`x-whooshd-embed-provider` supplies local-only/no-cloud posture. Compose specifies
healthy backend/Redis and completed model-prep dependencies. It also configures
Neo4j; no new graph-write authority is inferred.

Startup log `worker started queue=... import_queue=...` proves loop entry only,
not a health check or correct embeddings. Future proof must establish exact
prepared image/source, candidate-only DB/Redis/network/store/receipt bindings,
unchanged model selection and actual derived-state behavior. Neither starting
it nor testing it is authorized now. Do not read or copy uncommitted recovery
implementation into a runnable source tree.

## Recovery exclusion and invariant check

Recovery checkout and four content hashes observed read-only:

| Recovery-owned file | SHA-256 |
| --- | --- |
| `guardian/tests/migration/test_chatgpt_ingest.py` | `d904f467edb65211c40cb19e5d350af59938c10db8fbdd465b72383c3bf0eb1f` |
| `guardian/workers/chat_embedding_worker.py` | `c159df0aa8a7eef57d6f74104930e65c549f51feb454752b8f11bd77a319004b` |
| `tests/workers/test_chat_embedding_canonical_handoff.py` | `f7782be3da76b813e0713132c97af3ce83761985ea8ee2ccdac23e55b1ef4b13` |
| `tests/workers/test_chat_embedding_worker_import_replay.py` | `d1579a86d93dc97209609235fd4b1ef31c358bb2f7d1b51cc3d1233307e8c627` |

No matching recovery test process was found in the bounded host pattern scan;
no specific surviving PID was provided. That is not a proof of owner inactivity.
No process signals, restart, termination, message to the recovery chat or file
mutation occurred. All unrelated supplied-checkout changes remain outside scope.

Postgres stays canonical; Chroma remains derived and admitted to its existing
installation. Model/queue/message/request/deadline/terminal semantics remain
unchanged. Historical stores and current data were not imported, deleted,
restored or replaced. Browser visibility, request acceptance, build success and
empty queues have not been promoted to persistence/completion/release proof.

## Authoring validation — observed versus derived versus unproven

**Observed:** authoring Git HEAD/status and blocked commit; prepared source
commit existence; current candidate Docker inventory/volume labels; prepared
image identity/label; all 16 current-client output hashes; SELECT-only schema,
counts/terminal flags and queue-depth observations; no queue-name env overrides;
no matching recovery-test process. Source fingerprints and filtered baseline
are retained in `/private/tmp/codexify-native-runbook-authoring-20261007-01a116f7/`.
This is evidence scratch only, not a backup or maintained truth/config surface.

**Derived from versioned behavior:** committed chat-embed names/queues/mount
contract, chat-worker signal drain, document worker's active-drain limitation,
guarded Chroma reattachment, preview-only backup tool scope and operator-chosen
destination, Makefile config/restart semantics. No new operational semantics.

**Still unproven:** exclusive current custody, complete accepted-work drain,
store-wide writer quiescence, protected candidate backup/restore usability,
activation env/config fidelity, adoption, chat-embed activation, native chat
success/failure/final-read custody, restart and rollback correctness.

Required read-only Git/Docker checks ran successfully. Initial guessed `.env`
config check failed and was not hidden; corrected syntax-only config passed.
No helper that creates/stops/removes a container was run. PostgreSQL SELECT
queries were enclosed in a read-only transaction; Redis observations did not
mutate queue entries. No automated runtime tests apply to this preparation.
The Markdown's shell blocks are syntax checked without executing them; all
embedded Python preflight blocks are compiled without executing candidate
operations. Scoped proof diff/whitespace, final status, one-file commit scope
and pre/post preservation checks are required before closeout.

Only this document is created and committed. No application/source/test edits,
backups, runtime adoption, service stop/restart/recreation, migration, queue/lock
mutation, merge, push, deployment or release-claim expansion.

## Qualification handoff — ineligible until the frontier is resolved

After a separately approved executable checkpoint/adoption/rollback procedure
has actually passed fidelity/readiness, native qualification may check ordinary
chat, durable canonical readback, failure/rejection, composer release, no
automatic duplicate retry, no ghost assistant, a subsequent successful request,
final-read promise custody, derived embedding, bounded restart/recreation,
durable readback after restart and a new ordinary chat turn after restart.
None of those tests was run in this task. Fidelity/readiness alone would prove
adoption identity, not chat correctness or release readiness.

**STOP — HUMAN_DECISION_REQUIRED.** Approve the missing candidate-wide protected
checkpoint/restore procedure and independent destination before generating or
executing mutating adoption commands. This task does not make that selection or
begin the next slice. Release remains **HOLD**.
