# Stage 2J-R4 — First Read-Only Chat Capability Live Proof

## Date

2026-08-10

## Verdict

`NEXT-PROOF-NEEDED`

The one authorized ordinary DeepSeek completion executed and persisted, but it returned a plain assistant answer rather than selecting a capability. The attempt therefore did not enter the bounded tool-turn path. No retry was sent.

## Scope

This is an operator-truth reconciliation and one bounded live proof attempt. It updates the Tester runbook and records the existing ordinary-thread provider-selection path. It does not change production Python, Compose semantics, provider defaults, Whoosh'd source, supported profiles, or release posture.

## Stage 2J Proof History

- Stage 2J established the initial proof boundary but found the Tester mounted from stale source.
- R1 refreshed the proof approach but retained a worktree-safety boundary.
- R2 established that the protected local worktree state was legitimate and recreated the Tester from the canonical root.
- R3 correctly observed the current runtime and source identity, but classified `LLM_PROVIDER=local` as a failure under the older DeepSeek-only runbook assumption.
- R4 reconciles that interpretation with the later accepted dual-provider transition and performs the one permitted ordinary DeepSeek attempt.

## R3 Interpretation Correction

R3's runtime observations remain useful: the current-source backend and worker were healthy and used `v1-whooshd-deepseek-web` with `LLM_PROVIDER=local`. Its `FAIL` interpretation depended on the superseded DeepSeek-only operator-runbook/proof baseline. Repository history and ADR-052 establish the later, controlling topology: Whoosh'd/Gemma is the global primary provider and DeepSeek is the approved per-thread cloud lane. R4 treats R3 as discovery of operator-documentation/proof-baseline drift, not as proof that the provider override was broken.

## Frozen TARGET_MAIN

`bad5e41f764bb33a68a4628b17f4775d650fbc03` (`origin/main` after the one required fetch).

The persistent Tester root was on local `main` with later documentation-only commits. Its runtime-bearing surfaces (`guardian`, supported-profile configuration, the three Compose files, and Tester lifecycle script) had no diff from `TARGET_MAIN`.

## Stage 2I Ancestry

`61e1a4b2beb29c905bc14cfec1db524101b01e88` is an ancestor of `TARGET_MAIN`.

## Tester Dual-Provider Transition Ancestry

`9e862beafb99afa179dba2e6ebcdd9a2f76b9484` is an ancestor of `TARGET_MAIN`.

## Governing ADR-052

Aligned with existing ADR-052, *Whoosh'd Gemma and Approved DeepSeek Startup Profile*. No new ADR is required: this proof preserves local Whoosh'd/Gemma as the Tester default and selects the already approved DeepSeek lane only on the proof thread.

## Canonical Tester Provider Topology

- Supported profile: `v1-whooshd-deepseek-web`.
- Global provider/model: local Whoosh'd, `gemma-4-12b-it-qat-4bit`.
- Cloud lane: DeepSeek `deepseek-v4-flash`, allowed only by the Tester egress policy and selected through durable thread configuration.
- The canonical persistent lifecycle retains the ordered `docker-compose.whooshd-deepseek.yml` overlay. No runtime or environment change was made for this proof.

## Operator Documentation Drift

Before R4, `docs/Ops/friends-family-tester-runtime.md` still named `v1-friends-family-web` and stated that Tester chat routed through DeepSeek instead of Whoosh'd. R4 updates only that provider/startup truth and the corresponding canonical raw Compose examples.

## Runtime Source Identity

