# Whoosh'd Qwen execution-adapter diagnosis proof

**Result:** `WHOOSHD_QWEN_EXECUTION_ADAPTER_CAUSE_IDENTIFIED`

**ADR impact:** Aligned with ADR-074, the governing Tester dual-provider
runtime contract, and the existing Whoosh'd registry/runtime contracts; no ADR
change.

## Scope and proof window

This was a read-only diagnosis of the active Whoosh'd execution-adapter
posture. It did not change Whoosh'd source, configuration, launchd state,
registry contents, model artifacts, Tester, Guardian, storage, or any provider
authority. No inference endpoint was called.

```text
PROOF_WINDOW_START_UTC=2026-08-26T17:47:21Z
PROOF_WINDOW_END_UTC=2026-08-26T17:59:51Z
```

The diagnosis distinguishes the process-level adapter selector from the
registry-aware per-model route. That distinction is material: the process
banner and global readiness snapshot report the deterministic `stub` default,
while an exact request for the canonical Qwen registry entry resolves to the
already-running `mlx_vlm` adapter.

## Required lineage and Codexify worktree gate

The required prerequisite was verified before runtime inspection:

```text
git cat-file -e 88411b782b88c63fd32edabcf0a567faa4dc2bd9^{commit}  # passed
git merge-base --is-ancestor 88411b782b88c63fd32edabcf0a567faa4dc2bd9 HEAD  # passed
```

Codexify task worktree:

```text
branch: codex/diagnose-tester-fresh-chroma-failure
HEAD: 88411b782b88c63fd32edabcf0a567faa4dc2bd9
status: clean at diagnosis entry; ahead 2 of origin/codex/diagnose-tester-fresh-chroma-failure
```

The required architecture, ADR, operations, Tester-runtime, registry, and
prior Guardian/Whoosh'd proof documents were read before interpreting live
responses. `guardian/workers/watchdog_review_worker.py` was checked and left
untouched, unstaged, and unreformatted. `docs/architecture/00-current-state.md`
was not changed.

## Active Whoosh'd source and process identity

The active launchd service is tied to the identified Whoosh'd checkout:

| Field | Observed value |
| --- | --- |
| launchd label | `system/com.resonant.whooshd` |
| plist | `/Library/LaunchDaemons/com.resonant.whooshd.plist` |
| plist SHA-256 | `3a82268a28b81ed35019e2abf9bc587a93e16985572aaa31c6a86f4f4b990c33` |
| state | running, active count 1, runs 1 |
| PID | `50696` |
| executable | `/Users/chriscastillo/.local/bin/whooshd` |
| complete arguments | `/Users/chriscastillo/.local/bin/whooshd --host 127.0.0.1 --port 8000` |
| working directory | `/Volumes/Dev_SSD/ResonantConstructs/Whoosh'd` |
| listener | `127.0.0.1:8000`, PID `50696` |
| repository remote | `https://github.com/Resonant-Jones/whooshd.git` |
| branch / HEAD | `main` / `09e83a8359e3673e7c18a2e0b4733afd334b3bac` |
| repository status | `main...origin/main [ahead 1, behind 22]`, no dirty files |
| launcher SHA-256 | `2ad7b8f59038aa644fa694deec3a8b2151f7734ed956e38bfa16c3fc6149d62d` |

The active plist supplies these non-secret runtime values:

```text
WHOOSHD_ROOT=/Volumes/Dev_SSD/ResonantConstructs/Whoosh'd
WHOOSHD_PYTHON=/Volumes/Dev_SSD/ResonantConstructs/Whoosh'd/.venv311/bin/python
WHOOSHD_MODEL_REGISTRY_PATH=/Volumes/Dev_SSD/ResonantConstructs/Whoosh'd/configs/models.friends-family-guest.yaml
WHOOSHD_MLX_ENABLED=true
WHOOSHD_MLX_VLM_ENABLED=true
WHOOSHD_MLX_VLM_HOST=127.0.0.1
WHOOSHD_MLX_VLM_PORT=8082
WHOOSHD_MLX_VLM_MODEL=/Volumes/Dev_SSD/whooshd/model-weights/Qwen3.8-27B-4bit
WHOOSHD_HOST=127.0.0.1
WHOOSHD_PORT=8000
WHOOSHD_ADAPTER is absent from the plist
```

The process working directory, repository identity, plist target, and loaded
Python modules all agree. No `WHOOSHD_ACTIVE_SOURCE_IDENTITY_UNRESOLVED`
condition was present.

## Canonical registry and public inventory

