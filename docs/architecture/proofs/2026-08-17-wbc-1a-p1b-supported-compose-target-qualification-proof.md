# WBC-1A-P1B — Supported Compose Target Qualification Proof

## Purpose

This operational proof continues WBC-1A-P1 after P1A restored the VaultNode
Docker/Compose prerequisite. It resolves the prior clean-proof-checkout branch
ambiguity, instantiates the selected `codexify-audit` topology from a clean
current-tip `main` checkout, and stops at its first runtime prerequisite
failure. No WBC-1A ordinary-chat lifecycle was run.

## Result

**BLOCKED** — first blocking boundary: **migration/init**. The required
`migrator` exited `1` while applying the current migration head, preventing the
backend and required workers from starting. This proof performs no migration,
database, Compose, or source remediation.

## Authority and source identity

| Item | Observation |
| --- | --- |
| Current `origin/main` after `git fetch origin` | `eb6bdc530245fdffeff23589c98389be4102b564` |
| G0 baseline | `eb6bdc530245fdffeff23589c98389be4102b564` |
| Source checkout | `/private/tmp/codexify-wbc-1a-p1b-main` |
| Branch / HEAD / upstream | `main` / `eb6bdc530245fdffeff23589c98389be4102b564` / same |
| Merge base / G0 ancestry | both current main; G0 is an ancestor |
| Checkout status | clean; the local `.env` bootstrap is ignored |
| Runtime host | `VaultNode.local` |
| Host role / authority basis | `canonical_evidence_host` / `ADR-041` |

P1A's `wrong_branch` result was caused by its otherwise clean checkout being
on `codex/wbc-1a-p1-supported-proof`. The canonical identity collector requires
the symbolic branch to be exactly `main`; it does not accept a detached head or
an arbitrary proof branch. A separate normal clone of current `origin/main`
resolved that condition without resetting, stashing, committing, rebasing, or
otherwise disturbing an existing worktree.

The identity collector recorded `observation_complete=true`,
`canonical_repository_candidate=true`, and
`canonical_machine_candidate=true`, with no branch/repository reason code.

## Selected supported target and effective posture

| Item | Observation |
| --- | --- |
| Compose project / role | `codexify-audit` / `audit` |
| Compose source | clean clone's `docker-compose.yml` |
| Supported profile | `v1-local-core-web-mcp` |
| Required services | `frontend`, `backend`, `db`, `redis`, `worker-chat`, `worker-document-embed`, `migrator` |
| Optional services | `worker-warmup`, `neo4j`, `graph-init` |
| Expected local runtime | `whooshd-mlx` / Whoosh'd |
| Expected chat model | `qwen3.8-27b-4bit` |

The documented ignored local environment bootstrap was used without recording
its values. `docker compose ... config --quiet` passed before startup. A
bounded non-secret projection for backend, `worker-chat`, and
`worker-document-embed` agreed on:

- `CODEXIFY_CONFIG_SOURCE=core`;
- `CODEXIFY_SUPPORTED_PROFILE=v1-local-core-web-mcp`;
- local-only mode enabled, cloud providers disabled, and empty egress
  allowlist;
- provider `local`, preset `whooshd-mlx`, compatibility-first mode, and vendor
  `whooshd`; and
- local chat model `qwen3.8-27b-4bit`.

The host-local Whoosh'd model inventory advertised exactly
`qwen3.8-27b-4bit` before startup. That host preflight is not a claim that the
blocked target backend completed provider readiness.

## Supported startup and lifecycle observation

The repository-documented lifecycle was run from the clean `main` source with
the resolved project and environment inputs:

```text
docker compose --project-directory <clean-main-checkout> \
  --env-file <clean-main-checkout>/.env \
  -p codexify-audit -f <clean-main-checkout>/docker-compose.yml \
  up --build -d
```

The first invocation materialized the target's own containers while image
construction completed. A subsequent identical lifecycle invocation overlapped
that materialization and saw an `e2e` container-name collision, but bounded
label inspection established that the container already belonged to this exact
`codexify-audit` project and clean source checkout; nothing was deleted,
renamed, or reused from another project. The same supported lifecycle then
reached its dependency gates.

Required lifecycle state from the canonical collector was:

| Service | Lifecycle / state | Observation |
| --- | --- | --- |
| `db` | long-running / running, healthy | pass |
| `redis` | long-running / running, healthy | pass |
| `migrator` | required one-shot / exited `1` | fail — first blocker |
| `backend` | long-running / created | not running after migrator failure |
| `frontend` | long-running / created | not running after migrator failure |
| `worker-chat` | long-running / created | not running after migrator failure |
| `worker-document-embed` | long-running / created | not running after migrator failure |
| `neo4j` | optional / running, healthy | pass; not a substitute for required services |
| `graph-init` | optional one-shot / exited `0` | pass |

The bounded migrator signature identifies the failure in
`1c0a2b3c4d5e_add_chat_threads_origin_system.py`: PostgreSQL, via psycopg,
rejected the migration's parameterized tuple expansion at `IN $1` with a syntax
error. The migrator then reported `alembic upgrade failed` and exited `1`.
No migration source, database state, compatibility bridge, or migration
history was changed in this task.

## Health, provider, model, and worker readiness

Because migration/init failed, the required backend never started. Bounded
unauthenticated operator probes to `/health`, `/health/chat`, and
`/api/health/llm` each returned connection-refused (`curl` exit `7`, HTTP
`000`). Therefore:

- target-container local-provider and model readiness are not established;
- no supported model catalog projection is available from the backend;
- no chat-worker heartbeat or queue health can be established; and
- no synthetic health enqueue, real chat task, user message, or completion was
  run.

## Canonical live-proof receipt

The read-only collector was invoked from the clean `main` checkout with
`machine_id=vaultnode`, role `canonical_evidence_host`, project
`codexify-audit`, role `audit`, profile `v1-local-core-web-mcp`, and bounded
command/HTTP timeouts. It produced a schema-valid receipt:

| Field | Observation |
| --- | --- |
| Receipt ID | `live-proof-receipt-sha256-9a5e0c3e674cea9b8d4671a2e5bef1fc60173b418fea3e54563e7cd710366c2b` |
| Authority status | `CANONICAL` |
| Collector execution outcome | `ERROR` |
| Validation | passed; zero issues |
| Reason codes | `http_transport_error`, `required_one_shot_failed`, `required_service_not_running` |
| Docker projection | client and server both `29.7.2` |

The receipt no longer reports `docker_server_unavailable`,
`compose_project_missing`, or `wrong_branch`. Its remaining reason codes are
downstream effects of the recorded migrator failure, not grounds to continue
startup repair.

## Runtime/source correspondence and limits

The created audit backend labels identify project `codexify-audit`, service
`backend`, the clean-main Compose working directory, and that checkout's
Compose file. Its source bind mounts resolve to the same clean checkout's
`guardian`, `backend`, `config`, `plugins`, test, model, and local data paths.
No dirty Tester source is mounted into the audit target.

The existing cloud-capable, dirty `codexify_tester` stack was neither stopped,
reconfigured, relabelled, nor used as WBC evidence. PostgreSQL and Redis retain
their normal application roles; the state created by the supported lifecycle is
operational state, not a repository-source modification.

This proof does not establish an eligible WBC-1A target, G1, a successful
migration, backend/provider/model health, worker readiness, or chat closure.
The known turn-lock test was not run, diagnosed, or changed.

## ADR impact

Aligned with ADR-041, ADR-042, ADR-052, and ADR-069. This task instantiated
and observed the accepted local-only audit topology; no architectural decision
or release claim changed.

BLOCKED
