# Whoosh'd Qwen registry restoration receipt

## Result

`BLOCKED: WHOOSHD_LAUNCHD_RELOAD_PERMISSION_DENIED`

The canonical registry source was restored and committed byte-for-byte, and
the already-running Whoosh'd proxy dynamically began advertising the exact
configured Qwen ID. The task's required single fresh-process proof could not
run: the one permitted canonical launchd reload attempt failed at
`launchctl bootout system/com.resonant.whooshd` with `Operation not
permitted`. Bootstrap was not attempted and no alternate restart mechanism was
used.

This is not a Whoosh'd startup failure: the pre-existing proxy remained
running and healthy. It is a host lifecycle permission blocker, so the
required restart evidence and Guardian readback are deliberately unproven.

## Accepted prerequisite lineage

The task used the accepted mappings established by
`ec0e5693b0544477a225dc8447346bab49591493`:

```text
536c06c9e9297254c86b5974b1db4c0d327bc8ae -> 504c72f681350f37f98a7a41533a2c78b681c989
802f9baba0f22e38e13f37307b2769a10240119b -> 8e3af0191295704b59cba2c746fa8dc7bc098af8
```

All three accepted prerequisites (`ec0e5693…`, `504c72f6…`, and `8e3af019…`)
are ancestors of the Codexify task HEAD
`ec0e5693b0544477a225dc8447346bab49591493`.

The task worktree had, and still has, an unrelated unstaged modification in
`guardian/workers/watchdog_review_worker.py`. It was not edited, staged,
restored, or reformatted by this task.

## Active Whoosh'd identity and target resolution

| Field | Value |
| --- | --- |
| Root | `/Volumes/Dev_SSD/ResonantConstructs/Whoosh'd` |
| Remote | `https://github.com/Resonant-Jones/whooshd.git` |
| Branch / pre-restore HEAD | `main` / `da216d76a0a3ea5c8930f1a0cf722151af526e31` |
| Dirty state before restoration | clean, 22 commits behind `origin/main` |
| Proxy plist | `/Library/LaunchDaemons/com.resonant.whooshd.plist` |
| Registry argument | `WHOOSHD_MODEL_REGISTRY_PATH` |
| Raw argument and loader-resolved target | `/Volumes/Dev_SSD/ResonantConstructs/Whoosh'd/configs/models.friends-family-guest.yaml` |
| Proxy working directory | `/Volumes/Dev_SSD/ResonantConstructs/Whoosh'd` |

The current loader passes the explicit environment value to `Path(path)` and
loads it only when it is a file. Therefore this absolute plist value—not a
default filename or alternate registry—is the active target. It was absent
before restoration. The plist remained syntactically valid and unchanged.

## Canonical source, validation, and restoration

The active Whoosh'd repository's history supplied the authoritative source:

| Evidence | Value |
| --- | --- |
| Commit | `81fe385b44f124ce528902964e049d815da34979` |
| Source path | `configs/models.friends-family-guest.yaml` |
| Git blob | `dc70602d29c174560e012943f32b67b14b69d12a` |
| SHA-256 | `93fabb026ec3314271f58f1cea69a05fa96bb1fae8de4d54c0fa40c517775817` |
| Mapping | `qwen3.8-27b-4bit` -> `mlx_vlm` / `mlx` -> `/Volumes/Dev_SSD/whooshd/model-weights/Qwen3.8-27B-4bit` |

The current parser loaded the historical blob from a disposable path and then
from the restored target. Both validations passed: the canonical ID count was
one, required fields were present, and the resolved artifact directory exists.
The current active target had no registry before restoration; no current
registry file defines the canonical Qwen ID. No registry manifest or index is
needed because the loader consumes the explicit YAML path directly.

The target was restored directly from the Git object, not reconstructed. Its
Git blob and SHA-256 match the historical source exactly. It is not ignored,
so it is repository-owned configuration. The only Whoosh'd change was narrowly
committed before the reload attempt:

```text
09e83a8359e3673e7c18a2e0b4733afd334b3bac Restore friends family Qwen registry
```

## Inventory and lifecycle boundary

Before restoration, `/v1/models` advertised only:

1. `mlx-community/Llama-3.2-3B-Instruct-4bit`
2. `/Volumes/Dev_SSD/whooshd/model-weights/Qwen3.8-27B-4bit`

The exact configured ID was absent. Immediately after the file restoration,
before any successful service lifecycle action, the running proxy dynamically
advertised exactly one model:

```text
qwen3.8-27b-4bit
```

Its metadata reports `engine=mlx_vlm`, `format=mlx`, text/vision modalities,
and the historical registry's context, display-name, priority, and warm-policy
values. The raw filesystem-path Qwen identity is no longer advertised, so this
read-only inventory surface has no blocking duplicate identity. This dynamic
result does not substitute for the requested fresh-start proof.

The sole canonical reload attempt was:

```text
launchctl bootout system/com.resonant.whooshd
```

It failed before unload with `Operation not permitted`. Consequently:

```text
WHOOSHD_REGISTRY_RESTORE_RELOAD_ATTEMPTS=1
WHOOSHD_REGISTRY_RESTORE_RESTARTS=0
```

No bootstrap, retry, `sudo` fallback, plist edit, sidecar restart, Tester
restart, Redis restart, or backend refresh occurred. After the denied attempt,
the same proxy service remained `running` as PID `849`, listening on
`127.0.0.1:8000`, with `/health` reporting `ok=true`, `status=ready`, and
queue depth `0`.

## Unproven Guardian and execution boundaries

Guardian `/api/health/llm`, `/api/llm/catalog`, and `/health/chat` were not
queried after the lifecycle blocker. No backend inventory-refresh decision was
made. Their post-restoration state, Redis health, chat-worker heartbeat, and
chat queue depth are therefore not claimed by this receipt.

No thread, user message, completion task, assistant message, model inference,
DeepSeek request, Watchdog attempt/dispatch/result, GitHub I/O, Command Bus,
or Build Loop activity occurred.

```text
MODEL_INVOCATIONS_DURING_REGISTRY_RESTORE=0
DEEPSEEK_REQUESTS_DURING_REGISTRY_RESTORE=0
WATCHDOG_ACTIVITY_DURING_REGISTRY_RESTORE=0
```

No manual Postgres, Redis, Chroma, model-artifact, or migration mutation
occurred.

## ADR impact and required next decision

**Aligned with ADR-074; no ADR change.**

`docs/architecture/00-current-state.md` and all earlier BLOCKED receipts
remain unchanged. An operator with the required system launchd authority must
perform the already-specified one proxy-only reload, after which a new bounded
proof task may verify fresh-process inventory and Guardian health without
inference. Do not begin the authenticated Qwen completion or any Watchdog work
from this blocked receipt.
