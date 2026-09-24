# Explicit local-model request authority repair

## Scope and repository identity

This is a bounded architecture-impact repair of text-completion model selection.
It aligns the request path with ADR-069 and ADR-074 and uses ADR-087's existing
terminal task semantics. It does not revise those contracts or promote the
supported Compose campaign from `HOLD`.

| Field | Evidence |
| --- | --- |
| Branch / base | `main` / `1cbf7a56c6e404d48ec9da46ab8df018ca5a3668` |
| Upstream / divergence before mutation | `origin/main` / ahead 10, behind 0 |
| Worktree before mutation | One unrelated staged deletion: `docs/DEV_LOG/2026-09-22/Dev Log - 2026-09-22.md`; no unstaged or untracked files |
| Profile | `v1-local-core-web-mcp` with local-only, cloud-disabled `local-chat` |
| Runtime | `local` provider, Whoosh'd `0.1.0rc3`, `/v1/models` advertising `local-chat` |
| Application stack | Existing `codexify` Compose stack; only `worker-chat` was restarted after bind-mounted source changes; volumes were preserved |

## Pre-repair reproduction and root cause

Before source mutation, a worker-level reproduction used the current checkout,
an explicit `local` request for `missing-local-model-A7K9`, and synthetic
inventory containing only `local-chat`. Incoming `requested_provider=local`,
`requested_model=missing-local-model-A7K9`, and `selection_source=explicit`
survived task deserialization. `_compat_resolve_task` changed the execution
model from the sentinel to `local-chat` through
`_degraded_provider_model_fallback`; the fallback capability lookup ran once.
Independently, `resolve_local_execution_model` returned success with
`model=local-chat`, `source=LOCAL_CHAT_MODEL`, and a message saying the requested
model was overridden. The narrow probe did not invoke a provider or write an
assistant row; its predicted execution model was `local-chat`.

The immediately preceding frozen-tip live qualification provides the provider
and persistence half of the reproduction: accepted task
`a1333dcc-8f16-4f52-a18c-e0da54c037b2` requested the same unavailable
model, executed `local-chat`, persisted assistant message 61, and emitted
`task.completed` outbox row 140. See
[`2026-09-22-current-tip-final-supported-compose-qualification.md`](./2026-09-22-current-tip-final-supported-compose-qualification.md).

The root cause had three parts: worker compatibility fallback could replace an
explicit model; strict local resolution treated `LOCAL_CHAT_MODEL` as stronger
than request intent; and completion metadata could overwrite `explicit` with
the runtime configuration source. The route already carried the required
`requested_model` and `selection_source` fields. No route or provider-registry
change was needed.

## Authority repair

For a text completion with `selection_source=explicit` and a nonempty
`requested_model`, the worker checks the exact model against live local
inventory before provider dispatch. Rejection uses the existing
`local_model_resolution_error` / `local_model_unavailable` vocabulary and
sets accepted true, attempted false, executed false, completed false, and
fallback attempted false. The compatibility fallback remains available for
non-explicit degraded selection.

The local resolver accepts a transient boolean that means the caller's model
is exact. It selects the requested model only when inventory is available and
advertises it; unavailable inventory or model fails closed. Worker and
completion-service calls pass that boolean from existing task authority, and
local stream/nonstream calls preserve it through dispatch. Image payloads stay
on their existing vision-routing path. `LOCAL_CHAT_MODEL=local-chat` remains the
default and is recorded as runtime/config source metadata without overwriting
an explicit request's `selection_source`.

## Focused static validation

