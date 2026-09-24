# Guardian shell terminal projection repair — 2026-09-22

## Result

**Bounded result: PASS. F4 CLOSED.**

`GuardianChatWithSidebar` no longer manufactures a per-request `Queued` state
from provider runtime condition. The supported local browser path now keeps the
outer shell on provider truth while the existing inner Guardian lifecycle owns
queued, warming, first-token, streaming, and terminal request presentation.

This closes only the F4 projection defect. F5 retrieval provenance and F7
static/lifecycle-test findings remain open, so the overall supported-Compose
release posture remains `HOLD`.

## Environment

| Field | Evidence |
| --- | --- |
| Observation window | 2026-09-22 05:42–05:47 EDT (09:42–09:47 UTC) |
| Branch / base commit | `main`; `75707cb9a5b72e284262829cecac53aa88d344e0` |
| Upstream / divergence | `origin/main`; ahead 5, behind 0 |
| Initial worktree | One unrelated staged deletion: `docs/DEV_LOG/2026-09-22/Dev Log - 2026-09-22.md`; no unstaged or untracked paths |
| Supported topology | Existing healthy `docker-compose.yml` plus `docker-compose.whooshd-smoke.yml` stack; no rebuild, recreation, restart, stop, or volume mutation |
| Supported profile | `v1-local-core-web-mcp`, valid with no mismatches |
| Effective route | provider `local`; logical model `local-chat`; runtime Whoosh'd |
| Browser | Headed Playwright CLI against `http://127.0.0.1:5173/chat` |

The unrelated staged Dev Log deletion was not restored, unstaged, modified, or
included in this task's commit.

## Root cause

The local current-tip implementation still contained the exact false
projection before repair:

```ts
const requestState: ChatRequestState =
  providerStateToken === "model_warming" ? "awaiting_model" : "queued";
const visualState = mapRuntimeToVisualState(
  requestState,
  providerStateToken as ProviderRuntimeState
);
```

That code made provider/runtime state the source of a synthetic request state:

```text
provider model_warming -> request awaiting_model
every other provider state -> request queued
```

Provider availability and a completion attempt are separate authorities. The
inner lifecycle had already reached terminal truth, rendered the assistant,
persisted it, and returned the composer to idle. The parent shell nevertheless
recomputed `Queued` from a healthy provider on every render, including reload
and re-entry. The shell therefore contradicted canonical request and durable
runtime truth.

## Repair

`GuardianChatWithSidebar.tsx` now:

- normalizes `providerRuntimeState` through the existing canonical
  `normalizeProviderRuntimeState` helper;
- renders the existing `describeProviderState` title and detail as an explicit
  semantic provider status;
- exposes the canonical provider token through
  `data-provider-runtime-state` for stable inspection;
- preserves the prior blocking behavior for genuine `model_warming` and
  provider `error`; and
- removes the shell-owned synthetic `ChatRequestState` and its call to
  `mapRuntimeToVisualState`.

The repaired authority boundary is:

```text
outer Guardian shell -> provider/runtime condition only
inner Guardian chat -> actual per-attempt request lifecycle
```

No request evidence means the shell creates no request lifecycle presentation.
Healthy idle now presents `Ready`; warming presents `Model warming`; degraded
presents `Provider degraded`; offline presents `Provider offline`. No canonical
token changed, and no new request store, state variable, event channel, or
polling path was introduced.

## Static validation

| Command | Result | Interpretation |
| --- | --- | --- |
| `cd frontend/src && npm test -- --run components/persona/layout/__tests__/GuardianChatWithSidebar.terminal-projection.test.tsx` | PASS: 1 file, 6 tests | Healthy idle, completed transcript, remount/re-entry, model warming, degraded, and offline projections are covered. Each case asserts the semantic provider-status element and canonical provider token; `Queued` is retained only as a negative assertion. |
| `cd frontend/src && npm test -- --run components/persona/layout/__tests__/GuardianChatWithSidebar.stability.test.tsx` | PASS: 1 file, 37 tests | Existing sidebar stability coverage remains green. |
| `cd frontend/src && npx eslint components/persona/layout/GuardianChatWithSidebar.tsx components/persona/layout/__tests__/GuardianChatWithSidebar.terminal-projection.test.tsx` | PASS with warnings: 0 errors, 57 existing warnings in `GuardianChatWithSidebar.tsx`; the new test has no lint findings | Narrow lint introduces no error. Existing broad import/order, unused, and permissive-type warnings remain outside this task. |
| `cd frontend/src && npx tsc -p tsconfig.app.json --noEmit --pretty false` | FAIL before project checking | The installed TypeScript rejects the existing deprecated `baseUrl` option unless an ignore-deprecation override is supplied. |
| `cd frontend/src && npx tsc -p tsconfig.app.json --noEmit --pretty false --ignoreDeprecations 6.0` | FAIL: existing broad frontend error ledger | Errors span unrelated AppShell, dashboard, documents, command-center, flow-builder, settings, React DOM declarations, and existing Guardian source lines. No error points to the new regression file or the repaired provider-projection lines. This remains F7 evidence, not an F4 regression. |

