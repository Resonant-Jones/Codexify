# Whoosh'd Qwen MLX adapter activation proof

**Result:** `WHOOSHD_QWEN_MLX_VLM_ACTIVATION_PASS`

**ADR impact:** Aligned with ADR-074 and the existing Whoosh'd adapter
architecture; no ADR change.

## Scope and proof window

This proof activates the already-implemented Whoosh'd process selector through
the existing system launchd authority. It changes only the adapter environment
value in the root-owned plist, performs one teardown/quiescence/bootstrap
cycle, and verifies the fresh non-inference runtime. It does not change model
authority, the registry, the artifact, Guardian, Tester, storage, or provider
configuration.

```text
PROOF_WINDOW_START_UTC=2026-08-27T14:29:55Z
PROOF_WINDOW_END_UTC=2026-08-27T16:20:44Z
```

No inference endpoint was called. Historical POST records in the pre-existing
Whoosh'd log predate the fresh process; the fresh-process log slice contains
only startup and read-only GET probes.

## Required lineage and worktree gates

The preceding Codexify proof and the committed Whoosh'd selector were verified
before the launchd mutation:

```text
Codexify prerequisite: 17cd5d02b57bb2aaf4e5d80cbbc77d90d8165d65
Codexify prerequisite object: present
Codexify prerequisite ancestry: pass

Whoosh'd selector commit: 55f3e167f93857cb5e50e3236cfc133693179be3
Whoosh'd selector ancestry: pass
```

Codexify worktree:

```text
branch: codex/diagnose-tester-fresh-chroma-failure
HEAD before proof: 17cd5d02b57bb2aaf4e5d80cbbc77d90d8165d65
status: clean; unrelated guardian/workers/watchdog_review_worker.py untouched and unstaged
```

Whoosh'd source:

```text
root: /Volumes/Dev_SSD/ResonantConstructs/Whoosh'd
remote: https://github.com/Resonant-Jones/whooshd.git
branch: main
HEAD: 55f3e167f93857cb5e50e3236cfc133693179be3
status before/after: main...origin/main [ahead 2, behind 22], clean
```

The required architecture, ADR, operations, Tester-runtime, selector, and
preceding Guardian/Whoosh'd proof documents were read before the lifecycle
action. `docs/architecture/00-current-state.md` was not changed.

## Authoritative launchd source and pre-change process

The active process is owned by the existing system launchd plist:

| Field | Pre-change value |
| --- | --- |
| label | `system/com.resonant.whooshd` |
| plist | `/Library/LaunchDaemons/com.resonant.whooshd.plist` |
| owner/group/mode | `root:wheel -rw-r--r--` |
| plist SHA-256 | `3a82268a28b81ed35019e2abf9bc587a93e16985572aaa31c6a86f4f4b990c33` |
| syntax | `plutil -lint`: `OK` |
| state | running, active count 1, runs 1 |
| PID | `50696` |
| executable | `/Users/chriscastillo/.local/bin/whooshd` |
| arguments | `/Users/chriscastillo/.local/bin/whooshd --host 127.0.0.1 --port 8000` |
| working directory | `/Volumes/Dev_SSD/ResonantConstructs/Whoosh'd` |
| listener | `127.0.0.1:8000`, PID `50696` |
| stdout/stderr | `/tmp/whooshd.out`, `/tmp/whooshd.err` |

The plist's pre-change environment included the existing root, Python, registry,
VLM host/port/model, ports, logging, `KeepAlive`, `RunAtLoad`, and `UserName`
values. `WHOOSHD_ADAPTER` was absent, so the launcher defaulted it to `stub`.
The launcher source confirms the fresh source path and process command:

```text
WHOOSHD_ROOT=/Volumes/Dev_SSD/ResonantConstructs/Whoosh'd
WHOOSHD_PYTHON=/Volumes/Dev_SSD/ResonantConstructs/Whoosh'd/.venv311/bin/python
WHOOSHD_MODEL_REGISTRY_PATH=/Volumes/Dev_SSD/ResonantConstructs/Whoosh'd/configs/models.friends-family-guest.yaml
WHOOSHD_MLX_VLM_ENABLED=true
WHOOSHD_MLX_VLM_MODEL=/Volumes/Dev_SSD/whooshd/model-weights/Qwen3.8-27B-4bit
WHOOSHD_ADAPTER=absent before mutation

launcher: cd "$ROOT"
launcher: exec "$PYTHON_BIN" -m uvicorn whooshd.app:app --host "$HOST" --port "$PORT"
```

The pre-change public inventory was:

```text
GET /v1/models: HTTP 200; exactly one id=qwen3.8-27b-4bit
raw filesystem-path identity: absent
duplicate Qwen identity: absent
```

The registry remained the previously proven tracked blob
`dc70602d29c174560e012943f32b67b14b69d12a`, SHA-256
`93fabb026ec3314271f58f1cea69a05fa96bb1fae8de4d54c0fa40c517775817`, mapping
`qwen3.8-27b-4bit` to `mlx_vlm` / `mlx` and
`/Volumes/Dev_SSD/whooshd/model-weights/Qwen3.8-27B-4bit`.