The active registry is the repository-owned file restored by the preceding
registry proof and committed in Whoosh'd as
`09e83a8359e3673e7c18a2e0b4733afd334b3bac` (`Restore friends family Qwen
registry`). Its current tracked blob is
`dc70602d29c174560e012943f32b67b14b69d12a`, and its SHA-256 is
`93fabb026ec3314271f58f1cea69a05fa96bb1fae8de4d54c0fa40c517775817`.

The exact entry is:

```yaml
qwen3.8-27b-4bit:
  display_name: "Qwen3.8 27B 4-bit MLX"
  engine: mlx_vlm
  format: mlx
  path: "/Volumes/Dev_SSD/whooshd/model-weights/Qwen3.8-27B-4bit"
  modalities: [text, vision]
  context_window: 65536
  preferred_hardware: [apple_silicon, metal]
  warm_policy: keep_warm
  priority: guest_chat
  enabled: true
```

Read-only public inventory and health responses were:

```text
GET /v1/models: HTTP 200; exactly one id: qwen3.8-27b-4bit
GET /api/tags: HTTP 200; exactly one name/model: qwen3.8-27b-4bit; format=mlx; family=mlx_vlm
GET /health: HTTP 200; ok=true; status=ready; queue_depth=0; active_jobs=0
GET /ready: HTTP 200; ready=true; adapter=multi-runtime; configured_model=stub-model
GET /runtime: loaded_models=[]; lifecycle=ready; queue_capacity=32; active_jobs=0
GET /runtime/requests: requests=[]; active_count=0
GET /runtime/admission: active_jobs=0; queue_depth=0; counters all zero
```

The bounded pre- and post-diagnosis inventory reads were identical. The public
Whoosh'd surface contains no raw Qwen filesystem-path identity and no second
canonical entry. The upstream sidecar's internal `/v1/models` response does
include its configured raw path (and an unrelated Llama id); that is an
internal upstream identity, not a conflicting public Whoosh'd identity. The
registry contract intentionally maps that upstream artifact to the single
public canonical ID.

## Process-level selector and Stub semantics

The current process-level observation is:

```text
WHOOSHD_CURRENT_EXECUTION_ADAPTER=stub
```

This value is source-backed, not inferred from readiness. The launcher uses
`WHOOSHD_ADAPTER="${WHOOSHD_ADAPTER:-stub}"`; the active plist does not set the
variable; `whooshd/config.py` therefore returns `stub` from
`get_adapter_backend()`, and `whooshd/adapters/factory.py` selects the
deterministic `StubInferenceAdapter`. Under that process selector,
`get_advertised_model_id()` returns `stub-model`, which explains the
`configured_model=stub-model` metadata on `/ready` and the process-level
`/runtime/model` snapshot.

The source of `whooshd/adapters/stub.py` establishes that this is not a real
model wrapper:

- `generate()` returns synthetic text of the form `[stub response #N] echo: …`;
- `chat_completion()` returns the fixed synthetic chat-contract response;
- streaming yields deterministic stub tokens;
- `set_external_model_path()` explicitly ignores paths;
- `is_loaded()` and `health()` are always ready for `stub-model`;
- `warmup()` and `unload()` are no-ops; and
- `list_models()` reports only the synthetic stub model.

Therefore the evidence does **not** support `WHOOSHD_STUB_IS_REAL_EXECUTION_WRAPPER`.
It proves a deterministic process-level fallback/default only.

## Adapter abstraction, registry, and selection precedence

`whooshd/adapters/base.py` defines the `InferenceAdapter` protocol: generation,
chat completion (including streaming), load state, model identity, warmup,
unload, health, and model listing. `whooshd/contracts.py` defines the runtime
kinds `stub`, `mlx_lm`, `mlx_lm_server`, `mlx_vlm`, and `llama_cpp`.

The factory's supported process-level selector tokens are:

| Token | Implementation | Current registration/role |
| --- | --- | --- |
| `stub` | `StubInferenceAdapter` | always registered; default |
| `mlx` | legacy in-process `MLXInferenceAdapter` (`mlx_lm`) | registered only when `WHOOSHD_ADAPTER=mlx` |
| `llama_cpp` | `LlamaCppAdapter` | always registered, but disabled without server config |

The application additionally registers `MlxLmServerAdapter` when
`WHOOSHD_MLX_ENABLED=true` and `MlxVlmAdapter` when
`WHOOSHD_MLX_VLM_ENABLED=true`. Those are runtime-kind registrations, not
additional accepted values for the process-level factory selector.

`whooshd/routing.py` resolves a model in this order:

1. registry entry engine to runtime-kind mapping;
2. explicit external routes;
3. `.gguf` heuristic;
4. exact loaded-adapter identity;
5. stub preference for unresolved IDs when the process selector is `stub`;
6. one non-stub fallback;
7. stub-only fallback; then
8. an error if no adapter can serve the request.

