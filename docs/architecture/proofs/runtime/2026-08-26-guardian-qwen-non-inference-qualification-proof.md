# Guardian Qwen non-inference health qualification proof

**Result:** GUARDIAN_QWEN_NON_INFERENCE_HEALTH_PASS

**ADR impact:** Aligned with ADR-074, the governing Tester dual-provider
startup profile, and the provider-capability evidence distinctions; no ADR
change.

## Scope and proof window

This was a bounded Guardian qualification against the live Tester Qwen
inventory. The proof window was:

~~~
PROOF_WINDOW_START_UTC=2026-08-26T16:38:12Z
PROOF_WINDOW_END_UTC=2026-08-26T16:41:56Z
~~~

Only read-only identity, inventory, health, queue, and persistence checks were
performed. No runtime/configuration source was repaired in this task.

## Prerequisite and worktree gate

The required prerequisite c81a50eaa246a82150bdc790b3f5068f5215fe21 was present
and an ancestor of HEAD before probing:

~~~
git cat-file -e c81a50eaa246a82150bdc790b3f5068f5215fe21^{commit}  # passed
git merge-base --is-ancestor c81a50eaa246a82150bdc790b3f5068f5215fe21 HEAD  # passed
~~~

Codexify task worktree at entry:

~~~
branch: codex/diagnose-tester-fresh-chroma-failure
HEAD: c81a50eaa246a82150bdc790b3f5068f5215fe21
status: ahead 1 of origin/codex/diagnose-tester-fresh-chroma-failure; no task-worktree dirty files
~~~

The unrelated guardian/workers/watchdog_review_worker.py was not modified,
staged, restored, or reformatted. 00-current-state.md was not changed.

## Tester lifecycle boundary

The active codexify_tester-backend-1 was already reachable and healthy, so the
conditional lifecycle action was not authorized or needed:

~~~
TESTER_BACKEND_START_ACTIONS=0
GUARDIAN_BACKEND_RESTARTS_DURING_QUALIFICATION=0
WORKER_CHAT_RESTARTS_DURING_QUALIFICATION=0
MIGRATOR_RUNS_DURING_QUALIFICATION=0
SEED_RUNS_DURING_QUALIFICATION=0
MODEL_PREP_RUNS_DURING_QUALIFICATION=0
GRAPH_INIT_RUNS_DURING_QUALIFICATION=0
DEPENDENCY_AWARE_COMPOSE_STARTS_DURING_QUALIFICATION=0
~~~

Observed backend identity:

~~~
container: codexify_tester-backend-1
container_id: 475bb0079346fe3e7454f2056fa1d451b73fb742472a5bbf4bdc1b91acffa8e5
state: running
health: healthy
restart_count: 0
started_at: 2026-08-26T15:34:56.359647755Z
image_digest: sha256:2508fe43e87e883caea01fe36b5ab5eff3a1d9616d395d7e7903b03204a584cf
listener: 127.0.0.1:8889
GET /health: HTTP 200, status=ok
~~~

The container mounts the active source /Volumes/Dev_SSD/Codexify-main into the
running Guardian/backend paths. The active source is independently identified
as:

~~~
remote: https://github.com/Resonant-Jones/Codexify.git
branch: main
HEAD: 6b383badb1eb5c5301df0c92c88215e605bf9fff
status: behind 40 of origin/main, with pre-existing changes in
        docs/architecture/00-current-state.md and frontend connector files
~~~

Those pre-existing active-source changes were preserved and not included in
this proof.

## Active Tester provider posture

The following non-secret values were read from the actual running backend
container; no .env.tester or provider configuration was edited:

| Setting | Value |
| --- | --- |
| LLM_PROVIDER | local |
| LOCAL_CHAT_MODEL | qwen3.8-27b-4bit |
| LOCAL_PROVIDER_VENDOR | whooshd |
| LOCAL_BASE_URL | http://host.docker.internal:8000/v1 |
| ALLOW_CLOUD_PROVIDERS | true |
| CODEXIFY_LOCAL_ONLY_MODE | false |
| CODEXIFY_EGRESS_ALLOWLIST | deepseek |
| supported profile | v1-whooshd-deepseek-web, valid, selected provider local |
| release hold | true |

## Whoosh'd runtime and inventory

The live launchd service and its source are coherent:

