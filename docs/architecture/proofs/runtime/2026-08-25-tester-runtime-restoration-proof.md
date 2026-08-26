# Tester runtime restoration proof

## Result

`TESTER_BACKEND_STARTUP_FAILURE`

The one authorized canonical Tester backend start stopped at its declared
`migrator` dependency. The migrator exited once because its runtime could not
locate Alembic revision `6e9f0a1b2c3`; the backend consequently remained
`created` and was never started. `worker-chat` was not started.

This is an operational failure receipt only. It neither changes Tester
provider/model authority nor establishes current-`main` runtime or release
truth.

## Source, authority, and canonical posture

- Source HEAD before runtime activity:
  `0658cf4c21e0f48a61dc2151124f87f1d0eeec14` (`Prove Watchdog Gemma runtime`).
- Branch: `codex/diagnose-tester-fresh-chroma-failure`.
- Required Watchdog-blocker, authenticated Tester completion, and chat-worker
  readiness commits were all verified ancestors.
- Compose project: `codexify_tester`.
- Exact Compose inputs: `docker-compose.yml`, `docker-compose.tester.yml`, and
  `docker-compose.whooshd-deepseek.yml`, with `.env.tester`.
- `.env.tester` remained ignored and unchanged.

The read-only non-secret operator posture matched the accepted branch-local
Tester topology:

| Setting | Effective value |
| --- | --- |
| `LLM_PROVIDER` | `local` |
| `LOCAL_CHAT_MODEL` | `gemma-4-12b-it-qat-4bit` |
| `ALLOW_CLOUD_PROVIDERS` | `true` |
| `CODEXIFY_LOCAL_ONLY_MODE` | `false` |
| `CODEXIFY_EGRESS_ALLOWLIST` | `deepseek` |

The canonical Compose render passed with only the existing optional-unset
`LOCAL_VISION_MODEL` and `LOCAL_GGUF_MODEL` warnings. Sanitized backend and
worker-chat render values matched the same provider/model/cloud/local-only
posture and had their canonical database and Redis references present. No
model, provider, egress, or supported-profile value was changed.

## Pre-start runtime boundary

| Component | State before the attempt |
| --- | --- |
| Postgres | running and Docker healthy |
| Redis | running and Docker healthy; `PING=PONG` |
| Neo4j | running and Docker healthy |
| `graph-init` | exited `0` |
| `model-prep` | exited `0` |
| `migrator` | exited `1` |
| `backend` | `created` |
| `worker-chat` | `created` |
| Normal chat queue | depth `0` |

Source Alembic head and the live Tester database both reported the legitimate
current revision `6e9f0a1b2c3`. The migration failure was therefore not a
database-version mismatch: the existing migrator runtime's Alembic source did
not contain the revision already recorded by the database.

Before the start, durable counts were `5137` chat threads, `113328` chat
messages, and zero Watchdog attempts, dispatches, and results. No Redis queue
was inspected, cleared, popped, or changed.

The active derived Chroma path was
`/Users/chriscastillo/.codex/worktrees/5ab6/Codexify-main/.chroma`: five files,
`42,588,516` aggregate bytes, `chroma.sqlite3` SHA-256
`602eca12546c7bc177e801f065df87afa6713c3b1a61693450a455fc464a5e46`, and
manifest SHA-256
`0beae226796d1f605b99c5330b5a34f72a792d28e0fd911bdc652b46b94bce1f`.
Both historical Chroma preservation generations were read-only
(`dr-xr-xr-x`).

## One canonical backend start

`TESTER_BACKEND_START_ATTEMPTS=1`

The sole authorized operation was:

```text
docker compose --env-file .env.tester -p codexify_tester \
  -f docker-compose.yml -f docker-compose.tester.yml \
  -f docker-compose.whooshd-deepseek.yml up -d backend
```

Compose normally recreated the backend's declared dependency set while
preserving the existing named volumes. Database, graph-init, and model-prep
completed their normal lifecycle, but `migrator` exited `1`. The canonical
backend was recreated but remained `created`, with no start timestamp, no
health status, restart count `0`, and zero backend log bytes.

The first causal evidence from the migrator was:

```text
alembic.script.revision.ResolutionError: No such revision or branch '6e9f0a1b2c3'
alembic.util.exc.CommandError: Can't locate revision identified by '6e9f0a1b2c3'
```

No `CODEXIFY_STARTUP_FAILURE_RECEIPT` or `backend_startup_failure` event was
emitted because the backend process did not begin. There was no retry, image
rebuild, migration stamp, database reset, source repair, or manual schema
operation. `TESTER_CHAT_WORKER_START_ATTEMPTS=0` by design: its backend health
precondition was not reached.

## Post-attempt preservation and no-execution boundary

After the failed dependency gate, the database remained at `6e9f0a1b2c3` with
the same counts (`5137` threads, `113328` messages, zero Watchdog attempts,
dispatches, and results). Redis returned `PONG`; the normal chat queue remained
depth `0`. The Chroma fingerprint and both read-only preservation directories
were unchanged from the pre-start readback.

No `/health`, `/health/chat`, provider health/catalog, or post-restoration
Whoosh'd inventory request was made because the backend did not start. Thus
there is no new exact-model availability classification in this receipt.

No proof-only account/session was used. Threads created, chat tasks created,
assistant messages, local model requests, DeepSeek requests, Watchdog attempts,
Watchdog dispatches, and Watchdog model requests were all `0`. No Watchdog
worker, Command Bus, coding worker, Build Loop, GitHub, or publication surface
was started or invoked.

## ADR impact and validation

**Aligned with existing Tester provider/model authority; no ADR change.**
ADR-074 remains decisive: the operator-selected Gemma configuration was
observed, not rewritten in response to stale runtime inventory or startup
failure. ADR-052's local-default plus bounded DeepSeek lane remains unchanged.

- Required ancestry, clean-worktree, and `.env.tester` ignore checks passed.
- Canonical Tester Compose render passed with only pre-existing optional-model
  warnings.
- Source and live database Alembic revision checks matched at `6e9f0a1b2c3`.
- Redis reachability and empty-chat-queue checks passed before and after the
  attempt.
- The one canonical backend start and bounded migrator/backend evidence checks
  completed; the first causal migration-runtime failure was preserved.

`docs/architecture/00-current-state.md` is unchanged. This branch-local
receipt does not widen Beta or support posture.

## Deferred next slice

Repair only the first exposed seam: align the canonical Tester migrator runtime
with the current source migration lineage containing `6e9f0a1b2c3`, then rerun
the restoration proof from its start. Do not combine that repair with any
Tester model-authority or Watchdog policy change.