| Check | Result |
| --- | --- |
| `pytest -q tests/workers/test_chat_worker_explicit_model_authority.py tests/test_local_model_default_authority.py tests/core/test_ai_router.py tests/core/test_supported_profile_provider.py tests/architecture/test_supported_compose_local_model_projection.py tests/core/test_chat_completion_service_thread_config.py` | PASS, 60 tests |
| `pytest -q tests/core/test_chat_completion_service_model_selection_trace.py tests/core/test_chat_completion_service_image_routing.py tests/routes/test_chat_profile_trace.py` | PASS, 53 tests |
| `pytest -q tests/workers/test_chat_worker_streaming_chunks.py tests/core/test_completion_terminal_integrity.py guardian/tests/workers/test_chat_worker_completion_semantics.py` | PASS, 43 tests |
| `ruff check` on the three changed test files | PASS |
| `compileall -q` on the six changed Python files | PASS |
| `scripts/validate_docs.py` | PASS before this proof was drafted; rerun at closeout |
| Source-module Ruff comparison with base commit | 20 findings before and after; zero new findings |

One neighboring historical worker test still fails:
`guardian/tests/workers/test_chat_worker_provider_resolution.py::test_explicit_model_unavailable_fails_instead_of_fallback`
expects a model-unavailable message for a task with neither
`selection_source=explicit` nor `requested_model`; the current provider gate
reports `Provider blocked by egress policy`. The preceding frozen-tip proof
records the same failure before this repair. Changing that legacy task's
authority semantics or its test file is outside the authorized mutation set.
The adjacent non-explicit degraded-fallback test passes. A full source Ruff run
also reports the 20 pre-existing findings noted above, including undefined
names in unrelated lines; this repair introduced none.

## Bounded live failure and recovery

The bind-mounted supported stack was healthy. Before the probe, Whoosh'd was
ready, advertised `local-chat`, Redis queue depth was zero, and no turn lock
was present. After the final worker restart, authenticated API requests used
disposable thread 14:

| Turn | User message | Task | Result |
| --- | ---: | --- | --- |
| No-model default | 69 | `30b9016d-4aea-452e-8738-6105ca270541` | Accepted, executed `local-chat`, assistant 70 persisted, `task.completed` |
| Explicit unavailable | 71 | `be7647c1-aab8-4384-b7da-6bf92a2d36eb` | Accepted, `task.failed`, `local_model_unavailable` |
| Explicit `local-chat` recovery | 72 | `98e8d9b6-7d0f-4050-8de7-b66b2b37426b` | Accepted, executed, assistant 73 persisted, `task.completed` |

The failed turn ID was `c1cc341b-2945-47ca-8559-dba14f87b49e`.
Authenticated task events and durable outbox row 165 both retained
`requested_model=missing-local-model-A7K9`, `selection_source=explicit`,
`failure_kind=local_model_unavailable`, and completion truth
`accepted=true`, `attempted=false`, `fallback_attempted=false`,
`executed=false`, `completed=false`. The event stream contained no token,
chunk, or completed event for this task. PostgreSQL showed user message 71,
then user message 72, with zero intervening assistant rows; it showed one
`task.failed` outbox row and zero `task.completed` rows for the failed task.
Outbox row 166 was the matching `completion.error` visibility event.

Worker logs showed `chat.inference.request.built` for the successful turns
before and after rejection, with no such dispatch between failed-task start
and the next task start. The worker-level regression spies observed zero
provider-dispatch and assistant-persistence calls for the rejected request.
There was no alternate local-model or cloud rescue; the terminal fallback flag
was false. Whoosh'd request-history correlation was not exposed by the running
host service, so the direct provider-side count is not independently logged in
this receipt. The pre-dispatch failure, task truth, worker dispatch log, and
PostgreSQL evidence are the bounded zero-execution proof.

After recovery, Redis reported `EXISTS turn_lock:14 = 0` and chat queue depth
zero. The accepted recovery turn and persisted assistant 73 demonstrate that
the failed turn did not poison the thread or its lock.

## Disposition and limits

The explicit request-model authority blocker is **CLOSED** for this bounded
supported text-completion path. F1–F7 remain **CLOSED / DOWNSTREAM RESOLVED —
unchanged**. The supported Compose campaign remains **HOLD** until its full
frozen-tip qualification is rerun against this repair commit, including the
rows blocked in the preceding qualification. This task did not change
`00-current-state.md`, provider/runtime ownership, image/vision semantics,
Compose configuration, cloud policy, or release posture.