~~~
plist: /Library/LaunchDaemons/com.resonant.whooshd.plist
label: system/com.resonant.whooshd
state: running, active count=1
pid: 50696
working_directory: /Volumes/Dev_SSD/ResonantConstructs/Whoosh'd
registry: /Volumes/Dev_SSD/ResonantConstructs/Whoosh'd/configs/models.friends-family-guest.yaml
listener: 127.0.0.1:8000
repository: https://github.com/Resonant-Jones/whooshd.git
branch: main
HEAD: 09e83a8359e3673e7c18a2e0b4733afd334b3bac
registry_blob: dc70602d29c174560e012943f32b67b14b69d12a
~~~

The registry worktree was clean for this file and its tracked blob matched the
current source. The installed artifact path exists and is the same path
identified by the prior Whoosh'd registry proof:

~~~
/Volumes/Dev_SSD/whooshd/model-weights/Qwen3.8-27B-4bit
~~~

The registry entry is explicitly:

~~~
qwen3.8-27b-4bit:
  engine: mlx_vlm
  format: mlx
  path: /Volumes/Dev_SSD/whooshd/model-weights/Qwen3.8-27B-4bit
  modalities: [text, vision]
  enabled: true
~~~

Read-only runtime checks returned:

~~~
GET /health: HTTP 200, status=ready
GET /ready: ready=true (readiness metadata adapter=multi-runtime)
GET /v1/models: HTTP 200, ids=[qwen3.8-27b-4bit], count=1
GET /api/tags: HTTP 200, name=qwen3.8-27b-4bit, format=mlx, family=mlx_vlm
~~~

The startup log continues to classify the execution seam as:

~~~
WHOOSHD_EXECUTION_ADAPTER=stub
~~~

The readiness label is not treated as generation evidence. There is no second
raw filesystem-path Qwen identity, no duplicate canonical ID, and no
conflicting inventory entry. The pre-qualification and final advertised ID
were both exactly qwen3.8-27b-4bit.

Whoosh'd was not restarted:

~~~
WHOOSHD_RESTARTS_DURING_QUALIFICATION=0
~~~

## Guardian route qualification

The active guardian/routes/health.py and provider modules were inspected before
interpreting responses. The routes use health/readiness and model inventory
probes; they do not submit a completion. health/chat performs a Redis ping and
an ephemeral healthcheck queue round-trip, then removes the probe key.

### General health

~~~
GET /health: HTTP 200
status=ok
supported_profile.name=v1-whooshd-deepseek-web
supported_profile.valid=true
supported_profile.mismatches=[]
selected_provider=local
release_hold=true
~~~

### LLM health

~~~
GET /api/health/llm: HTTP 200
surface status=ok
details.status=online
provider=local
model=qwen3.8-27b-4bit
models_available=true
configured_model=qwen3.8-27b-4bit
configured_model_available=true
model_resolution.strict=true
model_resolution.source=LOCAL_CHAT_MODEL
model_resolution.endpoint_resolution.state=available
model_resolution.inventory_source=whooshd:/v1/models
provider_runtime.id=local
provider_runtime.authorized=true
provider_runtime.available=true
provider_runtime.enabled=true
provider_runtime.model_index.state=available
provider_runtime.model_index.model_count=1
completion_service.ok=true
completion_service.redis_reachable=true
completion_service.enqueue_test_ok=true
completion_service.worker_heartbeat_status=fresh
provider_truth.attempted=false
provider_truth.executed=false
provider_truth.completed=false
release_hold=true
~~~

There was no configured_model_not_advertised_by_whooshd failure.

### Catalog

Both catalog surfaces were queried:

~~~
GET /api/llm/catalog: HTTP 200
GET /api/llm/catalog?include=all: HTTP 200
~~~

The local provider was identical in both responses:

~~~
provider.id=local
provider.enabled=true
provider.authorized=true
provider.available=true
provider.default_model=qwen3.8-27b-4bit
provider.configured_model=qwen3.8-27b-4bit
provider.configured_model_available=true
provider.model_index.source=local
provider.model_index.state=available
provider.model_index.model_count=1
provider.models=[qwen3.8-27b-4bit]
provider.models[0].source=host.docker.internal:8000
~~~

The include-all response did not alter local selection or invoke any cloud
provider. No alias or normalization was added by this task.

### Chat infrastructure

~~~
GET /health/chat: HTTP 200
ok=true
status=healthy
provider=local
model=qwen3.8-27b-4bit
configured_model_available=true
redis=ok
worker.status=fresh
worker.reason=ok
queue.depth=0
queue.status=progressing
completion_service.ok=true
completion_service.redis_reachable=true
completion_service.enqueue_test_ok=true
completion_service.worker_heartbeat_status=fresh
provider_truth.attempted=false
provider_truth.executed=false
provider_truth.completed=false
~~~

