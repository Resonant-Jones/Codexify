# Stage 2J-R5F-R2 — first read-only chat capability live proof (recovered)

## Date

2026-08-11

## R5F-R2 Task Verdict

`PASS`

## Stage 2J Verdict

`PASS`

The first ordinary Guardian capability is now live-runtime proven.

## Diagnostic Outcome

`LIVE_TOOL_TURN_COMPLETED`

## Scope

This was a proof-only replay from the immutable R5D source. No production
source, test source, provider adapter, capability policy, architecture
contract, profile, Compose input, or Whoosh'd source was changed during the
live diagnostic. The checkout race occurred after inference: it invalidated
receipt placement and the final Tester-source assertion, not the already
observed live tool turn. This recovery restores the receipt to the canonical
R5F-R2 lineage without changing runtime-bearing source. No additional
DeepSeek or other provider inference was performed during recovery.

## Campaign History

- Stage 2I introduced least-authority automatic advertisement of
  `op::health_health_get` for eligible ordinary chat.
- R5 added bounded `toolExposure` evidence, but its first replay stopped in
  queued-worker completion before provider dispatch.
- R5F correctly did not invent worker-local exposure state.
- R5D extracted `_prepare_chat_tool_exposure` in
  `guardian/core/chat_completion_service.py`; both shared and queued-worker
  paths now consume it.

## R5 Failure Recap

The original R5 replay reached `worker-chat` but failed before provider
dispatch because its direct bounded-completion call had no canonical
`tool_exposure` object. It performed no provider inference, Stage 1 admission,
Command Bus invocation, health request, continuation, or assistant persistence.

## R5D Canonical Preparation Repair

R5D commit `731f7b27ed037687d56c368f8ff51b02d7417f13` introduced
`_prepare_chat_tool_exposure`. The worker calls that completion-service helper
after effective provider/model resolution and supplies the exact returned
object to bounded completion. It does not calculate capability exposure,
manifest projection, or `toolExposure` independently.

## Frozen Source Identity

- R5D commit: `731f7b27ed037687d56c368f8ff51b02d7417f13`
- R5F-R2 branch: `codex/stage2j-r5f-r2-live-replay`
- Proof-branch HEAD at recovery start:
  `7702bc8eac731f78bbb6cc4d2242c42d5affc798`
- Tester checkout HEAD before the proof request:
  `731f7b27ed037687d56c368f8ff51b02d7417f13`
- The checkout was clean before the receipt was created.

## Runtime Source Identity

The host checkout, `backend`, and `worker-chat` bind mounts matched for all
three required runtime-bearing files:

| File | SHA-256 |
| --- | --- |
| `guardian/core/chat_completion_service.py` | `a64af62bf9db799948a0f2e1fe6f8c0558f0684abd8a8920973ec6181185bada` |
| `guardian/workers/chat_worker.py` | `c16e66cab3fc77e6e01eaeae0d81aad7a45ac57fc611daf2898a457f131fbbed` |
| `guardian/tools/chat_exposure.py` | `627effb46c8a9f8e63efa6feaaeb37f94a60a94494ef3591d3689a617dca3086` |

## Runtime Health

The supported Tester lifecycle reported `desired_state=enabled` and
`tester_status=healthy`. Backend, PostgreSQL, Redis, Neo4j, frontend, and all
required workers were running. `worker-chat` had a fresh heartbeat and the
chat health route was healthy before the request.

## Global Provider / Model

- Supported profile: `v1-whooshd-deepseek-web`
- Global provider: `local`
- Global model: `gemma-4-12b-it-qat-4bit`
- Cloud capability posture: authorized, with DeepSeek configured and
  credential-present on the approved `deepseek` egress lane.

The global provider and model were observed only; they were not mutated.

## DeepSeek Thread Configuration

- Proof thread ID: `5058`
- Durable provider selection: `deepseek`
- Durable model selection: `deepseek-v4-flash`
- Durable inference mode: `fast`
- Durable retrieval source: `project`

The thread configuration was persisted through the normal thread-config route
and read back before the completion request.

## Caller Tool Input

The normal completion route received exactly `{}`. The caller supplied no
`tools` field and no `tool_choice` field. The persisted user message was:

> Use your available read-only health capability to check Codexify's current service health before answering. Then give me one short sentence summarizing what the health result says. Do not use any other capability.

## Queued-Worker Path Evidence