## Exact configuration mutation

The human operator retained sudo authority and executed the plist edit
interactively. No password was requested, captured, stored, or placed in an
environment variable. The only effective semantic change was:

```text
WHOOSHD_ADAPTER: absent -> mlx_vlm
```

The operator later repeated the insert command after the key already existed;
`plutil` returned `Value already exists at key path EnvironmentVariables.WHOOSHD_ADAPTER`
and made no change. A JSON semantic comparison against the captured pre-change
plist proved:

```text
environment_changes=[("WHOOSHD_ADAPTER", None, "mlx_vlm")]
non_environment_changes=[]
```

Post-change plist validation and metadata:

```text
SHA-256: 4795c5662309ac09974163bd5a89a04976a358df3d0ff02e5e60a97cd0da1142
owner/group/mode: root:wheel -rw-r--r--
plutil -lint: OK
```

The executable, arguments, working directory, registry path, model path,
ports, logging paths, lifecycle flags, and all other environment values were
unchanged. No `launchctl setenv`, wrapper, shell profile, second plist, or
repository-local override was introduced.

## One launchd lifecycle cycle

The operator performed exactly one system-domain bootout:

```text
WHOOSHD_BOOTOUT_ATTEMPTS=1
result: success
```

After bootout, three bounded checks established teardown quiescence:

```text
WHOOSHD_LAUNCHD_STATE=fully_unloaded
service label: absent on all checks
old PID 50696: gone on all checks
127.0.0.1:8000 listener: absent on all checks
launchd transition/removal state: absent
quiescence window: 2026-08-27T16:16:18Z -> 2026-08-27T16:16:22Z
```

The operator then performed exactly one bootstrap of the same plist:

```text
WHOOSHD_BOOTSTRAP_ATTEMPTS=1
result: success
WHOOSHD_MLX_VLM_ACTIVATION_CYCLES=1
```

No retry, alternate plist, adapter change, sidecar restart, Tester restart,
backend restart, worker restart, Redis restart, or Postgres restart occurred.

## Fresh process and source lineage

Fresh launchd state:

| Field | Observed value |
| --- | --- |
| state | running, active count 1, runs 1 |
| fresh PID | `30366` |
| prior PID | `50696` (different) |
| executable | `/Users/chriscastillo/.local/bin/whooshd` |
| arguments | `/Users/chriscastillo/.local/bin/whooshd --host 127.0.0.1 --port 8000` |
| working directory | `/Volumes/Dev_SSD/ResonantConstructs/Whoosh'd` |
| listener | exactly one `127.0.0.1:8000` listener, PID `30366` |
| session start | `2026-08-27T16:17:40Z` |

`launchctl print` shows the fresh process environment contains
`WHOOSHD_ADAPTER=mlx_vlm`, the exact Whoosh'd root, the root `.venv311` Python,
and the canonical registry path. `lsof` shows PID `30366` with cwd at that root
and loaded modules from its `.venv311`. The active checkout is clean at the
selector commit `55f3e167…`; the launcher changes into that root before
executing `uvicorn whooshd.app:app`. This ties the fresh process to the
committed selector source rather than an unrelated installed build.

The fresh stdout startup line is:

```text
Starting Whoosh'd on http://127.0.0.1:8000 with adapter=mlx_vlm
```

Fresh stderr recorded `Started server process [30366]`, application startup
completion, and `Uvicorn running on http://127.0.0.1:8000`. No import,
dependency, architecture, registry, artifact, or fatal startup error was
present.

## Fresh adapter and fallback proof

The required fresh selector observation is:

```text
WHOOSHD_CURRENT_EXECUTION_ADAPTER=mlx_vlm
WHOOSHD_CURRENT_ADAPTER_CLASS=MlxVlmAdapter
STUB_FALLBACK=false
```

The first value is present in the fresh launchd environment and startup log.
The committed factory branch constructs the existing `MlxVlmAdapter`; a
source-level check using the exact fresh environment returned:

```text
resolved_class=MlxVlmAdapter
resolved_name=mlx-vlm
resolved_kind=mlx_vlm
resolved_model_id=/Volumes/Dev_SSD/whooshd/model-weights/Qwen3.8-27B-4bit
is_stub=False
```

The registry-aware route check for canonical `qwen3.8-27b-4bit` returned the
same `MlxVlmAdapter`, not Stub. The source intentionally keeps a Stub adapter
registered as an always-available fallback for unresolved IDs, so
`/health/runtime` lists a ready `stub` runtime and `/runtime/model` retains a
process-level `stub-model` snapshot. Those fields are not the Qwen route and
do not represent a `mlx_vlm -> stub` fallback. The canonical public inventory
contains no `stub-model`, and the exact Qwen route resolves to `mlx_vlm` before
fallback evaluation.

## Adapter initialization and Qwen identity