The registry entry has `engine: mlx_vlm`. Under the exact non-secret launchd
environment, a source-level router check returned:

```json
{
  "backend_selector": "stub",
  "advertised_model_id": "stub-model",
  "registered_kinds": ["stub", "mlx_lm_server", "mlx_vlm", "llama_cpp"],
  "resolved_kind": "mlx_vlm",
  "resolved_name": "mlx-vlm",
  "resolved_model_id": "/Volumes/Dev_SSD/whooshd/model-weights/Qwen3.8-27B-4bit"
}
```

This is the critical route result: an exact canonical Qwen request consults the
registry first and resolves to `mlx_vlm`; it does not fall through to Stub.

## Real adapter inventory and compatibility

### `mlx_vlm` — compatible and live

`whooshd/adapters/mlx_vlm.py` implements `MlxVlmAdapter`, which proxies the
OpenAI-compatible `/v1` surface to an `mlx_vlm` server. It reports the
configured artifact path internally, probes `/v1/models` for health, and
supports text/vision streaming and non-streaming chat. The active sidecar is:

```text
launchd label: system/com.resonant.mlx-vlm-gemma12b
plist: /Library/LaunchDaemons/com.resonant.mlx-vlm-gemma12b.plist
PID: 850
program: /Volumes/Dev_SSD/ResonantConstructs/Whoosh'd/.venv311/bin/python
arguments: -m mlx_vlm server --model /Volumes/Dev_SSD/whooshd/model-weights/Qwen3.8-27B-4bit --host 127.0.0.1 --port 8082
working directory: /Volumes/Dev_SSD/ResonantConstructs/Whoosh'd
listener: 127.0.0.1:8082
```

Its read-only health response was:

```json
{
  "status": "healthy",
  "loaded_model": "/Volumes/Dev_SSD/whooshd/model-weights/Qwen3.8-27B-4bit",
  "loaded_adapter": null,
  "loaded_context_size": 262144,
  "loaded_tool_parser": "qwen3_coder",
  "continuous_batching_enabled": true
}
```

The sidecar stderr recorded model pre-loading and `Model ready`; `lsof` showed
the active `.venv311` MLX native library, Metal library, and AGX resources.
This proves the live host sidecar is the existing MLX runtime, while the
Whoosh'd adapter's `active_model=null` field is expected for an externally
launchd-managed process rather than an adapter-managed subprocess.

### Other registered or available adapters

| Adapter | Evidence | Qwen compatibility |
| --- | --- | --- |
| `mlx_lm_server` | Source manages/probes `python -m mlx_lm server`; live health was offline, port 8081 had no listener, and source retains an intentional not-implemented inference marker | text-only lane; not the Qwen vision route |
| legacy `mlx_lm` | In-process `MLXInferenceAdapter`; lazy `mlx_lm.load()` and `mlx_lm.generate()`; only registered for `WHOOSHD_ADAPTER=mlx` | text-only and not the canonical multimodal `mlx_vlm` route |
| `llama_cpp` | GGUF-focused external/managed server; no configured URL, auto-start false, disabled; `llama-server` absent | incompatible with the installed MLX safetensors artifact |
| `stub` | deterministic synthetic adapter described above | never loads or executes Qwen |

The checkout has tests covering factory defaults/fallbacks, registry engine and
vision validation, multi-runtime routing, `MlxVlmAdapter` identity/inventory/
health, MLX-LM server identity/health, and llama.cpp configuration/process
validation. The checked-out `mlx`, `mlx_lm`, and `mlx_vlm` packages are present;
direct imports from the Codex sandbox fail only because that sandbox has no
Metal device. The live sidecar on the host has native MLX/Metal loaded, so this
diagnostic limitation is not evidence of an incompatible host.

## Qwen artifact and compatibility proof

The selected artifact is unchanged and exists at:

```text
/Volumes/Dev_SSD/whooshd/model-weights/Qwen3.8-27B-4bit
```

Bounded metadata identifies `Qwen3_5ForConditionalGeneration`, model type
`qwen3_5`, 4-bit affine/group-size-64 quantization, vision and text configs,
and MLX safetensors shards (`model.safetensors.index.json` plus three shard
files). It is therefore an MLX safetensors multimodal artifact whose required
runtime family is `mlx_vlm`, not text-only `mlx_lm` or GGUF `llama_cpp`.

The registry's exact `mlx_vlm`/`mlx`/path mapping, the sidecar's loaded-model
path, and the public canonical inventory all agree. No artifact rename, move,
download, replacement, or hash-changing operation occurred.

