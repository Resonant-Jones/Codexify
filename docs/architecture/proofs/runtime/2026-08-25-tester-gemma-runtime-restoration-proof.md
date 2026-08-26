# Tester Gemma runtime restoration proof

## Result

`GEMMA_RUNTIME_REQUIRES_AUTHORITY_CHANGE`

The exact local Gemma artifact is present and the host Whoosh'd launchd
configuration has a repairable `WHOOSHD_STARTUP_ARGUMENT_DRIFT`: its active
system plists select Qwen, while the current Whoosh'd renderer produces valid
Gemma plists backed by `configs/models.yaml`. That operational repair was not
performed because the currently running Tester is not using this worktree's
operator environment. Its live container is mounted from
`/Volumes/Dev_SSD/Codexify-main` and its read-only environment selects
`qwen3.8-27b-4bit`.

Under ADR-074, that active operator environment owns the concrete Tester model
selection. Replacing the host runtime with Gemma would therefore leave the
running Guardian configured for Qwen and fail closed. Making Guardian accept
Gemma would require changing the active Tester's model selection, which this
task expressly forbids. The one permitted Whoosh'd restoration was preserved
rather than spent on a state that could not satisfy the required Guardian
readback.

This is a branch-local diagnostic receipt. It does not change current-main
release truth, establish live Gemma availability, prove a completion, or
qualify Watchdog.

## Source, lineage, and authority boundary

- Source worktree: `/Users/chriscastillo/.codex/worktrees/5ab6/Codexify-main`.
- Source branch / HEAD: `codex/diagnose-tester-fresh-chroma-failure` /
  `714b7fa66a07252f96048433c79d1ca5ae30513b`.
- Required commits `714b7fa66a07252f96048433c79d1ca5ae30513b`,
  `0ff80e332fa19edea85abc977275bd37fc8d409a`, and
  `17aebb8d8724998510578c188fc9af73a7f248fb` were verified ancestors.
- `.env.tester` is ignored by `.gitignore`; it was not modified.

The task worktree's non-secret operator values remained `LLM_PROVIDER=local`,
`LOCAL_CHAT_MODEL=gemma-4-12b-it-qat-4bit`,
`ALLOW_CLOUD_PROVIDERS=true`, and `CODEXIFY_LOCAL_ONLY_MODE=false`. They are
not the values used by the live Tester described below.

| Surface | Observed authority / identity |
| --- | --- |
| Running Tester project | `codexify_tester`, backend `codexify_tester-backend-1`, loopback port `8889`, image `sha256:2508fe43e87e883caea01fe36b5ab5eff3a1d9616d395d7e7903b03204a584cf` |
| Running Tester source mount | `/Volumes/Dev_SSD/Codexify-main` for backend, Guardian, config, tests, and Chroma; it is not this task worktree |
| Running Tester's non-secret environment | `LLM_PROVIDER=local`, `LOCAL_CHAT_MODEL=qwen3.8-27b-4bit`, `ALLOW_CLOUD_PROVIDERS=true`, `CODEXIFY_LOCAL_ONLY_MODE=false` |
| Mounted source state | detached `972c348301de68c54c0498c72d236a1e496bee0f`, with pre-existing unrelated `UU docs/architecture/00-current-state.md` and staged `docs/architecture/README.md` changes; left untouched |

ADR-074 makes the operator `.env.tester` the concrete local-model authority,
requires Compose to transport it, and requires Guardian to fail closed on an
inventory mismatch. It expressly does not allow live Whoosh'd inventory to
rewrite the configured model.

## Baseline Tester and Guardian observations

All requests in this section were non-inference health or catalog reads.

- `GET http://127.0.0.1:8889/health` returned `200`, selected provider
  `local`, and a valid `v1-whooshd-deepseek-web` profile.
- `GET /health/chat` reported Redis `ok`, a fresh `worker-chat` heartbeat,
  queue depth `0`, and `completion_service.ok=true`; its only unhealthy
  condition was that configured `qwen3.8-27b-4bit` was not advertised by
  Whoosh'd.
