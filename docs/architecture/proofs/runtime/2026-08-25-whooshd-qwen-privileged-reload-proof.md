# Whoosh'd Qwen privileged reload proof

## Result

`BLOCKED: WHOOSHD_SYSTEM_LAUNCHD_AUTHORITY_UNAVAILABLE`

The registry and currently running proxy meet every non-lifecycle precondition,
but this execution session cannot manage the `system` launchd domain. The
non-mutating authority preflight `sudo -n true` returned `sudo: a password is
required`. No bootout, bootstrap, proxy stop, or retry was attempted.

This receipt does not prove a fresh proxy process. It preserves the lifecycle
boundary for an operator session with system launchd authority.

## Prerequisites and pre-reload baseline

| Surface | Observation |
| --- | --- |
| Codexify task checkout | `codex/diagnose-tester-fresh-chroma-failure` at `c79bdaf3d0135882cc4cb01cbdef384875abaecf` |
| Prior blocked-receipt ancestry | `c79bdaf3…` is an ancestor of task HEAD |
| Codexify unrelated worktree state | pre-existing unstaged `guardian/workers/watchdog_review_worker.py`; left untouched and unstaged |
| Whoosh'd root / branch / HEAD | `/Volumes/Dev_SSD/ResonantConstructs/Whoosh'd`, `main`, `09e83a8359e3673e7c18a2e0b4733afd334b3bac` |
| Whoosh'd worktree state | clean; `ahead 1, behind 22` relative to `origin/main` |
| Registry path | `configs/models.friends-family-guest.yaml` |
| Registry blob / SHA-256 | `dc70602d29c174560e012943f32b67b14b69d12a` / `93fabb026ec3314271f58f1cea69a05fa96bb1fae8de4d54c0fa40c517775817` |
| Launchd service / plist | `system/com.resonant.whooshd` / `/Library/LaunchDaemons/com.resonant.whooshd.plist` |
| Registry argument | `WHOOSHD_MODEL_REGISTRY_PATH=/Volumes/Dev_SSD/ResonantConstructs/Whoosh'd/configs/models.friends-family-guest.yaml` |
| Pre-reload proxy PID / listener | `849` / `127.0.0.1:8000` |

The active plist passed `plutil -lint`, retains label
`com.resonant.whooshd`, and was not changed. The registry is present, tracked,
and byte-identical to the canonical blob. No Whoosh'd source or configuration
change was made in this proof task.

The pre-reload `/v1/models` inventory contains exactly:

```text
qwen3.8-27b-4bit
```

Its metadata reports `engine=mlx_vlm`, `format=mlx`, text/vision modalities,
and the restored registry metadata. The prior raw filesystem-path Qwen ID is
absent. The registry maps the canonical ID to the established artifact:

```text
/Volumes/Dev_SSD/whooshd/model-weights/Qwen3.8-27B-4bit
```

## Privilege gate and stop decision

The canonical operator documentation requires `sudo launchctl bootout system`
for this system LaunchDaemon. The task therefore requires an operator context
with non-interactive system-domain authority before changing lifecycle state.

```text
sudo -n true
sudo: a password is required
```

The prior unprivileged failure was not repeated. Because authority is absent,
there is no authorized way to run the packet's single bootout/bootstrap cycle
from this session.

```text
WHOOSHD_PRIVILEGED_RELOAD_CYCLES=0
WHOOSHD_PRIVILEGED_BOOTOUT_ATTEMPTS=0
WHOOSHD_PRIVILEGED_BOOTSTRAP_ATTEMPTS=0
```

No post-reload PID, startup log, fresh inventory, or fresh-process artifact
identity is claimed.

## Execution and architecture boundaries

No model invocation, chat task, Qwen warmup, DeepSeek request, Watchdog
activity, GitHub I/O, Command Bus activity, Build Loop activity, backend or
worker restart, Redis/Postgres/Chroma mutation, artifact mutation, registry
mutation, or plist mutation occurred.

```text
MODEL_INVOCATIONS_DURING_PRIVILEGED_RELOAD_PROOF=0
DEEPSEEK_REQUESTS_DURING_PRIVILEGED_RELOAD_PROOF=0
WATCHDOG_ACTIVITY_DURING_PRIVILEGED_RELOAD_PROOF=0
```

Guardian qualification endpoints were not queried; that is a separate task
following a successful fresh-start proof.

**Aligned with ADR-074; no ADR change.**

The next step requires an operator session with system launchd authority to
perform exactly one proxy-only bootout/bootstrap cycle using the unchanged
plist. After that succeeds, a separate bounded task may verify the new PID,
fresh `/v1/models` identity, and then Guardian health without inference.
