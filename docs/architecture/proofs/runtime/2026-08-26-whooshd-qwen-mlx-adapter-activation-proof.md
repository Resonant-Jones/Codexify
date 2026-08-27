# Whoosh'd Qwen MLX adapter activation proof

**Result:** `BLOCKED: WHOOSHD_MLX_ADAPTER_FALLBACK_TO_STUB`

**ADR impact:** Aligned with ADR-074 and the existing Tester provider/runtime
authority; no ADR change.

## Scope and proof window

This task was stopped before host mutation. The authoritative launchd plist was
inspected, but it was not edited, unloaded, bootstrapped, or otherwise
reloaded. The blocker was established from the active Whoosh'd source before
attempting the requested configuration change.

```text
PROOF_WINDOW_START_UTC=2026-08-27T01:29:20Z
PROOF_WINDOW_END_UTC=2026-08-27T01:29:21Z
```

The task permits only `WHOOSHD_ADAPTER=mlx_vlm` in the existing system launchd
configuration and prohibits Whoosh'd source changes. The active source does
not support `mlx_vlm` as a process-level factory selector; its unknown-value
branch returns the Stub adapter. Writing the requested value would therefore
violate the no-fallback acceptance criterion, so the task fails closed without
a lifecycle attempt.

## Required lineage and Codexify worktree gate

The required diagnosis proof commit was present and ancestral before source or
runtime inspection:

```text
git cat-file -e 5b6fa7fb970f7fc0c871d78542a12777db4ad6b3^{commit}  # passed
git merge-base --is-ancestor 5b6fa7fb970f7fc0c871d78542a12777db4ad6b3 HEAD  # passed
```

Codexify task worktree at entry:

```text
branch: codex/diagnose-tester-fresh-chroma-failure
HEAD: 5b6fa7fb970f7fc0c871d78542a12777db4ad6b3
status: clean; ahead 3 of origin/codex/diagnose-tester-fresh-chroma-failure
```

`guardian/workers/watchdog_review_worker.py` was checked and remained
untouched, unstaged, and unreformatted. `docs/architecture/00-current-state.md`
was not changed. The required architecture, ADR, operations, Tester-runtime,
and preceding Whoosh'd/Guardian proof documents were read before this gate.

## Pre-change authoritative runtime baseline

The active Whoosh'd process is owned by the system launchd plist, not a shell
override or repository-local environment file:

| Field | Observed value |
| --- | --- |
| launchd label | `system/com.resonant.whooshd` |
| plist | `/Library/LaunchDaemons/com.resonant.whooshd.plist` |
| plist owner/group/mode | `root:wheel -rw-r--r--` |
| plist SHA-256 | `3a82268a28b81ed35019e2abf9bc587a93e16985572aaa31c6a86f4f4b990c33` |
| plist syntax | `plutil -lint`: `OK` |
| state | running, active count 1, runs 1 |
| PID | `50696` |
| executable | `/Users/chriscastillo/.local/bin/whooshd` |
| arguments | `/Users/chriscastillo/.local/bin/whooshd --host 127.0.0.1 --port 8000` |
| working directory | `/Volumes/Dev_SSD/ResonantConstructs/Whoosh'd` |
| listener | `127.0.0.1:8000`, PID `50696` |
| repository remote | `https://github.com/Resonant-Jones/whooshd.git` |
| repository branch / HEAD | `main` / `09e83a8359e3673e7c18a2e0b4733afd334b3bac` |
| repository status | `main...origin/main [ahead 1, behind 22]`, clean |

The existing plist semantics were captured before any possible edit:

```text
Label=com.resonant.whooshd
ProgramArguments=/Users/chriscastillo/.local/bin/whooshd --host 127.0.0.1 --port 8000
WorkingDirectory=/Volumes/Dev_SSD/ResonantConstructs/Whoosh'd
StandardOutPath=/tmp/whooshd.out
StandardErrorPath=/tmp/whooshd.err
KeepAlive=true
RunAtLoad=true
UserName=chriscastillo
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
WHOOSHD_ADAPTER=absent (launcher default is stub)
```

The active process log independently reports:

```text
Starting Whoosh'd on http://127.0.0.1:8000 with adapter=stub
WHOOSHD_CURRENT_EXECUTION_ADAPTER=stub
```

The active registry is unchanged from the prior restoration proof. Its tracked
blob is `dc70602d29c174560e012943f32b67b14b69d12a` and its SHA-256 is
`93fabb026ec3314271f58f1cea69a05fa96bb1fae8de4d54c0fa40c517775817`. The
canonical mapping remains:

```text
qwen3.8-27b-4bit
  engine=mlx_vlm
  format=mlx
  path=/Volumes/Dev_SSD/whooshd/model-weights/Qwen3.8-27B-4bit
  modalities=text,vision
  enabled=true
```

The pre-change public inventory was read-only and exact:

```text
GET /v1/models: HTTP 200; exactly one id=qwen3.8-27b-4bit
raw filesystem-path Qwen identity: absent
duplicate canonical Qwen identity: absent
```

No `WHOOSHD_ADAPTER_AUTHORITY_DRIFT` condition exists: the process, launchd
plist, working directory, registry path, and Whoosh'd checkout agree.

## Source proof of the requested-selector fallback

The active Whoosh'd source at `09e83a8359e3673e7c18a2e0b4733afd334b3bac` is
decisive:

- `whooshd/config.py:get_adapter_backend()` returns the environment value,
  defaulting to `stub`.
- `whooshd/adapters/factory.py` documents and handles only `stub`, `mlx`, and
  `llama_cpp` as process-level factory selectors.
- Its final branch is `# Default / unknown -> stub`, returning
  `StubInferenceAdapter`.