- `GET /api/health/llm` and `GET /api/llm/catalog` reported the same active
  Qwen selection and the fail-closed
  `configured_model_not_advertised_by_whooshd` state. The local provider had
  `attempted=false`, `executed=false`, and `completed=false`.
- Redis `LLEN codexify:queue:chat` returned `0`; the standard
  `codexify:worker:chat:heartbeat` key existed.

## Whoosh'd runtime and exact artifact evidence

The live host runtime is the system LaunchDaemon `com.resonant.whooshd` on
`127.0.0.1:8000`, with the labeled Gemma sidecar
`com.resonant.mlx-vlm-gemma12b` on `127.0.0.1:8082`. Both active system plists
actually name the Qwen directory
`/Volumes/Dev_SSD/whooshd/model-weights/Qwen3.8-27B-4bit`; the proxy also names
the absent registry path `configs/models.friends-family-guest.yaml`.

`GET http://127.0.0.1:8000/v1/models` and the sidecar's `/v1/models` advertised
only:

1. `mlx-community/Llama-3.2-3B-Instruct-4bit`
2. `/Volumes/Dev_SSD/whooshd/model-weights/Qwen3.8-27B-4bit`

The exact Gemma artifact exists at
`/Volumes/Dev_SSD/whooshd/model-weights/hub/models--mlx-community--gemma-4-12B-it-qat-4bit`:

- directory owner/mode: `chriscastillo:staff`, `drwxr-xr-x`;
- bounded size: `10G`;
- expected files present: `config.json`, `tokenizer.json`,
  `tokenizer_config.json`, and three `model-0000*-of-00003.safetensors`
  weights.

The current external Whoosh'd checkout at
`da216d76a0a3ea5c8930f1a0cf722151af526e31` has an enabled
`gemma-4-12b-it-qat-4bit` entry in `configs/models.yaml` pointing to that exact
artifact. Rendering its existing launchd templates into a temporary directory
produced two syntactically valid plists that select the exact Gemma directory
and the existing `configs/models.yaml` registry. No existing plist, system
file, cache, source file, or container was changed.

This proves the host-side discrepancy is a repairable
`WHOOSHD_STARTUP_ARGUMENT_DRIFT`, not `GEMMA_LOCAL_ARTIFACT_ABSENT` or a model
alias equivalence. It does not override the independent active Tester model
authority described above.

## Decision and execution boundary

`WHOOSHD_RESTORE_ATTEMPTS=0`.

No operational restoration was attempted. The source-rendered Gemma plists
would correct the host inventory seam, but the active Guardian is explicitly
configured for Qwen. A host-only change could not make the required exact
Gemma model available to that Guardian, and changing the active
`LOCAL_CHAT_MODEL` would be a prohibited authority decision.

No source, Compose, provider-policy, `.env.tester`, backend/chat, Watchdog,
database, Redis, Chroma, migration, or release-truth file was changed. The
only tracked change for this task is this receipt.

`MODEL_INVOCATIONS_DURING_PROOF=0` and
`DEEPSEEK_REQUESTS_DURING_PROOF=0`. The work performed only inventory, health,
catalog, container/launchd identity, and bounded filesystem reads. No chat task
was submitted; no model warmup or completion request was made; no Watchdog
lineage, GitHub I/O, Command Bus, or Build Loop activity occurred.

## ADR impact, validation, and next slice

**No ADR change — existing Tester model authority was preserved.**

`docs/architecture/00-current-state.md` remained untouched. No runtime
regression test applies because no tracked runtime wiring was changed. The
documentation validation and Git diff checks for this receipt are recorded
with the task closeout.

Deferred next slice: reconcile Tester local-model authority against the current
Whoosh'd-supported inventory under ADR-074, selecting one explicit canonical
model only after comparing current runtime capability and prior support
doctrine. Keep Watchdog unchanged.