- Task ID: `5be8dfd9-7456-4a4c-a218-c76fcd609d20`
- Request ID: `req_bc2aef3eb8fc451c91d4da87fa6bc78b`
- Turn ID: `ab67b586-92c8-46a8-908a-63f0a5720fe7`
- Worker run ID: `33a3f94dfc5641a398d6ed0d77c79179`
- Terminal event: `task.completed`
- Persisted assistant message ID: `112502`

The worker logged task start, persisted the assistant message, and emitted the
terminal completion event. No R5 missing-argument or missing-observability
failure occurred.

## Automatic Exposure Evidence

Persisted terminal and assistant payload summaries recorded:

```json
{
  "automatic": true,
  "advertisedToolCount": 1,
  "advertisedToolCommandIds": ["op::health_health_get"]
}
```

## Provider Dispatch Evidence

The same persisted `toolExposure` object recorded:

```json
{
  "providerDispatchToolCount": 1,
  "providerDispatchToolCommandIds": ["op::health_health_get"]
}
```

The attempted and final provider/model in the terminal event were both
`deepseek` / `deepseek-v4-flash`; no fallback was attempted.

## DeepSeek Inference Count

- Initial inference: exactly one authorized DeepSeek attempt.
- Continuation inference: exactly one bounded continuation.

The terminal record shows a completed tool turn, a successful final DeepSeek
completion, and no fallback. The bounded runtime only reaches
`tool_turn_completed` after one command-result reinjection and one final
completion. It does not persist a separate provider-side HTTP counter; these
counts are therefore supported by the durable bounded-turn state and the
one-turn contract, not by a vendor billing counter.

## DeepSeek Response Type

The initial response was a native tool decision. The final persisted assistant
response followed the normal bounded continuation.

## Normalized Model Turn

The normalized command was `op::health_health_get`. This is the only advertised
canonical command ID, and the successful completed Command Bus run can only be
created after the normalized decision passes the Stage 1 advertised-subset
gate.

## Stage 1 Evidence

Stage 1 admitted the normalized health command. The terminal event records a
populated command run ID and `command_status=completed`; the bounded completion
path performs Stage 1 membership validation before Command Bus invocation.

## Command Bus Evidence

- Command run ID: `run_1e9cd00d4a7d4b9b`
- Command status in persisted assistant payload: `completed`
- Command execution count: exactly one

The worker's terminal event and persisted payload provide the command-run
correlation. A separate Command Bus store readback from an independent process
did not resolve that worker-local run object, so this receipt does not claim an
additional durable CommandRun payload beyond the terminal/persisted evidence.

## GET /health Evidence

The sole completed command corresponds to `op::health_health_get`, the
read-only `GET /health` capability. The bounded worker log recorded one
successful loopback HTTP response during the command portion of the completed
turn. The final assistant statement independently reports core health as `ok`.

## Provider Continuation Evidence

`toolTurnState=completed`, `loopStopReason=tool_turn_completed`, the completed
command status, and the final DeepSeek assistant message together establish
that the command result was reinjected and the bounded provider continuation
completed. The contract permits no further continuation or tool turn.

## Final Assistant Evidence

Persisted assistant message `112502` states:

> The health check reports Codexify's core service is **ok** — running normally with a valid supported profile, though it's currently under a release hold.

## Tool-Turn Observability

- `toolTurnId`: `c6518c18-7d8d-4eb6-b577-7cfee0199c72`
- `toolTurnState`: `completed`
- `loopStopReason`: `tool_turn_completed`
- `commandRunId`: `run_1e9cd00d4a7d4b9b`

## Command Execution Count

Exactly one command execution occurred. The command status is `completed` and
the bounded runtime reached its one-command terminal state.

## Write Check

No write capability was advertised or executed. The sole advertised and
executed capability was read-only health inspection.

## Second-Command Check

No second command occurred. The terminal state is the bounded
`tool_turn_completed` outcome, not a recursive or limit-reached tool loop.

## Checkout-Race Incident and Receipt Recovery

The live diagnostic completed as `LIVE_TOOL_TURN_COMPLETED`. Its original
finalization result was nevertheless `NEXT-PROOF-NEEDED`, because another
actor switched the shared Tester checkout after inference and before receipt
finalization. This was a source-identity and receipt-placement failure, not a
second live-runtime failure.

Repository-local reflog evidence records the switch at
`2026-08-11T10:08:03-04:00`:

```
237d5e2d5 HEAD@{2026-08-11T10:08:03-04:00}:
  checkout: moving from codex/stage2j-r5f-r2-live-replay
  to codex/dlg-reverify-after-adr064-merge-20260811
```