## First causal classification and deferred seam

The first causal classification is:

```text
WHOOSHD_STUB_DEFAULT_SELECTED
```

It is a diagnostic classification, not a claim that Qwen routing is stubbed.
The cause is the absent process-level `WHOOSHD_ADAPTER` setting combined with
the launcher's and factory's documented `stub` default. That default controls
the startup banner, global lifecycle shortcut, and process-level advertised
model metadata.

The exact canonical Qwen route is already source-proven to select the installed
and healthy `mlx_vlm` adapter. No adapter, model authority, registry, plist,
or runtime mutation is required to establish that route. The minimum deferred
seam for eliminating the misleading process-level `stub` label is the
`WHOOSHD_ADAPTER` launcher/plist/configuration contract. Current factory
support does not define `mlx_vlm` as a process-level token; setting
`WHOOSHD_ADAPTER=mlx` would select the incompatible text-only legacy MLX lane,
and inventing a new token is prohibited. Any global-label realignment therefore
requires a separate Whoosh'd execution-adapter architecture/observability
decision. It was not performed or guessed here.

## Authority and execution invariants

The following remained unchanged and are proven by the prior Tester/Guardian
runtime receipts plus the read-only checks in this window:

```text
Tester provider authority: local
Tester configured model: qwen3.8-27b-4bit
Guardian matching policy: exact canonical ID; unchanged
Whoosh'd registry/artifact mapping: unchanged
QWEN_REAL_INFERENCE_STATUS=UNPROVEN
MODEL_INVOCATIONS_DURING_ADAPTER_DIAGNOSIS=0
WHOOSHD_RESTARTS_DURING_ADAPTER_DIAGNOSIS=0
WHOOSHD_SIDECAR_RESTARTS_DURING_ADAPTER_DIAGNOSIS=0
GUARDIAN_BACKEND_RESTARTS_DURING_ADAPTER_DIAGNOSIS=0
WORKER_CHAT_RESTARTS_DURING_ADAPTER_DIAGNOSIS=0
POSTGRES_LIFECYCLE_ACTIONS_DURING_ADAPTER_DIAGNOSIS=0
REDIS_LIFECYCLE_ACTIONS_DURING_ADAPTER_DIAGNOSIS=0
DEEPSEEK_REQUESTS_DURING_ADAPTER_DIAGNOSIS=0
WATCHDOG_ACTIVITY_DURING_ADAPTER_DIAGNOSIS=0
GITHUB_IO_DURING_ADAPTER_DIAGNOSIS=0
COMMAND_BUS_ACTIVITY_DURING_ADAPTER_DIAGNOSIS=0
BUILD_LOOP_ACTIVITY_DURING_ADAPTER_DIAGNOSIS=0
POSTGRES_MUTATIONS_DURING_ADAPTER_DIAGNOSIS=0
REDIS_MUTATIONS_DURING_ADAPTER_DIAGNOSIS=0
CHROMA_MUTATIONS_DURING_ADAPTER_DIAGNOSIS=0
MODEL_ARTIFACT_MUTATIONS_DURING_ADAPTER_DIAGNOSIS=0
```

No chat task, proof-only session, user message, assistant message, completion,
warmup request, or inference endpoint was created or called. No Whoosh'd,
sidecar, Tester, backend, worker, Redis, Postgres, or Chroma lifecycle action
was performed.

## Validation and repository boundary

Only this Codexify proof file is attributable to the diagnosis. No Whoosh'd
working-tree change was made in this task; the prior Whoosh'd registry commit
remains the narrow repository-owned restoration. No launchd plist or registry
file was edited here.

The following checks are required for this proof artifact:

```text
python3 scripts/validate_docs.py
git diff --check
git diff --name-only
git status --short --branch
```

The final Codexify commit must stage only this path:

```text
docs/architecture/proofs/runtime/2026-08-26-whooshd-qwen-execution-adapter-diagnosis-proof.md
```

## Deferred next slice

Because an installed, compatible, live `mlx_vlm` route is proven, the next
bounded task may inspect or change only the proven Whoosh'd adapter-selection
seam, if a separate architecture decision authorizes global status alignment.
It may perform at most one required Whoosh'd lifecycle restart and must prove a
real adapter plus exact Qwen inventory without inference. The subsequent task
is the existing proof-only authenticated Tester session for exactly one ordinary
default-provider completion through local `qwen3.8-27b-4bit`, with durable API
and PostgreSQL readback, no retry, no fallback, no DeepSeek execution, and no
Watchdog activity. Watchdog remains frozen until that authenticated Qwen
completion passes.
