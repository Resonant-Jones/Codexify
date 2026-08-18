# WBC-1A-P1 — Supported Compose Target Readiness Proof

## Purpose

This proof establishes whether a distinct, current-tip local-only Compose
target is ready for a fresh WBC-1A closure run. It follows the blocked WBC-1A
receipt and deliberately does not submit a chat message, create a proof
thread, exercise queue or turn-lock behavior, or claim end-to-end closure.

## Result

**BLOCKED** — the first blocking boundary is the Docker/Compose prerequisite.
The clean, current-tip target and its local-only configuration were resolved,
but the documented Compose startup stopped before creating a project because
Docker Desktop reported that it was unable to start.

## Git and authority preflight

| Item | Observation |
| --- | --- |
| Current GitHub `main` | `eb6bdc530245fdffeff23589c98389be4102b564` |
| G0 baseline | `eb6bdc530245fdffeff23589c98389be4102b564` |
| Current-main delta from G0 | none |
| Isolated proof source HEAD | `eb6bdc530245fdffeff23589c98389be4102b564` |
| Proof source branch | `codex/wbc-1a-p1-supported-proof`, tracking `origin/main` |
| Cleanliness | clean; the local `.env` bootstrap is ignored |
| `origin/main` ancestry | HEAD equals `origin/main`; HEAD contains G0 |
| Runtime machine | `vaultnode.local` / machine id `vaultnode` |
| Machine role and authority basis | `canonical_evidence_host` / `ADR-041` |

`git fetch origin` completed before this preflight. The previously available
`main` worktree was excluded because it did not contain current `origin/main`.
No existing checkout was reset, stashed, committed, or otherwise changed.

The isolated source checkout is at
`/private/tmp/codexify-wbc-1a-p1-supported-proof`. It is a distinct clean
worktree created directly from current `origin/main`; it is the only source
authorized to supply the proposed target containers.

The canonical collector reported a **PROVISIONAL** authority status, not a
canonical evidence promotion. The machine assertion was complete, while the
dedicated proof worktree's branch name caused the bounded `wrong_branch` reason
code. That does not convert a clean current-tip source into a release claim.

## Existing Tester exclusion

The pre-existing `codexify_tester` project was not stopped, reconfigured,
relabelled, rebuilt, or used as WBC evidence. Its previously established
exclusion remains in force: it is a cloud-capable
`v1-whooshd-deepseek-web` topology bound to a different dirty source tree and
cannot substitute for the default local-only profile.

No other running project was repurposed. The proposed target is the distinct
`codexify-audit` Compose project with role `audit`.

## Supported target selection and effective posture

The target inputs came from the current supported-profile manifest, base
Compose configuration, and canonical collector interface:

| Item | Resolved target |
| --- | --- |
| Compose source | `docker-compose.yml` from the isolated current-tip worktree |
| Compose project / role | `codexify-audit` / `audit` |
| Supported profile | `v1-local-core-web-mcp` |
| Compose environment file | local ignored `.env` created by the documented template-copy bootstrap |
| Loopback origins reserved for the collector | API `http://127.0.0.1:8888`; frontend `http://127.0.0.1:5173` |
| Required services | `frontend`, `backend`, `db`, `redis`, `worker-chat`, `worker-document-embed`, `migrator` |
| Optional services | `worker-warmup`, `neo4j`, `graph-init` |
| Required one-shot service | `migrator` |
| Expected provider | local Whoosh'd / `whooshd-mlx` |

`docker compose config --quiet` succeeded for the selected project. A bounded
projection of backend, chat-worker, and document-embed-worker configuration
showed the same effective non-secret posture:

- `CODEXIFY_CONFIG_SOURCE=core`;
- `CODEXIFY_SUPPORTED_PROFILE=v1-local-core-web-mcp`;
- local-only mode enabled, cloud providers disabled, and an empty egress
  allowlist;
- selected provider `local` with the Whoosh'd runtime preset and local Docker
  host endpoint semantics;
- `LOCAL_COMPAT_FIRST=true`, vendor `whooshd`, display name `Whoosh'd`;
- local chat model `qwen3.8-27b-4bit`; and
- in-project Redis target semantics.

No cloud credential, provider override, raw dotenv value, database URL, or
other secret-bearing configuration was recorded. The local-only bootstrap
changed no tracked repository file.

## Local provider and model readiness

