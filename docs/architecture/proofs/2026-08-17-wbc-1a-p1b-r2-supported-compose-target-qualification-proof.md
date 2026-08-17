# WBC-1A-P1B-R2 — Supported Compose Target Qualification on Post-Repair Main

## Purpose and scope

This operational receipt requalifies the distinct supported audit target after
the historical P1B migration/init stop. It preserves P1B unchanged: that
attempt found the psycopg3 tuple-binding failure in revision `1c0a2b3c4d5e`.
P1C repaired that execution defect with SQLAlchemy expanding binds, retained
the revision and its parent `9d4c2a7e1b6f`, and proved the repair on disposable
PostgreSQL. PR #716 then landed the complete evidence and repair chain on
canonical `main`.

This task ran no ordinary WBC-1A chat lifecycle, authored no proof thread,
sent no completion request, and did not run, debug, or repair the turn-lock
test. It exercised only the supported audit lifecycle and its bounded
readiness observations.

## Canonical source and authority

| Item | Observation |
| --- | --- |
| VaultNode identity | `VaultNode.local` / machine ID `vaultnode` |
| Runtime and audit role | `canonical_evidence_host` under ADR-041 |
| Current `origin/main` | `e4168ad08f6c14de6dc78129e6053d504548382c` |
| Proof source branch / HEAD | literal `main` / `e4168ad08f6c14de6dc78129e6053d504548382c` |
| Source cleanliness | clean; the supported ignored local `.env` was the only bootstrap state |
| Merge base with `origin/main` | `e4168ad08f6c14de6dc78129e6053d504548382c` |
| PR #716 merge ancestry | `e4168ad08f6c14de6dc78129e6053d504548382c` is an ancestor of the proof HEAD and `origin/main` |
| Current-main delta from the task-generation merge | none |

The proof checkout was a newly created, isolated clone of canonical `main`.
It was not the stale historical proof branch and was not the dirty Tester
checkout. The pre-existing cloud-capable `codexify_tester` project and its
source tree were not stopped, rebuilt, reconfigured, relabelled, or used as
evidence.

## Repair and static target identity

The canonical source contains P1C's migration repair and regression test:

- `guardian/db/migrations/versions/1c0a2b3c4d5e_add_chat_threads_origin_system.py`
  declares revision `1c0a2b3c4d5e`, parent `9d4c2a7e1b6f`, and both
  `openai_tokens` and `anthropic_tokens` as `expanding=True` binds.
- `tests/db/test_chat_thread_origin_system_migration.py` is present on the
  same canonical source and P1C's proof artifact is present.
- The repository's static canonical-runtime identity collector resolved one
  migration head: `1c0a2b3c4d5e`; it reported a complete migration identity
  with no reason codes.

## Supported target and configuration

| Item | Observed value |
| --- | --- |
| Compose project / role | `codexify-audit` / `audit` |
| Compose file | `docker-compose.yml` |
| Supported profile | `v1-local-core-web-mcp` |
| Required profile services | `frontend`, `backend`, `db`, `redis`, `worker-chat`, `worker-document-embed`, `migrator` |
| Optional profile services | `worker-warmup`, `neo4j`, `graph-init` |
| Profile-required one-shot service | `migrator` |
| Local-only mode | enabled |
| Cloud-provider allowance | disabled |
| Egress allowlist | empty |
| Selected provider / preset | `local` / `whooshd-mlx` |
| Expected local model | `qwen3.8-27b-4bit` |

The ignored local environment file was copied unchanged from the already
established audit configuration, through the repository's template-copy
bootstrap convention. Only the bounded non-secret fields above were inspected.
`docker compose ... config --quiet` completed successfully before startup.
No provider credential, database DSN, API key, or raw environment value is
recorded here.

## Supported startup, migration, and database readback

The documented Compose lifecycle was run once from the isolated canonical-main
checkout, with its local environment file and explicit audit project:

```text
docker compose --project-directory <isolated-canonical-main-checkout> \
  --env-file <isolated-canonical-main-checkout>/.env \
  -p codexify-audit -f <isolated-canonical-main-checkout>/docker-compose.yml \
  up -d --build
```

It rebuilt the backend image and reconciled the existing audit containers
without `down -v`, a volume deletion, a PostgreSQL reset, manual schema SQL,
an Alembic stamp, or a source/configuration edit.

The one-shot observations were:

| Service | Result |
| --- | --- |
| `migrator` | exited 0 |
| `model-prep` | exited 0 |
| `graph-init` (profile optional) | exited 0 |

Read-only PostgreSQL queries against the actual `codexify-audit` database
returned:

| Check | Result |
| --- | --- |
| `alembic_version` | `1c0a2b3c4d5e` |
| `chat_threads.origin_system` | present |
| `ck_chat_threads_origin_system_canonical` | present |
| `ix_chat_threads_user_origin` on `(user_id, origin_system)` | present |

This confirms that the repaired migration completed through the actual
supported audit lifecycle, not merely in the P1C disposable database.

## Runtime readiness

All profile-required long-running services were running; Docker health was
healthy where a health state is exposed:

| Service | State |
| --- | --- |
| `backend` | running, healthy |
| `db` | running, healthy |
| `frontend` | running |
| `redis` | running, healthy |
| `worker-chat` | running |
| `worker-document-embed` | running |
| `migrator` | completed successfully as above |