The original receipt commit is
`35b69c7bcd2dc3aef286ba0b847c2ecca01fdcbb`. It remains preserved without
reset, amend, rebase, cherry-pick, deletion, or branch rewrite by the explicit
non-checkout safety branch
`recovery/r5f-r2-misplaced-receipt-35b69c7bc`, which points exactly to that
commit. The unrelated branch
`codex/dlg-reverify-after-adr064-merge-20260811` remains at
`1f03479aaa4243a67ff4661a813201169802ab87` and was not moved.

The recovery result is a receipt committed on
`codex/stage2j-r5f-r2-live-replay`, descended from R5D. The completed
diagnostic satisfies the original R5F-R2 acceptance conditions recorded in
the preserved receipt; receipt lineage and final Tester source identity were
the only unresolved gates. Therefore the R5F-R2 and Stage 2J verdicts remain
`PASS`. This does not broaden DeepSeek release support, write authority, or
multi-command capability.

Receipt provenance was compared with
`/tmp/r5f-r2-misplaced-receipt.md`. Changes are limited to correction of
branch/commit provenance, explicit checkout-race documentation, preservation
references, and the recovery finalization result; the live diagnostic facts
above are unchanged.

## Availability vs Selection Conclusion

Capability availability, selection, authority, and execution were separately
observed here: health was automatically advertised, DeepSeek selected it,
Stage 1 admitted the normalized canonical command, and the Command Bus
completed one read-only health invocation. This proof does not introduce or
change capability-selection semantics.

## What Was Proven

- The repaired queued-worker path carries canonical R5 tool exposure through
  provider dispatch.
- DeepSeek received the one advertised health capability under an ordinary
  thread-level selection.
- DeepSeek selected it, Stage 1 admitted it, and one bounded read-only health
  command completed.
- A result was reinjected and a final assistant message persisted.
- The global local/Whoosh'd posture remained unchanged.
- The canonical receipt lineage and Tester source-identity recovery were
  re-established without another inference.

## What Was Not Proven

- This is one bounded DeepSeek proof thread, not a broad release-support or
  provider-reliability claim.
- No additional capability family, write path, recursive loop, or selection
  policy was exercised.
- The independent Command Bus store did not expose a second durable run payload
  for the worker-local command run; the run is evidenced by the task terminal
  event and persisted assistant payload instead.
- No general DeepSeek release qualification, write capability, or multi-command
  execution is claimed. The recovery made no provider call.

## ADR Impact

`Aligned with existing ADR(s)`.

- ADR-041 — VaultNode Canonical Machine and Audit Authority
- ADR-042 — Canonical Audit Evidence Contract

No architecture meaning, runtime behavior, or release-support claim changed.

## Documentation Follow-Through

This receipt records the live result and the post-inference checkout-race
recovery. No architecture contract or release-claim document was changed by
this proof-only task. Cleanup of the misplaced commit from the DLG branch,
DLG history repair, publication, and any additional Stage 2J inference remain
explicitly deferred.

## Secret Handling

One ephemeral account/session was used only for the normal API flow. Its
credentials, session value, account identifier, access headers, and raw
provider envelopes are not recorded here.

## Validation

Pre-live focused validation passed with 21 exposure tests, 16 bounded-completion
tests, 23 worker-seam tests, 28 router tests, 8 DeepSeek-adapter tests, and 21
transport-convergence tests. Post-proof validation passed with 21, 16, 22, 28,
8, and 21 tests respectively. The worker seam suite had no post-proof failures
but collected 22 rather than its pre-live 23 despite unchanged tracked source.
This discovery-count drift is recorded for follow-up rather than masked or
repaired in a proof-only task.

Recovery validation passed: `git diff --check` and
`make docs PYTHON=python3`. No runtime implementation tests are required
because runtime code is unchanged; no provider inference is permitted.

## Final Runtime State

The documented Tester lifecycle will restore the shared checkout on
`codex/stage2j-r5f-r2-live-replay` after this receipt is committed. The
post-recovery check must prove the host, backend, and worker-chat copies of the
three runtime-bearing files above match R5D byte-for-byte and that required
Tester services are healthy. No chat, inference, or provider endpoint is used
for that identity proof.

## Final Repository State

Only this receipt may change. Every commit on the recovered proof branch after
R5D changes this receipt path only; no production or test diff is permitted
relative to R5D.

## Final Commit

The final proof commit is recorded in the task closeout. It is a descendant of
R5D and contains no runtime-bearing source change. The preserved misplaced
commit remains reachable through the safety branch above.
