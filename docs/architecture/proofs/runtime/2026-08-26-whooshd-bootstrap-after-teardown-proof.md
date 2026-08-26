# Whoosh'd bootstrap after launchd teardown proof

**Classification:** `WHOOSHD_QWEN_BOOTSTRAP_AFTER_TEARDOWN_PASS`
**ADR impact:** Aligned with ADR-074; no ADR change.

## Scope and authority boundaries

This proof records one system-domain bootstrap after the prior launchd removal
was proven complete. It does not change Tester provider/model authority, the
plist, registry, model artifacts, Guardian, backend/worker services,
DeepSeek, Watchdog, or storage.

The human operator, not the agent, supplied interactive system authority. No
sudo password, password file, `sudo -S` input, or credential environment value
was received or stored. The pre-existing unrelated unstaged edit in
`guardian/workers/watchdog_review_worker.py` was left untouched and unstaged.

## Required lineage and immutable configuration

- Codexify branch: `codex/diagnose-tester-fresh-chroma-failure`
- Prerequisite commit: `87f45f6b1c713ae79350962855937c774026e652`
  (`Diagnose Whooshd bootstrap failure`); `git cat-file -e` and
  `git merge-base --is-ancestor` both passed before the lifecycle action.
- Whoosh'd root/branch/HEAD: `/Volumes/Dev_SSD/ResonantConstructs/Whoosh'd`,
  `main`, `09e83a8359e3673e7c18a2e0b4733afd334b3bac`.
- Whoosh'd status remained clean:
  `main...origin/main [ahead 1, behind 22]`.
- Plist: `/Library/LaunchDaemons/com.resonant.whooshd.plist`, SHA-256
  `3a82268a28b81ed35019e2abf9bc587a93e16985572aaa31c6a86f4f4b990c33`,
  `root:wheel -rw-r--r--`, label `com.resonant.whooshd`; `plutil -lint`
  returned `OK`.
- Registry: `configs/models.friends-family-guest.yaml`, blob
  `dc70602d29c174560e012943f32b67b14b69d12a`.
- Qwen mapping: `qwen3.8-27b-4bit`, `engine: mlx_vlm`, `format: mlx`,
  to `/Volumes/Dev_SSD/whooshd/model-weights/Qwen3.8-27B-4bit`.

Bounded pre-bootstrap checks confirmed that the launcher remained executable,
the Whoosh'd working directory and canonical registry existed, the registry
remained readable, the established Qwen artifact remained present, and the
existing stdout/stderr destinations were usable. No configuration or artifact
was changed.

## Teardown-quiescence proof

Before the bootstrap:

- `launchctl print system/com.resonant.whooshd` reported no service in the
  system domain.
- `launchctl print-disabled system` showed the label as `enabled`.
- No matching Whoosh'd/Uvicorn process and no `127.0.0.1:8000` listener
  existed.
- A 15-minute, label-only unified-log query for the service and plist was
  empty.
- The system service tree contained no target-label record beyond the enabled
  preference entry.

```text
WHOOSHD_LAUNCHD_STATE=fully_unloaded
WHOOSHD_PRE_BOOTSTRAP_PROCESS_COUNT=0
WHOOSHD_PRE_BOOTSTRAP_PORT_LISTENERS=0
```

No target-label teardown, pending operation, or stale intermediate service
record remained. No `bootout` was run in this task.

## One operator bootstrap

The exact command handed to, and interactively executed by, the operator was:

```zsh
sudo launchctl bootstrap system /Library/LaunchDaemons/com.resonant.whooshd.plist
```

The operator confirmed completion without providing credentials. This was the
only bootstrap in the task:

```text
WHOOSHD_BOOTSTRAP_ATTEMPTS=1
WHOOSHD_BOOTOUT_ATTEMPTS_DURING_PROOF=0
```

## Fresh service and process proof

After bootstrap, `launchctl print system/com.resonant.whooshd` reported:

```text
state = running
active count = 1
runs = 1
pid = 50696
last exit code = (never exited)
program = /Users/chriscastillo/.local/bin/whooshd
```

The fresh PID was established by host-level process inspection:

```text
PID 50696
user chriscastillo
start Wed Aug 26 05:29:17 2026
command .../Python -m uvicorn whooshd.app:app --host 127.0.0.1 --port 8000
```

PID 50696 was the sole process listening on `127.0.0.1:8000`. The prior
zero-process/zero-listener baseline, launchd active count of one, and single
listener establish a fresh process and no duplicate stale process.

The bounded fresh stderr tail recorded successful Uvicorn startup for PID
50696 and `Uvicorn running on http://127.0.0.1:8000`. The bounded fresh stdout
tail recorded `Starting Whoosh'd on http://127.0.0.1:8000 with adapter=stub`.
No fatal registry parse, Qwen-artifact resolution failure, exception, or
traceback was present in the bounded stderr check.