The profile-optional `neo4j` and `worker-warmup` services were running and
healthy where applicable. `graph-init` completed successfully. The unprofiled
`worker-coding` service was restarting; it was neither required by the selected
profile nor used in this proof, and no Coding Loop action occurred.

Direct bounded operator observations returned the following:

| Surface | Safe result |
| --- | --- |
| `GET /health` | `ok`; valid `v1-local-core-web-mcp`; expected and selected provider `local`; no profile mismatches; cloud-capable configuration absent; `release_hold=false` |
| `GET /health/chat` | `healthy`; Redis reachable; enqueue diagnostic succeeded; chat-worker heartbeat fresh; queue depth 0 during observation |
| `GET /api/health/llm` | outer status `ok`, `details.status=online`; local provider enabled, authorized, and available; configured model present and available |
| `GET /api/llm/catalog` | exactly one visible provider, `local`; inventory contained `qwen3.8-27b-4bit` |

The LLM health payload's provider truth showed a valid approved supported
profile, no cloud-capable configuration, local endpoint availability, and no
provider execution attempt. The catalog, runtime availability, model inventory,
and selected provider are recorded separately; they are not treated as a chat
completion proof.

## Worker and source/runtime correspondence

`/health/chat` observed `codexify:worker:chat:heartbeat` as fresh (3.144
seconds old in the recorded health observation), along with successful queue
and Redis diagnostic checks. No ordinary user work was enqueued.

Bounded container inspection tied the running audit project to the isolated
canonical source:

- backend and migrator both carry Compose project `codexify-audit` and the
  isolated canonical-main checkout as their Compose working directory;
- both use rebuilt image
  `sha256:0f5b8787d28bbad00b840daf489704c6d3e02243efc57ffc3552981ba32a0222`;
- backend bind mounts its `guardian`, `backend`, and read-only `config` inputs
  from that checkout; and
- migrator uses that checkout's backend input and the rebuilt image that
  contains the corrected migration.

There is no source-tree correspondence to the dirty Tester checkout, the
historical pre-merge proof branch, or the older `eb6bdc530245fdffeff23589c98389be4102b564`
tip.

## Canonical live-proof collector and first blocking boundary

The current repository-defined collector was invoked read-only with the
canonical inputs, including `compose_env_file=.env`:

```text
make PYTHON=<repository-venv>/bin/python canonical-audit-live-proof-receipt \
  repo=. machine_id=vaultnode machine_role=canonical_evidence_host \
  authority_basis=ADR-041 assert_canonical_machine=1 \
  compose_file=docker-compose.yml compose_project=codexify-audit \
  project_role=audit audit_project=codexify-audit \
  profile_name=v1-local-core-web-mcp compose_env_file=.env \
  api_base=http://127.0.0.1:8888 frontend_base=http://127.0.0.1:5173 \
  command_timeout=15 http_timeout=10
```

Its schema validation passed and it identified canonical authority, the clean
literal-main source, `codexify-audit`, the requested profile, all required
service lifecycle states, and four passing fixed probes. Its receipt was:

| Field | Observation |
| --- | --- |
| Receipt ID | `live-proof-receipt-sha256-abd45ed63208d1b4c4a31e013c0acafd08c5f1031105271669972f1c949827c9` |
| Authority status | `CANONICAL` |
| Collector outcome | `FAIL` |
| Passing probes | `/ping`, `/health`, `/health/chat`, frontend `/` |
| Failing probe | `/api/health/llm` |
| Reason codes | `llm_models_unavailable`, `provider_runtime_unavailable` |

The collector's LLM probe reads `models_available` and `provider_runtime` only
at the response top level. Current main's LLM endpoint returns its operational
fields under `details`; the route's current focused tests also assert that
shape. Consequently, the direct bounded observation above proves both fields
are present and healthy while the collector projects them as null and emits the
two false-unavailable reason codes. The correctly parameterized second
collection reproduced the failure, so this is not an omitted environment-file
argument or an actual local-provider/model outage.

The first blocking boundary is therefore canonical live-proof collector
interpretation of the current `/api/health/llm` response contract. This task
does not change the collector, the endpoint, tests, profile, migration, or
runtime configuration to resolve it.

## Limitations and invariants

- The fixed canonical collector suite did not produce a passing receipt, so
  this target is not authorized for the fresh WBC-1A runtime-closure proof.
- This receipt does not establish ordinary chat completion, queue/dequeue
  lifecycle, live turn-lock semantics, provider completion, assistant
  persistence, API readback, PostgreSQL transcript readback, G1, or a release
  claim.
- The dirty cloud-capable Tester project was untouched and excluded.
- No database was reset, no schema was manually repaired, and no Alembic stamp
  or direct migration SQL was used.
- No tracked runtime, configuration, Compose, migration, test, Campaign,
  current-state, ADR, or historical-proof file was modified.
- No cloud provider was enabled, no secret was recorded, no ordinary chat was
  submitted, no turn-lock work occurred, and no Coding Loop was run.

## ADR impact

Aligned with existing ADR(s): ADR-041 (VaultNode authority), ADR-042
(canonical evidence boundaries), ADR-052 (cloud-capable private-preview
exclusion), and ADR-069 (default local-only Beta runtime posture). No
architectural or release decision changed.

**Final result: `BLOCKED` — first blocking boundary: canonical live-proof collector LLM-health projection.**