The existing external `mlx_vlm` sidecar remained running and healthy:

```text
PID: 850
listener: 127.0.0.1:8082
command: python -m mlx_vlm server --model /Volumes/Dev_SSD/whooshd/model-weights/Qwen3.8-27B-4bit --host 127.0.0.1 --port 8082
```

Its read-only health response reported:

```json
{
  "status": "healthy",
  "loaded_model": "/Volumes/Dev_SSD/whooshd/model-weights/Qwen3.8-27B-4bit",
  "loaded_context_size": 262144,
  "loaded_tool_parser": "qwen3_coder",
  "continuous_batching_enabled": true
}
```

The canonical public inventory after activation remained exactly:

```json
{
  "object": "list",
  "data": [
    {
      "id": "qwen3.8-27b-4bit",
      "metadata": {
        "engine": "mlx_vlm",
        "format": "mlx",
        "modalities": ["text", "vision"],
        "context_window": 65536
      }
    }
  ]
}
```

There is no raw filesystem-path Qwen identity, duplicate canonical identity,
or `stub-model` in `/v1/models`. The registry blob, artifact directory,
artifact metadata, and sidecar loaded-model path agree. No download, conversion,
rename, copy, re-quantization, replacement, or artifact hash change occurred.

## Execution and persistence boundaries

```text
MODEL_INVOCATIONS_DURING_MLX_VLM_ACTIVATION=0
QWEN_REAL_INFERENCE_STATUS=UNPROVEN
GUARDIAN_BACKEND_LIFECYCLE_ACTIONS_DURING_MLX_VLM_ACTIVATION=0
WORKER_CHAT_LIFECYCLE_ACTIONS_DURING_MLX_VLM_ACTIVATION=0
REDIS_LIFECYCLE_ACTIONS_DURING_MLX_VLM_ACTIVATION=0
POSTGRES_LIFECYCLE_ACTIONS_DURING_MLX_VLM_ACTIVATION=0
DEEPSEEK_REQUESTS_DURING_MLX_VLM_ACTIVATION=0
WATCHDOG_ACTIVITY_DURING_MLX_VLM_ACTIVATION=0
GITHUB_IO_DURING_MLX_VLM_ACTIVATION=0
COMMAND_BUS_ACTIVITY_DURING_MLX_VLM_ACTIVATION=0
BUILD_LOOP_ACTIVITY_DURING_MLX_VLM_ACTIVATION=0
POSTGRES_MUTATIONS_DURING_MLX_VLM_ACTIVATION=0
REDIS_MUTATIONS_DURING_MLX_VLM_ACTIVATION=0
CHROMA_MUTATIONS_DURING_MLX_VLM_ACTIVATION=0
MODEL_ARTIFACT_MUTATIONS_DURING_MLX_VLM_ACTIVATION=0
```

The fresh log slice after the `adapter=mlx_vlm` startup line contains only
read-only GET requests (`/v1/models`, `/health`, `/ready`,
`/health/runtime`, `/runtime/model`, and `/runtime`). No chat, completion,
generation, warmup-generation, Codexify completion, or Watchdog request was
issued. Guardian was not requalified in this task; its prior non-inference
Qwen qualification remains the governing receipt.

## Result and validation boundary

```text
WHOOSHD_QWEN_MLX_VLM_ACTIVATION_PASS
```

The activation proof chain is complete:

```text
selector commit present
-> authoritative launchd plist confirmed
-> only WHOOSHD_ADAPTER=mlx_vlm added
-> plist valid and semantically scoped
-> one bootout
-> fully unloaded
-> one bootstrap
-> fresh PID 30366
-> committed source/root lineage
-> WHOOSHD_CURRENT_EXECUTION_ADAPTER=mlx_vlm
-> MlxVlmAdapter / mlx_vlm
-> no canonical-Qwen Stub fallback
-> clean initialization
-> exact Qwen inventory
-> unchanged artifact
-> zero inference
```

The Codexify proof validation was:

```text
python3 scripts/validate_docs.py  # passed
git diff --check                  # passed
git diff --name-only              # proof artifact only
```

Only this proof artifact is attributable to the Codexify task. The unrelated
`guardian/workers/watchdog_review_worker.py` remained untouched and unstaged;
`docs/architecture/00-current-state.md` remained unchanged.

## Deferred next slice

The next task may execute exactly one authenticated ordinary Tester Qwen turn
through the canonical Codexify chat path:

```text
auth/session
-> one bounded proof thread
-> one persisted user message
-> exactly one completion request
-> Redis queue
-> existing worker-chat
-> provider local
-> qwen3.8-27b-4bit
-> active MlxVlmAdapter
-> one real Qwen generation
-> one persisted assistant message
-> API transcript and direct PostgreSQL readback
-> queue returns to 0
```

That proof must allow exactly one attempt and prohibit retry, replay, cloud
fallback, DeepSeek, Watchdog, and a second completion. Watchdog remains frozen
until the ordinary authenticated Qwen completion passes.