The `adapter=stub` line is recorded as observed. This proof establishes a
fresh registry-backed inventory process, not model loading or completion
execution.

## Canonical inventory and artifact identity

The non-inference `GET http://127.0.0.1:8000/v1/models` response had exactly
one model entry:

```text
id: qwen3.8-27b-4bit
engine: mlx_vlm
format: mlx
modalities: text, vision
context_window: 65536
display_name: Qwen3.8 27B 4-bit MLX
priority: guest_chat
warm_policy: keep_warm
```

No filesystem-path Qwen identity appeared in the response. The sole canonical
entry eliminates a raw-path or duplicate runtime identity.

Artifact identity is not inferred from the advertised string alone. The fresh
response metadata agrees with the unchanged canonical registry blob, whose
exact Qwen mapping remains `mlx_vlm` / `mlx` to
`/Volumes/Dev_SSD/whooshd/model-weights/Qwen3.8-27B-4bit`. That established
artifact directory was verified present without reading, moving, hashing, or
modifying model data.

## Result

`WHOOSHD_QWEN_BOOTSTRAP_AFTER_TEARDOWN_PASS`

The launchd race from the prerequisite did not recur after a fully quiescent
teardown. The unchanged plist registered one fresh Whoosh'd process and served
a canonical one-entry Qwen inventory with no raw-path duplicate.

## Execution and persistence boundaries

| Boundary | Result |
| --- | --- |
| Bootout attempts during this proof | `0` |
| Bootstrap attempts during this proof | `1` |
| Model invocations or completions | `0` |
| Guardian qualification calls | `0` |
| Backend restarts | `0` |
| `worker-chat` restarts | `0` |
| DeepSeek requests | `0` |
| Watchdog activity | `0` |
| Manual Postgres, Redis, Chroma, or model-artifact mutation | `0` |

The only HTTP operation issued by this proof was the Whoosh'd inventory read.
No chat task, warmup, completion, DeepSeek request, or Watchdog action was
issued. Previous proof receipts and `docs/architecture/00-current-state.md`
remain unchanged.

## Validation record

```text
git cat-file -e 87f45f6b1c713ae79350962855937c774026e652^{commit}
git merge-base --is-ancestor 87f45f6b1c713ae79350962855937c774026e652 HEAD
git status --short --branch
git rev-parse HEAD
git branch --show-current
launchctl print system/com.resonant.whooshd
launchctl print-disabled system
lsof -nP -iTCP:8000 -sTCP:LISTEN
plutil -lint /Library/LaunchDaemons/com.resonant.whooshd.plist
git -C /Volumes/Dev_SSD/ResonantConstructs/Whoosh'd rev-parse HEAD
git -C /Volumes/Dev_SSD/ResonantConstructs/Whoosh'd hash-object configs/models.friends-family-guest.yaml
curl --fail http://127.0.0.1:8000/v1/models
```

The host-level process observation confirmed the launchd PID as the expected
Uvicorn process. No validation command changed Whoosh'd runtime configuration.

## Deferred next slice

Qualify Guardian against this freshly bootstrapped Whoosh'd runtime using only
non-inference health and catalog surfaces. Prove `local` /
`qwen3.8-27b-4bit` availability, Redis health, fresh worker heartbeat, and an
idle chat queue. Do not execute an authenticated completion or Watchdog work
in that same task.