Before Compose startup, the host-local Whoosh'd inventory endpoint was
reachable and advertised exactly `qwen3.8-27b-4bit`. This matches the selected
target model. It proves host inventory reachability only; it is not a provider
execution or chat-completion proof.

## Startup attempt and first blocker

The documented normal lifecycle was invoked from the isolated source with the
selected project, environment file, and base Compose file:

```text
docker compose --project-directory <isolated-current-tip-worktree> \
  --env-file <isolated-current-tip-worktree>/.env \
  -p codexify-audit -f <isolated-current-tip-worktree>/docker-compose.yml up -d
```

It stopped immediately while resolving `neo4j:5`:

```text
Docker Desktop is unable to start
```

Read-only confirmation immediately afterward produced nonzero `docker info`
and `docker compose ... ps --all` results with the same Docker Desktop
unavailability. No service, migration, init job, volume, provider request,
worker heartbeat, or container source mount could therefore be observed.

This task did not retry the start, alter Docker Desktop, rebuild images, change
the shared image tag, modify Compose configuration, bypass an init service, or
use an alternate runtime.

## Canonical live-proof receipt

The required read-only collector was run against the selected target:

```text
make PYTHON=<repository-venv>/bin/python canonical-audit-live-proof-receipt \
  repo=. machine_id=vaultnode machine_role=canonical_evidence_host \
  authority_basis=ADR-041 assert_canonical_machine=1 \
  compose_file=docker-compose.yml compose_project=codexify-audit \
  project_role=audit audit_project=codexify-audit \
  profile_name=v1-local-core-web-mcp compose_env_file=.env \
  api_base=http://127.0.0.1:8888 frontend_base=http://127.0.0.1:5173 \
  command_timeout=10 http_timeout=5
```

Safe receipt summary:

| Field | Observation |
| --- | --- |
| Receipt ID | `live-proof-receipt-sha256-7cf6e2b710621e9aea99f2e45f4a746724daac39d59674da0e42f0a62e373a0c` |
| Collector outcome | `BLOCKED` |
| Receipt schema validation | passed |
| Authority status | `PROVISIONAL` |
| Repository projection | clean `eb6bdc530245fdffeff23589c98389be4102b564`, upstream equal |
| Supported profile | `v1-local-core-web-mcp` |
| Selected project / role | `codexify-audit` / `audit` |
| Services and fixed health probes | none observed; Docker server was unavailable before observation began |
| Reason codes | `docker_server_unavailable`, `wrong_branch` |

The collector's static runtime identity resolved the expected migration head
and supported service set, but no migration/init completion can be inferred
until Docker is available and the project starts.

## Eligibility matrix

| Requirement | Result |
| --- | --- |
| Allowed VaultNode machine and declared role | pass |
| Clean current-tip checkout containing G0 | pass |
| Distinct supported Compose project/profile resolved | pass |
| Local-only and cloud-disabled effective semantics | pass |
| Host-local model inventory coherent with selected model | pass |
| Source/runtime mount correspondence | not observable: no target container started |
| Migration/init completion | not observable |
| Required services healthy | not observable |
| Local provider available from target container | not observable |
| Worker heartbeat fresh | not observable |
| Canonical collector can observe live selected project | blocked by Docker server unavailability |
| WBC-1A chat lifecycle | intentionally not attempted |

## Static turn-lock test

The previously failing
`guardian/tests/test_chat_memory.py::test_chat_complete_turn_lock_blocks_parallel_requests`
test was not rerun. Docker availability is the first target-readiness blocker;
the test is not needed to classify this prerequisite result and was not
repaired or used to make a G1 determination.

## Limitations and invariant check

- This document does not establish `ELIGIBLE`; Docker availability prevented
  all live Compose service, migration, health, provider, and worker evidence.
- It does not establish WBC-1A completion, G1, G2, release readiness, or
  canonical evidence promotion.
- The dirty cloud-capable Tester stack was not repurposed or disturbed.
- No tracked runtime, profile, migration, Compose, test, ADR, Campaign, or
  current-state file changed.
- No cloud-provider enablement, chat attempt, turn-lock repair, release claim
  expansion, or secret leakage occurred.

**WBC-1A-P1 BLOCKED — prerequisite remediation required.** The next authorized
task must resolve the Docker Desktop/server prerequisite, then re-qualify this
exact current-tip isolated target before rerunning WBC-1A.

BLOCKED
