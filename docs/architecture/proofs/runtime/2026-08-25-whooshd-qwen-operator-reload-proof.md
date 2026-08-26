# Whoosh'd Qwen operator reload proof

## Result

`WHOOSHD_OPERATOR_BOOTSTRAP_FAILURE`

The human operator completed the task-authorized single lifecycle cycle
interactively. The bootout succeeded; the one permitted bootstrap failed with
`Bootstrap failed: 5: Input/output error`. No second bootstrap or alternate
service start was attempted.

This receipt proves the unload and captures the first causal bootstrap error.
It does not prove a fresh Whoosh'd PID, port listener, startup log, or
fresh-start Qwen inventory. The proxy is intentionally unloaded at closeout.

## Baseline and authority boundary

| Surface | Pre-reload observation |
| --- | --- |
| UTC baseline | `2026-08-25T21:39:48Z` |
| Codexify checkout | `codex/diagnose-tester-fresh-chroma-failure` at `edc66d28db6a4582227fb737af9ce32ebd538df0` |
| Prior proof ancestry | `edc66d28…` is an ancestor of the task HEAD |
| Whoosh'd checkout | `main` at `09e83a8359e3673e7c18a2e0b4733afd334b3bac` |
| Registry blob | `dc70602d29c174560e012943f32b67b14b69d12a` |
| Registry path | `configs/models.friends-family-guest.yaml` |
| Launchd service / plist | `system/com.resonant.whooshd` / `/Library/LaunchDaemons/com.resonant.whooshd.plist` |
| Registry argument | `WHOOSHD_MODEL_REGISTRY_PATH=/Volumes/Dev_SSD/ResonantConstructs/Whoosh'd/configs/models.friends-family-guest.yaml` |
| Pre-reload PID / port | `849` / `127.0.0.1:8000` |
| Pre-reload inventory | exact `qwen3.8-27b-4bit`; raw filesystem-path Qwen identity absent |

The active plist passed `plutil -lint`. The restored registry remains
byte-identical to its canonical SHA-1 blob and maps the canonical ID to the
existing local Qwen artifact at
`/Volumes/Dev_SSD/whooshd/model-weights/Qwen3.8-27B-4bit`. Neither the plist
nor registry was changed by this task. The Whoosh'd worktree remains clean.

The pre-existing unstaged Codexify edit in
`guardian/workers/watchdog_review_worker.py` remains untouched and unstaged.

## Operator-authorized lifecycle cycle

The agent presented these exact, live-resolved commands to the operator:

```bash
sudo launchctl bootout system/com.resonant.whooshd
sudo launchctl bootstrap system /Library/LaunchDaemons/com.resonant.whooshd.plist
```

The operator ran them interactively in a terminal where `sudo` requested the
operator's password. The password was never provided to, received by, stored
by, or logged by the agent.

The operator reported no bootout error and reported this bootstrap result:

```text
Bootstrap failed: 5: Input/output error
```

Independent post-action checks prove the bootout completed: launchd reports
that `com.resonant.whooshd` is absent from the `system` domain, no process
listens on TCP `127.0.0.1:8000`, and bounded `/health` and `/v1/models` probes
cannot connect. The existing bounded stdout/stderr startup logs contain no
new matching bootstrap, registry, Qwen-artifact, or fatal startup record,
consistent with bootstrap failing before a new proxy process began.

```text
WHOOSHD_OPERATOR_RELOAD_CYCLES=1
WHOOSHD_OPERATOR_BOOTOUT_RESULT=success
WHOOSHD_OPERATOR_BOOTSTRAP_RESULT=failed_input_output_error
WHOOSHD_POST_RELOAD_PID=none
```

## Execution and architecture boundaries

No model invocation, chat task, Qwen warmup, DeepSeek request, Watchdog
activity, GitHub I/O, Command Bus activity, Build Loop activity, backend or
worker restart, registry modification, plist modification, model-artifact
mutation, or manual Postgres/Redis/Chroma mutation occurred.

```text
MODEL_INVOCATIONS_DURING_OPERATOR_RELOAD_PROOF=0
DEEPSEEK_REQUESTS_DURING_OPERATOR_RELOAD_PROOF=0
WATCHDOG_ACTIVITY_DURING_OPERATOR_RELOAD_PROOF=0
```

Guardian qualification surfaces were not queried. No fresh Qwen inventory or
artifact-identity claim is made because bootstrap did not start a process.

**Aligned with ADR-074; no ADR change.**

The immediate next slice is a separate, bounded diagnosis of the single
launchd bootstrap `Input/output error` that preserves the registry and plist
unchanged. Do not retry bootout/bootstrap, perform Guardian qualification, or
run Qwen inference from this receipt.
