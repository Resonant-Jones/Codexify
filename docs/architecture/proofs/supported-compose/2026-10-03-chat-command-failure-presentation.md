# Command failures retain their meaning in chat presentation

Date: 2026-10-03. Baseline: `f4b8aed8e`.
Classification: `AUTHORIZED_IMPLEMENTATION`; architecture-impact lane.
Full qualification remains `HOLD`.

## Atomic Task Spec and authority

Preserve existing `tool_command_failed` and `tool_command_blocked` reasons in
the frontend's owned attempt presentation. Show action failure or authority
rejection rather than a provider error; retain failed terminal projection,
deadline precedence, identity ownership, and no automatic replay. A new request
clears prior failure metadata. Late observation errors and delay timers must
not overwrite an authoritative terminal failure.

This change belongs in the frontend runtime-token registry, inference state
type, shared failure presenter, owned task-stream hook, and GuardianChat global
failure handler. Scope also includes their neighboring tests and this receipt.
P1; owner Codex; architecture/proof review; target Ready for review. Validation
is the baseline regression, seven-suite frontend command below, production
bundle, TypeScript availability check, and `git diff --check`. Commit only those
ten files with subject `fix(chat): distinguish command failures from provider errors`.

Authority is the explicit reliability Goal under the Codex Development Operator
Goal, the Agent Tool Loop Contract, Chat Runtime Contract, runtime token
contract, and ADR-087. The frontend registry mirrors the existing backend tool
state/reason domains; it introduces no backend token, authority, retry policy,
request-state transition, or ADR. The composer's diagnostic lifecycle uses
the existing failed tool state for this failure. This is a presentation
projection, not an assertion of `failed_retryable` or `failed_fatal`.

Accepted event identity remains authoritative for ownership; typed tool fields
determine this presentation. Error prose is evidence only and cannot establish
a tool failure classification. Guardian still owns command authority. No new
durable record is created. Actual runtime evidence remains a separate gate.

## Causal seam and repair

The backend repair at `f4b8aed8e` stops failed/blocked returned commands before
final generation and assistant persistence. Its `task.failed` retains the
canonical reason and `toolTurnState=failed`. The frontend previously lost that
reason, displayed generic Provider error, and attributed its composer lifecycle
to `provider_error`.

The shared presenter now recognizes exact canonical failed tool state plus
either supported failure reason, including the contract's snake-case carrier.
It does not guess from messages, missing state, unknown reason, or contradictory
completed state. Command reasons take precedence over incidental provider timeout
metadata; authoritative accepted-task deadline failure takes precedence over both.

Owned task events (`task.failed`, `completion.error`, `task.state=FAILED`) and
the global GuardianChat terminal handler preserve the recognized reason. Status
and detail describe action failure or lack of authorization. They do not claim
provider offline, completion, a faster-mode remedy, or retryability. Starting a
new request resets the reason. Existing terminal timing does not become success.

## Validation

- Baseline: **8 failed, 68 passed**. Two formatter cases blamed the provider;
  six owned stream cases discarded the command reason.
- Initial repaired formatter/hook group: **76 passed**.
- Final seven-suite group: **196 passed**, zero failures/errors/skips in JUnit.
  Includes four actual-hook global GuardianChat cases, foreign/retired event
  rejection, terminal timer/transport stability, new-request clearing,
  deadline precedence, existing cancellation/fast-mode and sidebar controls.
- `pnpm exec vite build`: **passed**. Existing stale Browserslist, duplicate JSX
  `style` in unchanged SettingsPanelDock, dynamic-import/chunk-size warnings
  remain. This is a transpilation/bundle check, not a TypeScript type check.
- Standalone TypeScript check: **unavailable**. `pnpm exec tsc` returned
  `Command "tsc" not found`; resolving `typescript` returned
  `ERR_MODULE_NOT_FOUND`. No dependency installation or full type-check pass
  is claimed.
- `git diff --check`: **passed**. No unrelated source changes.

From `frontend/src`:

```sh
pnpm exec vitest run --config vitest.config.ts \
  features/chat/__tests__/requestFailurePresentation.test.ts \
  features/chat/__tests__/useInferenceRequestState.test.tsx \
  features/chat/__tests__/GuardianChat.turn-lock-lifecycle.test.tsx \
  features/chat/__tests__/GuardianChat.thread-sync.test.tsx \
  components/persona/layout/__tests__/GuardianChatWithSidebar.terminal-projection.test.tsx \
  contracts/__tests__/runtimeTokens.test.ts \
  contracts/__tests__/runtimeVisualState.test.ts
```

Evidence root:
`/private/tmp/codexify-chat-tool-presentation-f4b8aed8e-20261003/`.
Baseline/final logs and XML, build output, and TypeScript availability output
are retained. Test browser/event/API surfaces are synthetic.

## Whole-path re-evaluation

The retained live stack still runs the prior `065fb06e7` backend source and
has not loaded the returned-command repair. Its last actual ordinary browser
success advertised zero tools and cannot qualify this failure path. The next
atomic proof must refresh the idle task-owned source/worker and use the current
frontend, preserving databases and other queues, then obtain browser and
independent runtime/durable readback.

This receipt is documentation follow-through; no release-truth promotion,
push, main merge, deployment, or memory update occurred. Other tool-loop
failure reasons, durable diagnostic detail, server-side command quiescence,
context/database/terminal bounds, full restart/shutdown, and active-worker-loss
authority remain separate unfinished obligations. The Goal remains active.
