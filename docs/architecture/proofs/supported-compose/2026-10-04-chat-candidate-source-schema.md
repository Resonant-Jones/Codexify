# Coherent repaired chat source/schema candidate — 2026-10-04

## Authority and evaluated revision

Development Operator Level 0, architecture-impact, PROOF_REQUIRED, EXECUTE →
PROOF. The active ordinary-chat reliability Goal authorizes this isolated
supported-runtime refresh and forward schema proof. ADR-087/038/003 and the
human-approved original-deadline reconciliation policy govern. No new ADR,
runtime token, acceptance authority or release claim.

Clean evaluated repair `bbf319376ca8bde42e7ff94cbf1f3d77194a9391`, branch
`codex/chat-postgres-terminal-deadline-20261003`. Prior Task progress was the
[bounded SSE repair](./2026-10-04-chat-sse-read-bound.md). Its host/native tests
could not qualify the earlier retained application's source/schema. This Task
prepares that prerequisite; it does not perform a new accepted chat turn.

## Frozen source and reviewed activation

Private Task Spec and evidence root:
`/private/tmp/codexify-chat-candidate-runtime-bbf319376-20261004/`.
`prepare.py`, `activate.py`, `validate.py`, source/config manifests, activation
plan/logs, before/after data, catalog/health and preservation failures remain.
The new immutable runtime source snapshot is `source/` there. The earlier
`/private/tmp/codexify-chat-branch-proof-896387ad2-20261003/source/` is preserved.
Only existing LFS payloads matching their pointer hashes/sizes were retained;
no download or install occurred. Nonruntime asset pointers are not claimed as
hydrated application UI. Frontend serving is a separate next proof.

The project remains `codexify_chat_branch_proof_896387ad2`, backend loopback
port 18889, PostgreSQL loopback port 55433. Source comes from the clean repair,
not mutable main. Committed Compose files plus candidate binding overrides
form a private wrapper. Raw resolved configuration was compared in memory with
both prior app containers; all configured environment values matched. Secrets
were neither printed nor copied into the source artifact.

The exact existing app image is pinned:
`sha256:0f842ac1f9f8fec04af74b253f831aeb872644cbfbb58b839fd25eea37756649`.
Existing model bind paths, read/write posture, and named data volumes remain.
There was no build/pull, model download, volume deletion, database reset or
unrelated service operation. Preflight required health `ok`, idle heartbeat
with positive TTL, chat queue zero and no turn locks. All 71 messages and 37
attempts were captured before mutation.

The reviewable activation plan executed once:

```text
docker stop --time 15 <owned backend> <owned worker-chat>
<private compose.sh> run --rm --no-deps --pull never migrator
<private compose.sh> up -d --no-deps --no-build --pull never backend worker-chat
```

Each command exited zero. The canonical migrator ran `upgrade heads`, applied
`d4c69e03a712 -> e8a9b03d6712 -> f1a6d83b9024`, and ran its standard seed script.
Seed logging reported accounts=0/existing=0/promoted=0/created=0. No speculative
restart or duplicate migration followed a polling timeout. Both app containers
were intentionally recreated; their old lifecycle was not claimed unchanged.

## Native checks and preservation

`prepare.py`, `activate.py` and the final `validate.py` passed. Hash checks prove
all **1,140** tracked Guardian/backend Python files match the committed repair,
new source snapshot and both fresh app containers. This includes the two new
migrations and the repaired vector, acceptance/recovery, worker, PostgreSQL,
Redis and SSE surfaces. Recreated container start instants:

- Backend: `2026-10-05T02:02:44.686867759Z`, restart count 0.
- Chat worker: `2026-10-05T02:03:05.86418513Z`, restart count 0.

The UTC date crosses midnight; execution remains October 4 in the operator's
America/New_York timezone. PostgreSQL and Redis container IDs, image IDs, start
instants and restart counts stayed unchanged. The previous source's frozen
hashes remain unchanged.

Database head is exactly `f1a6d83b9024`. PostgreSQL exposes
`chat_attempt_recovery_snapshot_immutable` and `chat_attempt_orphan_fence`.
All 37 existing attempt projections retain request/task/thread/turn identity,
acceptance confirmation, assistant binding and terminal kind. All 71 existing
messages retain IDs, roles, contents and metadata. Every historical recovery
snapshot, cleanup token and orphan detail remains SQL NULL; no historical
backfill, deadline reconstruction or retroactive orphan classification occurred.

Fresh health is `ok`. Chat queue zero, locks absent, idle heartbeat with positive
TTL. Catalog returns approved, valid `v1-local-core-web-mcp`, local Whoosh'd
provider and one available `local-chat` model (Gemma 4 12B IT QAT 4-bit), no cloud
configuration promotion. Resolved app policy remains `LLM_PROVIDER=local`,
`CODEXIFY_LOCAL_ONLY_MODE=true`, `ALLOW_CLOUD_PROVIDERS=false`. Catalog availability
is not generation, durable completion or browser proof. A full fresh catalog
baseline was not separately saved before activation; environment parity and
post-activation inventory are the actual evidence.

## Preserved failures and concurrent state

The first validation failed an overly strict queue-count preservation assertion:
canonical backend startup added one `warmup` task with origin `startup`, system
queue **17 -> 18**. Evaluation queue stays 34, chat queue stays zero. Exact new
warmup identity/timestamp is retained in `startup-queue-delta.json`. The entry
was not deleted or executed by this Task. Existing queue payloads were not
individually snapshotted before activation, so raw queue-content equality is
not claimed. Initial script/log and corrected evidence are separate artifacts.
The validator's initially drafted trigger-name expectation was corrected to
the actual migration-defined name before that check ran.

The next validation passed runtime checks but detected concurrent main
advancement from `0163521312ef767c0884654e70094ae7b44a5eec` to
`b6f5423f1` (`Publish 2026-10-05 daily dev log`). Main also carries the existing
architecture/KG/workspace/memory-vault/test edits and staged dev-log deletions.
The Task issued no main mutation; read-only before/after status/hash observations
are retained. Original main checkpoint equality is explicitly false, not silently
reported as preservation. No concurrent edit was staged, reverted or copied
into this frozen repair candidate.

## Documentation, limits and next task

Only this repository proof receipt changed. No automated product regression
suite applies to the documentation-only diff; actual Docker, migration,
source-hash, API, SQL and Redis checks above are this Task's proof surface.
`python3 scripts/validate_docs.py`, local links and `git diff --check` passed.
Commit hash is supplied in the Task closeout. Release anchors remain unchanged;
no main integration, push, merge, deployment or shared-memory write.

The earlier unconfirmed-admission limitation remains: enqueue acknowledgement
followed by database confirmation failure yields `accepted_degraded`; an exact
worker packet can execute with the original stored snapshot, but recovery keeps
an unresolved `accepted_at`-NULL attempt unknown. This Task neither infers queue
acceptance later nor grants a new durable acceptance authority. The existing
worker-anchor test fixture failure recorded in the SSE receipt also remains.

The candidate now supports the next meaningful proof: serve the committed
frontend and perform fresh ordinary success and important failure/recovery turns,
checking exact original deadlines, attempt/message/event/UI agreement, explicit
new retry identities, provider rejection, orphan fencing, restart and graceful
shutdown. These have not been demonstrated on this candidate by this Task.
Full Goal remains active; release HOLD.
