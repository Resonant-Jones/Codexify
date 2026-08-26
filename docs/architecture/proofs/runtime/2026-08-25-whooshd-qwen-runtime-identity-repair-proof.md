# Whoosh'd Qwen runtime identity repair proof

## Result

`WHOOSHD_IDENTITY_DRIFT_UNRESOLVED`

The selected Tester model authority remains correct: the active backend and
`worker-chat` use provider `local` and exact
`qwen3.8-27b-4bit`. The running Whoosh'd proxy and MLX-VLM sidecar use the
existing Qwen3.8 artifact, but the proxy advertises the artifact's filesystem
path instead of the exact configured model ID.

The installed Whoosh'd runtime supports exact served IDs through an enabled
model-registry entry. Its active launchd plist points to the required Qwen
registry path, but that file is absent from the current Whoosh'd checkout. The
valid historical Qwen registry belongs to a different source lineage. This
task authorizes changing only the active host plist, not recreating or
restoring the absent registry source. Pointing the plist at an unrelated
existing registry, inventing a CLI flag, or adding a Guardian alias would not
preserve the required artifact-to-ID contract. No restart was attempted.

This is a branch-local blocked receipt. It does not prove Qwen inference,
alter Tester authority, or qualify Watchdog.

## Source, authority, and baseline

- Task checkout: `codex/diagnose-tester-fresh-chroma-failure` at
  `536c06c9e9297254c86b5974b1db4c0d327bc8ae`.
- Required authority-reconciliation and ADR-074 restoration commits are
  verified ancestors; `.env.tester` remains ignored and unchanged.
- Active Tester non-secret effective values: `LLM_PROVIDER=local`,
  `LOCAL_CHAT_MODEL=qwen3.8-27b-4bit`, cloud enabled, local-only disabled,
  egress allowlist `deepseek`.
- The active Tester backend and `worker-chat` remain running with restart count
  `0`; no backend or worker restart occurred.

ADR-074 remains aligned: the operator/configured value selects the concrete
model, Whoosh'd owns inventory truth, and Guardian correctly rejects an
advertised filesystem path as a substitute for the configured model ID.
No ADR, provider-routing, model-selection, DeepSeek, or Guardian matching rule
was changed.

## Active Whoosh'd baseline

| Surface | Observation |
| --- | --- |
| Proxy service | `system/com.resonant.whooshd`, PID `849`, `/Users/chriscastillo/.local/bin/whooshd`, package version `0.1.0`, loopback `127.0.0.1:8000` |
| Sidecar service | `system/com.resonant.mlx-vlm-gemma12b`, PID `850`, `.venv311/bin/python -m mlx_vlm server`, loopback `127.0.0.1:8082` |
| Active proxy plist | `/Library/LaunchDaemons/com.resonant.whooshd.plist` |
| Active sidecar plist | `/Library/LaunchDaemons/com.resonant.mlx-vlm-gemma12b.plist` |
| Artifact path in both active services | `/Volumes/Dev_SSD/whooshd/model-weights/Qwen3.8-27B-4bit` |
| Registry path in active proxy plist | `/Volumes/Dev_SSD/ResonantConstructs/Whoosh'd/configs/models.friends-family-guest.yaml` |

Both active plists passed `plutil -lint`; the launcher passed `zsh -n`.
The proxy launcher accepts only adapter/model/host/port controls and has no
explicit served-model-ID argument. Its local documentation states that direct
MLX mode advertises `WHOOSHD_MLX_MODEL` verbatim, while registry mode uses the
registry model key as the inventory identity.

The pre-repair `GET http://127.0.0.1:8000/v1/models` IDs were:

1. `mlx-community/Llama-3.2-3B-Instruct-4bit`
2. `/Volumes/Dev_SSD/whooshd/model-weights/Qwen3.8-27B-4bit`

The exact configured ID `qwen3.8-27b-4bit` was absent. `/api/tags` reported
the same path identity.

## Artifact and supported naming mechanism

The advertised Qwen path resolves to
`/Volumes/Dev_SSD/whooshd/model-weights/Qwen3.8-27B-4bit`, owned by
`chriscastillo:staff`, approximately `15G`. Its bounded `config.json`
evidence identifies `model_type=qwen3_5`,
`Qwen3_5ForConditionalGeneration`, and 4-bit affine quantization. The
sidecar startup log recorded pre-loading that same path and `Model ready,
continuous batching enabled.`

The installed editable Whoosh'd source documents and implements a registry
mapping of `model_id` to an enabled model entry. It loads the path named by
`WHOOSHD_MODEL_REGISTRY_PATH`; if the path is absent it falls back to
runtime-provided inventory, which exposes the VLM artifact path. `/v1/models`
uses registry entries as authoritative metadata when a registry is active.

The current Whoosh'd checkout is
`da216d76a0a3ea5c8930f1a0cf722151af526e31`. It contains only
`models.yaml`, `models.validated.yaml`, and `models.gguf-example.yaml`; none
contains `qwen3.8-27b-4bit`. The active configured guest registry is absent.

Local Git history contains a valid, but non-current-lineage, guest registry
whose one enabled entry maps exactly:

```text
qwen3.8-27b-4bit -> mlx_vlm -> /Volumes/Dev_SSD/whooshd/model-weights/Qwen3.8-27B-4bit
```

The current runtime's registry validator accepts that historical entry. Its
source commit `81fe385b44f124ce528902964e049d815da34979` is not an ancestor of
the current Whoosh'd checkout. The plist therefore has a
`WHOOSHD_LAUNCHD_RUNTIME_DRIFT`: it still points to a registry absent from its
current source root.

## Stop decision and runtime state

`WHOOSHD_IDENTITY_REPAIR_RESTARTS=0`.

No host plist, launcher/template, registry, artifact, cache, or source file
was modified. The only supported exact-ID mechanism requires restoring the
absent Qwen registry, but the packet declares the model registry read-only and
authorizes only the active host plist as a mutable runtime file. A plist-only
edit cannot provide the required mapping without selecting a wrong existing
registry or inventing an unsupported alias.

No model download, artifact move, rename, symlink, duplicate cache, or
inference occurred. `MODEL_INVOCATIONS_DURING_IDENTITY_REPAIR=0` and
`DEEPSEEK_REQUESTS_DURING_IDENTITY_REPAIR=0`.

## Guardian and queue readback

Without any backend restart, Guardian reported:

- `/api/health/llm`: provider `local`, model `qwen3.8-27b-4bit`,
  `configured_model_not_advertised_by_whooshd`, and unavailable configured
  model;
- `/health/chat`: Redis `ok`, fresh chat-worker heartbeat, queue depth `0`,
  and unhealthy solely because the configured Qwen ID is absent from
  inventory; and
- `/api/llm/catalog`: local provider authorized/reachable but disabled due to
  the exact identity mismatch. DeepSeek remained the bounded
  `deepseek-v4-flash` lane and was not attempted.

No chat task, Watchdog attempt or dispatch, GitHub I/O, Command Bus, Build
Loop, Postgres, Redis, or Chroma mutation occurred.

## ADR impact, validation, and follow-through

**Aligned with ADR-074; no ADR change.**

`docs/architecture/00-current-state.md` remained untouched. No focused runtime
test applies because no tracked launcher/template changed. Documentation
validation and Git diff checks for this receipt are recorded with task
closeout.

The necessary follow-up is an explicitly authorized restoration of the
canonical Qwen registry source (or a separately accepted equivalent
registry-owned mechanism), followed by one controlled Whoosh'd restart and
exact inventory/Guardian readback. Do not use a filesystem-path alias or begin
the authenticated Qwen completion or Watchdog qualification first.