- `whooshd/app.py` registers `MlxVlmAdapter` separately when
  `WHOOSHD_MLX_VLM_ENABLED=true`; that runtime-kind registration does not add
  `mlx_vlm` to the factory selector contract.
- `whooshd/config.py:get_advertised_model_id()` recognizes only backend `mlx`
  for the process-level advertised model and otherwise returns `stub-model`.

The exact requested value was simulated with the active checkout's own Python
environment, without starting a server or invoking a model:

```text
WHOOSHD_ADAPTER=mlx_vlm .venv311/bin/python -c '... create_adapter() ...'

backend=mlx_vlm
adapter_class=StubInferenceAdapter
adapter_kind=stub
adapter_name=stub
model_id=stub-model
```

This is the task's first causal blocker. A plist-only mutation to
`WHOOSHD_ADAPTER=mlx_vlm` would make the fresh process select an unknown factory
value and fall back to Stub. It would fail the required conditions:

```text
WHOOSHD_CURRENT_EXECUTION_ADAPTER=mlx_vlm
no fallback to stub
```

The appropriate fail-closed classification is therefore:

```text
BLOCKED: WHOOSHD_MLX_ADAPTER_FALLBACK_TO_STUB
```

No source edit is authorized to add a new factory token, and changing the
value to `mlx` is not an acceptable workaround: it selects the incompatible
legacy text-only `mlx_lm` lane and does not activate the canonical multimodal
Qwen `mlx_vlm` runtime. The exact Qwen registry route remains source-proven to
resolve to the separately registered `mlx_vlm` adapter, but that does not make
the unsupported process-level selector safe to write.

## Why no lifecycle action was attempted

The task requires one bootout followed by one quiescent bootstrap only after the
single plist delta is proven to select `mlx_vlm` without fallback. The source
simulation proves the opposite before mutation. Consequently:

```text
WHOOSHD_ADAPTER_CONFIG_MUTATIONS_DURING_ACTIVATION=0
WHOOSHD_ADAPTER_ACTIVATION_LIFECYCLE_CYCLES=0
WHOOSHD_ADAPTER_ACTIVATION_BOOTOUT_ATTEMPTS=0
WHOOSHD_ADAPTER_ACTIVATION_BOOTSTRAP_ATTEMPTS=0
WHOOSHD_LAUNCHD_STATE=running (unchanged; no teardown attempted)
```

The plist remained byte-for-byte unchanged, with the same SHA-256,
owner/group/mode, and syntax result. No parallel environment, shell wrapper,
`launchctl setenv`, second plist, repository-local override, or source change
was introduced. No sudo command was requested, executed, captured, or stored;
the operator retained all privileged credential authority.

## Execution, service, storage, and release boundaries

```text
MODEL_INVOCATIONS_DURING_MLX_ADAPTER_ACTIVATION=0
QWEN_REAL_INFERENCE_STATUS=UNPROVEN
GUARDIAN_BACKEND_LIFECYCLE_ACTIONS_DURING_MLX_ADAPTER_ACTIVATION=0
WORKER_CHAT_LIFECYCLE_ACTIONS_DURING_MLX_ADAPTER_ACTIVATION=0
REDIS_LIFECYCLE_ACTIONS_DURING_MLX_ADAPTER_ACTIVATION=0
POSTGRES_LIFECYCLE_ACTIONS_DURING_MLX_ADAPTER_ACTIVATION=0
DEEPSEEK_REQUESTS_DURING_MLX_ADAPTER_ACTIVATION=0
WATCHDOG_ACTIVITY_DURING_MLX_ADAPTER_ACTIVATION=0
GITHUB_IO_DURING_MLX_ADAPTER_ACTIVATION=0
COMMAND_BUS_ACTIVITY_DURING_MLX_ADAPTER_ACTIVATION=0
BUILD_LOOP_ACTIVITY_DURING_MLX_ADAPTER_ACTIVATION=0
POSTGRES_MUTATIONS_DURING_MLX_ADAPTER_ACTIVATION=0
REDIS_MUTATIONS_DURING_MLX_ADAPTER_ACTIVATION=0
CHROMA_MUTATIONS_DURING_MLX_ADAPTER_ACTIVATION=0
MODEL_ARTIFACT_MUTATIONS_DURING_MLX_ADAPTER_ACTIVATION=0
```

No Tester or Guardian restart, health requalification, chat task, proof-only
session, user message, assistant message, warmup, completion, DeepSeek call,
Watchdog operation, GitHub I/O, or storage operation occurred. The unrelated
`guardian/workers/watchdog_review_worker.py` remained untouched and unstaged.
`docs/architecture/00-current-state.md` remained unchanged.

## Validation and repository boundary

Only this Codexify proof file is attributable to this blocked task. No
Whoosh'd file was edited, and no launchd lifecycle action was attempted.

Required validation for the proof artifact:

```text
python3 scripts/validate_docs.py
git diff --check
git diff --name-only
git status --short --branch
```

The Codexify commit must stage only:

```text
docs/architecture/proofs/runtime/2026-08-26-whooshd-qwen-mlx-adapter-activation-proof.md
```

## Deferred repair decision

The next repair cannot be plist-only under the current source contract. A
separate bounded Whoosh'd architecture/source task must mechanically define and
implement (or document an existing supported path for) a process-level
`mlx_vlm` selector before any launchd activation can be attempted. That task
must preserve the registry mapping and exact Qwen authority, avoid `mlx` as a
text-only workaround, and prove no fallback before a single lifecycle cycle.

Only after a real `mlx_vlm` adapter activation passes may the separate
authenticated ordinary Tester Qwen completion proof run. That completion proof
must use exactly one attempt, no retry or fallback, durable API/PostgreSQL
readback, and no DeepSeek or Watchdog activity. Watchdog remains frozen.