No backend recreation or inventory-refresh action was required:

~~~
GUARDIAN_BACKEND_INVENTORY_REFRESH_ACTIONS=0
~~~

## Capability evidence boundary

guardian/core/provider_truth.py defines provider_truth.executable as the
runtime-enabled flag (bool(runtime.enabled)). It separately exposes attempted,
executed, and completed, all of which were false in the live LLM-health,
catalog, and chat-health responses. ADR-062 distinguishes catalog-proven and
health-proven capability from runtime-proven generation.

Accordingly, this proof records:

~~~
QWEN_REAL_INFERENCE_STATUS=UNPROVEN
~~~

The online, available, healthy, and runtime-enabled fields above are inventory,
transport, authorization, policy, and queue evidence only. They are not a
successful-generation receipt, so GUARDIAN_HEALTH_CAPABILITY_OVERCLAIM does not
apply.

## Queue, worker, persistence, and execution boundaries

Direct Redis and database readbacks were taken at the end of the same bounded
window:

~~~
chat queue depth: 0 at start -> 0 at end
worker heartbeat TTL: positive (44 seconds at final read)
worker heartbeat payload: status=idle, queue=codexify:queue:chat
worker service: running, restart_count=0
db service: running, healthy, restart_count=0
~~~

Rows created at or after the proof-window start were zero:

~~~
chat_threads=0
chat_messages=0
messages=0
github_watchdog_delivery_receipts=0
github_watchdog_review_attempts=0
github_watchdog_review_input_snapshots=0
github_watchdog_review_dispatches=0
github_watchdog_review_results=0
~~~

The health route's unique Redis healthcheck key was round-tripped and deleted by
the existing health implementation. No durable chat queue item or manual
Postgres, Redis, or Chroma mutation was performed.

~~~
MODEL_INVOCATIONS_DURING_GUARDIAN_QUALIFICATION=0
DEEPSEEK_REQUESTS_DURING_GUARDIAN_QUALIFICATION=0
WATCHDOG_ACTIVITY_DURING_GUARDIAN_QUALIFICATION=0
CHAT_TASKS_CREATED_DURING_GUARDIAN_QUALIFICATION=0
GITHUB_IO_DURING_GUARDIAN_QUALIFICATION=0
COMMAND_BUS_ACTIONS_DURING_GUARDIAN_QUALIFICATION=0
BUILD_LOOP_ACTIONS_DURING_GUARDIAN_QUALIFICATION=0
~~~

Whoosh'd access logs during the bounded checks contained inventory/tag/health
requests and no POST /v1/chat/completions or POST /v1/completions entry.

## Validation record

The following read-only or documentation checks were run:

~~~
git cat-file -e c81a50eaa246a82150bdc790b3f5068f5215fe21^{commit}
git merge-base --is-ancestor c81a50eaa246a82150bdc790b3f5068f5215fe21 HEAD
git status --short --branch
git rev-parse HEAD
git -C /Volumes/Dev_SSD/Codexify-main status --short --branch
git -C /Volumes/Dev_SSD/Codexify-main rev-parse HEAD
git -C "/Volumes/Dev_SSD/ResonantConstructs/Whoosh'd" status --short --branch
launchctl print system/com.resonant.whooshd
lsof -nP -iTCP:8000 -sTCP:LISTEN
curl GET /health, /health/llm, /api/health/llm, /api/llm/catalog,
     /api/llm/catalog?include=all, /health/chat, /v1/models, /api/tags, /ready
python3 scripts/validate_docs.py
git diff --check
~~~

No migration, seed, model-preparation, graph-initialization, service restart,
completion, or fallback command was run.

## Final classification

~~~
GUARDIAN_QWEN_NON_INFERENCE_HEALTH_PASS
~~~

This is a non-inference health/catalog qualification only. It does not prove
that Qwen can generate text, does not qualify the stub Whoosh'd execution
adapter, and does not widen current release truth.

## Deferred next slice

Classify and, if separately authorized, restore the Whoosh'd execution adapter
to a non-stub seam without performing a completion. Only after that bounded
adapter proof should the existing proof-only authenticated Tester session be
used for one ordinary authenticated Qwen completion. Watchdog remains frozen
until that completion passes.