- `make -C /Volumes/Dev_SSD/Codexify-main tester-status` reported a healthy backend and `worker-chat` from the canonical Tester root.
- Both runtime copies of `guardian/tools/chat_exposure.py` matched the host copy with SHA-256 `627effb46c8a9f8e63efa6feaaeb37f94a60a94494ef3591d3689a617dca3086`.
- Backend and worker bind mounts resolved to `/Volumes/Dev_SSD/Codexify-main` (with Docker Desktop's `/host_mnt` normalization on some mounts).

## Runtime Health

Before and after the attempt, `make tester-status`, `/health`, `/health/chat`, and `/api/health/llm` reported the Tester healthy. The chat queue was empty and the worker heartbeat was fresh after the run.

## Global Provider / Model

Backend and worker-chat non-secret configuration agreed:

```text
CODEXIFY_SUPPORTED_PROFILE=v1-whooshd-deepseek-web
LLM_PROVIDER=local
ALLOW_CLOUD_PROVIDERS=true
CODEXIFY_LOCAL_ONLY_MODE=false
CODEXIFY_EGRESS_ALLOWLIST=deepseek
LOCAL_PROVIDER_VENDOR=whooshd
LOCAL_CHAT_MODEL=gemma-4-12b-it-qat-4bit
DEEPSEEK_CHAT_MODEL=deepseek-v4-flash
```

Post-proof LLM health still reported local Whoosh'd/Gemma as the selected global default.

## DeepSeek Lane Availability

The non-secret provider catalog exposed `deepseek` as enabled, authorized, available, and chat-capable for `deepseek-v4-flash`. Both backend and worker confirmed the cloud credential was present without printing it. The current supported profile remained valid with DeepSeek as the egress-allowed cloud lane.

## Whoosh'd State

The exact qualified target, `gemma-4-12b-it-qat-4bit`, was advertised by Whoosh'd. Its read-only health snapshot reported `model_lifecycle=ready`, `active_model=null`, and the model provenance reported `model_lifecycle=unloaded`. R4 did not load, warm, unload, or otherwise alter it.

## Deterministic Regression Gate

The required suites passed before cloud inference (74 tests total):

```text
tests/core/test_chat_tool_exposure.py
tests/providers/test_tool_turn_transport_convergence.py
tests/core/test_chat_completion_service_tool_loop.py
tests/routes/test_thread_config_update.py
tests/core/test_chat_completion_service_thread_config.py
tests/ops/test_codexify_tester_services.py
tests/core/test_supported_profile_provider.py
```

## Authentication Path

No pre-existing safely reusable session was available. One ephemeral proof-only account was created through `POST /api/auth/register`, then authenticated through `POST /api/auth/login`. Its credential and session token remained only in the short-lived proof process and were not recorded in this receipt, repository, or command output.

## Proof Thread Creation

One ordinary thread was created through `POST /api/chat/threads`: thread `5056`.

## Thread Provider Configuration

The ordinary supported config endpoint accepted exactly the needed selection:

```json
{"providerId":"deepseek","modelId":"deepseek-v4-flash"}
```

The persisted full snapshot also retained only existing defaults: `inferenceMode=fast`, `retrievalSource=project`, and `personaId=null`.

## Thread Provider Readback

The normal thread readback completed before inference and returned `providerId=deepseek` and `modelId=deepseek-v4-flash`. Durable `chat_threads.thread_config` readback afterwards matched the same provider/model snapshot. The global local provider did not change.

## Ordinary Chat Request

The one user message (persisted as message `112498`) was:

> Use your available read-only health capability to check Codexify's current service health before answering. Then give me one short sentence summarizing what the health result says. Do not use any other capability.

One ordinary completion was accepted for task `c2d54c79-ea47-46fc-8a95-ccbcac998508`, request `req_ab7b015a63da445ab7a683d5e4cfa770`, and turn `b1f030db-62a6-4e2e-aa40-2d9d2bae4ece`.

## Confirmation Caller Supplied No Tools

The normal completion route received the ordinary empty JSON payload `{}`. The caller supplied neither `tools` nor `tool_choice`, and no private tool-loop or direct Command Bus route was invoked as the proof path.

## Effective Completion Provider

The durable task-completed payload records `attempted_provider=deepseek`, `attempted_model=deepseek-v4-flash`, `final_provider=deepseek`, `final_model=deepseek-v4-flash`, `fallback_triggered=false`, and `completion_truth.completed=true`.

## Automatic Exposure Evidence

Not proven live in this attempt. The running source contains the Stage 2I exposure canary, but because the provider returned a plain answer, this evidence cannot establish that `op::health_health_get` was automatically advertised to the model for this turn.

## DeepSeek Native Tool Call

Absent. The terminal payload reports `tool_turn_used=false`; no native DeepSeek tool call was received.

## Normalized Canonical Command

Absent. `op::health_health_get` was not selected or normalized during the one authorized attempt.

## Stage 1 Authority Evidence

Absent because no normalized command reached Stage 1. There is no evidence of a bypass; the bounded path was simply never entered.

## Command Bus Evidence

No Command Bus invocation occurred. Read-only durable storage checks found zero `command_runs` created after the proof request, including zero `op::health*` runs.

## Real GET /health Evidence

Absent: no command was selected, so no command execution could issue `GET /health`.

## Provider Continuation Evidence

Absent: there was no command result to reinject, and therefore no DeepSeek tool-result continuation turn.

## Final Assistant Evidence

The ordinary assistant reply persisted as message `112499`. It was a plain response declining live health access, rather than the requested health summary. Worker logs and the durable task event both record the task as completed.

## Canonical Tool-Turn Observability

The durable assistant metadata and task-completed event agree:

```text
messageId=112498
requestId=req_ab7b015a63da445ab7a683d5e4cfa770
toolTurnId=null
toolTurnState=idle
loopStopReason=plain_answer
commandRunId=null
```

This is conclusive negative evidence for the tool-turn requirements, not a substitute for them.

## Command Execution Count

`0`. No `command_runs` record was created for the proof window.

## Write-Action Check

No capability command, read or write, executed. The only durable writes were the explicitly authorized supported account/thread/message setup needed to make the ordinary chat attempt; no write capability was selected.

## Second-Command Check

`0`. No first command ran, and consequently no second command or recursive tool loop ran.

## Global Provider Preservation

Confirmed. Post-proof health still reported `LLM_PROVIDER=local`, Whoosh'd as the global provider, and `gemma-4-12b-it-qat-4bit` as the global model. The DeepSeek selection remained confined to proof thread `5056`.

## Secret Handling

No secret value was printed or committed. Cloud-credential evidence is recorded only as a presence boolean; proof-account credentials and session material were ephemeral.

## What Was Proven

- ADR-052's dual-provider Tester topology matches the healthy current runtime.
- The stale DeepSeek-only runbook claim was incorrect and is reconciled in the authorized runbook.
- The supported ordinary thread-config surface accepts and durably resolves the approved DeepSeek provider/model while global Tester defaults remain local Whoosh'd/Gemma.
- A real DeepSeek `deepseek-v4-flash` ordinary completion executed once, without fallback, and persisted its final assistant message.
- The one run did not execute any capability or Command Bus command.

## What Was Not Proven

- Automatic advertisement of `op::health_health_get` in this live provider turn.
- DeepSeek native tool selection, Stage 1 admission, Command Bus execution, real `GET /health`, tool-result continuation, or final answer after a tool turn.
- The Stage 2J first ordinary Guardian capability live proof.

## Observability Limitations

The normal task-list poll helper did not recognize the event system's `terminal` state label and was interrupted only after worker logs showed completion. No provider work was interrupted or retried. The final evidence comes from the durable `task.completed` event, persisted chat messages, bounded worker/backend logs, and read-only Command Bus storage checks. Because no tool turn occurred, there is necessarily no command-run readback to inspect.

## ADR Impact

Aligned with ADR-052. This task corrects operator documentation and uses an existing provider-selection contract; it does not change accepted provider topology, capability semantics, or release claims.

## Documentation Follow-Through

Updated `docs/Ops/friends-family-tester-runtime.md` to name the canonical dual-provider profile, preserve Whoosh'd/Gemma as default, describe the DeepSeek thread lane, and include the third Compose overlay in canonical raw lifecycle examples. No unrelated Tester documentation, ADR, current-state, or release claim changed.

## Validation

- Required seven-suite regression gate: passed (74 tests).
- Runtime source, health, provider, catalog, thread-config, task-event, persisted-message, and command-run readbacks: completed as recorded above.
- `python3 scripts/validate_docs.py`: passed.
- `make docs PYTHON=python3`: passed. Its optional diagram freshness helper could not read the linked-worktree Git-LFS temporary metadata, so it skipped its source-diff subcheck; it reported no runtime-source drift from its remaining checks.
- `git diff --check`: passed with the required read-only Git-LFS metadata access.
- Focused secret scan of the runbook and this receipt: no secret value or private-key material found.

## Final Runtime State

Tester remains enabled and healthy. No restart, environment mutation, profile change, Whoosh'd load/warm/unload action, or Compose change occurred.

## Final Repository State

The isolated proof worktree changes only the authorized runbook and this R4 receipt. The persistent Tester root's unrelated protected `.worktrees/` state remains untouched.

## Commit

The scoped commit hash is reported in the task closeout after final documentation validation and path-scoped staging.