Vitest emitted the existing Node warning that `--localstorage-file` lacked a
valid path; it did not affect either passing suite.

## Live proof

### Browser sequence

1. A fresh Guardian surface opened at `/chat`. The semantic outer status was
   `Provider runtime: Ready` / `ready`; no `Queued` text was present.
2. Existing idle thread `7` was opened before sending. Prior assistant message
   `37` (`F4_BEFORE_20260921_A`) rendered, the composer was idle, and the outer
   status remained `Ready` with no `Queued`.
3. The browser submitted `Reply with exactly F4_AFTER_20260922_X7. Do not add
   anything else.` as user message `38`.
4. While active, the outer shell remained the provider projection `Ready`.
   The existing inner request surface independently showed `Waiting for first
   token…`, a working response row, and a Stop control. This is legitimate
   request-lifecycle presentation rather than shell synthesis.
5. The assistant rendered `F4_AFTER_20260922_X7` as message `39`. The inner
   lifecycle showed `Completed`, the Stop control disappeared, and the composer
   returned to its idle empty state. Without a reload, the outer shell remained
   `Ready`; it did not show `Queued`.
6. A browser reload reconstructed both turn pairs and retained outer `Ready`.
7. The browser navigated to thread `6`, then explicitly re-entered thread `7`.
   The completed transcript reconstructed again and outer `Ready` remained
   correct with no `Queued`.

The final semantic shell element read:

```text
text=Ready
data-provider-runtime-state=ready
aria-label=Provider runtime: Ready
title=The model is loaded and ready for requests.
```

### Correlation and durable truth

| Field | Evidence |
| --- | --- |
| Thread / owner / Project | thread `7`; user `local`; Project `1` (`General`) |
| User message | `38` |
| Task | `c7e8ca30-6c53-4cae-aba8-3ee25be4f8f5` |
| Request | `req_aa497253d306462e9dee182150f877c8` |
| Run | `f9aebfd9739f4a3d8f971a21aca93af0` |
| Attempt | `attempt_5051c1a3265a426a8c4fac9a2721de79` |
| Turn | `9ef3f02a-ded8-4f8c-b6a6-7034bf400c7d` |
| Provider / model / runtime | `local` / `local-chat` / Whoosh'd |
| Assistant message | `39`; exact durable content `F4_AFTER_20260922_X7` |
| Redis task lifecycle | `QUEUED -> AWAITING_MODEL -> AWAITING_FIRST_TOKEN -> STREAMING -> COMPLETED -> task.completed` |
| Redis terminal time | `task.state=COMPLETED` at `2026-09-22T09:44:06.009175+00:00`; `task.completed` at `2026-09-22T09:44:06.292090+00:00` |
| Durable outbox | rows `89` (`task.running`), `90` (`message.created`, message `39`), and `91` (`task.completed`, message `39`) |
| Persistence ordering | rows `38` user then `39` assistant, both on thread `7`, owner `local` |
| Provider truth | terminal evidence reports accepted/executed/completed, persistence `persisted`, final provider `local`, final model `local-chat`, and no fallback |

PostgreSQL independently proved assistant persistence, thread ownership, row
ordering, and durable terminal outbox truth. Redis supplied operational task
lifecycle evidence; it was not treated as durable application authority.

## Finding disposition

| Finding | Disposition | Evidence |
| --- | --- | --- |
| F4 — outer terminal/request projection disagreement | **CLOSED** | Static regression plus real idle, active, terminal, reload, and re-entry browser proof agree with Redis lifecycle and PostgreSQL/outbox truth. |
| F5 — incomplete document/chunk retrieval provenance | **PERSISTS — unchanged** | No retrieval source, persistence, or provenance code was changed or qualified. |
| F7 — static/lifecycle-test findings | **PERSISTS — unchanged** | The narrow suites pass, but the existing repository-wide TypeScript error ledger and known large lifecycle-suite OOM/hang remain outside scope. |

## ADR impact and invariants

**ADR impact: aligned with ADR-069, ADR-087, the Chat Runtime Contract, and the
Runtime Protocol Token Contract; no ADR change.**

- Provider state no longer manufactures request state.
- `queued` remains owned by an actual completion attempt.
- `awaiting_model` remains owned by an actual completion attempt.
- Healthy idle, completed, reloaded, and re-entered surfaces are non-request
  provider presentations.
- Canonical warming, degraded, offline, and error provider meanings remain
  visible through the existing provider-state registry.
- The inner completion lifecycle remains unchanged and authoritative.
- No third request-state channel, duplicate hook, polling loop, token, backend
  change, queue change, worker change, persistence change, retrieval change, or
  lock change was introduced.
- No release claim is widened. The overall supported-Compose posture remains
  `HOLD` because F5 and F7 persist.

## Documentation follow-through

This proof artifact records the bounded F4 repair and qualification.
`docs/architecture/00-current-state.md` remains unchanged as required. Release
reconciliation remains deferred until the remaining supported-path proof gates
justify it.

The next single prerequisite is F5: persist attributable contributing
document/chunk provenance for the supported retrieval path. This proof does not
authorize or begin that work.
